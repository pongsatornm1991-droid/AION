"""Telegram notification wrapper -- lets AION tell the user, in near
real time, what it drafted or decided (a Facebook post it's about to
send, one it blocked at the safety gate, one it actually posted),
without requiring the user to run a CLI command to find out.

This is deliberately NOT gated through brain/tools.py's
ToolLifecycle: it is not an independent action AION decides to take on
its own initiative, but an automatic echo of something that already
happened (or was already decided) through a path that -- when it is a
real post -- already went through the full propose/approve/execute
lifecycle. Treat it the same as printing a report to the console: it
observes and reports, it never causes AION to do anything it wasn't
already going to do.

Credentials are never hardcoded and never committed: both the bot
token and the target chat id are read from environment variables
(TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID), loaded via .env exactly like
FACEBOOK_PAGE_ACCESS_TOKEN elsewhere in this project. `requests` is
imported lazily, matching tools/facebook.py's pattern.
"""

import os

from dotenv import load_dotenv

TELEGRAM_API_BASE = "https://api.telegram.org"


def send_telegram_message(text, bot_token=None, chat_id=None):
    """Send one text message to a Telegram chat via a bot.

    Returns the Telegram API's own response payload on success. Raises
    RuntimeError with the API's own error description on failure --
    never retries internally, matching post_to_facebook_page's
    discipline: a failure here is meant to be surfaced to whoever
    called it, not silently swallowed or retried.
    """

    text = str(text).strip()

    if not text:
        raise ValueError("text cannot be empty.")

    load_dotenv()

    bot_token = bot_token or os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = chat_id or os.getenv("TELEGRAM_CHAT_ID")

    if not bot_token:
        raise RuntimeError(
            "TELEGRAM_BOT_TOKEN is not configured. Add it to the .env "
            "file (see .env.example)."
        )

    if not chat_id:
        raise RuntimeError(
            "TELEGRAM_CHAT_ID is not configured. Add it to the .env "
            "file (see .env.example)."
        )

    import requests  # lazy: only needed when this actually runs

    url = f"{TELEGRAM_API_BASE}/bot{bot_token}/sendMessage"

    response = requests.post(
        url,
        data={"chat_id": chat_id, "text": text},
        timeout=15,
    )

    try:
        payload = response.json()
    except ValueError:
        payload = {}

    if response.status_code >= 400 or not payload.get("ok", False):
        raise RuntimeError(
            "Telegram API error: "
            f"{payload.get('description') or f'HTTP {response.status_code}'}"
        )

    return payload
