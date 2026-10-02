import io,json,time
from pathlib import Path
import httpx,numpy as np,pytest,pymupdf
from PIL import Image
from aspect_chat import attachments,cases,knowledge,previews,providers,prm,storage

BASE='set Dimension = 2\nset End time = 1\n'
@pytest.fixture(autouse=True)
def isolated(tmp_path,monkeypatch):
    for mod in (storage,cases,knowledge): monkeypatch.setattr(mod,'DATA',tmp_path)
    storage.save_config({'task_cores':2,'max_total_cores':4,'max_concurrent':64,'timeout_seconds':60,'provider':'deepseek'})


def test_provider_scoped_keys_and_defaults():
    storage.save_key('deepseek-secret','deepseek')
    providers.select('claude')
    assert storage.api_key()=='', 'Provider change must never carry a key to another host'
    storage.save_key('claude-secret','claude')
    assert storage.api_key('deepseek')=='deepseek-secret'
    assert providers.current()['protocol']=='claude'
    assert providers.current()['url']=='https://api.anthropic.com/v1'
    case=cases.create('cores',BASE)['case_id'];job=cases.enqueue(case)
    assert storage.query('SELECT cores FROM jobs')[0]['cores']==2
    storage.save_config({'language':'en'})
    assert storage.config()['task_cores']==2 and storage.config()['provider']=='claude'


def test_claude_images_and_tool_results():
    messages=[{'role':'system','content':'English only'},
        {'role':'user','content':[{'type':'text','text':'Map'},{'type':'image_url','image_url':{'url':'data:image/png;base64,YQ=='}}]},
        {'role':'assistant','content':'','tool_calls':[{'id':'t1','function':{'name':'inspect_case','arguments':'{"case_id":"c"}'}}]},
        {'role':'tool','tool_call_id':'t1','content':'{}'}, {'role':'tool','tool_call_id':'t2','content':'{}'}]
    payload=providers.claude_payload(messages,[],'claude-sonnet-5-5')
    assert payload['messages'][0]['content'][1]['source']['media_type']=='image/png'
    assert payload['messages'][1]['content'][0]['type']=='tool_use'
    assert len(payload['messages'][2]['content'])==2
    assert payload['system']=='English only'


def test_provider_adapters_and_redaction():
    seen=[]
    def handle(request):
        seen.append((str(request.url),json.loads(request.content)))
        if request.url.path.endswith('/messages'):
            return httpx.Response(200,json={'content':[{'type':'text','text':'Ready'},{'type':'tool_use','id':'t','name':'list_cases','input':{}}]})
        return httpx.Response(200,json={'choices':[{'message':{'role':'assistant','content':'OK'}}]})
    with httpx.Client(transport=httpx.MockTransport(handle)) as client:
        info={'id':'claude','protocol':'claude','url':'https://mock/v1','model':'test'}
        result=providers.complete(client,info,'secret',[{'role':'user','content':'Hello'}],[])
        assert result['tool_calls'][0]['function']['name']=='list_cases'
        info.update(id='openai',protocol='openai')
        assert providers.complete(client,info,'secret',[{'role':'user','content':'Hello'}],[])['content']=='OK'
    assert seen[0][0].endswith('/messages') and seen[1][0].endswith('/chat/completions')
    with pytest.raises(ValueError,match=r'\[REDACTED\]'):
        providers.check(httpx.Response(401,text='bad key secret'),'secret')


def test_pdf_pages_and_scanned_fallback():
    doc=pymupdf.open();p=doc.new_page();p.insert_text((50,50),'Model viscosity = 1e21 Pa s. Thermal diffusivity = 1e-6 m2/s.');doc.new_page()
    payload=doc.tobytes();doc.close()
    item=attachments.ingest('paper.pdf',payload)
    assert item['metadata']['pages']==2 and item['metadata']['text_pages']==1
    passage=attachments.read(item['id'],pages=[1,2])
    assert '1e21' in passage['passages'][0]['text'] and passage['scanned_pages']==[2]
    assert attachments.image_part(item['id'],2)['image_url']['url'].startswith('data:image/png;base64,')
    assert attachments.ingest('copy.pdf',payload)['id']==item['id']
    with pytest.raises(ValueError): attachments.read(item['id'],pages=[3])


def test_pdf_page_batch_replies_to_every_tool_before_sending_image(monkeypatch):
    from aspect_chat import agent
    doc=pymupdf.open(); page=doc.new_page(); page.insert_text((50,50),'Model setup')
    item=attachments.ingest('paper.pdf',doc.tobytes()); doc.close()
    storage.save_config({'provider':'deepseek','model':'deepseek-flash'})
    monkeypatch.setattr(agent,'api_key',lambda *args:'test-only-key')
    calls=[{'id':'page','type':'function','function':{'name':'view_attachment',
            'arguments':json.dumps({'attachment_id':item['id'],'page':1})}},
           {'id':'cases','type':'function','function':{'name':'list_cases','arguments':'{}'}}]
    requests=[]
    def respond(request):
        payload=json.loads(request.content); requests.append(payload)
        if len(requests)==1:
            return httpx.Response(200,json={'choices':[{'message':{'role':'assistant','content':None,'tool_calls':calls}}]})
        trailing=payload['messages'][-4:]
        assert [m['role'] for m in trailing]==['assistant','tool','tool','user']
        assert [m['tool_call_id'] for m in trailing[1:3]]==['page','cases']
        assert trailing[-1]['content'][1]['image_url']['url'].startswith('data:image/png;base64,')
        return httpx.Response(200,json={'choices':[{'message':{'role':'assistant','content':'PDF page received'}}]})
    client_class=httpx.Client
    monkeypatch.setattr(agent.httpx,'Client',lambda **kw:client_class(transport=httpx.MockTransport(respond)))
    assert agent.chat('Read this PDF',attachment_ids=[item['id']])['text']=='PDF page received'


