from pathlib import Path
import difflib, hashlib, io, json, math, shutil, stat, threading, time, zipfile
from . import prm, knowledge
from .storage import DATA, config, execute, get_case, query, uid

EXCLUDE={'build','.git','__pycache__','node_modules','output','outputs'}
_edit_lock=threading.RLock()

class RevisionConflict(ValueError): pass

def create(name,text,provenance=None,assets=None):
    prm.entries(text)
    case_id=uid(); root=DATA/'cases'/case_id; root.mkdir(parents=True)
    if assets:
        source=Path(assets).resolve()
        total=0
        for p in source.rglob('*'):
            rel=p.relative_to(source)
            if any(x in EXCLUDE or x.startswith('output-') for x in rel.parts): continue
            if p.is_symlink(): continue
            if p.is_file():
                total+=p.stat().st_size
                if total>300_000_000: raise ValueError('Case assets exceed 300 MB; import a smaller case folder')
                dest=root/'assets'/rel; dest.parent.mkdir(parents=True,exist_ok=True); shutil.copy2(p,dest)
    # Working directory is assets so relative WB/data paths remain valid.
    (root/'assets').mkdir(exist_ok=True)
    (root/'draft.prm').write_text(text)
    (root/'original.prm').write_text(text)
    execute('INSERT INTO cases VALUES(?,?,?,?,?)',(case_id,name,str(root),time.time(),json.dumps(provenance or {},ensure_ascii=False)))
    return {'case_id':case_id,'name':name,'draft':str(root/'draft.prm')}

def load_document(document_id):
    d=knowledge.read_document(document_id)
    if d.get('role')=='reference': raise ValueError('Reference-only source: adapt to the installed ASPECT version before creating a model')
    if d['kind']=='fragment' or not d['path'].endswith('.prm'): raise ValueError('Select a complete PRM model, not a manual fragment')
    p=Path(d['absolute_path'])
    source=next(s for s in knowledge.sources() if s['label']==d['source'])
    text=prm.expand(p,[source['root']])
    return create(p.stem,text,{'source':d['source'],'version':d['version'],'path':d['path']},p.parent)

def import_local(path):
    p=Path(path).expanduser().resolve()
    if not p.is_file() or p.suffix.lower()!='.prm': raise ValueError('Provide an existing PRM file')
    return create(p.stem,prm.expand(p,[p.parent,config()['source_root']]),{'local_path':str(p)},p.parent)

def import_upload(name,content):
    if name.lower().endswith('.prm'): return create(Path(name).stem,content.decode('utf-8-sig'),{'upload':name})
    if not name.lower().endswith('.zip'): raise ValueError('Upload PRM or ZIP')
    target=DATA/'uploads'/uid(); target.mkdir(parents=True)
    with zipfile.ZipFile(io.BytesIO(content)) as z:
        size=sum(i.file_size for i in z.infolist())
        if size>300_000_000 or len(z.infolist())>10000: raise ValueError('ZIP too large')
        for item in z.infolist():
            dest=(target/item.filename).resolve()
            if not dest.is_relative_to(target.resolve()) or stat.S_ISLNK(item.external_attr>>16):
                raise ValueError('Unsafe archive member')
            if item.is_dir(): dest.mkdir(parents=True,exist_ok=True)
            else:
                if Path(item.filename).suffix.lower() in {'.so','.dylib','.exe'}: raise ValueError('Import compiled plugins using a trusted local model directory')
                dest.parent.mkdir(parents=True,exist_ok=True); dest.write_bytes(z.read(item))
    prms=[p for p in target.rglob('*.prm') if not any(x.startswith('output') or x=='__MACOSX' for x in p.relative_to(target).parts)]
    main=[p for p in prms if p.name in {'model.prm','input.prm'}]
    if len(prms)==1: return import_local(prms[0])
    if len(main)==1: return import_local(main[0])
    return {'needs_selection':True,'prm_files':[str(p) for p in prms],'message':'ZIP contains multiple PRM files. Select the entry file via local import.'}

def draft(case_id): return (Path(get_case(case_id)['path'])/'draft.prm').read_text()

def save_draft(case_id,text,expected_revision=None):
    with _edit_lock:
        prm.entries(text); root=Path(get_case(case_id)['path'])
        before=draft(case_id)
        if expected_revision and hashlib.sha256(before.encode()).hexdigest()!=expected_revision:
            raise RevisionConflict('Parameter file changed')
        versions=root/'versions'; versions.mkdir(exist_ok=True)
        (versions/f'{time.time_ns()}.prm').write_text(before)
        tmp=root/'draft.tmp'; tmp.write_text(text); tmp.replace(root/'draft.prm')
        return {'case_id':case_id,'diff':''.join(difflib.unified_diff(before.splitlines(True),text.splitlines(True),fromfile='before',tofile='after'))}

def modify(case_id,changes,allow_new=False):
    with _edit_lock:
        return save_draft(case_id,prm.patch(draft(case_id),changes,allow_new))

