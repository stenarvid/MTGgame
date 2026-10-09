# Tactical prototype

Launch `python -m tactical.server --open` from the repository root. No additional
dependencies are needed. `python main.py` launches the same game and opens a browser.
For network play, use `--host 0.0.0.0`; each participant opens the host's address
and joins a room. This is a self-hosted prototype, without matchmaking or accounts.
For public hosting, put the server behind HTTPS; private seat tokens authenticate
actions. Serving through a different browser origin requires that browser's saved
seat credentials to be transferred deliberately, rather than exposing them in URLs.

## Play

Create a solo campaign or a two-seat human duel. Human groups can fill
seats with AI. The host starts commander selection once both seats are filled.
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
Multiplayer relics are chosen from three options after drafting and remain public.
Solo campaigns choose an owned starting item. New Relics use three unique
loadout slots; castable Equipment replaces deck cards. Legacy passive items
retain their saved behavior. Opening solo booster offers contain only commander-identity and neutral cards.

Opening hands contain five cards. The first full-hand mulligan is free. Further
mulligans still redraw five, but the second requires bottoming one card when
keeping, the third two, and so on (maximum six mulligans). Choose the cards yourself;
they go to the bottom of the deck, not the graveyard. Keep and finish bottoming,
then wait for both players to keep. Choose your first mana gem at the start of
your first main phase. The active
player draws one additional card on their first turn and every subsequent turn.
Health starts at 25. Mana refreshes on your turn and grows by one colored capacity
at the start of your first main phase each turn, up to ten. Capacity color is chosen when gained. Unspent mana
remains usable throughout opponents' turns. Green can ramp toward the cap and
generate temporary mana; excess temporary mana does not increase permanent capacity.

Click a hand card and select a legal target if required. Costs are paid upfront,
including Ward and explicit health/discard/sacrifice costs. Discard costs prompt
for a card; blue filtering also prompts for a discard after drawing. Costs are
not refunded if an action is countered or its target disappears.

The bottom action bar shows Draw, Main 1, Combat, Main 2 and End checkpoints for
your turn and the opponent's turn. Auto-Pass Priority (the orange **>>** toggle)
is on by default. It passes immediately when the server finds no meaningful
Instant-speed action; otherwise **Respond** gives you a three-second window to
pause it. Mana abilities alone do not create a window, but an Instant affordable
after activating them does. Polling and cosmetic updates never restart the window.

**Respond** pauses only your automation, even while the opponent has priority.
**Pass Once** gives up your priority while retaining manual control.
**Resume Auto-pass** immediately passes the current response opportunity and clears
Hold. Your own main phases still wait for **Enter Combat** or **End Turn** unless
you separately enable **Auto-advance my turn** in Turn settings.

Casting normally passes priority immediately. Arm **Hold Priority** before casting,
including untargeted cards, to retain priority for one response sequence. It remains
paused until Resume. Stack actions resolve one at a time, last in first out;
a changed stack or resolved action creates a new response opportunity. Solo manual
decisions are untimed; multiplayer keeps its normal decision clock and time bank.
Convenience toggles never replenish either clock.

Turns automatically refresh resources and draw, offer a Draw response checkpoint,
then stop for the mandatory first-main mana choice. The same pill progresses through
**Enter Combat**, **Confirm Attacks / Skip Combat**, **End Combat**, and **End Turn**.
Combat responses are labeled **Before attackers**, **Before blockers**, and
**Before damage**. Blocker assignment and required targets/choices always stop play.
Damage and its triggers finish before End Combat enters the second main phase.
End-step triggers enter the stack before the End checkpoint; cleanup follows.

Click a phase checkpoint to add or remove a stop. Choose your turn or the opponent's
turn explicitly. Stops are one-use by default; **Repeat every turn for new stops**
retains subsequent markers until removed. Reaching either kind pauses your auto-pass.
Draw stops happen after drawing; Main 1 stops happen after choosing mana; End stops
happen after end-step triggers are stacked and before they resolve.

Automatic triggers use active-player batches first, then opposing-player batches.
Within each player's batch, insertion order is Global Relics, Equipped Items, then
Creature Abilities, using relic slots, attachment order, battlefield entry order
and printed ability order as stable ties. LIFO reverses that insertion order on
resolution. **Auto-Order Triggers** is on by default. Disable it to choose your own
batch's intended resolution order; targets and required choices pause in either mode.
Continuous bonuses do not enter the stack.

