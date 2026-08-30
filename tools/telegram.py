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


def _telegram_error(payload, status_code):
    return RuntimeError(
        "Telegram API error: "
        f"{payload.get('description') or f'HTTP {status_code}'}"
    )


def send_telegram_message_with_buttons(text, buttons, bot_token=None, chat_id=None):
    """Send one text message with an inline keyboard attached -- the
    Phase 12 mechanism for asking the user, via Telegram, to approve
    or reject one AION-drafted identity change (Facebook Page bio,
    in the first version), without them needing to run a CLI command.

    `buttons`: a list of {"text": <label>, "callback_data": <data>}
    dicts, one inline button per entry, all on a single row -- this
    module never needs more than "Approve"/"Reject" at once. Returns
    the Telegram API's own response payload (contains the sent
    message's id, needed by nothing here but returned for
    completeness). Raises RuntimeError on failure, never retries
    internally -- same discipline as send_telegram_message.
    """

    text = str(text).strip()

    if not text:
        raise ValueError("text cannot be empty.")

    if not buttons:
        raise ValueError("buttons cannot be empty.")

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

    import json as _json
    import requests  # lazy: only needed when this actually runs

    url = f"{TELEGRAM_API_BASE}/bot{bot_token}/sendMessage"
    reply_markup = {
        "inline_keyboard": [
            [{"text": b["text"], "callback_data": b["callback_data"]} for b in buttons]
        ]
    }

    response = requests.post(
        url,
        data={
            "chat_id": chat_id,
            "text": text,
            "reply_markup": _json.dumps(reply_markup),
        },
        timeout=15,
    )

    try:
        payload = response.json()
    except ValueError:
        payload = {}

    if response.status_code >= 400 or not payload.get("ok", False):
        raise _telegram_error(payload, response.status_code)

    return payload


def get_telegram_updates(offset=None, timeout=0, bot_token=None):
    """Poll Telegram's getUpdates endpoint once -- used to discover
    button taps (callback_query updates) on messages sent by
    send_telegram_message_with_buttons.

    `offset`: pass the previous call's highest update_id + 1 to tell
    Telegram those earlier updates are confirmed processed and should
    not be returned again -- this module keeps no other "already
    seen" state of its own for Telegram updates; the caller
    (brain/profile_change.py) is responsible for persisting the next
    offset to use (see its ProfileChangeCycle for how). `timeout` is
    Telegram's own long-poll wait in seconds; kept at 0 (return
    immediately) by default since this is called from a short-lived
    scheduled script, not a long-running listener.

    Returns the list of update dicts from Telegram's own "result"
    array (empty list if there is nothing new). Raises RuntimeError on
    failure, never retries internally.
    """

    load_dotenv()

    bot_token = bot_token or os.getenv("TELEGRAM_BOT_TOKEN")

    if not bot_token:
        raise RuntimeError(
            "TELEGRAM_BOT_TOKEN is not configured. Add it to the .env "
            "file (see .env.example)."
        )

    import requests  # lazy: only needed when this actually runs

    url = f"{TELEGRAM_API_BASE}/bot{bot_token}/getUpdates"
    params = {"timeout": timeout}
    if offset is not None:
        params["offset"] = offset

    response = requests.get(url, params=params, timeout=timeout + 15)

    try:
        payload = response.json()
    except ValueError:
        payload = {}

    if response.status_code >= 400 or not payload.get("ok", False):
        raise _telegram_error(payload, response.status_code)

    return payload.get("result", [])


def answer_telegram_callback(callback_query_id, text=None, bot_token=None):
    """Acknowledge one callback_query (a button tap) so Telegram stops
    showing a loading spinner on the tapped button in the user's app.
    `text`, if given, is shown as a brief toast notification to the
    user. Best-effort in spirit -- callers should not treat a failure
    here as a reason to undo an approval/rejection that already
    happened; it still raises RuntimeError on failure so the caller
    can log it, matching this module's usual discipline, but a caller
    may reasonably choose to swallow that specific failure."""

    if not callback_query_id:
        raise ValueError("callback_query_id cannot be empty.")

    load_dotenv()

    bot_token = bot_token or os.getenv("TELEGRAM_BOT_TOKEN")

    if not bot_token:
        raise RuntimeError(
            "TELEGRAM_BOT_TOKEN is not configured. Add it to the .env "
            "file (see .env.example)."
        )

    import requests  # lazy: only needed when this actually runs

    url = f"{TELEGRAM_API_BASE}/bot{bot_token}/answerCallbackQuery"
    data = {"callback_query_id": callback_query_id}
    if text:
        data["text"] = text

    response = requests.post(url, data=data, timeout=15)

    try:
        payload = response.json()
    except ValueError:
        payload = {}

    if response.status_code >= 400 or not payload.get("ok", False):
        raise _telegram_error(payload, response.status_code)

    return payload
