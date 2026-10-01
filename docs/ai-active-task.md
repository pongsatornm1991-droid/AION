# Active AI work claim

This is a small, overwrite-in-place coordination board for Codex and Claude.
It prevents concurrent sessions from editing the same release path. It is not
a historical log: replace this block when taking a task, and set status to
`clear` when handing off. A claim expires at its stated time so a crashed
session never blocks the company indefinitely.

Status: clear
Owner: Codex
Started: 2026-10-02 Asia/Bangkok
Lease expires: completed 2026-10-02 Asia/Bangkok
Scope: Completed: motion production and Creator assembly now drain up to five
ready episodes in one bounded run, so bot-authored commits cannot leave later
episodes waiting for a daily/hourly recovery tick. Existing per-episode
motion, timing, render, subtitle, and video-quality gates remain mandatory.
Handoff: See docs/ai-session-log.md's 2026-09-26/27 entries for full detail
(commits f69b858, af28e02, 63970ef, 92fc52f, 34512b1, ef1dbac, 18ad2c8,
cd6174c, 2f76f90, 58f2ef3, fb4459a, d32392a, 2359b32, 508567b, 82a7b1b,
2849873, 8b6bbcd, 806fd12, aedfaea, fc7c8a3, fe19e99, e0f17e0, eeb5c5a, 083091b, 9977956, abcc207, b4cc255, 477a32f, ba35fdf, 74fd33e, 132537d, 619b660, 7979703). Quick summary of where things stand:

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

15. .github/workflows/thai-dub.yml (created 06:26 UTC 2026-09-26, cron
    14:30 UTC daily) had zero runs by ~16:00 UTC the same day, confirmed
    via GitHub's own Actions API (state: active, but 0 total runs past its
    first scheduled window). Not a YAML/code bug -- creator-competitive-scan.yml
    (same commit batch) fired correctly at its own 02:15 UTC schedule, so
    this looks like GitHub's documented "a scheduled run can be delayed or
    dropped under high load" behavior, plausible given ~57+ scheduled
    workflows on this repo. Worth checking again after a few more days; if
    it's still not firing by then, that's a real problem to escalate, not
    just a one-off.
16. Ran the Thai dub pipeline for real for the first time (owner asked
    why the newest clip had no Thai version) and found 3 real bugs no
    test had caught, all fixed: ThaiDubCycle kept a relative root as-is
    (broke the ffmpeg concat step's output path once cwd was set to a
    temp dir); synthesize_thai_voice's retry budget (3 attempts) wasn't
    always enough for the real, sometimes-degraded edge-tts backend
    (raised to 5, failures now logged instead of silently swallowed);
    and _published_candidates() picked oldest-first, which -- combined
    with 12 already-published episodes having no dub yet since the
    feature launched after them -- meant a brand new release would queue
    behind that whole backlog for ~12 days. Now newest-first, plus a new
    dub_batch(limit=3) so the backlog also clears in days. Manually
    dubbed the fireflies episode (TsGxyRCTcaE) for real once fixed:
    content/reels_thai/aion-auto-0b5a0385b87d-7d3a5028-short-thai.mp3 is
    ready for the owner's one remaining manual upload step, and the real
    aion-memory-data repo has the matching dedupe record so the automated
    pipeline won't redo this one.

17. Owner, 2026-09-27: "ตอนเก่าไม่เป็นไร เราจะเริ่มที่คลิปใหม่เลย" (don't
    bother with the old ones, start with new clips). The real
    aion-memory-data repo now has: a real "dubbed" record for EP.005
    (backfilled -- it was genuinely already done manually before
    ThaiDubCycle existed, so recorded as a completion, not a skip), and
    explicit `skipped: true` records for the other 10 pre-launch backlog
    episodes, so the automated pipeline only ever dubs episodes published
    2026-09-27 onward.
