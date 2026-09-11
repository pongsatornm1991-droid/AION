"""Convert an owner-approved improvement proposal into a bounded plan."""

import json


class ExperimentRunner:
    CATEGORY = "content_experiment_plans"

    def __init__(self, memory):
        self.memory = memory

    def _approved_reviews(self):
        items = []
        for entry in self.memory.all("improvement_reviews"):
            try:
                value = json.loads(entry.get("content") or "{}")
            except (TypeError, ValueError):
                continue
            if value.get("status") == "approved-for-experiment" and value.get("review_id"):
                items.append(value)
        return items

    def queue_once(self):
        existing = set()
        for entry in self.memory.all(self.CATEGORY):
            try:
                existing.add(json.loads(entry.get("content") or "{}").get("review_id"))
            except (TypeError, ValueError):
                continue
        review = next((item for item in self._approved_reviews() if item["review_id"] not in existing), None)
        if not review:
            return {"stage": "no-approved-proposal"}
        plan = {
            "review_id": review["review_id"], "proposal_id": review["proposal_id"],
            "status": "queued", "sample_size": 4,
            "method": "Use the approved content/process change for four comparable future pieces; preserve safety, evidence, and audience value.",
            "success_signal": "Compare response only after at least four attributed outcomes; do not claim a winner from a single post.",
            "stop_rule": "Stop if a safety gate blocks the change, quality declines, or the owner pauses the experiment.",
        }
        saved = self.memory.remember(self.CATEGORY, json.dumps(plan, ensure_ascii=False, sort_keys=True),
                                     memory_type="experiment", source="aion-experiment-runner", importance=4,
                                     tags=["content-experiment", "queued", f"review:{review['review_id']}"], related=[review["proposal_id"]])
        return {"stage": "queued", "plan": plan, "id": saved.get("id")}
