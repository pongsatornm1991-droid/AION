"""Safety-gated, durable direct-message reply cycle for Meta inboxes."""

import os


class DirectMessageCycle:
    CATEGORY = "direct_message_replies"

    def __init__(self, memory, generator, lifecycle, tool_name, platform):
        self.memory = memory
        self.generator = generator
        self.lifecycle = lifecycle
        self.tool_name = tool_name
        self.platform = platform

    def _seen(self):
        prefix = f"{self.platform}-dm:"
        return {
            tag[len(prefix):]
            for entry in self.memory.all(self.CATEGORY)
            for tag in (entry.get("tags") or []) if tag.startswith(prefix)
        }

    def _record(self, item, stage, detail):
        self.memory.remember(
            self.CATEGORY, f"[{stage}] {self.platform} message: {detail}",
            memory_type="action", source="direct-message-reply", importance=2,
            tags=[f"{self.platform}-dm:{item.get('id')}", self.platform],
        )

    def run_once(self, messages=None):
        if os.getenv("AION_MESSAGING_ENABLED", "false").lower() not in ("1", "true", "yes"):
            return {"handled": False, "stage": "permission-pending", "platform": self.platform}
        try:
            if messages is None:
                from tools.meta_messaging import get_recent_messages
                messages = get_recent_messages(self.platform)
        except Exception as exc:
            return {"handled": False, "stage": "fetch-failed", "error": str(exc)}
        seen = self._seen()
        candidates = [m for m in messages if m.get("id") not in seen and (m.get("message") or "").strip()]
        if not candidates:
            return {"handled": False, "stage": "no-messages", "platform": self.platform}
        item = sorted(candidates, key=lambda x: x.get("created_time") or "")[0]
        item = {**item, "platform": self.platform}
        try:
            draft = self.generator.draft_reply(item, style_notes=[])
        except Exception as exc:
            return {"handled": False, "stage": "draft-failed", "error": str(exc), "message": item}
        if not draft["safe"]:
            self._record(item, "blocked", draft.get("reason"))
            return {"handled": False, "stage": "blocked", "message": item, **draft}
        try:
            action = self.lifecycle.propose(
                self.tool_name,
                params={"recipient_id": item["recipient_id"], "message": draft["draft"]},
                source="aion",
            )
            action = self.lifecycle.auto_approve(action["id"], policy="message-safety-style-gate")
            action = self.lifecycle.execute(action["id"])
        except Exception as exc:
            self._record(item, "failed", str(exc))
            return {"handled": False, "stage": "lifecycle", "error": str(exc), "message": item}
        handled = action.get("status") == "executed"
        self._record(item, "executed" if handled else "failed", draft["draft"])
        return {"handled": handled, "stage": "executed" if handled else "failed",
                "message": item, "draft": draft["draft"], "action": action}
