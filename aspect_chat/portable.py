"""Container paths and a confined request queue for opening host folders."""
from functools import lru_cache
from pathlib import Path, PureWindowsPath
import os, re, subprocess, sys, json, time, tempfile, zipfile
from . import storage

def host_path(path):
    host=os.environ.get('ASPECT_CHAT_HOST_WORKSPACE')
    if not host: return str(path)
    try: relative=Path(path).resolve().relative_to(storage.DATA.resolve())
    except ValueError: return str(path)
    if re.match(r'^[A-Za-z]:[\\/]',host): return str(PureWindowsPath(host).joinpath(*relative.parts))
    return str(Path(host)/relative)

def input_path(path):
    host=os.environ.get('ASPECT_CHAT_HOST_WORKSPACE')
    if host:
        try:
            relative=PureWindowsPath(path).relative_to(PureWindowsPath(host)) if re.match(r'^[A-Za-z]:[\\/]',host) else Path(path).relative_to(Path(host))
        except ValueError: pass
        else:
            target=(storage.DATA/Path(*relative.parts)).resolve()
            if not target.is_relative_to(storage.DATA.resolve()): raise ValueError('Path escapes workspace')
            return str(target)
    return path

def present_paths(value):
    """Show host filenames to the chat without rewriting PRM text or logs."""
    if isinstance(value,list): return [present_paths(item) for item in value]
    if not isinstance(value,dict): return value
    return {key:host_path(item) if key in {'path','draft','output_directory','input_snapshot','csv'} and isinstance(item,str)
            else present_paths(item) for key,item in value.items()}

def folder_target(kind,identifier):
    if kind not in {'case','job'} or not re.fullmatch(r'[a-f0-9]{12}',identifier): raise ValueError('Invalid folder request')
    if kind=='case': target=Path(storage.get_case(identifier)['path'])
    else:
        if not storage.query('SELECT id FROM jobs WHERE id=?',(identifier,)): raise ValueError('Unknown job')
        target=storage.job_root(identifier)/'output'
    if not target.resolve().is_relative_to(storage.DATA.resolve()):raise ValueError('Folder escapes workspace')
    return target

def open_folder(kind,identifier):
    target=folder_target(kind,identifier)
    result={'path':host_path(target),'download_url':f'/api/archive?kind={kind}&id={identifier}'}
    if os.environ.get('ASPECT_CHAT_CONTAINER')=='1':
        queue=storage.DATA/'.host-open'; queue.mkdir(exist_ok=True)
        try:available=time.time()-json.loads((queue/'bridge.json').read_text())['time']<8
        except (OSError,ValueError,KeyError):available=False
        if not available:return {**result,'ok':False,'reason':'host_bridge_unavailable'}
        ident=storage.uid();request=queue/(ident+'.request')
        request.write_text(f'{kind}:{identifier}');return {**result,'ok':True,'queued':True,'request_id':ident}
    try:
        if sys.platform=='win32':os.startfile(str(target))
        else:subprocess.run(['open' if sys.platform=='darwin' else 'xdg-open',str(target)],check=True,timeout=5,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        return {**result,'ok':True,'queued':False}
    except (OSError,subprocess.SubprocessError):return {**result,'ok':False,'reason':'host_open_failed'}

def open_status(identifier):
    if not re.fullmatch(r'[a-f0-9]{12}',identifier):raise ValueError('Invalid folder request')
    p=storage.DATA/'.host-open'/(identifier+'.response')
    return json.loads(p.read_text()) if p.exists() else {'state':'pending'}

def archive(kind,identifier):
    target=folder_target(kind,identifier)
    if kind=='job':target=storage.job_root(identifier)
    name=target.name if kind=='job' else 'model'
    temporary=tempfile.SpooledTemporaryFile(max_size=8*1024*1024)
    try:
        with zipfile.ZipFile(temporary,'w',zipfile.ZIP_DEFLATED,allowZip64=True) as z:
            for p in sorted(target.rglob('*')):
                if p.is_file() and not p.is_symlink() and p.resolve().is_relative_to(target.resolve()):z.write(p,str(Path(name)/p.relative_to(target)))
        size=temporary.tell();temporary.seek(0);return temporary,size,name+'.zip'
    except Exception:temporary.close();raise

@lru_cache(maxsize=4)
def binary_version(binary):
    try:
        result=subprocess.run([binary,'--version'],capture_output=True,text=True,timeout=10)
        match=re.search(r'(?:\bversion\s+|\bASPECT\s+)(\d+\.\d+\.\d+(?:[-\w.]*))',result.stdout+' '+result.stderr,re.I)
        return match[1] if match else 'unknown'
    except (OSError,subprocess.TimeoutExpired): return 'unavailable'

def runtime():
    return {'version':os.environ.get('ASPECT_CHAT_VERSION') or binary_version(storage.config()['binary']),
            'packaged':os.environ.get('ASPECT_CHAT_CONTAINER')=='1'}
