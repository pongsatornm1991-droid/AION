# AION

AION is a Python prototype for a persistent cognitive loop:

1. build context from identity and memory;
2. generate and evaluate a self-reflection;
3. correct low-quality output; and
4. store experiences and lessons for later cycles.

It also provides a structured decision mode that separates facts,
inferences, and uncertainties before auditing a proposed conclusion.

## Setup

Install the dependencies and create a `.env` file from `.env.example`.
Set `GEMINI_API_KEY` before using reflection mode.

## Providers

`reflect` uses whichever provider `AI_PROVIDER` in `.env` names (default: `gemini`). `decide`/`history`/`verify` never touch a provider at all, so neither provider's SDK is required to use them.

- `AI_PROVIDER=gemini` (default) -- needs `GEMINI_API_KEY`. Already
  covered by `requirements.txt`.
- `AI_PROVIDER=claude` -- needs `ANTHROPIC_API_KEY` in `.env`, plus
  `pip install anthropic` (not in `requirements.txt` by default, since
  most setups only need one provider). Check the current model id at
  https://docs.claude.com/en/docs/about-claude/models before relying on
  the `ANTHROPIC_MODEL` default in `.env.example` -- model ids are
  periodically retired.

## Commands

Generate a reflection:

```powershell
python main.py reflect
```

Run a decision and audit without calling Gemini:

```powershell
python main.py decide `
  --question "Should the rollout proceed?" `
  --conclusion "Proceed with the limited rollout." `
  --option "Proceed" `
  --option "Delay" `
  --fact "The test plan covers the intended scope." `
  --inference "A limited rollout is appropriate." `
  --uncertainty "Demand may vary after release."
```

Each `--fact`, `--inference`, `--uncertainty`, and `--option` argument can
be repeated. Only a decision with `LOW` audit risk and no audit flags is
stored as `ACCEPTED` in `memory/decisions_accepted.md`. All other results are
stored as `NEEDS_VERIFICATION` in
`memory/decisions_pending_verification.md`. Use `--no-save` to preview the
report without changing memory.

View decision history:

```powershell
python main.py history --status all --limit 10
```

Re-audit a pending decision with new facts. Use the `ID` displayed by
`history` (a stable id, not the timestamp — two decisions can be recorded
in the same second); promotion occurs only if the new audit is `LOW` risk
and has no flags.

```powershell
python main.py verify `
  --id "a1b2c3d4e5f6" `
  --fact "The rollback procedure is documented." `
  --fact "The release owner is assigned."
```

Consolidate old, low-importance memories into semantic knowledge (calls
the configured AI provider once per batch, so it needs a valid key — this
is a live command, not covered by `run_tests.py`):

```powershell
python main.py consolidate `
  --category experiences `
  --target semantic `
  --max-importance 2 `
  --min-age-days 30 `
  --min-group-size 3 `
  --batch-size 8
```

Only entries at or below `--max-importance` and at least `--min-age-days`
old are eligible, and a batch is only summarized once it has at least
`--min-group-size` eligible entries. Each accepted summary is saved as a
`TYPE: semantic` entry (tagged with the union of its sources' tags, and
`RELATED:` pointing back to every source entry's id) in the `--target`
category, and its source entries are moved — never deleted — to
`memory/<category>_archived.md`. A drafted summary that fails
`OutputEvaluator`'s claim-safety check (any consciousness, subjective-
experience, or other unsafe claim) is rejected and its source entries are
left exactly where they were; nothing is ever silently lost or silently
kept.

## Memory tags and related entries

