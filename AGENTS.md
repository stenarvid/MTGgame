# Agent guide: Commander Spire

## Start here; avoid repeated project discovery

- Use this guide as the first project map. Read the mapped files relevant to the
  task instead of listing or searching the entire repository at the start of each
  task. Check `git status --short` to understand existing changes.
- Read implementation details before editing them; this map does not replace that
  check. Use targeted `rg` searches inside the relevant file or directory when
  needed. Broaden discovery only if a mapped path is missing, the map is stale, or
  the task crosses an undocumented boundary. Correct stale entries as you go.
- Check for applicable nested `AGENTS.md` instructions when entering a directory.
- Keep unrelated user changes intact. Do not open saves, generated images, logs,
  or retired code unless the task needs them.

## Project and architecture

Commander Spire is a five-color browser card game with a solo AI campaign and
1v1 multiplayer. Python 3.11+ and the standard library run the
backend; the frontend is plain HTML, CSS, and JavaScript, with no npm build step.
The former six-color Pygame mode is retired.

Rules are authoritative on the server. `battle.py` handles battles; `session.py`
handles progression and drafting; `server.py` serves browser clients and saves
rooms. Both solo and multiplayer use the same rules, content, and artwork. The
card review uses production battle rules with isolated in-memory scenarios.

## Preserve the game design and UI

- Read `tactical/README.md` for current gameplay and production controls;
  `docs/card-design-review.md` and `docs/ANIMATION_REVIEW.md` describe review
  behavior and the shared visual language. Check the relevant implementation
  before editing. Review-only layouts and controls do not automatically define
  production behavior; flag conflicts instead of silently choosing a redesign.
- Keep changes proportional to the request. Necessary targeted UI fixes for the
  requested feature, demonstrated bugs, or accessibility problems are allowed.
  A small change must not trigger a new layout, theme, navigation, or interaction
  model. Ask before expanding the scope into a broader redesign unless the user
  has already requested it; routine targeted fixes need no extra approval.
- Preserve the established illustrated temple battlefield, opposing card rows,
  mirrored commander portrait health orbs, physical deck piles, colored ready/spent
  mana gems, fanned hand, shared card frames/color ornaments, and full inspection
  unless changing them is part of the request or necessary for the targeted fix.
- Preserve immediate untargeted casting, target preview followed by same-target
  reconfirmation, Cancel/Escape without payment, combat assignment arrows followed
  by whole-decision confirmation, and the fixed mandatory first-main mana prompt.
  Keep mobile guidance and the readable expandable hand tray usable.
- Prefer edits to the responsible component and scope production-only styles to
  `.game-shell`. Check shared renderer/style consumers before changing them;
  avoid unrelated restyling or refactors. Effects must remain nonblocking, use
  public information, and respect reduced motion and intensity settings.
- For visible UI changes, compare the affected screen before and after at desktop
  and mobile sizes, run relevant browser checks, and verify nearby controls and
  inspection still work. Report the intended visible change and any validation
  limits. Documentation-only changes do not require browser captures.

## File map and task routing

Paths are relative to the repository root. Grouped entries cover every named
file; directory entries deliberately cover bulk generated or historical files.

