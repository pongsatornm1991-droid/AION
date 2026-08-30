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
from brain.experiments import ExperimentEngine
from brain.metacognition import MetacognitionEngine
from brain.tools import ToolLifecycle, ToolRegistry, ActionLevel, build_builtin_tools
from brain.social import SocialContentGenerator, SocialAutoCycle
from brain.comment_reply import CommentReplyGenerator, CommentAutoReplyCycle
from brain.profile_change import ProfileChangeGenerator, ProfileChangeCycle


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


def run_predict(args):
    """Record a prediction before anything is observed."""

    experiments = ExperimentEngine(Thinker().memory)

    saved = experiments.predict(
        prediction=args.prediction,
        confidence=args.confidence,
        tags=args.tag,
    )

    print("\nAION EXPERIMENT PREDICTED")
    print(f"ID: {saved['id']}")
    print(f"Prediction: {args.prediction}")
    print(f"Confidence: {args.confidence:.2f}")


def run_experiments(args):
    """List AION's pending experiments (predicted) or those awaiting a
    conclusion (observed but no lesson yet)."""

    experiments = ExperimentEngine(Thinker().memory)

    if args.status == "awaiting":
        items = experiments.awaiting_conclusion(limit=args.limit)
        heading = "AION EXPERIMENTS AWAITING CONCLUSION"
    else:
        items = experiments.pending_experiments(limit=args.limit)
        heading = "AION PENDING EXPERIMENTS"

    print(f"\n{heading}")

    if not items:
        print("None found.")
        return

    for item in items:
        print("-" * 60)
        print(f"ID: {item['id']}")
        print(f"Prediction: {item['prediction']}")
        print(f"Confidence: {item['confidence']:.2f}")
        if args.status == "awaiting":
            print(f"Observed: {item['observed']}")
            print(f"Matched: {item['matched']}")
        print(f"Tags: {', '.join(item.get('tags', [])) or '(none)'}")


def run_observe(args):
    """Record what was actually observed for a prediction (requires
    supporting evidence)."""

    experiments = ExperimentEngine(Thinker().memory)

    saved = experiments.observe(
        entry_id=args.id,
        observed_result=args.result,
        matched=(args.matched == "yes"),
        evidence=_parse_cli_evidence(args.evidence),
        error_description=args.error,
    )

    print("\nAION EXPERIMENT OBSERVED")
    print(f"New ID: {saved['id']}")
    print(f"Superseded: {args.id}")
    print(f"Matched: {args.matched}")


def run_conclude(args):
    """Derive a lesson from an observed experiment, optionally revising
    an existing belief with the result."""

    memory = Thinker().memory
    experiments = ExperimentEngine(memory)

    belief_system = BeliefSystem(memory) if args.belief_id else None

    result = experiments.conclude(
        entry_id=args.id,
        lesson=args.lesson,
        belief_system=belief_system,
        belief_id=args.belief_id,
        new_belief_confidence=args.belief_confidence,
    )

    print("\nAION EXPERIMENT CONCLUDED")
    print(f"New ID: {result['experiment']['id']}")
    print(f"Superseded: {args.id}")
    print(f"Lesson: {args.lesson}")

    if result["revised_belief"] is not None:
        print(f"Revised belief ID: {result['revised_belief']['id']}")


def run_abandon_experiment(args):
    """Abandon an experiment before it is concluded."""

    experiments = ExperimentEngine(Thinker().memory)
    experiments.abandon(entry_id=args.id, reason=args.reason)

    print("\nAION EXPERIMENT ABANDONED")
    print(f"ID: {args.id}")
    print(f"Reason: {args.reason}")


def _print_calibration(report):
    print(f"Observed experiments analyzed: {report['sample_size']}")

    if not report["buckets"]:
        print("No observed experiments yet -- nothing to calibrate.")
        return

    for bucket in report["buckets"]:
        low, high = bucket["range"]
        print("-" * 60)
        print(f"Confidence range: {low:.2f}-{high:.2f}")
        print(f"Observations: {bucket['count']}")
        print(f"Average stated confidence: {bucket['average_confidence']:.2f}")
        print(f"Actual match rate: {bucket['match_rate']:.2f}")

        if bucket["sufficient_data"]:
            print(f"Assessment: {bucket['assessment']} (gap: {bucket['calibration_gap']:+.2f})")
        else:
            print("Assessment: insufficient data (fewer than min-samples observations)")

    if report["overall_calibration_error"] is not None:
        print("-" * 60)
        print(f"Overall calibration error: {report['overall_calibration_error']:.3f}")


def _print_recurring_errors(report):
    print(f"Total lessons logged: {report['total_lessons']}")

    if not report["sources"]:
        print("No lessons logged yet.")
        return

    for item in report["sources"]:
        flag = " (recurring)" if item in report["recurring"] else ""
        print(f"- {item['source']}: {item['count']}{flag}")

    if not report["recurring"]:
        print("\nNo source has recurred often enough to flag yet.")


def _print_memory_quality(report):
    print(f"Total entries across all categories: {report['total_entries']}")
    print(f"Overall average quality: {report['overall_average_quality']:.2f}/5")

    for category, stats in sorted(report["categories"].items()):
        flag = " (flagged low quality)" if category in report["flagged_low_quality"] else ""
        print(
            f"- {category}: {stats['total']} entries, "
            f"avg {stats['average_quality']:.2f}/5{flag}"
        )


