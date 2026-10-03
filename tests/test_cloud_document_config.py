"""Unit-Tests für den expliziten Cloud-Dokument-Konfigurationsvertrag."""

from __future__ import annotations

import unittest

from app.cloud_document_config import CloudDocumentConfig, CloudDocumentMode


class CloudDocumentConfigTests(unittest.TestCase):
    def test_default_is_disabled_and_contains_no_secret(self) -> None:
        config = CloudDocumentConfig()

        self.assertEqual(config.mode, CloudDocumentMode.OFF)
        self.assertEqual(config.max_output_tokens, 32_768)
        self.assertNotIn("OPENAI_API_KEY", config.public_options())

    def test_openai_mode_requires_model_and_exposes_only_safe_options(self) -> None:
        config = CloudDocumentConfig(
            mode=CloudDocumentMode.OPENAI,
            model_id="gpt-5.6-terra",
            timeout_seconds=1_200,
            max_output_tokens=24_000,
        )

        self.assertEqual(config.public_options()["mode"], "openai")
        self.assertEqual(config.public_options()["model_id"], "gpt-5.6-terra")
        with self.assertRaises(ValueError):
            CloudDocumentConfig(mode=CloudDocumentMode.OPENAI)
        with self.assertRaises(ValueError):
            CloudDocumentConfig(model_id="gpt-5.6-terra")

    def test_timeout_and_output_token_bounds_are_enforced(self) -> None:
        with self.assertRaises(ValueError):
            CloudDocumentConfig(timeout_seconds=0)
        with self.assertRaises(ValueError):
            CloudDocumentConfig(max_output_tokens=1_023)
        with self.assertRaises(ValueError):
            CloudDocumentConfig(max_output_tokens=32_769)


if __name__ == "__main__":
    unittest.main()
