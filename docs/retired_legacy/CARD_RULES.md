# Where card behavior is implemented

`cards.json` defines card names, types, costs, colors, stats, displayed rules text,
and (for the expansion) structured trigger definitions. English `text` is display
text only: changing it does not change gameplay. Keep it consistent with the code.

## Loading

`models.py:load_game_data` builds the pool from archetype boosters, starters, and
expansion cards. `Card.from_dict` creates playable cards with their printed stats.
`engine.py:Run.card_choices` supplies matching-color rewards and merchant stock.

## Original card effects

`engine.py:Battle.play` validates phase, mana, and targets before putting a spell
on the stack. `pass_priority` resolves its newest entry through `resolve_card`.
Original spells are selected by name in `resolve_card`: for example, Magma Bolt
calls `spell_damage` against the opposing hero. Its JSON text is not parsed.

Other original abilities live in `summon` (Legion Vanguard), `enter_effect`
(Phase Shifter, Dawn Medic, Tide Scholar), `cleanup_deaths` (Crypt Ghoul and Soul
Collector), `start_turn` (Titan Overseer), and `damage_plan` (Guard and Trample).
`targets` declares legal targets. Renaming an original card can break its effect
unless the corresponding name checks are updated too.

## Data-driven expansion triggers

`trigger_rules.py:TriggerRules.ability` finds a card's `trigger` by its name.
Example for Dawn Musterer:

```json
"trigger": { "event": "attack", "effect": "tokens", "amount": 1 }
```

`attack_triggers` or `emit_trigger` detects the event. `queue_trigger` places an
ability onto the stack. `resolve_trigger` performs the structured effect when
priority is passed. Its amount comes from JSON, so changing `amount` changes the
effect (also update `text`). Supported events are `attack`, `enter`, `ally_enters`,
`ally_dies`, `enemy_dies`, `dies`, `spell_cast`, and `land`. Supported effects are
`search`, `copy`, `tokens`, `draw`, `heal`, `damage`, `drain`, `recall`, `land`, `team_buff`,
and `self_buff`. Copy targets are chosen before blockers and copied tokens are
exiled at turn end. The `land` trigger means playing a land; the `land` effect
searches lands into play tapped without triggering a land-play event.

New cards using these existing trigger combinations need a unique name, valid
stats/color/archetype, a supported trigger, and matching text. An entirely new
event or effect requires Python implementation and tests. Original spell effects
are still name-based; adding spell text alone does not implement a new spell.

## Commander abilities and unlocks

`data/commander_passives.json` and `commander_actives.json` contain base choices.
Their named effects are implemented in `engine.py`. `engine.py:UNLOCKS` defines
achievement requirements and rewards; `Progress.check` persists earned names in
`save.json`. `Run.record` tracks new achievement counters within the run.

Run validation from the project root: `python -m unittest discover -s tests -v`.

## Structured spells in the second expansion

The 50 new spells use `spell` definitions interpreted by `spell_rules.py`.
`target` is null (no target), `friendly` or `enemy` (creatures), or `any` (creatures
and heroes). Every declared target is validated before mana payment and again
on resolution. `effects` is an ordered list of effects with numerical amounts:

```json
"spell": {
  "target": null,
  "effects": [{"effect": "tokens", "amount": 2}, {"effect": "draw", "amount": 1}]
}
```

Supported effects: tokens, heal, draw, armor, drain, damage, area_damage, buff,
team_buff, blink, bounce, destroy, recall, search, ramp. `buff` additionally uses
`power` for its attack bonus and `amount` for health. Buffs last until turn end.
Upgrading a spell increases numerical effects by one; it does not duplicate
blink/bounce/destroy. `ramp` puts searched lands into play tapped, while `search`
puts them into hand. New effects require implementation and regression tests.

## Curated card identities

`data/refine_cards.py` defines the reviewed expansion abilities and generates both
`cards.json` rules text and the catalog. Edit these curated definitions when making
changes that must survive expansion regeneration. `identity_rules.py` implements
specialized tokens, filtered buffs, looting, mill, spell recovery, reanimation,
armor, life payment, freezing, sacrifice, untapping lands, and keyword grants.

Effects can include `condition`, `scale` and `cap`. Conditions evaluate current
state; chained effects resolve in the written order. A triggered ability's initial
condition is checked when it would trigger and again when its first effect
resolves. Its explicitly listed follow-up effects resolve in order. `then` adds
follow-up effects to a trigger. `once_per_turn` gates a source's trigger using a
saved turn serial. `selection` restricts group effects to tokens, nontokens,
attackers, small creatures, or all creatures. `permanent` controls group-buff
expiry. Keywords are `haste`, `guard`, `trample`, and `vigilance`.

`copy_mode` distinguishes default temporary full-size copies, `small` temporary
1/1 copies, and `permanent` copies. Printed stats/keywords are copied; unrelated
battlefield buffs are not. New token templates specify name, color, attack, health,
keywords and rules text. Tokens still retain independent game state and only share
a UI pile when their relevant properties match.