18. Owner noticed the fireflies description still read as generic
    ("#Shorts #AION #AI") with nothing about its actual topic, even after
    the title-hashtag change. YouTubeCreatorQueue._description_hashtags()
    now adds up to 4 topical hashtags (reusing the same keyword extraction
    as the title hashtag and the invisible tags field) ahead of the fixed
    channel/format tags -- affects future publishes. Also retroactively
    fixed the fireflies video's already-live English description (new
    tools/youtube.py:update_video_description(), a read-modify-write like
    set_video_localization() but for the primary snippet) and its Thai
    localization, since that's the exact video the owner was looking at.

19. Owner: name Thai audio files after the clip so they're findable.
    ThaiDubCycle._filename_slug() builds a readable slug from the video's
    real title (e.g. "fireflies-glow-dark-TsGxyRCTcaE-thai.mp3" instead of
    the opaque episode id) -- renamed the 2 existing files and their real
    aion-memory-data audio_path records to match.
20. Owner: why does every title start with "AION Wonders"/"AION Explains"
    instead of going straight to SEO. None of the 4 channels studied
    2026-09-27 prefix a title with their own channel name. Removed that
    prefix from research_story_handoff.py's working_title (the real
    source of every episode's title) and story_episode_stager.py's
    fallback -- both now start with the bare hook/topic. The internal
    `series` field (still "AION Wonders", for dashboard/pillar grouping)
    is untouched; only the public title text changed.

21. Owner shared a plush-toy reference image and liked its candy-color
    highlights and glow/sparkle particles, but explicitly did not want the
    whole plush/felt material or look adopted (would risk imitating that
    reference's overall visual identity, the same concern raised earlier
    over the Spider-Verse comparison). Applied both requested elements
    narrowly to AION's own existing signature prop only: the held glowing
    question-mark is now candy-bright cyan with soft rainbow-tinted
    highlights plus a few tiny sparkle particles drifting around it. The
    diorama material/rendering style itself is unchanged. Updated in the
    real image-prompt source (brain/costume_direction.py), both
    visual-planning gates (visual_narrative_gate.py,
    fact_first_visual_gate.py), and every identity/constitution doc
    (core/visual_identity.md, core/creator_bible.md,
    docs/AION_VISUAL_DIRECTION.md, assets/content-library/aion-character/
    README.md) -- same file set touched for the earlier crystal→
    question-mark change. Forward-looking only; no existing rendered
    image/video touched. Full test suite (python run_tests.py) green.

22. Owner shared a second reference image (Pixar-style selfie render) and
    said any adaptable elements were welcome; offered two bounded options
    (selfie-style first-person POV framing; a more visibly animated
    reaction) and the owner picked both. Added to
    CreatorSceneProduction._composition_direction()
    (brain/creator_scene_production.py) -- the same per-beat method as
    item 12's dynamic-framing change: selfie POV bounded to the hook beat
    only, heightened reaction bounded to the hook/reveal beats where AION
    appears, both explicitly still "restrained and friendly, never a
    generic mascot mugging for the camera" so AION's existing restrained-
    expression identity rule holds everywhere else. Forward-looking only.
    4 new regression tests; full suite green.

23. Owner noticed no clip had published in 2 days and asked for an
    immediate, durable fix. Root cause: ContentNoveltyLedger
    (brain/content_novelty.py) compared new video-topic candidates
    against AION's own Facebook/Instagram cognitive-reflection posts
    (belief/question/goal/experiment/birth-record), which share the
    same "published_reels" category as real topics but aren't
    comparable subjects -- TopicNoveltyGate's shared-word heuristic
    (brain/topic_novelty.py) matched e.g. a glassmaking question against
    a birth-statement reflection on nothing but "learn"/"first", and
    since that reflection corpus only grows, this got worse until 100%
    of the current backlog was blocked (confirmed by running the real
    pipeline against .aion-memory-inspect). Fixed both the pooling (own
    reflections excluded from the novelty pool; real creator-library
    reels still compared) and the word list (added
    people/first/make/learn/who/each/other/met/someone/never to
    STOPWORDS, each with a concrete real collision found this session).
    Cleared the real backlog into 5 story_research_briefs entries,
    pushed directly to aion-memory-data instead of waiting a 3-hour
    cron. 4 new regression tests; full suite green. Owner was told this
    fixes the confirmed cases, not a guarantee against every future
    possible word collision -- the mechanism is still a maintained list.

