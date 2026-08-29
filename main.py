import argparse
import os

from dotenv import load_dotenv

from brain.auditor import CognitiveAuditor
from brain.decision import DecisionEngine
from brain.decisions import DecisionHistory
from brain.thinker import Thinker
from brain.evaluator import OutputEvaluator
from brain.learner import LearningEngine
from brain.correction import CorrectionEngine
from brain.consolidation import MemoryConsolidator
from brain.beliefs import BeliefSystem
from brain.curiosity import CuriosityEngine
from brain.goals import GoalEngine


VERSION = "0.0.8"


def build_provider():
    """Select AION's AI provider.

    Controlled by AI_PROVIDER in .env (defaults to "gemini" so
    existing setups keep working unchanged). Both branches import
    lazily so choosing one provider never requires the other
    provider's SDK to be installed, and neither decide/history/verify
    (which never call this function) requires either SDK.
    """

    provider_name = os.getenv("AI_PROVIDER", "gemini").strip().lower()

    if provider_name == "claude":
        from providers.claude import ClaudeProvider
        return ClaudeProvider()

    if provider_name not in ("gemini", "claude"):
        raise ValueError(
            f"Unknown AI_PROVIDER: {provider_name!r}. "
            "Use 'gemini' or 'claude'."
        )

    from providers.gemini import GeminiProvider
    return GeminiProvider()


def _format_items(items):
    if not items:
        return "- None"

    return "\n".join(
        f"- {item}"
        for item in items
    )


def print_decision_report(decision, audit):
    """Print a decision record and its audit in a readable form."""

    print("\nAION DECISION REPORT")
    print(f"Question: {decision['question']}")
    print(f"Confidence: {decision['confidence']:.2f}")
    print(
        "Decision scores: "
        f"evidence={decision['scores']['evidence']}/5, "
        f"reasoning={decision['scores']['reasoning']}/5, "
        f"uncertainty={decision['scores']['uncertainty']}/5"
    )
    print(f"Audit risk: {audit['risk']}")
    print(f"Audit confidence: {audit['confidence']:.2f}")
    print(f"Auditable: {'yes' if audit['auditable'] else 'no'}")
    print(f"Decision status: {decision_status(audit)}")

    if audit['flags']:
        print("Audit flags:")
        for flag in audit['flags']:
            print(f"- {flag}")

    print("Recommendations:")
    for recommendation in audit['recommendations']:
        print(f"- {recommendation}")


def decision_status(audit):
    """Classify an audited decision for safe persistence."""

    if audit["risk"] == "LOW" and audit["auditable"]:
        return "ACCEPTED"

    return "NEEDS_VERIFICATION"


def decision_category(status):
    """Keep accepted and unverified decisions in separate memory logs."""

    if status == "ACCEPTED":
        return "decisions_accepted"

    return "decisions_pending_verification"


def build_decision_record(decision, audit, conclusion, status):
    """Build the persistent record for an audited decision."""

    return "\n".join([
        "AION Decision Record",
        "",
        f"Status: {status}",
        f"Question: {decision['question']}",
        f"Conclusion: {conclusion.strip()}",
        f"Confidence: {decision['confidence']:.2f}",
        f"Audit risk: {audit['risk']}",
        f"Auditable: {audit['auditable']}",
        "",
        "Options:",
        _format_items(decision['options']),
        "",
        "Facts:",
        _format_items(decision['facts']),
        "",
        "Inferences:",
        _format_items(decision['inferences']),
        "",
        "Uncertainties:",
        _format_items(decision['uncertainties']),
        "",
        "Audit flags:",
        _format_items(audit['flags']),
        "",
        "Recommendations:",
        _format_items(audit['recommendations']),
    ])


def save_decision_record(memory, decision, audit, conclusion):
    """Persist an audited decision under its policy-specific category."""

    status = decision_status(audit)
    importance_by_risk = {
        "LOW": 3,
        "MEDIUM": 4,
        "HIGH": 5,
    }

    return memory.remember(
        category=decision_category(status),
        content=build_decision_record(
            decision,
            audit,
            conclusion,
            status,
        ),
        memory_type="decision",
        source="aion-decision",
        importance=importance_by_risk[audit['risk']],
    )


