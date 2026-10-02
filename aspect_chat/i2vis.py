"""Version-scoped I2VIS inputs, snapshots and bounded execution (no shell tools)."""
from pathlib import Path
import difflib,hashlib,io,json,math,os,re,shutil,stat,time,zipfile
from . import storage

REVISION='a203df002bf8e41c3a29ad0c4857cef3d1daf0a1'
HEADER=['cartpolar','xnumx','ynumy','mnumx','mnumy','xsize','ysize','radius','pinit','GXKOEF','GYKOEF','timesum','nonstab']
ROCK=['markn0','markn1','marks0','marks1','marknu','markdh','markdv','markss','markmm','markll','marka0','marka1','markb0','markb1','marke0','marke1','markro','markbb','markaa','markcp','markkt','markkf','markkp','markht']
FILES={'init.t3c','mode.t3c'}

def runtime_root(): return Path(os.environ.get('CHATGFD_I2VIS_ROOT','/opt/i2vis'))
def source_root(): return runtime_root()/'source'
def tokens(text):
    # Upstream ffscanf skips individual tokens starting '/', not entire comment lines.
    return [(m.group(),m.start(),m.end()) for m in re.finditer(r'\S+',text) if not m.group().startswith('/')]
def number(token):
    m=re.match(r'^[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?',token)
    if not m: raise ValueError('Expected a numeric token: '+token)
    n=float(m.group())
    if not math.isfinite(n): raise ValueError('Nonfinite value')
    return n

def parse_init(text):
    ts=tokens(text);i=0;params={};positions={}
    def take(path,numeric=True):
        nonlocal i
        if i>=len(ts): raise ValueError('Unexpected end of init.t3c at '+path)
        t=ts[i];i+=1;positions[path]=(t[1],t[2]);params[path]=number(t[0]) if numeric else t[0];return params[path]
    for name in HEADER:
        take('init/'+name)
        if name in {'mnumx','mnumy'} and params['init/'+name]<0:
            for extra in (('minmx','maxmx') if name=='mnumx' else ('minmy','maxmy')): take('init/'+extra)
    n=params['init/nonstab']
    for name in (['dx','dy'] if n>0 else ['wamp','wlen']+(['wymin','wymid','wymax'] if n==-2 else []) if n<0 else []):take('init/'+name)
    take('init/markers_file',False)
    if params['init/markers_file']!='0': raise ValueError('Import initial geometry with markers_file=0; checkpoint restart is not an initialization template')
    take('init/output',False);take('init/output_type',False)
    rocks={}
    while i<len(ts) and ts[i][0]!='~':
        ident=ts[i][0];i+=1;rid=int(number(ident[1:] if ident.startswith('i') else ident));row={}
        if not 0<=rid<100: raise ValueError('Material ID must be in 0..99')
        for name in ROCK:
            path=f'rock/{rid}/{name}'
            if name=='markht' and ts[i][0].startswith('k'):
                t=ts[i];positions[path]=(t[1],t[2]);row[name]=number(t[0][1:])*row['markro'];params[path]=row[name];i+=1
            else:row[name]=take(path)
        rocks[rid]=row
    if not rocks: raise ValueError('No material records')
    i+=1;sections=[];section=[]
    for t in ts[i:]:
        if t[0]=='~': sections.append(section);section=[]
        else:section.append(t[0])
    if len(sections)!=3: raise ValueError('Expected boundary, material-box and temperature sections terminated by ~')
    boxes=[];a=sections[1]
    if len(a)%10: raise ValueError('Each material box needs type, rock ID and four coordinate pairs')
    for j in range(0,len(a),10):boxes.append(a[j:j+10])
    temps=[];a=sections[2];j=0
    while j<len(a):
        kind=int(number(a[j]));length=13+(4 if kind==8 else 3 if kind in {4,5,6,7} else 0)
        if j+length>len(a): raise ValueError('Incomplete temperature structure')
        temps.append(a[j:j+length]);j+=length
    return {'parameters':params,'positions':positions,'rocks':rocks,'boxes':boxes,'temperatures':temps,'boundaries':sections[0]}

def parse_mode(text):
    ts=tokens(text);cut=next((i for i,t in enumerate(ts) if t[0]=='~'),-1)
    if cut<2 or (cut-2)%6:raise ValueError('mode.t3c needs load file/type, save rows of six tokens and ~')
    params={};positions={};outputs=[]
    for j in range(2,cut,6):
        row=ts[j:j+6];outputs.append([t[0] for t in row])
        for name,t in zip(['name','type','cycles','maxxystep','maxtkstep','maxtmstep'],row):
            key=f'output/{len(outputs)-1}/{name}';params[key]=t[0] if name in {'name','type'} else number(t[0]);positions[key]=t[1:]
    for t in ts[cut+1:]:
        m=re.match(r'^([+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:e[+-]?\d+)?)-(.+)$',t[0],re.I)
        if not m:raise ValueError('General mode values must keep their source labels: '+t[0])
        key='mode/'+m[2];params[key]=number(m[1]);positions[key]=t[1:]
    return {'parameters':params,'positions':positions,'load':ts[0][0],'type':ts[1][0],'outputs':outputs}

