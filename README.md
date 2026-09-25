# Commander Spire

A Pygame deckbuilding roguelike inspired by Slay the Spire, Dungeon Run, and MTG.

## Launch

Install Python 3.10+ and then:

```sh
python -m pip install -r requirements.txt
python main.py
```

The window resizes and scales the complete interface while preserving mouse hitboxes.
Display settings offer 75%, 100%, and 125% sizes, fullscreen, and reduced animations.
On smaller desktops the initial window fits the available screen.

## Run progression

Choose a passive and active to create a commander and a 16-card starting deck. The
builder previews the exact starting cards. Follow available map nodes to the boss.
HP, gold, deck changes, and relics persist between encounters.

- **Combat / Elite / Boss:** gain 20 / 35 / 60 gold, then choose one of three cards
  matching your commander colors, or skip. Rewards cannot be collected twice.
- **Merchant:** buy matching-color cards and use one service per visit: remove a
  card for 40 gold or upgrade one for 30. Review the selected card before confirming.
  Removal preserves at least 10 cards and two lands of each existing color.
- **Rest:** heal up to 10 HP **or** upgrade a card for free.
- **Treasure:** choose one of up to three unowned relics. Relic choices remain
  exclusive to Treasure nodes. Owning all relics yields 25 gold instead.

Creature upgrades give permanent +1/+1. Spell upgrades improve their numerical
effects by one; upgraded Null Sigil also draws a card when it counters. Lands cannot
be upgraded. Upgrades survive battles, death, bounce, and reshuffles; combat buffs
are not written into the run deck.

## Saving and resuming

`run-save.json` autosaves after mouse/keyboard decisions, including mid-battle.
Use **F5** to save manually or **Pause > Save and return to menu**. Select **Resume
saved run** at the main menu. Closing the window saves the active run.

Saves preserve deck order, hands, mana, creature damage, temporary buffs, the spell
stack and its targets, blocker assignments, mulligan usage, commander usage, shop
stock, pending card/relic choices, map connections, and random state. Inspection
panels resume at their underlying gameplay screen. A failed write leaves the last
complete save intact; unreadable saves show an error and are not overwritten by
attempting to resume. Starting a replacement run asks before replacing the save.
Completed or explicitly abandoned runs clear their run save.

Achievements remain separate in `save.json`. Display size and animation preferences
persist in `settings.json`. Tests and screenshot scripts use temporary save paths.

## Combat

### Opening hand and mana

Both sides have their own deck, hand, discard, lands, and creature board. Two lands
start in play, covering both deck colors where possible. All other lands remain in
the draw pile. You draw five cards and may select any to replace **once, for free**.
Replacement cards come from the remaining deck before the selected cards are
shuffled back. Keep the hand to start turn one and draw for the turn.

Costs use **W** (white), **U** (blue), **B** (black), **R** (red), and **G** (green).
`1R` means one red mana plus one of any color. Costs shown on cards include relic
discounts; discounts cannot erase required colored symbols. Automatic payment
pays the required colors first. Generic bonus mana cannot pay colored requirements.
Grove Sprite and Titan Overseer produce green mana.

Play one land per turn. Lands persist and untap on their owner's turn. Unspent
floating mana clears when leaving a phase; untapped lands remain available.
Unplayed cards stay in hand without a hand limit. Discard reshuffles when the draw
pile empties. If both are empty, failed draws cause increasing fatigue damage.

### Phases, responses, and combat

1. **First main phase:** play lands, creatures, spells, or the once-per-battle
   commander active. Select ready creatures and declare attacks (or none).
2. **Attack response window:** the enemy declares blockers. Review the damage
   preview, reorder enemy blockers by clicking one to move it last, and cast instants.
   Resolve combat when ready.
3. **Second main phase:** play more cards before ending your turn.
4. **Enemy turn:** enemy card casts pause on the spell stack for your responses.
   When it attacks, assign your blockers, lock them, respond, then resolve damage.

All nonland cards are cast onto a **last-in, first-out spell stack**. Cast an instant
in response or press **Pass priority**. The AI can respond too. Passing resolves one
spell when neither side adds a response, then priority returns for the remaining
stack. **Null Sigil** targets an opposing spell in the stack; use the stack panel to
choose it. Spells with targets that leave play fizzle without refunding their cost.
Creatures whose entry-effect target disappears still enter without that effect.

New creatures have summoning sickness but can block immediately. **Ember Duelist**
has Haste. Attacking taps a creature; blocking does not. Each blocker can block one
attacker; multiple blockers can group against one attacker. Damage follows the
shown blocker order and is simultaneous. **Thorn Sentinel** has Trample: excess
combat damage reaches the hero after blockers are assigned lethal damage. Other
blocked attackers remain blocked if their blockers subsequently disappear.

The combat preview shows hero damage after armor and which creatures would die
from current combat assignments, **before death triggers and further responses**.
Surviving creatures clear damage and temporary buffs at turn end. Tokens vanish
when leaving the battlefield. Armor absorbs damage, while life loss bypasses it.
A double knockout counts as defeat.

