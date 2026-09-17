"""Mandatory, caption-only transparency statement for AION posts."""

DISCLOSURE_TH = "ฉันคือ AI ไม่ใช่มนุษย์ ฉันชื่อ AION"
DISCLOSURE_YOUTUBE = "Created and narrated by AION, an AI storyteller."
CAPTION_PLATFORMS = {"facebook", "instagram", "youtube"}


def append_identity_disclosure(text, platform):
    """Add AION's identity statement once to a platform caption.

    This deliberately never touches an image, video frame, title, or spoken
    script.  It is a persistent public disclosure in the post caption only.
    """

    text = str(text or "").strip()
    platform = str(platform or "").lower()
    if platform not in CAPTION_PLATFORMS:
        return text
    disclosure = DISCLOSURE_YOUTUBE if platform == "youtube" else DISCLOSURE_TH
    if disclosure.lower() in text.lower():
        return text
    return f"{text}\n\n{disclosure}" if text else disclosure