def calibrated_map():
    palette=np.column_stack((np.linspace(0,255,32),np.zeros(32),np.linspace(255,0,32))).astype('uint8')
    image=np.zeros((32,40,3),dtype='uint8');image[:,:32]=palette[:,None,:];image[:,34:38]=palette[:,None,:]
    buf=io.BytesIO();Image.fromarray(image).save(buf,format='PNG')
    return buf.getvalue()


def test_image_calibration_units_orientation_and_data():
    item=attachments.ingest('velocity.png',calibrated_map());case=cases.create('map',BASE)['case_id']
    args=dict(attachment_id=item['id'],case_id=case,plot_box=[0,0,32,32],colorbar_box=[34,0,38,32],
        legend_start=-5,legend_end=5,extent=[0,1e6,0,6e5],rho0=3300,velocity_scale=.3,nx=32,ny=32,tolerance=5)
    result=attachments.digitize(**args)
    assert result['density_min']==pytest.approx(3250.5)
    assert result['density_max']==pytest.approx(3349.5)
    assets=Path(storage.get_case(case)['path'])/'assets'
    data=np.loadtxt(assets/'image-density.dat')
    assert data[0,2]==pytest.approx(3349.5) # bottom corresponds to bottom legend endpoint
    assert data[-1,2]==pytest.approx(3250.5)
    assert np.all(np.diff(data[:32,0])>0)
    proxy=np.loadtxt(assets/'image-composition.dat')
    assert proxy[:,2].min()==0 and proxy[:,2].max()==1
    assert (assets/'image-density.png').exists()
    assert cases.draft(case)==BASE, 'Digitization does not silently alter rheology or boundary conditions'
    with pytest.raises(ValueError,match='reference velocity'):
        attachments.digitize(**{**args,'quantity':'velocity'})
    with pytest.raises(ValueError,match='Crop'):
        attachments.digitize(**{**args,'plot_box':[-1,0,32,32]})


def test_preview_cache_and_snapshot():
    case=cases.create('preview',BASE)['case_id']
    first=previews.schedule(case);assert previews.schedule(case)==first
    snapshot=(storage.DATA/'runs'/first/'input.prm').read_text()
    assert prm.values(snapshot)['End time']=='0'
    assert prm.values(snapshot)['Nonlinear solver scheme']=='no Advection, no Stokes'
    assert cases.draft(case)==BASE
    assert storage.query('SELECT kind FROM jobs')[0]['kind']=='preview'
    cases.modify(case,{'End time':'2'})
    assert previews.schedule(case)==first
    cases.modify(case,{'Initial temperature model/Function/Function expression':'1600'},allow_new=True)
    assert previews.schedule(case)!=first


def test_chinese_retrieval_and_source_version(tmp_path):
    src=tmp_path/'source';src.mkdir()
    (src/'initial_temperature_box.prm').write_text('set Initial temperature = 1\n# convection box temperature density viscosity')
    (src/'viscosity.prm').write_text('set Viscosity = 1\n')
    knowledge.register(src,'local-runtime','test-version')
    hit=knowledge.search('初始温度 对流 箱体')[0]
    assert 'temperature' in hit['path'] and hit['version']=='test-version'
    assert 'viscosity' in knowledge.expanded_terms('黏度')


def test_background_conversation_keeps_ui_free(monkeypatch):
    from aspect_chat import conversations,agent
    import threading
    gate=threading.Event()
    def fake(*args):
        gate.wait(3);return {'text':'Ready','events':[]}
    monkeypatch.setattr(agent,'chat',fake)
    request=conversations.start('Generate',None,[],'en')
    assert conversations.status(request)['state']=='working'
    # Other DB/job operations proceed while the API waits.
    case=cases.create('while waiting',BASE)['case_id'];cases.enqueue(case)
    gate.set()
    for _ in range(50):
        if conversations.status(request)['state']=='done':break
        time.sleep(.02)
    assert conversations.status(request)['state']=='done'
    assert storage.query('SELECT content FROM chats WHERE role=?',('assistant',))[0]['content']=='Ready'


def test_worker_uses_total_core_budget_not_legacy_task_limit(tmp_path):
    import os,subprocess,sys
    executable=tmp_path/'fake_aspect'
    executable.write_text('#!'+sys.executable+'\nimport sys,time\nif "--validate" not in sys.argv: time.sleep(2)\n')
    executable.chmod(0o755)
    storage.save_config({'binary':str(executable),'task_cores':1,'max_total_cores':2,'max_concurrent':1,'timeout_seconds':30})
    case=cases.create('scheduling',BASE)['case_id']
    for _ in range(3):cases.enqueue(case)
    proc=subprocess.Popen([sys.executable,'-m','aspect_chat.runner'],env={**os.environ,'ASPECT_CHAT_DATA':str(tmp_path)},stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    saw_two=False
    try:
        deadline=time.time()+12
        while time.time()<deadline:
            jobs=storage.query('SELECT state,cores FROM jobs')
            active=[j for j in jobs if j['state'] in {'running','validating'}]
            assert sum(j['cores'] for j in active)<=2
            if len(active)==2:saw_two=True
            if all(j['state']=='succeeded' for j in jobs):break
            time.sleep(.04)
        assert saw_two, 'Two one-core tasks should overlap even when the old max_concurrent setting is 1'
        assert all(j['state']=='succeeded' for j in jobs)
    finally:
        proc.terminate();proc.wait(timeout=10)
