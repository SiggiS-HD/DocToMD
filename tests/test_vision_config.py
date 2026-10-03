"""Unit-Tests für den expliziten, geheimnisfreien Vision-Konfigurationsvertrag."""

from __future__ import annotations

import unittest

from app.vision_config import VisionConfig, VisionMode, VisionProvider


class VisionConfigTests(unittest.TestCase):
    def test_default_is_local_and_network_free(self) -> None:
        config = VisionConfig()

        self.assertEqual(config.provider, VisionProvider.NONE)
        self.assertEqual(config.mode, VisionMode.OFF)
        self.assertEqual(config.public_options()["provider"], "none")
        self.assertNotIn("OPENAI_API_KEY", config.public_options())

    def test_openai_auto_requires_model_and_never_has_lm_endpoint(self) -> None:
        config = VisionConfig(
            provider=VisionProvider.OPENAI,
            mode=VisionMode.AUTO,
            model_id="gpt-5.6-terra",
        )

        self.assertEqual(config.public_options()["model_id"], "gpt-5.6-terra")
        self.assertNotIn("lm_studio_endpoint", config.public_options())
        with self.assertRaises(ValueError):
            VisionConfig(provider=VisionProvider.OPENAI, mode=VisionMode.AUTO)
        with self.assertRaises(ValueError):
            VisionConfig(
                provider=VisionProvider.OPENAI,
                mode=VisionMode.AUTO,
                model_id="gpt-5.6-terra",
                lm_studio_endpoint="http://192.168.2.52:1234",
            )

    def test_lm_studio_force_requires_a_valid_endpoint(self) -> None:
        config = VisionConfig(
            provider=VisionProvider.LM_STUDIO,
            mode=VisionMode.FORCE,
            model_id="google/gemma-3-12b",
            lm_studio_endpoint="http://192.168.2.52:1234",
        )

        self.assertEqual(config.public_options()["lm_studio_endpoint"], "http://192.168.2.52:1234")
        with self.assertRaises(ValueError):
            VisionConfig(
                provider=VisionProvider.LM_STUDIO,
                mode=VisionMode.FORCE,
                model_id="google/gemma-3-12b",
            )
        with self.assertRaises(ValueError):
            VisionConfig(
                provider=VisionProvider.LM_STUDIO,
                mode=VisionMode.FORCE,
                model_id="google/gemma-3-12b",
                lm_studio_endpoint="not-a-url",
            )

    def test_none_rejects_any_vision_activation_or_provider_settings(self) -> None:
        with self.assertRaises(ValueError):
            VisionConfig(mode=VisionMode.AUTO)
        with self.assertRaises(ValueError):
            VisionConfig(model_id="gpt-5.6-terra")


if __name__ == "__main__":
    unittest.main()
