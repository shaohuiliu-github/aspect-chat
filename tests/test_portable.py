"""Portable knowledge and host folder behavior, without user credentials."""
import json,shutil,sqlite3
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
    result=portable.open_folder('case',case)
    assert result['path']==f'C:\\Users\\Researcher\\ASPECT Chat\\workspace\\cases\\{case}'
    requests=list((storage.DATA/'.host-open').glob('*.request'))
    assert len(requests)==1 and requests[0].read_text()==f'case:{case}'
    assert portable.input_path('C:\\Users\\Researcher\\ASPECT Chat\\workspace\\inputs\\model.prm')==str(storage.DATA/'inputs/model.prm')
    with pytest.raises(ValueError): portable.open_folder('case','../../outside')
    with pytest.raises(ValueError): portable.open_folder('job','a'*12)
    with pytest.raises(ValueError): portable.input_path('C:\\Users\\Researcher\\ASPECT Chat\\workspace\\..\\secret.prm')

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
