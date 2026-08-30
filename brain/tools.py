"""Controlled tools and lifecycle.

This is the plumbing the next phase ("External integration") will plug
real tools into -- not the tools themselves. Only genuinely read-only,
already-existing introspection is wired up as real tools right now
(see build_builtin_tools()); nothing here pretends AION can already
send a message, post something, or touch the outside world, because it
can't yet. Building the safety machinery before there is anything
dangerous to run through it is the point: "read-only research first"
from the roadmap.

Every action goes through the same append-only, evidence-respecting
discipline as the rest of this codebase: propose -> (approve or
reject) -> execute (-> recover if it failed) or abandon. Nothing is
ever edited in place; each step writes a new entry superseding the
last, so the full lifecycle of every attempted action stays on disk.

Four independent safeguards, all enforced in code, none overridable by
anything an AI provider says:
- Action levels: READ_ONLY needs no approval at all; LOW_RISK can be
  approved by AION itself; HIGH_RISK can only ever be approved by
  someone who is not AION -- enforced in approve(), not by convention.
- A kill switch: when engaged, execute() refuses everything, no
  exceptions, checked before anything else.
- Budgets: a rolling-window cap on how many LOW_RISK/HIGH_RISK actions
  may actually run (READ_ONLY is unlimited, since it has no side
  effects to bound).
- Scheduling: a proposed action can carry a future ScheduledFor time;
  execute() refuses to run it early.
"""

import json
import uuid
from datetime import datetime, timedelta


class ActionLevel:
    """Ordered from safest to most dangerous. Higher levels require
    strictly more safeguards before AION may execute them."""

    READ_ONLY = "READ_ONLY"
    LOW_RISK = "LOW_RISK"
    HIGH_RISK = "HIGH_RISK"
    # Changes to AION's own presented identity (Facebook Page bio,
    # profile photo, etc.) -- kept as its OWN level, distinct from
    # HIGH_RISK, on purpose: HIGH_RISK covers routine public content
    # (posts, comment replies) and its budget is meant to flex with
    # how much AION is actually talking to people; identity changes
    # are rarer and more sensitive by nature (they change how AION
    # presents *itself*, not just what it says), so they get their
    # own small budget that loosening HIGH_RISK's never touches, and
    # the exact same self-approval ban as HIGH_RISK below.
    IDENTITY_CHANGE = "IDENTITY_CHANGE"


ACTION_LEVELS = {
    ActionLevel.READ_ONLY,
    ActionLevel.LOW_RISK,
    ActionLevel.HIGH_RISK,
    ActionLevel.IDENTITY_CHANGE,
}

# Levels that can never be self-approved by AION -- always require a
# real person's approval. HIGH_RISK and IDENTITY_CHANGE are both
# publicly-visible-or-identity-altering and irreversible-in-practice,
# so both live here.
_NEVER_SELF_APPROVE = {ActionLevel.HIGH_RISK, ActionLevel.IDENTITY_CHANGE}

_KILL_SWITCH_TOOL_NAME = "__kill_switch__"


class ToolRegistry:
    """A name -> (callable, level, description) lookup. Deliberately
    dumb: it does not run anything, decide anything, or know about
    memory at all -- it is just the list of what AION is currently
    allowed to even attempt, and at what risk level."""

    def __init__(self):
        self._tools = {}

    def register(self, name, func, level, description=""):
        name = str(name).strip()

        if not name:
            raise ValueError("Tool name cannot be empty.")

        if name == _KILL_SWITCH_TOOL_NAME:
            raise ValueError(f"'{_KILL_SWITCH_TOOL_NAME}' is a reserved name.")

        if name in self._tools:
            raise ValueError(f"Tool '{name}' is already registered.")

        if level not in ACTION_LEVELS:
            raise ValueError(f"Unknown action level: {level}")

        if not callable(func):
            raise TypeError("func must be callable.")

        self._tools[name] = {
            "name": name,
            "func": func,
            "level": level,
            "description": description,
        }

    def get(self, name):
        return self._tools.get(name)

    def list_tools(self):
        return [
            {"name": spec["name"], "level": spec["level"], "description": spec["description"]}
            for spec in self._tools.values()
        ]


