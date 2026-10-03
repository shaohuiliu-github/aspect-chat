"""Path-aware PRM edits, with explicit include expansion and continuation support."""
from dataclasses import dataclass
from pathlib import Path
import re

@dataclass
class Entry:
    path: str
    value: str
    start: int
    stop: int
    indent: str

def entries(text):
    lines=text.splitlines(keepends=True); stack=[]; result=[]; i=0
    while i<len(lines):
        start=i; raw=lines[i]; logical=raw.split('#',1)[0].rstrip(); i+=1
        while logical.endswith('\\'):
            if i==len(lines): raise ValueError('Dangling continuation')
            logical=logical[:-1]+lines[i].split('#',1)[0].strip(); i+=1
        s=logical.strip()
        if not s: continue
        if s.startswith('subsection '): stack.append(s[11:].strip())
        elif s=='end':
            if not stack: raise ValueError('Unmatched end')
            stack.pop()
        elif s.startswith('set '):
            if '=' not in s: raise ValueError('set requires =')
            key,value=s[4:].split('=',1)
            result.append(Entry('/'.join(stack+[key.strip()]), value.strip(), start,i,
                                re.match(r'\s*',raw).group()))
        elif s.startswith('include '): raise ValueError('Expand includes before editing')
        else: raise ValueError(f'Unrecognized PRM statement: {s[:100]}')
    if stack: raise ValueError('Unclosed subsections')
    return result

def values(text):
    return {e.path:e.value for e in entries(text)}

def patch(text, changes, allow_new=False):
    lines=text.splitlines(keepends=True); parsed=entries(text); known={e.path for e in parsed}
    missing=set(changes)-known
    if missing and not allow_new: raise ValueError('Parameter path not found: '+', '.join(sorted(missing)))
    for path,value in changes.items():
        if not path or any(not p.strip() for p in path.split('/')): raise ValueError('Invalid parameter path')
        if any(c in path for c in '\n\r=') or any(c in str(value) for c in '\n\r'):
            raise ValueError('Multiline path/value rejected; use a complete draft for multiline expressions')
    # Repeated assignments have last-write semantics; edit ALL occurrences to avoid stale values.
    for e in reversed(parsed):
        if e.path in changes:
            comment=''
            if e.stop==e.start+1 and '#' in lines[e.start]: comment='  #'+lines[e.start].split('#',1)[1].rstrip()
            lines[e.start:e.stop]=[f'{e.indent}set {e.path.split("/")[-1]} = {changes[e.path]}{comment}\n']
    out=''.join(lines)
    for path in sorted(missing):
        parts=path.split('/'); out+='\n'; depth=0
        for section in parts[:-1]:
            out+='  '*depth+'subsection '+section+'\n'; depth+=1
        out+='  '*depth+f'set {parts[-1]} = {changes[path]}\n'
        for _ in parts[:-1]: depth-=1; out+='  '*depth+'end\n'
    entries(out)
    return out

def expand(path, allowed_roots, seen=None):
    path=Path(path).resolve(); seen=set() if seen is None else seen
    if not any(path.is_relative_to(Path(r).resolve()) for r in allowed_roots):
        raise ValueError(f'Include outside allowed roots: {path}')
    if path in seen: raise ValueError(f'Include cycle: {path}')
    seen.add(path); out=[]
    for line in path.read_text().splitlines(keepends=True):
        s=line.split('#',1)[0].strip()
        if s.startswith('include '):
            name=s[8:].strip().strip('"')
            if '$' in name: raise ValueError('Variable include paths must be resolved explicitly')
            out.append(f'# expanded include {name}\n')
            out.append(expand(path.parent/name,allowed_roots,seen)+'\n')
        else: out.append(line)
    seen.remove(path)
    return ''.join(out)