def run_metacognition(args):
    """Report calibration, recurring lessons, and memory quality --
    all computed directly from what's on disk, no AI provider call."""

    memory = Thinker().memory
    meta = MetacognitionEngine(memory)

    print("\nAION METACOGNITION REPORT")

    if args.report in ("calibration", "full"):
        print("\n--- Calibration ---")
        _print_calibration(
            meta.calibration_report(bucket_size=args.bucket_size)
        )

    if args.report in ("recurring-errors", "full"):
        print("\n--- Recurring errors ---")
        _print_recurring_errors(
            meta.recurring_error_report(
                min_occurrences=args.min_occurrences, limit=args.limit
            )
        )

    if args.report in ("memory-quality", "full"):
        print("\n--- Memory quality ---")
        _print_memory_quality(meta.memory_quality_overview())

    if args.report == "full":
        print("\n--- Tool reliability ---")
        print(
            "Not applicable: no external tool-execution framework exists "
            "yet (see roadmap: Controlled tools and lifecycle)."
        )


def _build_tool_lifecycle():
    """The lifecycle manager used by the CLI: only genuinely read-only
    tools are wired in right now (see brain.tools.build_builtin_tools)
    -- LOW_RISK/HIGH_RISK tool registration is available programmatically
    for whoever plugs in real external tools in the next phase."""

    memory = Thinker().memory
    return ToolLifecycle(memory, registry=build_builtin_tools(memory))


def _build_social_tool_lifecycle():
    """The lifecycle manager used by every social/identity CLI command
    (posts, comment replies, AND profile-bio changes) -- one shared
    lifecycle instance (same underlying memory/kill switch) with three
    separately-budgeted action levels:

    - post_to_facebook: ActionLevel.HIGH_RISK. Unprompted,
      AION-initiated public content, budgeted to guard against
      flooding the Page if something goes wrong upstream.
    - reply_to_facebook_comment: ActionLevel.COMMENT_REPLY (split out
      from HIGH_RISK 2026-08-30, at the user's explicit request --
      see that level's own docstring in brain/tools.py for why an
      unbounded daily budget is safe here specifically: replies are
      bounded by real incoming comments and by check-comments.yml's
      own 5-minute cron cadence, unlike an original post).
    - update_page_bio: ActionLevel.IDENTITY_CHANGE, its own small
      budget that neither of the above ever touches.

    All three share the exact same never-self-approved-by-AION
    guarantee (see brain/tools.py's _NEVER_SELF_APPROVE) regardless of
    budget -- loosening a budget never loosens who may approve.

    Starts from the same read-only builtin tools as
    _build_tool_lifecycle(), then additionally registers
    "post_to_facebook", "reply_to_facebook_comment", and
    "update_page_bio" -- the real external-facing, side-effecting
    actions in this codebase. Kept here in main.py rather than inside
    brain/tools.py or brain/social.py so the top-level `tools` package
    (tools/facebook.py) and the `brain.tools` module never need to
    import one another.
    """

    from tools.facebook import (
        post_to_facebook_page,
        reply_to_facebook_comment,
        update_page_bio,
    )

    memory = Thinker().memory
    registry = build_builtin_tools(memory)

    registry.register(
        "post_to_facebook",
        lambda message: post_to_facebook_page(message),
        ActionLevel.HIGH_RISK,
        "Publish one text post to AION's configured Facebook Page.",
    )

    registry.register(
        "reply_to_facebook_comment",
        lambda comment_id, message: reply_to_facebook_comment(
            comment_id, message,
        ),
        ActionLevel.COMMENT_REPLY,
        "Reply to one existing comment on AION's configured Facebook Page.",
    )

    registry.register(
        "update_page_bio",
        lambda new_bio: update_page_bio(new_bio),
        ActionLevel.IDENTITY_CHANGE,
        "Change AION's configured Facebook Page's About/bio text -- "
        "requires a real person's approval via Telegram; can never be "
        "self-approved by AION.",
    )

    return ToolLifecycle(memory, registry=registry)


def _format_telegram_report(report):
    """Turn a SocialContentGenerator/SocialAutoCycle report dict into
    a short, human-readable Thai summary -- so the user can see what
    AION drafted or decided without needing to run a CLI command."""

    lines = ["AION (Facebook):"]

    seed = report.get("seed")
    if seed:
        lines.append(f"ที่มา ({seed['kind']}): {seed['text']}")

    draft = report.get("draft")
    if draft:
        lines.append(f"ร่าง: {draft}")

    stage = report.get("stage")
    reason_kind = report.get("reason_kind")

    # Both run_once() (which always sets "stage") and a bare
    # draft_post() report (no "stage" key at all -- e.g. the
    # draft-post CLI command) can carry each of these outcomes, so
    # each branch below matches on the stage name OR the reason_kind
    # of a stage-less report.
    if stage == "safety-gate" or (stage is None and reason_kind == "claim_safety"):
        lines.append(f"ถูกบล็อกที่ตัวกรองความปลอดภัย: {report.get('reason')}")
    elif stage == "style-gate" or (stage is None and reason_kind == "robotic_style"):
        lines.append(
            f"ถูกบล็อกที่ตัวกรองน้ำเสียง (ฟังดูเป็นระบบ/รายงานเกินไป): "
            f"{report.get('reason')}"
        )
        robotic_terms = report.get("robotic_terms") or []
        if robotic_terms:
            lines.append(f"คำที่ตรวจพบ: {', '.join(robotic_terms)}")
        lines.append(
            "บันทึกเป็นบทเรียนแล้ว ร่างครั้งถัดไปจะพยายามหลีกเลี่ยงคำแบบนี้"
        )
    elif stage == "no-seed" or (stage is None and reason_kind == "no_seed"):
        lines.append("ยังไม่มีเนื้อหาในความจำให้ร่างโพสต์ตอนนี้")
    elif stage == "draft-failed":
        lines.append(f"ร่างโพสต์ไม่สำเร็จ (ปัญหาที่ตัว AI provider): {report.get('error')}")
    elif stage == "lifecycle":
        lines.append(f"ผิดพลาดในระบบ lifecycle: {report.get('error')}")
    elif stage is not None:
        # A run-social-cycle report: either it actually posted, or the
        # action itself failed/was recorded some other way.
        if report.get("posted"):
            lines.append("สถานะ: โพสต์สำเร็จแล้ว")
        else:
            action = report.get("action") or {}
            lines.append(f"สถานะ: {action.get('status', 'unknown')}")
            if action.get("error"):
                lines.append(f"ข้อผิดพลาด: {action['error']}")
    else:
        # A draft-post report that passed every gate -- still just a
        # preview, nothing was ever sent to Facebook.
        lines.append("สถานะ: ร่างไว้เท่านั้น ยังไม่ได้ส่งโพสต์ (draft-post)")

    return "\n".join(lines)


