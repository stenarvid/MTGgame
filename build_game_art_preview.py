"""Review proposed artwork with the live browser card renderer and layout CSS."""
import json
import re
from pathlib import Path
from tactical.content import CARD_MAP, COMMANDER_MAP, RELIC_MAP, KEYWORDS

ROOT=Path(__file__).resolve().parent


def build():
    destination=ROOT/'assets/art/direction-v3'
    game=(ROOT/'tactical/web/index.html').read_text(encoding='utf-8')
    base_css=re.search(r'<style>(.*?)</style>',game,re.S).group(1)
    cost=re.search(r'function manaCost[^\n]+',game).group(0)
    entries=json.loads((destination/'prompts.json').read_text())
    cards={key:dict(CARD_MAP[key]) for key in CARD_MAP}
    cards['commander_wu']=dict(id='commander',uid='preview-commander',owner=0,name=COMMANDER_MAP['wu']['name'],
        color='W',kind='creature',cost=4,pips={'W':1,'U':1},attack=3,health=5,shown_attack=3,shown_health=5,
        text=COMMANDER_MAP['wu']['packages'][0]['description'],keywords=['Flying'])
    cards['relic_lens']=RELIC_MAP['lens']
    data=json.dumps(dict(entries=entries,cards=cards,commanders=COMMANDER_MAP,keywords=KEYWORDS))
    options=''.join(f'<option value="{e["key"]}">{e["name"]}</option>' for e in entries)
    overlay='''
    body{background:radial-gradient(ellipse at center,#3b5349,#142c31 60%,#101d29)!important}header{position:static}main{max-width:1100px}.preview-controls{margin-bottom:20px}.preview-layout{display:flex;gap:28px;align-items:flex-start;flex-wrap:wrap}.preview-layout>section{width:420px;max-width:100%;margin:0}.preview-layout .hand{margin:0}.preview-layout .cardgrid{display:flex;overflow:visible}.preview-layout .hand .card{width:190px;flex:0 0 190px}.preview-layout .board{display:flex}.preview-layout .board .card{width:135px;flex:0 0 135px}.frame-note{font-size:12px;color:#b5c2d1}.preview-controls label{margin-right:14px}.preview-layout .relic-choice{width:250px}.inspector-body>.card{width:320px;max-width:100%}.inspector-body>.card .illustration{height:250px!important}@media(max-width:850px){.preview-layout{gap:12px}.preview-layout>section{width:100%}.preview-layout .cardgrid{overflow:visible}.preview-layout .board .card{width:135px;flex-basis:135px}}
    '''
    script='''
    const state={commanders:Object.values(DATA.commanders),battle:{players:[{commander:'wu'}],keywords:DATA.keywords}},inspectionCards=new Map();
    const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
    const commander=id=>DATA.commanders[id];
    window.cardArtURL=key=>DATA.entries.find(e=>e.key===key)?.file||'';
    '''+cost+'''
    function render(){const key=document.querySelector('#sample').value,c={...DATA.cards[key]},condition=document.querySelector('#condition').value;
        c.tapped=condition==='exhausted';c.damage=condition==='damaged'&&c.kind==='creature'?1:0;
        let markup;
        if(key==='relic_lens'){markup='<section class="panel relic-choice"><h3>'+esc(c.name)+'</h3><img class="relic-art" src="relic_lens.png" alt="Focused Lens"><p>'+esc(c.text)+'</p><button disabled>Choose relic</button></section>';}
        else{const extra=key==='commander_wu'?'<button class="smallbtn" disabled>Use ability</button>':'';
            markup='<section class="panel hand"><h3>Your hand · 190 px</h3><div class="cardgrid">'+cardHTML(c)+'</div></section><section class="panel"><h3>Battlefield · 135 px</h3><div class="board">'+cardHTML(c,'',extra)+'</div></section>';}
        document.querySelector('#cards').innerHTML=markup;
        if(key==='commander_wu')document.querySelectorAll('#cards .card').forEach(x=>x.classList.add('commander','dual'));
        document.querySelector('#condition').disabled=c.kind!=='creature';
    }
    function inspect(key){const c=inspectionCards.get(key),dialog=document.querySelector('#artInspector');dialog.innerHTML='<div class="inspector-top"><h2>'+esc(c.name)+'</h2><button id="close">Close</button></div><div class="inspector-body">'+cardHTML(c)+'<div>'+(c.keywords||[]).map(k=>'<p><b>'+esc(k)+'</b>: '+esc(DATA.keywords[k])+'</p>').join('')+'</div></div>';dialog.querySelectorAll('.art-inspect').forEach(x=>x.remove());dialog.querySelector('#close').onclick=()=>dialog.close();dialog.showModal();}
    document.querySelector('#sample').onchange=render;document.querySelector('#condition').onchange=render;
    document.querySelector('#cards').onclick=e=>{const key=e.target.closest('[data-action]')?.dataset.action;if(key?.startsWith('inspect:'))inspect(key.slice(8));};
    installCardHover(document.querySelector('#cards'));render();
    '''
    page='''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>In-game card appearance review</title><style>'''+base_css+'''</style><link rel="stylesheet" href="../../../tactical/web/style.css"><style>'''+overlay+'''</style><header><h1>In-game card appearance</h1></header><main><p>Uses the game's real card renderer, typography, artwork windows, rules, stats and Inspect controls. Hover over a card to enlarge it. Use Ctrl+0 for 100% zoom.</p><p class="frame-note">Proposed artwork and identity frames are previewed here. Hand cards are 190 px wide; battlefield cards are 135 px. Battlefield cards show artwork and stats; hover reveals the full card over a black fade. Colored mana symbols replace letters.</p><div class="panel preview-controls"><label>Sample <select id="sample">'''+options+'''</select></label><label>State <select id="condition"><option value="ready">Ready</option><option value="exhausted">Exhausted</option><option value="damaged">1 damage</option></select></label></div><div id="cards" class="preview-layout"></div></main><dialog id="artInspector"></dialog><script>const DATA='''+data+';'+script.split('    function render()')[0]+'''</script><script src="../../../tactical/web/cards.js"></script><script src="../../../tactical/web/card-hover.js"></script><script>function render()'''+script.split('    function render()',1)[1]+'''</script></html>'''
    (destination/'game.html').write_text(page,encoding='utf-8')
    print(destination/'game.html')


if __name__=='__main__':build()
