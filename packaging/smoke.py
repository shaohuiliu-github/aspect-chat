"""Actual ASPECT/MPI/preview/sweep verification in a fresh container workspace."""
import json,time
from pathlib import Path
from aspect_chat import agent,cases,conversations,knowledge,portable,previews,prm,providers,runner,sessions,storage

assert not storage.api_key()
assert portable.binary_version(storage.config()['binary'])=='3.1.0'
sources={s['label']:s for s in knowledge.sources()}
assert all(s['version']=='3.1.0' for s in sources.values() if s['role']=='runtime' and s['label']!='world-builder-runtime')
assert sources['world-builder-runtime']['version']=='1.1.1'
assert sources['aspect-main']['role']=='reference'
assert all(r['role']=='runtime' for r in knowledge.search('subduction'))
assert knowledge.search('subducting plate',source='world-builder-runtime')
assert knowledge.search('compute',source='official-api-3.1.0',kind='code')
assert knowledge.parameter_info('Dimension')['default_value']
reference=next(r for r in knowledge.search('convection box',limit=20,kind='model') if r['path']=='cookbooks/convection-box/convection-box.prm')
case=cases.load_document(reference['id'])['case_id']
cases.modify(case,{'End time':'0.002','Mesh refinement/Initial global refinement':'2','Mesh refinement/Initial adaptive refinement':'0'})
storage.save_config({'max_total_cores':4,'task_cores':2,'timeout_seconds':180})
session=sessions.create('zh');sessions.bind(session['id'],case)
single=cases.enqueue(case,cores=2)
preview=previews.schedule(case)
scan=cases.sweep(case,'Material model/Simple model/Viscosity',1,2,count=2,sampling='linear',cores=1)
# Exercise the background conversation and real runner without a paid API call.
reply_count=0
def fake_complete(*_):
    global reply_count
    reply_count+=1
    if reply_count==1:
        calls=[('modify_parameters',{'case_id':case,'changes':{'End time':'0.001'}}),('submit_case',{'case_id':case,'cores':1})]
        return {'role':'assistant','content':None,'tool_calls':[{'id':'mock-'+str(i),'type':'function','function':{'name':name,'arguments':json.dumps(args)}} for i,(name,args) in enumerate(calls)]}
    return {'role':'assistant','content':'测试模型已修改并提交运行。'}
providers.complete=fake_complete
agent.api_key=lambda *_:'local-test-only'
request=sessions.start(session['id'],'将结束时间改为 0.001 并运行模型。',[])
for _ in range(80):
    chat=conversations.status(request)
    if chat['state']!='working': break
    time.sleep(.1)
assert chat['state']=='done',chat
chat_job=next(e['result']['job_id'] for e in chat['result']['events'] if e['tool']=='submit_case')
assert sessions.get(session['id'])['case_id']==case
ids=[single['job_id'],preview,chat_job]+[j['job_id'] for j in scan['jobs']]
deadline=time.time()+240;maximum=0
while time.time()<deadline:
    states=[runner.status(identifier) for identifier in ids]
    maximum=max(maximum,sum(x['cores'] for x in states if x['state'] in {'validating','running'}))
    assert maximum<=4
    if all(x['state'] in runner.TERMINAL for x in states): break
    time.sleep(.5)
assert all(x['state']=='succeeded' for x in states),json.dumps([{k:x[k] for k in ('id','state','note','log','validation_log')} for x in states])
assert '2 MPI processes' in runner.status(single['job_id'])['log']
assert runner.statistics(single['job_id'])['available']
assert all((storage.DATA/'runs'/preview/'initial-fields'/(name+'.png')).is_file() for name in previews.FIELDS)
assert all(list((storage.DATA/'runs'/identifier/'output').rglob('*.vtu')) for identifier in ids)
summary=runner.export_batch(scan['batch']);assert len(summary['rows'])==2
result={'solver':portable.runtime(),'knowledge':knowledge.summary(),'chat_api':'mock provider; real modification, submission and computation','chat_job':chat_job,'mpi_cores':2,'single_job':single['job_id'],
 'preview_job':preview,'sweep_jobs':[x['job_id'] for x in scan['jobs']],'all_succeeded':True,'maximum_observed_cores':maximum,
 'host_output_directory':portable.host_path(single['output_directory']),'checks':['real 2-process MPI','two parameter sweep runs','three initial field PNGs','ASPECT statistics','persistent VTU outputs','readonly version-matched knowledge']}
(storage.DATA/'smoke-report.json').write_text(json.dumps(result,indent=2))
print(json.dumps(result,indent=2))