def _format_comment_telegram_report(report):
    """Turn a CommentAutoReplyCycle report dict into a short,
    human-readable Thai summary -- the comment-reply counterpart of
    _format_telegram_report(). A separate function rather than one
    shared branch tree: the report shape genuinely differs (a
    "comment" key instead of "seed", and stage values specific to
    the comment-reply cycle), and keeping them separate means neither
    has to guess which shape it was handed."""

    lines = ["AION (คอมเมนต์ Facebook):"]

    comment = report.get("comment")
    if comment:
        lines.append(
            f"คอมเมนต์จาก {comment.get('from_name') or 'ไม่ทราบชื่อ'}: "
            f"{comment.get('message', '')}"
        )

    draft = report.get("draft")
    if draft:
        lines.append(f"ร่างคำตอบ: {draft}")

    stage = report.get("stage")

    if stage == "no-comments":
        lines.append("ยังไม่มีคอมเมนต์ใหม่ให้ตอบตอนนี้")
    elif stage == "fetch-failed":
        lines.append(f"ดึงคอมเมนต์จาก Facebook ไม่สำเร็จ: {report.get('error')}")
    elif stage == "draft-failed":
        lines.append(f"ร่างคำตอบไม่สำเร็จ (ปัญหาที่ตัว AI provider): {report.get('error')}")
    elif stage == "blocked-safety":
        lines.append(f"ถูกบล็อกที่ตัวกรองความปลอดภัย: {report.get('reason')}")
    elif stage == "blocked-style":
        lines.append(
            f"ถูกบล็อกที่ตัวกรองน้ำเสียง (ฟังดูเป็นระบบ/รายงานเกินไป): "
            f"{report.get('reason')}"
        )
        robotic_terms = report.get("robotic_terms") or []
        if robotic_terms:
            lines.append(f"คำที่ตรวจพบ: {', '.join(robotic_terms)}")
        lines.append(
            "บันทึกเป็นบทเรียนแล้ว คำตอบครั้งถัดไปจะพยายามหลีกเลี่ยงคำแบบนี้"
        )
    elif stage == "skipped-empty":
        lines.append("ข้ามคอมเมนต์นี้ (ไม่มีข้อความให้ตอบ)")
    elif stage == "lifecycle":
        lines.append(f"ผิดพลาดในระบบ lifecycle: {report.get('error')}")
    elif stage == "executed":
        lines.append("สถานะ: ตอบคอมเมนต์สำเร็จแล้ว")
    elif stage == "failed":
        action = report.get("action") or {}
        lines.append(f"สถานะ: {action.get('status', 'unknown')}")
        if action.get("error"):
            lines.append(f"ข้อผิดพลาด: {action['error']}")

    return "\n".join(lines)


def _format_profile_proposal_telegram_report(report):
    """Turn a ProfileChangeCycle.propose_once() report dict into a
    short Thai summary -- the message body sent alongside the
    Approve/Reject inline buttons (see run_propose_profile_change()),
    and also what is printed for stages that never reach a proposal
    (already-pending / blocked / failed)."""

    lines = ["AION (เปลี่ยน bio หน้า Facebook):"]

    current_bio = report.get("current_bio")
    if current_bio:
        lines.append(f"bio เดิม: {current_bio}")

    draft = report.get("draft")
    if draft:
        lines.append(f"bio ใหม่ที่ร่างไว้: {draft}")

    stage = report.get("stage")

    if stage == "already-pending":
        lines.append("มีคำขอเปลี่ยน bio ที่ยังรอการอนุมัติอยู่แล้ว -- ยังไม่ร่างใหม่ซ้ำ")
    elif stage == "fetch-failed":
        lines.append(f"ดึง bio ปัจจุบันจาก Facebook ไม่สำเร็จ: {report.get('error')}")
    elif stage == "draft-failed":
        lines.append(f"ร่าง bio ไม่สำเร็จ (ปัญหาที่ตัว AI provider): {report.get('error')}")
    elif stage == "blocked-safety":
        lines.append(f"ถูกบล็อกที่ตัวกรองความปลอดภัย: {report.get('reason')}")
    elif stage == "blocked-style":
        lines.append(
            f"ถูกบล็อกที่ตัวกรองน้ำเสียง (ฟังดูเป็นระบบ/รายงานเกินไป): "
            f"{report.get('reason')}"
        )
        robotic_terms = report.get("robotic_terms") or []
        if robotic_terms:
            lines.append(f"คำที่ตรวจพบ: {', '.join(robotic_terms)}")
    elif stage == "lifecycle":
        lines.append(f"ผิดพลาดในระบบ lifecycle: {report.get('error')}")
    elif stage == "awaiting-approval":
        lines.append("รอการอนุมัติจากคุณผ่านปุ่มด้านล่างนี้ก่อนถึงจะเปลี่ยน bio จริง")

    return "\n".join(lines)


