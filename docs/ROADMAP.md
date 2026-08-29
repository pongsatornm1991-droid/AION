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

## Phase 6 — Curiosity and goals (done, 2026-08-29)

Goal: AION can hold open questions and active goals, each bounded by its own
completion criteria and attempt budget, and never resolved without evidence.

- `brain/bounded_tracker.py` — `BoundedItemTracker`: the shared mechanics
  behind both curiosity and goal-selection. `open_item()` refuses an item
  with no completion criteria, and refuses a new item once `max_open` are
  already open system-wide (default 10) — something must be resolved or
  abandoned first. Each item also carries its own attempt `budget`;
  exhausting it only sets a `budget_exhausted` flag on read, it never
  auto-abandons anything.
- Nothing is edited in place: `record_attempt()` and `resolve_item()` each
  write a new entry (`Predecessor:` field + `related` metadata) and tag the
  previous one `superseded`; `history()` walks the full chain oldest-first,
  exactly like `BeliefSystem`. `resolve_item()` requires at least one piece
  of evidence, same rule as `form_belief()`. `abandon_item()` tags the item
  `abandoned` and logs a companion `lessons` entry recording why.
- `brain/curiosity.py` — `CuriosityEngine` (category `questions`,
  `TYPE: question`): `raise_question()` / `answer_question()` /
  `abandon_question()` / `open_questions()`.
- `brain/goals.py` — `GoalEngine` (category `goals`, `TYPE: goal`, default
  budget 5): `set_goal()` / `complete_goal()` / `abandon_goal()` /
  `active_goals()`. Both memory types were added to
  `MemoryEngine.MEMORY_TYPES`.
- New CLI: `main.py ask` / `questions` / `attempt-question` /
  `answer-question` / `abandon-question`, and the goal equivalents
  `set-goal` / `goals` / `attempt-goal` / `complete-goal` / `abandon-goal`.
  None of this calls an AI provider, so it is fully covered by
  `run_tests.py`.
- Tests: `tests/test_curiosity_goals.py` (19 tests, no AI call anywhere) —
  criteria/priority/budget validation, the bounded max-open cap and a slot
  freeing up on resolution, attempt supersession, the budget-exhausted flag
  never forcing a transition, evidence-gated resolution, refusing further
  attempts/resolution on an already-resolved item, abandonment + its lesson
  entry, full history-chain walking across attempts and resolution, topic
  filtering, and a lighter GoalEngine lifecycle test confirming the
  subclass wiring.

Exit criteria: an item can never be opened without completion criteria, the
system-wide open-item cap is enforced, resolution always requires evidence,
and every path (including the bounded-cap and budget-exhaustion behavior)
is covered by deterministic tests with no live API dependency. **Met.**

## Phase 7 — Experiments and reflection (done, 2026-08-29)

Goal: AION can state a prediction, record what was actually observed, and
derive a lesson — with a real, optional path from a measured result to a
revised belief, never an automatic one.

- `brain/experiments.py` — `ExperimentEngine` (category `experiments`,
  `TYPE: experiment`): `predict()` / `observe()` / `conclude()` /
  `abandon()`. Unlike beliefs, questions, and goals, `predict()` itself
  requires no evidence — a prediction is a stated expectation, not yet
  a claim. `observe()` does require at least one piece of evidence
  (an observation is a claim), rejects a non-bool `matched`, and
  requires an `error_description` whenever `matched=False`. `conclude()`
  only runs on an observed experiment, always logs a companion
  `lessons` entry, and — only when the caller supplies both
  `belief_system` and `belief_id` — drives a real
  `BeliefSystem.revise_belief()` call, tying a measured surprise back
  into what AION believes without ever doing so silently.
- Nothing is edited in place: `observe()` and `conclude()` each write a
  new entry (`Predecessor:` field + `related` metadata) and tag the
  previous one `superseded`; `history()` walks the full chain
  oldest-first, exactly like `BeliefSystem`/`BoundedItemTracker`.
  `status_of()` derives `predicted`/`observed`/`concluded`/`abandoned`
  purely from parsed content fields plus the `abandoned` tag, no extra
  lifecycle bookkeeping needed.
