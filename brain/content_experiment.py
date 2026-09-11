"""Assign approved content experiments and evaluate only attributed outcomes."""

import json


class ContentExperimentExecutor:
    ASSIGNMENTS = "content_experiment_assignments"
    RESULTS = "content_experiment_results"

    def __init__(self, memory):
        self.memory = memory

    def _plans(self):
        plans = []
        for entry in self.memory.all("content_experiment_plans"):
            try:
                value = json.loads(entry.get("content") or "{}")
            except (TypeError, ValueError):
                continue
            if value.get("review_id") and value.get("status") in {"queued", "active"}:
                plans.append({**value, "memory_id": entry.get("id")})
        return plans

    def assign_next(self, content_id):
        plan = next(iter(self._plans()), None)
        if not plan:
            return None
        assigned = []
        for entry in self.memory.all(self.ASSIGNMENTS):
            try:
                value = json.loads(entry.get("content") or "{}")
            except (TypeError, ValueError):
                continue
            if value.get("review_id") == plan["review_id"]:
                assigned.append(value)
        if len(assigned) >= int(plan.get("sample_size", 4)):
            return None
        assignment = {"review_id": plan["review_id"], "content_id": content_id,
                      "variant": "control" if len(assigned) % 2 == 0 else "experiment",
                      "sequence": len(assigned) + 1}
        self.memory.remember(self.ASSIGNMENTS, json.dumps(assignment, ensure_ascii=False, sort_keys=True),
                             memory_type="experiment", source="aion-content-experiment", importance=3,
                             tags=["content-experiment", assignment["variant"], plan["review_id"]], related=[plan["memory_id"]])
        return assignment

    def evaluate_once(self):
        completed = set()
        for entry in self.memory.all(self.RESULTS):
            try:
                completed.add(json.loads(entry.get("content") or "{}").get("review_id"))
            except (TypeError, ValueError):
                continue
        for plan in self._plans():
            if plan["review_id"] in completed:
                continue
            assignments = []
            for entry in self.memory.all(self.ASSIGNMENTS):
                try:
                    value = json.loads(entry.get("content") or "{}")
                except (TypeError, ValueError):
                    continue
                if value.get("review_id") == plan["review_id"]:
                    assignments.append(value)
            attribution = {}
            for entry in self.memory.all("content_attribution"):
                try:
                    value = json.loads(entry.get("content") or "{}")
                except (TypeError, ValueError):
                    continue
                attribution[value.get("content_id")] = value
            scored = [item for item in assignments if item.get("content_id") in attribution]
            if len(scored) < int(plan.get("sample_size", 4)):
                return {"stage": "waiting-for-attributed-outcomes", "observed": len(scored), "required": plan.get("sample_size", 4)}
            scores = {"control": [], "experiment": []}
            for item in scored:
                metric = attribution[item["content_id"]]
                scores[item["variant"]].append(int(metric.get("like_count") or 0) + 3 * int(metric.get("comments_count") or 0))
            if not scores["control"] or not scores["experiment"]:
                return {"stage": "waiting-for-balanced-outcomes"}
            averages = {key: sum(values) / len(values) for key, values in scores.items()}
            conclusion = "keep-testing" if averages["experiment"] > averages["control"] else "revise-or-stop"
            result = {"review_id": plan["review_id"], "status": "evaluated", "averages": averages,
                      "conclusion": conclusion, "uncertainty": "Small sample; this is a directional signal, not proof of causation."}
            self.memory.remember(self.RESULTS, json.dumps(result, ensure_ascii=False, sort_keys=True),
                                 memory_type="lesson", source="aion-content-experiment", importance=4,
                                 tags=["content-experiment", conclusion], related=[plan["memory_id"]])
            # A finished experiment must leave the active queue.  The durable
            # plan remains in memory as an audit trail, but its own state is
            # updated so dashboards and future cycles cannot call it pending.
            completed_plan = {key: value for key, value in plan.items() if key != "memory_id"}
            completed_plan["status"] = "evaluated"
            self.memory.update(
                "content_experiment_plans", plan["memory_id"],
                content=json.dumps(completed_plan, ensure_ascii=False, sort_keys=True),
            )
            return {"stage": "evaluated", "result": result}
        return {"stage": "no-active-experiment"}
