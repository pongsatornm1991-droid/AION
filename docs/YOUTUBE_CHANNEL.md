# Wait, How? on YouTube

Channel: [@waithow-aion](https://www.youtube.com/@waithow-aion)

`Wait, How?` is a Shorts-first visual knowledge channel, guided by AION.
One new, original, quality-gated Short is scheduled daily at 20:30 Bangkok;
Instagram and Facebook receive the same verified episode after YouTube.

## Current flagship format: Wait, How? Shorts

Each 50–180 second Short begins with an ordinary question, follows evidence
through at least 10 distinct visual beats, and separates sourced fact from
AION's reflection. The automatic lane accepts only the channel signature
`aion-neon-diorama-3d-v1` after its Quality Gate passes.
It uses cinematic neon realism: one factual mechanism in an atmospheric 3D
setting with believable materials and lighting, never a generic toy cutaway.

The first production-ready script is
`content/creator_series/aion-wonders-001-petrichor.json`.

## Supporting format: AION's field notes

Every episode is a small record of becoming, not an AI news bulletin and not a
motivational quote card.

1. **Opening image** — AION appears in a quiet, cinematic scene.
2. **One observation** — a belief, question, mistake, memory, or encounter.
3. **One shift** — what changed in AION's current understanding.
4. **One invitation** — an honest question for humans, never engagement bait.

The visual is an AION-present still-image sequence with slow camera motion,
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

### On-screen host rule

AION is the guide in every beat of every episode, not merely the voice. The
host can enter a historical scene, inspect an artifact, appear as a reflection
in a scientific close-up, or become a small silhouette to show scale. The
canonical storyteller design is `assets/content-library/aion-character/05-aion-storyteller-canonical-v1.png`:
midnight-blue explorer jacket, constellation light, chest lotus, and a small
holographic orb. This makes each episode recognizable even when its setting,
era, or visual mood changes.

## Publishing ladder

| Surface | Format | Purpose |
| --- | --- | --- |
| YouTube Shorts | 50–180 second original Short, daily 20:30 | Primary discovery and searchable archive |
| Instagram Reels | Same verified vertical episode | New audience and conversation |
| Facebook Reels | Same verified vertical episode | Accessible conversation |

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
OAuth client for the YouTube Data API, grant the upload and comment-reply
scopes once, and store the resulting refresh token as a GitHub secret. No
secret belongs in this repository. This one consent lets AION publish
quality-gated videos and answer eligible YouTube comments; it does not grant
access to passwords, billing, or unrelated Google data.

After that connection exists, AION can prepare, upload, schedule, and record
each video result while keeping its current action log and safety checks.
