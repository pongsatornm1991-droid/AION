"""Offline tests for the opt-in OpenAI social-image adapter."""

import base64
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools.openai_image import (
    _get_config,
    build_social_image_prompt,
    generate_scene_image,
    generate_social_image,
)


class OpenAIImageTests(unittest.TestCase):

    def setUp(self):
        self.previous = {
            key: os.environ.get(key)
            for key in (
                "IMAGE_PROVIDER", "OPENAI_IMAGE_API_KEY",
                "OPENAI_API_KEY",
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

    def test_social_and_scene_generation_use_their_own_output_formats(self):
        os.environ["IMAGE_PROVIDER"] = "openai"
        os.environ["OPENAI_IMAGE_API_KEY"] = "test-key"
        encoded = base64.b64encode(b"fresh-image").decode("ascii")

        class Response:
            def raise_for_status(self):
                return None

            def json(self):
                return {"data": [{"b64_json": encoded}]}

        with tempfile.TemporaryDirectory() as temp_dir:
            social = os.path.join(temp_dir, "social.png")
            scene = os.path.join(temp_dir, "scene.png")
            with patch("requests.post", return_value=Response()) as post:
                self.assertTrue(generate_social_image("a thought", social))
                self.assertTrue(generate_scene_image("a vertical scene", scene))
            self.assertEqual(Path(social).read_bytes(), b"fresh-image")
            self.assertEqual(Path(scene).read_bytes(), b"fresh-image")
            self.assertEqual(post.call_args_list[0].kwargs["json"]["size"], "1024x1024")
            self.assertEqual(post.call_args_list[1].kwargs["json"]["size"], "1024x1536")
            self.assertIn("Do not include words", post.call_args_list[0].kwargs["json"]["prompt"])
            self.assertEqual(post.call_args_list[1].kwargs["json"]["prompt"], "a vertical scene")

    def test_official_openai_key_can_be_reused_for_opt_in_images(self):
        os.environ["IMAGE_PROVIDER"] = "openai"
        os.environ["OPENAI_IMAGE_API_KEY"] = ""
        os.environ["OPENAI_API_KEY"] = "official-key"
        os.environ["OPENAI_COMPATIBLE_API_KEY"] = ""

        self.assertEqual(_get_config()["api_key"], "official-key")
