# AION Project Audit

Audit date: 2026-08-29  
Current runtime version: `0.0.8`

## Current file tree

```text
AION/
├── brain/          Cognitive components and persistent-memory logic
├── core/           Human-readable identity, purpose, values, and birth record
├── memory/         Markdown experiences and lessons
├── providers/      AI provider interface and Gemini implementation
├── tests/          Unit tests and deterministic benchmarks
├── main.py         CLI entry point
├── README.md       Setup and command guide
└── requirements.txt
```

The `evolution/`, `learning/`, and `tools/` directories exist but currently
contain no implementation files.

## Working components

- **Identity:** Markdown identity, purpose, values, and birth record are read
  by `Identity`.
- **Persistent memory:** `MemoryEngine` stores structured entries in Markdown,
  supports parsing, recent/important retrieval, duplicate detection, quality
  reports, statistics, and category moves.
- **Reflection loop:** `main.py reflect` builds context, calls Gemini, evaluates
  the result, optionally corrects it, and stores an experience plus a lesson.
- **Output guardrails:** `OutputEvaluator` checks response structure,
  uncertainty language, evidence language, prohibited self/subjective claims,
  unsupported external-data claims, and selected contradiction patterns.
- **Correction:** `CorrectionEngine` re-generates only when the initial score is
  below `4.0`, then retains the higher-scoring result.
- **Decision audit:** `DecisionEngine` and `CognitiveAuditor` score structured
  facts, inferences, and uncertainties.
- **Decision lifecycle:** `decide`, `history`, and `verify` commands separate
  `ACCEPTED` decisions from `NEEDS_VERIFICATION` records. Promotion requires a
  new audit with `LOW` risk and no flags.

## Current provider

- Provider: Google Gemini via `google-genai`.
- Configuration: `GEMINI_API_KEY` and optional `GEMINI_MODEL` in `.env`.
- Default configured model: `gemini-3.6-flash`.
- `AIProvider` exists as an abstract interface, but `GeminiProvider` is the only
  implementation and does not yet inherit from it.

## Current memory architecture

| Category | Purpose |
|---|---|
| `memory/experiences.md` | Reflection and operational experience records |
| `memory/lessons.md` | Evaluation-derived lessons |
| `memory/decisions_accepted.md` | Decisions that passed the acceptance policy |
| `memory/decisions_pending_verification.md` | Decisions requiring further evidence |

The project currently contains 14 experience records and 5 lessons. Markdown
is readable and survives restarts, but retrieval is recency/importance based;
there is no semantic search, provenance graph, locking, or external backup.

## Test and benchmark results

Run on 2026-08-29 without Gemini API calls:

| Check | Result |
|---|---|
| Unit tests | PASS — 7/7 |
| Offline evaluator benchmark | PASS — 21/21 expected domain issues, 100% |
| Offline correction benchmark | PASS — 10/10 cases, 100% |
| Correction average score | 1.02 → 5.00, average improvement +3.98 |
| CLI command discovery | PASS — `reflect`, `decide`, `history`, `verify` |
| Full syntax compile | PASS — `python -m compileall -q main.py brain providers tests` |

The live Gemini benchmark (`tests/run_benchmark.py`) was not run because it
would consume API quota and is not deterministic.

## Git status

- Repository: Git repository detected.
- Remote: `origin` fetch and push both point to
  `https://github.com/pongsatornm1991-droid/AION.git`.
- Remote configuration is correct; no remote change was made.
- The working tree is intentionally dirty. Tracked modifications include
  `README.md`, `brain/memory.py`, `brain/thinker.py`, `main.py`,
  `memory/experiences.md`, and `providers/gemini.py`.
- New, untracked cognitive modules and tests are also present. They should be
  reviewed, tested, and committed as a coherent baseline before broader work.

## Current autonomy and self-improvement level

- **Autonomy:** Level 1–2 only. The application performs local reasoning,
  local memory operations, and a configured model call when explicitly run. It
  has no scheduler, web research, inbox access, publishing, or 24/7 process.
- **Learning:** Operational feedback is stored as Markdown lessons. AION does
  not train model weights, verify web claims, or automatically revise beliefs.
- **Self-improvement:** The code has evaluation and correction behavior, but no
  controlled proposal/test/approval/deploy system for code changes.

## Gaps and risks