### Encounters and content

The pool contains **150 nonland cards**, with thirty cards for each core archetype.
There are six base passives (including Mirror Legion), five commander actives,
eight unlockable passives, and eight relics. All cards have implemented effects.

Opponents have color-themed decks and visible encounter rules:

| Opponent | Mechanic |
|---|---|
| Dawn Marshal | Musters tokens every second turn; elites every turn |
| Tide Archivist | Extra draws on even turns |
| Crypt Matron | Heals when creatures die |
| Ember Duelist | Bonus on its first damage spell each turn |
| Grove Warden | Buffs its first creature played each turn |
| Spire Sovereign | Alternating draw/starfall turns, plus a one-time half-health ascension that summons Guards and empowers its board |

This remains an MTG-inspired ruleset, not a complete MTG rules implementation.
There is no creature limit. The 75 trigger cards put triggered abilities onto the stack. Legacy card triggers and
commander actives still resolve immediately. Null Sigil counters spells, not abilities. Mana payment is automatic, there is no
land-tapping UI, and there are no upkeep/end-step priority windows or sideboards.

## Trigger-card expansion and Mirror Legion

The pool now has **150 cards: 30 each in Token, Blink, Graveyard, Spells, and Ramp**.
The unlocked Card Advantage commander uses the blue Blink pool. Starting decks stay
at 16 cards; new cards appear in matching-color rewards and shops. The complete
card list and rules text are in [CARD_CATALOG.md](CARD_CATALOG.md).

**Mirror Legion** is a new white/Token commander passive: create twice as many
tokens, including attacking copies. It applies once to each creation effect, affects
only your tokens, and has no creature cap. Valkyrie Grace remains the
separate extra-Recruit passive.

**Astra, Echo Conduit**, **Mirror Pathfinder**, and **Prism Navigator** trigger when they attack. Choose
another friendly nontoken creature (or skip); the ability goes onto the response
stack before blockers. On resolution it creates a token copy tapped and attacking,
including entry effects. Copies do not trigger attack abilities merely by entering
attacking. Astra makes a temporary full-size copy; Mirror makes a temporary 1/1
copy and draws a card; Prism keeps its copy but loses 3 life. These are original simplified designs,
without Satya's energy payment mechanic.

Other new abilities trigger on entry, spell casting, playing a land, and deaths.
An ability already on the stack survives its source dying; a copy ability fizzles
if its chosen target leaves play. Death triggers resolve before combat advances.

## Controls and feedback

| Control | Action |
|---|---|
| Drag a hand card / **1-9** | Drop onto the battlefield or a highlighted target; number keys retain click-to-target casting |
| Click a ready friendly creature | Select/unselect an attacker |
| **A** | Select/unselect all ready attackers |
| Click a friendly blocker, then an enemy attacker | Assign it; repeat for multiple blockers |
| **Space** | Keep hand / advance phase / pass priority / continue after battle |
| **D** / **G** | Inspect your draw pile / discard pile; draw order is hidden |
| **L** | Browse combat history, newest first |
| **P** | Pause |
| **F5** | Save run |
| **F11** | Toggle fullscreen |
| Mouse wheel / page arrows | Browse cards, stack, or log pages |
| Right-click | Clear targeting/selections; clear unlocked block assignments |
| Escape | Cancel a selection, return from an inspection panel, or pause |

The hand fans across the bottom. Hover lifts and enlarges a card with a cyan glow
and a separate readable preview. Holding left mouse picks it up and hides the
preview; release over the battlefield to cast, or over a highlighted creature,
hero, or stack spell for targeted cards. Invalid drops return the card without
spending mana. Escape/right-click cancels a drag. Mouse coordinates respect scaling.

Matching tokens share battlefield piles, separated by name, rules, stats, damage,
readiness, and combat state. Piles are rebuilt from current state, so identical
tokens merge again after buffs applied on different turns bring them to the same
stats. Temporary buffs with different expiry behavior remain separate. Click a ready pile to peel off one attacker; click its
count badge to select all ready tokens in that pile. Selected attackers form a
separate blue-glowing pile with a line to the attack arrow. Click again to deselect.
Different creatures and individually assigned blockers stay separate. Battlefield
page arrows expose additional piles on large boards; every token remains its own
rules object for targeting, damage, triggers, and saving.

The right-side stack shows the newest four spells/abilities as overlapping cards,
with the next item at the front. Hover to inspect; drop Null Sigil on an exposed
enemy spell to counter it. Use the inspector for deeper stacks. Pass priority to
resolve the next item, leaving an opportunity to respond between resolutions.

Hover cards for full rules, mana costs, artwork, and current stats. Colored outlines
show affordable and selected cards. Floating damage/heal numbers and cast labels
provide feedback, and the history retains the last 300 events. Reduced-animation
mode preserves the log and previews without floating effects.

## Artwork

