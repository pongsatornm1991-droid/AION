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

Still open: the live Venus video itself is still Private -- the owner
needs to run `python main.py release-private-youtube-creator` once to
flip it public, since this sandbox cannot reach YouTube's API. Will
update this entry / close the active-task board once confirmed public.

Commits: 3f39356 (active-task claim), 5c11923 (the fix + tests),
9af6a73 (durable episode_number recorded on the source episode).

---

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