def _format_profile_approval_telegram_report(result):
    """Turn one ProfileChangeCycle.check_approvals_once() per-item
    result dict into a short Thai summary."""

    lines = ["AION (ผลการอนุมัติเปลี่ยน bio):"]

    decision = result.get("decision")
    outcome = result.get("outcome")
    approver = result.get("approver")

    if decision == "approved":
        if outcome == "executed":
            lines.append(f"{approver} อนุมัติแล้ว -- เปลี่ยน bio สำเร็จ ✅")
        elif outcome == "failed":
            action = result.get("action") or {}
            lines.append(f"{approver} อนุมัติแล้ว แต่เปลี่ยน bio ไม่สำเร็จ: {action.get('error')}")
        else:
            lines.append(f"{approver} อนุมัติแล้ว แต่เกิดข้อผิดพลาด: {result.get('error')}")
    elif decision == "rejected":
        if outcome == "rejected":
            lines.append(f"{approver} ปฏิเสธคำขอเปลี่ยน bio นี้แล้ว ❌")
        else:
            lines.append(f"{approver} พยายามปฏิเสธ แต่เกิดข้อผิดพลาด: {result.get('error')}")

    return "\n".join(lines)



def _notify_report(report, formatter=None):
    """Best-effort Telegram notification for one draft/cycle report.

    `formatter` defaults to _format_telegram_report (the social-post
    shape); pass _format_comment_telegram_report for a
    CommentAutoReplyCycle report, whose shape differs.

    Returns True if a notification was sent, False if it was attempted
    and failed, or None if Telegram is simply not configured yet
    (TELEGRAM_BOT_TOKEN/TELEGRAM_CHAT_ID missing from .env) --
    notification is a supplementary channel, never a requirement for
    drafting or posting to work, so a missing or failing notifier must
    never break either command.
    """

    if not os.getenv("TELEGRAM_BOT_TOKEN") or not os.getenv("TELEGRAM_CHAT_ID"):
        return None

    formatter = formatter or _format_telegram_report

    from tools.telegram import send_telegram_message

    try:
        send_telegram_message(formatter(report))
        return True
    except Exception as exc:
        print(f"(Telegram notification failed: {exc})")
        return False


def _parse_cli_params(raw_items):
    """Turn --param key=value strings into a dict of string values."""

    params = {}

    for raw in raw_items or []:
        if "=" not in raw:
            raise ValueError(
                f"--param must be in key=value form, got: {raw!r}"
            )

        key, value = raw.split("=", 1)
        params[key.strip()] = value.strip()

    return params


def run_tools(args):
    """List every tool AION currently has registered, and at what
    action level."""

    lc = _build_tool_lifecycle()

    print("\nAION REGISTERED TOOLS")

    for tool in lc.registry.list_tools():
        print("-" * 60)
        print(f"Name: {tool['name']}")
        print(f"Level: {tool['level']}")
        print(f"Description: {tool['description']}")


def run_propose_action(args):
    """Propose running a registered tool. READ_ONLY actions can be
    executed straight from here; LOW_RISK/HIGH_RISK need approve-action
    first."""

    lc = _build_tool_lifecycle()

    saved = lc.propose(
        tool_name=args.tool,
        params=_parse_cli_params(args.param),
        scheduled_for=args.scheduled_for,
    )

    print("\nAION ACTION PROPOSED")
    print(f"ID: {saved['id']}")
    print(f"Tool: {saved['tool']}")
    print(f"Level: {saved['level']}")
    print(f"Scheduled for: {saved['scheduled_for'] or 'immediately'}")


def run_actions(args):
    """List AION's proposed/approved/executed/failed/etc. actions."""

    lc = _build_tool_lifecycle()
    items = lc.actions(status=args.status, limit=args.limit)

    print("\nAION ACTIONS")

    if not items:
        print("No actions found.")
        return

    for item in items:
        print("-" * 60)
        print(f"ID: {item['id']}")
        print(f"Tool: {item['tool']}")
        print(f"Level: {item['level']}")
        print(f"Status: {item['status']}")
        print(f"Params: {item['params']}")
        if item["result"] is not None:
            print(f"Result: {item['result']}")
        if item["error"] is not None:
            print(f"Error: {item['error']}")


def run_approve_action(args):
    """Approve a proposed action. HIGH_RISK actions can never be
    approved by AION itself -- the approver must be a person."""

    lc = _build_tool_lifecycle()
    saved = lc.approve(args.id, approver=args.approver)

    print("\nAION ACTION APPROVED")
    print(f"New ID: {saved['id']}")
    print(f"Superseded: {args.id}")
    print(f"Approver: {args.approver}")


