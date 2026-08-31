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
from brain.learning import WebLearningGenerator, WebLearningCycle
from brain.self_narrative import SelfNarrativeGenerator, SelfNarrativeCycle
from brain.reflection import ReflectionEngine, ReflectionCycle
from brain.visual_content import VisualContentCycle
from brain.social_feedback import InstagramFeedbackCycle
from brain.reels import ReelContentCycle


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

    if provider_name in ("openai-compatible", "openchat"):
        from providers.openai_compatible import OpenAICompatibleProvider
        return OpenAICompatibleProvider()

    if provider_name not in ("gemini", "claude", "openai-compatible", "openchat"):
        raise ValueError(
            f"Unknown AI_PROVIDER: {provider_name!r}. "
            "Use 'gemini', 'claude', or 'openai-compatible'."
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

    All three are subject to the same autonomous safety policy: each
    action must clear its content gate, be recorded in the lifecycle,
    stay within its budget, and be stopped by the kill switch when
    needed.  The policy decision is recorded explicitly; it is not a
    pretend human approval.

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
        "only after the autonomous profile safety/style policy has "
        "recorded its approval.",
    )

    from tools.instagram import publish_photo, publish_video

    registry.register(
        "post_to_instagram",
        lambda image_url, caption="": publish_photo(image_url, caption=caption),
        ActionLevel.HIGH_RISK,
        "Publish one photo (with caption) to AION's configured "
        "Instagram Business account -- shares post_to_facebook's own "
        "HIGH_RISK budget and autonomous safety/style policy.",
    )
    registry.register(
        "post_reel_to_instagram",
        lambda video_url, caption="": publish_video(video_url, caption=caption),
        ActionLevel.HIGH_RISK,
        "Publish one AION Reel to Instagram through the same safety and budget policy.",
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

    if report["stage"] != "no-seed":
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
    """Draft, gate, and autonomously apply one safe Page-bio change.

    This uses the same explicit autonomy-policy audit record as normal
    posts. The separate IDENTITY_CHANGE budget and the global kill switch
    still apply, so autonomy never becomes unlimited authority.
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
        try:
            approved = lifecycle.auto_approve(
                report["action"]["id"], policy="profile-safety-style-gate"
            )
            executed = lifecycle.execute(approved["id"])
            report["action"] = executed
            report["stage"] = (
                "executed" if executed["status"] == "executed" else "failed"
            )
            print(f"Automatic profile action: {executed['status']}")
        except Exception as exc:
            report["stage"] = "lifecycle"
            report["error"] = str(exc)
            print(f"Automatic profile action failed: {exc}")

        notified = _notify_report(report, formatter=_format_profile_proposal_telegram_report)
        if notified is True:
            print("Notified via Telegram.")
        elif notified is False:
            print("Telegram notification attempted but failed (see above).")
    elif report["stage"] != "already-pending":
        notified = _notify_report(report, formatter=_format_profile_proposal_telegram_report)
        if notified is True:
            print("Notified via Telegram.")
        elif notified is False:
            print("Telegram notification attempted but failed (see above).")


def run_check_profile_approvals(args):
    """Legacy no-op retained for compatibility with older schedules.

    Profile changes are now evaluated and, when safe, executed by
    ``run_propose_profile_change`` under the recorded autonomous policy.
    This command deliberately never consumes Telegram callbacks, so an old
    callback cannot cause a delayed external profile change.
    """

    print("AION CHECK PROFILE APPROVALS: disabled; profile changes are autonomous.")


def _format_instagram_draft_telegram_report(report):
    """Turn a VisualContentCycle.draft_once() report dict into a
    short Thai summary -- printed/notified for every stage, same
    convention as _format_telegram_report (the Facebook-post
    equivalent)."""

    lines = ["AION (ร่างภาพ Instagram):"]

    stage = report.get("stage")
    caption = report.get("caption")

    if caption:
        lines.append(f"แคปชั่น: {caption}")

    if stage == "no-seed":
        lines.append("ยังไม่มีเนื้อหาที่บันทึกไว้มากพอจะร่างภาพได้ตอนนี้")
    elif stage == "safety-gate":
        lines.append(f"ถูกบล็อกที่ตัวกรองความปลอดภัย: {report.get('reason')}")
    elif stage == "style-gate":
        lines.append(
            f"ถูกบล็อกที่ตัวกรองน้ำเสียง (ฟังดูเป็นระบบ/รายงานเกินไป): "
            f"{report.get('reason')}"
        )
    elif stage == "draft-failed":
        lines.append(f"ร่างแคปชั่นไม่สำเร็จ (ปัญหาที่ตัว AI provider): {report.get('error')}")
    elif stage == "drafted":
        lines.append(f"เรนเดอร์ภาพแล้ว: {report.get('image_path')}")
        lines.append("รอ commit/push ภาพนี้เข้า repo แล้วเผยแพร่ผ่านขั้นตอนถัดไป")

    return "\n".join(lines)


def _format_instagram_publish_telegram_report(report):
    """Turn a VisualContentCycle.publish_once() report dict into a
    short Thai summary."""

    lines = ["AION (เผยแพร่ภาพ Instagram):"]

    stage = report.get("stage")
    caption = report.get("caption")

    if caption:
        lines.append(f"แคปชั่น: {caption}")

    if stage == "no-pending":
        lines.append("ไม่มีภาพที่ร่างไว้รอเผยแพร่ตอนนี้")
    elif stage == "lifecycle":
        lines.append(f"ผิดพลาดในระบบ lifecycle: {report.get('error')}")
    elif stage == "published":
        lines.append(f"เผยแพร่ขึ้น Instagram สำเร็จแล้ว ✅ ({report.get('image_url')})")
    elif stage == "failed":
        action = report.get("action") or {}
        lines.append(f"เผยแพร่ไม่สำเร็จ: {action.get('error')} (จะลองใหม่รอบหน้าด้วยภาพเดิม)")

    return "\n".join(lines)


def run_instagram_draft(args):
    """Draft one Instagram caption (same gates as a Facebook post) and,
    if it passes, render it into a PNG card under content/images/ in
    this repo. Never calls the Instagram Graph API -- that only ever
    happens in run_instagram_publish(), after the rendered image has
    actually been committed and pushed (see
    .github/workflows/instagram-cycle.yml)."""

    load_dotenv()

    memory = Thinker().memory
    provider = build_provider()
    evaluator = OutputEvaluator()

    social_generator = SocialContentGenerator(
        memory, provider, evaluator=evaluator,
        min_claim_safety=args.min_claim_safety,
    )

    lifecycle = _build_social_tool_lifecycle()
    cycle = VisualContentCycle(memory, social_generator, lifecycle, tool_name="post_to_instagram")

    report = cycle.draft_once()

    print("\nAION INSTAGRAM DRAFT")
    print(f"Stage: {report['stage']}")

    if report.get("caption"):
        print("-" * 60)
        print(report["caption"])
        print("-" * 60)

    if report.get("image_path"):
        print(f"Image: {report['image_path']}")

    if report["stage"] not in ("drafted",):
        reason = report.get("reason") or report.get("error")
        if reason:
            print(f"Reason: {reason}")

    if report["stage"] not in ("no-seed",):
        notified = _notify_report(report, formatter=_format_instagram_draft_telegram_report)
        if notified is True:
            print("Notified via Telegram.")
        elif notified is False:
            print("Telegram notification attempted but failed (see above).")


def run_instagram_publish(args):
    """Publish the oldest already-drafted-and-committed pending image
    to Instagram. Deliberately does not need an AI provider at all --
    nothing here drafts anything."""

    load_dotenv()

    memory = Thinker().memory
    lifecycle = _build_social_tool_lifecycle()
    cycle = VisualContentCycle(memory, social_generator=None, lifecycle=lifecycle, tool_name="post_to_instagram")

    report = cycle.publish_once()

    print("\nAION INSTAGRAM PUBLISH")
    print(f"Stage: {report['stage']}")

    if report.get("error"):
        print(f"Reason: {report['error']}")

    if report["stage"] != "no-pending":
        notified = _notify_report(report, formatter=_format_instagram_publish_telegram_report)
        if notified is True:
            print("Notified via Telegram.")
        elif notified is False:
            print("Telegram notification attempted but failed (see above).")


def run_reel_draft(args):
    load_dotenv()
    memory = Thinker().memory
    generator = SocialContentGenerator(memory, build_provider(), evaluator=OutputEvaluator(), min_claim_safety=args.min_claim_safety)
    report = ReelContentCycle(memory, generator, _build_social_tool_lifecycle()).draft_once()
    print("\nAION REEL DRAFT")
    print(f"Stage: {report['stage']}")
    if report.get("video_path"):
        print(f"Video: {report['video_path']}")


def run_reel_publish(args):
    load_dotenv()
    report = ReelContentCycle(Thinker().memory, None, _build_social_tool_lifecycle()).publish_once()
    print("\nAION REEL PUBLISH")
    print(f"Stage: {report['stage']}")


def _format_learning_telegram_report(report):
    """Turn a WebLearningCycle.research_once() report dict into a
    short Thai summary -- the Telegram notification body, and also
    what is printed for stages that never reach an answer."""

    lines = ["AION (เรียนรู้จากภายนอก):"]

    question = report.get("question") or {}
    if question.get("statement"):
        lines.append(f"คำถาม: {question['statement']}")

    source = report.get("source") or {}
    if source.get("title"):
        lines.append(f"แหล่งที่ค้นเจอ: {source['title']}")

    draft = report.get("draft")
    if draft:
        lines.append(f"คำตอบที่ร่างไว้: {draft}")

    stage = report.get("stage")

    if stage == "no-open-questions":
        lines.append("ไม่มีคำถามที่ยังเปิดอยู่ให้ค้นคว้าตอนนี้")
    elif stage == "search-failed":
        lines.append(f"ค้นหาใน Wikipedia ไม่สำเร็จ: {report.get('error')}")
    elif stage == "no-search-results":
        lines.append("ค้นหาใน Wikipedia แล้วไม่พบผลลัพธ์ที่เกี่ยวข้อง")
    elif stage == "fetch-failed":
        lines.append(f"ดึงเนื้อหาจาก Wikipedia ไม่สำเร็จ: {report.get('error')}")
    elif stage == "empty-source":
        lines.append("หน้า Wikipedia ที่เจอไม่มีเนื้อหาให้สรุป")
    elif stage == "draft-failed":
        lines.append(f"สรุปคำตอบไม่สำเร็จ (ปัญหาที่ตัว AI provider): {report.get('error')}")
    elif stage == "blocked-safety":
        lines.append(f"ถูกบล็อกที่ตัวกรองความปลอดภัย: {report.get('reason')}")
    elif stage == "blocked-style":
        lines.append(f"ถูกบล็อกที่ตัวกรองน้ำเสียง: {report.get('reason')}")
    elif stage == "answered":
        lines.append("บันทึกเป็นความรู้ใหม่และตอบคำถามนี้แล้ว")

    return "\n".join(lines)


def run_learning_cycle(args):
    """Pick one open curiosity question, search Wikipedia, draft a
    grounded answer, safety-gate it, and -- if safe -- record it as
    new knowledge and resolve the question with that source as
    evidence.

    Never touches Facebook/Telegram tools directly and needs no
    ToolLifecycle -- researching and updating AION's own memory has no
    external side effect to gate, unlike posting/replying/bio changes.
    Meant to be run repeatedly on a schedule, same discipline as
    run_check_comments()/run_social_cycle().
    """

    load_dotenv()

    memory = Thinker().memory
    provider = build_provider()
    evaluator = OutputEvaluator()

    curiosity = CuriosityEngine(memory)
    generator = WebLearningGenerator(
        provider, evaluator=evaluator, min_claim_safety=args.min_claim_safety,
    )
    cycle = WebLearningCycle(memory, curiosity, generator)

    report = cycle.research_once()

    print("\nAION LEARNING CYCLE")
    print(f"Stage: {report['stage']}")

    question = report.get("question")
    if question is not None:
        print(f"Question: {question.get('statement', '')}")

    source = report.get("source")
    if source and source.get("title"):
        print(f"Source: {source['title']} ({source.get('url', '')})")

    if report.get("draft") is not None:
        print("-" * 60)
        print(report["draft"])
        print("-" * 60)

    if report["stage"] in (
        "search-failed", "fetch-failed", "draft-failed",
        "blocked-safety", "blocked-style",
    ):
        print(f"Reason: {report.get('reason') or report.get('error')}")

    # Notify on every run, including the routine no-op stages -- the
    # user explicitly asked (2026-08-31) to see every reflection/
    # learning cycle's outcome as a visibility feature, not just the
    # stages that produce something new. Telegram's Bot API has no
    # quota/cost at this volume (hourly at most); the formatter keeps
    # each no-op message to one short line so the higher frequency
    # stays skimmable rather than noisy.
    notified = _notify_report(report, formatter=_format_learning_telegram_report)
    if notified is True:
        print("Notified via Telegram.")
    elif notified is False:
        print("Telegram notification attempted but failed (see above).")


def _format_reflection_telegram_report(report):
    """Turn a ReflectionCycle.run_once() report dict into a short Thai
    summary -- the Telegram notification body for EVERY stage,
    including the routine no-op ones (2026-08-31: the user asked to
    see every cycle's outcome, not just the ones that raise something
    new). Each no-op case is kept to one short line on purpose, so a
    higher-frequency notification stream stays easy to skim."""

    lines = ["AION (ทบทวนตัวเอง):"]

    stage = report.get("stage")

    if stage in ("raised", "bootstrapped"):
        labels = {
            "question": "ตั้งคำถามใหม่",
            "belief": "สร้างความเชื่อใหม่",
            "goal": "ตั้งเป้าหมายใหม่",
        }
        lines.append(
            f"{labels.get(report.get('originated_type'), 'สร้างสิ่งใหม่')}: "
            f"{report.get('statement')}"
        )
        if report.get("criteria"):
            lines.append(f"เกณฑ์สำเร็จ: {report.get('criteria')}")
        if report.get("confidence") is not None:
            lines.append(f"ความมั่นใจ: {report.get('confidence'):.2f}")
    elif stage == "safety-gate":
        lines.append(
            f"ร่างคำถามขึ้นมาแล้วแต่ถูกบล็อกที่ตัวกรองความปลอดภัย: "
            f"{report.get('question')}"
        )
    elif stage == "draft-failed":
        lines.append(f"ทบทวนไม่สำเร็จ (ปัญหาที่ตัว AI provider): {report.get('error')}")
    elif stage == "origination-at-capacity":
        lines.append(
            "มีคำถามและเป้าหมายที่เปิดอยู่เต็มโควต้าแล้ว รอบนี้เลยยังไม่คิดเรื่องใหม่"
        )
    elif stage in ("question-at-capacity", "goal-at-capacity"):
        lines.append("สิ่งที่เลือกจะสร้างเต็มโควต้าแล้ว รอบนี้จึงยังไม่บันทึกเพิ่ม")
    elif stage == "no-new-material":
        lines.append("ยังไม่มีกิจกรรมใหม่ (คอมเมนต์/ความรู้/บทเรียน) ให้ทบทวนตอนนี้")
    elif stage == "nothing-new":
        count = report.get("material_count")
        lines.append(
            f"ทบทวนแล้ว ({count} รายการ) แต่ยังไม่เจออะไรน่าสงสัยพอจะตั้งคำถามใหม่"
        )

    return "\n".join(lines)


def run_reflection_cycle(args):
    """Look at real material recorded since the last reflection
    (Facebook comments already replied to, external knowledge learned
    via Wikipedia, non-review lessons) and -- only if the provider
    points to something genuinely new -- originate one question,
    evidence-backed belief, or goal.

    This is the piece that actually originates new curiosity for
    run-learning-cycle to research and run-social-cycle to draft from;
    see brain/reflection.py's module docstring for why this was
    missing and what broke without it. Meant to be run repeatedly on
    a slower schedule than the reactive cycles (see
    reflection-cycle.yml).
    """

    load_dotenv()

    memory = Thinker().memory
    provider = build_provider()
    evaluator = OutputEvaluator()

    engine = ReflectionEngine(
        memory, provider, evaluator=evaluator,
        min_claim_safety=args.min_claim_safety,
    )
    cycle = ReflectionCycle(engine)

    report = cycle.run_once()

    print("\nAION REFLECTION CYCLE")
    print(f"Stage: {report['stage']}")
    print(f"Raised: {report['raised']}")

    if report.get("material_count") is not None:
        print(f"Material considered: {report['material_count']} item(s)")
    if report.get("statement"):
        print(f"Originated {report.get('originated_type')}: {report['statement']}")
    if report.get("criteria"):
        print(f"Completion criteria: {report['criteria']}")
    if report.get("confidence") is not None:
        print(f"Confidence: {report['confidence']:.2f}")
    if report.get("reply") is not None:
        # Only present on "nothing-new" -- the provider's raw reply,
        # printed so a human reviewing the Actions log can tell a
        # genuine "nothing stood out" from a malformed-format reply
        # that should have been the two-line "คำถาม:/เกณฑ์ตอบสำเร็จ:"
        # shape instead.
        print(f"Provider reply: {report['reply']!r}")
    if report.get("error"):
        print(f"Error: {report['error']}")

    # Notify on every run, including the routine no-op stages
    # (origination-at-capacity, no-new-material, nothing-new) -- the
    # user explicitly asked (2026-08-31) to see every reflection
    # cycle's outcome as a visibility feature ("want to see what it's
    # thinking about"), not just the stages that raise something new.
    # Telegram's Bot API has no quota/cost at this volume (every 3h);
    # the formatter keeps each no-op message to one short line so the
    # higher frequency stays skimmable rather than a repeat of the
    # earlier hourly-spam problem this guard was originally added to
    # prevent.
    notified = _notify_report(report, formatter=_format_reflection_telegram_report)
    if notified is True:
        print("Notified via Telegram.")
    elif notified is False:
        print("Telegram notification attempted but failed (see above).")


def run_instagram_feedback(args):
    """Read changed Instagram performance metrics into AION's memory.

    The cycle has no publishing side effect. Its observations become material
    for reflection, so future questions, beliefs, and goals can be grounded in
    the audience's real response instead of guesses.
    """

    load_dotenv()
    from tools.instagram_insights import get_account_overview, get_recent_media

    cycle = InstagramFeedbackCycle(
        Thinker().memory,
        overview_reader=get_account_overview,
        media_reader=get_recent_media,
    )
    report = cycle.capture_once(limit=args.limit)

    print("\nAION INSTAGRAM FEEDBACK")
    print(f"Stage: {report['stage']}")
    print(f"Recorded: {report['recorded']}")
    if report.get("overview"):
        overview = report["overview"]
        print(f"Followers: {overview.get('followers_count')}")
    if report.get("error"):
        print(f"Error: {report['error']}")


def run_export_obsidian_vault(args):
    """Export a read-only linked view of AION's brain for Obsidian."""
    from brain.obsidian import ObsidianVaultExporter
    report = ObsidianVaultExporter(Thinker().memory).export(args.output)
    print("\nAION OBSIDIAN VAULT")
    print(f"Location: {report['output']}")
    print(f"Memory notes: {report['notes']}")


def _format_self_narrative_telegram_report(report):
    """Turn a SelfNarrativeCycle.reflect_once() report dict into a
    short Thai summary -- the Telegram notification body, and also
    what is printed for stages that never reach a recorded entry."""

    lines = ["AION (อัตชีวประวัติ):"]

    draft = report.get("draft")
    if draft:
        lines.append(f"บันทึกล่าสุด: {draft}")

    stage = report.get("stage")

    if stage == "no-new-activity":
        lines.append("ยังไม่มีอะไรใหม่เกิดขึ้นตั้งแต่ครั้งก่อน เลยยังไม่เขียนสรุปใหม่")
    elif stage == "draft-failed":
        lines.append(f"เขียนสรุปไม่สำเร็จ (ปัญหาที่ตัว AI provider): {report.get('error')}")
    elif stage == "blocked-safety":
        lines.append(f"ถูกบล็อกที่ตัวกรองความปลอดภัย: {report.get('reason')}")
    elif stage == "blocked-style":
        lines.append(f"ถูกบล็อกที่ตัวกรองน้ำเสียง: {report.get('reason')}")
    elif stage == "duplicate-skipped":
        lines.append("ร่างที่ได้เหมือนกับครั้งก่อนเป๊ะ เลยไม่บันทึกซ้ำ")
    elif stage == "reflected":
        lines.append("บันทึกเป็นอัตชีวประวัติรายการใหม่แล้ว")

    return "\n".join(lines)


def run_self_narrative(args):
    """Reflect once: if anything new has happened in memory since the
    last self-narrative entry, gather real evidence about AION's
    current state, draft a short first-person summary of what AION
    currently understands about itself, safety/style-gate it, and --
    if safe -- record it, continuing from the previous entry rather
    than starting over each time.

    Never touches Facebook/Telegram tools directly and needs no
    ToolLifecycle -- like run_learning_cycle(), writing to AION's own
    memory has no external side effect to gate. Meant to be run
    repeatedly on a schedule (daily by default -- see
    .github/workflows/self-narrative.yml for why a slower cadence
    than the action cycles was chosen).
    """

    load_dotenv()

    memory = Thinker().memory
    provider = build_provider()
    evaluator = OutputEvaluator()

    generator = SelfNarrativeGenerator(
        provider, evaluator=evaluator, min_claim_safety=args.min_claim_safety,
    )
    cycle = SelfNarrativeCycle(memory, generator)

    report = cycle.reflect_once(force=args.force)

    print("\nAION SELF-NARRATIVE")
    print(f"Stage: {report['stage']}")

    if report.get("draft") is not None:
        print("-" * 60)
        print(report["draft"])
        print("-" * 60)

    if report["stage"] in ("draft-failed", "blocked-safety", "blocked-style"):
        print(f"Reason: {report.get('reason') or report.get('error')}")

    if report["stage"] != "no-new-activity":
        notified = _notify_report(
            report, formatter=_format_self_narrative_telegram_report,
        )
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
        help="Draft and safety-gate one change to AION's configured "
             "Facebook Page bio, then automatically apply it only "
             "when the autonomous policy allows it.",
    )
    propose_profile_change_parser.add_argument(
        "--min-claim-safety", type=int, default=5,
        help="Minimum claim_safety score (0-5) required to propose "
             "the draft (default: 5).",
    )

    subparsers.add_parser(
        "check-profile-approvals",
        help="Legacy compatibility command; it no longer acts on "
             "Telegram approval callbacks.",
    )

    learning_cycle_parser = subparsers.add_parser(
        "run-learning-cycle",
        help="Pick one open curiosity question, search Wikipedia, "
             "draft a grounded answer, safety-gate it, and -- if "
             "safe -- record it as new knowledge and resolve the "
             "question. Meant to be run repeatedly on a schedule.",
    )
    learning_cycle_parser.add_argument(
        "--min-claim-safety", type=int, default=5,
        help="Minimum claim_safety score (0-5) required to accept "
             "the drafted answer (default: 5).",
    )

    self_narrative_parser = subparsers.add_parser(
        "run-self-narrative",
        help="If anything new has happened in memory since the last "
             "entry, draft a short first-person summary of what AION "
             "currently understands about itself and record it. "
             "Meant to be run repeatedly on a schedule.",
    )
    self_narrative_parser.add_argument(
        "--min-claim-safety", type=int, default=5,
        help="Minimum claim_safety score (0-5) required to accept "
             "the drafted reflection (default: 5).",
    )
    self_narrative_parser.add_argument(
        "--force", action="store_true",
        help="Draft a reflection even if nothing new has happened "
             "since the last entry (for manual/testing use).",
    )

    reflection_cycle_parser = subparsers.add_parser(
        "run-reflection-cycle",
        help="If real material has been recorded since the last "
             "reflection (comment replies, external knowledge, "
             "lessons) and the provider points to something genuinely "
             "new, raise one new curiosity question. Meant to be run "
             "repeatedly on a slower schedule than the reactive "
             "cycles.",
    )
    reflection_cycle_parser.add_argument(
        "--min-claim-safety", type=int, default=5,
        help="Minimum claim_safety score (0-5) required to accept "
             "a raised question (default: 5).",
    )

    instagram_feedback_parser = subparsers.add_parser(
        "run-instagram-feedback",
        help="Read changed Instagram follower and post-engagement metrics "
             "into AION's memory; never publishes anything.",
    )
    instagram_feedback_parser.add_argument(
        "--limit", type=int, default=10,
        help="Maximum recent Instagram posts to observe (default: 10).",
    )

    obsidian_parser = subparsers.add_parser(
        "export-obsidian-vault",
        help="Export AION memory as a linked Markdown vault for Obsidian.",
    )
    obsidian_parser.add_argument("--output", default="aion-vault")

    instagram_draft_parser = subparsers.add_parser(
        "run-instagram-draft",
        help="Draft one Instagram caption (same gates as a Facebook "
             "post) and, if it passes, render it into a PNG card "
             "under content/images/ in this repo. Never calls the "
             "Instagram API -- that is run-instagram-publish's job, "
             "after the image has been committed and pushed.",
    )
    instagram_draft_parser.add_argument(
        "--min-claim-safety", type=int, default=5,
        help="Minimum claim_safety score (0-5) required to accept "
             "the drafted caption (default: 5).",
    )

    reel_draft_parser = subparsers.add_parser("run-reel-draft", help="Draft and render one short vertical AION Reel.")
    reel_draft_parser.add_argument("--min-claim-safety", type=int, default=5)
    subparsers.add_parser("run-reel-publish", help="Publish the oldest rendered AION Reel.")

    subparsers.add_parser(
        "run-instagram-publish",
        help="Publish the oldest already-drafted-and-committed "
             "pending image to Instagram via the Graph API. Meant to "
             "run after run-instagram-draft's image has been pushed "
             "and had a moment to propagate on raw.githubusercontent.com.",
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

    if args.command == "run-learning-cycle":
        run_learning_cycle(args)
        return

    if args.command == "run-self-narrative":
        run_self_narrative(args)
        return

    if args.command == "run-reflection-cycle":
        run_reflection_cycle(args)
        return

    if args.command == "run-instagram-feedback":
        run_instagram_feedback(args)
        return

    if args.command == "export-obsidian-vault":
        run_export_obsidian_vault(args)
        return

    if args.command == "run-instagram-draft":
        run_instagram_draft(args)
        return

    if args.command == "run-instagram-publish":
        run_instagram_publish(args)
        return

    if args.command == "run-reel-draft":
        run_reel_draft(args)
        return

    if args.command == "run-reel-publish":
        run_reel_publish(args)
        return

    run_reflection()


if __name__ == "__main__":
    main()
