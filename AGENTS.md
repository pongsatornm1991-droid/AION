# AGENTS.md — how Codex and Claude work on this repo together

This file is read by AI coding assistants (Codex CLI reads `AGENTS.md`
automatically; Claude reads it on request). It exists because this repo is
worked on by both Codex and Claude in separate sessions with no shared
memory of each other — this file, plus `docs/ai-session-log.md`, is the
connective tissue between them. Read both before making changes.

## What this project is, in one paragraph

AION is an autonomous AI-persona bot that posts to Facebook, Instagram and
YouTube on its own, learns from its own self-generated curiosity questions,
and drafts its own creative intentions — all gated by a claim-safety system
that forbids it from ever claiming real consciousness. ~118 modules in
`brain/`, ~60 in `tools/`, 57 scheduled GitHub Actions workflows in
`.github/workflows/`. Start with `README.md` (the maintained command/feature
reference) and `core/*.md` (identity, values, purpose, visual identity —
AION's own constitution) before `brain/`.

## Before you start any session

1. `git pull --rebase origin main` — many workflows commit straight to
   `main` on their own schedules, so `main` moves under you constantly.
2. Read the last 5-10 entries of `docs/ai-session-log.md` to see what the
   other assistant (or AION's own self-repair/self-improvement cycles) did
   most recently, before re-deriving it from `git log`.
3. Check GitHub Actions health before assuming the repo is green:
   `https://github.com/pongsatornm1991-droid/AION/actions` — a red run is
   often more informative than anything in this file.
4. Read `docs/ai-active-task.md`. If it names another assistant and its
   lease has not expired, do not overlap that scope; take a clearly separate
   task instead. Claim your own nontrivial work there before editing.

## Git discipline (read this — it is not optional)

`git push` here has no retry logic in most workflows and this repo pushes
to `main` very frequently (bot commits every few minutes at peak). A bare
`git push` WILL occasionally get rejected as non-fast-forward. Always:
- `git pull --rebase origin main` immediately before you push.
- If rejected, pull --rebase again and retry — don't force-push `main`.
- Prefer small, focused commits over one giant one; it makes a rebase
  conflict trivial instead of painful.
- As of 2026-09-20 every workflow that commits+pushes to `main` (51
  files, starting with `.github/workflows/instagram-cycle.yml`'s
  original 5-retry rebase loop) uses this retry pattern -- if you add a
  NEW workflow that commits to `main`, copy the pattern, don't write a
  bare `git push`.

## Testing

`python run_tests.py` runs `unittest discover` over `tests/test_*.py` plus
two offline benchmarks — this is what `.github/workflows/tests.yml` ("AION
- deterministic tests") runs on every push to `main`. The suite is large
(138+ test files); if you're iterating, run a single module first:
`python -m unittest tests.test_<name> -v`.

## Division of labor (a default, not a rule)

- **Codex**: fast, high-volume, in-editor iteration — day-to-day feature
  and module work, the bulk of the commit history.
- **Claude (via Cowork)**: cross-cutting audits (CI health across all 57
  workflows, full-history git investigation), anything that needs a guided
  browser session (OAuth/token setup, reading a run's log in the GitHub
  UI), and keeping the higher-level project narrative documented.
- Either assistant can do either kind of work — this is just a default to
  reduce duplicate effort, not a hard boundary.

## When you finish a nontrivial change

Append one entry to `docs/ai-session-log.md` (see that file's own header
for the format) before ending your session. This is the single most
important habit this file asks of you — skipping it is how the next
session (human or AI) ends up re-discovering things from scratch.
