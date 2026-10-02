from pathlib import Path
import hashlib, json, os, re, shutil, sqlite3, time
from .storage import DATA

EXTENSIONS={'.prm','.md','.rst','.tex','.dox','.xml','.cc','.h','.wb',
            '.cpp','.hpp','.c','.f','.f90','.py','.sh','.cmake','.bib','.json','.ipynb','.grid','.txt','.t3c'}
SKIP={'build','.git','__pycache__','node_modules','output','outputs'}
CODE_EXTENSIONS={'.cc','.h','.cpp','.hpp','.c','.f','.f90','.py','.sh','.cmake'}

def directory():
    return Path(os.environ.get('ASPECT_CHAT_KNOWLEDGE',DATA)).resolve()

def source_root(root):
    path=Path(root)
    return path if path.is_absolute() else directory()/path

def connect():
    root=directory()
    if os.environ.get('ASPECT_CHAT_KNOWLEDGE_READONLY')=='1':
        c=sqlite3.connect((root/'knowledge.sqlite').as_uri()+'?mode=ro',uri=True,timeout=30)
        c.row_factory=sqlite3.Row
        c.execute('PRAGMA query_only=ON')
        return c
    root.mkdir(parents=True,exist_ok=True)
    c=sqlite3.connect(root/'knowledge.sqlite',timeout=30); c.row_factory=sqlite3.Row
    c.executescript('''
    CREATE TABLE IF NOT EXISTS sources(label TEXT PRIMARY KEY,root TEXT,version TEXT,origin TEXT,indexed REAL);
    CREATE TABLE IF NOT EXISTS documents(id INTEGER PRIMARY KEY,source TEXT,path TEXT,kind TEXT,sha256 TEXT,body TEXT);
    CREATE VIRTUAL TABLE IF NOT EXISTS chunks USING fts5(doc_id UNINDEXED,source UNINDEXED,path,body,tokenize='unicode61');
    ''')
    columns={r['name'] for r in c.execute('PRAGMA table_info(sources)')}
    for name,declaration in (('role',"TEXT NOT NULL DEFAULT 'runtime'"),('revision',"TEXT NOT NULL DEFAULT ''")):
        if name not in columns: c.execute(f'ALTER TABLE sources ADD COLUMN {name} {declaration}')
    return c

def register(root,label,version,origin='local',role='runtime',revision='',default_kind=None):
    if role not in {'runtime','reference'}: raise ValueError('Unknown knowledge source role')
    root=Path(root).expanduser().resolve()
    if not root.is_dir(): raise ValueError('Knowledge source must be an existing directory')
    count=0; counts={}
    with connect() as c:
        c.execute('DELETE FROM chunks WHERE source=?',(label,)); c.execute('DELETE FROM documents WHERE source=?',(label,))
        for p in sorted(root.rglob('*')):
            rel=p.relative_to(root)
            if p.is_symlink() or not p.is_file() or any(x in SKIP or x.startswith('output-') for x in rel.parts): continue
            if p.suffix.lower() not in EXTENSIONS or p.stat().st_size>5_000_000: continue
            # Include ASPECT's contribution tools, but not unrelated vendored Catch code.
            if 'catch' in rel.parts and 'contrib' in rel.parts: continue
            if label=='runtime-parameters' and p.name=='parameters.md' and (root/'entries').is_dir(): continue
            text=p.read_text(errors='replace')
            if p.suffix.lower()=='.ipynb':
                try:
                    notebook=json.loads(text)
                    text='\n\n'.join(''.join(cell.get('source',[])) for cell in notebook.get('cells',[]))
                except (ValueError,TypeError): continue
            # Tables remain available as input assets; index their headers and format, not megabytes of numbers.
            if p.suffix.lower() in {'.grid','.txt','.t3c'} and len(text)>24000:
                text=text[:12000]+'\n\n[Data excerpt only; full input file is bundled at '+str(rel)+']'
            if p.suffix=='.prm' and ('doc' in rel.parts or '.part.' in p.name): kind='fragment'
            elif p.suffix=='.prm': kind='test' if 'tests' in rel.parts else 'benchmark' if 'benchmarks' in rel.parts else 'model'
            elif p.suffix.lower() in CODE_EXTENSIONS: kind='code'
            elif 'tests' in rel.parts and p.suffix.lower() in {'.txt','.grid','.json'}: kind='test'
            else: kind=default_kind or 'manual'
            cur=c.execute('INSERT INTO documents(source,path,kind,sha256,body) VALUES(?,?,?,?,?)',
                (label,str(rel),kind,hashlib.sha256(p.read_bytes()).hexdigest(),text))
            doc_id=cur.lastrowid
            for start in range(0,len(text),6500):
                c.execute('INSERT INTO chunks(doc_id,source,path,body) VALUES(?,?,?,?)',
                    (doc_id,label,str(rel),text[start:start+7500]))
            count+=1; counts[kind]=counts.get(kind,0)+1
        stored=str(root.relative_to(directory())) if root.is_relative_to(directory()) else str(root)
        c.execute('INSERT OR REPLACE INTO sources(label,root,version,origin,indexed,role,revision) VALUES(?,?,?,?,?,?,?)',
                  (label,stored,version,origin,time.time(),role,revision))
    return {'source':label,'version':version,'role':role,'revision':revision,'documents':count,'categories':counts}

