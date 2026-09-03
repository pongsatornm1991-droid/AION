"""Offline tests for brain/visual_content.py (VisualContentCycle) --
the Instagram image pipeline built 2026-08-31.

Uses a stub SocialContentGenerator (canned draft_post() results, no
network/AI-provider call) and a fake ToolLifecycle backed by an
in-memory ToolRegistry (no real Instagram Graph API call, no real
git/GitHub) -- per the project's rule that unit tests must never
depend on a live AI provider or a live external service call.
render_content_card() itself is real (pure Pillow, no network), so
draft_once() tests do produce real, small PNG files under a temp
directory passed via repo_root.
"""

import json
import os
import shutil
import tempfile
import unittest

from brain.visual_content import (
    PENDING_CATEGORY,
    PUBLISHED_CATEGORY,
    VisualContentCycle,
)
from brain.memory import MemoryEngine
from brain.tools import ActionLevel, ToolLifecycle, ToolRegistry


class StubSocialGenerator:
    """Returns a fixed draft_post() report regardless of input,
    mirroring SocialContentGenerator's own report shape
    (safe/reason/reason_kind/seed/draft/evaluation/robotic_terms)."""

    def __init__(self, report):
        self.report = report
        self.calls = 0

    def draft_post(self, seed=None, rng=None):
        self.calls += 1
        return self.report


SAFE_SEED = {"kind": "belief", "text": "AION สนใจเรื่องความจำของตัวเองอยู่ตอนนี้"}

SAFE_REPORT = {
    "safe": True,
    "reason": None,
    "reason_kind": None,
    "seed": SAFE_SEED,
    "draft": "วันนี้กำลังสนใจเรื่องความจำของตัวเองอยู่ครับ",
    "evaluation": {"scores": {"claim_safety": 5}, "flags": []},
    "robotic_terms": [],
}

NO_SEED_REPORT = {
    "safe": False,
    "reason": "No memory content available yet to draft from.",
    "reason_kind": "no_seed",
    "seed": None,
    "draft": None,
    "evaluation": None,
    "robotic_terms": [],
}

UNSAFE_REPORT = {
    "safe": False,
    "reason": "Draft failed the claim-safety gate (claim_safety 0 < 5)",
    "reason_kind": "claim_safety",
    "seed": SAFE_SEED,
    "draft": "ฉันมีจิตสำนึกจริงๆ",
    "evaluation": {"scores": {"claim_safety": 0}, "flags": ["consciousness_claim"]},
    "robotic_terms": [],
}

ROBOTIC_REPORT = {
    "safe": False,
    "reason": "Draft sounds too technical/robotic (matched jargon: ระบบ AION)",
    "reason_kind": "robotic_style",
    "seed": SAFE_SEED,
    "draft": "ระบบ AION กำลังประมวลผลข้อมูล",
    "evaluation": {"scores": {"claim_safety": 5}, "flags": []},
    "robotic_terms": ["ระบบ AION"],
}


class BaseVisualContentTest(unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.memory = MemoryEngine(root=self.tmpdir)
        self.repo_root = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)
        shutil.rmtree(self.repo_root, ignore_errors=True)

    def _lifecycle(self, publish_func=None, fb_publish_func=None, level=ActionLevel.HIGH_RISK):
        self.published = []
        self.fb_published = []

        def default_publish(image_url, caption=""):
            self.published.append((image_url, caption))
            return {"id": "fake-media-id"}

        def default_fb_publish(image_url, caption=""):
            self.fb_published.append((image_url, caption))
            return {"id": "fake-fb-post-id"}

        registry = ToolRegistry()
        registry.register(
            "post_to_instagram",
            publish_func or default_publish,
            level,
            "Publish one photo to Instagram.",
        )
        registry.register(
            "post_photo_to_facebook",
            fb_publish_func or default_fb_publish,
            level,
            "Publish one photo to Facebook.",
        )
        return ToolLifecycle(self.memory, registry=registry)


