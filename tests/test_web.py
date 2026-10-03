"""Behavior checks for preserved history, model files and the local UI API."""
import hashlib,json,threading,time
import httpx,pytest
from aspect_chat import agent,cases,knowledge,runner,sessions,storage,web

@pytest.fixture(autouse=True)
def isolated(tmp_path,monkeypatch):
    for module in (storage,cases,knowledge,runner): monkeypatch.setattr(module,'DATA',tmp_path)
    storage.save_config({'language':'zh','provider':'deepseek'})

@pytest.fixture
def client():
    server=web.ThreadingHTTPServer(('127.0.0.1',0),web.Handler)
    thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    with httpx.Client(base_url=f'http://127.0.0.1:{server.server_port}',headers={'X-ASPECT-Token':web.TOKEN},trust_env=False) as client:
        yield client
    server.shutdown();server.server_close();thread.join(2)

def test_migration_and_new_chat_preserve_previous_history():
    case=cases.create('original','set Dimension = 2\n')['case_id']
    storage.add_chat('user','原始对话','zh');storage.add_chat('assistant','Previous answer','zh')
    storage.add_chat('user','English history','en')
    sessions.migrate();sessions.migrate()
    assert len(sessions.list_all('zh'))==1 and len(sessions.list_all('en'))==1
    original=sessions.list_all('zh')[0]
    assert original['case_id']==case
    fresh=sessions.create('zh')
    assert storage.query('SELECT content FROM chats WHERE session_id=?',(fresh['id'],))==[]
    assert len(storage.query('SELECT * FROM chats'))==3
    assert cases.draft(case)=='set Dimension = 2\n'

def test_background_request_binds_generated_model_to_its_conversation(monkeypatch):
    a=sessions.create('zh');b=sessions.create('zh')
    case=cases.create('generated','set Dimension = 2\n')['case_id']
    monkeypatch.setattr(web.previews,'schedule',lambda _:None)
    seen=[]
    def fake(*args,session_id=None):
        seen.append((args[0],session_id))
        return {'text':'Only this chat','events':[{'tool':'create_model','result':{'case_id':case}}]}
    monkeypatch.setattr(agent,'chat',fake)
    request=sessions.start(a['id'],'Generate a model',[])
    for _ in range(100):
        if web.conversations.status(request)['state']!='working': break
        time.sleep(.01)
    assert seen==[('Generate a model',a['id'])]
    assert sessions.get(a['id'])['case_id']==case
    assert sessions.get(b['id'])['case_id'] is None
    assert storage.query('SELECT * FROM chats WHERE session_id=?',(b['id'],))==[]

def test_api_never_exposes_saved_key_and_rejects_foreign_mutation(client):
    storage.save_key('private-test-credential','deepseek')
    result=client.get('/api/bootstrap')
    assert result.status_code==200 and result.json()['connection']['ready']
    assert 'private-test-credential' not in result.text
    assert result.json()['text']['active_runs']=='{count} 个任务处理中'
    assert client.post('/api/new',json={'lang':'zh'},headers={'X-ASPECT-Token':'wrong'}).status_code==403
    assert client.post('/api/new',json={'lang':'zh'},headers={'Origin':'https://foreign.example'}).status_code==403
    assert sessions.list_all('zh')==[]

def test_stale_editor_cannot_overwrite_chat_changes(client,monkeypatch):
    case=cases.create('concurrency','set End time = 1\n')['case_id']
    old_hash=hashlib.sha256(cases.draft(case).encode()).hexdigest()
    cases.save_draft(case,'set End time = 2\n')
    reply=client.post('/api/save',json={'case_id':case,'revision':old_hash,'text':'set End time = 3\n'})
    assert reply.status_code==409 and cases.draft(case)=='set End time = 2\n'
    current_hash=hashlib.sha256(cases.draft(case).encode()).hexdigest()
    reply=client.post('/api/save',json={'case_id':case,'revision':current_hash,'text':'set End time = 4\n'})
    assert reply.status_code==200 and cases.draft(case)=='set End time = 4\n'

def test_new_chat_ui_upload_keeps_prm_on_disk_and_out_of_other_chats(client):
    import base64
    a=client.post('/api/new',json={'lang':'zh'}).json();b=client.post('/api/new',json={'lang':'zh'}).json()
    payload='set Dimension = 2\nset End time = 1\n'
    result=client.post('/api/upload',json={'session_id':a['id'],'name':'model.prm','content':base64.b64encode(payload.encode()).decode()})
    assert result.status_code==200
    case=result.json()['case_id']
    assert sessions.get(a['id'])['case_id']==case and sessions.get(b['id'])['case_id'] is None
    assert cases.draft(case)==payload

def test_concurrent_editor_saves_do_not_lose_one_another():
    case=cases.create('concurrent','set End time = 1\n')['case_id']
    revision=hashlib.sha256(cases.draft(case).encode()).hexdigest()
    outcomes=[];gate=threading.Barrier(2)
    def edit(value):
        gate.wait()
        try: cases.save_draft(case,f'set End time = {value}\n',expected_revision=revision)
        except cases.RevisionConflict: outcomes.append('conflict')
        else: outcomes.append('saved')
    threads=[threading.Thread(target=edit,args=(n,)) for n in (2,3)]
    for thread in threads: thread.start()
    for thread in threads: thread.join(2)
    assert sorted(outcomes)==['conflict','saved']
    assert cases.draft(case) in {'set End time = 2\n','set End time = 3\n'}

def test_agent_only_reads_history_of_selected_conversation(monkeypatch):
    a=sessions.create('zh');b=sessions.create('zh')
    storage.add_chat('user','History from A','zh',a['id'])
    storage.add_chat('user','Private history from B','zh',b['id'])
    payloads=[];client_class=httpx.Client
    def respond(request):
        payloads.append(json.loads(request.content))
        return httpx.Response(200,json={'choices':[{'message':{'role':'assistant','content':'Ready'}}]})
    monkeypatch.setattr(agent,'api_key',lambda *args:'test-key')
    monkeypatch.setattr(agent.httpx,'Client',lambda **kwargs:client_class(transport=httpx.MockTransport(respond)))
    assert agent.chat('Continue A',lang='zh',session_id=a['id'])['text']=='Ready'
    sent=json.dumps(payloads)
    assert 'History from A' in sent and 'Private history from B' not in sent


def test_published_container_port_preserves_host_and_origin_checks(client,monkeypatch):
    monkeypatch.setenv('ASPECT_CHAT_PUBLIC_PORT','8520')
    headers={'Host':'127.0.0.1:8520','Origin':'http://127.0.0.1:8520'}
    assert client.get('/api/health',headers=headers).status_code==200
    assert client.post('/api/new',json={'lang':'zh'},headers=headers).status_code==200
    assert client.get('/api/health',headers={'Host':'remote.example:8520'}).status_code==403
    assert client.post('/api/new',json={'lang':'zh'},headers={**headers,'Origin':'http://localhost:9999'}).status_code==403


def test_health_identifies_the_installation_for_portable_launchers(client,monkeypatch):
    monkeypatch.setenv('ASPECT_CHAT_INSTANCE','aspect-chat-test-installation')
    response=client.get('/api/health')
    assert response.status_code==200 and response.json()['instance']=='aspect-chat-test-installation'
