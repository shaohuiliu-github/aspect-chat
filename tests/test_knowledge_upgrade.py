"""Knowledge completeness, runtime compatibility, and precise parameter retrieval."""
import json
import pytest
from aspect_chat import cases,knowledge,storage

@pytest.fixture
def isolated(tmp_path,monkeypatch):
    for module in (knowledge,storage,cases):monkeypatch.setattr(module,'DATA',tmp_path/'workspace')
    return tmp_path

def test_contribution_models_scripts_and_notebooks_are_indexed(isolated):
    root=isolated/'source/contrib/python';root.mkdir(parents=True)
    (root/'example.prm').write_text('set Dimension = 2\n')
    (root/'read_output.py').write_text('def read_statistics(): pass')
    (root/'tutorial.ipynb').write_text(json.dumps({'cells':[{'cell_type':'markdown','source':['Read ASPECT statistics']},{'cell_type':'code','source':['read_statistics()'],'outputs':[{'text':['do not index this saved output']}]}]}))
    knowledge.register(isolated/'source','official','3.1.0')
    assert knowledge.search('Dimension',kind='model')
    assert knowledge.search('read_statistics',kind='code')
    note=knowledge.search('statistics',kind='manual')[0]
    assert 'do not index' not in knowledge.read_document(note['id'])['body']

def test_parameters_have_separate_searchable_entries(isolated):
    payload={'Material model':{'Simple model':{'Viscosity':{'documentation':'Dynamic viscosity in Pa s','default_value':'1e21','pattern_description':'Double'}}},'End time':{'documentation':'Final simulation time','default_value':'1'}}
    result=knowledge.add_runtime_parameters(json.dumps(payload),'3.1.0')
    assert result['documents']==2
    hit=knowledge.search('Material model/Simple model/Viscosity')[0]
    assert hit['title']=='Material model/Simple model/Viscosity'
    assert '1e21' in knowledge.read_document(hit['id'])['body']
    assert knowledge.parameter_info(hit['title'])['default_value']=='1e21'
    noisy=isolated/'noisy';noisy.mkdir()
    for i in range(120):
        (noisy/f'{i}.md').write_text('# Generic parameter\nMaterial model Simple model Viscosity '*10)
    knowledge.register(noisy,'noisy','3.1.0')
    assert knowledge.search('material model/simple model/viscosity',limit=1)[0]['id']==hit['id']

def test_development_references_are_opt_in_and_cannot_load_as_runtime_models(isolated):
    stable=isolated/'stable';latest=isolated/'latest';stable.mkdir();latest.mkdir()
    for root in (stable,latest):(root/'convection.prm').write_text('set Dimension = 2\n# convection\n')
    knowledge.register(stable,'stable','3.1.0')
    knowledge.register(latest,'development','3.2.0-pre',role='reference',revision='fixed-commit')
    assert all(h['source']=='stable' for h in knowledge.search('convection',kind='model'))
    hit=knowledge.search('convection',source='development',kind='model')[0]
    assert hit['role']=='reference' and hit['revision']=='fixed-commit'
    with pytest.raises(ValueError,match='Reference-only'):cases.load_document(hit['id'])
