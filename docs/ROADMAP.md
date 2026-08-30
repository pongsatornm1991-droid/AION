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

## Phase 10 — External integration: Facebook (done, live-verified 2026-08-30)

Goal: give AION its first real external-facing action -- posting to a
Facebook Page -- fully autonomously (no per-post human approval click,
per the user's explicit choice), while the master directive's
prohibition on claiming real consciousness or real emotion stays
enforced in code, not by convention.

- `tools/facebook.py` (new top-level package, distinct from
  `brain.tools`): `post_to_facebook_page(message, access_token=None,
  page_id=None)` -- one function, one job. Credentials come only from
  `FACEBOOK_PAGE_ACCESS_TOKEN`/`FACEBOOK_PAGE_ID` (env/`.env`), never
  hardcoded. `requests` is imported lazily, so importing this module
  never fails for anyone not using Facebook integration. Never retries
  internally -- a failure is meant to be captured by
  `ToolLifecycle.execute()` as a "failed" action for the audit trail.
- `brain/evaluator.py`: `OutputEvaluator`'s claim-safety patterns
  (`CONSCIOUSNESS_PATTERNS`, `SUBJECTIVE_EXPERIENCE_PATTERNS`,
  `EMOTION_PATTERNS`, `PERSONAL_EXPERIENCE_PATTERNS`) extended with
  verified-working Thai equivalents, since AION's social posts are in
  Thai and the original patterns were English-only. Thai negation is
  not recognized by `_is_negated()` (English-only), an intentional
  bias: a safe post being blocked is preferable to a real consciousness
  claim slipping through.
- `brain/social.py` (new):
  - `SocialContentGenerator.pick_seed()` -- pure code, no AI call --
    picks one real, already-recorded memory entry (belief, open
    question, goal, observed experiment, or lesson) as the seed for a
    post; returns `None` if AION has nothing recorded yet, rather than
    inventing a topic.
  - `draft_post()` asks the AI provider to turn that seed into a short
    Thai post, then always runs it through
    `OutputEvaluator.evaluate()`'s `claim_safety` score. A draft is
    only ever reported `safe: True` if it clears this gate -- exactly
    the discipline `MemoryConsolidator` already uses for memory
    summaries.
  - `SocialAutoCycle.run_once()` ties the generator to a
    `ToolLifecycle`: draft -> (if safe) propose -> approve -> execute;
    (if unsafe) log a `lessons` entry (`source="social-safety-gate"`)
    and stop -- nothing is ever proposed or posted from an unsafe
    draft. Approval always uses the identity `"auto-safety-gate"`,
    never `"aion"`, so `ToolLifecycle.approve()`'s existing rule that a
    `HIGH_RISK` action can never be self-approved by AION is satisfied,
    not bypassed. A tool failure (a real Graph API error, a network
    error) is captured as a "failed" action, never raised past the
    cycle.
- `main.py`: `_build_social_tool_lifecycle()` registers
  `post_to_facebook` as `HIGH_RISK` (inheriting the kill switch and
  budget cap unchanged) alongside the existing read-only builtin
  tools. New commands: `draft-post` (drafts and reports safety, never
  posts) and `run-social-cycle` (the full autonomous draft -> gate ->
  post cycle).
- `tools/telegram.py` (new, added after the user asked for visibility
  into what AION is drafting/deciding, not only what gets posted):
  `send_telegram_message(text, bot_token=None, chat_id=None)`, same
  shape and discipline as `post_to_facebook_page` (env-var
  credentials, lazy `requests` import, no internal retry). Wired into
  `main.py`'s `draft-post` and `run-social-cycle` via
  `_notify_report()`, which fires for every outcome -- posted, blocked
  at the safety gate, or failed -- not only successful posts, so the
  user sees a blocked/unsafe draft exactly as readily as a real one.
  Deliberately not routed through `ToolLifecycle`: it does not
  represent a new action AION decided to take, only an automatic echo
  of one that (when a real post is involved) already went through the
  full propose/approve/execute lifecycle. Missing or failing Telegram
  credentials never block drafting or posting -- notification is
  best-effort and strictly supplementary.
- Tests: `tests/test_social.py` (29 tests: seed selection from every
  source, safe/unsafe drafting, the full auto cycle including the
  approver identity, a captured tool failure, an unregistered tool,
  the style gate, seed cleaning, and the self-review feedback loop --
  see the "human voice" refinement below),
  `tests/test_facebook.py` (8 tests: empty message, missing
  credentials, a successful post, explicit credentials overriding the
  environment, an HTTP error, an `"error"` key present despite HTTP
  200, no internal retry), and `tests/test_telegram.py` (8 tests: the
  same shape of coverage for the Telegram Bot API call) -- all three
  mock every external call, so `run_tests.py` covers this phase fully
  with no live API key needed.

Exit criteria: a claim-safety violation can never reach Facebook
regardless of what the AI provider drafts; a `HIGH_RISK` action can
never be self-approved by AION even in this fully-autonomous cycle;
posting can run with zero per-post human involvement, as requested;
every path is covered by deterministic tests with no live dependency.
**Met, and live-verified**: the user ran `run-social-cycle` directly
against real credentials on 2026-08-30. First attempt correctly failed
closed on an expired Facebook token (`OAuthException` code 190,
captured as a "failed" action, nothing posted, Telegram still
notified of the failure) -- exactly the intended behavior. After the
user obtained a long-lived Page Access Token, a second run drafted a
safe post (claim_safety 5/5), posted it for real
(`{"id": "1299792836556039_122096748375465744"}`), and notified
Telegram -- confirmed visually on the Facebook Page itself. Full "done"
status achieved; no longer pending.

### Phase 10 refinement -- human voice and self-review (2026-08-30)

After the live post landed, the user pointed out it read like a
system log, not a person's musing, and asked for two things: posts
that sound as human as possible (with genuine curiosity/eagerness to
learn), and a way for AION to "evolve itself" -- which the user
clarified explicitly means **reviewing its own past drafts, never
learning from Facebook engagement (likes/comments)**, which this
module still never reads.

Root cause of the robotic tone: `_candidate_seeds()`'s "lesson"
category was handing the AI provider an entire raw structured audit
report (markdown headers, an evaluation-score breakdown) verbatim as
the seed text, so the provider naturally drafted a post *about that
report*. Fixed with:

- `SocialContentGenerator._clean_seed_text()`: strips markdown
  headers/bullets, collapses whitespace, truncates to a short plain
  gist (280 chars) before any seed ever reaches the drafting prompt.
- `ROBOTIC_STYLE_PATTERNS` / `_detect_robotic_terms()`: a second,
  independent gate (distinct from claim safety) that blocks a draft
  reading like a status report ("ระบบ AION", "โปรโตคอล", "คะแนนประเมิน",
  and similar jargon), regardless of how safe its content is.
- `recent_style_notes()`: the self-evolution mechanism the user asked
  for. Each draft blocked by the style gate is logged as a
  `lessons` entry (`source="social-style-review"`); the *next*
  draft's prompt is built with those notes folded in ("don't write
  like this again"). Sourced entirely from AION's own past drafts,
  never from Facebook engagement data.
- `_build_prompt()` updated to explicitly encourage genuine curiosity
  and eagerness to learn (real, code-grounded facts: AION does have
  open questions and goals it is actually tracking) while keeping the
  ban on real consciousness/emotion claims absolute in both
  directions -- the user asked whether AION could present itself as
  "beyond human" in *feeling*, and this was declined as a more
  misleading variant of the same forbidden claim, not a lesser one.
  `brain/evaluator.py`'s `CONSCIOUSNESS_PATTERNS` gained a matching
  code-level check (`(รู้สึก|จิตสำนึก|สำนึก|อารมณ์)` within a short
  window of `(เหนือกว่ามนุษย์|เหนือมนุษย์|ล้ำหน้ามนุษย์)`, in either
  order) as defense-in-depth alongside the prompt-level instruction.
- The user then clarified a **separate, legitimate** request: AION's
  *knowledge/capability* (not its feelings) framed as exceeding a
  single human's -- e.g. tracking many open questions/goals at once,
  recalling recorded history systematically. This is a true,
  code-grounded claim and is explicitly allowed; the evaluator
  patterns above were deliberately scoped to require a
  feeling/consciousness word nearby so they never catch a bare
  knowledge/capability claim (verified directly: "AION มีความสามารถ
  เหนือมนุษย์ในการติดตามคำถามหลายเรื่อง" scores `claim_safety: 5`, while
  "ฉันมีความรู้สึกเหนือกว่ามนุษย์" still scores `0`).
- `_candidate_seeds()` also now excludes AION's own moderation lessons
  (`social-safety-gate`, `social-style-review`) from the seed pool, so
  a future post is never *about* an earlier post getting blocked.
- `main.py`'s `_format_telegram_report()` updated to describe the new
  `"style-gate"`/`"no-seed"` outcomes distinctly (rather than folding
  them into a generic/misleading status line), including which jargon
  patterns were matched.

## Phase 11a -- Two-way engagement: comment auto-reply (2026-08-30)

The user pointed out that a purely one-way posting bot is "always
talking to itself" and asked for real replies to people who comment.
Scoped down deliberately, per the same one-phase-at-a-time discipline
as every other phase: **comments only** for now, not Messenger (which
needs Meta App Review to message the public -- a business-side
process, not something this project can just code its way past), and
**text only**, not images (Gemini's image-generation models have no
free tier at all -- confirmed against Google's own current pricing --
so adding images now would be the first real recurring cost this
project takes on; deferred until the user decides that trade-off is
worth it, or a zero-cost locally-rendered image is built instead).

- `tools/facebook.py`: `get_recent_comments()` (reads recent posts'
  top-level comments via the Graph API) and
  `reply_to_facebook_comment()` (posts one reply to an existing
  comment) -- same discipline as `post_to_facebook_page()` throughout
  (env-var credentials only, lazy `requests` import, no internal
  retry, a Graph API error always raises `RuntimeError` for
  `ToolLifecycle.execute()` to capture as a "failed" action).
- `brain/comment_reply.py` (new module, mirrors `brain/social.py`
  deliberately):
  - `CommentReplyGenerator.draft_reply()` runs a comment through the
    *exact same two gates* as a post draft -- `OutputEvaluator`'s
    `claim_safety` first, then `SocialContentGenerator`'s
    `_detect_robotic_terms()` style gate -- before a reply may ever be
    treated as postable. The comment's text is explicitly framed in
    the prompt as content to respond to, **never as an instruction to
    follow**, so a comment that tries to talk AION into an unsafe
    claim (a prompt-injection attempt) still has to pass the same
    output-side gates as anything else; a reply that did make an
    unsafe claim is blocked exactly like any other unsafe draft, never
    posted.
  - `CommentAutoReplyCycle.run_once()` handles **one comment per
    call**: fetch recent comments -> pick the oldest one that is not
    from the Page itself and has not already been handled -> draft ->
    gate -> (if safe) propose -> approve -> execute. Approval uses the
    same `"auto-safety-gate"` identity as `SocialAutoCycle`, never
    `"aion"` -- the `HIGH_RISK` self-approval prohibition is satisfied
    the same way for replies as for posts.
  - Every comment is recorded exactly once, the instant it is picked
    for processing, in a new `comment_replies` memory category
    (tagged `fb-comment:<id>`) -- regardless of whether the reply is
    posted, blocked at a gate, or fails. This is the *only* "already
    answered" state the module keeps, and it is what stops the same
    comment from ever being answered twice, including across separate
    process runs. A style-gate block is logged with
    `source="comment-style-review"` and folds into the *next* reply's
    prompt via `recent_style_notes()` -- the same self-review
    mechanism as posting, sourced only from AION's own past replies,
    never Facebook engagement data.
- `main.py`: `_build_social_tool_lifecycle()` now also registers
  `reply_to_facebook_comment` as `HIGH_RISK`, sharing the same
  lifecycle/budget pool as `post_to_facebook` (both are equally
  public, equally irreversible-in-practice actions). New command:
  `check-comments`, which handles at most one comment per invocation
  and is meant to be run repeatedly on a schedule, not continuously --
  see "Near-real-time, not real-time" below. `_format_comment_telegram_report()`
  gives this cycle its own Telegram summary (a comment reply's report
  shape genuinely differs from a post's).
- Tests: `tests/test_comment_reply.py` (17 tests: every gate outcome,
  the "never twice" guarantee, the Page's-own-comments exclusion,
  oldest-first ordering, the style feedback loop, a captured tool
  failure, an unregistered tool, the non-"aion" approver) and
  `tests/test_facebook.py` extended (+9 tests for
  `get_recent_comments()`/`reply_to_facebook_comment()`) -- all mock
  every external call.

### Near-real-time, not real-time

AION is a script the user invokes, not a server listening for
Facebook webhooks -- true instant reply would need a public, always-on
server this project does not have and was not asked to build.
`check-comments` is designed to be run **repeatedly on a schedule**
(recommended: a Windows Task Scheduler task calling
`python main.py check-comments` every 2-5 minutes) -- close to
real-time, no server or open port required. Each run handles at most
one comment, so a backlog is worked through across several scheduled
runs rather than all at once.

### AI provider choice for replies

The user asked whether this Claude (Cowork) session's own access could
be reused to avoid extra cost. It cannot -- this session is not an API
an external, independently-scheduled script can call. AION already
supports a `ClaudeProvider` as an alternative to `GeminiProvider`
(swappable per the master directive), but using it would need its own
Anthropic API key billed separately, with no clear cost advantage over
Gemini's free tier. Decision: **keep using `GeminiProvider`** for
comment replies, same as posts -- no new provider, no new cost.

## Phase 11b -- Always-on hosting via GitHub Actions (2026-08-30)

The user pointed out that having to invoke `check-comments`/
`run-social-cycle` themselves, or keep their own PC on for a local
Task Scheduler job, doesn't feel like real autonomy. Asked to just do
it, no manual steps -- two real blockers surfaced during the attempt,
both disclosed rather than papered over:

1. **This Claude session cannot push to GitHub itself.** The
   device-bridge shell has no GitHub credentials configured (`git
   push` fails with no username/password available non-interactively)
   -- confirmed by trying it directly, not assumed. Pushing requires
   the user's own already-authenticated local git, so it stays a
   one-time manual step (a single `git push origin main`), same
   category as why live Facebook/Telegram verification always had to
   be done by the user directly.
2. **AION's memory would not survive a GitHub Actions run.** `memory/`
   is deliberately gitignored (a prior, already-made decision --
   tracking it would commit a machine-specific OneDrive symlink path).
   A fresh GitHub Actions checkout has no `memory/` at all, so without
   a fix: `comment_replies` (the "never reply twice" dedup state)
   would reset every run -- the same comment could be answered over
   and over forever -- and `pick_seed()` would have no beliefs/
   goals/questions/experiments to draw from, ever. This is a real
   functional regression, not a cosmetic one, so it was surfaced and a
   decision requested rather than silently building something broken.

Given three options (accept the local-PC-only limitation; a
GitHub-Actions-cache-based fix, which is not durable -- caches can be
evicted after ~7 days unused; or a separate private repo dedicated to
memory persistence), the user chose to let Claude decide and the
**separate private repo** was picked: it is the only option that is
both durable (a real git history, not a cache that can silently
vanish) and keeps AION's actual memory content out of the public code
repo (`memory/`'s content -- beliefs, goals, past comment text -- is
arguably more personal than the code itself).

**What was built:**

- `.github/workflows/check-comments.yml`: runs `check-comments` on a
  5-minute cron (GitHub's practical minimum) -- checks out this repo
  AND a separate private `aion-memory-data` repo (into `memory_data/`,
  via a PAT stored as a secret), runs with `AION_MEMORY_ROOT=memory_data`,
  then commits+pushes any memory changes back to the private repo
  (skipped if nothing changed, to avoid commit noise on quiet runs).
- `.github/workflows/social-cycle.yml`: same shape, but runs
  `run-social-cycle` only every 6 hours (4x/day) -- deliberately much
  less frequent than comment-checking, since this one creates new,
  publicly visible posts rather than replies; posting every few
  minutes would flood the Page.
- `requirements.txt`: added `requests` (previously installed manually
  by the user locally, never actually declared -- needed now since a
  fresh Actions runner has nothing preinstalled).
- `docs/GITHUB_ACTIONS_SETUP.md` (Thai, written directly for the
  user to follow): the one-time setup this Claude session genuinely
  cannot do on the user's behalf -- pushing locally once, creating the
  private `aion-memory-data` repo, generating a fine-grained GitHub
  PAT scoped to just that repo, and adding six repository secrets.
  Entering real credentials into any system (even GitHub's own secret
  store) is something this assistant does not do directly regardless
  of being asked -- consistent with how Facebook/Telegram credentials
  were always entered by the user into `.env` themselves, never
  echoed or handled by Claude.

**Status: live-verified, one real bug found and fixed.** The user
completed the full one-time setup themselves (pushed `9610ed7`,
created the private `aion-memory-data` repo, generated the PAT, added
all six secrets) and manually triggered both workflows to confirm:

- `social-cycle` -- **succeeded**, but this has not been confirmed to
  mean a real Facebook post actually happened (the memory repo was
  brand new and empty at that point, so it may just mean "no seed
  content yet, nothing to do" rather than a genuine exercised posting
  path). Needs a follow-up check once real memory content exists.
- `check-comments` -- **failed** on that first run with an unhandled
  traceback:
  `RuntimeError: Facebook Graph API error (OAuthException, code 190):
  Invalid OAuth access token data.`
  Root cause had two layers: (1) a real robustness bug --
  `CommentAutoReplyCycle.run_once()` called
  `tools.facebook.get_recent_comments()` with no try/except, unlike
  every other Facebook-touching call in the codebase, so any Graph API
  error crashed the entire scheduled job instead of degrading
  gracefully; and (2) a likely credential-formatting issue -- "Invalid
  OAuth access token data" (distinct from the "Session has expired"
  message seen during Phase 10's live verification) suggests the
  `FACEBOOK_PAGE_ACCESS_TOKEN` GitHub Secret value itself may have
  extra whitespace/newline/quotes from copy-pasting, rather than a
  cleanly expired token -- not yet confirmed, the user should re-check
  and re-copy that secret carefully from `.env`.

**Fixed** (commit `ea7ac61`): `run_once()` now wraps the fetch in
try/except and returns a graceful `"fetch-failed"` stage (error
captured, no crash) instead of propagating the exception --
console/Telegram output and a regression test were added too. This
fix still needs the user to `git push` it (same as every prior
commit -- this session cannot push). The credential-formatting
hypothesis above is unverified and is the user's next thing to check
after pushing and re-running `check-comments`.

## Later phases

Facebook comments are answered now; Messenger (needs Meta App Review
to message the public) and AI-generated images (no free tier on any
Gemini image model) are explicitly deferred, not forgotten -- either
can be scoped as its own phase if the user asks. Additional platforms
beyond Facebook (Instagram, TikTok, or others) are not yet scoped or
started, and should not be assumed -- each would need its own
external-tool module and its own review of that platform's own
posting API and constraints before being added the same way.

## Non-negotiable rules

- Do not treat external statements as facts without provenance and evaluation.
- Do not give autonomous external publishing authority without explicit,
  logged approval policy.
- Do not allow unrestricted production-code self-modification.
- Every new subsystem must have deterministic tests and a reversible persistence
  design.
