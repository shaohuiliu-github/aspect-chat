from pathlib import Path
import json, os, shutil, sqlite3, time, uuid
import datetime, re
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
DATA = Path(os.environ.get('ASPECT_CHAT_DATA', ROOT / 'data')).resolve()

class Connection(sqlite3.Connection):
    """Commit/roll back transactions and release the file handle on exit."""
    def __exit__(self, *args):
        try:
            return super().__exit__(*args)
        finally:
            self.close()

def db():
    DATA.mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(DATA / 'app.sqlite', timeout=30, factory=Connection)
    c.row_factory = sqlite3.Row
    c.execute('PRAGMA journal_mode=WAL')
    c.execute('PRAGMA busy_timeout=30000')
    c.executescript('''
    CREATE TABLE IF NOT EXISTS cases(id TEXT PRIMARY KEY, name TEXT, path TEXT, created REAL, provenance TEXT);
    CREATE TABLE IF NOT EXISTS jobs(id TEXT PRIMARY KEY, case_id TEXT, batch TEXT, state TEXT, cores INTEGER,
    created REAL, started REAL, ended REAL, pid INTEGER, cancel INTEGER DEFAULT 0, note TEXT DEFAULT '', value TEXT);
    CREATE TABLE IF NOT EXISTS chats(id INTEGER PRIMARY KEY, role TEXT, content TEXT, created REAL);
    CREATE TABLE IF NOT EXISTS events(id INTEGER PRIMARY KEY, tool TEXT, input TEXT, output TEXT, created REAL);
    CREATE TABLE IF NOT EXISTS attachments(id TEXT PRIMARY KEY,name TEXT,kind TEXT,path TEXT,metadata TEXT,created REAL);
    CREATE TABLE IF NOT EXISTS previews(case_id TEXT,signature TEXT,job_id TEXT,created REAL,PRIMARY KEY(case_id,signature));
    CREATE TABLE IF NOT EXISTS requests(id TEXT PRIMARY KEY,state TEXT,lang TEXT,created REAL,pid INTEGER,event TEXT,result TEXT,error TEXT);
    CREATE TABLE IF NOT EXISTS chat_sessions(id TEXT PRIMARY KEY,title TEXT,lang TEXT,case_id TEXT,created REAL,updated REAL);
    ''')
    for table, column, definition in [('jobs','kind',"TEXT DEFAULT 'simulation'"),('chats','lang',"TEXT DEFAULT 'zh'"),
                                       ('chats','session_id','TEXT'),('requests','session_id','TEXT'),
                                       ('chats','attachments',"TEXT DEFAULT '[]'"),
                                       ('cases','engine',"TEXT DEFAULT 'aspect'"),
                                       ('chat_sessions','engine',"TEXT DEFAULT 'aspect'")]:
        if column not in {r[1] for r in c.execute('PRAGMA table_info('+table+')')}:
            c.execute(f'ALTER TABLE {table} ADD COLUMN {column} {definition}')
    if 'folder' not in {r[1] for r in c.execute('PRAGMA table_info(jobs)')}:
        c.execute('ALTER TABLE jobs ADD COLUMN folder TEXT')
    c.commit()
    return c

def query(sql, args=()):
    with db() as c:
        return [dict(r) for r in c.execute(sql, args).fetchall()]

def execute(sql, args=()):
    with db() as c:
        c.execute(sql, args)

def uid():
    return uuid.uuid4().hex[:12]

def new_run_directory():
    try: zone=ZoneInfo(config().get('timezone','UTC'))
    except (ValueError,KeyError): zone=datetime.timezone.utc
    stem=datetime.datetime.now(zone).strftime('%Y%m%d-%H%M')
    parent=DATA/'runs';parent.mkdir(parents=True,exist_ok=True)
    index=1
    while True:
        name=stem if index==1 else f'{stem}-{index:02d}'
        root=parent/name
        try:root.mkdir();return root
        except FileExistsError:index+=1

def job_root(identifier):
    if not re.fullmatch(r'[a-f0-9]{12}',identifier):raise ValueError('Invalid job ID')
    rows=query('SELECT folder FROM jobs WHERE id=?',(identifier,))
    if not rows:raise ValueError('Unknown job')
    name=rows[0]['folder'] or identifier
    if name!=identifier and not re.fullmatch(r'\d{8}-\d{4}(?:-\d{2,})?',name):raise ValueError('Invalid run directory')
    return DATA/'runs'/name

def config():
    p = DATA / 'config.json'
    local_source = Path.home() / 'aspect'
    local_binary = local_source / 'build' / 'aspect-release'
    binary=os.environ.get('ASPECT_CHAT_BINARY')
    if not binary:
        try: installed=local_binary.exists()
        except OSError: installed=False
        binary=str(local_binary) if installed else shutil.which('aspect-release') or shutil.which('aspect') or 'aspect'
    defaults = {'binary': binary,
                'source_root': os.environ.get('ASPECT_CHAT_SOURCE', str(local_source)),
                'mpi': os.environ.get('ASPECT_CHAT_MPI', shutil.which('mpirun') or 'mpirun'),
                'max_concurrent': 64, 'task_cores': 1, 'max_total_cores': min(8,os.cpu_count() or 1), 'timeout_seconds': 21600,
                'provider': 'deepseek', 'language': 'en', 'base_url': 'https://api.deepseek.com/v1', 'model': 'deepseek-flash'}
    if p.exists(): defaults.update(json.loads(p.read_text()))
    return defaults

def save_config(value):
    p = DATA / 'config.json'; DATA.mkdir(parents=True, exist_ok=True)
    merged=config(); merged.update(value)
    p.write_text(json.dumps(merged, ensure_ascii=False, indent=2)); p.chmod(0o600)

def api_key(provider=None):
    provider=provider or config()['provider']
    keys=DATA/'provider_keys.json'
    if keys.exists():
        value=json.loads(keys.read_text()).get(provider,'')
        if value: return value
    # A legacy key belongs only to the provider originally configured, never to another service.
    p=DATA/'api_key'
    legacy=DATA/'legacy_provider'
    owner=legacy.read_text().strip() if legacy.exists() else 'deepseek'
    if provider!=owner: return ''
    return os.environ.get('ASPECT_CHAT_API_KEY') or (p.read_text().strip() if p.exists() else '')

def save_key(value,provider=None):
    DATA.mkdir(parents=True, exist_ok=True); p=DATA/'provider_keys.json'
    keys=json.loads(p.read_text()) if p.exists() else {}
    keys[provider or config()['provider']]=value.strip()
    p.write_text(json.dumps(keys)); p.chmod(0o600)

def add_chat(role, content,lang=None,session_id=None,attachments=None):
    execute('INSERT INTO chats(role,content,created,lang,session_id,attachments) VALUES(?,?,?,?,?,?)',
            (role,content,time.time(),lang or config()['language'],session_id,json.dumps(attachments or [],ensure_ascii=False)))

def audit(tool, args, output):
    execute('INSERT INTO events(tool,input,output,created) VALUES(?,?,?,?)',
        (tool,json.dumps(args,ensure_ascii=False),json.dumps(output,ensure_ascii=False,default=str),time.time()))

def get_case(case_id):
    rows=query('SELECT * FROM cases WHERE id=?',(case_id,))
    if not rows: raise ValueError('Unknown case')
    return rows[0]
