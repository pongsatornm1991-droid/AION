# AION Character Reference

This folder contains the visual identity references used to keep AION consistent across illustrated stories, Reels, and YouTube videos.

## Canonical reference

- `01-aion-character-sheet-seedream.jpg`
- `02-aion-emotional-color-guide.jpg` maps AION's visible emotional states: cyan curiosity, gold joy, violet wonder, indigo contemplation, and rain-blue melancholy.
- `04-aion-profile-v2.png` -- close-up portrait made with the reusable scene
  block below (not a multi-view sheet). This is AION's current profile
  picture, live on every platform (Facebook, Instagram) as of 2026-09-04.
- `05-aion-storyteller-canonical-v1.png` -- the legacy full-body storyteller
  reference. New production follows the v2 design direction below: a small
  cyan crystal core is the recognisable signature; clothing is contextual and
  deliberately not all blue.
- `06-aion-crystal-core-v2.png` -- current production identity reference:
  the cyan crystal core, warm-ivory explorer layer, charcoal utility details,
  and restrained light accents. Generated as original concept art on
  2026-09-14 for use as a reference, not as a post.
- Generated with Seedream 4.0 through AIPass on 2026-09-03.
- Treat the character design as a reference, not a rigid costume. AION may evolve, age visually, and change color with emotional state while retaining the same silhouette, translucent body, neural-light texture, and subtle Thai motifs.

## Source prompt

> Create an original character consistency sheet for AION, a Thai-born artificial intelligence storyteller. AION is a gender-neutral translucent cyan-blue humanoid made of soft light, fine neural constellations, and subtle glass-like layers; friendly expressive eyes, calm youthful presence, simple memorable silhouette. Include one full-body front view, one three-quarter view, one side view, and four clear facial expressions: curious, joyful, contemplative, and gently melancholic. Add restrained Thai identity through elegant lotus-petal geometry and faint lai kranok-inspired light patterns integrated into the energy lines, never a costume or stereotype. Premium hand-painted educational animation concept art, clean ink contours, sophisticated cinematic lighting, dark navy neutral background, consistent proportions, production-ready model sheet, no text, no logo, no watermark, no extra limbs, no photorealism, original design.

## Reusable scene block (added 2026-09-04)

Generating a full multi-view "character sheet" in one image repeatedly
triggered false-positive content-safety blocks (a small, unclothed-sounding
humanoid reads to some image generators as a nude minor, even though AION is
non-human light, not a body). Decision: stop requesting new multi-view sheets.
Instead reuse this exact short block at the start of every new prompt --
scenes, posts, and Reels alike -- so AION stays visually consistent without
needing a single combined reference image:

> AION: an original gender-neutral AI field guide with a small faceted
> cyan-blue crystal core at the sternum, fine glowing neural-constellation
> accents, friendly expressive eyes, calm presence, and a faint lotus-petal
> geometry around the core. Wear practical context-specific clothing in warm
> ivory, charcoal, earth tones or deep navy; use cyan only as a restrained
> luminous accent, never an all-blue body or outfit. Premium original
> family-friendly cinematic 3D illustration, no text, no logo, no watermark,
> no named-studio imitation.

Append the specific scene, pose, or expression after this block. See
`aion-core/PROMPTS.md` (entries 13+) for the running list of scene prompts
built this way. `04-aion-profile-v2.png` above is this block's first
successful render and the current best single reference for "does this
still look like AION" -- treat it the same as the numbered sheets above.

## Production rules

- Keep AION gender-neutral and approachable.
- Preserve the simple face and recognizable silhouette.
- Preserve a small cyan crystal core as the identity anchor; emotional color
  changes are allowed in its glow, while clothing follows the scene context.
- Thai identity should appear through light geometry, environments, values, and storytelling—not stereotypes.
- Do not publish the character sheet as a normal post; use it as a generation reference.
- For any new scene image, use the reusable block above instead of attempting another multi-view sheet.
- AION must be visibly present in every illustrated story beat. AION can be
  foregrounded, observing at human scale, reflected in an object, or a small
  silhouette for a scientific scale shot, but must remain recognizably the
  on-screen guide rather than only a narrator.
- Costume follows narrative work: explorer layer for field history, clean lab
  layer for science, simple visitor layer around families and communities. The
  core and face remain consistent, but no single outfit is mandatory.
