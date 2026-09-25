# Active AI work claim

This is a small, overwrite-in-place coordination board for Codex and Claude.
It prevents concurrent sessions from editing the same release path. It is not
a historical log: replace this block when taking a task, and set status to
`clear` when handing off. A claim expires at its stated time so a crashed
session never blocks the company indefinitely.

Status: clear
Owner: none
Started: n/a
Lease expires: n/a
Scope: None.
Handoff: See docs/ai-session-log.md's three 2026-09-26 entries for full
detail (commits f69b858, af28e02, 63970ef, 92fc52f, 34512b1). Quick summary
of where things stand:

1. AION's identity signature is a glowing cyan question-mark held in one
   hand (not a chest core, not a crystal) -- updated everywhere it's
   described/generated. Existing reference PNGs still show the old crystal
   visually; no new reference image rendered yet.
2. YouTube uploads now send real per-video search tags and a plain title
   with no "EP. NNN —" prefix (display_title, with the prefix, is still
   used internally on the Operations dashboard/work-queue).
3. Verified (not just assumed) that custom thumbnails and Facebook/
   Instagram cross-posting are both working correctly on the real channel
   right now -- no code change needed for either.
4. Added a subscribe call-to-action to the video description
   (YouTubeCreatorQueue.SUBSCRIBE_CTA).
5. dashboard/operations.html now renders the `integrity` alerts and the
   5-lane `portfolio` (content-pillar) mix that were already in the JSON
   but never shown. `tools/creator_competitive_scan.py` is a YouTube Data
   API scan of AION's own niche, giving the previously-dead
   `youtube_discovery` source registry entry a real, scoped job
   (title/view-count pattern scouting, never episode evidence). `series`
   (episode.py) and `ResearchPortfolio`'s 5 fixed topic lanes both already
   implement "sub-series" -- no schema change was needed there.
6. The competitive scan now runs daily on its own: `.github/workflows/creator-competitive-scan.yml`
   (02:15 UTC) → `brain/creator_competitive_scan_cycle.py` (dedupes per
   day, keeps top 15 results) → persisted into the separate
   `aion-memory-data` repo, not this one. Quota checked and safe (see
   session log).

Nothing urgent open. The owner has been told, and agreed, that the
easy/code-findable technical gaps in this pipeline are largely closed for
now -- what's next needs real time and view/subscriber data to accumulate,
not more speculative code changes. Still explicitly deferred: wiring real
engagement data into topic/hook decisions (revisit once there's more
channel data), and a Thai-language evidence source (Wikipedia calls are
hardcoded to en.wikipedia.org; noted as a gap, not acted on since it
implies a bigger call about the channel's target language). The recovery
catalogue (brain/initiative.py) is still correctly at 0/57 fresh topics
with its 21-day cooldown safety net not yet eligible -- an expected state,
not a bug, per the 2026-09-25 entries.