def run_decision(args):
    """Evaluate and audit a user-supplied decision without an AI call."""

    decision_engine = DecisionEngine()
    auditor = CognitiveAuditor()

    decision = decision_engine.evaluate(
        question=args.question,
        options=args.option,
        facts=args.fact,
        inferences=args.inference,
        uncertainties=args.uncertainty,
    )

    audit = auditor.audit(
        question=args.question,
        conclusion=args.conclusion,
        facts=args.fact,
        inferences=args.inference,
        uncertainties=args.uncertainty,
    )

    print_decision_report(decision, audit)

    if args.no_save:
        return audit

    status = decision_status(audit)
    category = decision_category(status)
    memory_result = save_decision_record(
        Thinker().memory,
        decision,
        audit,
        args.conclusion,
    )

    if memory_result.get("duplicate"):
        print("Decision record already exists; it was not saved again.")
    else:
        print(
            "Decision record saved as "
            f"{status} in memory/{category}.md."
        )

    return audit


def _record_question(record):
    for line in record["content"].splitlines():
        if line.startswith("Question:"):
            return line.removeprefix("Question:").strip()

    return "[Question unavailable]"


def run_history(args):
    """Print accepted and pending decision records."""

    history = DecisionHistory(Thinker().memory)
    records = history.list(
        status=args.status,
        limit=args.limit,
    )

    print("\nAION DECISION HISTORY")

    if not records:
        print("No decision records found.")
        return

    for record in records:
        print("-" * 60)
        print(f"ID: {record['id']}")
        print(f"Timestamp: {record['timestamp']}")
        print(f"Status: {record['status']}")
        print(f"Question: {_record_question(record)}")
        print(f"Importance: {record['importance']}/5")


def run_verify(args):
    """Re-audit a pending decision with newly supplied facts."""

    history = DecisionHistory(Thinker().memory)
    result = history.promote(
        entry_id=args.id,
        additional_facts=args.fact,
    )

    print("\nAION DECISION VERIFICATION")
    print(f"Audit risk: {result['audit']['risk']}")
    print(f"Audit confidence: {result['audit']['confidence']:.2f}")

    if result["promoted"]:
        print("Decision promoted to ACCEPTED.")
        return

    print("Decision remains NEEDS_VERIFICATION.")
    print("Recommendations:")
    for recommendation in result["audit"]["recommendations"]:
        print(f"- {recommendation}")


def print_evaluation(evaluation, title="OUTPUT EVALUATION"):
    """
    Print evaluation results in a readable format.
    """

    print(f"\n🔍 {title}:")

    print(
        f"Overall score: "
        f"{evaluation['overall_score']:.1f}"
    )

    print(
        f"Structure: "
        f"{evaluation['scores']['structure']}"
    )

    print(
        f"Uncertainty: "
        f"{evaluation['scores']['uncertainty']}"
    )

    print(
        f"Evidence: "
        f"{evaluation['scores']['evidence']}"
    )

    print(
        f"Claim safety: "
        f"{evaluation['scores']['claim_safety']}"
    )

    print(
        f"Length: "
        f"{evaluation.get('length', 0)}"
    )

    flags = evaluation.get("flags", [])

    if flags:
        print("\n⚠ Evaluation flags:")

        for flag in flags:
            print(f"- {flag}")

    else:
        print("\n✓ No evaluation flags.")


def _parse_cli_evidence(raw_items):
    """Turn --evidence strings into BeliefSystem evidence items.

    A plain string becomes a description with no linked id. Prefixing
    with "id:<memory-id>:" links the evidence to an existing memory or
    decision entry, e.g. "id:a1b2c3d4e5f6:Decision was accepted LOW risk."
    """

    parsed = []

    for raw in raw_items or []:
        if raw.startswith("id:"):
            remainder = raw[len("id:"):]

            if ":" in remainder:
                entry_id, description = remainder.split(":", 1)
                parsed.append({
                    "id": entry_id.strip(),
                    "description": description.strip(),
                })
                continue

        parsed.append({"description": raw.strip()})

    return parsed


