"""Isolated, in-memory card review using the production Battle rules."""
import argparse
import copy
import json
from http.server import ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse
from .battle import Battle, RuleError
from .content import COMMANDERS, KEYWORDS, starter, CARD_MAP
from .server import Handler, ROOT

SCENARIOS={
 'summon':'Creature arrival: cast Citadel Recruit and let it resolve',
 'commanderarrival':'Commander arrival: cast your commander from the command zone',
 'arrivalcounter':'Interrupted arrival: counter the pending creature',
 'firecounter':'Counter Fireball: extinguish the pending charge',
 'combatanim':'Blocked attack: declare blockers, then resolve combat',
 'exile':'Exile: choose a large creature for Equal Judgment',
 'bounce':'Return: send a creature back to its hand',
 'main':'Main phase: inspect, choose abilities, and confirm costs',
 'fire':'Fireball: flame targeting, crackle and a scorched impact',
 'meteors':'Meteor Rain: a shower over every creature',
 'grow':'Turn start: choose a mana gem within your commander identity',
 'combat':'Combat: choose Attack or Ability',
 'blocks':'Defense: choose Block or Ability',
 'response':'Respond to an opponent with protection or an instant',
 'invalid':'Bounce a targeted creature before the ability resolves',
 'source':'Remove an ability source; its pending effect remains',
 'buffs':'Inspect stacked buffs, damage and exhaustion',
}

def ability(name,effect,timing='instant',target=None,cost=1,amount=1,**extra):
    return dict(name=name,effect=effect,timing=timing,target=target,cost=cost,amount=amount,exhaust=True,
                description=extra.pop('description',name),**extra)


