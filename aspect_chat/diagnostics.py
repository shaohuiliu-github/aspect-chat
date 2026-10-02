"""Concrete validation and execution failures, shown in the chat."""
from pathlib import Path
import difflib,hashlib,json,re,time
from . import storage,prm,knowledge,physics

def concise(log):
    log=str(log)
    m=re.search(r'Additional information:\s*(.*?)\n\s*Stacktrace:',log,re.S)
    if m:return ' '.join(m[1].split())[:1600]
    lines=log.splitlines();hits=[line for line in lines if re.search(r'error|exception|invalid|failed|unexpected|not found|nonfinite|space out',line,re.I)]
    return '\n'.join(hits[-6:])[:1600] or log[-1600:]

def known_parameters(case_id):
    c=storage.get_case(case_id)
    if c['engine']=='i2vis':
        from .i2vis import inspect
        return inspect(case_id)
    actual=prm.values((Path(c['path'])/'draft.prm').read_text());errors=[]
    for prefix in ('Initial temperature model','Initial composition model'):
        old=prefix+'/Model name'
        if old in actual and actual[old]!='unspecified':errors.append({'path':old,'code':'deprecated_parameter','message':'Deprecated in the installed ASPECT 3.1.0 runtime; set the old value to unspecified and use List of model names.','suggestions':[prefix+'/List of model names']})
    for prefix in ('Geometry model','Gravity model','Material model'):
        key=prefix+'/Model name'
        if actual.get(key,'unspecified')=='unspecified':errors.append({'path':key,'code':'missing_plugin','message':'This required plugin has not been selected','suggestions':[]})
    path=knowledge.directory()/'runtime-manual/parameters.md'
    if not path.exists():return {'ok':not errors,'available':False,'errors':errors}
    tree=json.loads(path.read_text());known=set()
    def walk(obj,prefix=''):
        for k,v in obj.items():
            if not isinstance(v,dict):continue
            p=prefix+'/'+k if prefix else k
            if 'documentation' in v:known.add(p)
            else:walk(v,p)
    walk(tree)
    for p in actual:
        if p not in known:
            hints=difflib.get_close_matches(p,known,n=3,cutoff=.55)
            errors.append({'path':p,'message':'Unknown parameter path','suggestions':hints})
    return {'ok':not errors,'available':True,'errors':errors}

def save_check(case_id,result):
    p=Path(storage.get_case(case_id)['path'])/'validation.json'
    result={**result,'input_revision':physics.revision(case_id),'created':time.time(),'summary':concise(result.get('log','')) if not result['ok'] else ''}
    p.write_text(json.dumps(result,indent=2,ensure_ascii=False));return result

def model_status(case_id):
    if not case_id:return None
    c=storage.get_case(case_id);p=Path(c['path'])/'validation.json';check=json.loads(p.read_text()) if p.exists() else None
    if check and check.get('input_revision')!=physics.revision(case_id):check=None
    static=known_parameters(case_id)
    errors=static.get('errors',[])
    # Legacy conversations may have an unsaved validation result from the earlier app.
    if not check:
        for r in storage.query("SELECT input,output FROM events WHERE tool='validate_case' ORDER BY id DESC LIMIT 100"):
            if json.loads(r['input']).get('case_id')==case_id:
                candidate=json.loads(r['output'])
                # Only surface a historical error if static checking still proves a current fault.
                if errors and candidate.get('ok') is False:check=candidate;check['summary']=concise(candidate.get('log',''))
                break
    runs=storage.query("SELECT j.id,j.case_id,j.state,j.created,j.cores,j.note FROM jobs j JOIN cases c ON c.id=j.case_id WHERE j.kind='simulation' AND (j.case_id=? OR json_extract(c.provenance,'$.parent')=?) ORDER BY j.created DESC LIMIT 8",(case_id,case_id))
    for r in runs:
        if r['state'] in {'failed','interrupted'}:
            from .runner import status
            s=status(r['id']);r['summary']=concise(s['log'] or s['validation_log'] or r['note'])
    return {'case_id':case_id,'name':c['name'],'engine':c['engine'],'validation':check,'parameter_errors':errors,'jobs':runs,'physics':physics.report(case_id)}
