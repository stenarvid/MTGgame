"""Run with python -m tactical.server; browser clients have private bearer seats."""
import argparse
import json
import secrets
import threading
import time
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse, parse_qs
from .battle import RuleError
from .session import Session
from .artwork import artwork_path

ROOT = Path(__file__).resolve().parent
SAVE = ROOT.parent / 'tactical-save.json'


class Rooms:
    def __init__(self, save_path=SAVE):
        self.rooms = {}
        self.lock = threading.RLock()
        self.save_path = Path(save_path)
        self.error = ''
        self.dirty = False
        self.last_save = 0
        if self.save_path.exists():
            try:
                data = json.loads(self.save_path.read_text(encoding='utf-8'))
                if data['version'] != 1:
                    raise ValueError('Unsupported tactical save version')
                for code,room in data['rooms'].items():
                    self.rooms[code] = dict(session=Session.from_dict(room['session']),tokens=room['tokens'])
            except (ValueError,KeyError,TypeError,OSError) as exc:
                self.error = f'Could not load tactical saves: {exc}. Existing file will not be overwritten.'

    def save(self):
        if self.error:
            return
        data = dict(version=1,rooms={code:dict(session=r['session'].to_dict(),tokens=r['tokens']) for code,r in self.rooms.items()})
        temp = self.save_path.with_suffix('.tmp')
        try:
            temp.write_text(json.dumps(data),encoding='utf-8')
            temp.replace(self.save_path)
            self.dirty = False
            self.last_save = time.time()
        except OSError as exc:
            self.error = f'Save failed: {exc}'

    def create(self, body):
        session = Session(body.get('mode','solo'),target=body.get('target',5),size=4 if body.get('mode','solo') == 'solo' else body.get('size',4))
        seat = session.add_member(body.get('name','Player'))
        code = secrets.token_hex(3).upper()
        while code in self.rooms:
            code = secrets.token_hex(3).upper()
        token = secrets.token_urlsafe(32)
        self.rooms[code] = dict(session=session,tokens={token:seat})
        self.dirty = True
        return dict(code=code,token=token)

    def join(self, body):
        code = str(body.get('code','')).upper()
        room = self.rooms.get(code)
        if not room:
            raise RuleError('Room not found.')
        if room['session'].mode == 'solo':
            raise RuleError('Solo campaigns cannot be joined.')
        seat = room['session'].add_member(body.get('name','Player'))
        token = secrets.token_urlsafe(32)
        room['tokens'][token] = seat
        self.dirty = True
        return dict(code=code,token=token)

    def authenticate(self, code, token):
        room = self.rooms.get(str(code).upper())
        if not room or token not in room['tokens']:
            raise RuleError('Invalid room or private seat token.')
        return room['session'], room['tokens'][token]

    def tick(self):
        with self.lock:
            for room in self.rooms.values():
                s = room['session']
                before = (s.stage,len(s.battle.log) if s.battle else 0,s.pick_number)
                try:
                    s.tick()
                except RuleError as exc:
                    # Surface a rule failure instead of silently killing the game loop.
                    if s.battle:
                        s.battle.note(f'AI paused: {exc}')
                    for m in s.members:
                        if m['bot'] and s.mode == 'human':
                            m['bot'] = False
                after = (s.stage,len(s.battle.log) if s.battle else 0,s.pick_number)
                self.dirty |= before != after
            if self.dirty and time.time()-self.last_save >= 2:
                self.save()