def sources():
    with connect() as c:
        rows=[dict(x) for x in c.execute('SELECT * FROM sources')]
    for row in rows: row['root']=str(source_root(row['root']))
    return rows

ALIASES={
 '黏度':['viscosity','rheology'],'粘度':['viscosity','rheology'],'密度':['density'],
 '温度':['temperature'],'初始':['initial'],'边界':['boundary'],'速度':['velocity'],
 '波速':['seismic','velocity','tomography'],'地震':['seismic','tomography'],
 '俯冲':['subduction'],'地幔':['mantle'],'对流':['convection'],'盒子':['box'],'箱体':['box'],
 '球壳':['spherical','shell'],'组分':['compositional'],'成分':['composition'],
 '网格':['mesh','refinement'],'重力':['gravity'],'板块':['plate'],
 '热膨胀':['thermal','expansivity'],'热导率':['thermal','conductivity'],
 '塑性':['plastic'],'蠕变':['creep'],'扩散':['diffusion'],'位错':['dislocation'],
 '应变率':['strain','rate'],'自由表面':['free','surface'],'世界构建器':['world','builder'],
 '几何':['geometry'],'压强':['pressure'],'压力':['pressure'],'年':['years'],
 '终止':['termination'],'输出':['output'],'函数':['function'],'扰动':['perturbation'],
 '检查点':['checkpoint'],'续算':['resume','checkpoint'],'熔融':['melt','melting'],
 '黏弹':['viscoelastic','visco','elastic'],'弹性':['elastic'],'地形':['topography'],
 '构建器':['world','builder'],'参数':['parameter'],'默认值':['default'],
 '脚本':['python','script'],'颗粒':['particle'],'粒子':['particle'],
}

def expanded_terms(query):
    terms=re.findall(r'[A-Za-z0-9_]+',query)
    for word,translations in ALIASES.items():
        if word in query: terms.extend(translations)
    stop={'the','a','an','of','to','and','i','my','want','please','model','set','some','how','with','from'}
    return list(dict.fromkeys(t.lower() for t in terms if t.lower() not in stop))[:30]

def search(query, limit=8, source=None, kind=None, engine=None):
    terms=expanded_terms(query)
    if not terms: return []
    # Escape input, never treat user text as an FTS query language expression.
    match=' OR '.join('"'+t.replace('"','""')+'"' for t in terms)
    sql='''SELECT d.id,d.source,d.path,d.kind,s.version,s.role,s.revision,substr(d.body,1,500) AS heading,
    snippet(chunks,3,'','',' … ',90) AS excerpt,
    bm25(chunks,0,0,5,1) AS score FROM chunks JOIN documents d ON d.id=chunks.doc_id
    JOIN sources s ON s.label=d.source
    WHERE chunks MATCH ?'''; args=[match]
    if source: sql+=' AND d.source=?'; args.append(source)
    if engine=='i2vis': sql+=" AND d.source LIKE 'i2vis%'"
    elif engine=='aspect': sql+=" AND d.source NOT LIKE 'i2vis%'"
    if not source: sql+=" AND s.role='runtime'"
    if kind: sql+=' AND d.kind=?'; args.append(kind)
    else: sql+=" AND d.kind NOT IN ('test','fragment','code')"
    sql+=' ORDER BY score LIMIT ?'; args.append(max(50,min(limit,20)*20))
    with connect() as c:
        rows=[dict(x) for x in c.execute(sql,args)]
        # FTS's limited candidate set can omit the exact parameter among many generic matches.
        if engine!='i2vis' and source in (None,'runtime-parameters') and kind in (None,'manual'):
            exact=c.execute('''SELECT d.id,d.source,d.path,d.kind,s.version,s.role,s.revision,
            substr(d.body,1,500) AS heading,substr(d.body,1,1500) AS excerpt,0 AS score
            FROM documents d JOIN sources s ON s.label=d.source
            WHERE d.source='runtime-parameters' AND
            substr(d.body,1,instr(d.body,char(10))-1)=? COLLATE NOCASE''',
            ('# Parameter: '+query.strip(),)).fetchall()
            rows=[dict(x) for x in exact]+rows
    # Reward coverage of distinct concepts; prefer current runtime and usable models.
    for r in rows:
        heading=r.pop('heading')
        r['title']=heading.splitlines()[0].removeprefix('# Parameter: ').removeprefix('# ').strip() if heading.startswith('# ') else r['path']
        content=(r['path']+' '+r['title']+' '+r['excerpt']).lower()
        coverage=sum(t in content for t in terms)/len(terms)
        r['_rank']=coverage*12-min(5,r['score'])
        r['_rank']+=.7 if r['source']=='local-runtime' else .4 if r['source']=='runtime-parameters' else 0
        r['_rank']+=.4 if r['kind']=='model' else 0
        if query.strip().lower() in {r['title'].lower(),r['path'].lower()}: r['_rank']+=20
    unique={}
    for r in sorted(rows,key=lambda x:x['_rank'],reverse=True): unique.setdefault((r['path'],r['kind']),r)
    selected=list(unique.values())[:max(1,min(limit,20))]
    for r in selected: r.pop('_rank',None)
    return selected

