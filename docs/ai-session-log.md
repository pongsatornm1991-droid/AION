# AI session log

Append-only. One entry per nontrivial session by Codex or Claude — newest
at the top. Keep each entry to a few lines: what changed, why, and the
commit hash(es) if you committed. This exists so the next session (either
assistant, or the human) doesn't have to re-derive context from `git log`
across 1000+ commits. See `AGENTS.md` for the fuller collaboration protocol.

Format:
```
## YYYY-MM-DD — <assistant> — <one-line summary>
<2-5 lines of detail>
Commits: <hash> [, <hash> ...]
```

## 2026-09-21 — Claude — Published the Venus flytrap short, found a real "false Stage: published" bug

Ran the missing step first (`prepare-youtube-creator --episode-id
aion-wonders-005-venus-flytrap-counts` -- no queue record existed yet,
which is why publish had returned no-authorized-creator-episode), then
`run-youtube-creator-publish`. It printed Stage: published with a real
video ID (https://www.youtube.com/watch?v=mdMF5AebtmY), but the
browser confirmed the video was actually Private.

Root cause: `tools/youtube.py`'s `upload_short()` defaults privacy to
`os.getenv("YOUTUBE_PRIVACY_STATUS", "private")` when no privacy_status
is passed, and `publish_once()` never passed one -- it only behaves
correctly inside GitHub Actions because youtube-creator.yml explicitly
sets that env var. Any manual/local run silently uploads private while
still claiming success. Fixed `publish_once()` to pass privacy_status
explicitly (default "public", matching the workflow's own default) and
added a post-upload check: if the result isn't actually public, it
tries once to self-heal via `set_video_privacy`, and if that still
fails it records the honest state and returns `uploaded-but-not-public`
instead of `published`. Two regression tests added; one existing test's
bare uploader mock updated to declare privacy_status explicitly. Full
suite: 906/906 relevant tests pass (2 pre-existing failures in this
sandbox only, from a broken OneDrive memory symlink, unrelated).

Owner then hit two auth snags running `release-private-youtube-creator`
locally (`invalid_scope`, then `invalid_client`) -- root cause was a
stale/placeholder `YOUTUBE_CLIENT_ID`/`YOUTUBE_CLIENT_SECRET` pair in
`.env` left over from a prior edit, plus a refresh token that needed
`youtube.force-ssl` scope. Owner re-ran `tools/youtube_authorize.py`
themselves and pasted the new refresh token in; `.env`'s client
id/secret were repaired to match `client_secret.json`. Release then
succeeded: `Stage: released-public`, Privacy: public. Independently
re-verified via browser (no "Private" label, comments enabled, channel
public-video count moved from 12 to 14) -- confirmed genuinely public,
not just CLI-reported. Active-task board closed back to clear.

Commits: 3f39356 (active-task claim), 5c11923 (the fix + tests),
9af6a73 (durable episode_number recorded on the source episode),
fcd5872 (this entry's first half).

---

## 2026-09-21 — Claude — Style lock: a clip needs explicit approval to enter the release queue

Follow-up to the same session's Venus publish. The user asked that the
system lock visual style before publishing: no clip without an approved
primary visual style should enter the release queue, and no
experimental/old-style clip should win a slot in place of new work --
directly describing how the earlier rainbow clip (old
`illustrated-aion-storyboard-v4` style, `urgent` release_priority) won an
automatic release slot.

First attempt was wrong and never committed: gating on
`pacing_policy == VisualStoryPolicy.VERSION` or on a single hardcoded
`visual_style.id` would have blocked almost every real in-flight episode,
since the channel legitimately runs several concurrent styles at once
(Venus = Neon Graphic Science, the Thailand/rain episodes = Illustrated
Postcard, others declare no style at all yet) -- only the rainbow clip's
own style happened to match the one hardcoded constant. Caught this by
inspecting the real content/creator_series/*.json files before shipping,
discarded that version, and asked the user how "approved" should be
defined.

Shipped instead: an explicit opt-in flag. `YouTubeCreatorQueue.candidates()`
now blocks any episode from `release_eligible` unless
`visual_style.approved is True` (blocker id
`visual-style-not-approved-for-release`), checked before either automatic
selection or an explicit `--episode-id` request -- style lock is not
something episode targeting can bypass. `story_episode_stager.py` stamps
`approved: true` on every newly staged AION Wonders episode automatically,
so the normal pipeline is unaffected. Backfilled `approved: true` onto the
six episodes currently sitting production-ready-and-unpublished
(aion-gentle-thailand-rice-journey-v1, aion-illustrated-postcard-after-rain-v1,
aion-longform-001-yakhchal, aion-special-octopus-chromatophores-v1,
aion-wonders-003-roman-nobody, aion-wonders-005-venus-flytrap-counts) since
they were already legitimately in the ready queue -- this only formalizes
their existing state under the new field, it does not approve anything new.
Deliberately left aion-special-rainbow-perspective-v1's style unapproved,
even though it is already published, so it can never again win an
automatic slot for any reason.

Two existing tests (test_release_readiness, test_release_buffer_recovery)
used fixture episodes with no visual_style at all and started correctly
failing under the new gate; updated their fixtures to declare an approved
style, matching what real content now needs. Two new regression tests
added to test_youtube_creator_queue.py: an unapproved/experimental style
with urgent priority is rejected from both automatic selection and
explicit `--episode-id` targeting; an episode with no visual_style field
at all is also rejected. Full suite re-run in chunks: 908 tests across all
four chunks, 2 pre-existing failures confirmed unrelated by reproducing
them on the unmodified tree first (the broken OneDrive memory symlink in
this sandbox only, and one direct-message dedup test unrelated to this
change).

Also correcting an earlier note in this session: I had flagged
`public/aion-release-readiness.json` showing Venus as still "available"
after publishing as a possible bug in `brain/release_readiness.py`. It is
not -- that file is a CI-generated snapshot (`.github/workflows/publish-workflow-status.yml`,
hourly cron) and was simply stale at the moment I read it; the underlying
logic was already correct per the passing
`test_does_not_count_a_video_without_a_saved_quality_gate` test.

Commits: (this entry's own commit follows).

## 2026-09-21 — Claude — Documented the Neon Graphic Science style, blended in a magenta/yellow accent per owner confirmation

Follow-up to the same session's style-lock work. The owner wrote out a full
artistic definition of "AION Neon Graphic Science" / Sci-Fi Graphic Novel
Illustration (Pop-Science Halftone Style): halftone comic-print texture,
high-contrast ink-navy outlines, a meaningful (not scattered) neon palette,
and dramatic radial vignette lighting. No named-style catalog existed in the
repo (styles only lived as inline prompt strings in
`brain/creator_scene_production.py`), so added
`docs/AION_VISUAL_STYLE_LIBRARY.md` cataloging every `visual_style.id` the
render pipeline recognizes (Neon Graphic Science, Illustrated Postcard, Vivid
Storyworld 2D, Animated Documentary, Thoughtscape/Original Warm 3D, and the
fallback), cross-checked against the current code.

Flagged one gap to the owner: the code's Neon Graphic Science palette assigns
colour by narrative role (amber = observed input, coral = the answer, fresh
green = the subject, cyan reserved only for AION's identity signature) rather
than using the owner's example neon colours (electric cyan, hot magenta,
cyber yellow) directly. Owner confirmed: "ใช่จริงครับ ผสมกับสิ่งที่มี" (yes,
blend it with what's already there) -- not a replacement. Updated
`creator_scene_production.py`'s `aion-neon-graphic-science-v1` prompt rule to
allow a restrained hot-magenta or cyber-yellow neon accent on one specific
electrical/energetic/signal-like moment in the mechanism, explicitly scoped
to a single element (never general scene lighting, never displacing the base
amber/coral/green/cyan roles). Added a regression test
(`test_neon_graphic_science_blends_a_restrained_magenta_or_yellow_accent`)
asserting both the base roles and the new accent language are present.
Updated the style-library doc to record the decision instead of leaving it
open. Full targeted suite re-run clean (test_creator_scene_production,
test_story_episode_stager, test_youtube_creator_queue).

Commits: (this entry's own commits follow -- the doc, then the code+test
change).

## 2026-09-21 — Claude — URGENT: found published Shorts with no Studio queue record; added the missing reconcile CLI

While explaining a shorts-buffer shortage to the owner, I incorrectly guessed
the cause (no saved Quality Gate) without being able to check the real
memory-backed queue records from this sandbox (the OneDrive memory symlink
is inaccessible here -- durable, sandbox-only limitation). The owner
corrected me and sent a YouTube Studio screenshot: aion-gentle-thailand-rice-journey-v1
("How One Grain of Rice Reaches Your Bowl", public since 19 Sep, 1,015
views), aion-illustrated-postcard-after-rain-v1 ("After the Rain: Where Does
the Water Go?", public since 18 Sep, 73 views), and
aion-special-octopus-chromatophores-v1 ("How an Octopus Changes Color in
Seconds", public since 17 Sep, 181 views) are all already live -- confirming
they were never missing a Quality Gate at all, they were simply already
published through a path that never wrote (or later lost) a Studio queue
memory record for them.

I had already told the owner to run `prepare-youtube-creator --episode-id
aion-gentle-thailand-rice-journey-v1` as a "safe" diagnostic before this came
to light. It was not safe for an already-published episode: since no queue
record existed, it created a fresh "authorized-for-aion-publish" record (and,
as a side effect, wrote `episode_number: 2` into the episode's source file
via EpisodeNumbering.assign()) -- exactly the stray-record situation that
risks a duplicate upload if quality-youtube-creator / run-youtube-creator-publish
are run next. Reverted the stray episode_number write (git checkout, never
committed). The stray memory record itself lives in the owner's real memory
store, which this sandbox cannot reach or fix directly.

`brain/youtube_creator_queue.py` already had exactly the right recovery
method for this, `reconcile_owner_confirmed_publication(episode_id, video_id,
url)` -- "a narrow recovery path... preventing Studio from offering the same
video for upload again" -- but it had no CLI entry point, so there was no way
for the owner to actually use it. Added `reconcile-youtube-creator
--episode-id --video-id --url` to main.py (never calls YouTube, never
uploads, never changes privacy -- purely a memory-record write). Verified
`--help` output and confirmed the underlying method already has full test
coverage (`test_owner_confirmed_reconciliation_removes_a_public_video_from_release_queue`
in test_youtube_creator_queue.py, still passing).

Also noticed in passing, not yet investigated: Venus's own episode file has
`episode_number: 1`, but its real published title reads "EP. 002" -- the
numbering stored in the file does not match what actually went out. Separate
pre-existing issue, not caused by today's work.

RESOLVED same day: owner sent the three real YouTube URLs
(youtube.com/shorts/7Z1JCECq1KM, /JXG5VGosstk, /fmkUR8tWHz4). Before writing
anything, fetched each page's title with WebFetch to confirm which episode it
actually belonged to -- the owner's paste order did not match the order I had
assumed (I would have swapped octopus and rice-journey if I had not checked):
7Z1JCECq1KM = "How an Octopus Changes Color in Seconds" ->
aion-special-octopus-chromatophores-v1; JXG5VGosstk = "After the Rain: Where
Does the Water Go?" -> aion-illustrated-postcard-after-rain-v1; fmkUR8tWHz4 =
"How One Grain of Rice Reaches Your Bowl" -> aion-gentle-thailand-rice-journey-v1.
Owner ran `reconcile-youtube-creator` for all three; all three returned
`Stage: reconciled-published`. The stray rice-journey record from the earlier
mistaken `prepare-youtube-creator` call is now correctly overwritten. None of
the three will be offered for upload again.

Still open, not blocking: whether "AION Wonders: How can an octopus change
color so..." (16 Sep) is a distinct fourth video or a duplicate/draft of the
octopus episode -- asked the owner, awaiting answer. Also still open, low
priority: Venus's file has episode_number:1 but its real published title
reads "EP. 002" -- not investigated.

Commits: c9e8bff (reconcile-youtube-creator CLI); this entry's own commit
follows (docs only).

## 2026-09-21 — Codex — Fixed truthful Creator Shorts release handoff

Found the actual release block: a valid 1080×1920 Short cover was incorrectly rejected as a 16:9 long-form thumbnail, while the workflow still appeared green without checking for `Stage: published`. Shorts now accept vertical covers, manual releases can target one exact episode, run a persisted Quality Gate first, and fail visibly if YouTube did not confirm publication.

Verified release evidence: the automatic lane published `aion-special-rainbow-perspective-v1` publicly as `https://www.youtube.com/watch?v=ujytX6ba7jY`. `aion-wonders-005-venus-flytrap-counts` remains authorized and has not been claimed as published. Added `docs/ai-active-task.md` as an expiring live-claim board for Codex/Claude coordination.

Commits: f77c4bf

## 2026-09-20 — Claude — Retried git push race across all 50 remaining commit+push workflows

Follow-up to the instagram-cycle.yml fix below, at the user's request after
explaining the tradeoffs. Every other workflow that commits+pushes to main
(50 files) used a bare `git push` with the same latent non-fast-forward
race risk. Mechanically substituted a drop-in retry-with-rebase expression
for every standalone `git push` occurrence (one regex substitution per
file, validated every touched file still parses as YAML afterward, spot-
checked 3 diffs by hand for both the one-liner and multi-line styles).

Deliberately did NOT refactor this into a shared composite GitHub Action
(`.github/actions/...`) to cut the duplication -- that would need
restructuring each file's step rather than a pure substitution, which is
riskier to get right across 50 varied files in one pass. Worth doing as a
follow-up if this pattern needs to change again.

Commits: 81b2ce6

---

## 2026-09-20 — Claude — Full status audit + one race-condition fix + this coordination protocol

Full audit at the user's request ("developed far ahead with Codex, go read
everything"): local repo was 4 commits behind origin (pulled), 288 files
showed as modified but were confirmed 100% CRLF/line-ending noise (zero
real content change — stashed, no `.gitattributes` yet to stop this
recurring). Checked latest run of all 57 active workflows: 53 green, 1 new
workflow with no runs yet, 1 manually cancelled, 2 real failures.

`AION - deterministic tests` was failing (5 straight runs) on a genuine
test/code mismatch in `tests/test_aion_creative_director.py` — AION's own
self-repair cycle fixed this itself before I could (commit `04a3072`,
confirmed by 4 straight green runs afterward). No action needed; noting it
here as a genuine, verified example of the self-repair loop working.

`AION - Instagram content cycle` had been failing since run #17
(2026-09-16, 4 days with no further runs) at the "commit + push the new
image" step. Root cause: a bare `git push` with no retry, racing against
the many other workflows that also push straight to `main`. Fixed with a
5-attempt pull --rebase retry loop. Same latent risk exists in ~50 other
workflows' commit+push steps — not fixed yet, flagged for whoever picks
this up next (see AGENTS.md's git discipline section).

Also created `AGENTS.md` and this file, since neither existed — Codex had
no written context about what Claude sessions had done, and vice versa.

Commits: 6678759 (instagram-cycle retry fix), plus AGENTS.md + this file
(pending commit as of this entry).
