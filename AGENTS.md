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
two-to-four-player multiplayer. Python 3.11+ and the standard library run the
backend; the frontend is plain HTML, CSS, and JavaScript, with no npm build step.
The former six-color Pygame mode is retired.

Rules are authoritative on the server. `battle.py` handles battles; `session.py`
handles progression and drafting; `server.py` serves browser clients and saves
rooms. Both solo and multiplayer use the same rules, content, and artwork. The
card review uses production battle rules with isolated in-memory scenarios.

## File map and task routing

Paths are relative to the repository root. Grouped entries cover every named
file; directory entries deliberately cover bulk generated or historical files.

| Area / task | Files and responsibilities |
| --- | --- |
| Agent instructions | `AGENTS.md`: this map and working instructions; maintain with structural changes. |
| Launch and setup | `main.py`: browser game launcher. `requirements.txt`: standard-library-only runtime. `.gitignore`: local data/cache exclusions. `pytest.ini`: pytest discovery exclusions. |
| User documentation | `README.md`: setup and overview. `tactical/README.md`: detailed gameplay, controls, saves, and validation. |
| Game definitions | `tactical/content.py`: cards, commanders, packages, relics, keywords, and starter builds; rules use effect identifiers rather than parsing card text. |
| Battle rules and AI | `tactical/battle.py`: authoritative battle state, actions, combat, priority/stack, effects, and AI. |
| Draft and progression | `tactical/session.py`: rooms' game sessions, drafting, deck building, campaign, competition scoring, and serialization. |
| HTTP and persistence | `tactical/server.py`: routes, room/seat authentication, polling, static files, and autosaves. `tactical/__init__.py`: package marker. |
| Main browser interface | `tactical/web/index.html`: game markup and inline client logic. `tactical/web/style.css`: shared interface styles. |
| Cards and inspection | `tactical/web/cards.js`: shared card rendering. `tactical/web/card-hover.js`: card hover behavior. |
| Animation and effects | `tactical/web/battle-presentation.js`, `battle-presentation.css`, `spell-fx.js`, `spell-fx.css`, and `effect-profiles.json` (all under `tactical/web/`): shared presentation and spell effects. `docs/ANIMATION_REVIEW.md`: review scenes and behavior. |
| Playable card review | `tactical/preview.py`: isolated review server/scenarios. `tactical/web/preview.html`, `preview.js`, `preview.css`, `temple-review.css`, and `arena-review.css`: review interface/styles. `docs/card-design-review.md`: design review notes. |
| Artwork lookup | `artwork_catalog.py`: stable design identities. `tactical/artwork.py`: game artwork lookup. |
| Artwork preparation | `prepare_anime_art.py`: prompt/manifest preparation. `tactical/prepare_artwork.py`: compatibility entry point. `artwork_progress.py`: completion report. |
| Artwork reviews | `build_art_review.py`: searchable gallery. `build_art_direction_review.py`: approved direction review. `build_game_art_preview.py`: review art with the game renderer. |
| Artwork cleanup | `cleanup_artwork.py`: explicit inventory and verified cleanup; default invocation reviews, `--apply` removes eligible files. |
| Production artwork | `assets/art/anime/`: illustrations, `manifest.json` (exact prompts and filenames), `approved-prompts.json`, `README.md`, and `READY` marker. Use the manifest instead of enumerating PNGs. |
| Art references and experiments | `assets/art/`: `PROMPTS.md`, `INDIVIDUAL_PROMPTS.md`, `arena-board.prompt.md`, `temple-table-prompt.txt`, `temple-table.png`, and `review-table.png`. `assets/art/direction-v2/` and `assets/art/direction-v3/`: direction samples, prompts, READMEs, and generated review pages. |
| Python tests | `tests/test_tactical.py`: game/session/server behavior. `tests/test_card_preview.py`: review behavior. `tests/test_artwork.py`: artwork integrity. |
| Browser validation | `tests/capture_tactical.py` + `tactical_browser.mjs`; `capture_card_preview.py` + `card_preview_browser.mjs`; `capture_anime_art.py` + `anime_art_browser.mjs`; `capture_art_direction_v2.py` + `art_direction_v2_browser.mjs` (all under `tests/`). `tests/game_art_browser.mjs`: game-art browser review. |
| Historical launcher test | `tests/test_ask_code.ps1`: references `ask-code.ps1`, which is absent in this checkout; outside active game validation. |
| Retired desktop references | `docs/retired_legacy/`, `tests/retired_legacy/`, `tools/retired_legacy/`: historical documentation, tests, and tools; excluded from active test discovery. |
| Generated outputs | `artifacts/`: screenshots, generated gallery HTML, progress/cleanup reports, and server/check logs; not implementation source. |
| Local state | `tactical-save.json`: active room/campaign save. `save.json`, `run-save.json`, `settings.json`: historical user data. `.ollama-reviews/`: local review output. `__pycache__/` and any `.venv/`: local generated/runtime directories. |

## Commands and validation

Run commands from the repository root:

```sh
python main.py                        # Start game and open browser, port 8765
python main.py --no-open              # Start without opening browser
python -m tactical.preview --help     # Review-server options
python -m unittest discover -s tests  # Active Python tests
python tests/capture_tactical.py      # Multiplayer/campaign browser checks
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
