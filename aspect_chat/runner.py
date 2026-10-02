from pathlib import Path
import csv, json, os, re, signal, subprocess, time, sys
from .storage import DATA, config, execute, query

TERMINAL={'succeeded','failed','cancelled','interrupted'}

def tail(path,limit=18000):
    p=Path(path)
    if not p.exists(): return ''
    with p.open('rb') as f:
        f.seek(0,2); f.seek(max(0,f.tell()-limit)); return f.read().decode(errors='replace')

def status(job_id):
    rows=query('SELECT * FROM jobs WHERE id=?',(job_id,))
    if not rows: raise ValueError('Unknown job')
    row=rows[0]; root=DATA/'runs'/job_id; log=tail(root/'run.log')
    matches=list(re.finditer(r'Timestep\s+(\d+):\s*t=\s*([\deE+\-.]+)\s*(\w*)',log))
    row['progress']=({'timestep':int(matches[-1][1]),'simulation_time':matches[-1][2],
                      'unit':matches[-1][3]} if matches else {})
    row['output_directory']=str(root/'output'); row['log']=log
    row['validation_log']=tail(root/'validate.log',8000)
    row['elapsed_seconds']=round((row['ended'] or time.time())-row['started'],1) if row['started'] else 0
    return row

def statistics(job_id):
    p=DATA/'runs'/job_id/'output'/'statistics'
    if not p.exists(): return {'job_id':job_id,'available':False}
    columns={}; last=None
    with p.open() as f:
        for line in f:
            m=re.match(r'#\s*(\d+):\s*(.*)',line)
            if m: columns[int(m[1])-1]=m[2].strip()
            elif line.strip() and not line.startswith('#'):
                fields=line.strip().split(maxsplit=max(columns) if columns else -1)
                if columns and len(fields)<=max(columns): continue # skip partially written row
                parsed=[]
                for value in fields:
                    try: parsed.append(float(value))
                    except ValueError: parsed.append(value)
                last=parsed
    if last is None: return {'job_id':job_id,'available':False}
    return {'job_id':job_id,'available':True,'latest':{columns.get(i,f'column_{i+1}'):x for i,x in enumerate(last)}}

def export_batch(batch):
    rows=query('SELECT * FROM jobs WHERE batch=? ORDER BY created',(batch,)); result=[]
    for j in rows:
        parameter=json.loads(j['value'] or 'null') or {}
        data={'job_id':j['id'],'state':j['state'],**parameter}
        data.update(statistics(j['id']).get('latest',{})); result.append(data)
    path=DATA/'batches'/f'{batch}.csv'; path.parent.mkdir(exist_ok=True)
    columns=list(dict.fromkeys(k for row in result for k in row))
    with path.open('w',newline='') as f:
        writer=csv.DictWriter(f,columns); writer.writeheader(); writer.writerows(result)
    return {'batch':batch,'csv':str(path),'rows':result}

def validation(case_id,binary=None):
    from .cases import draft
    from .storage import get_case
    from . import diagnostics
    if get_case(case_id)['engine']=='i2vis':
        from .i2vis import inspect
        result=inspect(case_id);return diagnostics.save_check(case_id,{'ok':result['ok'],'log':'\n'.join(result['errors']),'scope':result['scope']})
    root=DATA/'checks'/case_id; root.mkdir(parents=True,exist_ok=True)
    p=root/'input.prm'; p.write_text(draft(case_id))
    from .storage import get_case
    cp=subprocess.run([binary or config()['binary'],'--validate',str(p)],
        cwd=Path(get_case(case_id)['path'])/'assets',stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=60)
    return diagnostics.save_check(case_id,{'ok':cp.returncode==0,'returncode':cp.returncode,'log':cp.stdout[-16000:],
            'scope':'Syntax and individual parameter patterns only; runtime/physics not certified.'})

