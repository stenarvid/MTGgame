"""Build the approved six-subject art review without changing the live game."""
import html
import json
from pathlib import Path
from tactical.content import CARD_MAP, COMMANDER_MAP, RELIC_MAP

ROOT=Path(__file__).resolve().parent
DEST=ROOT/'assets/art/direction-v2'
PALETTE={'W':'#ead6a3','U':'#69bcec','B':'#b493d4','R':'#f58564','G':'#81bd84','C':'#bd9971'}
MOTIFS={
    'W':'M6 3H22V14L14 24 6 14Z M10 10H18 M14 6V17',
    'U':'M3 10Q7 2 12 10T24 10 M3 17Q7 9 12 17T24 17',
    'B':'M5 23V10L14 2 23 10V23 M9 23V13L14 8 19 13V23',
    'R':'M6 23L10 16 6 13 14 2 15 11 23 7 19 17 23 23',
    'G':'M5 24Q13 16 14 5 M14 14Q3 15 4 5 13 5 14 14 M14 20Q24 21 25 10 16 10 14 20',
    'C':'M7 5H21L25 14 21 23H7L3 14Z M9 14H19',
}


def motif(color,side):
    return f'<svg class="motif {side}" viewBox="0 0 28 28" aria-hidden="true"><path d="{MOTIFS[color]}" stroke="{PALETTE[color]}"/></svg>'


def card(entry,size):
    key=entry['key']
    if key.startswith('commander_'):
        item=COMMANDER_MAP[key.removeprefix('commander_')]
        colors=item['colors'];kind='commander';cost='2 W U';stats='3 / 5'
        rules='Sky Formation: Flying; reinforce coordinated attacks.'
        short='Flying · Reinforcements'
    elif key.startswith('relic_'):
        item=RELIC_MAP[key.removeprefix('relic_')]
        colors=['C'];kind='relic';cost='Relic';stats='Persistent'
        rules=item['text'];short='Third spell → draw'
    else:
        item=CARD_MAP[key];colors=[item['color']];kind=item['kind']
        pips=sum(item['pips'].values());generic=item['cost']-pips
        cost=(str(generic)+' ' if generic else '')+''.join(c*n for c,n in item['pips'].items())
        stats=f"{item['attack']} / {item['health']}" if kind=='creature' else kind.title()
        rules=item['text'] or 'Early defensive creature.'
        short={'w_recruit':'Early defense','u_apprentice':'Early blue creature','w_shield':'Prevent creature damage','r_bolt':'3 damage · Any target'}.get(key, '3 damage to every creature')
    left,right=colors[0],colors[-1]
    name=item['name'] if size=='hand' else item['name'].split(',')[0]
    esc=html.escape
    crest='<span class="crest" aria-label="Commander crest">◆</span>' if kind=='commander' else ''
    text=rules if size=='hand' else short
    return f'''<article class="frame {size} identity-{left} {kind} {'dual' if len(colors)>1 else ''}" style="--left:{PALETTE[left]};--right:{PALETTE[right]}">
    <div class="card-face"><div class="motif-band">{motif(left,'left')}{crest}{motif(right,'right')}</div>
    <div class="title"><strong>{esc(name)}</strong><span class="cost">{esc(cost)}</span></div>
    <a class="art-link" href="{esc(entry['file'])}" title="Open full illustration"><img src="{esc(entry['file'])}" alt="{esc(item['name'])} illustration"></a>
    <div class="rules">{esc(text)}</div><div class="stats"><span>{'Commander' if kind=='commander' else 'Artifact' if kind=='relic' else kind.title()}</span><b>{esc(stats)}</b></div></div></article>'''


