import io, json, os, subprocess, sys, time, zipfile
from pathlib import Path
import pytest
from aspect_chat import cases, knowledge, prm, runner, storage

BASE='''set Dimension = 2
set End time = 0.1
subsection Material model
 subsection Simple model
  set Viscosity = 1 # keep comment
 end
end
'''

@pytest.fixture(autouse=True)
def isolated(tmp_path,monkeypatch):
    for module in (storage,cases,knowledge,runner): monkeypatch.setattr(module,'DATA',tmp_path)
    storage.save_config({'binary':sys.executable,'max_total_cores':4,'max_concurrent':1,'timeout_seconds':60})

def test_nested_duplicate_and_continuation():
    t=BASE+'subsection Material model\n subsection Simple model\n set Viscosity = 2\n end\nend\n'
    out=prm.patch(t,{'Material model/Simple model/Viscosity':'3'})
    assert all(e.value=='3' for e in prm.entries(out) if e.path.endswith('Viscosity'))
    assert '# keep comment' in out
    multi='subsection Function\n set Expression = x + \\\n y\nend\n'
    assert prm.values(multi)['Function/Expression']=='x + y'
    assert 'set Expression = z' in prm.patch(multi,{'Function/Expression':'z'})

def test_invalid_path_and_include_cycle(tmp_path):
    with pytest.raises(ValueError): prm.patch(BASE,{'Viscosity':'2'})
    with pytest.raises(ValueError): prm.patch(BASE,{'End time':'1\nset Dimension = 3'})
    a=tmp_path/'a.prm'; b=tmp_path/'b.prm'
    a.write_text('include b.prm'); b.write_text('include a.prm')
    with pytest.raises(ValueError,match='cycle'): prm.expand(a,[tmp_path])
    b.write_text('set Dimension = 2\n')
    assert 'set Dimension = 2' in prm.expand(a,[tmp_path])

def test_zip_traversal_and_missing_dependencies():
    buf=io.BytesIO()
    with zipfile.ZipFile(buf,'w') as z: z.writestr('../outside.prm',BASE)
    with pytest.raises(ValueError,match='Unsafe'): cases.import_upload('case.zip',buf.getvalue())
    with pytest.raises(ValueError): cases.import_upload('case.prm',b'include missing.prm\n')

def test_snapshots_and_log_sweep():
    base=cases.create('test',BASE)['case_id']
    scan=cases.sweep(base,'Material model/Simple model/Viscosity',1,100,3,'log')
    vals=[]
    for j in scan['jobs']:
        p=Path(j['input_snapshot']); vals.append(float(prm.values(p.read_text())['Material model/Simple model/Viscosity']))
        assert prm.values(p.read_text())['Output directory']==j['output_directory']
    assert vals==pytest.approx([1,10,100])
    cases.modify(base,{'End time':'0.2'})
    assert prm.values(Path(scan['jobs'][0]['input_snapshot']).read_text())['End time']=='0.1'
    assert len({j['output_directory'] for j in scan['jobs']})==3
    with pytest.raises(ValueError): cases.sweep(base,'Material model/Simple model/Viscosity',-1,100)

def test_list_component_guard():
    base=cases.create('list',BASE.replace('Viscosity = 1','Viscosity = 1,2,3'))['case_id']
    with pytest.raises(ValueError,match='component'): cases.sweep(base,'Material model/Simple model/Viscosity',1,10)
    s=cases.sweep(base,'Material model/Simple model/Viscosity',1,10,2,index=1)
    for j in s['jobs']:
        vals=prm.values(Path(j['input_snapshot']).read_text())['Material model/Simple model/Viscosity'].split(',')
        assert vals[0]=='1' and vals[2]=='3'

def test_kb_provenance_and_sql_escape(tmp_path):
    src=tmp_path/'src'; src.mkdir(); (src/'box.prm').write_text(BASE)
    assert knowledge.register(src,'v1','test')['documents']==1
    hits=knowledge.search('Viscosity')
    assert hits and knowledge.read_document(hits[0]['id'])['version']=='test'
    knowledge.search('" OR DROP TABLE documents;')

def test_cancel_queued_and_partial_statistics():
    case=cases.create('test',BASE)['case_id']; job=cases.enqueue(case)
    cases.cancel(job['job_id']); assert runner.status(job['job_id'])['state']=='cancelled'
    out=Path(job['output_directory']); (out/'statistics').write_text('# 1: Time\n# 2: RMS velocity\n0 3\n1')
    assert runner.statistics(job['job_id'])['latest']['RMS velocity']==3

def test_statistics_with_visualization_path_spaces():
    case=cases.create('test',BASE)['case_id']; job=cases.enqueue(case)
    (Path(job['output_directory'])/'statistics').write_text('# 1: Time\n# 2: RMS velocity\n# 3: Visualization file name\n0 3 /a folder/solution\n')
    stats=runner.statistics(job['job_id'])['latest']
    assert stats['RMS velocity']==3
    assert stats['Visualization file name']=='/a folder/solution'

def test_generated_asset_freeze_and_escape():
    case=cases.create('asset',BASE)['case_id']
    cases.write_input_file(case,'world.wb','{"version":"1.1","features":[]}')
    job=cases.enqueue(case)
    cases.write_input_file(case,'world.wb','{"version":"1.1","features":[{}]}')
    assert json.loads((Path(job['input_snapshot']).parent/'assets/world.wb').read_text())['features']==[]
    with pytest.raises(ValueError): cases.write_input_file(case,'../escape.txt','hello')
    with pytest.raises(ValueError): cases.write_input_file(case,'run.sh','echo hello')

def test_agent_tool_loop_without_live_provider(monkeypatch):
    from aspect_chat import agent
    import httpx
    case=cases.create('agent test',BASE)['case_id']
    responses=[{'role':'assistant','content':None,'tool_calls':[{'id':'c1','type':'function','function':{
        'name':'modify_parameters','arguments':json.dumps({'case_id':case,'changes':{'End time':'0.2'}})}}]},
        {'role':'assistant','content':None,'tool_calls':[{'id':'c2','type':'function','function':{
        'name':'submit_case','arguments':json.dumps({'case_id':case,'cores':1})}}]},
        {'role':'assistant','content':'已提交。'}]
    def handle(request):
        return httpx.Response(200,json={'choices':[{'message':responses.pop(0)}]})
    client_class=httpx.Client
    monkeypatch.setattr(agent,'api_key',lambda *args:'test-only-key')
    monkeypatch.setattr(agent.httpx,'Client',lambda **kw:client_class(transport=httpx.MockTransport(handle)))
    result=agent.chat('把 End time 改为 0.2 并运行',case)
    assert result['text']=='已提交。'
    job=storage.query('SELECT * FROM jobs')[0]
    assert job['state']=='queued'
    assert prm.values((storage.DATA/'runs'/job['id']/'input.prm').read_text())['End time']=='0.2'
