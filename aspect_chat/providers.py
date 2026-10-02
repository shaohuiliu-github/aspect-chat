"""Provider presets and small protocol adapters. Keys stay scoped to providers."""
import base64, json, re, time
from urllib.parse import urlparse
import httpx
from . import storage

PROVIDERS = {
 'openai': {'name':'OpenAI','url':'https://api.openai.com/v1','models':['gpt-6.1-sol','gpt-6-astra','gpt-6-luna','gpt-5.4','gpt-5.4-mini','gpt-4.1'],'protocol':'openai'},
 'claude': {'name':'Claude','url':'https://api.anthropic.com/v1','models':['claude-sonnet-5-5','claude-opus-5-5','claude-fable-5-1','claude-haiku-4-5'],'protocol':'claude'},
 'gemini': {'name':'Gemini','url':'https://generativelanguage.googleapis.com/v1beta/openai','models':['gemini-3.8-flash','gemini-3.7-flash','gemini-3.1-pro-preview'],'protocol':'openai'},
 'deepseek': {'name':'DeepSeek','url':'https://api.deepseek.com/v1','models':['deepseek-flash','deepseek-v4-pro','deepseek-chat','deepseek-reasoner'],'protocol':'openai'},
 'qwen': {'name':'Qwen','url':'https://dashscope.aliyuncs.com/compatible-mode/v1','models':['qwen3.8-max','qwen3.8-flash','qwen3.7-plus','qwen-plus','qwen3-vl-plus','qwen3-coder-plus'],'protocol':'openai'},
 'zhipu': {'name':'GLM','url':'https://open.bigmodel.cn/api/paas/v4','models':['glm-4.6','glm-4.5v'],'protocol':'openai'},
 'kimi': {'name':'Kimi','url':'https://api.moonshot.cn/v1','models':['kimi-k3','kimi-k2.7-code','kimi-k2.6','kimi-k2.5'],'protocol':'openai'},
 'minimax': {'name':'MiniMax','url':'https://api.minimax.io/v1','models':['MiniMax-M3','MiniMax-M2.7','MiniMax-M2.5'],'protocol':'openai'},
 'custom': {'name':'Custom','url':'http://127.0.0.1:11434/v1','models':[],'protocol':'openai'},
}

def current(provider=None):
    cfg=storage.config(); pid=provider or cfg['provider']; preset=PROVIDERS[pid]
    saved=cfg.get('providers',{}).get(pid,{})
    # Preserve legacy custom endpoint/model until this provider has its own settings.
    if not saved and pid==cfg['provider']: saved={'url':cfg['base_url'],'model':cfg['model']}
    return {'id':pid,**preset,**saved}

def select(provider,model=None,url=None):
    cfg=storage.config(); info=current(provider)
    selected=model or info.get('model') or next(iter(info['models']),'')
    address=url or info['url']; parsed=urlparse(address)
    if parsed.scheme not in {'https','http'} or not parsed.netloc or parsed.username or parsed.password or parsed.query:
        raise ValueError('Invalid API URL')
    all_settings=cfg.get('providers',{}); all_settings[provider]={'url':address.rstrip('/'),'model':selected}
    storage.save_config({'provider':provider,'model':selected,'base_url':address.rstrip('/'),'providers':all_settings})

def headers(info,key):
    if info['protocol']=='claude': return {'x-api-key':key,'anthropic-version':'2023-06-01'}
    return {'Authorization':'Bearer '+key}

def check(response,key):
    if response.status_code>=400:
        # Never put credentials or request objects in the exception/log.
        body=response.text.replace(key,'[REDACTED]') if key else response.text
        raise ValueError(f'HTTP {response.status_code}: {body[:500]}')
    return response.json()

def discover(provider=None):
    info=current(provider); key=storage.api_key(info['id'])
    if not key and info['id']!='custom': raise ValueError('API key required')
    with httpx.Client(timeout=25,follow_redirects=False) as client:
        payload=check(client.get(info['url'].rstrip('/')+'/models',headers=headers(info,key)),key)
    models=sorted({r['id'] for r in payload.get('data',[]) if r.get('id') and not any(x in r['id'].lower() for x in
        ('embedding','whisper','tts','dall-e','image','moderation','realtime','audio','rerank','live','transcribe','veo','omni-1.1'))})
    if not models: raise ValueError('No chat models returned; enter the model ID provided by your service.')
    path=storage.DATA/'models.json'; cached=json.loads(path.read_text()) if path.exists() else {}
    cached[info['id']]={'models':models,'url':info['url'],'time':time.time()}
    path.write_text(json.dumps(cached)); return models

