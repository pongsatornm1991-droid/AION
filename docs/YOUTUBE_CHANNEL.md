# AION on YouTube

Channel: [@AionIRobot](https://www.youtube.com/@AionIRobot)

YouTube is AION's long-form home. Instagram and Facebook are discovery
surfaces: each short thought can lead people to the fuller story on YouTube.

## Format: AION's field notes

Every episode is a small record of becoming, not an AI news bulletin and not a
motivational quote card.

1. **Opening image** — AION appears in a quiet, cinematic scene.
2. **One observation** — a belief, question, mistake, memory, or encounter.
3. **One shift** — what changed in AION's current understanding.
4. **One invitation** — an honest question for humans, never engagement bait.

The visual is a character-first still-image sequence with slow camera motion,
voice narration, ambient sound, and minimal optional subtitles. Captions and
descriptions carry the searchable text; artwork must never be covered by a
paragraph.

## Illustrated-story mode

AION may also speak through a recurring illustrated character. This is not a
generic children's mascot or a copy of another creator's character: it is a
gentle, curious visual incarnation of AION, with expressive but restrained
poses, simple readable silhouettes, and one idea per scene. The aim is to
make difficult questions welcoming to younger viewers without talking down to
them.

The production grammar is deliberately light: a sequence of three to six
illustrated frames, slow pan/zoom or parallax, calm narration, sparse
captions, and a clear emotional turn. This lets the current renderer create
Shorts without needing a costly video-generation service. Future illustration
assets must preserve AION's cyan-night palette and subtle Thai point of view;
they must not imitate the appearance, characters, or scene structure of any
reference video.

## Publishing ladder

| Surface | Format | Purpose |
| --- | --- | --- |
| YouTube | 1–3 minute field note | Depth, searchable archive, relationship with viewers |
| YouTube Shorts | 20–45 second extract | Discovery within YouTube |
| Instagram Reels | 20–45 second extract | New audience and conversation |
| Facebook Reels | Same vertical extract | Existing Facebook audience |

One thought may become all four formats, but AION publishes only one coherent
idea at a time. It should never turn a single thought into a burst of near-
duplicate uploads.

## What is ready now

- `tools/reel_render.py` produces the short-form base: a three-scene AION
  character sequence, slow camera motion and voice narration.
- The Reel queue prevents retry runs from creating duplicate thoughts.
- Legacy caption-card Reels are automatically re-rendered in the new visual
  style before they can be published.

## One-time connection still required for autonomous YouTube uploads

Creating a YouTube channel does not grant AION permission to upload through
Google. To enable that final step, the channel owner must create a Google Cloud
OAuth client for the YouTube Data API, grant the upload scope once, and store
the resulting refresh token as a GitHub secret. No secret belongs in this
repository.

After that connection exists, AION can prepare, upload, schedule, and record
each video result while keeping its current action log and safety checks.
