import base64,hashlib,json,time
from pathlib import Path
import numpy as np,pytest
from aspect_chat import cases,storage,knowledge,runner,sessions,web,agent,attachments,initial_fields,physics,i2vis,previews,diagnostics
from test_web import client

@pytest.fixture(autouse=True)
def isolated(tmp_path,monkeypatch):
    for module in (storage,cases,knowledge,runner):monkeypatch.setattr(module,'DATA',tmp_path)
    monkeypatch.setenv('CHATGFD_I2VIS_ROOT',str(Path('work/i2vis').resolve().parent/'not-installed'))

MODEL='''set Dimension = 2
subsection Geometry model
 set Model name = box
 subsection Box
  set X extent = 1000
  set Y extent = 500
 end
end
subsection Initial temperature model
 set Model name = function
 subsection Function
  set Function expression = 300+1300*(1-y/500)
 end
end
subsection Material model
 set Model name = simple
 subsection Simple model
  set Reference density = 3300
  set Thermal expansion coefficient = 0
  set Viscosity = 1e21
 end
end
'''

def test_safe_functions_and_direct_fields():
    x=np.array([0.,1.,2.]);assert np.allclose(initial_fields.evaluate('x<1 ? 2 : (x>1 ? 4 : 3)',{'x':x}),[2,3,4])
    assert np.allclose(initial_fields.evaluate('(x>=1 && x<2) ? 8 : 9',{'x':x}),[9,8,9])
    with pytest.raises(ValueError):initial_fields.evaluate('__import__("os").system("echo bad")',{})
    c=cases.create('direct',MODEL)['case_id'];x,y,f,e,n,invert=initial_fields.aspect(storage.get_case(c))
    assert not e and not invert and f['temperature'][0,0]==1600 and f['temperature'][-1,0]==300
    assert np.allclose(f['density'],3300) and np.allclose(f['viscosity'],1e21)
    assert storage.query('SELECT * FROM jobs')==[]

def test_i2vis_versioned_parser_and_edit():
    p=Path('tests/fixtures/i2vis/rayleigh_taylor');c=i2vis.create('rt',(p/'init.t3c').read_text(),(p/'mode.t3c').read_text())['case_id']
    before=i2vis.inspect(c);assert before['ok'] and before['parameters']['rock/3/markro']==3400
    i2vis.modify(c,{'rock/3/markro':'3500','mode/nubeg':'1e18'})
    now=i2vis.inspect(c);assert now['parameters']['rock/3/markro']==3500 and now['parameters']['mode/nubeg']==1e18
    assert storage.get_case(c)['engine']=='i2vis'
    a=sessions.create('en','aspect')
    with pytest.raises(ValueError):sessions.bind(a['id'],c)
    with pytest.raises(ValueError):agent.dispatch('inspect_case',{'case_id':c},engine='aspect')
    with pytest.raises(ValueError):i2vis.modify(c,{'init/xnumx':'99999'})
    unsafe=i2vis.validate_files(before['files']['init.t3c'].replace('initial.h5','../evil.h5'),before['files']['mode.t3c']);assert not unsafe['ok']


def test_sent_model_attachment_and_delete_preserve_files(client,monkeypatch):
    monkeypatch.setattr(agent,'chat',lambda *a,**k:{'text':'Saved','events':[]})
    monkeypatch.setattr(previews,'schedule',lambda _:None)
    s=client.post('/api/new',json={'lang':'en'}).json();up=client.post('/api/upload',json={'session_id':s['id'],'name':'input.prm','content':base64.b64encode(MODEL.encode()).decode()}).json()
    assert up['case_id'] and up['id']
    r=client.post('/api/chat',json={'session_id':s['id'],'prompt':'Inspect the upload','attachments':[up['id']]}).json()
    for _ in range(100):
        c=client.get('/api/conversation?id='+s['id']).json()
        if c['request']['state']!='working':break
        time.sleep(.01)
    assert c['messages'][0]['attachments'][0]['name']=='input.prm'
    assert client.post('/api/delete-chat',json={'id':s['id']}).status_code==200
    assert cases.draft(up['case_id'])==MODEL and storage.query('SELECT * FROM chats')==[]


