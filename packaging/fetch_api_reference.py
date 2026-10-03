"""Fetch the pinned official Doxygen reference as searchable text, without scripts."""
from pathlib import Path
from html.parser import HTMLParser
from urllib.parse import urljoin,urlparse,urldefrag
import argparse,asyncio,hashlib,json,time
import httpx

class Page(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True);self.links=[];self.text=[];self.title=[];self.depth=0;self.capture=None;self.skip=0;self.in_title=False
    def handle_starttag(self,tag,attrs):
        a=dict(attrs)
        if tag=='a' and a.get('href'):self.links.append(a['href'])
        if tag=='title':self.in_title=True
        if tag in {'script','style'}:self.skip+=1
        if tag=='div':
            self.depth+=1
            if self.capture is None and 'contents' in a.get('class','').split():self.capture=self.depth
        if self.capture and tag in {'p','div','tr','li','h1','h2','h3','pre','br'}:self.text.append('\n')
        if self.capture and tag=='img' and a.get('alt'):self.text.append(a['alt'])
    def handle_endtag(self,tag):
        if tag=='title':self.in_title=False
        if tag in {'script','style'}:self.skip=max(0,self.skip-1)
        if tag=='div':
            if self.capture==self.depth:self.capture=None
            self.depth-=1
        if self.capture and tag in {'p','tr','li','pre'}:self.text.append('\n')
    def handle_data(self,data):
        if self.in_title:self.title.append(data)
        if self.capture and not self.skip:self.text.append(data)

async def fetch(base,dest):
    dest.mkdir(parents=True,exist_ok=True)
    pending={base+p for p in ('index.html','classes.html','modules.html','namespaces.html','files.html','pages.html')};seen=set();records=[];failed=[]
    previous=dest/'fetch-manifest.json'
    if previous.exists():
        saved=json.loads(previous.read_text())
        records=[r for r in saved['pages'] if (dest/r['path']).is_file()]
        seen={r['url'] for r in records}
        pending.update(r['url'] for r in saved['failed'])
        pending.difference_update(seen)
    semaphore=asyncio.Semaphore(2)
    async with httpx.AsyncClient(timeout=45,follow_redirects=True) as client:
        async def get(url):
            async with semaphore:
                error='retry limit'
                for attempt in range(5):
                    try:
                        await asyncio.sleep(.6)
                        r=await client.get(url)
                        if r.status_code in (429,500,502,503,504):
                            error='HTTP '+str(r.status_code)
                            await asyncio.sleep(min(45,5*(attempt+1)));continue
                        r.raise_for_status();page=Page();page.feed(r.text);return url,page,r.content
                    except (httpx.HTTPError,ValueError) as e:
                        if attempt==4:return url,None,str(e)
                        await asyncio.sleep(attempt+1)
                return url,None,error
        while pending:
            if len(seen)+len(pending)>5000:raise RuntimeError('Unexpected API reference size')
            batch=sorted(pending)[:60];pending.difference_update(batch);seen.update(batch)
            for url,page,raw in await asyncio.gather(*(get(u) for u in batch)):
                if page is None:failed.append({'url':url,'error':raw});continue
                body='\n'.join(line.strip() for line in ''.join(page.text).splitlines() if line.strip())
                name=urlparse(url).path.rsplit('/',1)[-1].removesuffix('.html')+'.md'
                (dest/name).write_text('# '+''.join(page.title)+'\n\nSource: '+url+'\nVersion: ASPECT 3.1.0\n\n'+body+'\n')
                records.append({'url':url,'path':name,'sha256':hashlib.sha256(raw).hexdigest()})
                for link in page.links:
                    candidate=urldefrag(urljoin(url,link))[0];path=urlparse(candidate).path;filename=path.rsplit('/',1)[-1]
                    if not candidate.startswith(base) or not path.endswith('.html') or urlparse(candidate).query:continue
                    if filename.endswith(('_source.html','-members.html')) or filename.startswith(('functions','globals','dir_')):continue
                    if candidate not in seen:pending.add(candidate)
            print(json.dumps({'downloaded':len(records),'pending':len(pending),'failed':len(failed)}),flush=True)
            # Preserve progress across interruption or server rate limits.
            checkpoint={'base':base,'version':'3.1.0','retrieved':time.strftime('%Y-%m-%d'),'pages':records,
                        'failed':failed+[{'url':u,'error':'not yet fetched'} for u in sorted(pending)]}
            previous.write_text(json.dumps(checkpoint,indent=2))
    report={'base':base,'version':'3.1.0','retrieved':time.strftime('%Y-%m-%d'),'pages':records,'failed':failed}
    (dest/'fetch-manifest.json').write_text(json.dumps(report,indent=2))
    if failed:raise RuntimeError(str(len(failed))+' API pages failed; inspect manifest before release')
    return report

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('destination',type=Path);a=p.parse_args()
    asyncio.run(fetch('https://aspect-documentation.readthedocs.io/en/v3.1.0/doxygen/',a.destination))