def summary():
    with connect() as c:
        return {'documents':c.execute('SELECT count(*) FROM documents').fetchone()[0],
            'models':c.execute("SELECT count(*) FROM documents d JOIN sources s ON s.label=d.source WHERE d.kind='model' AND s.role='runtime'").fetchone()[0],
            'sources':len(sources())}

def read_document(document_id):
    with connect() as c:
        r=c.execute('SELECT * FROM documents WHERE id=?',(document_id,)).fetchone()
        if not r: raise ValueError('Unknown knowledge document')
        d=dict(r)
        root=c.execute('SELECT root,version,role,revision,origin FROM sources WHERE label=?',(d['source'],)).fetchone()
        d['absolute_path']=str(source_root(root['root'])/d['path'])
        d.update({key:root[key] for key in ('version','role','revision','origin')})
        return d

def add_runtime_parameters(text,version):
    # Runtime declarations give exact defaults and accepted patterns for the installed binary.
    start=text.find('{'); end=text.rfind('}')
    if start<0: raise ValueError('No parameter JSON in ASPECT output')
    payload=json.loads(text[start:end+1])
    root=directory()/'runtime-manual'; root.mkdir(parents=True,exist_ok=True)
    (root/'parameters.md').write_text(json.dumps(payload,indent=2,ensure_ascii=False))
    entries=root/'entries'
    if entries.exists(): shutil.rmtree(entries)
    entries.mkdir()
    def emit(obj,prefix=''):
        for name,value in obj.items():
            if not isinstance(value,dict): continue
            path=prefix+'/'+name if prefix else name
            if 'documentation' not in value: emit(value,path); continue
            filename=hashlib.sha256(path.encode()).hexdigest()[:20]+'.md'
            body='# Parameter: '+path+'\n\nASPECT '+version+' runtime declarations.\n\n'
            for field in ('default_value','value','pattern','pattern_description','documentation'):
                if field in value: body+='## '+field+'\n'+str(value[field])+'\n\n'
            (entries/filename).write_text(body)
    emit(payload)
    return register(root,'runtime-parameters',version,'installed binary --output-json')


def parameter_info(path):
    p=directory()/'runtime-manual'/'parameters.md'
    if not p.exists(): raise ValueError('Runtime parameter export unavailable')
    obj=json.loads(p.read_text())
    for part in path.split('/'):
        if not isinstance(obj,dict) or part not in obj:
            import difflib
            available=list(obj) if isinstance(obj,dict) else []
            return {'path':path,'found':False,'similar_names':difflib.get_close_matches(part,available,n=8),'available_names':available[:80]}
        obj=obj[part]
    if not isinstance(obj,dict): raise ValueError('Invalid parameter path')
    if 'documentation' not in obj:
        def declarations(tree,prefix):
            result=[]
            for name,value in tree.items():
                if not isinstance(value,dict):continue
                p=prefix+'/'+name
                if 'documentation' in value:result.append({'path':p,'default':value.get('default_value'),'documentation':value['documentation'][:1500]})
                else:result.extend(declarations(value,p))
            return result
        return {'path':path,'subsection':True,'parameters':declarations(obj,path)}
    version=next((s['version'] for s in sources() if s['label']=='runtime-parameters'),'unknown')
    return {'path':path,'source':f'ASPECT {version} runtime declarations',**obj}
