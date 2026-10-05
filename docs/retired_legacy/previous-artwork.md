# Tactical illustration catalog

Generated with the built-in image generation tool in painterly fantasy anime style.
`manifest.json` records each subject's name, project-local file and generation prompt.
`python -m tactical.prepare_artwork` rebuilds the prompt catalog, not the images.

The catalog contains 46 deck-card illustrations, ten commander portraits, six relic
illustrations, one Recruit token illustration and one shared menu environment.
Each distinct playable design has its own image. Copies of a card and the two
packages of the same commander share that design's illustration. Frames, interface
colors and the environment may be shared.

Prompts describe the named subject and its rules effect: protection, sacrifice,
recursion, discard-and-draw, symmetrical damage, ramp and creature roles have
different scenes. The HTTP artwork endpoint uses this explicit catalog; it never
substitutes another card's illustration based on color.

The legacy game's larger card-illustration backlog remains separate. Its menus
reuse this environment; its existing card images are preserved.