| Area / task | Files and responsibilities |
| --- | --- |
| Agent instructions | `AGENTS.md`: this map and working instructions; maintain with structural changes. |
| Launch and setup | `main.py`: browser game launcher. `requirements.txt`: standard-library-only runtime. `.gitignore`: local data/cache exclusions. `pytest.ini`: pytest discovery exclusions. |
| User documentation | `README.md`: setup and overview. `tactical/README.md`: detailed gameplay, controls, saves, and validation. |
| Game definitions | `tactical/content.py`: cards, commanders, packages, relics, keywords, and starter builds; rules use effect identifiers rather than parsing card text. |
| RPG items and sockets | `tactical/items.py`: approved card/item/consumable definitions and deterministic socket composition. `tactical/battle_items.py`: shared Equipment, ward, pouch, trigger-choice and copy/control rules. `tactical/item_session.py`: owned gear, reusable gems, pouch spending, curated rivals and separate supply rewards. `docs/RPG_ITEMS.md`: design text, compatibility and initial tuning. |
| Battle rules and AI | `tactical/battle.py`: authoritative battle state, actions, combat, priority/stack, effects, and AI. `tactical/priority.py`: server response deadlines, manual control, phase stops, timing permissions and APNAP trigger ordering. |
| Draft and progression | `tactical/session.py`: rooms' game sessions, drafting, deck building, campaign, competition scoring, and serialization. `tactical/progression.py`: legacy additive item tiers, socket-only tiers for new items, and design upgrade previews. `tactical/tutorial.py`: isolated playable training campaign and action-driven lessons. |
| Campaign routes and loot | `tactical/campaign.py`: connected left-to-right act maps, public challenge definitions, Essence bonuses, and treasure odds. `tactical/session.py` freezes routes for retries and persists once-only equipment/currency rewards. |
| HTTP and persistence | `tactical/server.py`: routes, room/seat authentication, polling, static files, and autosaves. `tactical/__init__.py`: package marker. |
| Main browser interface | `tactical/web/index.html`: inline client logic, journey progress, contextual casting reasons, and combat choices. `tactical/web/priority-ui.js` and `priority-ui.css`: production bottom action bar, response countdown, phase stops and trigger resolution ordering. `tactical/web/temple-game.js` and `temple-game.css`: production illustrated temple battlefield, mirrored portrait health orbs, mana gems and fixed mandatory mana choices, target reconfirmation, combat assignment arrows, and mobile hand tray. `tactical/web/inventory.js` and `item-ui.js`: three-slot inventory, socket previews, consumable pouch and gem shops, battle item controls, upgrade previews, tutorial guidance, and opponent portrait selection. `tactical/web/style.css`: shared cards/frames and cinematic desktop/mobile styles; main-game overrides use `.game-shell`. |
| Cards and inspection | `tactical/web/cards.js`: shared card rendering and detailed vector ornaments for mono/dual color identities and commanders, plus distinct vector sigils for new RPG designs. `tactical/web/card-hover.js`: card hover behavior. |
| Quality of life and rewards | `tactical/web/qol.js` and `qol.css`: room-scoped collection search/filter/sort, mana curve, panel/focus preservation, target-cost hints, route map, spending confirmations, and skippable earned-treasure reveal. |
| Animation and effects | `tactical/web/battle-presentation.js`, `battle-presentation.css`, `spell-fx.js`, `spell-fx.css`, and `effect-profiles.json` (all under `tactical/web/`): public-event presentation, pending family seals, bounded overlapping combat, per-hit feedback, socket/equipment/relic cues, sound, intensity, and reduced motion. `docs/ANIMATION_REVIEW.md`: review scenes and behavior. |
| Playable card review | `tactical/preview.py`: isolated review server/scenarios. `tactical/web/preview.html`, `preview.js`, `preview.css`, `temple-review.css`, and `arena-review.css`: review interface/styles. `docs/card-design-review.md`: design review notes. |
| Artwork lookup | `artwork_catalog.py`: stable design identities. `tactical/artwork.py`: game artwork lookup. |
| Artwork preparation | `prepare_anime_art.py`: prompt/manifest preparation. `tactical/prepare_artwork.py`: compatibility entry point. `artwork_progress.py`: completion report. |
| Artwork reviews | `build_art_review.py`: searchable gallery. `build_art_direction_review.py`: approved direction review. `build_game_art_preview.py`: review art with the game renderer. |
| Artwork cleanup | `cleanup_artwork.py`: explicit inventory and verified cleanup; default invocation reviews, `--apply` removes eligible files. |
| Production artwork | `assets/art/anime/`: illustrations, `manifest.json` (exact prompts and filenames), `approved-prompts.json`, `README.md`, and `READY` marker. Use the manifest instead of enumerating PNGs. |
| Art references and battlefield environments | `assets/art/`: `PROMPTS.md`, `INDIVIDUAL_PROMPTS.md`, `arena-board.prompt.md`, `temple-table-prompt.txt`, `temple-table.png`, and `review-table.png`; field/town battlefield backgrounds and their generation prompts. `assets/art/direction-v2/` and `assets/art/direction-v3/`: direction samples, prompts, READMEs, and generated review pages. |
| Python tests | `tests/test_tactical.py`: game/session/server behavior. `tests/test_priority_flow.py`: response deadlines, manual priority, timing grants, phase stops, trigger ordering and save continuity. `tests/test_items.py`: sockets, owned deck copies, triggered ward, consumable persistence, attachment, copying/control and approved templates. `tests/test_campaign_features.py`: equipment ownership, upgrades, mulligans, legal offers, and a complete production-rule tutorial walkthrough. `tests/test_card_preview.py`: review behavior. `tests/test_artwork.py`: artwork integrity. |
| Campaign route validation | `tests/test_campaign_routes.py`: graph reachability/counts, challenge rules, retry freeze, save migration, and persistent once-only treasure rewards. |
| Quality-of-life browser validation | `tests/qol_browser.mjs` via `tests/capture_tactical.py --qol`: isolated fixtures for filtering, focus/panels/drafts, polling races, rejected actions, public zones, targeting costs, loot reveal, scenery, and mobile layout. |
| RPG item browser validation | `tests/items_browser.mjs` via `tests/capture_tactical.py --items`: isolated desktop/mobile inventory, gem previews/apply, owned gear deck exchange, spending cancellation, attachment, inspection, pouch targeting and reload persistence. |
| Browser validation | `tests/priority_browser.mjs` via `tests/capture_tactical.py --priority`: isolated priority action bar, real response deadlines, Hold/Respond/Resume and desktop/mobile checks. `tests/capture_tactical.py` + `tactical_browser.mjs` and `tutorial_browser.mjs` (`--tutorial`): desktop/mobile journey, real drafting, private hands, rewards, temple targeting/combat arrows, and contextual controls. `tests/capture_card_preview.py` + `card_preview_browser.mjs`: playable rules, family casts/resolutions/cleanup, and reduced motion. `tests/capture_anime_art.py` + `anime_art_browser.mjs`; `capture_art_direction_v2.py` + `art_direction_v2_browser.mjs` (all under `tests/`). `tests/game_art_browser.mjs`: game-art browser review. |
| Historical launcher test | `tests/test_ask_code.ps1`: references `ask-code.ps1`, which is absent in this checkout; outside active game validation. |
| Retired desktop references | `docs/retired_legacy/`, `tests/retired_legacy/`, `tools/retired_legacy/`: historical documentation, tests, and tools; excluded from active test discovery. |
| Generated outputs | `artifacts/`: screenshots (including mobile journey/rewards, family pending/impact reviews, tutorial/inventory, temple targeting/crowded-table, priority before/after, paused action bars and trigger ordering, mana prompts, QOL map/filtering, treasure reveals, field/town scenery, and RPG inventory/pouch desktop/mobile reviews, socket before/impact desktop/mobile comparisons, and combat impact feedback), generated gallery HTML, progress/cleanup reports, and server/check logs; not implementation source. |
| Local state | `tactical-save.json`: active room/campaign save. `save.json`, `run-save.json`, `settings.json`: historical user data. `.ollama-reviews/`: local review output. `__pycache__/` and any `.venv/`: local generated/runtime directories. |

