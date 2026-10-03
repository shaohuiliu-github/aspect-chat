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
        def event(name,state):
            storage.execute('UPDATE requests SET event=? WHERE id=?',
                (json.dumps({'tool':name,'state':state}),request_id))
        try:
            args=(prompt,case_id,True,event,attachment_ids,lang)
            result=agent.chat(*args,session_id=session_id) if session_id else agent.chat(*args)
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