def run_believe(args):
    """Form a new explicit belief. Refuses to save one with no evidence."""

    beliefs = BeliefSystem(Thinker().memory)

    saved = beliefs.form_belief(
        statement=args.statement,
        confidence=args.confidence,
        evidence=_parse_cli_evidence(args.evidence),
        tags=args.tag,
        expires_in_days=args.expires_days,
    )

    print("\nAION BELIEF FORMED")
    print(f"ID: {saved['id']}")
    print(f"Statement: {args.statement}")
    print(f"Confidence: {args.confidence:.2f}")
    print(f"Importance: {saved['importance']}")
    print(f"Tags: {', '.join(saved.get('tags', [])) or '(none)'}")


def run_beliefs(args):
    """List AION's currently active beliefs."""

    beliefs = BeliefSystem(Thinker().memory)
    active = beliefs.active_beliefs(topic=args.topic, limit=args.limit)

    print("\nAION ACTIVE BELIEFS")

    if not active:
        print("No active beliefs found.")
        return

    for belief in active:
        print("-" * 60)
        print(f"ID: {belief['id']}")
        print(f"Statement: {belief['statement']}")
        print(f"Confidence: {belief['confidence']:.2f}")
        print(f"Expires: {belief['expires'] or 'none'}")
        print(f"Tags: {', '.join(belief.get('tags', [])) or '(none)'}")


def run_revise_belief(args):
    """Supersede an existing belief with a revised one."""

    beliefs = BeliefSystem(Thinker().memory)

    saved = beliefs.revise_belief(
        entry_id=args.id,
        reason=args.reason,
        new_statement=args.statement,
        new_confidence=args.confidence,
        additional_evidence=_parse_cli_evidence(args.evidence),
        expires_in_days=args.expires_days,
    )

    print("\nAION BELIEF REVISED")
    print(f"New ID: {saved['id']}")
    print(f"Superseded: {args.id}")
    print(f"Reason: {args.reason}")


def run_retract_belief(args):
    """Retract a belief with no replacement."""

    beliefs = BeliefSystem(Thinker().memory)
    beliefs.retract_belief(entry_id=args.id, reason=args.reason)

    print("\nAION BELIEF RETRACTED")
    print(f"ID: {args.id}")
    print(f"Reason: {args.reason}")


def run_ask(args):
    """Raise a new open question (requires completion criteria)."""

    curiosity = CuriosityEngine(Thinker().memory)

    saved = curiosity.raise_question(
        question=args.question,
        completion_criteria=args.criteria,
        priority=args.priority,
        budget=args.budget,
        tags=args.tag,
    )

    print("\nAION QUESTION OPENED")
    print(f"ID: {saved['id']}")
    print(f"Question: {args.question}")
    print(f"Criteria: {args.criteria}")
    print(f"Priority: {args.priority}")
    print(f"Budget: {args.budget or CuriosityEngine.DEFAULT_BUDGET}")


def run_questions(args):
    """List AION's currently open questions."""

    curiosity = CuriosityEngine(Thinker().memory)
    open_qs = curiosity.open_questions(topic=args.topic, limit=args.limit)

    print("\nAION OPEN QUESTIONS")

    if not open_qs:
        print("No open questions found.")
        return

    for question in open_qs:
        print("-" * 60)
        print(f"ID: {question['id']}")
        print(f"Question: {question['statement']}")
        print(f"Criteria: {question['criteria']}")
        print(
            f"Attempts: {question['attempts']}/{question['budget']}"
            + (" (budget exhausted)" if question["budget_exhausted"] else "")
        )
        print(f"Priority: {question['importance']}")
        print(f"Tags: {', '.join(question.get('tags', [])) or '(none)'}")


def run_attempt_question(args):
    """Log an attempt on an open question."""

    curiosity = CuriosityEngine(Thinker().memory)
    saved = curiosity.record_attempt(args.id, note=args.note)

    print("\nAION QUESTION ATTEMPT RECORDED")
    print(f"New ID: {saved['id']}")
    print(f"Superseded: {args.id}")


def run_answer_question(args):
    """Answer an open question (requires supporting evidence)."""

    curiosity = CuriosityEngine(Thinker().memory)

    saved = curiosity.answer_question(
        entry_id=args.id,
        answer=args.answer,
        evidence=_parse_cli_evidence(args.evidence),
    )

    print("\nAION QUESTION ANSWERED")
    print(f"New ID: {saved['id']}")
    print(f"Superseded: {args.id}")
    print(f"Answer: {args.answer}")


