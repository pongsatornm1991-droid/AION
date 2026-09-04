"""Publish a human-supplied local video: upload it to YouTube, then post
the resulting link to Facebook and Instagram.

Unlike every other content path in this project (ReelContentCycle,
YouTubeShortsCycle, VisualContentCycle, ...), this one does NOT read from
AION's own memory queue -- there is nothing for AION to have written,
since the video is something a person filmed and supplied directly. It
exists purely as a manual, one-off tool: run it by hand, on a machine
that actually has the video file, whenever there is a new video to
share. GitHub Actions cannot run this -- CI has no way to reach a local
file on someone's computer.

Facebook supports plain text posts, so the Facebook side is just a
message containing the YouTube link (tools.facebook.post_to_facebook_page).
Instagram's Graph API has no text-only post type -- every post needs an
image or video -- so the Instagram side attaches an existing AION
reference image and puts the link in the caption instead, the same
raw.githubusercontent.com pattern main.py's run-instagram-publish
already relies on for its own images.
"""

from tools.facebook import post_to_facebook_page
from tools.instagram import publish_photo
from tools.youtube import upload_short

# AION's current profile picture (public repo, already live on every
# platform) -- used as the Instagram image when the caller doesn't pass
# a more specific one for this particular video.
DEFAULT_INSTAGRAM_ANNOUNCE_IMAGE = (
    "https://raw.githubusercontent.com/pongsatornm1991-droid/AION/main/"
    "assets/content-library/aion-character/04-aion-profile-v2.png"
)


def publish_local_video_everywhere(
    video_path,
    title,
    caption=None,
    description=None,
    privacy_status=None,
    instagram_image_url=None,
    skip_facebook=False,
    skip_instagram=False,
):
    """Upload one local video to YouTube, then announce it on Facebook
    and Instagram.

    Raises if the YouTube upload itself fails -- without a link there is
    nothing for Facebook/Instagram to announce, so there is no useful
    partial result to return. Once YouTube succeeds, Facebook and
    Instagram are each attempted independently and never raise: one
    platform's failure is recorded in the report rather than hiding the
    other platform's success (or aborting a post that already worked).
    """

    caption = (caption or title or "").strip()
    report = {"stage": "started", "video_path": str(video_path), "title": title}

    youtube = upload_short(
        video_path,
        title,
        description or caption or title,
        privacy_status=privacy_status,
    )
    report["youtube"] = dict(youtube)
    report["stage"] = "youtube-done"

    message = f"{caption}\n\nดูคลิปเต็มได้ที่ YouTube: {youtube['url']}".strip()

    if skip_facebook:
        report["facebook"] = {"status": "skipped"}
    else:
        try:
            result = post_to_facebook_page(message)
            report["facebook"] = {"status": "ok", "id": result.get("id")}
        except Exception as exc:
            report["facebook"] = {"status": "failed", "error": str(exc)}

    if skip_instagram:
        report["instagram"] = {"status": "skipped"}
    else:
        try:
            result = publish_photo(
                image_url=instagram_image_url or DEFAULT_INSTAGRAM_ANNOUNCE_IMAGE,
                caption=message,
            )
            report["instagram"] = {"status": "ok", "id": result.get("id")}
        except Exception as exc:
            report["instagram"] = {"status": "failed", "error": str(exc)}

    report["stage"] = "done"
    return report
