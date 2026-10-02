"""Persistent chat history. A new conversation never deletes earlier work."""
import threading,time
from . import storage

_migration_lock=threading.Lock()
_start_lock=threading.Lock()

def migrate():
    with _migration_lock,storage.db() as db:
        for lang in ('zh','en'):
            rows=db.execute('SELECT * FROM chats WHERE session_id IS NULL AND lang=? ORDER BY id',(lang,)).fetchall()
            if not rows: continue
            ident=storage.uid(); first=next((r['content'] for r in rows if r['role']=='user'), 'ASPECT')
            case=db.execute('SELECT id FROM cases ORDER BY created DESC LIMIT 1').fetchone()
            db.execute('INSERT INTO chat_sessions VALUES(?,?,?,?,?,?)',
                       (ident,first.strip().replace('\n',' ')[:32],lang,case['id'] if case else None,rows[0]['created'],rows[-1]['created']))
            db.execute('UPDATE chats SET session_id=? WHERE session_id IS NULL AND lang=?',(ident,lang))
            db.execute('UPDATE requests SET session_id=? WHERE session_id IS NULL AND lang=?',(ident,lang))

def create(lang):
    ident=storage.uid(); now=time.time()
    storage.execute('INSERT INTO chat_sessions VALUES(?,?,?,?,?,?)',(ident,'',lang,None,now,now))
    return get(ident)

def get(ident):
    rows=storage.query('SELECT * FROM chat_sessions WHERE id=?',(ident,))
    if not rows: raise ValueError('Unknown conversation')
    return rows[0]

def list_all(lang):
    return storage.query('SELECT * FROM chat_sessions WHERE lang=? ORDER BY updated DESC',(lang,))

def bind(ident,case_id):
    if case_id: storage.get_case(case_id)
    storage.execute('UPDATE chat_sessions SET case_id=?,updated=? WHERE id=?',(case_id,time.time(),ident))

def start(ident,prompt,attachment_ids):
    from . import conversations
    with _start_lock:
        session=get(ident)
        for row in storage.query("SELECT id FROM requests WHERE session_id=? AND state='working'",(ident,)):
            if conversations.status(row['id'])['state']=='working':
                raise ValueError('This conversation is already processing a request')
        title=session['title'] or prompt.strip().replace('\n',' ')[:32]
        storage.execute('UPDATE chat_sessions SET title=?,updated=? WHERE id=?',(title,time.time(),ident))
        return conversations.start(prompt,session['case_id'],attachment_ids,session['lang'],ident)