24. Owner asked for long-term prevention, not just today's fix.
    SystemIntegrity (brain/system_integrity.py) already alerts on stuck
    episodes and pushes to Telegram hourly (built for the 2026-09-25
    stale-OAuth incident), but only watches an episode already
    authorized-for-aion-publish -- a novelty-gate block happens earlier
    and was invisible to it. Added
    SystemIntegrity._research_pipeline_stall(): critical alert when >=3
    evidence-qualified topics sit unconverted for 24h+ (research-to-
    story.yml runs every 3h). Reuses the exact existing alert path (no
    new plumbing): dashboard's "integrity" card + hourly Telegram push
    via tools/production_control.py. Verified against real production
    data both ways: reads healthy-ish now (backlog cleared), would have
    read critical against today's original 100%-blocked backlog. 5 new
    regression tests; full suite green.

25. Fixed a real gap the owner spotted: uploads never declared
    defaultLanguage/defaultAudioLanguage (now "en", confirmed with
    owner). Also made thai-dub.yml trigger via workflow_run right after
    youtube-creator.yml completes instead of waiting up to 1h for its
    own daily cron tick (kept as a safety net).
26. Open, awaiting owner decision: reading the real narration of the
    next-to-publish episode found that 4 structural beats
    (evidence-one/two-intro, takeaway, invitation --
    brain/story_episode_stager.py lines ~402-430) are hardcoded
    templates that literally speak the raw source-paper title or the
    full raw question sentence -- still reads like a citation/lecture
    despite the 2026-09-27 AI-rewrite feature already fixing the
    evidence beats. Asked whether to extend that rewrite's scope to
    cover these too; nothing changed yet pending the answer.

27. "พัฒนาเลย" confirmed: extended the AI narration rewrite
    (brain/story_beats.py's new STRUCTURAL_TEMPLATE_BEATS,
    is_rewritable_narration_beat()) to evidence-one/two-intro, takeaway,
    and invitation, plus fixed the two worst offenders' deterministic
    fallback templates (no more raw source-title citations even with no
    AI provider). question/boundary stay hand-authored (boundary is
    claim-safety-adjacent). 3 new tests; full suite green.
28. Owner: publish twice a day instead of once (18:00/20:30 Bangkok) --
    "ปล่อยหลายตอนต่อวันยิ่งดี". No daily cap existed in publish_once() to
    begin with, so this was purely a scheduling change:
    channel_policy.py's shorts_times (now a list) + doubled
    shorts_buffer_target (7->14, same 168h/7-day horizon) +
    release_readiness.py's slots() + a second cron in
    youtube-creator.yml + tools/youtube_release_watchdog.py rewritten to
    self-heal each slot independently via its own bounded window (was
    hardcoded to one slot) + tools/dashboard.py's separately-stale
    hardcoded Thu/Fri/Sun@20:30 check replaced with a real policy read.
    10 tests updated, 9 new; full suite green.
29. Compared AION's real narration against two reference channels
    (ไอ้ก้าง เล่าเรื่อง, Kurzgesagt Shorts) per owner request -- both lead
    with a short declarative claim or casual question, never the full
    formal research-question sentence repeated multiple times per video
    the way AION's hook/takeaway/invitation beats did. Owner confirmed
    "พัฒนาเลย": added StoryEpisodeStager._derive_hook_phrase()
    (brain/story_episode_stager.py) -- AI-compresses the topic into one
    short spoken phrase (screened by claim-safety + a new subject-drift
    guard, falls back to the bare topic on any failure), used in place
    of the raw topic in hook/takeaway/invitation narration only; the
    actual SEO title and image-generation `visual` fields are untouched.
    9 new tests; full suite green.

