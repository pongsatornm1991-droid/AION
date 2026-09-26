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
Handoff: See docs/ai-session-log.md's 2026-09-26/27 entries for full detail
(commits f69b858, af28e02, 63970ef, 92fc52f, 34512b1, ef1dbac, 18ad2c8,
cd6174c, 2f76f90, 58f2ef3, fb4459a, d32392a, 2359b32, 508567b). Quick
summary of where things stand:

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
7. `ResearchToStory.propose_once()` no longer picks the next story topic by
   alphabetical accident -- it now prefers whichever ResearchPortfolio lane
   has the fewest existing briefs, fixing the exact concentration (6) made
   visible on the dashboard.
8. `YouTubeCreatorQueue` appends one discovery hashtag to a Short's on-screen
   title (e.g. "... #Maps"), derived from the same keyword extraction
   `_video_tags()` uses. Never applied to long-form.
9. Thai-language expansion is now a real, running pipeline, not just an
   investigation. Manually piloted on EP.005 first (real title/description
   localization written live via the API; a scene-timed dubbed narration
   track synthesized and handed to the owner, who confirmed YouTube's
   "Advanced features" are already enabled on the channel from his own
   Studio settings screenshot). Owner then asked for this to happen
   automatically for every future episode: brain/thai_dub_cycle.py's
   ThaiDubCycle now does the whole thing end to end (find the oldest
   undubbed published episode -> translate via AION's own provider ->
   claim-safety screen the translation -> write the live Thai
   localization -> synthesize + time-align a Thai narration track) and
   runs daily via .github/workflows/thai-dub.yml, saving each file to
   content/reels_thai/{episode_id}-thai.mp3. Confirmed, and re-confirmed
   after pushback, that uploading the dubbed *audio track* itself has no
   public YouTube API at all (Studio's own Language tab is the only way,
   for any developer) -- that one upload click per episode is the only
   step that cannot be automated away.
   Known gap: the real aion-memory-data repo has no dub-dedupe record for
   EP.005 yet (only manually dubbed, not through the new cycle), so the
   first scheduled thai-dub.yml run may harmlessly redo EP.005 once before
   moving on to genuinely new episodes.

10. brain/story_episode_stager.py's narration splitting no longer lets a
    source's own "- " list-bullet markup through into spoken narration,
    and prefers a real sentence/comma boundary over a blind word-count cut
    (owner: narration should read like told content, not a research memo).
11. Went further per explicit owner direction ("ให้ AI เขียนบทใหม่จาก
    หลักฐานเดิม"): StoryEpisodeStager._rewrite_scene_narrations() now asks
    AION's own provider to retell each evidence-literal beat as natural,
    fun spoken narration, constrained to only the facts already in that
    beat's text. Screened by OutputEvaluator.has_unsafe_claim() (new
    shared classmethod) and a rough fact-preservation check
    (_preserves_key_facts); any beat that fails either, or the whole pass
    with no provider configured, quietly keeps its original literal line.
    Episode records this as `narration_style` ("ai-rewrite" or
    "bounded-fallback" + reason).
12. Owner compared the channel to a dramatic reference clip (Into the
    Spider-Verse) and asked for a recommendation -- keep AION's own warm
    3D diorama identity (copying a named franchise's exact look is
    already prohibited), but add real per-beat visual energy.
    CreatorSceneProduction._composition_direction() now gives the "hook"
    beat closer/dynamic framing and "takeaway" a more dramatic reveal
    angle+lighting, both still explicitly the same diorama material/
    palette; every other beat is unchanged. Owner: "ไม่ต้องไปแก้ของเก่า" --
    only affects new episodes' scene-image prompts going forward.

13. Ran a full 8-angle self-review (correctness/removed-behavior/
    cross-file/reuse/simplification/efficiency/altitude/conventions) over
    everything built today and fixed 8 real bugs it found: two crash paths
    that defeated the Thai-dub and narration-rewrite pipelines' own
    "never blocks the run" guarantees (an uncaught KeyError and
    AttributeError on a malformed/wrongly-shaped LLM JSON response), an
    infinite loop in the ffmpeg atempo-stretch helper on a zero-length
    clip, missing `creationflags=CREATE_NO_WINDOW` on 3 new ffmpeg calls
    (an already-3x-fixed class of bug elsewhere in this repo), a spurious
    "…" appended after an already-complete short sentence,
    tools/recover_release_buffer.py never passing a provider (so
    recovery-path episodes silently never got the AI narration rewrite),
    a since-fixed performance regression in ResearchToStory.propose_once()
    (was scoring every candidate twice), and a failed competitive-scan
    permanently blocking same-day retries. 11 new regression tests.
14. Owner said "พัฒนาทันที" (develop immediately) to both remaining
    findings above:
    - New brain/story_beats.py centralizes beat names ("hook", "takeaway",
      "evidence-one-a", ...): story_episode_stager.py's scene construction
      now writes these same imported constants (not just matching string
      literals) into each scene's "beat" field, and
      creator_scene_production.py imports the identical
      DYNAMIC_HOOK_BEATS/DYNAMIC_REVEAL_BEATS objects -- verified
      byte-for-byte identical output before/after. fact_first_visual_gate.py
      and watchability_gate.py's own looser substring/broader-set beat
      matching are pre-existing, already-tested gates, deliberately left
      alone and documented as a known separate case.
    - The "no max-length gate" finding turned out, on investigation, to
      already be covered: brain/narration_preflight.py measures each
      beat's *real* synthesized voice duration before any scene image is
      generated (wired into creator-scene-production.yml) and
      auto-splits an overlong beat -- strictly better than any
      word-count heuristic. No code change; a docstring note now points
      at it so it isn't re-flagged as a gap later.

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