## Commands and validation

Run commands from the repository root:

```sh
python main.py                        # Start game and open browser, port 8765
python main.py --no-open              # Start without opening browser
python -m tactical.preview --help     # Review-server options
python -m unittest discover -s tests  # Active Python tests
python tests/capture_tactical.py      # Multiplayer/campaign browser checks
python tests/capture_tactical.py --tutorial # Playable tutorial and inventory checks
python tests/capture_tactical.py --qol # Routes, loot, controls, and connection regressions
python tests/capture_tactical.py --priority # Priority clocks, action bar and phase stops
python tests/capture_tactical.py --items # Sockets, gear, pouch and item persistence
python tests/capture_card_preview.py  # Playable card-review browser checks
python tests/capture_anime_art.py     # Artwork gallery browser checks
```

Browser capture checks require Node and installed Edge, or `EDGE_PATH` pointing
to a Chromium browser. They use temporary browser profiles and isolated saves,
and write outputs to `artifacts/`. Run checks relevant to the change; documentation
and map-only edits need path/link verification rather than game/browser tests.

Preserve user saves/settings. Use a temporary save with `--save PATH` for manual
game checks that could change persistent state. Keep private seat tokens and
opponents' hidden cards out of public responses, URLs, and presentation events.

## Required maintenance when files change

- Whenever you add, delete, rename, or move a project file, update this `AGENTS.md`
  in the same change, before reporting completion. Add its path and purpose,
  remove obsolete paths, and correct references and task routing after moves.
  Include new nested agent guides in the map.
- For files covered by a bulk directory entry (artwork, generated artifacts,
  caches, local state, or retired references), update that entry's description or
  scope to reflect the addition/removal; do not list every PNG, log, or cache.
  Routine regeneration of existing outputs does not need an edit here.
- If an existing file changes responsibility, or launch/test/dependency commands
  change, update the relevant entry or command even without a file addition.
- Before finishing, inspect `git status --short` and the diff for added, deleted,
  renamed, and moved files, including untracked files you created. Confirm each
  structural change is reflected here and every explicit mapped path exists.
- Keep this guide concise and current: replace stale information instead of
  appending a change history or copying entire implementation details.
