"""Curated scanned-table provenance works without a vision API; previews stay independent."""
import hashlib,json
from pathlib import Path
import pymupdf,pytest
from aspect_chat import attachments,cases,initial_fields,knowledge,physics,storage,web
from test_chatgfd import MODEL

@pytest.fixture
def paper(tmp_path,monkeypatch):
    for module in (knowledge,cases,storage):monkeypatch.setattr(module,'DATA',tmp_path/'workspace')
    monkeypatch.setenv('ASPECT_CHAT_KNOWLEDGE',str(tmp_path/'knowledge'))
    doc=pymupdf.open();doc.new_page().insert_text((40,40),'Test model paper, DOI 10.1234/test');doc.new_page().insert_text((40,40),'Raster table caption only')
    content=doc.tobytes();doc.close();sha=hashlib.sha256(content).hexdigest()
    root=tmp_path/'knowledge/papers/test';root.mkdir(parents=True)
    source={'pdf_sha256':sha,'doi':'10.1234/test'}
    (root/'record.json').write_text(json.dumps({'source':source,'title':'Test paper','run_ready':False,'model_families':[{'solver':'other 3D code'}]}))
    (root/'facts.json').write_text(json.dumps({'schema':'chatgfd.paper-facts.v1','source':source,'facts':{'density':{'value':3300,'unit':'kg/m3','pdf_page':2,'category':'density'},'output':{'value':1,'unit':'Pa','pdf_page':2,'category':'diagnostic'}}}))
    (root/'overview.md').write_text('# Test paper density\nScanned table facts are physical reference, not a runnable model.')
    knowledge.register(root,'paper-test','test',role='reference',revision=sha)
    a=attachments.ingest('paper.pdf',content)
    ident=next(d['id'] for d in knowledge.match_paper(sha)['documents'] if d['path']=='facts.json')
    return a,ident,root,sha

def test_scanned_table_reference_available_to_both_solvers(paper):
    a,ident,root,sha=paper
    ref=attachments.read(a['id'],pages=[2])['prepared_reference']
    assert ref['exact_pdf_match'] and not ref['run_ready']
    assert all(knowledge.search('density',engine=engine) for engine in ('aspect','i2vis'))
    assert not knowledge.search('density',kind='model')
    with pytest.raises(ValueError,match='Reference-only'):cases.load_document(ident)
    alternate=knowledge.match_paper('different copy','DOI 10.1234/test')
    assert alternate and not alternate['exact_pdf_match']
    with pytest.raises(ValueError,match='exact PDF'):knowledge.prepared_fact(ident,'density','different copy')

def test_private_paper_source_is_not_listed_in_demo_settings(paper):
    assert any(s['label']=='paper-test' for s in knowledge.sources())
    assert not any(s['label']=='paper-test' for s in web.bootstrap('en')['sources'])

def test_prepared_alignment_checks_page_units_value_and_file(paper):
    a,ident,root,sha=paper;c=cases.create('paper',MODEL)['case_id']
    row={'category':'density','parameter':'reference density','status':'paper','source_value':3300,'source_unit':'kg/m3','attachment_id':a['id'],'page':2,'knowledge_document_id':ident,'fact_id':'density','path':'Material model/Simple model/Reference density','written_value':'3300'}
    result=physics.record(c,[row],[])
    assert result['rows'][0]['prepared_evidence']['document_sha256']
    assert result['rows'][0]['source_sha256']==sha
    for changes in ({'page':1},{'source_unit':'g/cm3'},{'source_value':3400},{'fact_id':'output'}):
        with pytest.raises(ValueError):physics.record(c,[{**row,**changes}],[])
    (root/'facts.json').write_text('{}')
    with pytest.raises(ValueError,match='changed since indexing'):knowledge.prepared_fact(ident,'density',sha)

def test_three_initial_maps_constant_viscosity_log_without_run(paper,tmp_path):
    c=cases.create('preview',MODEL)['case_id']
    metadata=initial_fields.render(storage.get_case(c),tmp_path/'preview')
    assert set(metadata['files'])=={'density','viscosity','temperature'}
    assert len(set(metadata['color_maps'].values()))==3
    assert metadata['scales']['viscosity']=='log'
    assert metadata['ranges']['viscosity']['min']==metadata['ranges']['viscosity']['max']==1e21
    assert all(Path(p).stat().st_size>1000 for p in metadata['files'].values())
    assert storage.query('SELECT * FROM jobs')==[]