def validate_files(init,mode):
    a=parse_init(init);b=parse_mode(mode);p=a['parameters'];errors=[]
    def check(ok,message):
        if not ok:errors.append(message)
    check(p['init/cartpolar'] in {1,2},'cartpolar must be 1 (Cartesian) or 2 (annulus)')
    check(5<=p['init/xnumx']<=2201 and 5<=p['init/ynumy']<=521,'Grid outside compiled limits (5..2201 by 5..521)')
    check(p['init/xsize']>0 and p['init/ysize']>0,'Domain sizes must be positive')
    check(1<=abs(p['init/mnumx'])<=20 and 1<=abs(p['init/mnumy'])<=20,'Markers per cell must be 1..20')
    check(p['init/output_type']=='h' and b['type']=='h','This runtime supports HDF5 output only')
    def safe_name(n):return bool(re.fullmatch(r'[A-Za-z0-9_.-]{1,40}',n)) and n not in {'.','..'}
    check(safe_name(p['init/output']) and safe_name(b['load']),'Use a simple relative checkpoint name')
    check(p['init/output']==b['load']+'.h5','Initial output must equal mode load name + .h5')
    check(len(b['outputs'])>0 and len(b['outputs'])<=3000,'At least one bounded save block is required')
    for row in b['outputs']:
        check(safe_name(row[0]) and row[1]=='h','Invalid save file name/type')
        check(1<=number(row[2])<=100000 and number(row[5])>0,'Save cycles and time step must be positive and bounded')
    for rid,r in a['rocks'].items():check(r['markro']>0 and r['markcp']>0 and r['markkt']>0,f'Material {rid}: density, heat capacity and conductivity must be positive')
    for row in a['boxes']:
        rid=int(number(row[1].lstrip('i')))%100;check(rid in a['rocks'],f'Undefined material {rid} in a box')
    return {'ok':not errors,'errors':errors,'parameters':{**a['parameters'],**b['parameters']},'revision':REVISION,'scope':'Input structure and compiled limits; physical equivalence requires separate evidence alignment.'}

def create(name,init,mode,provenance=None):
    check=validate_files(init,mode)
    if not check['ok']:raise ValueError('; '.join(check['errors']))
    ident=storage.uid();root=storage.DATA/'cases'/ident;root.mkdir(parents=True);(root/'assets').mkdir()
    (root/'init.t3c').write_text(init);(root/'mode.t3c').write_text(mode)
    storage.execute('INSERT INTO cases(id,name,path,created,provenance,engine) VALUES(?,?,?,?,?,?)',(ident,name,str(root),time.time(),json.dumps(provenance or {'revision':REVISION}), 'i2vis'))
    return {'case_id':ident,'name':name,'draft':str(root/'init.t3c'),'engine':'i2vis'}

def inspect(case_id):
    c=storage.get_case(case_id);root=Path(c['path']);a=(root/'init.t3c').read_text();b=(root/'mode.t3c').read_text()
    return {'case_id':case_id,'engine':'i2vis','files':{'init.t3c':a,'mode.t3c':b},**validate_files(a,b)}

def save(case_id,filename,text,revision=None):
    from .cases import _edit_lock,RevisionConflict
    if filename not in FILES:raise ValueError('Select init.t3c or mode.t3c')
    with _edit_lock:
        root=Path(storage.get_case(case_id)['path']);p=root/filename;before=p.read_text()
        if revision and hashlib.sha256(before.encode()).hexdigest()!=revision:raise RevisionConflict('Parameter file changed')
        # Allow editing an intermediate draft; the real run checks both files together.
        (parse_init if filename=='init.t3c' else parse_mode)(text)
        versions=root/'versions';versions.mkdir(exist_ok=True);(versions/f'{time.time_ns()}-{filename}').write_text(before)
        tmp=p.with_suffix('.tmp');tmp.write_text(text);tmp.replace(p)
        return {'case_id':case_id,'diff':''.join(difflib.unified_diff(before.splitlines(True),text.splitlines(True)))}

def modify(case_id,changes):
    info=inspect(case_id);prepared={}
    for filename,parser in [('init.t3c',parse_init),('mode.t3c',parse_mode)]:
        text=info['files'][filename];positions=parser(text)['positions'];edits=[]
        for path,value in changes.items():
            if path in positions:
                old=text[slice(*positions[path])];number(str(value));suffix=old[len(re.match(r'^[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?',old).group()):]
                edits.append((*positions[path],str(value)+suffix))
        for start,end,value in sorted(edits,reverse=True):text=text[:start]+value+text[end:]
        prepared[filename]=text
    if any(p not in info['parameters'] for p in changes):raise ValueError('Unknown exact I2VIS parameter path')
    check=validate_files(prepared['init.t3c'],prepared['mode.t3c'])
    if not check['ok']:raise ValueError('; '.join(check['errors']))
    diffs=[save(case_id,f,t)['diff'] for f,t in prepared.items()]
    return {'case_id':case_id,'diff':'\n'.join(diffs)}

