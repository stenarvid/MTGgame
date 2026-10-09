"""Real-browser smoke test; uses installed Edge and Node, no extra packages.

Run python tests/capture_tactical.py. Screenshots go to artifacts/tactical-*.png.
"""
import os
import json
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
        fixture_path = Path(tmp)/'qol-fixtures.json'
        if '--qol' in sys.argv:
            from tactical.content import COMMANDERS, CARDS, legal
            fixtures = {}
            for name in ('build','battle'):
                auth = server.rooms.create(dict(mode='solo',name='QOL '+name,difficulty='custom',modifier_nodes=0))
                s = server.rooms.rooms[auth['code']]['session']
                s.start(0);s.members[0]['offers']=[COMMANDERS[0]['id']]
                s.choose_commander(0,COMMANDERS[0]['id'],0)
                while s.stage == 'draft':s.action(0,'pick',index=0)
                s.members[0]['relic_options']=['reserves']
                s.action(0,'relic',relic='reserves')
                s.currency=12;s.members[0]['essence']=1
                s.members[0]['owned'].extend(c['id'] for c in CARDS if legal(c['id'],s.colors(0)))
                s.add_item(s.members[0],'roots',1);s.add_item(s.members[0],'roots',2)
                s.setup_shop();s.award_treasure(True);s.ensure_map()
                s.reports=[dict(seconds=60,turns=[2,2],spectator_seconds=[0,0])]
                if name == 'battle':
                    s.action(0,'ready');b=s.battle
                    for p in b.players:p['kept']=True
                    b.active=b.priority=0;b.phase='main'
                    for p in b.players:
                        p['capacity']={p['colors'][0]:5};p['mana']={c:5 for c in 'WUBRG'}
                    b.players[0]['hand']=[b.instance('u_return',0),b.instance('r_bolt',0)]
                    for i in (0,1):
                        c=b.instance('w_recruit',i);c['sick']=False
                        if i:c['keywords']=['Ward','Flying']
                        b.players[i]['board']=[c]
                        b.players[i]['grave']=[b.instance('w_patrol',i)]
                        b.players[i]['exile']=[b.instance('w_medic',i)]
                    # These isolated fixtures deliberately wait for human actions.
                    s.ai_since=time.time()+3600
                fixtures[name]=auth
            fixture_path.write_text(json.dumps(fixtures),encoding='utf-8')
        if '--items' in sys.argv or '--priority' in sys.argv:
            from tactical.content import COMMANDER_MAP
            fixtures = {}
            for name in ('build', 'battle'):
                auth = server.rooms.create(dict(mode='solo',name='Item review '+name))
                s = server.rooms.rooms[auth['code']]['session']
                s.start(0);s.members[0]['offers']=['wu'];s.choose_commander(0,'wu',0)
                while s.stage == 'draft':s.action(0,'pick',index=0)
                m=s.members[0];m['relic_options']=['reserves'];s.action(0,'relic',relic='reserves')
                s.currency=30;m['essence']=30
                m['gem_unlocks']=dict.fromkeys(('might','brood','vitality','binding','guardian','bastion'),2)
                for design in ('spiresteel_blade','spiresteel_blade','smith_insignia'):
                    s.add_item(m,design,2)
                for design in ('healing_draught','mistveil_vial'):
                    supply=s.add_consumable(m,design)
                    s.action(0,'pouch',uid=supply['uid'],slot=0 if design=='healing_draught' else 1)
                if name == 'battle':
                    blades=[x for x in m['items'] if x['design']=='spiresteel_blade']
                    blades[0]['gems']={'binding':2}
                    m['deck'][-2:]=['gear:'+x['uid'] for x in blades]
                    s.action(0,'ready');b=s.battle
                    for p in b.players:
                        p['kept']=True;p['completed_turn']=True
                        p['mana']={color:8 for color in 'WUBRG'}
                        p['capacity']={color:3 for color in p['colors']}
                    b.active=b.priority=0;b.phase='main';b.players[0]['hp']=17
                    b.players[0]['board']=[b.instance('w_spire_recruit',0)]
                    b.players[0]['hand']=[b.instance('gear:'+x['uid'],0) for x in blades]
                    b.players[1]['board']=[b.instance('r_duelist',1)]
                    b.players[1]['mana']={}
                    b.players[1]['pouch']=[]
                    s.ai_since=0
                fixtures[name]=auth
            fixture_path.write_text(json.dumps(fixtures),encoding='utf-8')
        if '--priority' in sys.argv:
            import copy, secrets
            auth = server.rooms.create(dict(mode='solo',name='Response timing'))
            response = copy.deepcopy(s)
            response.mode='human'
            for member in response.members:
                member['bot']=False
                member['auto']=member['seat']==0
            rb=response.battle
            rb.phase='main';rb.active=rb.priority=1;rb.stack=[];rb.choice=None;rb.passes=0
            for player in rb.players:
                player['hp']=25;player['hand']=[];player['pouch']=[];player['board']=[]
                player['mana']={'U':8,'R':8};player['capacity']={'U':4,'R':4}
            rb.players[0]['hand']=[rb.instance('u_counter',0)]
            rb.players[1]['hand']=[rb.instance('r_bolt',1),rb.instance('r_bolt',1)]
            server.rooms.rooms[auth['code']]['session']=response
            token=secrets.token_urlsafe(32)
            server.rooms.rooms[auth['code']]['tokens'][token]=1
            fixtures['response']=auth
            fixtures['response_friend']=dict(code=auth['code'],token=token)
            for name in ('transitions', 'triggers'):
                extra_auth=server.rooms.create(dict(mode='solo',name='Priority '+name))
                extra=copy.deepcopy(response);eb=extra.battle
                eb.phase='main';eb.active=eb.priority=0;eb.stack=[];eb.choice=None;eb.passes=0
                for member in extra.members:
                    member['auto']=name=='transitions'
                    member['hold_priority']=False
                    member['auto_order']=name=='transitions'
                for player in eb.players:
                    player['hand']=[];player['board']=[];player['pouch']=[];player['equipment']=[];player['relic']=None
                if name=='triggers':
                    victim=eb.instance('b_shambler',0);victim['damage']=victim['health']
                    watcher=eb.instance('b_collector',0)
                    eb.mark_entry(watcher);eb.mark_entry(victim)
                    eb.players[0]['board']=[watcher,victim]
                    eb.auto_order={'0':False,'1':True}
                    eb.push(0,'heal',amount=1,name='Trigger cause')
                    eb.action(0,'pass');eb.action(1,'pass')
                server.rooms.rooms[extra_auth['code']]['session']=extra
                fixtures[name]=extra_auth
            fixture_path.write_text(json.dumps(fixtures),encoding='utf-8')
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
            debug_port = None
            for _ in range(100):
                try:
                    debug_port = port_file.read_text().splitlines()[0]
                    break
                except (OSError, IndexError):
                    time.sleep(.1)
            if not debug_port:raise RuntimeError('Browser debugger did not start')
            script='priority_browser.mjs' if '--priority' in sys.argv else 'items_browser.mjs' if '--items' in sys.argv else 'qol_browser.mjs' if '--qol' in sys.argv else 'tutorial_browser.mjs' if '--tutorial' in sys.argv else 'tactical_browser.mjs'
            subprocess.run(['node',str(ROOT/'tests'/script),
                f'http://127.0.0.1:{server.server_address[1]}',debug_port,*([str(fixture_path)] if '--qol' in sys.argv or '--items' in sys.argv or '--priority' in sys.argv else [])],check=True,cwd=ROOT)
        finally:
            stopped.set();ticker.join(timeout=2)
            server.shutdown();server.server_close();worker.join(timeout=2)
            browser.terminate()
            try:browser.wait(timeout=10)
            except subprocess.TimeoutExpired:browser.kill();browser.wait()


if __name__ == '__main__':main()
