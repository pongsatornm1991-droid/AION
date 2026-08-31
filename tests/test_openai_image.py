"""Offline tests for the opt-in OpenAI social-image adapter."""

import os
import tempfile
import unittest
from unittest.mock import patch

from tools.openai_image import build_social_image_prompt, generate_social_image


class OpenAIImageTests(unittest.TestCase):

    def setUp(self):
        self.previous = {
            key: os.environ.get(key)
            for key in (
                "IMAGE_PROVIDER", "OPENAI_IMAGE_API_KEY",
                "OPENAI_COMPATIBLE_API_KEY",
            )
        }

    def tearDown(self):
        for key, value in self.previous.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value

    def test_disabled_provider_never_makes_a_network_request(self):
        os.environ["IMAGE_PROVIDER"] = "branded-card"
        with patch("requests.post") as post:
            self.assertFalse(generate_social_image("a thought", "unused.png"))
        post.assert_not_called()

    def test_prompt_preserves_brand_and_forbids_text(self):
        prompt = build_social_image_prompt("AION is learning from silence.")
        self.assertIn("AION", prompt)
        self.assertIn("Do not include words", prompt)
        self.assertIn("silence", prompt)

    def test_api_failure_falls_back_without_creating_an_image(self):
        os.environ["IMAGE_PROVIDER"] = "openai"
        os.environ["OPENAI_IMAGE_API_KEY"] = "test-key"
        with tempfile.TemporaryDirectory() as temp_dir:
            out_path = os.path.join(temp_dir, "image.png")
            with patch("requests.post", side_effect=RuntimeError("offline")):
                self.assertFalse(generate_social_image("a thought", out_path))
            self.assertFalse(os.path.exists(out_path))