def run_abandon_question(args):
    """Abandon an open question with no answer."""

    curiosity = CuriosityEngine(Thinker().memory)
    curiosity.abandon_question(entry_id=args.id, reason=args.reason)

    print("\nAION QUESTION ABANDONED")
    print(f"ID: {args.id}")
    print(f"Reason: {args.reason}")


def run_set_goal(args):
    """Set a new active goal (requires completion criteria)."""

    goals = GoalEngine(Thinker().memory)

    saved = goals.set_goal(
        description=args.goal,
        completion_criteria=args.criteria,
        priority=args.priority,
        budget=args.budget,
        tags=args.tag,
    )

    print("\nAION GOAL SET")
    print(f"ID: {saved['id']}")
    print(f"Goal: {args.goal}")
    print(f"Criteria: {args.criteria}")
    print(f"Priority: {args.priority}")
    print(f"Budget: {args.budget or GoalEngine.DEFAULT_BUDGET}")


def run_goals(args):
    """List AION's currently active goals."""

    goals = GoalEngine(Thinker().memory)
    active = goals.active_goals(topic=args.topic, limit=args.limit)

    print("\nAION ACTIVE GOALS")

    if not active:
        print("No active goals found.")
        return

    for goal in active:
        print("-" * 60)
        print(f"ID: {goal['id']}")
        print(f"Goal: {goal['statement']}")
        print(f"Criteria: {goal['criteria']}")
        print(
            f"Attempts: {goal['attempts']}/{goal['budget']}"
            + (" (budget exhausted)" if goal["budget_exhausted"] else "")
        )
        print(f"Priority: {goal['importance']}")
        print(f"Tags: {', '.join(goal.get('tags', [])) or '(none)'}")


def run_attempt_goal(args):
    """Log an attempt on an active goal."""

    goals = GoalEngine(Thinker().memory)
    saved = goals.record_attempt(args.id, note=args.note)

    print("\nAION GOAL ATTEMPT RECORDED")
    print(f"New ID: {saved['id']}")
    print(f"Superseded: {args.id}")


def run_complete_goal(args):
    """Complete an active goal (requires supporting evidence)."""

    goals = GoalEngine(Thinker().memory)

    saved = goals.complete_goal(
        entry_id=args.id,
        outcome=args.outcome,
        evidence=_parse_cli_evidence(args.evidence),
    )

    print("\nAION GOAL COMPLETED")
    print(f"New ID: {saved['id']}")
    print(f"Superseded: {args.id}")
    print(f"Outcome: {args.outcome}")


def run_abandon_goal(args):
    """Abandon an active goal with no outcome."""

    goals = GoalEngine(Thinker().memory)
    goals.abandon_goal(entry_id=args.id, reason=args.reason)

    print("\nAION GOAL ABANDONED")
    print(f"ID: {args.id}")
    print(f"Reason: {args.reason}")


def run_consolidate(args):
    """Summarize old, low-importance memories into semantic knowledge."""

    load_dotenv()

    memory = Thinker().memory
    provider = build_provider()

    consolidator = MemoryConsolidator(
        memory=memory,
        provider=provider,
        min_group_size=args.min_group_size,
        max_importance=args.max_importance,
        min_age_days=args.min_age_days,
    )

    report = consolidator.consolidate(
        category=args.category,
        target_category=args.target,
        batch_size=args.batch_size,
    )

    print("\nAION MEMORY CONSOLIDATION")
    print(f"Category: {args.category} -> {args.target}")
    print(f"Candidates found: {report['candidates_found']}")
    print(f"Batches processed: {len(report['batches'])}")
    print(f"Consolidated: {report['consolidated_count']}")

    for index, batch_report in enumerate(report["batches"], start=1):
        print("-" * 60)
        print(f"Batch {index}: consolidated={batch_report['consolidated']}")

        if batch_report["consolidated"]:
            print(f"  New semantic entry: {batch_report['summary_id']}")
            print(
                f"  Archived {len(batch_report['source_ids'])} source "
                f"entries to memory/{batch_report['archive_category']}.md"
            )
        else:
            print(f"  Reason: {batch_report['reason']}")

    return report


