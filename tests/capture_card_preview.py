"""Capture and verify the isolated playable card review in Edge."""
import os
from pathlib import Path
import subprocess
import tempfile
import threading
import time
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from tactical.preview import make_preview_server

def main():
    edge=Path(os.environ.get('EDGE_PATH',r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe'))
    with tempfile.TemporaryDirectory(prefix='card-review-',ignore_cleanup_errors=True) as tmp:
        server=make_preview_server(0);worker=threading.Thread(target=server.serve_forever,daemon=True);worker.start()
        browser=subprocess.Popen([str(edge),'--headless=new','--disable-gpu','--no-first-run','--no-sandbox','--remote-debugging-port=0','--remote-allow-origins=*',f'--user-data-dir={tmp}','about:blank'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        try:
            portfile=Path(tmp)/'DevToolsActivePort'
            for _ in range(100):
                if portfile.exists():break
                time.sleep(.1)
            subprocess.run(['node',str(ROOT/'tests/card_preview_browser.mjs'),f'http://127.0.0.1:{server.server_address[1]}',portfile.read_text().splitlines()[0]],check=True,cwd=ROOT)
        finally:
            server.shutdown();server.server_close();worker.join(2);browser.terminate()
            try:browser.wait(10)
            except subprocess.TimeoutExpired:browser.kill();browser.wait()
if __name__=='__main__':main()
