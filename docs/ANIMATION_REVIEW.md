# Playable animation review

Run `python -m tactical.preview --port 8768`, then open http://127.0.0.1:8768/?scenario=fire&presentation=1&v=animation-4.
Use Next scene to cycle Fireball, countered Fireball, Meteor Rain, blocked combat, protection/response, creature arrival, commander arrival, countered arrival, exile, and return-to-hand.
The review keeps your camera and private hand fixed. Let Mira respond controls the opposing response without exposing hidden cards. Cast commander is available in its entrance scenario.

Rules apply immediately. Public visual events carry public card details, combat assignments, and before/after health and battlefield snapshots; effects never need opponents? private cards. Cast charges remain pending until resolution, and cost payment does not imply impact. Meteor Rain remains one resolution.

Settings provide separate effects, ambience and optional music volumes, reduced motion, faster animations and effect intensity. Sounds begin after a user gesture. A new action can finish presentation immediately without delaying play. Ordinary combat shakes only damaged cards. One 100 ms battlefield jolt, capped at 3 px, marks commander damage of at least 5 (20% of starting health) in a combat resolution or lethal damage.

The shared animation layer is loaded by both the review and game. This review establishes the animation language; individual card signatures can be refined after motion and sound review.

Effects run automatically during ordinary selection, casting, and resolution. The scenario selector changes the starting state; it does not itself cast a card.

The review also includes Measured Insight (`wisdom`), Null Sigil (`counterseal`),
Cruel Exchange (`shadow`), Unearth (`revival`), Verdant Surge (`growth`), Cultivate
(`roots`), Disrupt Engine (`shatter`), and United Front (`rally`). Next scene cycles
through these alongside the existing fire, combat, and arrival scenes.

Non-fire spells have sustained pending seals and illustrated selection auras.
Resolution uses layered ink outlines and cel highlights: blue waves and open
grimoires, black tendrils and grave portals, green branches and leaf silhouettes,
white shields and formation banners, and angular neutral crystal fragments.
Leaves, pages, drops, shards, and stars have distinct geometry. Family-specific
sound tones accompany the visual sequences. Offscreen targets fall back to public
player summaries; hidden hands are never consulted for opposing cast artwork.

Reduced motion removes animated selection auras and sustained moving charges;
resolved effects use brief stationary cues. Setting effect intensity to Off clears
active effects. `python tests/capture_card_preview.py` verifies family pending
charges, real resolutions, cleanup, mobile review, and reduced motion, and saves
`artifacts/card-review-<family>-pending.png` and `-impact.png` snapshots.

Production also presents opening-hand deals, ordinary draws (only card backs for
opponents), mana gain/spend/refresh, turn/phase accents, portrait damage/healing,
and victory/defeat feedback. These additions use public state or the viewer's own
hand, never another player's private cards. Resource motion is interruptible;
reduced motion uses short stationary brightness cues and Off suppresses it.
Ambient scenery clears outside battles and delayed impact callbacks cannot affect
a subsequent battle after cancellation.

Earned campaign treasures have one illustrated reel per awarded item, ticking
audio, a slowing finish, and stronger upgraded-item highlights/chimes. The server
awards and saves every item before presentation. Skip and reduced-motion reveals
show the same result immediately. `python tests/capture_tactical.py --qol` checks
reel landing, replay without additional rewards, public zone inspection, desktop
and mobile scenery, and settings behavior.

## Combat and item feedback

Creature attacks use 70 ms anticipation, a 110 ms accelerating lunge to edge
contact, a 45 ms hold, and a 140 ms eased recoil. Edge contact preserves the
other card's readable stats. Contacts stagger by 80 ms, compressed for crowded
combats so motion, deaths, and damage fades finish within 900 ms. Blockers deal
their return damage at the same collision. Public per-hit records include actual
and attempted damage, source, target, and remaining health; no private zones
enter this feed. Server state and controls update immediately.

Actual damage uses a 40 ms number pop and 450 ms fade beside the card, plus a
120 ms local shake. Hits removing at least half the recipient's remaining health
are heavy; lethal damage takes precedence and uses a brief fracture and 220 ms
buckle. Prevention reacts at the shield boundary; full prevention says Blocked.
Healing gathers inward for 180 ms and uses a stationary +N number, including +0.
New effects start immediately and replace competing local decoration. There is
no presentation queue or temporary rewrite of health labels.

Target previews use thin lines and steady outlines. Casts retain restrained
pending seals; resolution produces mechanical family cues colored by identity.
Impact callbacks synchronize spell damage and removal with projectile arrival.
A countered pending seal shatters at its source into capped crystal shards with
optional shattering audio. Subtle effects use a 120 ms inward collapse; reduced
motion uses a stationary fade. Both retain Countered for 450 ms and produce no
target impact. Audio follows the separate sound setting in every visual mode.

Creature placement takes 160 ms plus a 60 ms settle/edge cue. Draws deal from the
public deck in 180 ms with 50 ms stagger; opposing cards remain backs. Desktop
hover lift takes 100 ms and returns in 80 ms, without bounce or cursor tilt.
Production targeting/reconfirmation, combat confirmation, inspection, and mobile
hand controls retain their existing interactions.

Inventory sockets expose occupied gem anchors. Successful socketing snaps the
gem in over 140 ms, flashes the socket for 80 ms, then sends a 180 ms pulse into
the changed printed rules. Equipment connects to its recipient over 160 ms and
highlights the resulting stat/ability for 250 ms. Relic resolutions pulse their
public source and connect to the recipient over 180 ms; identical source,
recipient, and effect cues received together are grouped with ×N. Separate rules
resolutions stay separate. Upgrades highlight their result; this adds no fusion
or status mechanics. Applied statuses remain static icons with grouped counts
and inspection details rather than continuous particle loops.

Reduced motion uses low-intensity stationary boundaries and stationary numbers:
no attack displacement, shakes, moving links, buckles, or draw movement. Effects
Off removes visual cues. Every overlay ignores pointer input and cleanup cancels
delayed callbacks across battles. Sounds are optional, combat taps are capped in
frequency, and gem changes use a short chime.

Validation adds public-hit/prevention tests and browser checks for simultaneous
blocked feedback, the presentation budget, socket pulses, reduced sockets, and
cleanup. Captures include combat impact, a desktop socket before/impact comparison, and
mobile socket impact alongside the existing battlefield and inventory screens.