def worker():
    import fcntl
    DATA.mkdir(parents=True,exist_ok=True)
    lock=(DATA/'worker.lock').open('w')
    try: fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    except BlockingIOError: raise SystemExit('A worker is already running')
    execute("UPDATE jobs SET state='interrupted',note='Worker restarted; prior process requires inspection',ended=? WHERE state IN ('validating','running')",(time.time(),))
    execute("UPDATE jobs SET state='cancelled',note='Replaced by direct initial-field evaluation' WHERE kind='preview' AND state='queued'")
    active={}; stopping=False
    def stop(*_):
        nonlocal stopping
        stopping=True
    signal.signal(signal.SIGTERM,stop); signal.signal(signal.SIGINT,stop)
    def finish(job_id,state,note,proc=None):
        if proc and proc.poll() is None:
            try: os.killpg(proc.pid,signal.SIGTERM); proc.wait(timeout=5)
            except subprocess.TimeoutExpired: os.killpg(proc.pid,signal.SIGKILL); proc.wait()
            except ProcessLookupError: pass
        execute('UPDATE jobs SET state=?,note=?,ended=? WHERE id=?',(state,note,time.time(),job_id))
    try:
        while not stopping:
            cfg=config()
            (DATA/'worker_heartbeat.json').write_text(json.dumps({'pid':os.getpid(),'time':time.time()}))
            for job_id,item in list(active.items()):
                p=item['proc']; rows=query('SELECT cancel FROM jobs WHERE id=?',(job_id,))
                if rows[0]['cancel']:
                    finish(job_id,'cancelled','Cancelled by user',p)
                elif time.time()-item['started']>item['timeout']:
                    finish(job_id,'failed','Wall time limit exceeded',p)
                elif p.poll() is None: continue
                elif item['stage']=='validating' and p.returncode==0:
                    try:
                        handle=(item['root']/'run.log').open('ab',buffering=0)
                        cmd=([sys.executable,'-m','aspect_chat.i2vis_runtime','solve',str(item['root'])] if item['engine']=='i2vis' else [item['binary'],str(item['root']/'input.prm')])
                        if item['engine']=='aspect' and item['cores']>1: cmd=[item['mpi'],'-np',str(item['cores'])]+cmd
                        item['handle'].close(); item['handle']=handle
                        item['proc']=subprocess.Popen(cmd,cwd=item['root']/'assets',stdin=subprocess.DEVNULL,
                            stdout=handle,stderr=subprocess.STDOUT,start_new_session=True,env=item['env'])
                        item['stage']='running'
                        execute("UPDATE jobs SET state='running',pid=? WHERE id=?",(item['proc'].pid,job_id))
                        continue
                    except Exception as e: finish(job_id,'failed',str(e))
                else:
                    success=item['stage']=='running' and p.returncode==0
                    note=f'{item["stage"]} exited {p.returncode}'
                    if success and item['kind']=='preview':
                        try:
                            from .previews import render
                            render(job_id)
                        except Exception as e: success=False; note='Initial preview: '+str(e)
                    finish(job_id,'succeeded' if success else 'failed',note)
                item['handle'].close(); del active[job_id]
            used=sum(x['cores'] for x in active.values())
            for job in query("SELECT * FROM jobs WHERE state='queued' AND cancel=0 ORDER BY created"):
                if used>=int(cfg['max_total_cores']): break
                if used+job['cores']>int(cfg['max_total_cores']): continue
                job_id=job['id']; root=DATA/'runs'/job_id
                with __import__('aspect_chat.storage',fromlist=['db']).db() as c:
                    updated=c.execute("UPDATE jobs SET state='validating',started=? WHERE id=? AND state='queued' AND cancel=0",(time.time(),job_id)).rowcount
                if not updated: continue
                handle=None
                try:
                    snapshot=json.loads((root/'manifest.json').read_text())
                    engine=snapshot.get('engine','aspect');env=os.environ.copy()
                    env['PYTHONPATH']=str(Path(__file__).resolve().parents[1]);env['OMP_NUM_THREADS']=str(job['cores']) if engine=='i2vis' else '1'
                    binary=str(Path(snapshot['binary']).expanduser().resolve()) if engine=='aspect' else ''
                    if engine=='aspect' and not Path(binary).is_file(): raise ValueError('ASPECT executable not found')
                    handle=(root/'validate.log').open('ab',buffering=0)
                    cmd=[sys.executable,'-m','aspect_chat.i2vis_runtime','initialize',str(root)] if engine=='i2vis' else [binary,'--validate',str(root/'input.prm')]
                    p=subprocess.Popen(cmd,cwd=root/'assets',env=env,
                        stdin=subprocess.DEVNULL,stdout=handle,stderr=subprocess.STDOUT,start_new_session=True)
                    active[job_id]={'proc':p,'stage':'validating','root':root,'handle':handle,'binary':binary,
                        'kind':job['kind'],'engine':engine,'env':env,
                        'mpi':snapshot.get('mpi',cfg['mpi']),'cores':job['cores'],'started':time.time(),'timeout':int(snapshot.get('timeout_seconds',cfg['timeout_seconds']))}
                    execute('UPDATE jobs SET pid=? WHERE id=?',(p.pid,job_id)); used+=job['cores']
                except Exception as e:
                    if handle: handle.close()
                    finish(job_id,'failed',str(e))
            time.sleep(0.5)
    finally:
        for job_id,item in active.items():
            finish(job_id,'interrupted','Worker stopped',item['proc']); item['handle'].close()
        (DATA/'worker_heartbeat.json').unlink(missing_ok=True)

if __name__=='__main__': worker()
