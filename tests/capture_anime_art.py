"""Capture the current searchable catalog review, including partial generation."""
import argparse
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from build_art_review import build_review

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--pages',type=int,default=30)
    args=parser.parse_args()
    available,total=build_review()
    edge=os.environ.get('EDGE_PATH',r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe')
    with tempfile.TemporaryDirectory(prefix='anime-review-',ignore_cleanup_errors=True) as tmp:
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
            subprocess.run(['node',str(ROOT/'tests/anime_art_browser.mjs'),
                (ROOT/'artifacts/anime-art-review.html').as_uri(),port_file.read_text().splitlines()[0],
                str(args.pages),str(available)],check=True,cwd=ROOT)
        finally:
            browser.terminate()
            try:browser.wait(timeout=10)
            except subprocess.TimeoutExpired:browser.kill();browser.wait()

if __name__=='__main__':main()