- `"experiment"` was added to `MemoryEngine.MEMORY_TYPES`.
- New CLI: `main.py predict` / `experiments --status pending|awaiting` /
  `observe` / `conclude` / `abandon-experiment`. None of this calls an
  AI provider, so it is fully covered by `run_tests.py`.
- Tests: `tests/test_experiments.py` (29 tests, no AI call anywhere) —
  prediction validation (empty statement, out-of-range/bool/non-numeric
  confidence, no evidence required), observation validation (evidence
  required, non-bool matched rejected, mismatch without
  error_description rejected, cannot observe twice or observe an
  abandoned/unknown experiment), conclusion validation (cannot conclude
  before observed or twice, empty lesson rejected, companion lesson
  entry logged, optional belief revision wired end-to-end with a real
  `BeliefSystem`, and confirmed no belief is touched when `belief_id`
  is omitted), abandonment from either `predicted` or `observed` (never
  from `concluded`) with its own lesson entry, full history-chain
  walking across predict/observe/conclude, and pending/awaiting
  filtering + sorting + limit.

Exit criteria: a prediction can be stated freely, but an observation can
never be recorded without evidence and a mismatch never without an
explanation; a belief only ever changes from an experiment's conclusion
when the caller explicitly asks for it; every path is covered by
deterministic tests with no live API dependency. **Met.**

## Phase 8 — Metacognition (done, 2026-08-29)

Goal: AION can report on its own track record -- calibration, recurring
failure sources, and memory quality -- using only numbers computed from
what's already on disk, never an AI-judged self-assessment.