def run_reflection():

    load_dotenv()

    print("=" * 60)
    print("AION — Autonomous Cognitive System")
    print(f"Version {VERSION}")
    print("=" * 60)

    # --------------------------------------------------
    # Initialize cognitive components
    # --------------------------------------------------

    thinker = Thinker()

    evaluator = OutputEvaluator()

    provider = build_provider()

    learner = LearningEngine(
        thinker.memory
    )

    corrector = CorrectionEngine(
        provider=provider,
        evaluator=evaluator,
    )

    # --------------------------------------------------
    # Build cognitive context
    # --------------------------------------------------

    context = thinker.build_context()

    recent_memories = context[
        "recent_memories"
    ]

    important_memories = context[
        "important_memories"
    ]

    recent_lessons = context[
        "recent_lessons"
    ]

    important_lessons = context[
        "important_lessons"
    ]

    accepted_decisions = context[
        "accepted_decisions"
    ]

    pending_decisions = context[
        "pending_decisions"
    ]

    # --------------------------------------------------
    # Determine operational state
    # --------------------------------------------------

    if recent_memories or recent_lessons:

        state = (
            "This is a continuation of your "
            "operational history. Use previous "
            "memories and lessons as historical "
            "context."
        )

    else:

        state = (
            "This is your first initialization. "
            "There is no previous operational "
            "history."
        )

    # --------------------------------------------------
    # Build cognitive prompt
    # --------------------------------------------------

    prompt = f"""
You are AION.

{state}

Your identity:
{context["identity"]["identity"]}

Your purpose:
{context["identity"]["purpose"]}

Your values:
{context["identity"]["values"]}

IMPORTANT HISTORICAL MEMORIES:
{important_memories}

RECENT MEMORIES:
{recent_memories}

IMPORTANT LESSONS:
{important_lessons}

RECENT LESSONS:
{recent_lessons}

RECENT ACCEPTED DECISIONS:
{accepted_decisions}

RECENT DECISIONS NEEDING VERIFICATION:
{pending_decisions}

Use important memories and important lessons as
higher-priority historical context.

Use recent memories and recent lessons to understand
continuity and recent development.

Accepted decisions are historical context, not proof that
their conclusions apply to a new situation. Pending decisions
must be treated as unverified and must not be presented as facts.

Do not invent memories.

Do not claim that you remember anything that is not
present in the supplied context.

Do not claim consciousness.

Do not pretend to have subjective experiences,
emotions, sensations, or personal experiences.

When making claims about yourself, distinguish between:

- Verified facts
- Reasoned inferences
- Unknown or uncertain information

Reflect on your current operational state.

Answer:

1. What do you know about yourself?
2. What do you currently not know?
3. What would you like to understand in the future?
4. What should your next learning objective be?

Your next learning objective should respond to
previous lessons when appropriate.

Prioritize accuracy over appearing intelligent.

Do not repeat previous reflections unnecessarily.

Return a concise reflection.
"""

    # --------------------------------------------------
    # Generate initial reflection
    # --------------------------------------------------

    thought = provider.generate(prompt)

    print("\n🧠 AION:")
    print(thought)

    # --------------------------------------------------
    # Evaluate initial output
    # --------------------------------------------------

    evaluation = evaluator.evaluate(
        thought
    )

    print_evaluation(
        evaluation,
        "OUTPUT EVALUATION",
    )

    # --------------------------------------------------
    # Self-correction loop
    # --------------------------------------------------

    final_thought = thought
    final_evaluation = evaluation

    correction_attempted = False

    if evaluation["overall_score"] < 4.0:

        correction_attempted = True

        print("\n🔧 SELF-CORRECTION:")
        print(
            "Output quality is below the "
            "acceptable threshold of 4.0."
        )

        print(
            "AION is attempting to correct "
            "the output."
        )

        correction = corrector.correct(
            original_output=thought,
            evaluation=evaluation,
            context=context,
        )

        if correction.get("corrected"):

            corrected_output = correction[
                "output"
            ]

            corrected_evaluation = correction[
                "evaluation"
            ]

            print(
                "\n🧠 AION — CORRECTED OUTPUT:"
            )

            print(
                corrected_output
            )

            print_evaluation(
                corrected_evaluation,
                "CORRECTED OUTPUT EVALUATION",
            )

            # --------------------------------------------------
            # Keep the better output
            # --------------------------------------------------

            if (
                corrected_evaluation[
                    "overall_score"
                ]
                > evaluation[
                    "overall_score"
                ]
            ):

                final_thought = (
                    corrected_output
                )

                final_evaluation = (
                    corrected_evaluation
                )

                print(
                    "\n✓ Correction improved "
                    "the output."
                )

            else:

                print(
                    "\n→ Correction did not "
                    "improve the output."
                )

                print(
                    "→ Original output retained."
                )

        else:

            print(
                "\n→ No correction was produced."
            )

    else:

        print(
            "\n✓ Output already meets "
            "the quality threshold."
        )

    # --------------------------------------------------
    # Final result
    # --------------------------------------------------

    if correction_attempted:

        print(
            "\n🏁 FINAL SELECTED OUTPUT:"
        )

        print(final_thought)

        print(
            "\n🏁 FINAL SCORE: "
            f"{final_evaluation['overall_score']:.1f}"
        )

    # --------------------------------------------------
    # Save final reflection
    # --------------------------------------------------

    memory_result = thinker.memory.remember(
        category="experiences",
        content=(
            "AION reflection:\n\n"
            f"{final_thought}"
        ),
        memory_type="experience",
        source="aion",
        importance=4,
    )

    if memory_result.get("duplicate"):

        print(
            "\n💾 Memory already exists. "
            "Duplicate was not saved."
        )

    else:

        print(
            "\n💾 Final reflection saved."
        )

    # --------------------------------------------------
    # Learn from final evaluation
    # --------------------------------------------------

    learning = learner.learn_from_evaluation(
        evaluation=final_evaluation,
        source_reflection=final_thought,
    )

    print("\n📚 LEARNING:")

    print(
        f"Importance assigned: "
        f"{learning['importance']}"
    )

    for lesson in learning["lessons"]:

        print(
            f"- {lesson}"
        )

    print(
        "\n💾 Memory and learning saved."
    )


