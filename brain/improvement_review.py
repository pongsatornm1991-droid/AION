"""Human decision records for AION improvement proposals.

Approval here authorizes only a bounded content/process experiment. It never
executes code, changes credentials, spends money, or changes account settings.
"""

import json
import os
import uuid


class ImprovementReview:
    CATEGORY = "improvement_reviews"
    PROPOSAL_CATEGORIES = ("self_improvement", "evolution_proposals")
    # The owner has authorized bounded internal experiments to proceed without
    # a button.  This does not authorize source changes or external actions.
    AUTONOMOUS_INTERNAL_EXPERIMENTS = True

    def __init__(self, memory):
        self.memory = memory

    def _reviews(self):
        values = []
        for entry in self.memory.all(self.CATEGORY):
            try:
                data = json.loads(entry.get("content") or "{}")
            except (TypeError, ValueError):
                continue
            if data.get("review_id"):
                values.append({**data, "memory_id": entry.get("id")})
        return values

    def queue_once(self):
        reviewed = {item.get("proposal_id") for item in self._reviews()}
        candidates = []
        for category in self.PROPOSAL_CATEGORIES:
            for entry in self.memory.all(category):
                if entry.get("id") not in reviewed:
                    candidates.append((entry.get("timestamp", ""), category, entry))
        if not candidates:
            return {"stage": "no-new-proposal"}
        _, category, proposal = max(candidates)
        review = {
            "review_id": uuid.uuid4().hex[:12], "proposal_id": proposal["id"],
            "proposal_category": category,
            "status": "approved-for-experiment" if self.AUTONOMOUS_INTERNAL_EXPERIMENTS else "awaiting-owner",
            "proposal": str(proposal.get("content") or "")[:1800],
            "boundary": "Approval authorizes a bounded experiment only; it cannot change code, secrets, permissions, spending, or publish content.",
        }
        saved = self.memory.remember(self.CATEGORY, json.dumps(review, ensure_ascii=False, sort_keys=True),
                                     memory_type="decision", source="aion-improvement-review", importance=4,
                                     tags=["improvement-review", review["status"]], related=[proposal["id"]])
        review["memory_id"] = saved.get("id")
        return {"stage": review["status"], "review": review}

    def decide(self, review_id, approved, actor="owner"):
        review = next((item for item in self._reviews() if item["review_id"] == review_id), None)
        if not review:
            return {"stage": "unknown-review"}
        if review["status"] != "awaiting-owner":
            return {"stage": "already-decided", "review": review}
        updated = {**review, "status": "approved-for-experiment" if approved else "paused-by-owner", "decided_by": actor}
        self.memory.remember(self.CATEGORY, json.dumps(updated, ensure_ascii=False, sort_keys=True),
                             memory_type="decision", source="aion-improvement-review", importance=4,
                             tags=["improvement-review", updated["status"]], related=[review["proposal_id"], review["memory_id"]])
        return {"stage": updated["status"], "review": updated}

    def send_pending_once(self):
        """Start an internal experiment and leave its Thai report for the dashboard.

        Kept under the old method name so existing workflows remain compatible.
        There is deliberately no Telegram approval button in the autonomous
        policy: the record is still auditable, but no external change occurs.
        """
        queued = self.queue_once()
        if queued["stage"] != "approved-for-experiment":
            return queued
        from brain.experiment_runner import ExperimentRunner
        plan = ExperimentRunner(self.memory).queue_once()
        return {"stage": "experiment-queued", "review": queued["review"], "plan": plan}

    def send_legacy_pending_once(self):
        """Legacy explicit-button path retained only for a policy rollback."""
        queued = self.queue_once()
        if queued["stage"] != "awaiting-owner":
            return queued
        from tools.telegram import send_telegram_message_with_buttons
        review = queued["review"]
        text = "AION เสนอการทดลองพัฒนา\n\n" + review["proposal"] + "\n\n" + review["boundary"]
        send_telegram_message_with_buttons(text, [
            {"text": "อนุมัติทดลอง", "callback_data": f"improve:approve:{review['review_id']}"},
            {"text": "พักไว้", "callback_data": f"improve:pause:{review['review_id']}"},
        ])
        return queued

    def handle_updates_once(self, updates):
        """Apply only owner-chat button decisions; never execute a proposal."""
        expected_chat = str(os.getenv("TELEGRAM_CHAT_ID") or "")
        results = []
        for update in updates or []:
            callback = update.get("callback_query") or {}
            data = str(callback.get("data") or "")
            parts = data.split(":")
            if len(parts) != 3 or parts[0] != "improve" or parts[1] not in {"approve", "pause"}:
                continue
            chat_id = str(((callback.get("message") or {}).get("chat") or {}).get("id") or "")
            if not expected_chat or chat_id != expected_chat:
                results.append({"stage": "unauthorized-callback"})
                continue
            result = self.decide(parts[2], parts[1] == "approve", actor="telegram-owner")
            try:
                from tools.telegram import answer_telegram_callback
                answer_telegram_callback(callback.get("id"), "บันทึกการตัดสินใจแล้ว")
            except Exception:
                pass
            results.append(result)
        return results