- `brain/metacognition.py` — `MetacognitionEngine`:
  - `calibration_report()` buckets every experiment that has actually
    been observed (`ExperimentEngine.observed_experiments()`, a new
    method that includes concluded and abandoned-after-observation
    experiments, since the observation itself is real signal
    regardless of what happened after) by stated confidence, and
    compares average confidence to actual match rate per bucket.
    A bucket below `min_samples_per_bucket` (default 3) is reported
    `insufficient_data` rather than treated as a finding — a single
    lucky or unlucky guess is never a calibration result.
  - `recurring_error_report()` groups every `lessons` entry by its
    `source` field (a literal count, not an AI-judged theme) and flags
    any source recurring at least `min_occurrences` times.
  - `memory_quality_overview()` auto-discovers every category file on
    disk and aggregates `MemoryEngine.quality_report()`/`stats()`
    across them, flagging a category (with at least 3 entries) whose
    average quality falls below a threshold.
  - `full_report()` combines all three, plus `tool_reliability`
    reported as `not_applicable` — AION has no external-tool-execution
    framework yet (that's the next phase), so reporting a reliability
    figure now would be a fabricated number, not a measured one.
- New CLI: `main.py metacognition --report
  {calibration,recurring-errors,memory-quality,full}`. None of this
  calls an AI provider, so it is fully covered by `run_tests.py`.
- Tests: `tests/test_metacognition.py` (20 tests, no AI call anywhere)
  — invalid bucket-size validation, empty-state handling for all three
  reports, insufficient-data flagging, overconfident/underconfident/
  well-calibrated detection with hand-computed expected gaps,
  abandoned-after-observation experiments still counting toward
  calibration, source grouping and the min-occurrences threshold,
  category auto-discovery vs. an explicit category list, a thin
  category never being flagged, and a weighted overall-quality
  average. Plus 5 new tests in `tests/test_experiments.py` for
  `observed_experiments()` itself (excludes predicted-only and
  abandoned-before-observation experiments, includes observed/
  concluded/abandoned-after-observation ones, respects `limit`).

Exit criteria: every reported number traces back to something already
on disk, a report says "not enough data" rather than guessing when data
is thin, and tool reliability is honestly reported as not-yet-
applicable rather than invented. Every path is covered by deterministic
tests with no live API dependency. **Met.**

## Phase 9 — Controlled tools and lifecycle (done, 2026-08-29)

Goal: build the safety machinery a real external tool will need before
any real external tool exists to plug into it -- "read-only research
first" taken literally: only genuinely read-only tools are wired up
for real right now.

- `brain/tools.py`:
  - `ActionLevel` (`READ_ONLY`/`LOW_RISK`/`HIGH_RISK`) and
    `ToolRegistry` (name -> callable + level + description; rejects a
    duplicate name, an unknown level, or a non-callable).
  - `ToolLifecycle` implements propose -> approve/reject -> execute ->
    recover/abandon, in the same append-only, never-edit-in-place
    style as `BeliefSystem`/`ExperimentEngine`: every step writes a
    new entry superseding the last, so `history()` walks the full
    chain. `propose()` requires a registered tool; `approve()`
    requires a non-empty approver and rejects self-approval by "aion"
    for `HIGH_RISK`; `execute()` lets `READ_ONLY` run straight from
    "proposed" but requires "approved" for the other two levels;
    a tool's own exception is caught and recorded as a "failed" entry
    rather than propagated, so the audit trail never has a gap;
    `recover()` only runs on a "failed" entry and requires evidence,
    same discipline as everywhere else -- it documents how a failure
    was handled, it never silently retries.
  - **Kill switch**: `engage_kill_switch()`/`disengage_kill_switch()`/
    `kill_switch_engaged()`, checked first and unconditionally inside
    `execute()` -- when engaged, nothing runs, at any level, no matter
    what else is true.
  - **Budgets**: a rolling-window cap (default 24h) per action level
    on how many actions may actually run (`READ_ONLY` unlimited,
    `LOW_RISK`/`HIGH_RISK` capped); counts both successes and failures
    (an attempt is an attempt), and the window genuinely rolls forward
    over time.
  - **Scheduling**: `propose()` accepts a `scheduled_for` time;
    `execute()` refuses to run it early.
  - `build_builtin_tools()` registers the only tools that actually
    exist right now, all `READ_ONLY`: `memory_stats`, `quality_report`,
    `metacognition_report` -- thin wrappers around primitives that
    already exist elsewhere in this codebase. `LOW_RISK`/`HIGH_RISK`
    tool registration works and is fully tested, but nothing dangerous
    is pluggable in the CLI yet -- that's the next phase.
  - Adds `"action"` to `MemoryEngine.MEMORY_TYPES`.
- New CLI: `main.py tools` / `propose-action` / `actions` /
  `approve-action` / `reject-action` / `execute-action` /
  `recover-action` / `abandon-action` / `engage-kill-switch` /
  `disengage-kill-switch` / `kill-switch-status`. None of this calls an
  AI provider, so it is fully covered by `run_tests.py`.
- Tests: `tests/test_tools.py` (53 tests, no AI call anywhere) --
  registry validation, the full propose/approve/reject/execute/
  recover/abandon lifecycle for all three action levels, self-approval
  allowed for `LOW_RISK` and forbidden for `HIGH_RISK`, tool-exception
  capture as a "failed" record, evidence-gated recovery, the kill
  switch halting execution at every level (with a real clock-mock test
  confirming the budget window actually rolls forward), scheduling
  (future/past/none), full history-chain walking, status/limit
  filtering, and the built-in read-only tools executing against a real
  `MemoryEngine`. Also confirms `MemoryEngine`'s own duplicate-content
  detection would otherwise silently drop a repeated identical
  proposal or kill-switch toggle -- fixed by giving every generated
  entry a random nonce.

Exit criteria: no action can execute while the kill switch is engaged,
a `HIGH_RISK` action can never be self-approved, a budget genuinely
caps how much can run in a window, a failed action is always captured
rather than propagated, and only tools that actually, honestly exist
are registered. Every path is covered by deterministic tests with no
live API dependency. **Met.**

## Later phases

1. **External integration** — only after the prior controls are verified;
   Facebook and messaging integrations should begin as drafts requiring review.

## Non-negotiable rules

- Do not treat external statements as facts without provenance and evaluation.
- Do not give autonomous external publishing authority without explicit,
  logged approval policy.
- Do not allow unrestricted production-code self-modification.
- Every new subsystem must have deterministic tests and a reversible persistence
  design.
