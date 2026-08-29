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

## Explicit boundaries

- Memory is data supplied to the model, not proof of fact.
- A pending decision is always treated as unverified context.
- Gemini output is evaluated, but the evaluator does not independently verify
  external facts.
- External communication, web retrieval, social-media actions, scheduling, and
  self-modifying code are not implemented.

## Intended evolution

Stabilization comes before adding new cognitive subsystems. The next systems
should be introduced as separate, testable components with explicit data
contracts and persistence formats.
