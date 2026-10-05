"""Remove verified superseded artwork and the explicitly retired desktop mode."""
import argparse
import hashlib
import json
import shutil
from pathlib import Path
from artwork_catalog import ROOT, ART_ROOT

LEGACY_CODE=['anime_artwork.py','arena_ui.py','art.py','battlefield_piles.py',
             'card_interaction.py','engine.py','identity_rules.py','models.py',
             'persistence.py','rendering.py','spell_rules.py','trigger_rules.py','ui_panels.py']
LEGACY_TESTS=['test_arena.py','test_command_zone.py','test_content.py','test_engine.py',
              'test_expansion.py','test_game.py','test_identity.py','test_morph.py']


def safe_path(relative):
    path=(ROOT/relative).resolve()
    if not path.is_relative_to(ROOT.resolve()) or path==ROOT.resolve():
        raise ValueError('Unsafe cleanup target: '+str(relative))
    return path


def verify_catalog():
    catalog=json.loads((ART_ROOT/'anime/manifest.json').read_text(encoding='utf-8'))
    files,hashes=set(),set()
    for key,entry in catalog.items():
        path=(ART_ROOT/entry['file']).resolve()
        if not path.is_relative_to(ART_ROOT.resolve()):raise ValueError('Asset leaves artwork root: '+key)
        data=path.read_bytes()
        if not data.startswith(b'\x89PNG\r\n\x1a\n') or len(data)<10000:raise ValueError('Invalid image: '+key)
        digest=hashlib.sha256(data).hexdigest()
        if path in files or digest in hashes:raise ValueError('Duplicate illustration: '+key)
        files.add(path);hashes.add(digest)
    if len(catalog)!=64 or any(key.startswith('legacy_') for key in catalog):
        raise ValueError('Only the retained 64-design game may be active')
    return catalog


def preserve_history():
    moves={}
    for name in LEGACY_TESTS:moves['tests/'+name]='tests/retired_legacy/'+name
    for name in ['capture_screens.py','capture_arena.py']:
        moves['tests/'+name]='tools/retired_legacy/'+name
    for name in ['expand_cards.py','refine_cards.py','fifty_card_sets.py']:
        moves['data/'+name]='tools/retired_legacy/'+name
    moves['CARD_CATALOG.md']='docs/retired_legacy/CARD_CATALOG.md'
    moves['data/CARD_RULES.md']='docs/retired_legacy/CARD_RULES.md'
    moves['assets/art/tactical/README.md']='docs/retired_legacy/previous-artwork.md'
    moved=[]
    for source,destination in moves.items():
        src,dst=safe_path(source),safe_path(destination)
        if not src.exists():continue
        if dst.exists():raise ValueError('Refusing to overwrite historical file: '+destination)
        dst.parent.mkdir(parents=True,exist_ok=True)
        shutil.move(str(src),str(dst));moved.append(dict(source=source,destination=destination))
    descriptions={
        'tests/retired_legacy':'Historical tests for the removed Pygame mode. Retained as reference; excluded from active test discovery because their implementation was retired. Current gameplay tests are tests/test_tactical.py and tests/test_artwork.py.',
        'tools/retired_legacy':'Historical card generators and captures for the removed Pygame mode. Retained as development reference, not active game tools. Current captures are tests/capture_tactical.py and tests/capture_anime_art.py.',
        'docs/retired_legacy':'Historical card/rules documentation for the removed six-color Pygame mode. It does not describe the current five-color browser game; see tactical/README.md for current rules.'}
    for directory,description in descriptions.items():
        folder=safe_path(directory);folder.mkdir(parents=True,exist_ok=True)
        (folder/'README.md').write_text(description+'\n',encoding='utf-8')
    return moved


def plan_cleanup():
    catalog=verify_catalog()
    used={(ART_ROOT/e['file']).resolve() for e in catalog.values()}
    targets=[]
    def add(relative,reason):
        path=safe_path(relative)
        if path.exists():targets.append(dict(path=str(path.relative_to(ROOT)),reason=reason,directory=path.is_dir()))
    for path in ART_ROOT.glob('*.png'):add(path.relative_to(ROOT),'Superseded illustration')
    for path in (ART_ROOT/'anime').glob('*.png'):
        if path.resolve() not in used:add(path.relative_to(ROOT),'Retired legacy illustration; not in current catalog')
    add('assets/art/cards.json','Superseded legacy artwork mapping')
    add('assets/art/anime/TACTICAL_READY','Obsolete transition flag; current catalog is canonical')
    for name in ['tactical','direction-preview']:
        add('assets/art/'+name,'Superseded artwork package; approved images and prompts retained in anime/')
    for name in LEGACY_CODE:add(name,'Explicitly removed Pygame game implementation')
    add('data','Retired legacy card/commander/relic data; generators and documentation preserved separately')
    for name in ['capture_art_direction.py','art_direction_browser.mjs']:
        add('tests/'+name,'Superseded preview-only tool; current artwork review tools retained')
    for path in (ROOT/'artifacts').glob('*.png'):
        add(path.relative_to(ROOT),'Outdated generated screenshot; fresh retained-game captures follow cleanup')
    add('artifacts/artwork-revisions.json','Generated revision jobs belonging to the retired card pool')
    for directory in ROOT.rglob('__pycache__'):
        if not any(part in ('.git','.venv','node_modules','.agents','.codex','.aws') for part in directory.relative_to(ROOT).parts):
            add(directory.relative_to(ROOT),'Regenerable Python bytecode cache')
    return targets


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--apply',action='store_true');parser.add_argument('--preserve-history',action='store_true');args=parser.parse_args()
    moved=preserve_history() if args.preserve_history or args.apply else []
    prior=ROOT/'artifacts/artwork-cleanup.json'
    previous=json.loads(prior.read_text(encoding='utf-8')) if prior.is_file() else {}
    moved=previous.get('moved_history',[])+moved
    targets=plan_cleanup()
    preserved={}
    for pattern in ['*save*.json','*save*.tmp','settings.json','settings.tmp']:
        for path in ROOT.glob(pattern):preserved[str(path.relative_to(ROOT))]=hashlib.sha256(path.read_bytes()).hexdigest()
    if args.apply:
        if not (ART_ROOT/'anime/READY').is_file():raise ValueError('Verify the retained artwork before cleanup')
        for entry in targets:
            path=safe_path(entry['path'])
            if not path.exists():continue  # A parent target may already have removed a cache.
            if entry['directory']:shutil.rmtree(path)
            else:path.unlink()
        for name,digest in preserved.items():
            if hashlib.sha256(safe_path(name).read_bytes()).hexdigest()!=digest:raise ValueError('Preserved data changed: '+name)
    report=ROOT/'artifacts/artwork-cleanup.json';report.parent.mkdir(exist_ok=True)
    recorded={entry['path']:entry for entry in previous.get('targets',[])}
    recorded.update({entry['path']:entry for entry in targets})
    report.write_text(json.dumps(dict(applied=args.apply,targets=list(recorded.values()),moved_history=moved,
        preserved_file_hashes=preserved,preserved=['saves','settings','historical tests','documentation','development references','current capture tools']),indent=2)+'\n',encoding='utf-8')
    print(('Removed' if args.apply else 'Planned'),len(targets),'verified cleanup targets')

if __name__=='__main__':main()
