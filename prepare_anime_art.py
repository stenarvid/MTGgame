"""Build the complete prompt inventory; raster generation uses built-in imagegen."""
import hashlib
import json
from artwork_catalog import ROOT, design_filename
from tactical.content import CARDS, COMMANDERS, RELICS

STYLE = ('Original high fantasy 2D ANIME illustration, clearly cartoony animation art. Clean confident outlines, bold graphic shapes, mostly flat cel shading with two or three shadow tones. '
         'Expressive stylized anime faces and dramatic poses; no realistic skin texture, photorealism, 3D render or intricate armor filigree. '
         'One dominant subject or action with a clear silhouette readable at small card size. Softly painted simplified background and luminous magical effects. '
         'Portrait composition, keep the focal subject in the central region and leave faces comfortably inside framing. No text, lettering, border, watermark or UI. ')
COLORS = {'W':'Ivory, gold, protective light, coordinated formations and sunlit citadels.',
          'U':'Azure and silver, water, reflections, arcane knowledge and coastal architecture.',
          'B':'Violet, obsidian and spectral teal, sacrifice, resurrection and gothic ruins; no gore.',
          'R':'Crimson, copper and ember orange, speed, fragile aggression and explosive fire.',
          'G':'Emerald, moss and warm wood, durable beasts, growing resources and ancient forests.',
          'C':'Pearl and weathered bronze with prismatic accents, readable magical artifacts and neutral utility.'}

def silhouette_brief(key, name, kind):
    """Keep adjacent designs distinct instead of defaulting to one ornate mage."""
    seed=int(hashlib.sha256(key.encode()).hexdigest()[:8],16)
    if kind in ('relic','engine','land','environment'):
        return 'The literal named object or landscape must be recognizable. Do not substitute a generic glowing orb. '
    if kind in ('spell','response','Instant Spell','Enchantment','Sorcery'):
        return ('ACTION SCENE, not a portrait: the effect is the dominant silhouette. '
                'Use a close composition of the transformation, impact, protection or exchange described below. '
                'Any caster is secondary, seen from the side or behind; avoid a front-facing ornate woman reaching at the viewer. ')
    lowered=name.lower()
    creatures={
        'ghoul':'a lanky undead male ghoul, hunched, ragged cloak, clawed hands',
        'shambler':'a heavy stooped undead creature, stitched robe and oversized hands',
        'larva':'a small iridescent caterpillar with a faceted shell, no humanoid body',
        'broodmother':'a formidable spider queen tending spectral eggs, eight-legged silhouette',
        'beast':'a broad four-legged fantasy beast, oversized paws and distinctive horns',
        'plant':'a tiny animate seedling, leafy limbs and a bulb-shaped body',
        'spark':'a tiny lively flame elemental, no human face or armor',
        'spirit':'a floating translucent spirit with a tapered ethereal body',
        'colossus':'a towering moss-covered stone giant with broad block-shaped limbs',
        'guardian':'a robust broad-shouldered defender with a massive shield and simple tabard',
        'sentinel':'an imposing armored woodland golem with branch-shaped horns',
        'mourner':'a hooded elderly mourner holding a single memorial lantern',
        'gardener':'a stout elderly caretaker with a digging tool and bone-seed basket',
        'artificer':'a goggle-wearing workshop inventor, apron, gauntlets and a handheld device',
        'chronicler':'an elderly scribe with a scroll case and prominent feather pen',
        'harvester':'a tall masked reaper carrying a curved harvest blade',
        'rider':'a mounted fighter, with the mount integral to the silhouette',
        'duelist':'a nimble short-haired swordfighter in a practical dueling jacket',
        'medic':'a gentle adult healer wearing a simple field apron and carrying bandages',
        'courier':'a lean running messenger with a messenger satchel and short cape',
        'savant':'an eccentric adult scholar with round glasses and floating study diagrams',
    }
    for word,subject in creatures.items():
        if word in lowered:return 'Required subject silhouette: '+subject+'. '
    identities=['a sturdy adult man with short dark hair and a strong square face',
                'an adult woman with short curly hair and expressive brows',
                'an elderly man with tied-back silver hair and a long mustache',
                'an adult horned fantasy warrior with warm dark skin',
                'a tall adult elf with a long braided ponytail',
                'a stocky adult dwarf with a broad face and cropped red hair',
                'an adult woman with dark skin, a high bun and an angular face',
                'a slim adult man with long teal hair and narrow eyes']
    poses=['a clear side profile in motion','a low three-quarter stance',
           'a confident upright full-body pose','a back-three-quarter pose looking over one shoulder']
    return ('Required distinct subject: '+identities[seed%len(identities)]+'. '+poses[(seed//8)%len(poses)]+'. '
            'Use practical equipment appropriate to this exact role, a simple costume and strong readable outline. '
            'Do not reuse the long-haired ornate female mage silhouette. ')

def build_catalog():
    manifest=ROOT/'assets/art/anime/manifest.json'
    previous=json.loads(manifest.read_text(encoding='utf-8')) if manifest.exists() else {}
    catalog={}
    def add(key,name,kind,colors,text,details=None):
        palette=' '.join(COLORS[c] for c in dict.fromkeys(colors) if c in COLORS)
        brief=f'Subject: {name}. Design type: {kind}. Exact gameplay concept: {text}. '
        if details:brief+='Illustrate these mechanics, never print them: '+json.dumps(details)+'. '
        prompt=STYLE+silhouette_brief(key,name,kind)+brief+palette
        catalog[key]=dict(name=name,kind=kind,colors=list(dict.fromkeys(colors)),text=text,
                          file=design_filename(key),prompt=prompt)
    for card in CARDS:
        add(card['id'],card['name'],card['kind'],card['color'],
            card['text'] or ', '.join(card['keywords']),
            {key:card[key] for key in ('attack','health','effect') if key in card})
    for commander in COMMANDERS:
        add('commander_'+commander['id'],commander['name'],'commander',commander['colors'],
            ' / '.join(package['description'] for package in commander['packages']))
    for relic in RELICS:
        add('relic_'+relic['id'],relic['name'],'relic','C',relic['text'])
    add('token_recruit','Recruit','token','W','Modest 1/1 militia recruit with a small shield.')
    scene=('Wide high fantasy anime floating citadels above a forest and ocean at sunset. '
           'Bold readable architectural shapes, clean linework, softly painted sky. '
           'Large quiet low-detail center and left for interface text; magical towers at edges.')
    add('environment','environment','environment',[],scene)
    catalog['environment']['prompt']='Cartoony 2D anime animation background, wide landscape. '+scene+' No text, lettering, characters, borders or UI.'
    # Preserve the exact prompts and metadata of already completed illustrations.
    for key,entry in catalog.items():
        if key in previous and (ROOT/'assets/art'/entry['file']).is_file():
            entry.update(previous[key])
    manifest.parent.mkdir(parents=True,exist_ok=True)
    manifest.write_text(json.dumps(catalog,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    return catalog

if __name__=='__main__':
    print('Anime catalog:',len(build_catalog()),'distinct designs')
