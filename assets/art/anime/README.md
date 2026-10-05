# Anime artwork

The five-color browser game has 64 unique illustrations: 46 deck cards, ten
commanders, six relics, the Recruit token and a menu environment. Multiplayer and
the solo AI campaign use this same pool. Each commander has one character shared
by its two packages; copies retain their own design's illustration.

The style uses anime outlines, bold shapes and cel shading, with softer scenery
and magical effects. Creature and commander costumes reflect their roles and
colors. Spell illustrations show their actions; relics show recognizable objects.

`manifest.json` records stable design keys, rules concepts, exact prompts and local
PNG filenames. Images were generated individually with the built-in image tool.
`approved-prompts.json` retains the six approved art-direction prompts. Original
prompt documents in the parent directory remain historical documentation.

- `python prepare_anime_art.py`: rebuild the prompt inventory, preserving exact
  prompts for completed images. This does not generate raster files.
- `python artwork_progress.py`: report completed illustrations and missing designs.
- `python build_art_review.py`: build a searchable full-art gallery in `artifacts/`.
- `python tests/capture_anime_art.py`: decode and capture all gallery pages.

Retired desktop cards, pink Morph designs and procedural commander combinations
are not part of this catalog or the current game.