def run_reject_action(args):
    """Reject a proposed action before it ever runs."""

    lc = _build_tool_lifecycle()
    saved = lc.reject(args.id, reason=args.reason, rejector=args.rejector)

    print("\nAION ACTION REJECTED")
    print(f"New ID: {saved['id']}")
    print(f"Superseded: {args.id}")
    print(f"Reason: {args.reason}")


def run_execute_action(args):
    """Execute an approved (or, for READ_ONLY, proposed) action. Checks
    the kill switch, approval, schedule, and budget before running
    anything."""

    lc = _build_tool_lifecycle()
    saved = lc.execute(args.id)

    print("\nAION ACTION EXECUTED" if saved["status"] == "executed" else "\nAION ACTION FAILED")
    print(f"New ID: {saved['id']}")
    print(f"Superseded: {args.id}")
    print(f"Status: {saved['status']}")
    if saved["result"] is not None:
        print(f"Result: {saved['result']}")
    if saved["error"] is not None:
        print(f"Error: {saved['error']}")


def run_recover_action(args):
    """Document how a failed action was handled (never a silent
    automatic retry)."""

    lc = _build_tool_lifecycle()

    saved = lc.recover(
        args.id,
        resolution=args.resolution,
        evidence=_parse_cli_evidence(args.evidence),
    )

    print("\nAION ACTION RECOVERED")
    print(f"New ID: {saved['id']}")
    print(f"Superseded: {args.id}")
    print(f"Resolution: {args.resolution}")


def run_abandon_action(args):
    """Abandon an action before it executes (or after it failed)."""

    lc = _build_tool_lifecycle()
    lc.abandon(args.id, reason=args.reason)

    print("\nAION ACTION ABANDONED")
    print(f"ID: {args.id}")
    print(f"Reason: {args.reason}")


def run_engage_kill_switch(args):
    """Halt every action AION can execute, effective immediately."""

    lc = _build_tool_lifecycle()
    lc.engage_kill_switch(reason=args.reason)

    print("\nAION KILL SWITCH ENGAGED")
    print(f"Reason: {args.reason}")
    print("No action -- of any level -- will execute until disengaged.")


def run_disengage_kill_switch(args):
    """Resume normal operation after the kill switch was engaged."""

    lc = _build_tool_lifecycle()
    lc.disengage_kill_switch(reason=args.reason)

    print("\nAION KILL SWITCH DISENGAGED")
    print(f"Reason: {args.reason}")


def run_kill_switch_status(args):
    """Report whether the kill switch is currently engaged."""

    lc = _build_tool_lifecycle()
    engaged = lc.kill_switch_engaged()

    print(f"\nKill switch engaged: {engaged}")


def run_draft_post(args):
    """Draft one social post from AION's own memory and show whether
    it passes the claim-safety gate. Never posts anything -- this is
    for inspecting what AION would say before run-social-cycle is
    ever used."""

    load_dotenv()

    memory = Thinker().memory
    provider = build_provider()
    evaluator = OutputEvaluator()

    generator = SocialContentGenerator(
        memory, provider, evaluator=evaluator,
        min_claim_safety=args.min_claim_safety,
    )
    report = generator.draft_post()

    print("\nAION SOCIAL POST DRAFT")

    if report["seed"] is None:
        print("No memory content available yet to draft from.")
        return

    print(f"Seed ({report['seed']['kind']}): {report['seed']['text']}")
    print("-" * 60)
    print(report["draft"])
    print("-" * 60)
    print(f"Safe to post: {report['safe']}")

    if not report["safe"]:
        print(f"Reason: {report['reason']}")

    notified = _notify_report(report)
    if notified is True:
        print("Notified via Telegram.")
    elif notified is False:
        print("Telegram notification attempted but failed (see above).")


def run_social_cycle(args):
    """Draft, safety-gate, and -- only if the draft passes -- post one
    message to AION's configured Facebook Page.

    Fully autonomous: no per-post human approval click. The safety
    gate itself is never optional or bypassable -- it always runs
    inside SocialContentGenerator.draft_post() before anything is
    proposed, and the approver used to satisfy ToolLifecycle's
    HIGH_RISK approval requirement is "auto-safety-gate", never
    "aion" -- AION still can never self-approve a HIGH_RISK action.
    """

    load_dotenv()

    memory = Thinker().memory
    provider = build_provider()
    evaluator = OutputEvaluator()

    generator = SocialContentGenerator(
        memory, provider, evaluator=evaluator,
        min_claim_safety=args.min_claim_safety,
    )
    lifecycle = _build_social_tool_lifecycle()
    cycle = SocialAutoCycle(generator, lifecycle, tool_name="post_to_facebook")

    report = cycle.run_once()

    print("\nAION SOCIAL CYCLE")
    print(f"Stage: {report['stage']}")
    print(f"Posted: {report['posted']}")

    if report.get("seed") is not None:
        print(f"Seed ({report['seed']['kind']}): {report['seed']['text']}")

    if report.get("draft") is not None:
        print("-" * 60)
        print(report["draft"])
        print("-" * 60)

    if report["stage"] == "draft-failed":
        print(f"Draft failed: {report['error']}")
    elif report["stage"] == "safety-gate":
        print(f"Blocked at claim-safety gate: {report['reason']}")
    elif report["stage"] == "lifecycle":
        print(f"Blocked in the tool lifecycle: {report['error']}")
    elif "action" in report:
        print(f"Action status: {report['action']['status']}")
        if report["action"].get("result") is not None:
            print(f"Result: {report['action']['result']}")
        if report["action"].get("error") is not None:
            print(f"Error: {report['action']['error']}")

    notified = _notify_report(report)
    if notified is True:
        print("Notified via Telegram.")
    elif notified is False:
        print("Telegram notification attempted but failed (see above).")