30. Owner: "ทั้งหมดเลย หากเพิ่มข้อมูลได้อีกก็เพิ่มเลย" (add whatever you
    can). Filled core/source_registry.json's long-declared, never-built
    "official_primary_sources" tier and the history/human-culture lane
    gap in one move: tried loc.gov (blocked, HTTP 403 even with a
    compliant User-Agent), Wikidata (wrong shape -- property claims, not
    prose), and Wikisource (many documents transclude text from Page:
    namespace scans, extracts often empty) before landing on Project
    Gutenberg via the Internet Archive, confirmed live end to end.
    search_primary_source_texts()/get_primary_source_text()
    (tools/web_search.py) strip Gutenberg's license boilerplate; auto-
    registers in brain/learning.py the same way openalex/hacker_news do.
    Registry entry renamed honestly (public library, not literally a
    government source) with scope_keywords targeting history/culture/
    literature. 12 new tests; full suite green.

31. INCIDENT, 2026-09-29: the `MEMORY_REPO_PAT` fine-grained PAT expired,
    breaking the private `aion-memory-data` checkout step in every
    workflow that touches it (youtube-creator, creator-scene-production,
    creator-queue-quality, research-to-story, production-control) for
    several hours -- diagnosed by noticing every one of them failing at
    the identical "Run actions/checkout@v4" step. Owner rotated the token
    (new fine-grained PAT, Contents: Read/write on aion-memory-data only,
    expires 2027-09-29) and updated the `MEMORY_REPO_PAT` secret; verified
    fixed within minutes (production-control/research-to-story/
    creator-scene-production all back to success). Buffer was fully
    drained during the outage (0/14 ready); needs a few learning-cycle
    ticks to rebuild before new episodes resume. No code change -- purely
    a credential rotation only the owner could do.
