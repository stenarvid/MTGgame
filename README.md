# Commander Spire

A five-color tactical card game with browser multiplayer and a solo AI campaign.
The original six-color Pygame game has been removed.

## Launch

Python 3.11 or newer is sufficient; no third-party packages are required.

```sh
python main.py
```

The launcher starts the game at `http://127.0.0.1:8765` and opens your browser.
Use `python main.py --no-open` to start without opening a browser. You can also
run `python -m tactical.server --open`.

For friends on other computers:

```sh
python main.py --host 0.0.0.0
```

Friends open your computer's address on port 8765 and join using the room code.
Keep the host process running. This is a self-hosted prototype, with no accounts
or matchmaking. Use HTTPS when deploying to a public host.

## Play

- **Solo campaign:** four acts, each containing three encounters and a boss.
  Multiplayer AI encounters use the same duel rules as human play. Victory packs,
  a limited-currency shop, free deck/reserve exchanges, optional boss relic
  replacement, one retry, and saving between encounters remain supported.
- **Human groups:** two players, private hands, pick-and-pass drafting,
  elimination/survival victory points, personal reward packs and continuation votes.
  Groups can fill empty seats with AI.
- **Decks:** fixed 30-card decks plus a commander, two packages per commander,
  public equipment/relic effects, and white/blue/black/red/green identities. Green can ramp.
- **Duels:** renewable colored mana, commander tax, priority and a response stack,
  blocking, persistent creature damage, eight keywords, and finite loop declarations
  that preserve opponents' response opportunities.

The current prototype has **46 deck-card designs, 10 commanders, 6 multiplayer relics and 7 solo equipment designs**.
The 150-design launch pool is a future content milestone. Balance, draft diversity,
credible counterplay and 20-30-minute battles still require human playtesting.

See [the gameplay guide](tactical/README.md) for detailed rules and controls.

## Artwork and interface

All **64 distinct designs** have unique cartoony anime illustrations: 46 cards,
10 commanders, 6 relics, the Recruit token and the menu environment. Copies share
only their own design's image; commander packages share their commander character.
The same pool and illustrations serve multiplayer and the solo campaign.

The desktop layout keeps hand, decision controls and pending actions together.
Commander selection separates choosing a character from choosing its package.
Card inspection explains full rules and keywords. Mobile has a fixed decision bar,
collapsible opponents and a horizontally scrollable hand.

Cards use detailed vector ornaments matched to their color identity, with blended
frames for dual-color commanders. Journey progress, commander package previews,
contextual casting explanations, and an accessible build action bar guide setup
through rewards. Spell animations extend beyond fire with cel-shaded shields,
waves, grimoires, shadow tendrils, grave portals, growing branches, and crystal
fragments. Effects settings include reduced motion and intensity controls.

Exact prompts and filenames are in [the anime manifest](assets/art/anime/manifest.json).
Images were created with the built-in image generation tool and are bundled locally.
See [the artwork guide](assets/art/anime/README.md) for review commands.

## Saves

The host autosaves rooms and solo campaigns to `tactical-save.json`. Browsers retain
private seat credentials for resuming. Solo play pauses while its browser is absent;
human seats can be reclaimed after AI takeover. `--save PATH` selects another save.

Existing desktop saves and settings are preserved as historical user data, but the
removed Pygame mode is no longer available to open them. No automatic conversion
changes their contents.

## Validation

```sh
python -m unittest discover -s tests
python tests/capture_tactical.py
python tests/capture_anime_art.py
```

Browser checks use installed Edge and Node, with isolated temporary profiles and
saves. Screenshots and the searchable art gallery are generated in `artifacts/`.
Historical desktop tests, documents and generator/capture references are retained
under `tests/retired_legacy`, `docs/retired_legacy`, and `tools/retired_legacy`.
They are excluded from active test discovery and do not describe current gameplay.

`python cleanup_artwork.py` reviews the explicit cleanup inventory; `--apply`
verifies the retained catalog before removing superseded files. It preserves user
save/settings files and records their hashes in `artifacts/artwork-cleanup.json`.

Solo campaigns include a three-slot equipment inventory, Essence upgrades for
card designs and individual items, and an optional playable **Learn to play**
mini-campaign from Rooms. Opponent portraits open a focused battlefield. Human
solo decisions are untimed, with optional automatic response passing.

Campaigns have branching left-to-right act maps, visible difficulty challenges
for bonus Essence, and earned treasure chests with independently upgraded items.
Field and town-street scenery joins the temple battlefield. Collection filters,
combat-plan reset/counts, target-cost hints, public exile inspection, spending
confirmations, and reliable live updates preserve the established controls.
Draws, mana changes, healing, and rewards have additional interruptible motion
and sound, with reduced-motion and intensity settings.