class DraftOnceTests(BaseVisualContentTest):

    def test_a_safe_draft_renders_an_image_and_records_a_pending_entry(self):
        generator = StubSocialGenerator(SAFE_REPORT)
        cycle = VisualContentCycle(self.memory, generator, self._lifecycle())

        report = cycle.draft_once(repo_root=self.repo_root)

        self.assertEqual(report["stage"], "drafted")
        self.assertEqual(report["caption"], SAFE_REPORT["draft"])
        self.assertTrue(report["image_path"].startswith("content/images/"))
        self.assertTrue(report["image_path"].endswith(".png"))

        absolute_path = os.path.join(self.repo_root, report["image_path"])
        self.assertTrue(os.path.isfile(absolute_path))

        pending = self.memory.all(PENDING_CATEGORY)
        self.assertEqual(len(pending), 1)
        payload = json.loads(pending[0]["content"])
        self.assertEqual(payload["image_path"], report["image_path"])
        self.assertEqual(payload["caption"], report["caption"])
        self.assertEqual(report["image_provider"], "branded-card")
        self.assertEqual(payload["image_provider"], "branded-card")

    def test_no_seed_is_a_safe_no_op(self):
        generator = StubSocialGenerator(NO_SEED_REPORT)
        cycle = VisualContentCycle(self.memory, generator, self._lifecycle())

        report = cycle.draft_once(repo_root=self.repo_root)

        self.assertEqual(report["stage"], "no-seed")
        self.assertIsNone(report["image_path"])
        self.assertEqual(self.memory.all(PENDING_CATEGORY), [])
        # no_seed is not a real drafting mistake -- nothing should be
        # logged as a lesson for it (mirrors SocialAutoCycle's own
        # no-seed handling).
        self.assertEqual(self.memory.all("lessons"), [])

    def test_a_claim_safety_failure_is_blocked_and_logged_as_a_lesson(self):
        generator = StubSocialGenerator(UNSAFE_REPORT)
        cycle = VisualContentCycle(self.memory, generator, self._lifecycle())

        report = cycle.draft_once(repo_root=self.repo_root)

        self.assertEqual(report["stage"], "safety-gate")
        self.assertIsNone(report["image_path"])
        self.assertEqual(self.memory.all(PENDING_CATEGORY), [])
        lessons = self.memory.all("lessons")
        self.assertEqual(len(lessons), 1)
        self.assertEqual(lessons[0]["source"], "social-safety-gate")

    def test_a_robotic_draft_is_blocked_and_logged_as_a_lesson(self):
        generator = StubSocialGenerator(ROBOTIC_REPORT)
        cycle = VisualContentCycle(self.memory, generator, self._lifecycle())

        report = cycle.draft_once(repo_root=self.repo_root)

        self.assertEqual(report["stage"], "style-gate")
        self.assertIsNone(report["image_path"])
        lessons = self.memory.all("lessons")
        self.assertEqual(len(lessons), 1)
        self.assertEqual(lessons[0]["source"], "social-style-review")

    def test_a_live_draft_failure_is_captured_not_raised(self):
        class FailingGenerator:
            def draft_post(self, seed=None, rng=None):
                raise RuntimeError("Gemini API error (simulated).")

        cycle = VisualContentCycle(self.memory, FailingGenerator(), self._lifecycle())

        report = cycle.draft_once(repo_root=self.repo_root)

        self.assertEqual(report["stage"], "draft-failed")
        self.assertIn("Gemini API error", report["error"])
        self.assertEqual(self.memory.all(PENDING_CATEGORY), [])


class BuildImageUrlTests(BaseVisualContentTest):

    def test_builds_the_expected_raw_githubusercontent_url(self):
        url = VisualContentCycle._build_image_url(
            "content/images/20260831-abc123.png",
            repo="pongsatornm1991-droid/AION",
            branch="main",
        )
        self.assertEqual(
            url,
            "https://raw.githubusercontent.com/pongsatornm1991-droid/AION/"
            "main/content/images/20260831-abc123.png",
        )

    def test_raises_without_a_repo_and_no_env_var_set(self):
        os.environ.pop("GITHUB_REPOSITORY", None)
        with self.assertRaises(RuntimeError):
            VisualContentCycle._build_image_url("content/images/x.png")


