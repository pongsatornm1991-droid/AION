# AION Roadmap

## Phase 1 — Stabilize current architecture (next)

Goal: make the current reflection, memory, decision, and audit paths safe to
extend.

- Provide one deterministic test command and document it.
- Add filesystem-level tests for memory writes, duplicate detection, and moves.
- Replace timestamp-only decision references with stable IDs.
- Make `GeminiProvider` conform to `AIProvider` and add provider-error tests.
- Review the dirty working tree and create a tested baseline commit.

Exit criteria: deterministic tests pass locally, key persistence paths have
regression coverage, and the repository has a reviewed baseline.

## Later phases

1. **Memory retrieval and consolidation** — provenance, search, summaries, and
   retention policy.
2. **Self-model and beliefs** — explicit claims with confidence, evidence,
   revision history, and expiration.
3. **Curiosity and goals** — bounded open questions, priorities, budgets, and
   completion criteria.
4. **Experiments and reflection** — prediction, observed result, error, lesson,
   and measurable belief/behavior change.
5. **Metacognition** — monitor recurring errors, calibration, memory quality,
   and tool reliability.
6. **Controlled tools and lifecycle** — read-only research first, action levels,
   approval gates, scheduling, recovery, budgets, and kill switch.
7. **External integration** — only after the prior controls are verified;
   Facebook and messaging integrations should begin as drafts requiring review.

## Non-negotiable rules

- Do not treat external statements as facts without provenance and evaluation.
- Do not give autonomous external publishing authority without explicit,
  logged approval policy.
- Do not allow unrestricted production-code self-modification.
- Every new subsystem must have deterministic tests and a reversible persistence
  design.
