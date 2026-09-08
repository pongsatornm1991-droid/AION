"""Read and answer Facebook Messenger / Instagram Direct messages.

The Graph calls are deliberately small and stateless.  Durable de-duplication,
safety review, and the one-message-per-run budget live in brain/direct_message.py.
"""

import os
from dotenv import load_dotenv
from tools.facebook import GRAPH_API_BASE, _graph_error


def _credentials(platform):
    load_dotenv()
    platform = str(platform).lower()
    if platform == "instagram":
        token = os.getenv("INSTAGRAM_ACCESS_TOKEN") or os.getenv("FACEBOOK_PAGE_ACCESS_TOKEN")
        account_id = os.getenv("INSTAGRAM_BUSINESS_ACCOUNT_ID")
    else:
        token = os.getenv("FACEBOOK_PAGE_ACCESS_TOKEN")
        account_id = os.getenv("FACEBOOK_PAGE_ID")
    if not token or not account_id:
        raise RuntimeError(f"{platform.title()} messaging credentials are not configured.")
    return token, account_id


def get_recent_messages(platform="facebook", conversation_limit=10, message_limit=20):
    """Normalize recent inbox messages from Meta conversation threads."""
    platform = str(platform).lower()
    token, account_id = _credentials(platform)
    import requests
    params = {
        "fields": f"id,participants,updated_time,messages.limit({message_limit})"
                  "{id,message,from,created_time}",
        "limit": conversation_limit,
        "access_token": token,
    }
    if platform == "instagram":
        params["platform"] = "instagram"
    response = requests.get(
        f"{GRAPH_API_BASE}/{account_id}/conversations", params=params, timeout=15,
    )
    try:
        payload = response.json()
    except ValueError:
        payload = {}
    if response.status_code >= 400 or "error" in payload:
        raise _graph_error(payload, response.status_code)

    result = []
    for conversation in payload.get("data", []):
        conversation_id = conversation.get("id")
        for item in (conversation.get("messages") or {}).get("data", []):
            author = item.get("from") or {}
            author_id = author.get("id")
            if not author_id or author_id == account_id:
                continue
            result.append({
                "id": item.get("id"), "message": item.get("message", ""),
                "from_id": author_id, "from_name": author.get("name"),
                "recipient_id": author_id, "conversation_id": conversation_id,
                "created_time": item.get("created_time"), "platform": platform,
            })
    return result


def send_message(recipient_id, message, platform="facebook"):
    """Send a response within Meta's allowed messaging window."""
    if not recipient_id or not str(message or "").strip():
        raise ValueError("recipient_id and message are required.")
    platform = str(platform).lower()
    token, account_id = _credentials(platform)
    import requests
    response = requests.post(
        f"{GRAPH_API_BASE}/{account_id}/messages",
        json={
            "recipient": {"id": recipient_id},
            "message": {"text": str(message).strip()},
            "messaging_type": "RESPONSE",
        },
        params={"access_token": token}, timeout=15,
    )
    try:
        payload = response.json()
    except ValueError:
        payload = {}
    if response.status_code >= 400 or "error" in payload:
        raise _graph_error(payload, response.status_code)
    return payload