def enqueue(case_id,cores=None,batch='',value=None,kind='simulation',timeout=None):
    info=inspect(case_id)
    if not info['ok']:raise ValueError('; '.join(info['errors']))
    cfg=storage.config();cores=int(cores or cfg['task_cores'])
    if not 1<=cores<=cfg['max_total_cores']:raise ValueError('Core budget exceeded')
    if not (runtime_root()/'bin/in2h5').is_file():raise ValueError('The I2VIS runtime is not installed')
    ident=storage.uid();root=storage.DATA/'runs'/ident;root.mkdir(parents=True);out=root/'output';out.mkdir();(root/'assets').mkdir()
    for f,t in info['files'].items():(out/f).write_text(t)
    for f in ('file.t3c','stop.yn'):(out/f).write_text('0\n' if f=='file.t3c' else 'n\n')
    shutil.copytree(Path(storage.get_case(case_id)['path'])/'assets',out,dirs_exist_ok=True)
    from . import physics
    identity=physics.snapshot(case_id,root)
    (root/'manifest.json').write_text(json.dumps({**identity,'engine':'i2vis','case_id':case_id,'job_id':ident,'cores':cores,'timeout_seconds':timeout or cfg['timeout_seconds'],'kind':kind,'source_revision':REVISION,'linear_solver':'SuiteSparse UMFPACK (portable PARDISO adapter)','output_directory':str(out)},indent=2))
    storage.execute('INSERT INTO jobs(id,case_id,batch,state,cores,created,value,kind) VALUES(?,?,?,?,?,?,?,?)',(ident,case_id,batch,'queued',cores,time.time(),json.dumps(value),kind))
    return {'job_id':ident,'state':'queued','output_directory':str(out),'input_snapshot':str(out/'init.t3c')}

def sweep(case_id,path,start,stop,count=5,sampling='log',cores=None,index=None):
    if index is not None:raise ValueError('Use an exact rock/<id>/<parameter> path instead of a list index')
    base=inspect(case_id)
    if path not in base['parameters']:raise ValueError('Unknown parameter path')
    if not 2<=count<=64 or sampling not in {'log','linear'} or not all(math.isfinite(x) for x in (start,stop)):raise ValueError('Invalid range')
    if sampling=='log' and min(start,stop)<=0:raise ValueError('Log sampling requires positive endpoints')
    cfg=storage.config();cores=int(cores or cfg['task_cores'])
    if not 1<=cores<=cfg['max_total_cores'] or not (runtime_root()/'bin/in2h5').is_file():raise ValueError('Runtime or core budget unavailable')
    batch=storage.uid();jobs=[]
    for i in range(count):
        f=i/(count-1);v=math.exp(math.log(start)*(1-f)+math.log(stop)*f) if sampling=='log' else start+(stop-start)*f
        c=create(f'sweep-{path}-{v:.5g}',base['files']['init.t3c'],base['files']['mode.t3c'],{'parent':case_id,'parameter':path,'value':v});modify(c['case_id'],{path:str(v)})
        jobs.append(enqueue(c['case_id'],cores,batch,{'path':path,'value':v}))
    return {'batch':batch,'jobs':jobs,'count':count}

def import_upload(name,content,case_id=None):
    if name.endswith('.t3c'):
        if Path(name).name not in FILES:raise ValueError('Upload init.t3c or mode.t3c')
        if case_id:
            save(case_id,Path(name).name,content.decode('utf-8-sig'));return {'case_id':case_id}
        template=templates('subduction');template[Path(name).name]=content.decode('utf-8-sig')
        return create(Path(name).stem,template['init.t3c'],template['mode.t3c'],{'upload':name,'companion':'Bundled subduction template; verify physics before running'})
    if not name.endswith('.zip'):raise ValueError('Upload a T3C file or a ZIP containing init.t3c and mode.t3c')
    with zipfile.ZipFile(io.BytesIO(content)) as z:
        if sum(i.file_size for i in z.infolist())>200_000_000:raise ValueError('Archive too large')
        selected={Path(i.filename).name:i for i in z.infolist() if Path(i.filename).name in FILES}
        if set(selected)!=FILES:raise ValueError('ZIP must contain init.t3c and mode.t3c')
        result=create(Path(name).stem,*[z.read(selected[f]).decode('utf-8-sig') for f in ('init.t3c','mode.t3c')],{'upload':name})
        from .cases import write_input_file
        for item in z.infolist():
            p=Path(item.filename)
            if p.suffix in {'.dat','.json','.txt','.csv'}:
                if p.is_absolute() or '..' in p.parts or stat.S_ISLNK(item.external_attr>>16):raise ValueError('Unsafe archive member')
                write_input_file(result['case_id'],p.name,z.read(item).decode())
        return result

def templates(name='subduction'):
    path=source_root()/'templates'/name
    if not path.is_dir():raise ValueError('Unknown bundled I2VIS template')
    return {f:(path/f).read_text() for f in FILES}
