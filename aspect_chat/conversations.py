"""API/tool work runs off the UI thread so jobs and files can keep refreshing."""
import json,os,threading,time
from . import agent,storage

def start(prompt,case_id,attachment_ids,lang,session_id=None):
    request_id=storage.uid()
    from . import attachments
    files=[{k:v for k,v in attachments.get(ident).items() if k in {'id','name','kind'}} for ident in attachment_ids]
    storage.add_chat('user',prompt,lang,session_id,files)
    storage.execute('INSERT INTO requests(id,state,lang,created,pid,event,result,error,session_id) VALUES(?,?,?,?,?,?,?,?,?)',
        (request_id,'working',lang,time.time(),os.getpid(),'','','',session_id))
    def run():
        partial_events=[]
        announced=set()
        def publish(name,args,output):
            # Publish saved work before another remote model call can delay the reply.
            partial_events.append({'tool':name,'args':args,'result':output})
            storage.execute('UPDATE requests SET result=? WHERE id=?',
                (json.dumps({'text':'','events':partial_events},ensure_ascii=False,default=str),request_id))
            if not isinstance(output,dict) or output.get('error'): return
            bound=output.get('case_id')
            if bound and name in {'load_model','create_model','create_i2vis_model','modify_parameters','digitize_density_map','couple_density_map'}:
                if session_id:
                    storage.execute('UPDATE chat_sessions SET case_id=?,updated=? WHERE id=?',(bound,time.time(),session_id))
                from . import previews
                try: previews.schedule(bound)
                except Exception: pass
                if name in {'load_model','create_model','create_i2vis_model'} and bound not in announced:
                    announced.add(bound)
                    case=storage.get_case(bound)
                    text=(f"**模型已保存：{case['name']}**\n\n初始场正在生成。可以立即查看和编辑参数；计算状态会单独更新。" if lang=='zh' else
                          f"**Model saved: {case['name']}**\n\nPreparing the initial fields. You can view and edit the inputs now; simulation status updates separately.")
                    storage.add_chat('assistant',text,lang,session_id)
            submitted=output.get('jobs',[]) if name=='sweep_parameter' else [output] if name=='submit_case' else []
            for job in submitted:
                if not isinstance(job,dict) or not job.get('job_id') or job['job_id'] in announced: continue
                announced.add(job['job_id'])
                directory=job.get('output_directory','')
                text=(f"**任务已提交：{job.get('name',job['job_id'])}**\n\n结果目录：`{directory}`\n\n正在排队或启动，尚未确认成功。初始场和输入文件现在就可以查看；任务完成后会提醒。" if lang=='zh' else
                      f"**Simulation submitted: {job.get('name',job['job_id'])}**\n\nResults: `{directory}`\n\nQueued or starting; completion is not confirmed yet. View the initial fields and inputs now. You will be notified when the task finishes.")
                storage.add_chat('assistant',text,lang,session_id)
        def event(name,state):
            storage.execute('UPDATE requests SET event=? WHERE id=?',
                (json.dumps({'tool':name,'state':state}),request_id))
        try:
            args=(prompt,case_id,True,event,attachment_ids,lang)
            result=agent.chat(*args,session_id=session_id,on_result=publish,
                              on_message=lambda text: storage.add_chat('assistant',text,lang,session_id))
            storage.add_chat('assistant',result['text'],lang,session_id)
            if session_id:
                bound_case=case_id
                for item in result.get('events',[]):
                    output=item.get('result')
                    if isinstance(output,dict) and output.get('case_id') and item['tool'] in {'load_model','create_model','create_i2vis_model','modify_parameters','digitize_density_map','couple_density_map'}:
                        bound_case=output['case_id']
                storage.execute('UPDATE chat_sessions SET case_id=?,updated=? WHERE id=?',(bound_case,time.time(),session_id))
                if bound_case:
                    from . import previews
                    try: previews.schedule(bound_case)
                    except Exception: pass  # The model panel reports preview failures separately.
            storage.execute("UPDATE requests SET state='done',result=? WHERE id=?",(json.dumps(result,ensure_ascii=False),request_id))
        except Exception as e:
            from .i18n import t
            storage.add_chat('assistant',t('failed_request',lang),lang,session_id)
            storage.execute("UPDATE requests SET state='error',error=? WHERE id=?",(str(e),request_id))
    threading.Thread(target=run,name='aspect-chat-'+request_id,daemon=True).start()
    return request_id

def status(request_id):
    rows=storage.query('SELECT * FROM requests WHERE id=?',(request_id,))
    if not rows: return None
    item=rows[0]
    if item['state']=='working':
        try: os.kill(item['pid'],0)
        except ProcessLookupError:
            storage.execute("UPDATE requests SET state='error',error='Application restarted during request' WHERE id=?",(request_id,))
            item['state']='error'; item['error']='Application restarted during request'
    item['event']=json.loads(item['event']) if item['event'] else None
    item['result']=json.loads(item['result']) if item['result'] else None
    return item