def model_options(provider=None):
    info=current(provider); path=storage.DATA/'models.json'
    cached=json.loads(path.read_text()).get(info['id'],{}) if path.exists() else {}
    models=cached.get('models',[]) if cached.get('url')==info['url'] else []
    return list(dict.fromkeys(m for m in [info.get('model',''),*models,*info['models']] if m))

def vision_supported(provider,model):
    m=model.lower()
    if provider=='deepseek': return m in {'deepseek-flash','deepseek-v4-flash','deepseek-v4-flash-vision-exp'} or m.startswith('deepseek-v4.1-flash')
    if provider=='minimax': return 'minimax-m3' in m
    if provider=='qwen': return any(s in m for s in ('vl','omni','vision','qwen3.5','qwen3.6','qwen3.7','qwen3.8'))
    if provider=='zhipu': return any(s in m for s in ('4v','4.5v','4.6v','vision'))
    if provider=='kimi': return any(s in m for s in ('k2.5','k2.6','k2.7','k3','vision'))
    if provider=='openai' and any(s in m for s in ('o1-mini','o3-mini','gpt-3.5','gpt-4-turbo')): return False
    return provider in {'openai','claude','gemini','custom'}

def claude_payload(messages,tools,model):
    system='\n'.join(m['content'] for m in messages if m['role']=='system'); converted=[]
    for m in messages:
        if m['role']=='system': continue
        role='assistant' if m['role']=='assistant' else 'user'; blocks=[]
        if m['role']=='tool':
            blocks=[{'type':'tool_result','tool_use_id':m['tool_call_id'],'content':m['content']}]
        else:
            content=m.get('content') or ''
            if isinstance(content,str):
                if content: blocks.append({'type':'text','text':content})
            else:
                for part in content:
                    if part['type']=='text': blocks.append(part)
                    elif part['type']=='image_url':
                        url=part['image_url']['url']; prefix,data=url.split(',',1)
                        blocks.append({'type':'image','source':{'type':'base64','media_type':prefix[5:].split(';')[0],'data':data}})
            for call in m.get('tool_calls') or []:
                blocks.append({'type':'tool_use','id':call['id'],'name':call['function']['name'],'input':json.loads(call['function']['arguments'])})
            if m.get('_claude_content'): blocks=m['_claude_content']
        if not blocks: continue
        if converted and converted[-1]['role']==role: converted[-1]['content'].extend(blocks)
        else: converted.append({'role':role,'content':blocks})
    return {'model':model,'max_tokens':8192,'system':system,'messages':converted,
        'tools':[{'name':t['function']['name'],'description':t['function']['description'],
                  'input_schema':t['function']['parameters']} for t in tools]}

def complete(client,info,key,messages,tools):
    if info['protocol']=='claude':
        payload=claude_payload(messages,tools,info['model'])
        data=check(client.post(info['url'].rstrip('/')+'/messages',headers=headers(info,key),json=payload),key)
        calls=[]; text=[]
        for b in data.get('content',[]):
            if b['type']=='text': text.append(b['text'])
            if b['type']=='tool_use': calls.append({'id':b['id'],'type':'function','function':{'name':b['name'],'arguments':json.dumps(b['input'])}})
        return {'role':'assistant','content':'\n'.join(text),'tool_calls':calls,'_claude_content':data.get('content',[])}
    payload={'model':info['model'],'messages':messages,'tools':tools,'tool_choice':'auto'}
    if info['id']=='qwen': payload['enable_thinking']=False
    if info['id']=='kimi' and 'k2.5' in info['model']: payload['thinking']={'type':'disabled'}
    data=check(client.post(info['url'].rstrip('/')+'/chat/completions',headers=headers(info,key),json=payload),key)
    # Keep reasoning_content for services that require it in tool continuations.
    return data['choices'][0]['message']

def visible_text(content):
    return re.sub(r'<think>.*?</think>','',content or '',flags=re.S).strip()
