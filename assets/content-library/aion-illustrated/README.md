# Illustrated AION starter library

This is AION's first original illustrated three-scene arc. It is intentionally
small so that future images are added only when a new thought needs them.

1. `01-curiosity-violet-pond.png` — a question takes form.
2. `02-reflection-indigo-rain-city.png` — the question is held against the
   human world.
3. `03-momentum-amber-horizon.png` — AION carries a revised understanding
   forward.

The renderer uses the three frames in this order for illustrated narration.
They are original generated assets for this project; no reference-video
characters, artwork, audio, or scene sequence is reproduced.

## Character-forward scenes (added 2026-09-04)

Three more stills, built from `aion-core/PROMPTS.md` prompts 13-15 using the
reusable character block in `aion-character/README.md` (see that file for
why: multi-view character sheets started triggering content-safety false
positives, so scene consistency now comes from repeating one text block,
not from a single reference image). Not yet wired into `reel_render.py`'s
selection logic -- currently reference-only, same as the numbered sheets in
`aion-character/`.

4. `04-rain-window.png` — AION at home, rain on the glass (prompt 13).
5. `05-canal-blue-hour.png` — AION beside a canal at dusk (prompt 14).
6. `06-garden-dusk.png` — AION in a tropical garden at dusk (prompt 15).

Minor known drift: `04` and `05` render AION's head with a slightly
different silhouette (a teardrop peak) than `06` and the profile picture
(rounded). Expected, since each render is built from the text block alone
with no image reference -- worth a light touch-up pass, or feeding
`04-aion-profile-v2.png` as an image reference (not just text) to the
generator if/when it supports that, before these ship as regular posts.
