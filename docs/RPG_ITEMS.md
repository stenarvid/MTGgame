# RPG item set

Approved first batch: 10 cards (two per color), 5 castable Equipment, 3 loadout
Relics, 5 Consumables, and 6 reusable gem families with three tiers.

## Integration

- Three dedicated Relic slots, one active copy of each new Relic name.
- Each Equipment card requires one owned copy and replaces a card in the 30-card
  deck. Modified copies share the base design's two-copy limit and color identity.
- Equipment stays unattached when its bearer leaves. Equip uses the stack and
  sorcery timing. Socket modifications survive zone changes, control changes,
  and copies; token copies never award inventory items.
- Two pouch slots, with a separate owned Consumable for each slot. Activation
  permanently spends the copy, even when countered, fizzled, defeated, or retried.
  Invalid activations and Cancel spend nothing. Consume is a custom cost action.
- Sockets and pouch selections are editable only between battles. Relic and
  Equipment tiers unlock sockets, without increasing their underlying effects.
- Gems are reusable unlocks. Higher-tier unlocks preserve all lower tiers.
  Preview shows the complete result and occupied roles before applying for free.
- Existing legacy passive items and their upgrades retain their saved behavior;
  the playable tutorial continues to teach those items.
- New designs currently use vector sigils. Existing illustrated artwork remains
  unchanged. Card mechanics and printed text do not depend on artwork.

## Initial acquisition tuning

Equipment/Relics retain chest odds and boss item choice. Equipment offers and chest drops fit commander color identity. Consumables and gems
never replace chest contents: independent victory rolls are initially 20% for
one legal Consumable and 10% for one locked base gem. If every gem is unlocked,
that gem roll awards 1 Essence. Defeats award nothing; result guards prevent
repeated rewards. Shops offer legal Consumables for 1 currency and locked gems
for 2. Gem and item upgrades cost 3 Essence, then 6. These are initial tuning
values, separate from the approved rules effects.

## Socket compatibility

Equipment unlocks Bonus, Trigger, Condition in that order. Relics unlock Bonus,
Condition, Trigger. Each item has one/two/three sockets at base/+1/+2.

| Family | Compatible items | Base / +1 / +2 | Reserved roles |
| --- | --- | --- | --- |
| Might | All five Equipment; Smith?s Insignia | Replace stat bonus with +1/+0, +2/+0, +3/+0 | Bonus; Bonus+Condition; all |
| Brood | All three new Relics | Replace condition with creature tokens; higher tiers grant +0/+2 or +0/+3 | Condition; Condition+Bonus; all |
| Vitality | All three new Relics | Attack trigger gives current stat bonus, +0/+2, or +0/+3 until end of turn, plus 1 life per attacker | Trigger; Trigger+Bonus; all |
| Binding | All five Equipment | Attach on entry with +1 generic casting surcharge; remove surcharge; also grant haste | Trigger; Trigger+Condition; all |
| Guardian | All five Equipment | Replace stat bonus with bearer ward {2}, {3}, {4} | Bonus; Bonus+Condition; all |
| Bastion | All five Equipment | Replace stat bonus with Equipment ward {2}, {3}, {4} | Bonus; Bonus+Condition; all |

Higher-tier gems require every named role to be unlocked. Roles reserved by a gem
cannot hold another. Equipment's Condition socket and the Bonus socket on Muster
Standard/Sovereign?s Crest have no standalone gem in this batch; stronger gems
can reserve them. Might does not fit those two Relics, restricting repeated
army-wide attack gems. Original keywords and equip costs survive stat replacement.

Base Might + Brood + Vitality on Smith?s Insignia produces:

> Whenever a creature token you control attacks, it gets +1/+0 until end of turn and you gain 1 life.

There is no trigger cap. The effect is checked per declared attacker. Vitality
replaces the continuous bonus, retaining the agreed temporary stat benefit and
life gain. New ward abilities trigger, use the stack, and let the opponent pay
or decline when they resolve. Legacy Ward keeps the existing upfront surcharge.

Campaign rivals use deterministic curated Relics, gear, and pouch loadouts.
Relics, their gem effects, and pouch contents are public before combat. Gear stays
hidden with the enemy deck/hand until revealed. Humans and AI use the same actions.

## Printed designs

### Cards

**Spire Recruit** - {1}{W}

Creature — Human Soldier

2/2

As long as Spire Recruit is equipped, it gets +1/+1 and has vigilance.

**Stand Together** - {1}{W}

Instant

Target creature gets +2/+2 until end of turn. You gain 2 life.

**Artificer’s Study** - {2}{U}

Enchantment

Whenever you cast an Equipment spell, draw a card.

**Disrupt the Ritual** - {1}{U}

Instant

Counter target noncreature spell unless its controller pays {3}.

**Graveward Squire** - {2}{B}

Creature — Human Soldier

2/3

Whenever an equipped creature you control dies, you may pay {1}. If you do, draw a card and lose 1 life.

**Cut Down the Weak** - {1}{B}

Instant

Destroy target creature with mana value 3 or less.

**Forgefire Raider** - {2}{R}

Creature — Human Warrior

3/2

Whenever Forgefire Raider attacks, if it’s equipped, you may discard a card. If you do, draw a card.

**Cinder Strike** - {1}{R}

Instant

Cinder Strike deals 3 damage to target creature.

**Wildsteel Tender** - {1}{G}

Creature — Elf Artificer

2/2

Whenever you cast an Equipment spell, put a +1/+1 counter on target creature you control.

**Break the Armory** - {1}{G}

Instant

Destroy target artifact.

### Equipment

**Spiresteel Blade** - {1}

Artifact — Equipment

Equipped creature gets +1/+0.
Equip {1}

**Dawnward Shield** - {1}{W}

Artifact — Equipment

Equipped creature gets +0/+2 and has vigilance.
Equip {2}

**Embercleave Axe** - {1}{R}

Artifact — Equipment

Equipped creature gets +2/+0.
Equip {2}

**Gravebound Fang** - {1}{B}

Artifact — Equipment

Equipped creature gets +1/+0 and has lifelink.
Equip {2}

**Rootbreaker Maul** - {2}{G}

Artifact — Equipment

Equipped creature gets +2/+2 and has trample.
Equip {3}

### Relics

**Smith’s Insignia**

Relic

Equipped creatures you control get +0/+1.

**Muster Standard**

Relic

Nontoken creatures you control get +0/+1.

**Sovereign’s Crest**

Relic

Legendary creatures you control get +0/+1.

### Consumables

**Healing Draught**

Consumable

{1}, Consume Healing Draught: You gain 3 life.

**Ember Flask**

Consumable

{R}, Consume Ember Flask: It deals 2 damage to target creature.

**Mistveil Vial**

Consumable

{U}, Consume Mistveil Vial: Target creature you control gains hexproof until end of turn.

**Barkskin Tonic**

Consumable

{G}, Consume Barkskin Tonic: Target creature gets +1/+2 until end of turn.

**Militia Beacon**

Consumable

{1}{W}, Consume Militia Beacon: Create a 1/1 white Soldier creature token. Activate only as a sorcery.

## Validation

Run `python -m unittest discover -s tests` and
`python tests/capture_tactical.py --items`. Item browser fixtures use isolated
saves and check desktop/mobile inventory, socket previews, owned-deck exchange,
spending cancellation, attachment, inspection, consumption and reload persistence.