class Handler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

    def reply(self, payload, status=200):
        data = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header('Content-Type','application/json')
        self.send_header('Cache-Control','no-store')
        self.send_header('Content-Length',str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path.startswith('/art/'):
            path = artwork_path(parsed.path.removeprefix('/art/'))
            if path is None:
                self.reply(dict(error='Unknown illustration'),404)
                return
            data = path.read_bytes()
            self.send_response(200)
            self.send_header('Content-Type','image/png')
            self.send_header('Content-Length',str(len(data)))
            self.send_header('Cache-Control','public, max-age=3600')
            self.end_headers()
            self.wfile.write(data)
            return
        if parsed.path in ('/', '/style.css', '/cards.js', '/card-hover.js', '/spell-fx.js', '/spell-fx.css', '/effect-profiles.json', '/battle-presentation.js', '/battle-presentation.css'):
            filename = 'index.html' if parsed.path == '/' else parsed.path[1:]
            content_type = {'index.html':'text/html','style.css':'text/css','cards.js':'text/javascript','card-hover.js':'text/javascript','spell-fx.js':'text/javascript','spell-fx.css':'text/css','effect-profiles.json':'application/json','battle-presentation.js':'text/javascript','battle-presentation.css':'text/css'}[filename]
            data = (ROOT/'web'/filename).read_bytes()
            self.send_response(200)
            self.send_header('Content-Type',content_type+'; charset=utf-8')
            self.send_header('Content-Length',str(len(data)))
            self.send_header('X-Content-Type-Options','nosniff')
            self.end_headers()
            self.wfile.write(data)
            return
        if parsed.path != '/api/state':
            self.reply(dict(error='Not found'),404)
            return
        try:
            query = parse_qs(parsed.query)
            with self.server.rooms.lock:
                s,i = self.server.rooms.authenticate(query.get('code',[''])[0],self.headers.get('Authorization','').removeprefix('Bearer '))
                s.members[i]['last_seen'] = time.time()
                state = s.view(i)
                state['save_error'] = self.server.rooms.error
            self.reply(state)
        except RuleError as exc:
            self.reply(dict(error=str(exc)),403)

    def do_POST(self):
        try:
            length = int(self.headers.get('Content-Length','0'))
            if not 0 < length <= 16384:
                raise RuleError('Invalid request size.')
            body = json.loads(self.rfile.read(length))
            if not isinstance(body,dict):
                raise RuleError('Expected an action object.')
            with self.server.rooms.lock:
                if self.path == '/api/create':
                    result = self.server.rooms.create(body)
                elif self.path == '/api/join':
                    result = self.server.rooms.join(body)
                elif self.path == '/api/action':
                    s,i = self.server.rooms.authenticate(body.pop('code',''),self.headers.get('Authorization','').removeprefix('Bearer '))
                    action = body.pop('action','')
                    if not isinstance(action,str):
                        raise RuleError('Invalid action.')
                    s.action(i,action,**body)
                    self.server.rooms.dirty = True
                    result = dict(ok=True)
                else:
                    self.reply(dict(error='Not found'),404)
                    return
                self.server.rooms.save()
            self.reply(result)
        except (RuleError,ValueError,KeyError,TypeError,IndexError) as exc:
            self.reply(dict(error=str(exc)),400)


def make_server(host='127.0.0.1',port=8765,save_path=SAVE):
    server = ThreadingHTTPServer((host,port),Handler)
    server.rooms = Rooms(save_path)
    return server


def serve(server, open_browser=False):
    stopped = threading.Event()
    def loop():
        while not stopped.wait(.25):
            server.rooms.tick()
    worker = threading.Thread(target=loop,daemon=True)
    worker.start()
    if open_browser:
        webbrowser.open(f'http://127.0.0.1:{server.server_address[1]}')
    try:
        server.serve_forever()
    finally:
        stopped.set()
        worker.join(timeout=2)
        with server.rooms.lock:
            server.rooms.save()
        server.server_close()


def main(argv=None, open_browser=False):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--host',default='127.0.0.1',help='Use 0.0.0.0 to accept other computers.')
    parser.add_argument('--port',default=8765,type=int)
    browser = parser.add_mutually_exclusive_group()
    browser.add_argument('--open',dest='open',action='store_true')
    browser.add_argument('--no-open',dest='open',action='store_false')
    parser.set_defaults(open=open_browser)
    parser.add_argument('--save',type=Path,default=SAVE)
    args = parser.parse_args(argv)
    server = make_server(args.host,args.port,args.save)
    print(f'Tactical mode: http://{args.host}:{server.server_address[1]} (Ctrl+C to stop)')
    try:
        serve(server,args.open)
    except KeyboardInterrupt:
        pass


if __name__ == '__main__':
    main()
