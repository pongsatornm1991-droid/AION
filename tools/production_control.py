"""Write a read-only public production-control report for the dashboard."""
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from brain.production_control import ProductionControl


def _notify_integrity_alerts(integrity):
    """Best-effort Telegram push for a SystemIntegrity finding.

    A dashboard only helps if someone opens it. The class of bug this
    guards against (2026-09-25: an expired YouTube OAuth token silently
    failing every publish for 5+ days) was never actually invisible -- it
    was sitting in a JSON file nobody was looking at. This runs hourly
    alongside the rest of production control specifically so a critical or
    warning finding reaches Telegram instead of waiting to be noticed.
    Never raises: notification is supplementary, not a requirement for the
    report itself to be written.
    """
    alerts = integrity.get("alerts") or []
    if not alerts or not os.getenv("TELEGRAM_BOT_TOKEN") or not os.getenv("TELEGRAM_CHAT_ID"):
        return
    lines = ["AION production-control integrity alert:"]
    for alert in alerts:
        lines.append(f"[{alert['severity']}] {alert['check']}: {alert['detail']}")
    try:
        from tools.telegram import send_telegram_message
        send_telegram_message("\n".join(lines))
    except Exception as exc:  # pragma: no cover - best-effort notifier
        print(f"(Telegram integrity notification failed: {exc})")


def main():
    report = ProductionControl(ROOT).snapshot()
    path = ROOT / "public" / "aion-production-control.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    _notify_integrity_alerts(report.get("integrity") or {})
    print(json.dumps({"state": report["state"], "path": str(path)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