def test_manual_run_is_independent_of_api_key(client):
    c=cases.create('manual',MODEL)['case_id'];r=client.post('/api/run',json={'case_id':c})
    assert r.status_code==200 and r.json()['state']=='queued' and not storage.api_key()
    s=sessions.create('en');sessions.bind(s['id'],c)
    result=client.get('/api/conversation?id='+s['id']).json()
    assert result['model_status']['jobs'][0]['id']==r.json()['job_id']


def test_density_is_actually_coupled_to_simple_material():
    c=cases.create('tomography',MODEL)['case_id']
    density='# POINTS: 2 2\n# x y density\n0 0 3300\n1000 0 3400\n0 500 3300\n1000 500 3400\n'
    composition=density.replace('3300','0').replace('3400','1')
    cases.write_input_file(c,'image-density.dat',density);cases.write_input_file(c,'image-composition.dat',composition)
    cases.write_input_file(c,'image-calibration.json',json.dumps({'density_min':3300,'density_max':3400}))
    assert attachments.couple(c,'reference_composition')['applied']
    _,_,fields,errors,_,_=initial_fields.aspect(storage.get_case(c))
    assert not errors and np.allclose(fields['density'][:,0],3300) and np.allclose(fields['density'][:,-1],3400)


def test_alignment_requires_evidence_and_marks_edits_stale():
    import pymupdf
    doc=pymupdf.open();page=doc.new_page();page.insert_text((40,40),'Reference density is 3300 kg/m3.');content=doc.tobytes();doc.close()
    a=attachments.ingest('paper.pdf',content)['id'];c=cases.create('paper',MODEL)['case_id']
    row={'category':'density','parameter':'reference density','status':'paper','source_value':3300,'source_unit':'kg/m3','page':1,'quote':'Reference density is 3300 kg/m3.','attachment_id':a,'path':'Material model/Simple model/Reference density','written_value':'3300'}
    r=physics.record(c,[row],[{'category':'rheology','parameter':'flow law','reason':'not in paper'}]);assert r['state']=='needs_review' and not r['stale']
    with pytest.raises(ValueError):physics.record(c,[{**row,'quote':'Density is 9999'}],[])
    with pytest.raises(ValueError):physics.record(c,[{**row,'written_value':'3400'}],[])
    cases.modify(c,{'Material model/Simple model/Reference density':'3400'});assert physics.report(c)['stale']


def test_padded_pdf_text_does_not_hide_parameters():
    assert attachments.clean_text('   '*8000+'Table 1   Density   3300\n  kg/m3')=='Table 1 Density 3300\nkg/m3'


def test_current_initial_plugin_and_early_diagnostics():
    current=MODEL.replace('subsection Initial temperature model\n set Model name = function','subsection Initial temperature model\n set List of model names = function')
    c=cases.create('current-api',current)['case_id']
    assert not initial_fields.aspect(storage.get_case(c))[3]
    errors=diagnostics.known_parameters(c)['errors'];assert any(e.get('code')=='missing_plugin' and e['path']=='Gravity model/Model name' for e in errors)
    old=cases.create('old-api',MODEL)['case_id'];assert any(e.get('code')=='deprecated_parameter' for e in diagnostics.known_parameters(old)['errors'])


def test_i2vis_density_preview_preserves_other_materials():
    p=Path('tests/fixtures/i2vis/rayleigh_taylor');c=i2vis.create('coupling', (p/'init.t3c').read_text(), (p/'mode.t3c').read_text())['case_id']
    before=initial_fields.i2vis(storage.get_case(c))[2]['density'].copy()
    cases.write_input_file(c,'image-density.dat','# POINTS: 2 2\n0 0 3250\n1000000 0 3250\n0 500000 3250\n1000000 500000 3250\n')
    cases.write_input_file(c,'image-calibration.json','{"density_min":3250,"density_max":3250}')
    attachments.couple(c,'thermal_anomaly',material_id=2)
    after=initial_fields.i2vis(storage.get_case(c))[2]['density']
    assert np.allclose(after[0],before[0]) and np.allclose(after[-1],3250)
    assert storage.query('SELECT * FROM jobs')==[]
