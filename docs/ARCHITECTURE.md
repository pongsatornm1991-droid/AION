# AION Architecture

## Current system

```text
core/*.md ──► Identity ─────────────────────────────────────────────┐
memory/*.md ► MemoryEngine ► Thinker ► Reflection prompt ─► Gemini  │
                                                              │      │
                                                              ▼      │
                                                    OutputEvaluator  │
                                                              │      │
                         score < 4.0 ─► CorrectionEngine ─────┘      │
                                                              │      │
                                                              ▼      │
                                             experiences + lessons ──┘
```

The reflection loop is explicitly invoked through `python main.py reflect`.
It is not a background process and does not claim awareness or consciousness.

## Decision path

```text
Question + options + facts + inferences + uncertainties
                         │
              ┌──────────┴──────────┐
              ▼                     ▼
       DecisionEngine         CognitiveAuditor
       confidence score       risk, flags, recommendations
              └──────────┬──────────┘
                         ▼
          LOW risk and no flags?
               ├── yes ─► decisions_accepted.md
               └── no  ─► decisions_pending_verification.md
                                  │
                     additional verified facts
                                  ▼
                         re-audit through `verify`
```

## Component responsibilities

| Component | Responsibility |
|---|---|
| `Identity` | Loads stable core Markdown files |
| `MemoryEngine` | Structured Markdown persistence and retrieval |
| `Thinker` | Assembles identity, memory, lessons, and recent decisions into context |
| `GeminiProvider` | Sends prompts to the configured Gemini model |
| `OutputEvaluator` | Applies deterministic output-quality and safety checks |
| `CorrectionEngine` | Requests a corrected output only when evaluation is insufficient |
| `LearningEngine` | Converts evaluation outcomes into persistent lessons |
| `DecisionEngine` | Computes structured confidence from supplied inputs |
| `CognitiveAuditor` | Assesses risk and recommendations for a proposed conclusion |
| `DecisionHistory` | Lists and conditionally promotes persisted decisions |
| `MemoryConsolidator` | Summarizes old, low-importance memories into semantic knowledge, gated on `OutputEvaluator`'s claim-safety sub-score |
| `BeliefSystem` | Explicit claims with confidence, required evidence, revision lineage, and computed expiration — never an in-place edit |
| `BoundedItemTracker` | Shared base for a bounded, evidence-gated open-item tracker (raise/open with completion criteria + budget, log attempts, resolve only with evidence, or abandon with a reason) — never an in-place edit |
| `CuriosityEngine` | AION's bounded set of open questions, built on `BoundedItemTracker` |
| `GoalEngine` | AION's bounded set of active goals, built on `BoundedItemTracker` |
| `ExperimentEngine` | A predict -> observe -> conclude loop: predictions need no evidence, but an observation always does; conclude() can optionally revise an existing belief — never in place |
| `MetacognitionEngine` | Reports calibration, recurring lesson sources, and memory quality purely from what's on disk; reports tool reliability as not-yet-applicable rather than fabricating a figure |
| `ToolRegistry` / `ToolLifecycle` | Propose -> approve/reject -> execute -> recover/abandon for any registered tool, gated by action level, a kill switch, per-level budgets, and scheduling; only read-only tools are actually registered yet |
| `SocialContentGenerator` / `SocialAutoCycle` (`brain/social.py`) | Picks a real memory entry as a seed, drafts a post via the AI provider, gates every draft through `OutputEvaluator.claim_safety` before it may be proposed; runs the full propose -> approve -> execute cycle autonomously using a non-AION approver identity |
| `tools/facebook.py` | The one real external-facing action: publishes one text post to a Facebook Page via the Graph API; credentials come only from environment variables, never hardcoded |
| `tools/telegram.py` | Sends a short Thai summary of every draft/cycle outcome (posted, blocked, or failed) to the user's own Telegram; optional, never blocks drafting or posting if unconfigured; deliberately outside `ToolLifecycle` -- an echo of a decision, not a new one |

## Explicit boundaries

- Memory is data supplied to the model, not proof of fact.
- A pending decision is always treated as unverified context.
- Gemini output is evaluated, but the evaluator does not independently verify
  external facts.
- External communication, web retrieval, social-media actions, scheduling, and
  self-modifying code are not implemented.
- A belief is never created from bare AI output: `BeliefSystem.form_belief()`
  raises if no evidence is supplied, regardless of how confident the
  statement sounds.
- A question or goal can never be opened without stating its own
  completion criteria, and can never be resolved without supporting
  evidence — the same discipline as beliefs, applied to curiosity and
  goal-selection. Only a bounded number may be open at once.
- An experiment's observation can never be recorded without evidence,
  and a mismatched prediction can never be recorded without stating
  what the mismatch was. Whether a prediction "matched" is always
  stated explicitly by the caller — `ExperimentEngine` never infers
  it. A belief is only ever revised from an experiment's conclusion
  when the caller explicitly names both the belief and the
  experiment; nothing here revises a belief automatically.
- `MetacognitionEngine` never invents a self-assessment: calibration
  and recurring-error numbers come straight from `ExperimentEngine`
  and logged lessons, memory-quality numbers come straight from
  `MemoryEngine`'s own primitives, and a bucket/category with too
  little data is reported as `insufficient_data` rather than guessed
  at. Tool reliability is reported `not_applicable` until a tool
  framework exists to measure.
- No action -- of any level -- executes while the kill switch is
  engaged; this is checked first, unconditionally, in
  `ToolLifecycle.execute()`, before approval, schedule, or budget are
  even considered. A `HIGH_RISK` action can never be approved by AION
  itself (`approve()` raises if the approver is "aion"); only a
  `LOW_RISK` or `READ_ONLY` action can be self-approved. Only
  genuinely read-only tools are registered for real right now
  (`build_builtin_tools()`) -- nothing claims AION can already act on
  the outside world.
- Social posting is fully autonomous in *when* and *how often*, but
  never in *whether an unsafe claim can go out*: every draft passes
  through `OutputEvaluator.claim_safety` inside
  `SocialContentGenerator.draft_post()` before it may even be
  proposed, and `SocialAutoCycle` approves with the identity
  `"auto-safety-gate"` -- never `"aion"` -- so the `HIGH_RISK`
  self-approval prohibition above is never weakened for this phase.
  `post_to_facebook` is registered as `HIGH_RISK`, so it also inherits
  the kill switch and the budget cap unchanged. A "beyond human"
  *feeling/consciousness* claim is blocked the same as an ordinary
  one (`CONSCIOUSNESS_PATTERNS` requires a feeling/consciousness word
  near the "เหนือมนุษย์"-style phrase); a "beyond human"
  *knowledge/capability* claim is a different, true claim and is not
  blocked. A second, independent gate (`_detect_robotic_terms()`)
  blocks a draft that reads like a system status report rather than a
  person's musing, regardless of how safe its content is; each block
  is logged as a lesson and folded into the next draft's prompt --
  AION's voice evolves purely from reviewing its own past drafts,
  never from Facebook engagement data.
- Telegram notification (`tools/telegram.py`, wired in `main.py`) fires
  for every `draft-post`/`run-social-cycle` outcome -- posted, blocked
  at the safety gate, or failed -- so the user sees a blocked/unsafe
  draft exactly as readily as a successful post, never only the good
  news. It is a best-effort side channel: unconfigured or failing
  Telegram credentials never prevent drafting or posting from working.

## Intended evolution

Stabilization comes before adding new cognitive subsystems. The next systems
should be introduced as separate, testable components with explicit data
contracts and persistence formats.