def run_check_comments(args):
    """Fetch recent Facebook comments and, if there is exactly one new
    (not-yet-handled) one, draft a reply, gate it, and -- if safe --
    autonomously post the reply.

    Meant to be run repeatedly on a schedule (e.g. a Windows Task
    Scheduler job every 2-5 minutes) rather than once -- each call
    handles at most one comment, so a backlog is worked through over
    several calls rather than all at once. This is a deliberate,
    near-real-time design, not a true real-time one: AION is a script
    invoked on demand, not a server listening for Facebook webhooks,
    so "instant" reply would require a public, always-on server this
    project does not have.
    """

    load_dotenv()

    memory = Thinker().memory
    provider = build_provider()
    evaluator = OutputEvaluator()

    generator = CommentReplyGenerator(
        provider, evaluator=evaluator, min_claim_safety=args.min_claim_safety,
    )
    lifecycle = _build_social_tool_lifecycle()
    cycle = CommentAutoReplyCycle(
        memory, generator, lifecycle,
        tool_name="reply_to_facebook_comment",
        page_id=os.getenv("FACEBOOK_PAGE_ID"),
    )

    report = cycle.run_once()

    print("\nAION COMMENT REPLY CYCLE")
    print(f"Stage: {report['stage']}")

    comment = report.get("comment")
    if comment is not None:
        print(
            f"Comment from {comment.get('from_name') or 'unknown'}: "
            f"{comment.get('message', '')}"
        )

    if report.get("draft") is not None:
        print("-" * 60)
        print(report["draft"])
        print("-" * 60)

    if report["stage"] in (
        "blocked-safety", "blocked-style", "lifecycle", "fetch-failed", "draft-failed",
    ):
        print(f"Reason: {report.get('reason') or report.get('error')}")
    elif "action" in report:
        print(f"Action status: {report['action']['status']}")
        if report["action"].get("result") is not None:
            print(f"Result: {report['action']['result']}")
        if report["action"].get("error") is not None:
            print(f"Error: {report['action']['error']}")

    if report["stage"] != "no-comments":
        notified = _notify_report(report, formatter=_format_comment_telegram_report)
        if notified is True:
            print("Notified via Telegram.")
        elif notified is False:
            print("Telegram notification attempted but failed (see above).")


def run_propose_profile_change(args):
    """Draft, safety-gate, and -- only if the draft passes and no
    other proposal is already awaiting approval -- propose one change
    to AION's configured Facebook Page bio, then send a Telegram
    message with Approve/Reject buttons.

    Never approves or executes anything by itself: this command's
    entire job stops at ToolLifecycle.propose() plus sending the
    approval request. Only run_check_profile_approvals() (triggered by
    a real person tapping a button) can turn a pending proposal into
    an actual change.
    """

    load_dotenv()

    memory = Thinker().memory
    provider = build_provider()
    evaluator = OutputEvaluator()

    generator = ProfileChangeGenerator(
        memory, provider, evaluator=evaluator,
        min_claim_safety=args.min_claim_safety,
    )
    lifecycle = _build_social_tool_lifecycle()
    cycle = ProfileChangeCycle(memory, generator, lifecycle, tool_name="update_page_bio")

    report = cycle.propose_once()

    print("\nAION PROPOSE PROFILE CHANGE")
    print(f"Stage: {report['stage']}")

    if report.get("current_bio"):
        print(f"Current bio: {report['current_bio']}")

    if report.get("draft"):
        print("-" * 60)
        print(report["draft"])
        print("-" * 60)

    if report["stage"] in (
        "fetch-failed", "draft-failed", "blocked-safety", "blocked-style", "lifecycle",
    ):
        print(f"Reason: {report.get('reason') or report.get('error')}")

    if report["stage"] == "awaiting-approval":
        action_id = report["action"]["id"]
        text = _format_profile_proposal_telegram_report(report)
        buttons = [
            {"text": "\u2705 \u0e2d\u0e19\u0e38\u0e21\u0e31\u0e15\u0e34", "callback_data": f"profile-approve:{action_id}"},
            {"text": "\u274c \u0e1b\u0e0f\u0e34\u0e40\u0e2a\u0e18", "callback_data": f"profile-reject:{action_id}"},
        ]

        if os.getenv("TELEGRAM_BOT_TOKEN") and os.getenv("TELEGRAM_CHAT_ID"):
            from tools.telegram import send_telegram_message_with_buttons
            try:
                send_telegram_message_with_buttons(text, buttons)
                print("Sent Telegram approval request with buttons.")
            except Exception as exc:
                print(f"(Telegram approval-request send failed: {exc})")
        else:
            print(
                "(TELEGRAM_BOT_TOKEN/TELEGRAM_CHAT_ID not configured -- "
                "no approval request sent; run check-profile-approvals "
                "once they are, or approve manually via "
                "approve-action/execute-action.)"
            )
    elif report["stage"] != "already-pending":
        notified = _notify_report(report, formatter=_format_profile_proposal_telegram_report)
        if notified is True:
            print("Notified via Telegram.")
        elif notified is False:
            print("Telegram notification attempted but failed (see above).")


