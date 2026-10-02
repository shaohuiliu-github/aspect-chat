"""Container paths and a confined request queue for opening host folders."""
from functools import lru_cache
from pathlib import Path, PureWindowsPath
import os, re, subprocess, sys
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

def open_folder(kind,identifier):
    if kind not in {'case','job'} or not re.fullmatch(r'[a-f0-9]{12}',identifier): raise ValueError('Invalid folder request')
    if kind=='case': target=Path(storage.get_case(identifier)['path'])
    else:
        if not storage.query('SELECT id FROM jobs WHERE id=?',(identifier,)): raise ValueError('Unknown job')
        target=storage.DATA/'runs'/identifier/'output'
    if os.environ.get('ASPECT_CHAT_CONTAINER')=='1':
        if not target.resolve().is_relative_to(storage.DATA.resolve()): raise ValueError('Folder escapes workspace')
        queue=storage.DATA/'.host-open'; queue.mkdir(exist_ok=True)
        request=queue/(storage.uid()+'.request')
        request.write_text(f'{kind}:{identifier}'); return {'ok':True,'path':host_path(target)}
    subprocess.Popen(['open' if sys.platform=='darwin' else 'xdg-open',str(target)])
    return {'ok':True,'path':str(target)}

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
