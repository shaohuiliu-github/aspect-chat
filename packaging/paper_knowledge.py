"""Index original factual paper notes; never copy a user's uploaded PDF."""
from pathlib import Path
import argparse,json,os,shutil,sys

APP=Path(__file__).resolve().parents[1]
def install(destination,source_dir=None):
    destination=Path(destination).resolve();destination.mkdir(parents=True,exist_ok=True)
    os.environ['ASPECT_CHAT_KNOWLEDGE']=str(destination)
    os.environ.pop('ASPECT_CHAT_KNOWLEDGE_READONLY',None)
    sys.path.insert(0,str(APP))
    from aspect_chat import knowledge
    results=[]
    for source in sorted(Path(source_dir or APP/'paper_knowledge').iterdir()):
        if not source.is_dir():continue
        record=json.loads((source/'record.json').read_text())
        target=destination/'papers'/source.name
        if target.is_symlink():raise ValueError('Paper source destination must not be a symlink')
        if target.exists():shutil.rmtree(target)
        shutil.copytree(source,target,dirs_exist_ok=True)
        results.append(knowledge.register(target,'paper-'+source.name,str(record['year']),record['source']['url'],role='reference',revision=record['source']['pdf_sha256'],default_kind='manual'))
    manifest_path=destination/'manifest.json'
    manifest=json.loads(manifest_path.read_text()) if manifest_path.exists() else {}
    with knowledge.connect() as c:
        manifest['sources']=[{'source':s['label'],'version':s['version'],'role':s['role'],'revision':s['revision'],'origin':s['origin'],
          'documents':c.execute('SELECT count(*) FROM documents WHERE source=?',(s['label'],)).fetchone()[0],
          'categories':{r['kind']:r['n'] for r in c.execute('SELECT kind,count(*) AS n FROM documents WHERE source=? GROUP BY kind',(s['label'],))}} for s in knowledge.sources()]
    manifest.update({'package_version':'2.0.3','knowledge':knowledge.summary(),'prepared_papers':{'sources':results,'full_pdfs_redistributed':False,'runtime_templates':False,'shared_between_solvers':True}})
    manifest_path.write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
    return manifest
if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('destination',type=Path)
    print(json.dumps(install(parser.parse_args().destination)['knowledge']))