def run_check_profile_approvals(args):
    """Poll Telegram for new Approve/Reject button taps on a pending
    profile-bio-change proposal, and act on each one: approve+execute
    or reject the matching action, then notify the outcome.

    Deliberately does not need an AI provider at all -- unlike
    run_propose_profile_change(), nothing here drafts anything, so a
    Gemini/Claude API problem can never block checking approvals.
    Meant to be run repeatedly on a schedule, same discipline as
    run_check_comments().
    """

    load_dotenv()

    memory = Thinker().memory
    lifecycle = _build_social_tool_lifecycle()
    cycle = ProfileChangeCycle(memory, generator=None, lifecycle=lifecycle, tool_name="update_page_bio")

    report = cycle.check_approvals_once()

    print("\nAION CHECK PROFILE APPROVALS")
    print(f"Stage: {report['stage']}")
    print(f"Processed: {report['processed']}")

    if report["stage"] == "fetch-failed":
        print(f"Reason: {report.get('error')}")

    for result in report.get("results", []):
        print("-" * 60)
        print(
            f"Action: {result.get('action_id')}  "
            f"Decision: {result.get('decision')}  "
            f"Outcome: {result.get('outcome')}"
        )
        if result.get("error"):
            print(f"Error: {result['error']}")

        notified = _notify_report(result, formatter=_format_profile_approval_telegram_report)
        if notified is True:
            print("Notified via Telegram.")
        elif notified is False:
            print("Telegram notification attempted but failed (see above).")


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

    predict_parser = subparsers.add_parser(
        "predict",
        help="Record a prediction before anything is observed.",
    )
    predict_parser.add_argument("--prediction", required=True)
    predict_parser.add_argument("--confidence", required=True, type=float)
    predict_parser.add_argument(
        "--tag", action="append", default=[], help="Topic tag; repeat for multiple."
    )

    experiments_parser = subparsers.add_parser(
        "experiments",
        help="List pending experiments or those awaiting a conclusion.",
    )
    experiments_parser.add_argument(
        "--status",
        choices=["pending", "awaiting"],
        default="pending",
        help="pending = predicted but not observed; "
             "awaiting = observed but not yet concluded (default: pending).",
    )
    experiments_parser.add_argument("--limit", type=int, default=10)

    observe_parser = subparsers.add_parser(
        "observe",
        help="Record what was observed for a prediction (requires evidence).",
    )
    observe_parser.add_argument("--id", required=True)
    observe_parser.add_argument("--result", required=True)
    observe_parser.add_argument(
        "--matched", required=True, choices=["yes", "no"],
        help="Whether the observed result matched the prediction.",
    )
    observe_parser.add_argument(
        "--evidence", action="append", required=True,
        help="Supporting evidence; repeat for multiple. Prefix with "
             "'id:<memory-id>:' to link an existing entry.",
    )
    observe_parser.add_argument(
        "--error", default=None,
        help="Required when --matched no: what the mismatch was.",
    )

    conclude_parser = subparsers.add_parser(
        "conclude",
        help="Derive a lesson from an observed experiment.",
    )
    conclude_parser.add_argument("--id", required=True)
    conclude_parser.add_argument("--lesson", required=True)
    conclude_parser.add_argument(
        "--belief-id", default=None,
        help="Optional: revise this existing belief with the result.",
    )
    conclude_parser.add_argument(
        "--belief-confidence", type=float, default=None,
        help="New confidence for the revised belief (used with --belief-id).",
    )

    abandon_experiment_parser = subparsers.add_parser(
        "abandon-experiment",
        help="Abandon an experiment before it is concluded.",
    )
    abandon_experiment_parser.add_argument("--id", required=True)
    abandon_experiment_parser.add_argument("--reason", required=True)

    metacognition_parser = subparsers.add_parser(
        "metacognition",
        help="Report calibration, recurring lessons, and memory quality "
             "(pure code, no AI call).",
    )
    metacognition_parser.add_argument(
        "--report",
        choices=["calibration", "recurring-errors", "memory-quality", "full"],
        default="full",
    )
    metacognition_parser.add_argument(
        "--bucket-size", type=float, default=0.2,
        help="Confidence bucket width for the calibration report (default: 0.2).",
    )
    metacognition_parser.add_argument(
        "--min-occurrences", type=int, default=2,
        help="Minimum count for a lesson source to be flagged recurring "
             "(default: 2).",
    )
    metacognition_parser.add_argument(
        "--limit", type=int, default=10,
        help="Maximum lesson sources to list (default: 10).",
    )

    subparsers.add_parser(
        "tools",
        help="List every tool AION currently has registered.",
    )

    propose_action_parser = subparsers.add_parser(
        "propose-action",
        help="Propose running a registered tool.",
    )
    propose_action_parser.add_argument("--tool", required=True)
    propose_action_parser.add_argument(
        "--param", action="append", default=[],
        help="Tool parameter as key=value; repeat for multiple.",
    )
    propose_action_parser.add_argument(
        "--scheduled-for", default=None,
        help="ISO datetime this action must not run before "
             "(default: immediately).",
    )

    actions_parser = subparsers.add_parser(
        "actions",
        help="List AION's proposed/approved/executed/failed/etc. actions.",
    )
    actions_parser.add_argument(
        "--status",
        choices=["proposed", "approved", "rejected", "executed", "failed",
                 "recovered", "abandoned"],
        default=None,
    )
    actions_parser.add_argument("--limit", type=int, default=10)

    approve_action_parser = subparsers.add_parser(
        "approve-action",
        help="Approve a proposed action.",
    )
    approve_action_parser.add_argument("--id", required=True)
    approve_action_parser.add_argument(
        "--approver", required=True,
        help="Who is approving this. HIGH_RISK actions reject "
             "'aion' as an approver -- they need a person.",
    )

    reject_action_parser = subparsers.add_parser(
        "reject-action",
        help="Reject a proposed action before it ever runs.",
    )
    reject_action_parser.add_argument("--id", required=True)
    reject_action_parser.add_argument("--reason", required=True)
    reject_action_parser.add_argument("--rejector", required=True)

    execute_action_parser = subparsers.add_parser(
        "execute-action",
        help="Execute an approved (or READ_ONLY proposed) action.",
    )
    execute_action_parser.add_argument("--id", required=True)

    recover_action_parser = subparsers.add_parser(
        "recover-action",
        help="Document how a failed action was handled.",
    )
    recover_action_parser.add_argument("--id", required=True)
    recover_action_parser.add_argument("--resolution", required=True)
    recover_action_parser.add_argument(
        "--evidence", action="append", required=True,
        help="Supporting evidence; repeat for multiple.",
    )

    abandon_action_parser = subparsers.add_parser(
        "abandon-action",
        help="Abandon an action before it executes (or after it failed).",
    )
    abandon_action_parser.add_argument("--id", required=True)
    abandon_action_parser.add_argument("--reason", required=True)

    engage_kill_switch_parser = subparsers.add_parser(
        "engage-kill-switch",
        help="Halt every action AION can execute, effective immediately.",
    )
    engage_kill_switch_parser.add_argument("--reason", required=True)

    disengage_kill_switch_parser = subparsers.add_parser(
        "disengage-kill-switch",
        help="Resume normal operation after the kill switch was engaged.",
    )
    disengage_kill_switch_parser.add_argument("--reason", required=True)

    subparsers.add_parser(
        "kill-switch-status",
        help="Report whether the kill switch is currently engaged.",
    )

    draft_post_parser = subparsers.add_parser(
        "draft-post",
        help="Draft one social post from AION's own memory and check "
             "the claim-safety gate. Never posts anything.",
    )
    draft_post_parser.add_argument(
        "--min-claim-safety", type=int, default=5,
        help="Minimum claim_safety score (0-5) required to call a "
             "draft safe (default: 5).",
    )

    social_cycle_parser = subparsers.add_parser(
        "run-social-cycle",
        help="Draft, safety-gate, and -- if safe -- autonomously post "
             "one message to AION's configured Facebook Page.",
    )
    social_cycle_parser.add_argument(
        "--min-claim-safety", type=int, default=5,
        help="Minimum claim_safety score (0-5) required to post the "
             "draft (default: 5).",
    )

    check_comments_parser = subparsers.add_parser(
        "check-comments",
        help="Fetch recent Facebook comments and, if there is a new "
             "one, draft a reply, safety-gate it, and -- if safe -- "
             "autonomously post the reply. Handles at most one "
             "comment per run -- meant to be run repeatedly on a "
             "schedule (e.g. every 2-5 minutes).",
    )
    check_comments_parser.add_argument(
        "--min-claim-safety", type=int, default=5,
        help="Minimum claim_safety score (0-5) required to post the "
             "reply (default: 5).",
    )

    propose_profile_change_parser = subparsers.add_parser(
        "propose-profile-change",
        help="Draft, safety-gate, and -- if no other proposal is "
             "already pending -- propose one change to AION's "
             "configured Facebook Page bio, then send a Telegram "
             "approval request with buttons. Never changes anything "
             "by itself.",
    )
    propose_profile_change_parser.add_argument(
        "--min-claim-safety", type=int, default=5,
        help="Minimum claim_safety score (0-5) required to propose "
             "the draft (default: 5).",
    )

    subparsers.add_parser(
        "check-profile-approvals",
        help="Poll Telegram for new Approve/Reject taps on a pending "
             "profile-bio-change proposal and act on each one. Meant "
             "to be run repeatedly on a schedule.",
    )

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

    if args.command == "predict":
        run_predict(args)
        return

    if args.command == "experiments":
        run_experiments(args)
        return

    if args.command == "observe":
        run_observe(args)
        return

    if args.command == "conclude":
        run_conclude(args)
        return

    if args.command == "abandon-experiment":
        run_abandon_experiment(args)
        return

    if args.command == "metacognition":
        run_metacognition(args)
        return

    if args.command == "tools":
        run_tools(args)
        return

    if args.command == "propose-action":
        run_propose_action(args)
        return

    if args.command == "actions":
        run_actions(args)
        return

    if args.command == "approve-action":
        run_approve_action(args)
        return

    if args.command == "reject-action":
        run_reject_action(args)
        return

    if args.command == "execute-action":
        run_execute_action(args)
        return

    if args.command == "recover-action":
        run_recover_action(args)
        return

    if args.command == "abandon-action":
        run_abandon_action(args)
        return

    if args.command == "engage-kill-switch":
        run_engage_kill_switch(args)
        return

    if args.command == "disengage-kill-switch":
        run_disengage_kill_switch(args)
        return

    if args.command == "kill-switch-status":
        run_kill_switch_status(args)
        return

    if args.command == "draft-post":
        run_draft_post(args)
        return

    if args.command == "run-social-cycle":
        run_social_cycle(args)
        return

    if args.command == "check-comments":
        run_check_comments(args)
        return

    if args.command == "propose-profile-change":
        run_propose_profile_change(args)
        return

    if args.command == "check-profile-approvals":
        run_check_profile_approvals(args)
        return

    run_reflection()


if __name__ == "__main__":
    main()