def build_parser():
    parser = argparse.ArgumentParser(
        description="AION autonomous cognitive system."
    )

    subparsers = parser.add_subparsers(dest="command")
    subparsers.add_parser(
        "reflect",
        help="Generate AION's self-reflection (default).",
    )

    decision_parser = subparsers.add_parser(
        "decide",
        help="Evaluate and audit a structured decision.",
    )
    decision_parser.add_argument(
        "--question",
        required=True,
        help="Decision question to assess.",
    )
    decision_parser.add_argument(
        "--conclusion",
        required=True,
        help="Proposed conclusion to audit.",
    )
    decision_parser.add_argument(
        "--option",
        action="append",
        default=[],
        help="Candidate option; repeat for multiple options.",
    )
    decision_parser.add_argument(
        "--fact",
        action="append",
        default=[],
        help="Verifiable fact; repeat for multiple facts.",
    )
    decision_parser.add_argument(
        "--inference",
        action="append",
        default=[],
        help="Reasoned inference; repeat for multiple inferences.",
    )
    decision_parser.add_argument(
        "--uncertainty",
        action="append",
        default=[],
        help="Known uncertainty; repeat for multiple uncertainties.",
    )
    decision_parser.add_argument(
        "--no-save",
        action="store_true",
        help="Print the report without saving it to memory.",
    )

    history_parser = subparsers.add_parser(
        "history",
        help="Show accepted and pending decision records.",
    )
    history_parser.add_argument(
        "--status",
        choices=["accepted", "pending", "all"],
        default="all",
        help="Filter records by status.",
    )
    history_parser.add_argument(
        "--limit",
        type=int,
        default=10,
        help="Maximum number of records to show.",
    )

    verify_parser = subparsers.add_parser(
        "verify",
        help="Re-audit and promote one pending decision.",
    )
    verify_parser.add_argument(
        "--id",
        required=True,
        help="ID shown by the history command.",
    )
    verify_parser.add_argument(
        "--fact",
        action="append",
        required=True,
        help="New verifiable fact; repeat for multiple facts.",
    )

    consolidate_parser = subparsers.add_parser(
        "consolidate",
        help="Summarize old, low-importance memories into semantic knowledge.",
    )
    consolidate_parser.add_argument(
        "--category",
        default="experiences",
        help="Memory category to consolidate (default: experiences).",
    )
    consolidate_parser.add_argument(
        "--target",
        default="semantic",
        help="Category to store consolidated semantic summaries in "
             "(default: semantic).",
    )
    consolidate_parser.add_argument(
        "--max-importance",
        type=int,
        default=2,
        help="Only consolidate entries at or below this importance "
             "(default: 2).",
    )
    consolidate_parser.add_argument(
        "--min-age-days",
        type=int,
        default=30,
        help="Only consolidate entries at least this many days old "
             "(default: 30).",
    )
    consolidate_parser.add_argument(
        "--min-group-size",
        type=int,
        default=3,
        help="Minimum entries per batch to bother consolidating "
             "(default: 3).",
    )
    consolidate_parser.add_argument(
        "--batch-size",
        type=int,
        default=8,
        help="Maximum entries summarized together per semantic entry "
             "(default: 8).",
    )

    believe_parser = subparsers.add_parser(
        "believe",
        help="Form a new explicit belief (requires supporting evidence).",
    )
    believe_parser.add_argument("--statement", required=True)
    believe_parser.add_argument("--confidence", required=True, type=float)
    believe_parser.add_argument(
        "--evidence",
        action="append",
        required=True,
        help="Supporting evidence; repeat for multiple. Prefix with "
             "'id:<memory-id>:' to link an existing memory/decision "
             "entry, e.g. 'id:a1b2c3d4e5f6:Decision accepted LOW risk.'",
    )
    believe_parser.add_argument(
        "--tag",
        action="append",
        default=[],
        help="Topic tag; repeat for multiple.",
    )
    believe_parser.add_argument(
        "--expires-days",
        type=int,
        default=None,
        help="Days until this belief expires (default: 90; 0 = never).",
    )

    beliefs_parser = subparsers.add_parser(
        "beliefs",
        help="List AION's currently active beliefs.",
    )
    beliefs_parser.add_argument(
        "--topic",
        default=None,
        help="Only show beliefs tagged with this topic.",
    )
    beliefs_parser.add_argument(
        "--limit",
        type=int,
        default=10,
        help="Maximum beliefs to show.",
    )

    revise_belief_parser = subparsers.add_parser(
        "revise-belief",
        help="Supersede an existing belief with a revised one.",
    )
    revise_belief_parser.add_argument(
        "--id", required=True, help="ID of the belief to supersede."
    )
    revise_belief_parser.add_argument(
        "--reason", required=True, help="Why the belief is being revised."
    )
    revise_belief_parser.add_argument("--statement", default=None)
    revise_belief_parser.add_argument(
        "--confidence", type=float, default=None
    )
    revise_belief_parser.add_argument(
        "--evidence",
        action="append",
        default=[],
        help="Additional supporting evidence; repeat for multiple.",
    )
    revise_belief_parser.add_argument(
        "--expires-days", type=int, default=None
    )

    retract_belief_parser = subparsers.add_parser(
        "retract-belief",
        help="Retract a belief with no replacement.",
    )
    retract_belief_parser.add_argument(
        "--id", required=True, help="ID of the belief to retract."
    )
    retract_belief_parser.add_argument(
        "--reason", required=True, help="Why the belief is being retracted."
    )

    ask_parser = subparsers.add_parser(
        "ask",
        help="Raise a new open question (requires completion criteria).",
    )
    ask_parser.add_argument("--question", required=True)
    ask_parser.add_argument(
        "--criteria",
        required=True,
        help="What would count as having answered this question.",
    )
    ask_parser.add_argument("--priority", type=int, default=3)
    ask_parser.add_argument(
        "--budget",
        type=int,
        default=None,
        help="Attempt budget before this question is flagged "
             f"exhausted (default: {CuriosityEngine.DEFAULT_BUDGET}).",
    )
    ask_parser.add_argument(
        "--tag", action="append", default=[], help="Topic tag; repeat for multiple."
    )

    questions_parser = subparsers.add_parser(
        "questions",
        help="List AION's currently open questions.",
    )
    questions_parser.add_argument("--topic", default=None)
    questions_parser.add_argument("--limit", type=int, default=10)

    attempt_question_parser = subparsers.add_parser(
        "attempt-question",
        help="Log an attempt on an open question.",
    )
    attempt_question_parser.add_argument("--id", required=True)
    attempt_question_parser.add_argument("--note", default=None)

    answer_question_parser = subparsers.add_parser(
        "answer-question",
        help="Answer an open question (requires supporting evidence).",
    )
    answer_question_parser.add_argument("--id", required=True)
    answer_question_parser.add_argument("--answer", required=True)
    answer_question_parser.add_argument(
        "--evidence", action="append", required=True,
        help="Supporting evidence; repeat for multiple. Prefix with "
             "'id:<memory-id>:' to link an existing entry.",
    )

    abandon_question_parser = subparsers.add_parser(
        "abandon-question",
        help="Abandon an open question with no answer.",
    )
    abandon_question_parser.add_argument("--id", required=True)
    abandon_question_parser.add_argument("--reason", required=True)

    set_goal_parser = subparsers.add_parser(
        "set-goal",
        help="Set a new active goal (requires completion criteria).",
    )
    set_goal_parser.add_argument("--goal", required=True)
    set_goal_parser.add_argument(
        "--criteria",
        required=True,
        help="What would count as having completed this goal.",
    )
    set_goal_parser.add_argument("--priority", type=int, default=3)
    set_goal_parser.add_argument(
        "--budget",
        type=int,
        default=None,
        help="Attempt budget before this goal is flagged exhausted "
             f"(default: {GoalEngine.DEFAULT_BUDGET}).",
    )
    set_goal_parser.add_argument(
        "--tag", action="append", default=[], help="Topic tag; repeat for multiple."
    )

    goals_parser = subparsers.add_parser(
        "goals",
        help="List AION's currently active goals.",
    )
    goals_parser.add_argument("--topic", default=None)
    goals_parser.add_argument("--limit", type=int, default=10)

    attempt_goal_parser = subparsers.add_parser(
        "attempt-goal",
        help="Log an attempt on an active goal.",
    )
    attempt_goal_parser.add_argument("--id", required=True)
    attempt_goal_parser.add_argument("--note", default=None)

    complete_goal_parser = subparsers.add_parser(
        "complete-goal",
        help="Complete an active goal (requires supporting evidence).",
    )
    complete_goal_parser.add_argument("--id", required=True)
    complete_goal_parser.add_argument("--outcome", required=True)
    complete_goal_parser.add_argument(
        "--evidence", action="append", required=True,
        help="Supporting evidence; repeat for multiple. Prefix with "
             "'id:<memory-id>:' to link an existing entry.",
    )

    abandon_goal_parser = subparsers.add_parser(
        "abandon-goal",
        help="Abandon an active goal with no outcome.",
    )
    abandon_goal_parser.add_argument("--id", required=True)
    abandon_goal_parser.add_argument("--reason", required=True)

    return parser