`MemoryEngine.remember()` accepts optional `tags` (a list of short labels)
and `related` (a list of other entries' `id`s) alongside the existing
`memory_type`/`source`/`importance` fields; both are stored as `TAGS:`/
`RELATED:` lines and survive `move()`. Retrieval helpers — `by_tag()`,
`add_tags()` (retroactive tagging), and `related_entries()` (explicit
`RELATED:` ids first, then other entries ranked by shared-tag overlap) —
are all pure code, so they work fully offline with no AI call.

## Beliefs

Form an explicit belief. `--evidence` is required — `BeliefSystem` refuses
to save a belief with none. Prefix an item with `id:<memory-id>:` to link it
to an existing memory or decision entry:

```powershell
python main.py believe `
  --statement "Staged rollouts reduce rollback incidents." `
  --confidence 0.7 `
  --evidence "id:a1b2c3d4e5f6:Three prior staged rollouts had no rollback." `
  --tag rollout `
  --tag ops
```

List currently active beliefs (excludes superseded, retracted, and expired
ones — expiration is computed from the stored date at read time, so nothing
needs a separate cleanup pass):

```powershell
python main.py beliefs --topic rollout --limit 10
```

Revising a belief never edits it in place — it writes a new belief entry and
tags the old one `superseded`, keeping the full lineage on disk:

```powershell
python main.py revise-belief `
  --id "80fb5bb871e8" `
  --reason "New data changed my confidence." `
  --confidence 0.9
```

Retracting leaves no replacement, tags the entry `retracted`, and logs a
companion lesson recording why:

```powershell
python main.py retract-belief --id "80fb5bb871e8" --reason "Turned out false."
```

None of `believe`/`beliefs`/`revise-belief`/`retract-belief` calls an AI
provider — belief formation, revision, and retraction are pure code with a
hard requirement for evidence, so this whole subsystem is covered by
`run_tests.py`, unlike `consolidate`.

## Curiosity and goals

`CuriosityEngine` (open questions) and `GoalEngine` (active goals) are both
built on the same `BoundedItemTracker`: an item can't be opened without
stating its own completion criteria, only `max_open` items may be open at
once (default 10 — resolve or abandon one to open another), each item has
its own attempt budget that only ever gets *flagged* exhausted (never
auto-abandoned), and resolving one always requires evidence, the same rule
`BeliefSystem` enforces.

Raise a question:

```powershell
python main.py ask `
  --question "Why do staged rollouts reduce rollback incidents?" `
  --criteria "Find at least 2 confirming decisions." `
  --priority 4 `
  --budget 3 `
  --tag rollout
```

```powershell
python main.py questions --topic rollout --limit 10
python main.py attempt-question --id "<id>" --note "Checked one decision."
python main.py answer-question --id "<id>" --answer "..." --evidence "id:<memory-id>:..."
python main.py abandon-question --id "<id>" --reason "No longer relevant."
```

Goals use the identical shape:

```powershell
python main.py set-goal --goal "Ship staged rollout tooling." --criteria "Deployed and used once." --priority 5
python main.py goals
python main.py attempt-goal --id "<id>" --note "Built prototype."
python main.py complete-goal --id "<id>" --outcome "..." --evidence "deployment log"
python main.py abandon-goal --id "<id>" --reason "Deprioritized."
```

Nothing here is edited in place: `attempt-question`/`attempt-goal` and
`answer-question`/`complete-goal` each write a new entry superseding the
current one, so the full attempt/revision history stays on disk (see
`CuriosityEngine.history()` / `GoalEngine.history()`). None of these
commands call an AI provider, so this whole subsystem is covered by
`run_tests.py` too.

## Experiments and reflection

`ExperimentEngine` is AION's predict -> observe -> conclude loop. A
prediction states a confidence level before anything is known (no
evidence required — a prediction isn't a claim yet); an observation
always requires supporting evidence, since claiming what was actually
seen is a claim like any other; concluding derives a lesson and can
optionally revise an existing belief, but only when the caller
explicitly names a `--belief-id` — nothing here changes a belief on
its own.

```powershell
python main.py predict --prediction "Staged rollout reduces rollback incidents." --confidence 0.7 --tag rollout
python main.py experiments --status pending
```

```powershell
python main.py observe --id "<id>" --result "Rollbacks dropped 40% over 2 weeks." --matched yes --evidence "id:<memory-id>:rollback log"
python main.py observe --id "<id>" --result "Latency got worse." --matched no --evidence "note" --error "Cache warmup not accounted for."
python main.py experiments --status awaiting
```

```powershell
python main.py conclude --id "<id>" --lesson "Confirmed staged rollout reduces incidents."
python main.py conclude --id "<id>" --lesson "Raise confidence." --belief-id "<belief-id>" --belief-confidence 0.85
python main.py abandon-experiment --id "<id>" --reason "No longer relevant."
```

Like beliefs, questions, and goals, nothing here is edited in place:
`observe` and `conclude` each write a new entry superseding the
current one, so the full predict/observe/conclude trail stays on disk
(see `ExperimentEngine.history()`). None of this calls an AI provider,
so this whole subsystem is covered by `run_tests.py` too.

## Metacognition

`MetacognitionEngine` reports on AION's own track record -- every
number is computed directly from what's already on disk, nothing is
judged or estimated by an AI provider.

```powershell
python main.py metacognition
python main.py metacognition --report calibration --bucket-size 0.2
python main.py metacognition --report recurring-errors --min-occurrences 2
python main.py metacognition --report memory-quality
```

- **Calibration** buckets every observed experiment (from
  `ExperimentEngine.observed_experiments()`) by its stated confidence
  and compares that to how often it actually matched, flagging each
  bucket `overconfident` / `underconfident` / `well-calibrated` -- or
  `insufficient_data` when there simply aren't enough observations yet
  to say anything honestly.
- **Recurring errors** groups every logged lesson by its source (e.g.
  `experiment-abandonment`, `question-abandonment`) and flags any
  source that recurs at least `--min-occurrences` times -- a literal
  count, not an AI-judged theme.
- **Memory quality** aggregates `MemoryEngine`'s own
  `quality_report()`/`stats()` across every category found on disk,
  flagging any category (with at least 3 entries, so a couple of thin
  entries never look like a systemic problem) whose average quality
  falls below a threshold.
- **Tool reliability** — the fourth thing this phase names — is
  deliberately reported as `not_applicable`: AION has no
  external-tool-execution framework yet (that's the next phase), and
  inventing a reliability figure for tools that don't exist would be
  exactly the kind of fabricated self-assessment this project forbids.

None of this calls an AI provider, so it's fully covered by
`run_tests.py` too.

## Offline verification

Single deterministic command (unit tests + both offline benchmarks; never
calls Gemini, so it needs no API key and costs no quota):

```powershell
python run_tests.py
```

Exits non-zero if unit tests fail or either benchmark drops below 100%.
The individual pieces can still be run on their own:

```powershell
python -m unittest discover -s tests -p "test_*.py"
python tests\offline_benchmark.py
python tests\correction_benchmark.py
```

`tests\run_benchmark.py` is separate: it calls the live Gemini API, is not
deterministic, and is excluded from `run_tests.py` on purpose.
