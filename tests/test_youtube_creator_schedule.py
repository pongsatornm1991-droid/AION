"""Regression checks for AION's fixed Bangkok publishing appointments."""

import unittest
from pathlib import Path


class YouTubeCreatorScheduleTests(unittest.TestCase):
    def test_has_daily_shorts_first_cron(self):
        # Scaled from a 4-day (Thu-Sun) to a daily cadence on 2026-09-21,
        # once creator-scene-production.yml also became a daily shift.
        workflow = (Path(__file__).resolve().parents[1] / ".github" / "workflows" / "youtube-creator.yml").read_text(encoding="utf-8")
        self.assertIn('cron: "30 13 * * *"', workflow)
        self.assertNotIn('cron: "15 13 * * 6"', workflow)

    def test_scheduled_release_lane_is_short(self):
        workflow = (Path(__file__).resolve().parents[1] / ".github" / "workflows" / "youtube-creator.yml").read_text(encoding="utf-8")
        self.assertNotIn('SCHEDULE" == "15 13 * * 6"', workflow)
        self.assertIn('RELEASE_KIND="short"', workflow)
        self.assertIn('--content-kind "$RELEASE_KIND"', workflow)
        self.assertIn('episode_id:', workflow)
        self.assertIn('quality-youtube-creator', workflow)
        self.assertIn('Stage: published', workflow)

    def test_a_real_upload_fault_always_fails_the_run_after_saving_the_audit_trail(self):
        # Regression for 2026-09-25: an expired YouTube OAuth refresh token
        # made every scheduled and self-healing recovery publish attempt
        # report "Stage: upload-failed" for at least 5 days straight, but
        # the job kept reporting green because the old exit-1 check only
        # applied to an explicit, non-recovery workflow_dispatch. Nobody
        # noticed without reading the raw log text.
        workflow = (Path(__file__).resolve().parents[1] / ".github" / "workflows" / "youtube-creator.yml").read_text(encoding="utf-8")
        self.assertIn('grep -q "Stage: upload-failed" youtube-creator-publish-report.txt', workflow)
        publish_index = workflow.index("Publish one authorized Creator episode")
        persist_index = workflow.index("Persist private memory")
        fault_check_index = workflow.index("Fail the run on a real publish fault")
        upload_failed_check_index = workflow.index('grep -q "Stage: upload-failed"')
        # The fault check must come after persistence (so the audit trail of
        # a real failure is saved before the job can go red), and the
        # unconditional upload-failed check must live inside that later step,
        # not back inside the publish step where an early exit would have
        # skipped saving that same audit trail.
        self.assertLess(publish_index, persist_index)
        self.assertLess(persist_index, fault_check_index)
        self.assertLess(fault_check_index, upload_failed_check_index)
        # Both the publish step and the persistence step must survive a
        # failure raised later in the job.
        self.assertIn('name: Persist private memory\n        if: ${{ always() }}', workflow)
