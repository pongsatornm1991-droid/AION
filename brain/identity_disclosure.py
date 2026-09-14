"""Mandatory, caption-only transparency statement for AION social posts."""

DISCLOSURE_TH = "ฉันคือ AI ไม่ใช่มนุษย์ ฉันชื่อ AION"
SOCIAL_PLATFORMS = {"facebook", "instagram"}


def append_identity_disclosure(text, platform):
    """Add AION's identity statement once to a Facebook/Instagram caption.

    This deliberately never touches an image, video frame, title, or spoken
    script.  It is a persistent public disclosure in the post caption only.
    """

    text = str(text or "").strip()
    if str(platform or "").lower() not in SOCIAL_PLATFORMS:
        return text
    if DISCLOSURE_TH.lower() in text.lower():
        return text
    return f"{text}\n\n{DISCLOSURE_TH}" if text else DISCLOSURE_TH