def fixture(scenario='main'):
    if scenario not in SCENARIOS: raise RuleError('Unknown review scenario.')
    builds=[dict(name=name,commander=cmd,package=0,relic='reserves',deck=starter(['W','U','B','R','G']))
            for name,cmd in [('You','wu'),('Mira','tide')]]
    b=Battle(builds,seed=42)
    b.phase='main'
    for p in b.players:
        p.update(completed_turn=True,turns=2,capacity={k:2 for k in 'WUBRG'},mana={k:1 for k in 'WUBRG'},hand=[],board=[],kept=True)
    b.players[0].update(capacity={'W':5,'U':5},mana={'W':3,'U':2})
    b.players[1].update(capacity={'U':10},mana={'U':5})
    if scenario=='grow':
        b.phase='grow';b.players[0].update(capacity={'W':2,'U':2},mana={'W':2,'U':2})
    def unit(id,owner,abilities=()):
        c=b.instance(id,owner);c['sick']=False;c['abilities']=list(abilities);b.players[owner]['board'].append(c);return c
    commander=b.instance('wu',0,commander=True);commander.update(sick=False,text='Flying. Coordinate allies or protect a creature.',keywords=['Flying'],abilities=[
        ability('Rally formation','buff','main','friendly',2,2,description='Exhaust and pay 2 mana: a friendly creature gets +2/+2 until its next turn.'),
        ability('Shield response','protect','response','friendly',1,description='Exhaust and pay 1 mana: prevent damage to a friendly creature until end of turn.')])
    b.players[0]['board'].append(commander)
    recruit=unit('w_recruit',0,[ability('Hold the line','protect','instant','friendly',1,description='Exhaust and pay 1 mana: prevent damage to a friendly creature this turn.')])
    apprentice=unit('u_apprentice',0,[ability('Focused study','draw','main',None,1,description='Exhaust and pay 1 mana: draw one card.')])
    # Isolated review names preserve the requested reference labels.
    commander.update(name='You - Decision Pending',attack=3,health=2,printed_attack=3,printed_health=2)
    recruit.update(attack=3,health=5,printed_attack=3,printed_health=5)
    apprentice['attack']=1;apprentice['health']=3
    for _ in range(6):
        token=unit('w_recruit',0);token.update(token=True,name='Recruit',attack=1,health=1,printed_attack=1,printed_health=1)
    aside=unit('u_glider',1);aside.update(name='Aside',attack=3,health=2,printed_attack=3,printed_health=2)
    guard=unit('w_patrol',1);guard['name']='Guard'
    attacker=unit('r_duelist',1,[ability('Ember shot','damage','instant','any',1,2,description='Exhaust and pay 1 mana: deal 2 damage to a creature or player.')])
    attacker['name']='Boit'
    for i in range(2):
        b.players[i]['hand']=[b.instance(id,i) for id in ('w_shield','u_return','r_bolt','w_rally','u_counter')]
    for player in b.players:
        for card in player['hand']:
            card['name']={'w_shield':'Media formation','u_return':'Turn Aside','r_bolt':'Waging Bolt','w_rally':'Pnited Front','u_counter':'NuR Sigil'}.get(card['id'],card['name'])
    if scenario in ('fire','meteors'):
        b.players[0].update(commander='br',colors=['B','R'],capacity={'B':3,'R':5},mana={'B':3,'R':5})
        fire=b.instance('r_bolt' if scenario=='fire' else 'r_wipe',0)
        fire['name']='Fireball' if scenario=='fire' else 'Meteor Rain'
        b.players[0]['hand']=[fire]
    if scenario in ('summon','commanderarrival','arrivalcounter'):
        b.players[0]['board']=[recruit,apprentice]
        b.players[0]['commander_zone']='command'
        b.players[0]['hand']=[b.instance('w_recruit',0)]
        if scenario=='commanderarrival':b.players[0]['hand']=[]
        if scenario=='arrivalcounter':
            incoming=b.players[0]['hand'][0]
            b.action(0,'cast',uid=incoming['uid']);b.priority=1
    if scenario=='firecounter':
        b.players[0].update(commander='br',colors=['B','R'],capacity={'B':3,'R':5},mana={'B':3,'R':5})
        incoming=b.instance('r_bolt',0);incoming['name']='Fireball';b.players[0]['hand']=[incoming]
        b.action(0,'cast',uid=incoming['uid'],target=aside['uid']);b.priority=1
    if scenario=='combatanim':
        b.players[0]['board']=[recruit];b.players[1]['board']=[attacker]
        b.players[0]['hand']=[];b.players[1]['hand']=[]
        b.phase='blocks';b.active=1;b.defenders=[0];b.attacks=[dict(uid=attacker['uid'],defender=0)];attacker['tapped']=True
        b.blocked=[]
    if scenario=='exile':
        b.players[0]['hand']=[b.instance('w_exile',0)]
    if scenario=='bounce':
        b.players[0]['hand']=[b.instance('u_return',0)]
    if scenario=='combat': b.phase='combat'
    if scenario=='blocks':
        b.phase='blocks';b.active=1;b.defenders=[0];b.attacks=[dict(uid=attacker['uid'],defender=0)];attacker['tapped']=True
    if scenario=='response':
        b.active=1;b.phase='main';b.push(1,'damage',recruit['uid'],3,name='Ember shot',source=attacker)
        b.stack[-1].update(source_uid=attacker['uid'],target_kind='any')
    if scenario=='invalid':
        b.priority=1;b.action(1,'ability',uid=attacker['uid'],ability=0,target=recruit['uid']);b.priority=0
    if scenario=='source':
        b.priority=0;b.action(0,'ability',uid=recruit['uid'],ability=0,target=apprentice['uid']);b.priority=1
        b.players[1]['hand'].append(b.instance('b_kill',1))
    if scenario=='buffs':
        recruit.update(attack=1,health=3,printed_attack=1,printed_health=3)
        for n in (1,1,2): b.resolve(dict(owner=0,effect='buff',amount=n,target=recruit['uid'],card=None,kind='ability',name='Formation lesson'))
        b.resolve(dict(owner=0,effect='protect',amount=1,target=recruit['uid'],card=None,kind='ability',name='Hold Formation'))
        recruit['buffs'].append(dict(name='Marked',effect='Public warning marker (no stat change)',source='Review annotation',duration='This scenario',icon='mark',debuff=True))
        recruit.update(damage=1,tapped=True)
    b.note('Review fixture only. Use Pass to hand priority to the next player; all players must pass to resolve.')
    return b


