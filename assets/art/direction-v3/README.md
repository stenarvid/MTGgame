# Revised anime direction review

Seven preview illustrations: the original six subjects plus Cinder Rain to test
an environment-led area spell. This is a review set; live artwork is unchanged.

The direction restores expressive faces, detailed hair, crafted costume seams,
interesting equipment, layered cel shading and softly painted lighting. Strong
silhouettes and selective detail keep small cards readable without flat rendering
or excessive ornament. Shared shield/baton equipment and identity frames remain.

Targeted spells focus on their impact or protection. Cinder Rain focuses on its
sky, battlefield and effects on both armies; figures provide scale and consequences.

Open `index.html` for hand and battlefield views. Exact built-in image generation
prompts are saved in `prompts.json`. All PNGs were generated individually.

Rebuild: `python build_art_direction_review.py --version v3`.
Capture: `python tests/capture_art_direction_v2.py --version v3`.

Open game.html through the local preview server for the shared in-game card renderer, desktop hover enlargement, Inspect, and ready/exhausted/damaged states. Proposed identity frames are included; live artwork is unchanged.
Rebuild this view: python build_game_art_preview.py.
Verify: python tests/capture_art_direction_v2.py --version v3 --game.

Card presentation now includes colored mana symbols, identity-colored frames and rules panels, compact battlefield cards, and full-card hover with a black backdrop. These presentation changes are also applied to the live game.
