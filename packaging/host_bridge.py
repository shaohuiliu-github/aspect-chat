"""Optional file-manager bridge, confined to one workspace and known IDs."""
import argparse,json,os,re,subprocess,sys,time
from pathlib import Path

def target_for(workspace,value):
    workspace=workspace.resolve()
    match=re.fullmatch(r'(case|job):([a-f0-9]{12})',value)
    if not match:raise ValueError('Invalid request')
    kind,ident=match.groups()
    # A host and its Linux VM must not open the same live SQLite WAL database.
    # The runner writes immutable per-run manifests before queuing each task.
    if kind=='case':
        target=workspace/'cases'/ident
        resolved=target.resolve()
        if not resolved.is_relative_to(workspace):raise ValueError('Folder unavailable')
        if not any((resolved/name).is_file() for name in ('draft.prm','init.t3c')):raise ValueError('Unknown model')
    else:
        matches=[]
        for root in (workspace/'runs').glob('*'):
            if root.name!=ident and not re.fullmatch(r'\d{8}-\d{4}(?:-\d{2,})?',root.name):continue
            manifest=root/'manifest.json'
            if not root.resolve().is_relative_to(workspace) or manifest.is_symlink() or not manifest.is_file():continue
            try:record=json.loads(manifest.read_text())
            except (OSError,ValueError):continue
            if isinstance(record,dict) and record.get('job_id')==ident:matches.append(root/'output')
        if len(matches)!=1:raise ValueError('Unknown or ambiguous task')
        target=matches[0]
    target=target.resolve()
    if not target.is_relative_to(workspace) or not target.is_dir():raise ValueError('Folder unavailable')
    return target

def process(workspace,request,opener=None):
    queue=workspace/'.host-open';response=queue/(request.stem+'.response')
    try:
        if time.time()-request.stat().st_mtime>30:raise ValueError('Expired request')
        target=target_for(workspace,request.read_text().strip())
        if opener:opener(target)
        elif sys.platform=='win32':os.startfile(str(target))
        else:subprocess.run(['open' if sys.platform=='darwin' else 'xdg-open',str(target)],check=True,timeout=5,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        result={'state':'opened','time':time.time()}
    except Exception as e:result={'state':'failed','reason':str(e),'time':time.time()}
    response.write_text(json.dumps(result));request.unlink(missing_ok=True);return result

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--workspace',type=Path,required=True);args=parser.parse_args()
    workspace=args.workspace.expanduser().resolve();queue=workspace/'.host-open';queue.mkdir(parents=True,exist_ok=True)
    lock=(queue/'bridge.lock').open('a+b')
    if sys.platform!='win32':
        import fcntl
        try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:return
    while True:
        temporary=queue/'bridge.tmp';temporary.write_text(json.dumps({'time':time.time(),'platform':sys.platform}));temporary.replace(queue/'bridge.json')
        for request in queue.glob('*.request'):
            if re.fullmatch(r'[a-f0-9]{12}',request.stem):process(workspace,request)
        for response in queue.glob('*.response'):
            if time.time()-response.stat().st_mtime>86400:response.unlink(missing_ok=True)
        time.sleep(.5)

if __name__=='__main__':main()
