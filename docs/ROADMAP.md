# AION Roadmap

## Phase 1 — Stabilize current architecture (done, 2026-08-29)

Goal: make the current reflection, memory, decision, and audit paths safe to
extend.

- Provide one deterministic test command and document it.
- Add filesystem-level tests for memory writes, duplicate detection, and moves.
- Replace timestamp-only decision references with stable IDs.
- Make `GeminiProvider` conform to `AIProvider` and add provider-error tests.
- Review the dirty working tree and create a tested baseline commit.

Exit criteria: deterministic tests pass locally, key persistence paths have
regression coverage, and the repository has a reviewed baseline. **Met** —
commit `c9b09e4`, `run_tests.py` passes (unit tests, offline evaluator and
correction benchmarks all 100%).

## Phase 4 — Memory retrieval and consolidation (done, 2026-08-29)

Goal: entries carry provenance/relationships, and old low-value episodic
memories get summarized into semantic knowledge instead of growing forever.

- `MemoryEngine.remember()` accepts `tags`/`related`; both persist through
  `move()` (`brain/memory.py`).
- Pure-code retrieval: `by_tag()`, `add_tags()` (retroactive), `related_entries()`
  (explicit `RELATED:` ids first, then tag-overlap ranking) — no AI call.
- `MemoryConsolidator` (`brain/consolidation.py`): selects old (`--min-age-days`)
  + low-importance (`--max-importance`) entries in code, drafts one summary
  per batch via the swappable AI provider, gates acceptance on `OutputEvaluator`'s
  `claim_safety` sub-score (never on the reflection-shaped `overall_score`),
  and only then archives sources (`move()`, never delete) and saves a
  `TYPE: semantic` entry linking back to them. `main.py consolidate` CLI.
- Tests: `tests/test_consolidation.py` (stub provider, no live API) covers
  selection filtering, too-small batches, a full consolidate-and-archive pass,
  an unsafe-summary rejection, and no-reselection after consolidation.

Exit criteria: consolidation never runs against a live provider in `run_tests.py`,
an unsafe or too-small draft never touches source entries, and a real
filesystem round trip is covered by tests. **Met.**

## Later phases

1. **Self-model and beliefs** — explicit claims with confidence, evidence,
   revision history, and expiration.
2. **Curiosity and goals** — bounded open questions, priorities, budgets, and
   completion criteria.
3. **Experiments and reflection** — prediction, observed result, error, lesson,
   and measurable belief/behavior change.
4. **Metacognition** — monitor recurring errors, calibration, memory quality,
   and tool reliability.
5. **Controlled tools and lifecycle** — read-only research first, action levels,
   approval gates, scheduling, recovery, budgets, and kill switch.
6. **External integration** — only after the prior controls are verified;
   Facebook and messaging integrations should begin as drafts requiring review.

## Non-negotiable rules

- Do not treat external statements as facts without provenance and evaluation.
- Do not give autonomous external publishing authority without explicit,
  logged approval policy.
- Do not allow unrestricted production-code self-modification.
- Every new subsystem must have deterministic tests and a reversible persistence
  design.
