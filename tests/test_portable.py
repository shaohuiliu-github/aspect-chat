"""Portable knowledge and host folder behavior, without user credentials."""
import json,shutil,sqlite3,time,zipfile,importlib.util
from pathlib import Path
import pytest
from aspect_chat import cases,knowledge,portable,storage

@pytest.fixture
def isolated(tmp_path,monkeypatch):
    for module in (storage,cases,knowledge): monkeypatch.setattr(module,'DATA',tmp_path/'workspace')
    return tmp_path

def test_official_knowledge_is_relocatable_and_read_only(isolated,monkeypatch):
    kb=isolated/'build/knowledge';source=kb/'sources/official';source.mkdir(parents=True)
    (source/'model.prm').write_text('set Dimension = 2\n')
    monkeypatch.setenv('ASPECT_CHAT_KNOWLEDGE',str(kb))
    knowledge.register(source,'official-3.1.0','3.1.0')
    knowledge.add_runtime_parameters(json.dumps({'End time':{'documentation':'Final time','default_value':'1'}}),'3.1.0')
    moved=isolated/'recipient/knowledge';shutil.move(str(kb),str(moved))
    monkeypatch.setenv('ASPECT_CHAT_KNOWLEDGE',str(moved));monkeypatch.setenv('ASPECT_CHAT_KNOWLEDGE_READONLY','1')
    doc=knowledge.search('Dimension',kind='model')[0]
    assert Path(knowledge.read_document(doc['id'])['absolute_path']).is_relative_to(moved)
    case=cases.load_document(doc['id'])
    assert cases.draft(case['case_id'])=='set Dimension = 2\n'
    assert knowledge.parameter_info('End time')['source']=='ASPECT 3.1.0 runtime declarations'
    with knowledge.connect() as c:
        with pytest.raises(sqlite3.OperationalError): c.execute('DELETE FROM documents')

def test_folder_requests_cannot_open_arbitrary_host_paths(isolated,monkeypatch):
    monkeypatch.setenv('ASPECT_CHAT_CONTAINER','1');monkeypatch.setenv('ASPECT_CHAT_HOST_WORKSPACE','C:\\Users\\Researcher\\ASPECT Chat\\workspace')
    case=cases.create('example','set Dimension = 2\n')['case_id']
    queue=storage.DATA/'.host-open';queue.mkdir();(queue/'bridge.json').write_text(json.dumps({'time':time.time()}))
    result=portable.open_folder('case',case)
    assert result['path']==f'C:\\Users\\Researcher\\ASPECT Chat\\workspace\\cases\\{case}'
    requests=list((storage.DATA/'.host-open').glob('*.request'))
    assert len(requests)==1 and requests[0].read_text()==f'case:{case}'
    assert portable.input_path('C:\\Users\\Researcher\\ASPECT Chat\\workspace\\inputs\\model.prm')==str(storage.DATA/'inputs/model.prm')
    with pytest.raises(ValueError): portable.open_folder('case','../../outside')
    with pytest.raises(ValueError): portable.open_folder('job','a'*12)
    with pytest.raises(ValueError): portable.input_path('C:\\Users\\Researcher\\ASPECT Chat\\workspace\\..\\secret.prm')

def test_no_host_bridge_returns_useful_download_and_no_false_success(isolated,monkeypatch):
    monkeypatch.setenv('ASPECT_CHAT_CONTAINER','1')
    case=cases.create('files','set Dimension = 2\n')['case_id']
    result=portable.open_folder('case',case)
    assert not result['ok'] and result['download_url'].endswith(case)
    stream,_,name=portable.archive('case',case)
    with stream,zipfile.ZipFile(stream) as z:assert z.read('model/draft.prm')==b'set Dimension = 2\n'

def test_time_directories_do_not_collide_and_old_jobs_still_open(isolated):
    case=cases.create('times','set Dimension = 2\n')['case_id']
    a=cases.enqueue(case);b=cases.enqueue(case)
    assert a['name']!=b['name'] and a['name'][:13]==b['name'][:13]
    assert portable.folder_target('job',a['job_id'])==storage.job_root(a['job_id'])/'output'
    old='a'*12;storage.execute('INSERT INTO jobs(id,case_id,state) VALUES(?,?,?)',(old,case,'succeeded'))
    assert storage.job_root(old)==storage.DATA/'runs'/old