Consumables and abilities show **Instant** or **Sorcery** speed. Sorcery requires
your own main phase and an empty stack. Equipment is Sorcery speed by default;
sockets change between battles. Timing grants name their exact category:
`equip`, `noncreature_sorcery_cast`, or `creature_cast` in `instant_actions` on a
relic definition or public permission source. Flash allows creature casting with
priority; it does not change that creature's activated abilities. All timing grants
retain normal costs, target restrictions and priority requirements. Pure mana
abilities resolve immediately; mana-producing spells still use the stack.

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
offer an additional equipment choice. Ordinary victories grant 2 Essence and
bosses grant 4. Shops also sell equipment for 2 currency. One retry repeats the encounter with the same
seed, allowing owned-card rearrangement first; defeat never grants extra rewards.

## Branching maps, challenges, and treasures

Solo campaigns now offer a left-to-right map for each act: three columns of
branching battles lead to one boss. Start at the left; each chosen battle connects
to the same or neighboring lane in the next column. Other routes are skipped.
Shops and preparation remain available between battles, including free deck
exchanges and equipment changes. The selected route's opponent is shown in
Upcoming rivals. Each location uses temple, open-field, or town-street scenery
with the same battlefield controls.

Choose Normal, Hard, or Custom when creating a solo run. Normal maps contain
1–2 challenge nodes; Hard maps contain 3–4; Custom lets you choose 0–4. These
counts include every available branch, not only battles you will play. Each
marked node randomly has 1–3 distinct challenges:

| Challenge | Effect for this battle | Extra Essence on victory |
| --- | --- | --- |
| Enemy extra mana | Enemy starts with 1 extra mana gem. | +1 |
| Weaker creatures | Your creatures have 1 less attack, minimum 0. | +1 |
| No arrival effects | Your creature/engine arrival effects do not trigger. | +2 |
| Creatures only | Only cast creature cards; activated abilities still work. | +2 |

The total challenge bonus caps at +4 Essence. Map nodes show the exact reward:
2 base Essence for ordinary/elite fights or 4 for bosses, plus the bonus. Losing
awards nothing. A retry keeps the same opponent, route, scenery, and challenges;
deck and equipment adjustments remain available. These initial difficulty weights
need playtesting. Existing saves continue from their current encounter; active
battles retain their original rules. Tutorial and multiplayer rules are unchanged.

Ordinary victories have a 25% treasure-chest chance; bosses guarantee a chest
in addition to their existing equipment choice. A chest grants 1–3 independently
rolled equipment items and 1–3 shop currency, with equal chances for each count.
Items have a 75% base-tier, 20% +1, and 5% +2 chance. Duplicates are separate owned
copies. Odds are displayed before opening. Rewards are awarded and saved once on
victory; the roughly four-second spinning reveal only presents those results.
Skip, Escape, reopening, and reconnecting cannot reroll or duplicate them. Opening
is free. Reduced motion or effects Off uses a stationary reveal; sounds follow
the effects volume and mute controls.

## Quality-of-life controls

Deck and reserve panels offer name/rules search, color/type/cost filters, sorting
by name/cost/copies, and a mana-curve summary. Illegal replacements explain copy
limits before submission. Shop and reward cards show owned/deck counts. Inventory
offers equipment/design search, equipped-status and tier filters, slot labels,
and the Essence shortage for unavailable upgrades. Purchases, upgrades, and shop
refreshes ask for confirmation; free exchanges and equipment changes stay immediate.

Combat controls show planned attacker/blocker counts and let you clear the entire
plan. Rejected submissions preserve the plan. Hovering a legal target shows its
mana cost, colored requirements, Ward, and other applicable costs without opening
automatic card inspection; touch uses the target-preview prompt. Brief pop-ups
explain unavailable creature actions. Both players' graveyards, exile cards, and
engines are public and inspectable; opponent hands and deck order stay private.

Open panels, keyboard focus, and unfinished text input survive live updates.
Collection preferences persist within each room. Connection status recovers after
successful polling; Retry requests an immediate update. Copy room code copies
only the public invite code.

## Equipment, upgrades, and training

Inventory shows three flexible slots, separately owned item copies, and exact
upgrade previews. Equipping and unequipping are free between encounters. Each
item upgrades independently; card upgrades affect every existing and future copy
of that design during the current campaign. +1 costs 3 Essence; +2 costs another
6 Essence, and +2 is the maximum. Currency buys cards and equipment; Essence buys
upgrades. Their costs and effects are shown before purchase.

