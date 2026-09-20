import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools.produce_creator_motion import render_kinetic_fallback


class CreatorMotionResilienceTests(unittest.TestCase):
    def test_kinetic_fallback_creates_a_five_second_video_from_the_current_image(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "scene.png"
            target = Path(directory) / "motion.mp4"
            source.write_bytes(b"new-scene")
            with patch("tools.produce_creator_motion.subprocess.run") as run:
                run.side_effect = lambda *args, **kwargs: target.write_bytes(b"new-motion")
                self.assertTrue(render_kinetic_fallback(source, target))
            command = run.call_args.args[0]
            self.assertIn("-t", command)
            self.assertIn("5", command)