def test_host_bridge_acknowledges_time_folder_and_rejects_escape(isolated):
    spec=importlib.util.spec_from_file_location('host_bridge',Path('packaging/host_bridge.py'));bridge=importlib.util.module_from_spec(spec);spec.loader.exec_module(bridge)
    case=cases.create('safe','set Dimension = 2\n')['case_id'];job=cases.enqueue(case)
    root=storage.DATA.resolve();queue=root/'.host-open';queue.mkdir();request=queue/('b'*12+'.request');request.write_text('job:'+job['job_id'])
    opened=[];assert bridge.process(root,request,opened.append)['state']=='opened'
    assert opened==[storage.job_root(job['job_id'])/'output']
    request=queue/('c'*12+'.request');request.write_text('case:../../outside');assert bridge.process(root,request,opened.append)['state']=='failed'

def test_host_bridge_uses_manifests_without_opening_live_database(isolated,monkeypatch):
    spec=importlib.util.spec_from_file_location('host_bridge',Path('packaging/host_bridge.py'));bridge=importlib.util.module_from_spec(spec);spec.loader.exec_module(bridge)
    case=cases.create('safe','set Dimension = 2\n')['case_id'];job=cases.enqueue(case);root=storage.DATA.resolve()
    def forbidden(*args,**kwargs):raise AssertionError('Host must not open the container database')
    monkeypatch.setattr(sqlite3,'connect',forbidden)
    assert bridge.target_for(root,'case:'+case)==root/'cases'/case
    folder=next((root/'runs').glob('*'))
    assert bridge.target_for(root,'job:'+job['job_id'])==folder/'output'
    with pytest.raises(ValueError):bridge.target_for(root,'job:'+'a'*12)
    outside=isolated/'outside';outside.mkdir();(outside/'draft.prm').write_text('set Dimension = 2\n')
    (root/'cases'/('d'*12)).symlink_to(outside,target_is_directory=True)
    with pytest.raises(ValueError):bridge.target_for(root,'case:'+'d'*12)
    duplicate=root/'runs'/'20000101-0000';shutil.copytree(folder,duplicate)
    with pytest.raises(ValueError):bridge.target_for(root,'job:'+job['job_id'])

def test_database_context_commits_rolls_back_and_releases_connections(isolated,monkeypatch):
    with storage.db() as connection:
        connection.execute('INSERT INTO chats(role,content) VALUES(?,?)',('user','saved'))
    with pytest.raises(sqlite3.ProgrammingError):connection.execute('SELECT 1')
    with pytest.raises(RuntimeError):
        with storage.db() as failed:
            failed.execute('INSERT INTO chats(role,content) VALUES(?,?)',('user','discarded'))
            raise RuntimeError('cancel transaction')
    with pytest.raises(sqlite3.ProgrammingError):failed.execute('SELECT 1')
    assert [r['content'] for r in storage.query('SELECT content FROM chats')]==['saved']
    monkeypatch.setenv('ASPECT_CHAT_KNOWLEDGE',str(isolated/'knowledge'))
    with knowledge.connect() as index:index.execute('SELECT 1')
    with pytest.raises(sqlite3.ProgrammingError):index.execute('SELECT 1')

def test_container_defaults_do_not_require_author_computer(isolated,monkeypatch):
    monkeypatch.setenv('ASPECT_CHAT_BINARY','/opt/aspect/bin/aspect-release')
    monkeypatch.setenv('ASPECT_CHAT_SOURCE','/opt/chat/knowledge/sources/aspect-3.1.0')
    monkeypatch.setenv('ASPECT_CHAT_MPI','/usr/bin/mpirun')
    cfg=storage.config()
    assert cfg['binary']=='/opt/aspect/bin/aspect-release' and cfg['mpi']=='/usr/bin/mpirun'
    storage.save_config({'task_cores':2})
    assert storage.config()['task_cores']==2 and storage.config()['source_root']==cfg['source_root']


def test_chat_paths_are_host_readable_without_rewriting_model_text(isolated,monkeypatch):
    monkeypatch.setenv('ASPECT_CHAT_HOST_WORKSPACE','/computer/ASPECT Chat/workspace')
    inside=str(storage.DATA/'runs/abcd/output')
    result=portable.present_paths({'jobs':[{'output_directory':inside}], 'path':'Material model/Simple model/Viscosity',
                                   'text':'set Output directory = '+inside,'log':'Writing to '+inside})
    assert result['jobs'][0]['output_directory']=='/computer/ASPECT Chat/workspace/runs/abcd/output'
    assert result['path']=='Material model/Simple model/Viscosity'
    assert result['text'].endswith(inside) and result['log'].endswith(inside)