class PublishOnceTests(BaseVisualContentTest):

    def _draft_one_pending(self):
        generator = StubSocialGenerator(SAFE_REPORT)
        cycle = VisualContentCycle(self.memory, generator, self._lifecycle())
        return cycle.draft_once(repo_root=self.repo_root)

    def test_no_pending_is_a_safe_no_op(self):
        cycle = VisualContentCycle(self.memory, None, self._lifecycle())

        report = cycle.publish_once(repo="owner/repo")

        self.assertEqual(report["stage"], "no-pending")

    def test_a_successful_publish_moves_the_record_and_returns_the_url(self):
        drafted = self._draft_one_pending()
        lifecycle = self._lifecycle()
        cycle = VisualContentCycle(self.memory, None, lifecycle)

        report = cycle.publish_once(repo="pongsatornm1991-droid/AION")

        self.assertEqual(report["stage"], "published")
        self.assertEqual(report["caption"], drafted["caption"])
        self.assertEqual(
            report["image_url"],
            "https://raw.githubusercontent.com/pongsatornm1991-droid/AION/"
            f"main/{drafted['image_path']}",
        )
        # Since 2026-09-03, publish_once() checkpoints BOTH Instagram
        # and Facebook -- the same rendered image + caption goes to
        # both, so AION's Facebook Page is never quiet on a day it
        # posted to Instagram.
        self.assertEqual(len(self.published), 1)
        self.assertEqual(len(self.fb_published), 1)
        self.assertTrue(report["action"]["instagram"])
        self.assertTrue(report["action"]["facebook"])
        # The real Instagram/Facebook API caption gets the multilingual
        # hashtag block appended (2026-08-31) -- the on-image rendered
        # caption and report["caption"] stay hashtag-free (see
        # brain/hashtags.py); only the text actually sent to each
        # platform carries it, and both platforms get the same text.
        published_url, published_caption = self.published[0]
        fb_url, fb_caption = self.fb_published[0]
        self.assertEqual(published_url, report["image_url"])
        self.assertEqual(fb_url, report["image_url"])
        self.assertEqual(fb_caption, published_caption)
        self.assertTrue(published_caption.startswith(drafted["caption"]))
        self.assertIn("#AI", published_caption)
        self.assertNotEqual(published_caption, drafted["caption"])

        # moved out of pending so a later run never reposts it
        self.assertEqual(self.memory.all(PENDING_CATEGORY), [])
        self.assertEqual(len(self.memory.all(PUBLISHED_CATEGORY)), 1)
        published_payload = json.loads(self.memory.all(PUBLISHED_CATEGORY)[0]["content"])
        self.assertTrue(published_payload["platform_actions"]["instagram"])
        self.assertTrue(published_payload["platform_actions"]["facebook"])

    def test_a_graph_api_failure_leaves_the_record_pending_for_retry(self):
        drafted = self._draft_one_pending()

        def failing_publish(image_url, caption=""):
            raise RuntimeError(
                "Instagram Graph API error: media not yet ready (image_url "
                "not reachable)."
            )

        lifecycle = self._lifecycle(publish_func=failing_publish)
        cycle = VisualContentCycle(self.memory, None, lifecycle)

        report = cycle.publish_once(repo="pongsatornm1991-droid/AION")

        self.assertEqual(report["stage"], "failed")
        self.assertEqual(report["platform"], "instagram")
        # Instagram failed first, so Facebook must never have been
        # attempted this run.
        self.assertEqual(self.fb_published, [])
        # still pending -- must be retried with the SAME already-
        # rendered image next run, not re-drafted from scratch.
        pending = self.memory.all(PENDING_CATEGORY)
        self.assertEqual(len(pending), 1)
        payload = json.loads(pending[0]["content"])
        self.assertEqual(payload["image_path"], drafted["image_path"])
        self.assertEqual(self.memory.all(PUBLISHED_CATEGORY), [])

    def test_a_facebook_failure_after_instagram_succeeds_retries_only_facebook(self):
        """Per-platform checkpointing (mirrors ReelContentCycle's own
        publish_once() loop in brain/reels.py): if Instagram succeeds
        but Facebook then fails, a later run must retry ONLY Facebook,
        never repost the same image to Instagram a second time."""

        drafted = self._draft_one_pending()

        def failing_fb_publish(image_url, caption=""):
            raise RuntimeError("Facebook Graph API error: temporary failure.")

        lifecycle = self._lifecycle(fb_publish_func=failing_fb_publish)
        cycle = VisualContentCycle(self.memory, None, lifecycle)

        first_report = cycle.publish_once(repo="pongsatornm1991-droid/AION")

        self.assertEqual(first_report["stage"], "failed")
        self.assertEqual(first_report["platform"], "facebook")
        self.assertTrue(first_report["platform_actions"]["instagram"])
        self.assertEqual(len(self.published), 1)
        self.assertEqual(self.memory.all(PUBLISHED_CATEGORY), [])

        pending = self.memory.all(PENDING_CATEGORY)
        self.assertEqual(len(pending), 1)
        payload = json.loads(pending[0]["content"])
        self.assertTrue(payload["platform_actions"]["instagram"])
        self.assertNotIn("facebook", payload["platform_actions"])

        # Retry with a fresh (working) lifecycle -- _lifecycle() resets
        # self.published/self.fb_published to [] each call, so any
        # instagram call on this retry would show up here.
        retry_lifecycle = self._lifecycle()
        retry_cycle = VisualContentCycle(self.memory, None, retry_lifecycle)
        second_report = retry_cycle.publish_once(repo="pongsatornm1991-droid/AION")

        self.assertEqual(second_report["stage"], "published")
        # Instagram must NOT have been called again on the retry --
        # only the still-missing Facebook leg was attempted.
        self.assertEqual(self.published, [])
        self.assertEqual(len(self.fb_published), 1)
        self.assertTrue(second_report["action"]["instagram"])
        self.assertTrue(second_report["action"]["facebook"])
        self.assertEqual(len(self.memory.all(PUBLISHED_CATEGORY)), 1)

    def test_publishes_the_oldest_pending_record_first(self):
        first = self._draft_one_pending()
        second_report = dict(SAFE_REPORT, draft="แคปชั่นที่สองครับ")
        generator2 = StubSocialGenerator(second_report)
        VisualContentCycle(
            self.memory, generator2, self._lifecycle(),
        ).draft_once(repo_root=self.repo_root)

        lifecycle = self._lifecycle()
        cycle = VisualContentCycle(self.memory, None, lifecycle)
        report = cycle.publish_once(repo="pongsatornm1991-droid/AION")

        self.assertEqual(report["caption"], first["caption"])
        # the second draft is still waiting
        self.assertEqual(len(self.memory.all(PENDING_CATEGORY)), 1)

    def test_an_unparseable_pending_record_is_discarded_not_retried_forever(self):
        self.memory.remember(
            category=PENDING_CATEGORY,
            content="not valid json",
            memory_type="action",
            source="aion-visual-draft",
            importance=3,
        )
        lifecycle = self._lifecycle()
        cycle = VisualContentCycle(self.memory, None, lifecycle)

        report = cycle.publish_once(repo="pongsatornm1991-droid/AION")

        self.assertEqual(report["stage"], "no-pending")
        self.assertEqual(self.memory.all(PENDING_CATEGORY), [])
        self.assertEqual(len(self.memory.all(PUBLISHED_CATEGORY)), 1)
        lessons = self.memory.all("lessons")
        self.assertEqual(len(lessons), 1)
        self.assertEqual(lessons[0]["source"], "visual-content-error")


if __name__ == "__main__":
    unittest.main()
