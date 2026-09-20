"""Safe, credential-free readiness checks before AION platform actions."""

import os


class PlatformPreflight:
    """Reports readiness without reading, logging, or returning secret values."""

    REQUIREMENTS = {
        "image": ("OPENAI_IMAGE_API_KEY", "OPENAI_API_KEY"),
        "video": ("GEMINI_API_KEY",),
        "youtube": ("YOUTUBE_CLIENT_ID", "YOUTUBE_CLIENT_SECRET", "YOUTUBE_REFRESH_TOKEN"),
        "facebook": ("FACEBOOK_PAGE_ACCESS_TOKEN", "FACEBOOK_PAGE_ID"),
        "instagram": ("INSTAGRAM_ACCESS_TOKEN", "INSTAGRAM_BUSINESS_ACCOUNT_ID"),
    }

    def __init__(self, environ=None):
        self.environ = environ if environ is not None else os.environ

    def check(self, platform):
        name = str(platform).strip().lower()
        if name not in self.REQUIREMENTS:
            raise ValueError("Unknown platform preflight target.")
        alternatives = self.REQUIREMENTS[name]
        if name == "image":
            configured = any(str(self.environ.get(key) or "").strip() for key in alternatives)
            missing = [] if configured else ["image-provider-key"]
        else:
            missing = [key.lower() for key in alternatives if not str(self.environ.get(key) or "").strip()]
            configured = not missing
        return {
            "platform": name,
            "state": "ready" if configured else "waiting-for-owner-configuration",
            "configured": configured,
            "missing": missing,
            "boundary": "ตรวจเฉพาะว่าการตั้งค่ามีอยู่หรือไม่ ไม่เปิดเผยค่า ไม่ตรวจสิทธิ์แทนผู้ให้บริการ และไม่เปลี่ยนบัญชี",
        }

    def snapshot(self):
        checks = [self.check(name) for name in self.REQUIREMENTS]
        return {
            "checks": checks,
            "ready": [item["platform"] for item in checks if item["configured"]],
            "waiting": [item["platform"] for item in checks if not item["configured"]],
        }
