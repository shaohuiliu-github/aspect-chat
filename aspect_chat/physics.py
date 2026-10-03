"""Paper-to-input evidence ledger, tied to the immutable input revision."""
from pathlib import Path
import hashlib,json,time
from . import storage,prm
CATEGORIES={'geometry','gravity','rheology','density','thermal','initial_conditions','boundary_conditions','numerics'}
CRITICAL=CATEGORIES-{'numerics'}

def revision(case_id):
    c=storage.get_case(case_id);root=Path(c['path']);h=hashlib.sha256()
    for name in ('draft.prm',) if c['engine']=='aspect' else ('init.t3c','mode.t3c'):
        h.update(name.encode());h.update((root/name).read_bytes())
    for p in sorted((root/'assets').rglob('*')):
        if p.is_file() and p.suffix in {'.json','.dat','.wb','.txt','.csv'}:h.update(str(p.relative_to(root)).encode());h.update(p.read_bytes())
    return h.hexdigest()

def current_values(case_id):
    c=storage.get_case(case_id)
    if c['engine']=='i2vis':
        from .i2vis import inspect
        return inspect(case_id)['parameters']
    return prm.values((Path(c['path'])/'draft.prm').read_text())

def record(case_id,rows,missing,notes=''):
    from . import attachments,knowledge
    vals=current_values(case_id);clean=[]
    for index,row in enumerate(rows):
        r=dict(row)
        if r.get('category') not in CATEGORIES or r.get('status') not in {'paper','converted','assumed','template','missing'}:raise ValueError('Invalid alignment category/status')
        if r.get('status') in {'paper','converted'}:
            prepared=r.get('knowledge_document_id') is not None
            if not r.get('attachment_id') or not isinstance(r.get('page'),int) or not (r.get('quote') or prepared) or not r.get('source_unit'):
                missing_fields=[]
                if not r.get('attachment_id'):missing_fields.append('attachment_id')
                if not isinstance(r.get('page'),int):missing_fields.append('page (integer; the key is page, not pdf_page or source_page)')
                if not (r.get('quote') or prepared):missing_fields.append('quote or knowledge_document_id')
                if not r.get('source_unit'):missing_fields.append('source_unit')
                raise ValueError(f"Alignment row {index}, {r.get('parameter','unnamed')}: supply "+', '.join(missing_fields))
            r['source_sha256']=hashlib.sha256(Path(attachments.get(r['attachment_id'])['path']).read_bytes()).hexdigest()
            normalize=lambda s:' '.join(str(s).split()).lower()
            if prepared:
                f=knowledge.prepared_fact(r['knowledge_document_id'],r.get('fact_id',''),r['source_sha256'])
                if f['category']=='diagnostic':raise ValueError('A published diagnostic result cannot be recorded as a prescribed physical parameter')
                if f['pdf_page']!=r['page'] or f['unit']!=r['source_unit'] or f['category']!=r['category']:
                    raise ValueError('Prepared fact page, units or category do not match the ledger row')
                value=r.get('source_value')
                try:equal=float(value)==float(f['value'])
                except (ValueError,TypeError):equal=value==f['value']
                if not equal:raise ValueError('Source value differs from the prepared paper fact')
                r['prepared_evidence']=f
            else:
                source=attachments.read(r['attachment_id'],pages=[r['page']])['passages'][0]['text']
                if normalize(r['quote']) not in normalize(source):raise ValueError('The supporting quote is not found on the cited PDF page; inspect the rendered page and mark uncertain/OCR values as assumed')
            if r['status']=='converted' and not r.get('conversion'):raise ValueError('Converted values require the conversion formula')
        path=r.get('path','')
        if path:
            if path not in vals:raise ValueError('Alignment points to an unknown input parameter: '+path+'. Use one exact inspected path per row; do not append variable names or combine paths with |. Put variable-level details in conversion.')
            actual=str(vals[path]);r['actual_value']=actual
            if 'written_value' in r and str(r['written_value']).replace(' ','')!=actual.replace(' ',''):raise ValueError('The recorded value does not match the current file: '+path)
        clean.append(r)
    payload={'case_id':case_id,'input_revision':revision(case_id),'created':time.time(),'rows':clean,'missing':missing,'notes':notes,
             'priority':'Physical parameter alignment first; discretization and solver convergence second. Evidence quotes are checked, but scientific equivalence still needs expert review.'}
    p=Path(storage.get_case(case_id)['path'])/'physics-alignment.json';p.write_text(json.dumps(payload,ensure_ascii=False,indent=2));return report(case_id)

def report(case_id):
    p=Path(storage.get_case(case_id)['path'])/'physics-alignment.json'
    if not p.exists():return {'state':'unreviewed','rows':[],'missing':[],'uncovered_categories':sorted(CRITICAL)}
    r=json.loads(p.read_text());r['stale']=r['input_revision']!=revision(case_id)
    covered={v['category'] for v in r['rows'] if v['status'] in {'paper','converted'}};r['uncovered_categories']=sorted(CRITICAL-covered)
    r['state']='stale' if r['stale'] else 'needs_review' if r['missing'] or r['uncovered_categories'] or any(x['status'] in {'assumed','template','missing'} for x in r['rows']) else 'evidence_recorded'
    return r


def snapshot(case_id,run_root):
    """Preserve evidence and exact input identity with each run."""
    r=report(case_id)
    payload={'engine':storage.get_case(case_id)['engine'],'draft_revision':revision(case_id),'alignment':r}
    (Path(run_root)/'physics-alignment.json').write_text(json.dumps(payload,ensure_ascii=False,indent=2))
    return {'draft_revision':payload['draft_revision'],'physics_alignment_state':r['state'],'physics_alignment_file':'physics-alignment.json'}