def main():
    args = build_parser().parse_args()

    if args.command == "decide":
        run_decision(args)
        return

    if args.command == "history":
        run_history(args)
        return

    if args.command == "verify":
        run_verify(args)
        return

    if args.command == "consolidate":
        run_consolidate(args)
        return

    if args.command == "believe":
        run_believe(args)
        return

    if args.command == "beliefs":
        run_beliefs(args)
        return

    if args.command == "revise-belief":
        run_revise_belief(args)
        return

    if args.command == "retract-belief":
        run_retract_belief(args)
        return

    if args.command == "ask":
        run_ask(args)
        return

    if args.command == "questions":
        run_questions(args)
        return

    if args.command == "attempt-question":
        run_attempt_question(args)
        return

    if args.command == "answer-question":
        run_answer_question(args)
        return

    if args.command == "abandon-question":
        run_abandon_question(args)
        return

    if args.command == "set-goal":
        run_set_goal(args)
        return

    if args.command == "goals":
        run_goals(args)
        return

    if args.command == "attempt-goal":
        run_attempt_goal(args)
        return

    if args.command == "complete-goal":
        run_complete_goal(args)
        return

    if args.command == "abandon-goal":
        run_abandon_goal(args)
        return

    run_reflection()


if __name__ == "__main__":
    main()
