"""Capture the six-piece review in an isolated browser; never change live assets."""
import os
import argparse
from pathlib import Path
import subprocess
import sys
import tempfile
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from build_art_direction_review import build


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--version',choices=['v2','v3'],default='v2');parser.add_argument('--size',action='store_true');parser.add_argument('--game',action='store_true')
    args=parser.parse_args();version=args.version
    build(version)
    edge=os.environ.get('EDGE_PATH',r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe')
    with tempfile.TemporaryDirectory(prefix='art-v2-',ignore_cleanup_errors=True) as tmp:
        browser=subprocess.Popen([edge,'--headless=new','--disable-gpu','--no-first-run','--no-sandbox',
            '--disable-crash-reporter','--remote-debugging-port=0','--remote-allow-origins=*',
            f'--user-data-dir={tmp}','about:blank'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,
            creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        try:
            port_file=Path(tmp)/'DevToolsActivePort'
            for _ in range(100):
                if port_file.exists():break
                time.sleep(.1)
            if not port_file.exists():raise RuntimeError('Browser debugger did not start')
            subprocess.run(['node',str(ROOT/('tests/game_art_browser.mjs' if args.game else 'tests/art_direction_v2_browser.mjs')),
                (ROOT/('assets/art/direction-'+version+('/game.html' if args.game else '/size.html' if args.size else '/index.html'))).as_uri(),port_file.read_text().splitlines()[0],version],check=True,cwd=ROOT)
        finally:
            browser.terminate()
            try:browser.wait(timeout=10)
            except subprocess.TimeoutExpired:browser.kill();browser.wait()


if __name__=='__main__':main()