def enqueue(case_id,cores=None,batch='',value=None,kind='simulation',text_override=None,timeout=None):
    cores=int(cores or config()['task_cores'])
    if not 1<=cores<=int(config()['max_total_cores']): raise ValueError('Core request exceeds configured total core budget')
    text=text_override if text_override is not None else draft(case_id); prm.entries(text); job_id=uid()
    root=DATA/'runs'/job_id; root.mkdir(parents=True)
    shutil.copytree(Path(get_case(case_id)['path'])/'assets',root/'assets')
    # Outputs live on host disk, never in a temporary container or draft folder.
    out=root/'output'; out.mkdir()
    text=prm.patch(text,{'Output directory':str(out)},allow_new=True)
    (root/'input.prm').write_text(text)
    (root/'manifest.json').write_text(json.dumps({'job_id':job_id,'case_id':case_id,'cores':cores,
        'binary':config()['binary'],'source_root':config()['source_root'],'mpi':config()['mpi'],
        'timeout_seconds':timeout or config()['timeout_seconds'],'created':time.time(),'kind':kind,
        'value':value,'output_directory':str(out)},ensure_ascii=False,indent=2))
    execute('INSERT INTO jobs(id,case_id,batch,state,cores,created,value,kind) VALUES(?,?,?,?,?,?,?,?)',
        (job_id,case_id,batch,'queued',cores,time.time(),json.dumps(value),kind))
    return {'job_id':job_id,'state':'queued','output_directory':str(out),'input_snapshot':str(root/'input.prm')}

def sweep(case_id,path,start,stop,count=5,sampling='log',cores=None,index=None):
    cores=int(cores or config()['task_cores'])
    start=float(start); stop=float(stop); count=int(count)
    if not math.isfinite(start) or not math.isfinite(stop) or not 2<=count<=64: raise ValueError('Finite range and 2–64 samples required')
    if sampling not in {'log','linear'}: raise ValueError('sampling must be log or linear')
    if sampling=='log' and min(start,stop)<=0: raise ValueError('Log sampling requires positive endpoints')
    vals=prm.values(draft(case_id))
    if path not in vals: raise ValueError('Parameter path not found')
    base=vals[path]
    if ',' in base and index is None: raise ValueError('List parameter: explicitly specify the zero-based component index')
    if index is not None:
        parts=base.split(','); index=int(index)
        if not 0<=index<len(parts): raise ValueError('Component index outside list')
    # Complete preflight before creating any jobs.
    if not 1<=int(cores)<=int(config()['max_total_cores']): raise ValueError('Core budget exceeded')
    batch=uid(); jobs=[]
    for i in range(count):
        f=i/(count-1)
        val=math.exp(math.log(start)*(1-f)+math.log(stop)*f) if sampling=='log' else start*(1-f)+stop*f
        replacement=f'{val:.12g}'
        if index is not None:
            arr=base.split(','); arr[index]=replacement; replacement=','.join(arr)
        text=prm.patch(draft(case_id),{path:replacement})
        case=create(f'sweep-{path.split("/")[-1]}-{val:.5g}',text,
            {'parent':case_id,'parameter':path,'value':val,'index':index},Path(get_case(case_id)['path'])/'assets')
        jobs.append(enqueue(case['case_id'],cores,batch,{'path':path,'value':val,'index':index}))
    return {'batch':batch,'jobs':jobs,'count':len(jobs)}

def cancel(job_id):
    rows=query('SELECT * FROM jobs WHERE id=?',(job_id,))
    if not rows: raise ValueError('Unknown job')
    execute("UPDATE jobs SET cancel=1,state=CASE WHEN state='queued' THEN 'cancelled' ELSE state END WHERE id=?",(job_id,))
    return {'job_id':job_id,'cancel_requested':True}


def write_input_file(case_id,filename,content):
    root=Path(get_case(case_id)['path'])/'assets'
    dest=(root/filename).resolve()
    if not dest.is_relative_to(root.resolve()) or dest.suffix.lower() not in {'.wb','.txt','.dat','.csv','.json'}:
        raise ValueError('Only relative WB/text/data input files inside this case are supported')
    if len(content.encode())>2_000_000: raise ValueError('Generated input exceeds 2 MB')
    if dest.suffix.lower() in {'.wb','.json'}: json.loads(content)
    if dest.exists():
        versions=root.parent/'versions'; versions.mkdir(exist_ok=True)
        shutil.copy2(dest,versions/f'{time.time_ns()}-{dest.name}')
    dest.parent.mkdir(parents=True,exist_ok=True)
    tmp=dest.with_name(dest.name+'.tmp'); tmp.write_text(content); tmp.replace(dest)
    return {'case_id':case_id,'filename':filename,'path':str(dest),'bytes':len(content.encode())}

def read_input_file(case_id,filename):
    root=Path(get_case(case_id)['path'])/'assets'; dest=(root/filename).resolve()
    if not dest.is_relative_to(root.resolve()) or dest.suffix.lower() not in {'.wb','.txt','.dat','.csv','.json','.prm'}:
        raise ValueError('Only case input files can be read')
    return {'filename':filename,'content':dest.read_text()[:200000]}
