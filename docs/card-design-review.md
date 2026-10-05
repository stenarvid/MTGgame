# Playable card design review

Run `python -m tactical.preview --port 8768` and open http://127.0.0.1:8768/.
This server is local-only, holds its scenarios in memory, and never reads or writes campaign saves.
The review uses the shared card renderer and the production Battle priority/stack engine.
Its additional abilities are attached to fixture instances; they do not enter the released card pool.
Full UI rollout awaits review approval.

Choose a scenario and reset it whenever needed. You control the current priority holder in this
review, so Pass moves control to the next seat. Each opponent's hand stays hidden until that seat
holds priority. Two consecutive passes resolve one stack entry; the active player then gets priority.

- Hover: full card centered over a black fade, effects and keyword explanations on the right.
- Right-click, long-press, or click a card with no available action: persistent inspection.
- Click an eligible creature: ability selection, or Attack/Block choice when both actions are legal.
- Hover a compact ability option or tap its information control for its complete description.
- Choose a target or drag a card toward one. The cyan arrow locks to a legal target.
- Confirm pays costs and queues the action; Cancel or Escape before confirmation spends nothing.
- Orange dashed arrows show pending actions. Cyan arrows show your current selection.
- Escape closes inspection before cancelling a preserved target selection.
- Battlefield effects show three distinct icons plus +N; inspection groups identical effects
  while retaining each source and duration. Mobile explanations appear below the full card.

Scenarios cover main-phase, instant-speed and response-only abilities; attacking and blocking;
protection and counterspell responses; illegal targets after bounce; source removal; and stacked effects.
To exercise source removal, cast Cruel Exchange at the Citadel Recruit while its protection is pending.
The paid ability remains on the stack after its source dies.

Verify: `python -m unittest tests.test_card_preview tests.test_tactical tests.test_artwork`
and `python tests/capture_card_preview.py`. Screenshots are written to artifacts/card-review-*.png.

The desktop review now follows the Arena reference: an open illustrated tabletop, direct battlefield placement, portrait health badges, a curved hand, deck piles, and floating decision controls. Card inspection and rules scenarios are retained.

Response windows now automatically pass only when the rules engine finds no legal,
affordable instant or activated ability. Target legality and Ward costs are checked.
Main-phase, mana, attack, block and discard decisions remain manual. Preview Settings
allows disabling this automation for inspecting individual priority steps.

The temple preview animates card entry, exhaustion, damage, stack entry, resolution,
phase changes and refreshed gems. Settings provides reduced motion and faster animations;
OS reduced-motion preferences are respected. Animations do not block input.

Spell effects are driven by the public `visual_events` feed. Casts, successful resolution,
fizzles and counters are distinct; reconnection never replays old effects. Card effect
profiles cover the current card pool, commanders, tokens and relic designs. Shared effect
families match mechanics and color; these are procedural effects rather than bespoke movie
assets per card. Fire and Meteor scenarios exercise targeting trails, synthesized crackle,
projectiles, showers, and scorch marks. Spell sounds start after a player gesture and can
be muted or adjusted in Settings. Scorch marks expire after 3.2 seconds; particle counts,
DPR, and concurrent marks are capped. Effects don't intercept clicks or alter rules.

Fire targeting now uses layered red flame tongues with turbulent curling tips and a
four-second synthesized fire loop combining low roar and irregular crackles. The
fireball keeps the accepted cast's hand-card origin until it resolves. Meteor showers
include staggered strikes across the open battlefield as well as affected creatures.
