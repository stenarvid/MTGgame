# Art direction review, version 2

Six preview illustrations and proposed frames for approval before a full rollout.
The live game's catalog and frames are unchanged.

Open `index.html` to compare 190-pixel hand cards and 135-pixel battlefield cards.
Expand each sample to inspect its full art and exact prompt. Elya's signature
sun-disk kite shields and wave-tip baton connect her to the simpler equipment
of the white recruit and blue apprentice. The protection spell uses that shield.

Borders have distinct identity motifs; Elya's frame cuts white/blue equally at
the center and combines shield/wave motifs. Commander crests and relic artifact
frames provide hierarchy while rules and costs keep consistent positions.

Each PNG was generated individually with the built-in image tool. Exact prompts
are in `prompts.json`. Frames use HTML/CSS and original SVG motifs.

Rebuild with `python build_art_direction_review.py`. Capture and check image
loading with `python tests/capture_art_direction_v2.py`.
