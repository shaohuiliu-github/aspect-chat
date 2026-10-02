"""Local chat UI, using the standard library and the existing ASPECT tools."""
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit,parse_qs
import argparse,base64,hashlib,json,mimetypes,os,secrets,subprocess,sys,threading,time
from . import attachments,cases,conversations,i18n,knowledge,portable,previews,providers,runner,sessions,storage

WEB=storage.ROOT/'web'
TOKEN=secrets.token_urlsafe(32)
_preview_lock=threading.Lock()

def ensure_worker():
    try:
        info=json.loads((storage.DATA/'worker_heartbeat.json').read_text())
        alive=time.time()-info['time']<10
    except (OSError,ValueError,KeyError): alive=False
    if not alive and os.environ.get('ASPECT_CHAT_MANAGED_WORKER')!='1':
        storage.DATA.mkdir(parents=True,exist_ok=True)
        with (storage.DATA/'worker.log').open('ab') as log:
            subprocess.Popen([sys.executable,'-m','aspect_chat.runner'],cwd=storage.ROOT,
                             stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
    return alive

def job_list():
    return storage.query("SELECT j.id,j.case_id,j.state,j.created,j.cores,c.name AS model_name FROM jobs j LEFT JOIN cases c ON j.case_id=c.id WHERE j.kind='simulation' ORDER BY j.created DESC LIMIT 100")

def connection():
    info=providers.current()
    return {'id':info['id'],'name':info['name'],'model':info.get('model',''),'url':info['url'],
            'models':providers.model_options(),'ready':bool(storage.api_key()) or info['id']=='custom',
            'vision':providers.vision_supported(info['id'],info.get('model',''))}

def bootstrap(lang):
    cfg=storage.config()
    runtime=portable.runtime()
    text={k:v[0 if lang=='zh' else 1] for k,v in i18n.TEXT.items()}
    text['runtime_note']=text['runtime_note'].replace('{version}',runtime['version'])
    return {'lang':lang,'text':text,'runtime':runtime,'connection':connection(),
            'providers':[{'id':key,'name':value['name']} for key,value in providers.PROVIDERS.items()],
            'settings':{k:cfg[k] for k in ('task_cores','max_total_cores','timeout_seconds','binary','source_root','mpi')},
            'storage':portable.host_path(storage.DATA),'sessions':sessions.list_all(lang),
            'cases':storage.query('SELECT id,name FROM cases ORDER BY created DESC'),
            'attachments':storage.query('SELECT id,name,kind FROM attachments ORDER BY created DESC LIMIT 100'),
            'knowledge':knowledge.summary(),'sources':knowledge.sources(),'jobs':job_list()}

class Handler(BaseHTTPRequestHandler):
    server_version='ASPECTChat/2'
    def log_message(self,*args): pass  # Request bodies/keys are never logged.

    def send(self,value,status=200,content_type='application/json; charset=utf-8'):
        content=value if isinstance(value,bytes) else json.dumps(value,ensure_ascii=False,default=str).encode()
        self.send_response(status)
        self.send_header('Content-Type',content_type)
        self.send_header('Content-Length',str(len(content)))
        self.send_header('Cache-Control','no-store')
        self.send_header('X-Content-Type-Options','nosniff')
        self.send_header('Content-Security-Policy',"default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'")
        self.end_headers(); self.wfile.write(content)

    def check_host(self):
        return self.headers.get('Host') in self.allowed_hosts()

    def allowed_hosts(self):
        ports={self.server.server_port,int(os.environ.get('ASPECT_CHAT_PUBLIC_PORT',self.server.server_port))}
        return {f'{host}:{port}' for host in ('127.0.0.1','localhost') for port in ports}

    def do_GET(self):
        if not self.check_host(): self.send({'error':'Invalid host'},403); return
        try:
            path=urlsplit(self.path); args={k:v[0] for k,v in parse_qs(path.query).items()}
            if path.path in {'/','/index.html','/app.js','/style.css'}:
                name='index.html' if path.path=='/' else path.path[1:]
                content=(WEB/name).read_bytes()
                if name=='index.html': content=content.replace(b'__CSRF_TOKEN__',TOKEN.encode())
                self.send(content,content_type=mimetypes.guess_type(name)[0]+'; charset=utf-8'); return
            if path.path=='/api/health':
                self.send({'app':'aspect-chat','interface':2,'instance':os.environ.get('ASPECT_CHAT_INSTANCE',''),**portable.runtime()}); return
            if path.path=='/api/bootstrap':
                lang=args.get('lang',storage.config()['language'])
                if lang not in {'zh','en'}: raise ValueError('Invalid language')
                self.send(bootstrap(lang)); return
            if path.path=='/api/conversation':
                session=sessions.get(args['id'])
                messages=storage.query('SELECT id,role,content FROM chats WHERE session_id=? ORDER BY id',(session['id'],))
                requests=storage.query('SELECT id FROM requests WHERE session_id=? ORDER BY created DESC LIMIT 1',(session['id'],))
                request=conversations.status(requests[0]['id']) if requests else None
                diff=''
                if request and request['result']:
                    for event in request['result'].get('events',[]):
                        result=event.get('result')
                        if isinstance(result,dict) and result.get('diff'): diff=result['diff']
                self.send({'session':session,'messages':messages,'request':request,'diff':diff}); return
            if path.path=='/api/jobs':
                try: alive=time.time()-json.loads((storage.DATA/'worker_heartbeat.json').read_text())['time']<10
                except (OSError,ValueError,KeyError): alive=False
                self.send({'jobs':job_list(),'online':alive}); return
            if path.path=='/api/job':
                result=runner.status(args['id']); result['output_directory']=portable.host_path(result['output_directory'])
                self.send(result); return
            if path.path=='/api/model':
                case=storage.get_case(args['id']); text=cases.draft(case['id'])
                try:
                    with _preview_lock: previews.schedule(case['id'])
                except Exception as e: preview_error=str(e)
                else: preview_error=''
                preview=previews.latest(case['id'])
                if preview:
                    preview['files']={key:f"/api/field?job={preview['job_id']}&field={key}" for key in preview['files']}
                self.send({'case':case,'text':text,'revision':hashlib.sha256(text.encode()).hexdigest(),
                           'preview':preview,'preview_error':preview_error,'path':portable.host_path(Path(case['path'])/'draft.prm')}); return
            if path.path=='/api/field':
                job=args['job']; field=args['field']
                if field not in previews.FIELDS or len(job)!=12 or not all(c in '0123456789abcdef' for c in job): raise ValueError('Invalid field')
                image=storage.DATA/'runs'/job/'initial-fields'/(field+'.png')
                self.send(image.read_bytes(),content_type='image/png'); return
            if path.path=='/api/knowledge':
                self.send(knowledge.search(args.get('q',''),limit=8,source=args.get('source') or None,kind=args.get('kind') or None)); return
            self.send({'error':'Not found'},404)
        except (ValueError,KeyError,OSError) as e: self.send({'error':str(e)},400)
        except Exception as e: self.send({'error':str(e)},500)

    def do_POST(self):
        if not self.check_host() or self.headers.get('X-ASPECT-Token')!=TOKEN:
            self.send({'error':'Invalid request token'},403); return
        origin=self.headers.get('Origin')
        if origin and origin not in {'http://'+host for host in self.allowed_hosts()}:
            self.send({'error':'Invalid origin'},403); return
        try:
            size=int(self.headers.get('Content-Length',0))
            if size<1 or size>57*1024*1024: raise ValueError('Request too large')
            body=json.loads(self.rfile.read(size)); path=urlsplit(self.path).path
            if path=='/api/new':
                if body.get('lang','zh') not in {'zh','en'}: raise ValueError('Invalid language')
                self.send(sessions.create(body.get('lang','zh'))); return
            if path=='/api/bind':
                sessions.bind(body['session_id'],body.get('case_id')); self.send({'ok':True}); return
            if path=='/api/chat':
                prompt=body['prompt'].strip()
                if not prompt or len(prompt)>50000: raise ValueError('Invalid message length')
                ids=body.get('attachments',[])
                if not isinstance(ids,list) or len(ids)>5: raise ValueError('Select up to 5 attachments')
                self.send({'request_id':sessions.start(body['session_id'],prompt,ids)}); return
            if path=='/api/language':
                if body['lang'] not in {'zh','en'}: raise ValueError('Invalid language')
                storage.save_config({'language':body['lang']}); self.send({'ok':True}); return
            if path=='/api/provider':
                providers.select(body['provider'],model=body.get('model'))
                self.send(connection()); return
            if path=='/api/connection':
                pid=body['provider']; providers.select(pid,model=body.get('model'),url=body['url'].strip())
                if body.get('key','').strip(): storage.save_key(body['key'],pid)
                try: options=providers.discover(pid); error=''
                except Exception as e: options=providers.model_options(pid); error=str(e)
                self.send({'connection':connection(),'discovered':not bool(error),'count':len(options),'discovery_error':error}); return
            if path=='/api/compute':
                task=int(body['task_cores']); total=int(body['max_total_cores']); timeout=float(body['hours'])
                if not 1<=task<=total<=64 or not .01<=timeout<=168: raise ValueError('Invalid core budget or time limit')
                storage.save_config({'task_cores':task,'max_total_cores':total,'max_concurrent':64,'timeout_seconds':int(timeout*3600),
                                     **{k:body[k].strip() for k in ('binary','source_root','mpi')}})
                self.send({'ok':True}); return
            if path=='/api/upload':
                name=Path(body['name']).name; content=base64.b64decode(body['content'],validate=True)
                if len(content)>40*1024*1024: raise ValueError('Maximum file size: 40 MB')
                result=cases.import_upload(name,content) if name.lower().endswith(('.prm','.zip')) else attachments.ingest(name,content)
                if result.get('needs_selection'):
                    result['prm_files']=[portable.host_path(p) for p in result['prm_files']]
                if result.get('case_id') and body.get('session_id'): sessions.bind(body['session_id'],result['case_id'])
                self.send(result); return
            if path=='/api/import':
                result=cases.import_local(portable.input_path(body['path']))
                if body.get('session_id'): sessions.bind(body['session_id'],result['case_id'])
                self.send(result); return
            if path=='/api/load':
                result=cases.load_document(int(body['id']))
                if body.get('session_id'): sessions.bind(body['session_id'],result['case_id'])
                self.send(result); return
            if path=='/api/save':
                try: result=cases.save_draft(body['case_id'],body['text'],expected_revision=body['revision'])
                except cases.RevisionConflict:
                    self.send({'error':i18n.t('file_conflict',storage.config()['language'])},409); return
                self.send(result); return
            if path=='/api/open':
                self.send(portable.open_folder('job',body['job_id']) if body.get('job_id') else portable.open_folder('case',body['case_id'])); return
            if path=='/api/cancel': cases.cancel(body['id']); self.send({'ok':True}); return
            self.send({'error':'Not found'},404)
        except (ValueError,KeyError,OSError) as e: self.send({'error':str(e)},400)
        except Exception as e: self.send({'error':str(e)},500)

def main():
    parser=argparse.ArgumentParser(); parser.add_argument('--port',type=int,default=8517)
    parser.add_argument('--host',default='127.0.0.1'); args=parser.parse_args()
    sessions.migrate(); ensure_worker()
    server=ThreadingHTTPServer((args.host,args.port),Handler)
    print(f'ASPECT Chat: http://127.0.0.1:{server.server_port}',flush=True)
    try: server.serve_forever()
    except KeyboardInterrupt: pass
    finally: server.server_close()

if __name__=='__main__': main()
