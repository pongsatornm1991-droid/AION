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

---

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
