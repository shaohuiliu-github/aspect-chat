"""Build a clean context from explicitly public inputs, never from user data."""
from pathlib import Path
import argparse, json, shutil, sys

APP=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser();parser.add_argument('destination',type=Path)
parser.add_argument('--i2vis',type=Path,required=True);parser.add_argument('--parameters',type=Path);parser.add_argument('--extras',type=Path,required=True);parser.add_argument('--private-papers',type=Path);args=parser.parse_args()
dest=args.destination.resolve();dest.mkdir(parents=True,exist_ok=True)
if (dest/'app/paper_knowledge').exists():shutil.rmtree(dest/'app/paper_knowledge')
if (dest/'knowledge/papers').exists():shutil.rmtree(dest/'knowledge/papers')
for name in ('aspect_chat','web'):
    shutil.copytree(APP/name,dest/'app'/name,dirs_exist_ok=True,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
if args.private_papers:
    if not args.private_papers.resolve().is_dir():parser.error('Private papers directory does not exist')
    shutil.copytree(args.private_papers.resolve(),dest/'app/paper_knowledge',dirs_exist_ok=True)
for name in ('app.py','requirements.txt'):
    shutil.copy2(APP/name,dest/'app'/name)
shutil.copytree(APP/'packaging',dest/'packaging',dirs_exist_ok=True,ignore=shutil.ignore_patterns('__pycache__'))
kb=dest/'knowledge';kb.mkdir(exist_ok=True)
for database in kb.glob('knowledge.sqlite*'): database.unlink()
for source,target in ((APP/'data/sources/aspect-3.1.0',kb/'sources/aspect-3.1.0'),
                      (APP/'data/official-manual-3.1.0',kb/'official-manual-3.1.0')):
    shutil.copytree(source,target,dirs_exist_ok=True,ignore=shutil.ignore_patterns('.git','__pycache__','*.pyc'))
extra_sources=[
 ('official-api-3.1.0','3.1.0','https://aspect-documentation.readthedocs.io/en/v3.1.0/doxygen/','runtime','','code'),
 ('world-builder-runtime','1.1.1','https://github.com/GeodynamicWorldBuilder/WorldBuilder','runtime','','manual'),
 ('model-catalog','3.1.0','https://github.com/geodynamics/aspect/tree/v3.1.0','runtime','','manual'),
 ('aspect-main','3.2.0-pre','https://github.com/geodynamics/aspect/tree/982977e2070ab0b100ad58aa8213cb304948158e','reference','982977e2070ab0b100ad58aa8213cb304948158e',None),
 ('aspect-wiki','snapshot-2026-10-02','https://github.com/geodynamics/aspect/wiki','reference','9b4e08a8b977ece3b4ffe6dafc5fd5a1f2e607c3','manual')]
for label,*_ in extra_sources:
    shutil.copytree(args.extras/label,kb/label,dirs_exist_ok=True,ignore=shutil.ignore_patterns('.git','__pycache__','*.pyc'))
import os
os.environ['ASPECT_CHAT_KNOWLEDGE']=str(kb)
os.environ.pop('ASPECT_CHAT_KNOWLEDGE_READONLY',None)
sys.path.insert(0,str(APP))
from aspect_chat import knowledge
results=[knowledge.register(kb/'sources/aspect-3.1.0','official-3.1.0','3.1.0','https://github.com/geodynamics/aspect/tree/v3.1.0'),
         knowledge.register(kb/'official-manual-3.1.0','official-manual-3.1.0','3.1.0','https://aspect-documentation.readthedocs.io/en/v3.1.0/')]
if args.parameters: results.append(knowledge.add_runtime_parameters(args.parameters.read_text(),'3.1.0'))
for label,version,origin,role,revision,kind in extra_sources:
    results.append(knowledge.register(kb/label,label,version,origin,role=role,revision=revision,default_kind=kind))
with knowledge.connect() as c:
    indexed_prm=c.execute("SELECT count(*) FROM documents WHERE source='official-3.1.0' AND path LIKE '%.prm'").fetchone()[0]
prm_count=sum(1 for _ in (kb/'sources/aspect-3.1.0').rglob('*.prm'))
assert indexed_prm==prm_count,(indexed_prm,prm_count)
api_manifest=json.loads((kb/'official-api-3.1.0/fetch-manifest.json').read_text())
assert not api_manifest['failed'],'API crawl must complete before release'
manifest={'aspect_version':'3.1.0','base_image':'geodynamics/aspect:v3.1.0',
 'base_digest':'sha256:a3b599ac1d20d2a150f567a31d39591de18cf0c7e31fa9e9807d07dc291526c4',
 'knowledge':knowledge.summary(),'sources':results,'user_data_included':False,
 'coverage':{'official_prm_files':prm_count,'indexed_prm_files':indexed_prm,
             'runtime_parameter_entries':len(list((kb/'runtime-manual/entries').glob('*.md'))),
             'official_api_pages':len(api_manifest['pages']),'wiki_mode':'navigation records; article text not redistributed'},
 'retrieved':'2026-10-02','development_sources_require_explicit_selection':True}
(kb/'manifest.json').write_text(json.dumps(manifest,indent=2))
shutil.copytree(args.i2vis,kb/'i2vis-source',dirs_exist_ok=True,ignore=shutil.ignore_patterns('.git','._*','__pycache__'))
from aspect_chat import i2vis
import subprocess
subprocess.run([sys.executable,str(APP/'packaging/i2vis/templates.py'),str(kb/'i2vis-source')],check=True)
subprocess.run([sys.executable,str(APP/'packaging/i2vis/catalog.py'),str(kb/'i2vis-source'),str(kb/'i2vis-manual')],check=True,cwd=APP)
for label,root,kind in [('i2vis-source',kb/'i2vis-source','code'),('i2vis-templates',kb/'i2vis-source/templates','model'),('i2vis-manual',kb/'i2vis-manual','manual')]:
    results.append(knowledge.register(root,label,i2vis.REVISION,'supplied publicly authorized runtime',revision=i2vis.REVISION,default_kind=kind))
for label,url,revision in [('i2vis-public-i2elvis','https://github.com/FormingWorlds/i2elvis_planet','e2c8487015db5bfea80ec4c178f30bf6c32541c4'),('i2vis-public-dripping','https://github.com/YirenGou/Gou-and-Liu-2026-Dripping-Tectonics','65b9b4b4c26ae8b718f821b1c9dd0fc3642e3c63')]:
    if (args.extras/label).exists():
        shutil.copytree(args.extras/label,kb/label,dirs_exist_ok=True)
        results.append(knowledge.register(kb/label,label,'reference branch',url,role='reference',revision=revision,default_kind='manual'))
manifest.update({'package_version':'2.0.5','knowledge':knowledge.summary(),'sources':results,'i2vis':{'revision':i2vis.REVISION,'backend':'SuiteSparse UMFPACK portable PARDISO adapter','source_owner_permission':'user confirmed; documentary evidence pending'}})
(kb/'manifest.json').write_text(json.dumps(manifest,indent=2))
# Private paper facts are an opt-in local build input, never part of a public build.
(kb/'papers').mkdir(exist_ok=True)
if args.private_papers:
    from paper_knowledge import install
    manifest=install(kb,source_dir=dest/'app/paper_knowledge')
# All stored knowledge roots must survive a package relocation.
with knowledge.connect() as c:
    assert all(not Path(r[0]).is_absolute() for r in c.execute('SELECT root FROM sources'))
    c.execute('VACUUM')
print(json.dumps(manifest,indent=2))