Equipped duplicates stack additively. Panharmonicon repeats triggered creature
and engine entry abilities, without duplicating their summons. Each base copy
adds one trigger, +1 adds two, and +2 adds three: two base copies give three
triggers total, and three +2 copies give ten total. Existing relic effects have
explicit tier-scaled equipment versions. Old solo saves migrate their relic into
one equipped base item; in-progress battles retain their original state.

**Learn to play** in Rooms starts an optional, replayable mini-campaign in its own
room. Its action-driven lessons cover card stats, mana, playing cards and priority,
blocking and attacking, rewards, card upgrades, the shop, equipment, item upgrades,
and a boss. Announced training resource bonuses fund practice purchases. Restart
training freely; its resources and progress never spend another campaign's funds.

## Saves, timing, and validation

The host stores all rooms and random state atomically in `tactical-save.json`.
Browser session storage holds the active seat; local storage holds recent seats.
Resume from **Rooms** after restarting the host at the same address/port.
Do not delete this browser's saved site data if you need its seat credentials.
Solo simulation pauses when its player stops polling. Shared games keep running.

Solo human decisions are untimed and never transfer to AI control. Automatic
passing is off by default; its checkbox only skips eligible response windows.
Mana growth, attackers, blockers, and discard decisions always require input.
Choose an opponent portrait to inspect its battlefield; all opponents remain in
the battle, and attacker menus let you choose a defender for each creature.

In friend groups, response windows default to 30 seconds, other decisions to 60, with a 60-second
time bank. Expiry passes, skips optional combat/blocking, or chooses a mandatory
color/discard; it never spends mana. Repeated timeouts or a disconnected seat
trigger visible AI takeover. Reclaim restores human control. Optional auto-pass
stops for combat, direct targeting, targeting your pending actions, and global
damage/board-changing effects.

Tests:

```sh
python -m unittest discover -s tests -v
python tests/capture_tactical.py
python tests/capture_tactical.py --tutorial
python tests/capture_tactical.py --qol
```

Browser smoke coverage requires Node and installed Edge (or `EDGE_PATH` pointing
to Chromium). It uses an isolated temporary headless profile and exports screenshots
to `artifacts/tactical-*.png`.

Current content is **46 deck designs, ten commanders with 20 packages, six multiplayer relics and seven equipment designs**.
The expanded roster is available immediately so mono/two-color differences can
be tested. The 150-design target remains ten commanders + 25 designs per color +
15 neutral designs. Replace redundant cards first; expand for demonstrated gaps.
Balance, 20–30-minute pacing, two distinct builds per package, and credible recovery
from poor drafts have **not** been established by automated tests. Record player
reflections alongside elapsed times, spectator waits, concessions and counterplays.
AI is a deterministic public-information heuristic, not a validated expert opponent.

New rooms are strictly 1v1. Solo play automatically supplies one AI opponent;
friend rooms have one guest seat, which the host may fill with a single AI.
Existing larger battles remain intact until completion; subsequent solo
encounters use one rival. Restart the server to load this rules change.
The main 1v1 battlefield uses the illustrated temple table: portraits and public
resources sit beside opposing card rows, with physical deck piles, mirrored commander portrait health orbs,
colored mana gems, and a fanned hand. Ready gems glow and spent gems dim;
mana choices use matching clickable crystals. Full card rules remain in inspection.
Click an untargeted card to play immediately. For targeted cards, select the card,
click a legal target to preview it, and click that same target again to commit.
Choosing another target changes the preview; Cancel/Escape clears it. Mana is
spent only on commit. Select attackers/blockers and click their destinations;
arrows preview assignments before confirming the whole attack/block decision.
On mobile, the table scrolls under persistent guidance, and Expand hand opens a
readable tray which folds when selecting a targeted spell.

At the start of your first main phase each turn (including turn one), choose one mana
gem in the fixed prompt. Opening-hand setup only handles keeping and mulligans.
The mana choice cannot be passed; at 10 permanent capacity, no gem is added.

## RPG item set

The approved item set adds drawn/cast Equipment, three unique loadout Relics,
a two-slot consumable pouch, and reusable socket gems. Equipment replaces deck
cards and each copy must be owned. Preview gem combinations in Inventory before
applying them; item tiers unlock sockets rather than increasing base effects.
Pouch activation permanently spends the item through defeat, retry and reload.
Consumables and gem unlocks have separate shop/reward channels and never replace
chest items. Existing legacy passive items retain their saved behavior.

See [RPG_ITEMS.md](../docs/RPG_ITEMS.md) for printed rules, gem compatibility,
initial prices/drop rates, and current vector-sigil art. Validate with
`python tests/capture_tactical.py --items`.