32. Same day, separately: owner noticed a published episode
    ("trade routes") had no Thai dub at all and asked why it isn't
    automatic. Found thai-dub.yml had zero runs that day -- its own daily
    14:30 UTC cron was silently dropped by GitHub (same failure class as
    youtube-creator.yml's 2026-09-22 incident) and its brand-new
    workflow_run trigger (added earlier the same day) hadn't activated in
    time either. Generalized tools/youtube_release_watchdog.py to watch
    any workflow (not just youtube-creator.yml); youtube-release-
    watchdog.yml now self-heals both. 9 new tests; full suite green.

33. Owner: what else to level up toward "content creator." Agreed on a
    two-way engagement loop (viewers currently only ever got a one-off
    reply, never a real chance to shape content), guided by "คนชอบความ
    สงสัย อยากรู้ ไม่ใช่อยากเรียน". Added
    CommentAutoReplyCycle._capture_audience_curiosity()
    (brain/comment_reply.py): a genuine viewer question, after a
    successful reply, becomes a real CuriosityEngine open question
    (tagged audience-suggested) that flows through the normal research
    pipeline like any other -- deduped against open questions, never
    raises, never fabricates an answer in the reply itself. 6 new tests;
    full suite green. Not yet done: the reverse direction (surfacing in
    a video or a public post that a topic came from a viewer) --
    natural next step if the owner wants the loop to feel visible, not
    just functional.

34. Owner, still not satisfied after item 27's hook-phrase fix: "ฉันยัง
    ต้องการการเล่าเรื่องแบบ เพจ ไอก้าง ไม่ใช่อ่านวิจัยให้ฟัง". Found and
    fixed more research/citation-flavored wording: CONNECTION's fallback
    ("And from the second source:"), QUESTION's fixed opening
    methodology line, and leftover "evidence" wording in the
    EVIDENCE_ONE/TWO_INTRO fallback fixed this morning. Also rewrote the
    AI-rewrite prompt to explicitly name the ไอ้ก้าง/Kurzgesagt style and
    ban a list of research-sounding words. 2 new tests; full suite
    green. IMPORTANT, told to owner: this fixes wording, not structure
    -- the beat architecture itself (intro/a/b for source 1, intro/a/b
    for source 2, connection, boundary) still shapes every episode like
    "compare two citations," not a mystery-reveal story arc. A real fix
    for that would mean redesigning brain/story_beats.py's beat set
    itself (touches creator_scene_production.py, visual_narrative_gate.py,
    fact_first_visual_gate.py, watchability_gate.py too, since beat names
    are read across the whole pipeline) -- worth doing if the owner still
    isn't satisfied once a new episode using today's wording fixes is
    actually seen and heard.

35. Direct answer to item 34's open structural question. Owner: "ทำไม ไม่
    สรุปออกมาก่อนแล้วเขียนบทละ ให้เป็นเรื่องเล่า ไม่ใช่นั่งฟังวิจัย" (why
    not summarize first, then write the script as a story). Added
    `StoryEpisodeStager._synthesize_understanding()`: one AI call that
    reads both source observations together and produces a single
    coherent, story-like understanding, screened the same way as
    `hook_phrase`. The CONNECTION beat now states that synthesis
    directly (instead of concatenating each source's first fragment),
    and `_rewrite_scene_narrations()` gets it as shared context so the
    whole episode can build toward one payoff instead of polishing
    disconnected fragments. Bounded fallback on any failure -- never
    blocks staging. This does NOT yet touch the beat architecture itself
    (still 12 fixed beats: hook/question/evidence-one-intro/a/b/
    evidence-two-intro/a/b/connection/boundary/takeaway/invitation) --
    only what feeds the connection beat and the shared rewrite context.
    A full beat-count/order redesign is still the bigger remaining option
    from item 34, not yet requested. 5 new tests; full suite green.

36. Status check, 2026-09-30, ~02:20 UTC: read `public/aion-production-
    control.json` and `public/aion-workflow-status.json` (both bot-
    refreshed minutes earlier). Two things worth a look, neither blocking
    release right now:
    a. RESOLVED same session: `integrity.alerts`' live `motion-fallback-
       rate` warning (last 3 episodes, 38/38 scenes on still-hold). The
       affected episodes' manifests actually live at
       `content/creator_series/*.json` (not assets/content-library/aion-
       stories/, which only holds binary assets) -- once found, all 4
       recent fallback episodes showed the identical `motion_contract.
       fallback_error_type: "ValueError"`. Reproduced the exact
       `tools/gemini_video.py::generate_scene_video()` call locally
       against the currently installed `google-genai` SDK and confirmed
       the cause: `generate_audio=False` is rejected outright (plain
       ValueError) in Gemini Developer API mode, which is what a bare
       `GEMINI_API_KEY` uses. Fixed, plus a second latent bug found in
       the same pass (`files.download()`'s `destination=` kwarg was
       removed, would have raised TypeError right behind the ValueError)
       and a proactive migration off the separately-deprecated
       `prompt=`/`image=` args to `source=`. Pinned `google-genai==
       2.25.0` in requirements.txt -- it was unpinned, which is *why*
       this broke silently with no code change on our side. 1 new
       regression test (exercises the real installed SDK types, mocks
       only the network-calling Client). Full suite green.
       Commits: 619b660
    b. 8 of 45 workflow tiles in aion-workflow-status.json still show
       their LAST run as a failure, all dated 2026-09-29 and several
       citing the exact `actions/checkout@v4` / "Checkout AION memory"
       symptom from the MEMORY_REPO_PAT expiry (item 31) -- but none of
       them have run again since the token was rotated to confirm the
       fix actually reached them (their schedules are infrequent:
       growth-pulse.yml, scientific-discovery.yml, obsidian-brain.yml,
       propose-profile-change.yml, youtube-audience.yml, asset-hygiene.
       yml, creator-competitive-scan.yml, revenue-brain.yml). Worth
       checking after each one's next scheduled run, not urgent today.
    `shorts_buffer` is 6/14 quality-ready (normal catch-up, not a stall --
    no `research-pipeline-stall` alert fired), and the 18:00/20:30 cadence
    is running.

37. Owner asked for a suggestion; agreed to it directly ("ทำได้เลย").
    Pinned the remaining external-provider SDKs in requirements.txt --
    `edge-tts`, `google-api-python-client`, `google-auth-oauthlib`,
    `google-auth-httplib2` -- to their current, verified-working
    installed versions, closing the same "unpinned dependency breaks
    silently" risk class item 36.a just found and fixed for
    `google-genai`. Full suite green. Commits: 7979703

Nothing urgent open beyond item 36.b's watch-item above. The owner has been told, and agreed, that the
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
