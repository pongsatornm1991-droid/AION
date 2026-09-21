# AION Named Visual Styles

Reference catalog for the per-episode illustration styles the render pipeline
recognizes. `episode["visual_style"]["id"]` selects one of these in
`brain/creator_scene_production.py`'s scene/cover prompt builder — that file is
the source of truth for the exact prompt text; this doc explains what each
style is and why, for anyone briefing Studio or reviewing an episode without
reading Python string literals.

An episode's style must also be explicitly approved to enter the release
queue: `visual_style.approved: true` (see `brain/youtube_creator_queue.py`,
`docs/ai-session-log.md` 2026-09-21). This catalog does not decide approval by
itself -- a style being documented here is not the same as a given episode
being cleared to publish.

## aion-neon-graphic-science-v1 -- "AION Neon Graphic Science"

Also described as Sci-Fi Graphic Novel Illustration (Pop-Science Halftone
Style). Used for `aion-wonders-005-venus-flytrap-counts`. Four pillars:

1. **Comic Book & Pop Art (halftone texture)** -- vintage comic-print
   halftone dots as a background texture, giving the image depth and a
   graphic-novel storytelling feel instead of a flat illustration.
2. **High-contrast line art (ink-navy outlines)** -- strong outlines in a
   dark navy ink tone rather than pure black, keeping the linework crisp and
   comic-like while staying softer and more premium than solid black.
3. **Neon & cyber-science aesthetics, used with intent** -- a synthetic neon
   palette against a dark background, reserved for elements that matter
   (a mechanism, a moment of insight, an energy signal), never scattered
   indiscriminately across the frame.
4. **Dramatic vignette lighting** -- a radial gradient from a dark edge into
   a bright focal point, drawing the eye to the center of the frame like a
   spotlight in a dramatic scene.

Current implementation (`creator_scene_production.py`) renders this as: strong
dark-navy ink outlines, controlled halftone-dot texture, shallow cel-shaded
depth, clean geometric colour shapes, and a near-black-indigo-to-electric-cobalt
radial gradient that brightens only behind the one focal mechanism. Within
that neon palette, colour is assigned by narrative role rather than by a fixed
set of hues: amber = observed input, coral = the answer/threshold, fresh green
= the subject, cyan = reserved only for AION's small signature. One mechanism
per frame, sparse background, no text/logos/photorealism/anime/clutter, never
imitating a named artist, studio, channel, mascot or franchise.

Note for review: the functional colour roles above (amber/coral/green, cyan
reserved for AION) are narrower than "electric cyan, hot magenta, cyber
yellow" as literal palette entries -- cyan is deliberately held back for
AION's identity signature across the whole channel (see
`core/visual_identity.md`), not used as a general neon accent. If magenta/
yellow-style neon accents are wanted in the mechanism/energy elements
themselves, that is a deliberate palette change to make in
`creator_scene_production.py`, not just a documentation update.

## aion-illustrated-postcard-v1 -- Illustrated Postcard

Original hand-painted watercolor and gouache illustrated-postcard look: soft
rainy-season atmosphere, visible paper grain, gentle pigment blooms, warm
everyday Southeast Asian setting. Used for the Thailand-set episodes
(`aion-gentle-thailand-rice-journey-v1`, `aion-illustrated-postcard-after-rain-v1`).

## aion-vivid-storyworld-2d-v1 -- AION Vivid Storyworld 2D

Flat editorial science illustration: clean consistent linework, simplified
geometric forms, deliberate paper-grain texture, large readable colour blocks,
selective atmospheric depth, one dominant object/mechanism per frame. Deep
navy/cobalt for the question, warm amber for observed evidence, fresh green or
coral for the answer, cyan only as AION's tiny signature. No photorealism, no
3D, no anime.

## aion-animated-documentary-v1 -- Animated Documentary

Premium 2D animated documentary illustration: clean expressive linework, soft
cel shading, cinematic painted depth and textures, friendly intelligent
characters, all-ages educational mood.

## aion-thoughtscape-director-v1 / aion-original-warm-3d-storytelling-v1 -- Thoughtscape / Original Warm 3D

The channel's original default: a per-story "AION Thoughtscape" direction
composed from that episode's own creative deliberation (premise, world, mood,
palette/material, rendering rule), but always anchored to the channel's core
Visual DNA -- original warm 3D educational storytelling with readable staging,
rounded appealing forms, tactile natural materials and gentle cinematic light.
`story_episode_stager.py` stamps this as the default style (and pre-approves
it) for ordinary auto-staged AION Wonders episodes.

## Fallback (no recognized id)

Original premium family-friendly cinematic 3D character with photorealistic
lighting, material texture and environment; never imitate a named studio or
franchise. This is what an episode gets if `visual_style.id` is missing or
unrecognized -- it is a rendering fallback only, not an approval: the release
queue still requires `visual_style.approved: true` separately.
