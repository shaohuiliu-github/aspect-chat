"""Supervise web and worker so Docker stop preserves honest job states."""
import os, signal, subprocess, sys, time
from pathlib import Path

stopping=False
children=[]
def stop(*_):
    global stopping
    stopping=True
signal.signal(signal.SIGTERM,stop)
signal.signal(signal.SIGINT,stop)
data=Path(os.environ['ASPECT_CHAT_DATA']); data.mkdir(parents=True,exist_ok=True)
(data/'inputs').mkdir(exist_ok=True)
(data/'.host-open').mkdir(exist_ok=True)
from aspect_chat import sessions
sessions.migrate()
with (data/'worker.log').open('ab',buffering=0) as log:
    children.append(subprocess.Popen([sys.executable,'-m','aspect_chat.runner'],stdout=log,stderr=subprocess.STDOUT))
    children.append(subprocess.Popen([sys.executable,'-m','aspect_chat.web','--host','0.0.0.0','--port','8517']))
    try:
        while not stopping and all(p.poll() is None for p in children): time.sleep(.25)
    finally:
        # Stop the scheduler first: it cancels its ASPECT process groups and updates the DB.
        for child in children:
            if child.poll() is None: child.terminate()
        for child in children:
            try: child.wait(timeout=12)
            except subprocess.TimeoutExpired: child.kill(); child.wait()
if not stopping: sys.exit(1)