1. No stable project-wide test command or CI workflow.
2. `MemoryEngine.move` rewrites a Markdown category and needs filesystem-level
   tests for preservation and failure recovery.
3. Decision records identify promotion targets by timestamp, which can be
   ambiguous if multiple decisions are stored in the same second.
4. Output evaluation is deterministic but primarily vocabulary/regex based; it
   is not a general factual-verification system.
5. No belief, self-model, curiosity, goal, experiment, metacognition, tool, or
   autonomous lifecycle subsystem exists yet.
6. All memory is local Markdown and has no locking or conflict handling.

## Recommended next implementation phase

**Phase 1 — Stabilize current architecture.**

Do not add beliefs, web research, or autonomous actions yet. First establish a
single test command, complete deterministic tests for memory moves and failure
paths, assign stable decision IDs, make the provider interface real, and create
a reviewed Git baseline commit.


---

## Independent verification (Claude, 2026-08-29)

This section was added by an independent audit pass. It does not replace the
analysis above; it confirms what was reproducible and records new findings.

### Confirmed accurate (reproduced independently)

- `python -m compileall -q main.py brain providers tests` -> PASS (exit 0).
- Offline evaluator benchmark (`tests/offline_benchmark.py`) -> PASS, 21/21
  expected domain issues detected, 100%.
- Offline correction benchmark (`tests/correction_benchmark.py`) -> PASS,
  10/10 cases, average improvement +3.98 (matches this document).
- `git remote -v` -> `origin` fetch/push both point to
  `https://github.com/pongsatornm1991-droid/AION.git`. No `/tree/main`
  suffix present. No remote change was needed.
- `memory/experiences.md` contains 14 entries, `memory/lessons.md` contains
  5 entries (counted directly with `grep -c "^## "`).
- `VERSION` in `main.py` is `"0.0.8"`. The only Git tag is `v0.0.2`
  (on commit `31ccb26`), so the tag is stale relative to the working tree.

### Correction: environment gap found and fixed

Before any fix, `python -m unittest discover -s tests -p "test_*.py"` and
every `main.py` subcommand -- including `decide`, `history`, and `verify`,
none of which call Gemini -- failed immediately with:

```
ImportError: cannot import name 'genai' from 'google' (unknown location)
```

Cause: the `google-genai` package (listed in `requirements.txt`) was not
installed in this machine's Python environment. This is an environment gap,
not a code defect. It was fixed by running `pip install google-genai`. After
the fix, `python -m unittest discover -s tests -p "test_*.py"` passed 7/7 and
`python main.py decide --no-save ...` ran successfully -- both now match the
"Test and benchmark results" section above.

### New finding: decide/history/verify are needlessly coupled to Gemini

`main.py` line 12 unconditionally imports
`from providers.gemini import GeminiProvider` at module load time. This means
`decide`, `history`, and `verify` -- commands that never call Gemini --
cannot run at all in any environment where `google-genai` is missing. This
conflicts with the project's own goal that the decision/audit path work
"without calling Gemini." Recommended fix (Phase 1 scope): import
`GeminiProvider` lazily inside `run_reflection()` instead of at module level.

### New finding: large diffs in core/*.md with no visible content change

`git diff --stat` reports `core/birth.md`, `core/identity.md`,
`core/purpose.md`, and `core/values.md` as changed by 76-176 lines each, but
reading the working-tree files directly shows the same visible Markdown
content as the version fetched from GitHub. This is most likely a
line-ending (CRLF/LF) or whitespace-only difference. **NOT VERIFIED** beyond
the diff stat -- review with `git diff --ignore-all-space core/` before
creating the Phase 1 baseline commit.

### Confirmed: decision persistence is untested end-to-end

`memory/decisions_accepted.md` and `memory/decisions_pending_verification.md`
do not exist on disk. The `decide`/`history`/`verify` commands are covered by
unit tests using in-memory mock objects (`RecordingMemory`, `HistoryMemory`),
but no real `decide` run has ever written to actual memory files on this
machine. **NOT VERIFIED**: real-file persistence behavior for these two
categories.

### Confirmed: no live Gemini key configured

`.env` exists but both `GEMINI_API_KEY` and `GEMINI_MODEL` are empty. This
means `python main.py reflect` and `tests/run_benchmark.py` (which calls the
real API) cannot run yet. This is expected/by design (no key has been added),
not a bug.
