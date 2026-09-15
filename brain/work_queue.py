"""Durable, idempotent work cards for AION's real department hand-offs.

This is deliberately a coordination record, not a second scheduler.  Existing
workflows keep executing their specialist work; this ledger gives each handoff
a stable fingerprint so a later workflow can resume it instead of creating a
second copy of the same task.
"""

import hashlib
import json


class WorkQueue:
    CATEGORY = "company_work_queue"
    ACTIVE = {"planned", "in-progress", "ready", "waiting"}
    TERMINAL = {"completed", "cancelled", "blocked"}
    PRIORITIES = {"urgent", "normal", "background"}

    def __init__(self, memory):
        self.memory = memory

    @staticmethod
    def _payload(entry):
        try:
            value = json.loads(entry.get("content") or "{}")
        except (TypeError, ValueError):
            return None
        return value if isinstance(value, dict) else None

    @staticmethod
    def _fingerprint(lane, key):
        source = f"{str(lane).strip().lower()}::{str(key).strip().lower()}"
        return hashlib.sha256(source.encode("utf-8")).hexdigest()[:16]

    def cards(self):
        values = []
        for entry in self.memory.all(self.CATEGORY):
            payload = self._payload(entry)
            if payload and payload.get("task_id"):
                values.append({**payload, "memory_id": entry.get("id"), "timestamp": entry.get("timestamp")})
        return values

    def ensure(self, lane, key, owner, title, next_owner, status="planned", related=None, priority="normal"):
        """Create one card or return its existing active/terminal record.

        The caller supplies a domain-specific key (research-question id,
        episode id, or platform-content id).  Consequently retries are safe:
        they find the same card rather than duplicating the external action.
        """
        if status not in self.ACTIVE | self.TERMINAL:
            raise ValueError("Unknown work-card status.")
        if priority not in self.PRIORITIES:
            raise ValueError("Unknown work-card priority.")
        fingerprint = self._fingerprint(lane, key)
        existing = next((card for card in reversed(self.cards()) if card.get("fingerprint") == fingerprint), None)
        if existing:
            return {"created": False, "card": existing}
        card = {
            "version": 1,
            "task_id": f"{str(lane).strip()}-{fingerprint}",
            "fingerprint": fingerprint,
            "lane": str(lane).strip(),
            "owner": str(owner).strip(),
            "next_owner": str(next_owner).strip(),
            "title": str(title).strip(),
            "status": status,
            "priority": priority,
            "key": str(key).strip(),
        }
        saved = self.memory.remember(
            self.CATEGORY, json.dumps(card, ensure_ascii=False, sort_keys=True),
            memory_type="action", source="aion-work-queue", importance=4,
            tags=["work-card", card["lane"], card["status"]], related=list(related or []),
        )
        card["memory_id"] = saved.get("id")
        return {"created": bool(saved.get("saved")), "card": card}

    def transition(self, task_id, status, owner=None, next_owner=None, detail=None):
        """Advance one existing card, preserving a single auditable identity."""
        if status not in self.ACTIVE | self.TERMINAL:
            raise ValueError("Unknown work-card status.")
        card = next((item for item in reversed(self.cards()) if item.get("task_id") == task_id), None)
        if card is None:
            raise ValueError("Unknown work-card.")
        if card.get("status") in self.TERMINAL and card.get("status") != status:
            return {"changed": False, "card": card, "reason": "terminal-card"}
        updated = {key: value for key, value in card.items() if key not in {"memory_id", "timestamp"}}
        updated["status"] = status
        if owner:
            updated["owner"] = str(owner)
        if next_owner:
            updated["next_owner"] = str(next_owner)
        if detail:
            updated["detail"] = str(detail)
        self.memory.update(self.CATEGORY, card["memory_id"], json.dumps(updated, ensure_ascii=False, sort_keys=True))
        updated["memory_id"] = card["memory_id"]
        updated["timestamp"] = card.get("timestamp")
        return {"changed": True, "card": updated}

    def snapshot(self):
        cards = self.cards()
        latest = {}
        for card in cards:
            latest[card.get("fingerprint")] = card
        rank = {"urgent": 0, "normal": 1, "background": 2}
        values = sorted(latest.values(), key=lambda item: (rank.get(item.get("priority"), 1), item.get("timestamp", "")))
        return {
            "total": len(values),
            "active": [item for item in values if item.get("status") in self.ACTIVE],
            "completed": [item for item in values if item.get("status") == "completed"],
            "blocked": [item for item in values if item.get("status") == "blocked"],
        }