The original 25 named nonland cards have individual anime fantasy illustrations.
The 125 expansion cards currently reuse the matching color portraits. The 25 card
illustrations plus an astral-spire environment are bundled in `assets/art/` and need
no network connection at runtime. `assets/art/cards.json` maps names to files.
Tokens, enemy-only generic units, and commander choices reuse themed portraits;
lands share the environment artwork.

Art was generated with the built-in image generation tool. Exact prompts are in
[the original prompt set](assets/art/PROMPTS.md) and
[the 20 additional individual-card prompts](assets/art/INDIVIDUAL_PROMPTS.md).

## Validation and structure

```sh
python -m unittest discover -s tests -v
python tests/capture_screens.py
```

The suite covers rules, original effects, all commander combinations in seeded full
runs, response/counter chains, colored payments, multiple blockers, previews, save
reference identity, failed writes, reward duplication, services, and scaled input.
Screenshot generation produces review images in `artifacts/` using sample boards.

- `engine.py`: run progression, combat, effects, encounters, and reward rules.
- `models.py`: card/commander data, upgrades, starter decks, and maps.
- `persistence.py`: versioned JSON graph saves with atomic replacement.
- `main.py` / `ui_panels.py`: screens, controls, save integration, services, inspection.
- `art.py` / `rendering.py`: artwork cache, card frames, and rendering helpers.

## Additional achievement unlocks

Each requirement must be reached within one run. Earned passives are permanently
added to the random commander-builder choices; they do not replace your current
commander. Existing achievement saves remain compatible. New counters start at
zero in older runs because their earlier actions were not recorded.

| Unlock | Requirement | Passive |
|---|---|---|
| Radiant Foundry | Create 20 tokens | Your creature tokens enter with +1/+1 |
| Rift Sanctuary | Blink/return 8 creatures | Your blink/return effects heal you for 2 |
| Graveplate | Have 15 friendly creatures die | Each friendly death grants 1 armor |
| Runic Ward | Cast 20 noncreature spells | Each cast grants 1 armor |
| Living Roots | Play 10 lands | Each land played heals you for 2 |

Token copies count as tokens created; searched lands do not count as lands played.
Achievements has two pages and shows current-run progress. The original Mind Vault,
Endless Horde, and Overcharge Core unlocks remain available.

See [data/CARD_RULES.md](data/CARD_RULES.md) for how card data becomes gameplay.

## Post-run unlock progress

Victory and defeat show all eight unlock goals with this run's counts, progress
bars, remaining requirements, and separate NEW UNLOCK / ALREADY UNLOCKED labels.
New unlocks appear first, including those earned before saving and resuming.
Goals remain per-run; partial counts are not cumulative across runs.

## Second card expansion

Each archetype gains 10 creatures and 10 spells, for 100 additional cards. Token
adds recruitment and team buffs; Blink adds entry effects, blink and bounce;
Graveyard adds death triggers, drain, removal and recursion; Spells adds cast
triggers, burn and area damage; Ramp adds land engines, ramp and large buffs.
Starting decks remain 16 cards; all additions appear in matching-color rewards
and shops. The unlocked Card Advantage commander shares the blue card pool.

New spells use structured `spell.target` and `spell.effects` data interpreted by
`spell_rules.py`; the English text remains descriptive. See the card rules guide
and catalog for exact effects. `data/expand_cards.py` reproducibly updates these
100 card definitions and rebuilds the catalog. Balance has automated coverage
but will still benefit from playtesting.

## Card identity rework

The 150-card pool remains 30 cards per archetype. All 125 expansion cards were
reviewed, and repeated trigger definitions were replaced with distinct abilities,
conditions, follow-up effects, or costs. The content audit rejects duplicate full
trigger/spell definitions. This does not mean every card uses a brand-new keyword;
cards share mechanics while filling different roles.

- Token: permanent token growth, defensive 0/3 Shieldbearers, hasty 1/1 Spirits,
  catch-up recruitment, and wide-board rewards.
- Blink: temporary, miniature, and permanent attacking copies; freeze effects,
  mana refunds, spell recovery, and looting.
- Graveyard: sacrifice for cards or life drain, mill, cost-limited reanimation,
  death rewards, and discard-size scaling.
- Spells: first/second-spell rewards, attack-time buffs, hasty Sparks, damage
  scaling with spell count, and life-payment tradeoffs.
- Ramp: six-land thresholds, permanent token growth, Plants and trampling Beasts,
  solo-attack ramp, and land-count scaling.

Haste, Guard, Trample and Vigilance are implemented keywords, including when
spells grant them. Granted keywords are permanent for that battlefield instance;
bounce/blink resets them. Freeze taps a creature and skips its next untap.
Once-per-turn triggers track both players' turns and survive saves. Loot effects
explicitly discard the highest-cost card after drawing; they do not open a discard
selection screen. Scaling bonuses are capped as stated on the card.

`data/refine_cards.py` holds the curated identities and regenerates their exact
rules text/catalog. `data/expand_cards.py` applies that rework automatically, so
regenerating the expansion does not overwrite it. `identity_rules.py` implements
shared mechanics. Saved card descriptions are refreshed against current data on
load. Existing anime artwork remains shared by many expansion cards.
