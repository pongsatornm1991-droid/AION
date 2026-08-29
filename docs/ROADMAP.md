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

## Phase 5 — Self-model and beliefs (done, 2026-08-29)

Goal: AION can hold explicit claims about itself or the world, each backed by
evidence, with confidence, a revision trail, and an expiration — never a
bare assertion picked up from AI output.

- `brain/beliefs.py` — `BeliefSystem`: `form_belief()` refuses to save
  anything with zero supporting evidence (a code-enforced guardrail, not a
  suggestion); confidence is validated to `[0.0, 1.0]` and mapped to the
  existing memory `importance` field.
- Revision is never an in-place edit: `revise_belief()` writes a brand-new
  belief entry (`Predecessor:` field + `related` metadata pointing at the
  old id) and tags the old entry `superseded`. `history()` walks the
  predecessor chain oldest-first, and it is never filtered by status — the
  full lineage, superseded entries included, stays on disk.
- `retract_belief()` tags an entry `retracted` (no replacement) and writes a
  companion `lessons` entry recording why, so a retraction is itself
  auditable.
- Expiration is a computed property, not a one-way stored transition:
  `status_of()` compares the stored `Expires:` date against the current
  time on every read, so a belief that looks expired under a mocked future
  clock is active again once real time is back before that date.
  `expires_in_days=0` opts a belief out of expiring at all (e.g. for a
  foundational claim); the default is 90 days.
- Beliefs live in `memory/beliefs.md` under the existing `TYPE: belief`
  memory type, reusing Phase 4's `tags`/`related` fields directly — no new
  storage format was needed.
- New CLI: `main.py believe` / `beliefs` / `revise-belief` / `retract-belief`.
  None of this calls an AI provider, so unlike `consolidate` it is fully
  covered by `run_tests.py`.
- Tests: `tests/test_beliefs.py` (16 tests, no AI call anywhere) — evidence
  requirement, confidence/expiry validation, disk roundtrip, topic
  filtering, revision supersession and lineage, retraction and its lesson
  entry, and the mocked-clock expiration/un-expiration case.

Exit criteria: a belief can never be created without evidence, a revision
never destroys the previous version, expiration is verifiably computed
rather than stored, and every path is covered by deterministic tests with
no live API dependency. **Met.**

## Later phases

1. **Curiosity and goals** — bounded open questions, priorities, budgets, and
   completion criteria.
2. **Experiments and reflection** — prediction, observed result, error, lesson,
   and measurable belief/behavior change.
3. **Metacognition** — monitor recurring errors, calibration, memory quality,
   and tool reliability.
4. **Controlled tools and lifecycle** — read-only research first, action levels,
   approval gates, scheduling, recovery, budgets, and kill switch.
5. **External integration** — only after the prior controls are verified;
   Facebook and messaging integrations should begin as drafts requiring review.

## Non-negotiable rules

- Do not treat external statements as facts without provenance and evaluation.
- Do not give autonomous external publishing authority without explicit,
  logged approval policy.
- Do not allow unrestricted production-code self-modification.
- Every new subsystem must have deterministic tests and a reversible persistence
  design.
