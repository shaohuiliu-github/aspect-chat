"""Cached direct initial-field diagrams; no simulation jobs are created."""
from pathlib import Path
import hashlib,json,threading,time
from . import storage,cases,prm,initial_fields
FIELDS={'density':('density','kg/m³'),'viscosity':('viscosity','Pa·s'),'temperature':('temperature','K')}
_lock=threading.Lock()

def connect():
    c=storage.db();c.execute('CREATE TABLE IF NOT EXISTS initial_previews(case_id TEXT,signature TEXT,id TEXT,state TEXT,note TEXT,created REAL,PRIMARY KEY(case_id,signature))');c.commit();return c

def signature(case_id):
    case=storage.get_case(case_id);text=cases.draft(case_id)
    if case['engine']=='aspect':
        ignored={'End time','Start time','Output directory','Resume computation','Nonlinear solver scheme','Max nonlinear iterations','Nonlinear solver tolerance','CFL number','Maximum first time step','Maximum time step'}
        params={k:v for k,v in prm.values(text).items() if k not in ignored and not k.startswith(('Postprocess/','Solver parameters/','Termination criteria/','Checkpointing/'))}
        text=json.dumps(params,sort_keys=True)
    h=hashlib.sha256(b'direct-initial-v4-3d-central-slice'+case['engine'].encode()+text.encode())
    for p in sorted((Path(case['path'])/'assets').rglob('*')):
        if p.is_file() and not p.is_symlink() and p.suffix in {'.json','.dat','.txt','.csv','.wb'}:h.update(str(p.name).encode());h.update(p.read_bytes())
    return h.hexdigest()

def schedule(case_id):
    case=storage.get_case(case_id);sig=signature(case_id)
    with _lock,connect() as c:
        row=c.execute('SELECT id FROM initial_previews WHERE case_id=? AND signature=?',(case_id,sig)).fetchone()
        if row:return row['id']
        ident=storage.uid();c.execute('INSERT INTO initial_previews VALUES(?,?,?,?,?,?)',(case_id,sig,ident,'running','',time.time()))
    # Snapshot all inputs, so edits made during rendering cannot produce a mixed preview.
    import shutil
    root=storage.DATA/'previews'/ident;root.mkdir(parents=True)
    original=Path(case['path']);shutil.copytree(original/'assets',root/'assets')
    for filename in ('draft.prm','init.t3c','mode.t3c'):
        if (original/filename).exists():shutil.copy2(original/filename,root/filename)
    snapshot={**case,'path':str(root)}
    db_path=storage.DATA/'app.sqlite'
    def run():
        try:
            with _lock: initial_fields.render(snapshot,root/'initial-fields')
            state,note='succeeded',''
        except Exception as e:state,note='failed',str(e)
        import sqlite3
        with sqlite3.connect(db_path,timeout=30,factory=storage.Connection) as c:c.execute('UPDATE initial_previews SET state=?,note=? WHERE id=?',(state,note,ident))
    threading.Thread(target=run,daemon=True,name='initial-fields-'+ident).start();return ident

def latest(case_id):
    with connect() as c:
        row=c.execute('SELECT * FROM initial_previews WHERE case_id=? AND signature=?',(case_id,signature(case_id))).fetchone()
    if not row:return None
    r=dict(row);r['job_id']=r['id'];root=storage.DATA/'previews'/r['id']/'initial-fields';r['files']={k:str(root/(k+'.png')) for k in FIELDS if (root/(k+'.png')).exists()}
    if (root/'metadata.json').exists():r['metadata']=json.loads((root/'metadata.json').read_text())
    return r
