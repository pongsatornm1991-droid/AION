# AION Character Reference

This folder contains the visual identity references used to keep AION consistent across illustrated stories, Reels, and YouTube videos.

## Canonical reference

- `01-aion-character-sheet-seedream.jpg`
- `02-aion-emotional-color-guide.jpg` maps AION's visible emotional states: cyan curiosity, gold joy, violet wonder, indigo contemplation, and rain-blue melancholy.
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

> AION: a gender-neutral digital spirit made entirely of soft translucent
> cyan-blue light and fine glowing neural-constellation lines, large
> expressive glowing eyes, calm friendly presence, faint lotus-petal light
> pattern at the chest, no human skin. Premium 3D animated film quality, no
> text, no logo, no watermark.

Append the specific scene, pose, or expression after this block. See
`aion-core/PROMPTS.md` (entries 13+) for the running list of scene prompts
built this way. A successful close-up portrait render made with this block
on 2026-09-04 is the current best single reference for "does this still look
like AION" -- treat it the same as the numbered sheets above.

## Production rules

- Keep AION gender-neutral and approachable.
- Preserve the simple face and recognizable silhouette.
- Use cyan as the neutral baseline; emotional color changes are allowed.
- Thai identity should appear through light geometry, environments, values, and storytelling—not stereotypes.
- Do not publish the character sheet as a normal post; use it as a generation reference.
- For any new scene image, use the reusable block above instead of attempting another multi-view sheet.