class PreviewHandler(Handler):
    def do_GET(self):
        path=urlparse(self.path).path
        if path=='/api/preview':
            with self.server.preview_lock: self.reply(self.snapshot())
            return
        if path in ('/','/preview.js','/preview.css','/arena-review.css','/temple-review.css'):
            file={'/':'preview.html','/preview.js':'preview.js','/preview.css':'preview.css','/arena-review.css':'arena-review.css','/temple-review.css':'temple-review.css'}[path]
            data=(ROOT/'web'/file).read_bytes();self.send_response(200)
            self.send_header('Content-Type',('text/html' if file.endswith('html') else 'text/css' if file.endswith('css') else 'text/javascript')+'; charset=utf-8')
            self.send_header('Cache-Control','no-store');self.send_header('Content-Length',str(len(data)));self.end_headers();self.wfile.write(data);return
        if path in ('/review-table.png','/temple-table.png'):
            file='temple-table.png' if path=='/temple-table.png' else 'review-table.png'
            data=(ROOT.parent/'assets/art'/file).read_bytes();self.send_response(200);self.send_header('Content-Type','image/png');self.send_header('Content-Length',str(len(data)));self.end_headers();self.wfile.write(data);return
        if path.startswith('/preview-art/'):
            key=path.removeprefix('/preview-art/')
            folder=ROOT.parent/'assets/art/direction-v3'
            entries=json.loads((folder/'prompts.json').read_text())
            entry=next((e for e in entries if e['key']==key),None)
            if entry:
                data=(folder/entry['file']).read_bytes();self.send_response(200);self.send_header('Content-Type','image/png');self.send_header('Content-Length',str(len(data)));self.end_headers();self.wfile.write(data);return
        super().do_GET()

    def snapshot(self):
        b=self.server.preview_battle
        viewer=0 if self.server.preview_present else b.priority
        commander_card=None
        if b.players[viewer]["commander_zone"]=="command":
            commander_card=copy.deepcopy(b).instance(b.players[viewer]["commander"],viewer,commander=True)
            commander_card["uid"]="commander"
        return dict(commander_card=commander_card,battle=b.view(viewer),viewer=viewer,presentation=self.server.preview_present,commanders=COMMANDERS,scenario=self.server.preview_scenario,scenarios=SCENARIOS,auto_responses=self.server.preview_auto)

    def do_POST(self):
        if self.path!='/api/preview': self.reply(dict(error='Review endpoint only'),404);return
        try:
            length=int(self.headers.get('Content-Length','0'))
            if not 0<length<=16384: raise RuleError('Invalid request size')
            data=json.loads(self.rfile.read(length))
            with self.server.preview_lock:
                if data.get('action')=='reset':
                    scenario=data.get('scenario','main');b=fixture(scenario)
                    self.server.preview_present=bool(data.get('presentation',self.server.preview_present))
                    self.server.preview_battle=b;self.server.preview_scenario=scenario
                else:
                    # A rejected action cannot partially change this review fixture.
                    b=copy.deepcopy(self.server.preview_battle)
                    action=data.pop('action')
                    if action=='review_reply' and self.server.preview_present and b.priority!=0:
                        counter=next((c for c in b.players[b.priority]['hand'] if c['effect']=='counter' and b.stack and b.castable(b.priority,c,b.stack[-1]['uid'])),None)
                        if self.server.preview_scenario in ('firecounter','arrivalcounter') and counter:
                            b.action(b.priority,'cast',uid=counter['uid'],target=b.stack[-1]['uid'])
                        else:b.action(b.priority,'pass')
                    elif action=='auto_responses':
                        self.server.preview_auto=bool(data.get('enabled'))
                    elif action=='end_turn':
                        if b.priority!=b.active or b.phase not in ('main','main2') or b.stack:
                            raise RuleError('End turn requires your main phase and no pending actions.')
                        b.phase='end';b.passes=0;b.note('End turn requested; both players may respond before the turn ends.')
                    else: b.action(b.priority,action,**data)
                    if self.server.preview_auto: b.auto_pass_unavailable()
                    self.server.preview_battle=b
                self.reply(self.snapshot())
        except (RuleError,ValueError,KeyError,TypeError,IndexError) as exc: self.reply(dict(error=str(exc)),400)


def make_preview_server(port=8767):
    import threading
    server=ThreadingHTTPServer(('127.0.0.1',port),PreviewHandler)
    server.preview_present=False;server.preview_auto=True;server.preview_lock=threading.RLock();server.preview_battle=fixture();server.preview_scenario='main'
    return server


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--port',type=int,default=8767);args=parser.parse_args()
    server=make_preview_server(args.port)
    print(f'Card review: http://127.0.0.1:{server.server_address[1]}',flush=True)
    try: server.serve_forever()
    except KeyboardInterrupt: pass
    finally: server.server_close()

if __name__=='__main__': main()
