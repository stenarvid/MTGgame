# Tactical prototype

Launch `python -m tactical.server --open` from the repository root. No additional
dependencies are needed. `python main.py` launches the same game and opens a browser.
For network play, use `--host 0.0.0.0`; each participant opens the host's address
and joins a room. This is a self-hosted prototype, without matchmaking or accounts.
For public hosting, put the server behind HTTPS; private seat tokens authenticate
actions. Serving through a different browser origin requires that browser's saved
seat credentials to be transferred deliberately, rather than exposing them in URLs.

## Play

Create a solo campaign or a two-to-four-seat human group. Human groups can fill
seats with AI. The host starts commander selection once at least two players join.
First choose one of three commanders. The next screen shows only that commander's
two packages; select one, review the combined choice, and confirm. Back lets you
change the commander before confirmation. Both packages keep
the same color identity. Commander and package remain locked through the run or
competition. Duplicate commanders across players are allowed.

Human drafts have three 15-card packs per player, passed left/right/left. Each
pack guarantees two cards per color and two neutral cards, with three variable
slots. Off-color picks can be retained but cannot enter the deck. Solo players
choose five legal cards from each of three personal 15-card packs.

Everyone starts with a legal 30-card deck. Between battles, click a deck card,
then a reserve card to exchange them. Cards stay owned for the current run/group.
The two-copy limit excludes the basic early creature of each commander color.
Initial relics are chosen from three options after drafting. Relics are permanent,
public, nonremovable modifiers with conditions or tradeoffs.

Opening hands contain five cards, with one free full-hand mulligan. Keep first,
then choose the initial mana color. Choices reveal simultaneously. The active
player draws one additional card on their first turn and every subsequent turn.
Health starts at 25. Mana refreshes on your turn and grows by one colored capacity
on subsequent turns, up to ten. Capacity color is chosen when gained. Unspent mana
remains usable throughout opponents' turns. Green can ramp toward the cap and
generate temporary mana; excess temporary mana does not increase permanent capacity.

Click a hand card and select a legal target if required. Costs are paid upfront,
including Ward and explicit health/discard/sacrifice costs. Discard costs prompt
for a card; blue filtering also prompts for a discard after drawing. Costs are
not refunded if an action is countered or its target disappears.

Everyone passes priority before the top pending action resolves. The casting
player retains priority until passing; after resolution the active player gets
priority first. Spells and nonmana abilities share the stack. Creatures and major
spells require your main phase and an empty stack; response cards can be played
with priority. Commander actives additionally exhaust their creature and cost
two generic mana. Mana abilities resolve immediately.

Turns have first main, precombat response, attacker declaration, attack response,
blocker assignment, damage response, second main, and end windows. Drawing, mana
refresh, readying and damage recovery happen at turn start. Attack dropdowns
choose a defender per creature; confirm all attacks together. Defender dropdowns
assign blockers, with multiple blockers allowed per attacker. The attacker can
rotate blocker order before damage. Blocking does not exhaust creatures.

New creatures can block but cannot attack or exhaust for abilities until their
controller's next turn, unless they have Haste. Guard prevents exhaustion from
attacking. Flying requires Flying/Reach blockers. Trample sends excess damage
past blockers. A blocked creature stays blocked if blockers disappear. Damage is
simultaneous and persists until each creature controller's next turn. Lifesteal
heals for damage actually dealt, including excess damage. Ward adds one generic
mana when an opponent targets the creature. Goad requires attacking another
opponent if possible and expires after the creature controller's next turn.

Commanders are 3/5 creatures costing four total mana with one pip per identity
color. First cast is untaxed; subsequent command-zone casts add two generic mana
each. Leaving play returns them to the command zone. Passives operate while the
commander is in play. The command zone is separate from the 30-card deck.

Opening protection keeps health at one or more until everyone completes a first
turn. It does not pay health costs or queue lethal damage. Failed draws cause
fatigue of 1, 2, 3, ...; graveyards never automatically reshuffle into decks.
After each action resolves, check lethal creatures and players before priority.
Eliminated players' cards and pending actions leave the battle. Spectators see
public cards/actions, never opponents' hands.

## Repeatable combo

