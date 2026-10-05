"""Real-browser smoke test; uses installed Edge and Node, no extra packages.

Run python tests/capture_tactical.py. Screenshots go to artifacts/tactical-*.png.
"""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from tactical.server import make_server


def main():
    edge = Path(os.environ.get('EDGE_PATH',r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe'))
    if not edge.exists():
        raise SystemExit('Set EDGE_PATH to an installed Chromium browser executable.')
    with tempfile.TemporaryDirectory(prefix='tactical-browser-',ignore_cleanup_errors=True) as tmp:
        server = make_server(port=0,save_path=Path(tmp)/'save.json')
        worker = threading.Thread(target=server.serve_forever,daemon=True)
        worker.start()
        stopped = threading.Event()
        def tick():
            while not stopped.wait(.25):server.rooms.tick()
        ticker = threading.Thread(target=tick,daemon=True);ticker.start()
        # A dedicated temporary profile avoids interacting with the user's browser.
        browser = subprocess.Popen([str(edge),'--headless=new','--disable-gpu','--no-first-run','--no-sandbox','--disable-crash-reporter',
            '--remote-debugging-port=0','--remote-allow-origins=*',f'--user-data-dir={tmp}','--window-size=1500,1100','about:blank'],
            stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,
            creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        try:
            port_file = Path(tmp)/'DevToolsActivePort'
            for _ in range(100):
                if port_file.exists():break
                time.sleep(.1)
            if not port_file.exists():raise RuntimeError('Browser debugger did not start')
            debug_port = port_file.read_text().splitlines()[0]
            subprocess.run(['node',str(ROOT/'tests'/'tactical_browser.mjs'),
                f'http://127.0.0.1:{server.server_address[1]}',debug_port],check=True,cwd=ROOT)
        finally:
            stopped.set();ticker.join(timeout=2)
            server.shutdown();server.server_close();worker.join(timeout=2)
            browser.terminate()
            try:browser.wait(timeout=10)
            except subprocess.TimeoutExpired:browser.kill();browser.wait()


if __name__ == '__main__':main()