def build_builtin_tools(memory):
    """The only tools wired up for real right now: read-only
    introspection over AION's own memory, using primitives that
    already exist (MemoryEngine.stats/quality_report,
    MetacognitionEngine.*_report). Nothing here has a side effect
    outside of reading what's already on disk."""

    from .metacognition import MetacognitionEngine

    registry = ToolRegistry()
    meta = MetacognitionEngine(memory)

    registry.register(
        "memory_stats",
        lambda category: memory.stats(category),
        ActionLevel.READ_ONLY,
        "Entry counts and importance/type breakdown for one memory category.",
    )
    registry.register(
        "quality_report",
        lambda category: memory.quality_report(category),
        ActionLevel.READ_ONLY,
        "Quality statistics for one memory category.",
    )
    registry.register(
        "metacognition_report",
        lambda report="full": {
            "calibration": meta.calibration_report,
            "recurring-errors": meta.recurring_error_report,
            "memory-quality": meta.memory_quality_overview,
            "full": meta.full_report,
        }[report](),
        ActionLevel.READ_ONLY,
        "One of MetacognitionEngine's reports (calibration, "
        "recurring-errors, memory-quality, or full).",
    )

    return registry


class ToolLifecycle:
    """Manages the propose -> approve/reject -> execute -> recover/
    abandon lifecycle for every action AION attempts through a
    registered tool, plus the kill switch that can halt all of it."""

    CATEGORY = "actions"
    MEMORY_TYPE = "action"

    DEFAULT_BUDGETS = {
        ActionLevel.READ_ONLY: None,  # unlimited: no side effects to bound
        ActionLevel.LOW_RISK: 20,
        # Shared by post_to_facebook and reply_to_facebook_comment.
        # Raised from an earlier, much stricter 5/24h (2026-08-30, at
        # the user's explicit request: AION's engagement shouldn't be
        # artificially capped far below what Gemini's free tier or
        # Facebook's own API can actually sustain -- "mind the real
        # quota, don't invent a tighter one"). 30/24h is still a real
        # ceiling, not "unlimited": a budget that can never be hit
        # stops being a safety control at all, and a shared pool
        # across posting and replying still guards against either one
        # silently flooding the Page if something goes wrong upstream
        # (e.g. a seed/prompt bug that makes every draft pass the
        # safety gate). Raise further if 30/day is ever actually hit.
        ActionLevel.HIGH_RISK: 30,
        # Deliberately small and separate from HIGH_RISK -- see
        # ActionLevel.IDENTITY_CHANGE's docstring. Changing AION's own
        # bio/photo more than twice a day would almost certainly mean
        # something is wrong (a loop, a bad prompt), not real intent.
        ActionLevel.IDENTITY_CHANGE: 2,
    }
    DEFAULT_BUDGET_WINDOW_HOURS = 24

    def __init__(
        self,
        memory,
        registry=None,
        budgets=None,
        budget_window_hours=None,
        category=None,
    ):
        self.memory = memory
        self.registry = registry or ToolRegistry()
        self.budgets = {**self.DEFAULT_BUDGETS, **(budgets or {})}
        self.budget_window_hours = (
            budget_window_hours or self.DEFAULT_BUDGET_WINDOW_HOURS
        )
        self.category = category or self.CATEGORY

    # ---------------------------------------------------------
    # KILL SWITCH
    # ---------------------------------------------------------

    def engage_kill_switch(self, reason):
        return self._set_kill_switch("engaged", reason)

    def disengage_kill_switch(self, reason):
        return self._set_kill_switch("disengaged", reason)

    def kill_switch_engaged(self):
        latest = None

        for entry in self.memory.all(self.category):
            if entry["type"] != self.MEMORY_TYPE:
                continue
            parsed = self._parse_content(entry["content"])
            if parsed["tool"] == _KILL_SWITCH_TOOL_NAME:
                latest = parsed

        return latest is not None and latest["status"] == "engaged"

    def _set_kill_switch(self, status, reason):
        reason = str(reason).strip()

        if not reason:
            raise ValueError("A reason is required to change the kill switch.")

        content = self._format_content(
            tool=_KILL_SWITCH_TOOL_NAME,
            params={"reason": reason},
            level=ActionLevel.HIGH_RISK,
            status=status,
            predecessor=None,
            scheduled_for=None,
            approver=None,
            result=None,
            error=None,
            resolution=None,
            evidence=[],
        )

        saved = self.memory.remember(
            category=self.category,
            content=content,
            memory_type=self.MEMORY_TYPE,
            source="kill-switch",
            importance=5,
        )

        return {**saved, **self._parse_content(content)}

    # ---------------------------------------------------------
    # PROPOSE
    # ---------------------------------------------------------

    def propose(self, tool_name, params=None, scheduled_for=None, source="aion"):
        tool_name = str(tool_name).strip()

        if not tool_name:
            raise ValueError("Tool name cannot be empty.")

        spec = self.registry.get(tool_name)

        if spec is None:
            raise ValueError(f"No tool named '{tool_name}' is registered.")

        params = dict(params or {})
        scheduled_for = self._normalize_schedule(scheduled_for)

        content = self._format_content(
            tool=tool_name,
            params=params,
            level=spec["level"],
            status="proposed",
            predecessor=None,
            scheduled_for=scheduled_for,
            approver=None,
            result=None,
            error=None,
            resolution=None,
            evidence=[],
        )

        saved = self.memory.remember(
            category=self.category,
            content=content,
            memory_type=self.MEMORY_TYPE,
            source=source,
            importance=self._level_to_importance(spec["level"]),
        )

        return {**saved, **self._parse_content(content)}

    # ---------------------------------------------------------
    # APPROVE / REJECT
    # ---------------------------------------------------------

    def approve(self, entry_id, approver):
        approver = str(approver).strip()

        if not approver:
            raise ValueError("An approver name is required.")

        current, parsed = self._get_parsed(entry_id)

        if parsed["status"] != "proposed":
            raise ValueError(
                f"Cannot approve an action that is {parsed['status']}."
            )

        if parsed["level"] in _NEVER_SELF_APPROVE and approver.lower() == "aion":
            raise ValueError(
                f"{parsed['level']} actions can never be self-approved by "
                "AION -- they require an approver who is not AION."
            )

        return self._supersede(
            entry_id, current, parsed, status="approved", approver=approver
        )

    def reject(self, entry_id, reason, rejector):
        reason = str(reason).strip()

        if not reason:
            raise ValueError("A reason is required to reject an action.")

        current, parsed = self._get_parsed(entry_id)

        if parsed["status"] != "proposed":
            raise ValueError(
                f"Cannot reject an action that is {parsed['status']}."
            )

        saved = self._supersede(
            entry_id, current, parsed, status="rejected", approver=rejector,
        )

        self.memory.remember(
            category="lessons",
            content=f"Rejected action '{entry_id}' ({parsed['tool']}): {reason}",
            memory_type="lesson",
            source="action-rejection",
            importance=current["importance"],
            related=[entry_id],
        )

        return saved

    # ---------------------------------------------------------
    # EXECUTE
    # ---------------------------------------------------------

    def execute(self, entry_id):
        if self.kill_switch_engaged():
            raise RuntimeError(
                "The kill switch is engaged -- no action may execute."
            )

        current, parsed = self._get_parsed(entry_id)
        level = parsed["level"]

        if level == ActionLevel.READ_ONLY:
            # READ_ONLY needs no approval, but approving one first is
            # harmless -- both states are acceptable here.
            if parsed["status"] not in ("proposed", "approved"):
                raise ValueError(
                    f"Cannot execute a READ_ONLY action that is {parsed['status']}."
                )
        else:
            if parsed["status"] != "approved":
                raise ValueError(
                    f"Cannot execute a {level} action that is "
                    f"{parsed['status']} (it must be approved first)."
                )

        if parsed["scheduled_for"] is not None:
            scheduled_for = datetime.fromisoformat(parsed["scheduled_for"])
            if datetime.now() < scheduled_for:
                raise ValueError(
                    f"This action is not due until {parsed['scheduled_for']}."
                )

        if level != ActionLevel.READ_ONLY:
            self._check_budget(level)

        spec = self.registry.get(parsed["tool"])

        if spec is None:
            raise ValueError(
                f"No tool named '{parsed['tool']}' is currently registered."
            )

        try:
            result = spec["func"](**parsed["params"])
        except Exception as exc:  # noqa: BLE001 -- deliberately broad: any
            # tool failure must be captured as a "failed" record, never
            # allowed to propagate and skip the audit trail.
            return self._supersede(
                entry_id, current, parsed, status="failed", error=str(exc),
            )

        return self._supersede(
            entry_id, current, parsed, status="executed",
            result=self._stringify_result(result),
        )

    # ---------------------------------------------------------
    # RECOVER / ABANDON
    # ---------------------------------------------------------

    def recover(self, entry_id, resolution, evidence):
        resolution = str(resolution).strip()

        if not resolution:
            raise ValueError("A resolution is required to recover a failed action.")

        evidence = list(evidence or [])

        if not evidence:
            raise ValueError(
                "Recovering a failed action requires at least one piece "
                "of supporting evidence."
            )

        current, parsed = self._get_parsed(entry_id)

        if parsed["status"] != "failed":
            raise ValueError(
                f"Cannot recover an action that is {parsed['status']} "
                "(it must have failed first)."
            )

        related = self._evidence_ids(evidence)
        if entry_id not in related:
            related.append(entry_id)

        return self._supersede(
            entry_id, current, parsed, status="recovered",
            resolution=resolution, evidence=evidence, related=related,
        )

    def abandon(self, entry_id, reason):
        reason = str(reason).strip()

        if not reason:
            raise ValueError("A reason is required to abandon an action.")

        current, parsed = self._get_parsed(entry_id)

        if parsed["status"] not in ("proposed", "approved", "failed"):
            raise ValueError(
                f"Cannot abandon an action that is {parsed['status']}."
            )

        saved = self._supersede(entry_id, current, parsed, status="abandoned")

        self.memory.remember(
            category="lessons",
            content=f"Abandoned action '{entry_id}' ({parsed['tool']}): {reason}",
            memory_type="lesson",
            source="action-abandonment",
            importance=current["importance"],
            related=[entry_id],
        )

        return saved

    # ---------------------------------------------------------
    # QUERY
    # ---------------------------------------------------------

    def status_of(self, entry):
        return self._parse_content(entry["content"])["status"]

    def _latest_entries(self):
        results = []

        for entry in self.memory.all(self.category):
            if entry["type"] != self.MEMORY_TYPE:
                continue
            tags = [tag.lower() for tag in entry.get("tags", [])]
            if "superseded" in tags:
                continue
            parsed = self._parse_content(entry["content"])
            if parsed["tool"] == _KILL_SWITCH_TOOL_NAME:
                continue
            results.append({**entry, **parsed})

        return results

    def actions(self, status=None, limit=None):
        results = self._latest_entries()

        if status is not None:
            results = [entry for entry in results if entry["status"] == status]

        results.sort(key=lambda entry: entry["timestamp"], reverse=True)

        if limit is not None:
            results = results[:limit]

        return results

    def history(self, entry_id):
        by_id = {
            entry["id"]: entry
            for entry in self.memory.all(self.category)
            if entry["type"] == self.MEMORY_TYPE
        }

        if entry_id not in by_id:
            raise ValueError("No action matches the supplied id.")

        chain = []
        seen = set()
        current = by_id.get(entry_id)

        while current is not None and current["id"] not in seen:
            seen.add(current["id"])
            parsed = self._parse_content(current["content"])
            chain.append({**current, **parsed})

            predecessor_id = parsed.get("predecessor")
            current = by_id.get(predecessor_id) if predecessor_id else None

        chain.reverse()

        return chain

    # ---------------------------------------------------------
    # INTERNAL HELPERS
    # ---------------------------------------------------------

    def _get(self, entry_id):
        for entry in self.memory.all(self.category):
            if entry["id"] == entry_id:
                return entry
        return None

    def _get_parsed(self, entry_id):
        current = self._get(entry_id)

        if current is None:
            raise ValueError("No action matches the supplied id.")

        return current, self._parse_content(current["content"])

    def _supersede(
        self,
        entry_id,
        current,
        parsed,
        status,
        approver=None,
        result=None,
        error=None,
        resolution=None,
        evidence=None,
        related=None,
    ):
        content = self._format_content(
            tool=parsed["tool"],
            params=parsed["params"],
            level=parsed["level"],
            status=status,
            predecessor=entry_id,
            scheduled_for=parsed["scheduled_for"],
            approver=approver if approver is not None else parsed["approver"],
            result=result if result is not None else parsed["result"],
            error=error if error is not None else parsed["error"],
            resolution=resolution if resolution is not None else parsed["resolution"],
            evidence=evidence if evidence is not None else parsed["evidence"],
        )

        saved = self.memory.remember(
            category=self.category,
            content=content,
            memory_type=self.MEMORY_TYPE,
            source=current.get("source", "aion"),
            importance=current["importance"],
            tags=current.get("tags", []),
            related=related,
        )

        self.memory.add_tags(self.category, entry_id, ["superseded"])

        return {**saved, **self._parse_content(content)}

    def _check_budget(self, level):
        budget = self.budgets.get(level)

        if budget is None:
            return

        window_start = datetime.now() - timedelta(hours=self.budget_window_hours)
        count = 0

        for entry in self.memory.all(self.category):
            if entry["type"] != self.MEMORY_TYPE:
                continue

            parsed = self._parse_content(entry["content"])

            if parsed["tool"] == _KILL_SWITCH_TOOL_NAME:
                continue
            if parsed["level"] != level:
                continue
            if parsed["status"] not in ("executed", "failed"):
                continue

            timestamp = datetime.strptime(entry["timestamp"], "%Y-%m-%d %H:%M:%S")
            if timestamp >= window_start:
                count += 1

        if count >= budget:
            raise ValueError(
                f"Budget exceeded for {level}: {count}/{budget} actions "
                f"already executed in the last {self.budget_window_hours}h."
            )

    @staticmethod
    def _normalize_schedule(scheduled_for):
        if scheduled_for is None:
            return None

        if isinstance(scheduled_for, str):
            # Validate it parses; raises ValueError on malformed input.
            datetime.fromisoformat(scheduled_for)
            return scheduled_for

        if isinstance(scheduled_for, datetime):
            return scheduled_for.isoformat(sep=" ", timespec="seconds")

        raise TypeError("scheduled_for must be a datetime, an ISO string, or None.")

    @staticmethod
    def _level_to_importance(level):
        return {
            ActionLevel.READ_ONLY: 1,
            ActionLevel.LOW_RISK: 3,
            ActionLevel.HIGH_RISK: 5,
            ActionLevel.IDENTITY_CHANGE: 5,
        }[level]

    @staticmethod
    def _stringify_result(result):
        try:
            return json.dumps(result)
        except TypeError:
            return str(result)

    @staticmethod
    def _evidence_ids(evidence):
        ids = []

        for item in evidence:
            if isinstance(item, dict) and item.get("id"):
                entry_id = str(item["id"]).strip()
                if entry_id and entry_id not in ids:
                    ids.append(entry_id)

        return ids

    @classmethod
    def _format_evidence_line(cls, item):
        if isinstance(item, dict):
            description = str(item.get("description", "")).strip()
            entry_id = item.get("id")

            if entry_id:
                return f"- {description} (id: {entry_id})"

            return f"- {description}"

        return f"- {str(item).strip()}"

    @classmethod
    def _format_content(
        cls,
        tool,
        params,
        level,
        status,
        predecessor,
        scheduled_for,
        approver,
        result,
        error,
        resolution,
        evidence,
    ):
        try:
            params_text = json.dumps(params, sort_keys=True)
        except TypeError:
            params_text = str(params)

        lines = [
            # MemoryEngine.is_duplicate() compares normalized content
            # regardless of when it was written, so two calls that
            # would otherwise produce byte-identical content (e.g.
            # proposing the same tool with the same params twice, or
            # engaging the kill switch with the same reason text
            # twice) must be distinguished here, or the second one is
            # silently dropped as a duplicate.
            f"Nonce: {uuid.uuid4().hex[:8]}",
            f"Tool: {tool}",
            f"Params: {params_text}",
            f"Level: {level}",
            f"Status: {status}",
            f"Predecessor: {predecessor or 'none'}",
            f"ScheduledFor: {scheduled_for or 'none'}",
            f"Approver: {approver or 'none'}",
            f"Result: {result or 'none'}",
            f"Error: {error or 'none'}",
            f"Resolution: {resolution or 'none'}",
            "",
            "Evidence:",
        ]

        evidence_lines = [
            cls._format_evidence_line(item) for item in (evidence or [])
        ] or ["- None"]
        lines.extend(evidence_lines)

        return "\n".join(lines)

    @classmethod
    def _parse_content(cls, content):
        fields = {
            "tool": "",
            "params": {},
            "level": None,
            "status": "proposed",
            "predecessor": None,
            "scheduled_for": None,
            "approver": None,
            "result": None,
            "error": None,
            "resolution": None,
            "evidence": [],
        }

        current_section = None

        for raw_line in content.splitlines():
            line = raw_line.strip()

            if not line:
                continue

            if line.startswith("Nonce:"):
                current_section = None

            elif line.startswith("Tool:"):
                fields["tool"] = line[len("Tool:"):].strip()
                current_section = None

            elif line.startswith("Params:"):
                raw_params = line[len("Params:"):].strip()
                try:
                    fields["params"] = json.loads(raw_params)
                except (ValueError, TypeError):
                    fields["params"] = {}
                current_section = None

            elif line.startswith("Level:"):
                fields["level"] = line[len("Level:"):].strip()
                current_section = None

            elif line.startswith("Status:"):
                fields["status"] = line[len("Status:"):].strip()
                current_section = None

            elif line.startswith("Predecessor:"):
                value = line[len("Predecessor:"):].strip()
                fields["predecessor"] = None if value.lower() == "none" else value
                current_section = None

            elif line.startswith("ScheduledFor:"):
                value = line[len("ScheduledFor:"):].strip()
                fields["scheduled_for"] = None if value.lower() == "none" else value
                current_section = None

            elif line.startswith("Approver:"):
                value = line[len("Approver:"):].strip()
                fields["approver"] = None if value.lower() == "none" else value
                current_section = None

            elif line.startswith("Result:"):
                value = line[len("Result:"):].strip()
                fields["result"] = None if value.lower() == "none" else value
                current_section = None

            elif line.startswith("Error:"):
                value = line[len("Error:"):].strip()
                fields["error"] = None if value.lower() == "none" else value
                current_section = None

            elif line.startswith("Resolution:"):
                value = line[len("Resolution:"):].strip()
                fields["resolution"] = None if value.lower() == "none" else value
                current_section = None

            elif line == "Evidence:":
                current_section = "evidence"

            elif current_section == "evidence" and line.startswith("- "):
                raw_item = line[2:].strip()

                if raw_item == "None":
                    continue

                if raw_item.endswith(")") and " (id: " in raw_item:
                    description, _, rest = raw_item.rpartition(" (id: ")
                    fields["evidence"].append({
                        "description": description.strip(),
                        "id": rest[:-1].strip(),
                    })
                else:
                    fields["evidence"].append(
                        {"description": raw_item, "id": None}
                    )

        return fields