Recruit Foundry replaces a dead friendly token. Reclamation Relay readies friendly
creatures and refunds one temporary mana when a token dies. Bone Broker exhausts,
pays one mana, and sacrifices another creature to draw a card. Soul Collector
adds damage/healing to friendly deaths. These visible pieces create a repeatable
combo, but card draw can also cause fatigue and opponents can counter individual
abilities, remove creatures, or remove engines with Disrupt Engine.

With Broker, both engines and a token in play, use **Declare loop** and specify a
finite count. Only the initiator's repeated actions/passes are automated; opponents
still receive every response opportunity. **Stop loop** is available to its owner
even without priority. Opposing spells interrupt the declaration, and missing
pieces/resources stop it. Mandatory unbreakable loops are excluded. Counts are
limited to one million as an input bound, and execution happens incrementally.

## Progression

In human play, each opponent eliminated awards one victory point to the finishing
action's controller; survival awards one additional point. Simultaneous elimination
credit is assigned before removing players, including a controller who also dies.
If everyone dies, nobody earns survival. Conceding with an empty stack grants no
elimination credit and is logged. Negotiated concessions and cross-battle point
trading are house-rule violations; this prototype does not automatically adjudicate
social deals.

Scoring any points earns at most one five-card pack, keeping two legal cards.
Every nonsurvivor receives one loss, even if they scored. Every two losses offers
three distinct relic alternatives, excluding the current relic; keeping it is
allowed. Rewards and deck changes happen after battles.

The default target is five VP. Finish the battle before voting on extending,
quitting, or restarting. A majority means more than half of remaining participants.
Split votes enter a two-option runoff; option-count ties prioritize quit, extend,
restart for choosing the runoff. A tied runoff ends the competition. Extensions
set the target to the highest score plus three and retain builds/scores. Restart
resets builds/scores and returns to the lobby before a fresh draft. Vacant seats
can be filled there. Departures are allowed between battles; new entrants require
a restart. First seating/starting player are randomized, then the starting player
rotates each battle. A group
ending with tied highest scores has shared leaders.

Solo survival clears an encounter. Three encounters plus a boss repeat across
four acts. Ordinary rivals pursue their own survival; publicly marked elites and
bosses coordinate. Elites create reinforcements, bosses gain recurring draws.
Later acts improve existing-card synergy and threat assessment, without stat buffs.
Each clear gives a pack and one currency. A three-card legal shop sells cards for
one currency; refresh costs one. Exchanges with owned cards remain free. Bosses
offer optional relic replacement. One retry repeats the encounter with the same
seed, allowing owned-card rearrangement first; defeat never grants extra rewards.

## Saves, timing, and validation

The host stores all rooms and random state atomically in `tactical-save.json`.
Browser session storage holds the active seat; local storage holds recent seats.
Resume from **Rooms** after restarting the host at the same address/port.
Do not delete this browser's saved site data if you need its seat credentials.
Solo simulation pauses when its player stops polling. Shared games keep running.

Response windows default to 30 seconds, other decisions to 60, with a 60-second
time bank. Expiry passes, skips optional combat/blocking, or chooses a mandatory
color/discard; it never spends mana. Repeated timeouts or a disconnected seat
trigger visible AI takeover. Reclaim restores human control. Optional auto-pass
stops for combat, direct targeting, targeting your pending actions, and global
damage/board-changing effects.

Tests:

```sh
python -m unittest discover -s tests -p test_tactical.py -v
python tests/capture_tactical.py
```

Browser smoke coverage requires Node and installed Edge (or `EDGE_PATH` pointing
to Chromium). It uses an isolated temporary headless profile and exports screenshots
to `artifacts/tactical-*.png`.

Current content is **46 deck designs, ten commanders with 20 packages, six relics**.
The expanded roster is available immediately so mono/two-color differences can
be tested. The 150-design target remains ten commanders + 25 designs per color +
15 neutral designs. Replace redundant cards first; expand for demonstrated gaps.
Balance, 20–30-minute pacing, two distinct builds per package, and credible recovery
from poor drafts have **not** been established by automated tests. Record player
reflections alongside elapsed times, spectator waits, concessions and counterplays.
AI is a deterministic public-information heuristic, not a validated expert opponent.