def build(version='v2'):
    global DEST
    DEST=ROOT/('assets/art/direction-'+version)
    entries=json.loads((DEST/'prompts.json').read_text(encoding='utf-8'))
    sections=''.join(f'''<section class="sample"><h2>{html.escape(e['name'])}</h2><div class="sizes"><div><p class="label">Hand · 190 px</p>{card(e,'hand')}</div><div><p class="label">Battlefield · 135 px</p>{card(e,'battlefield')}</div></div><details><summary>Full illustration and art brief</summary><a href="{e['file']}"><img class="full-art" src="{e['file']}" alt="Full {html.escape(e['name'])} illustration"></a><p>{html.escape(e['prompt'])}</p></details></section>''' for e in entries)
    swatches=''.join(f'<div class="frame swatch identity-{c}" style="--left:{PALETTE[c]};--right:{PALETTE[c]}"><div class="card-face">{motif(c,"left")}<b>{name}</b>{motif(c,"right")}</div></div>' for c,name in [('W','White'),('U','Blue'),('B','Black'),('R','Red'),('G','Green'),('C','Neutral')])
    style='''
    *{box-sizing:border-box}body{margin:0;background:#0d1a28;color:#edf3f9;font:15px system-ui;line-height:1.45}header{padding:28px 32px;background:#152b3b;border-bottom:2px solid #54718a}h1{font-size:28px;margin:0 0 12px}header p{max-width:1000px;margin:8px 0;color:#c6d6e3}main{padding:24px 32px}h2{font-size:18px;margin:0 0 14px}.sample-grid{display:grid;grid-template-columns:repeat(3,minmax(370px,1fr));gap:20px}.sample{padding:18px;background:#162b3b;border:1px solid #4c687c;border-radius:12px}.sizes{display:flex;align-items:flex-start;gap:18px;justify-content:center}.label{font-size:12px;margin:0 0 10px;color:#b9d0de}.frame{position:relative;padding:3px;background:linear-gradient(90deg,var(--left) 0 50%,var(--right) 50% 100%);border-radius:8px;color:#ecf3fa;flex-shrink:0;filter:drop-shadow(0 5px 6px #0005)}.card-face{background:#102332;border-radius:5px;position:relative;overflow:hidden}.frame.hand{width:190px}.frame.battlefield{width:135px;padding:2px}.identity-W{clip-path:polygon(7px 0,calc(100% - 7px) 0,100% 7px,100% calc(100% - 10px),calc(100% - 10px) 100%,10px 100%,0 calc(100% - 10px),0 7px)}.identity-U{border-radius:17px 5px 17px 5px}.identity-U .card-face{border-radius:14px 3px 14px 3px}.identity-B{clip-path:polygon(0 9px,9px 9px,9px 0,calc(100% - 9px) 0,calc(100% - 9px) 9px,100% 9px,100% calc(100% - 9px),calc(100% - 9px) calc(100% - 9px),calc(100% - 9px) 100%,9px 100%,9px calc(100% - 9px),0 calc(100% - 9px))}.identity-R{clip-path:polygon(0 8px,6px 8px,10px 0,calc(100% - 10px) 0,calc(100% - 6px) 8px,100% 8px,100% calc(100% - 8px),calc(100% - 8px) 100%,8px 100%,0 calc(100% - 8px))}.identity-G{border-radius:20px 8px 20px 8px}.identity-G .card-face{border-radius:17px 6px 17px 6px}.identity-C{border-radius:5px}.dual{clip-path:none;border-radius:10px 7px 16px 7px}.dual .card-face{border-radius:7px 4px 13px 4px}.motif-band{position:relative;height:22px;background:#0a1925}.motif{width:22px;height:22px;position:absolute;top:0;fill:none;stroke-width:2;stroke-linecap:round;stroke-linejoin:round}.motif.left{left:4px}.motif.right{right:4px}.crest{position:absolute;left:calc(50% - 13px);top:0;width:26px;height:24px;display:grid;place-items:center;background:linear-gradient(90deg,var(--left) 0 50%,var(--right) 50%);color:#112232;font-size:20px;clip-path:polygon(50% 100%,0 50%,0 0,100% 0,100% 50%)}.commander{padding:4px}.commander .motif-band{height:26px}.relic .motif-band{background:#352c22}.relic .art-link{border:2px solid #997d5e;border-radius:18px 18px 5px 5px;margin:0 7px;overflow:hidden}.title{min-height:48px;display:flex;gap:6px;align-items:center;padding:6px 7px;font-size:12px;line-height:1.15}.title strong{flex:1}.cost{white-space:nowrap;color:#f6e4b9;font-size:11px;font-weight:700;padding:3px;background:#081724;border-radius:3px}.art-link{display:block;margin:0 5px;background:#0a1721}.art-link img{width:100%;height:165px;object-fit:cover;object-position:center 28%;display:block}.commander .art-link img{object-position:center 15%}.rules{margin:7px 6px 0;padding:7px;background:#19374a;border-radius:3px;font-size:11px;min-height:78px;color:#e9f1f7}.stats{display:flex;justify-content:space-between;align-items:center;padding:9px 7px;font-size:10px}.stats b{font-size:13px;color:#ffe8b2}.battlefield .motif-band{height:15px}.battlefield .motif{width:15px;height:15px}.battlefield .crest{width:19px;height:18px;left:calc(50% - 9px);font-size:14px}.battlefield .title{min-height:35px;font-size:10px;padding:4px}.battlefield .cost{font-size:9px;padding:2px}.battlefield .art-link img{height:82px}.battlefield .rules{font-size:9px;padding:4px;margin:5px 4px 0;min-height:34px}.battlefield .stats{font-size:8px;padding:5px}.battlefield .stats b{font-size:11px}.swatches{display:flex;gap:14px;flex-wrap:wrap;margin:16px 0 24px}.swatch{width:155px;height:64px}.swatch .card-face{height:58px;display:grid;place-items:center;font-size:12px}.swatch .motif{top:18px}.note{background:#153c3a;padding:12px 18px;border-left:4px solid #91dbbf;max-width:1200px}details{margin-top:18px;font-size:12px;color:#c5d7e4}summary{cursor:pointer}.full-art{width:100%;margin-top:12px}footer{padding:24px 32px;color:#adc1d1;font-size:12px}a{color:#b7e4ff}@media(max-width:1200px){.sample-grid{grid-template-columns:repeat(2,minmax(370px,1fr))}}@media(max-width:800px){main,header{padding:18px 12px}.sample-grid{grid-template-columns:1fr}.sample{padding:14px 10px}.sizes{gap:12px}}
    '''
    page=f'''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Commander Spire — art direction review</title><style>{style}</style><header><h1>Art direction review · {len(entries)} samples</h1><p>Polished anime rendering, crafted equipment, clear silhouettes and color-identity borders. Area spells make the environment their subject.</p><p>Elya's sun-disk kite shields connect her to the white recruit; her wave-tip baton connects her to the blue apprentice. The commander frame splits white/blue equally at its center.</p></header><main><p class="note">Preview only. The live game's artwork and frames have not been replaced. Compare at these actual CSS card widths; open an illustration for the full composition.</p><h2>Frame language · all six identities</h2><div class="swatches">{swatches}</div><div class="sample-grid">{sections}</div></main><footer>Illustrations generated individually with the built-in image tool. Frames use HTML/CSS and original vector motifs. Exact prompts: <a href="prompts.json">prompts.json</a>.</footer></html>'''
    (DEST/'index.html').write_text(page,encoding='utf-8')
    print('Review:',DEST/'index.html')


if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument('--version',choices=['v2','v3'],default='v2')
    build(parser.parse_args().version)
