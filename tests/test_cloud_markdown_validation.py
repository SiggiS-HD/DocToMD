"""Vertragstests für die lokale Mindestvalidierung des Cloud-Markdowns."""

from __future__ import annotations

import unittest

from app.cloud_markdown_validation import CloudMarkdownValidationError, validate_cloud_markdown_response


def _response(markdown: str, **extra: object) -> dict:
    return {"status": "completed", "incomplete_details": None, "output_text": markdown, **extra}


class CloudMarkdownValidationTests(unittest.TestCase):
    def test_accepts_complete_page_marked_markdown(self) -> None:
        result = validate_cloud_markdown_response(
            response=_response("<!-- doctomd:page=1 -->\n\n# Titel\n\n<!-- doctomd:page=2 -->\n\n$$x = 1$$\n"),
            expected_page_count=2,
        )

        self.assertEqual(result.page_numbers, (1, 2))
        self.assertIn("# Titel", result.content)

    def test_reads_nested_output_text_when_sdk_convenience_field_is_absent(self) -> None:
        result = validate_cloud_markdown_response(
            response={"status": "completed", "incomplete_details": None, "output": [{"content": [{"type": "output_text", "text": "<!-- doctomd:page=1 -->\nText"}]}]},
        )

        self.assertEqual(result.page_numbers, (1,))

    def test_rejects_empty_missing_or_malformed_page_markers(self) -> None:
        cases = [
            _response(" "),
            _response("# Titel"),
            _response("<!-- doctomd:page=1 -->\n<!-- doctomd:page=3 -->"),
            _response("<!-- doctomd:page=1 --> Text"),
        ]

        for response in cases:
            with self.subTest(response=response):
                with self.assertRaises(CloudMarkdownValidationError):
                    validate_cloud_markdown_response(response=response)

    def test_accepts_source_code_blocks_but_rejects_dangerous_output_forms(self) -> None:
        result = validate_cloud_markdown_response(
            response=_response("<!-- doctomd:page=1 -->\n\n```python\nprint('source code')\n```\n")
        )

        self.assertIn("```python", result.content)
        with self.assertRaisesRegex(CloudMarkdownValidationError, "unzulässige"):
            validate_cloud_markdown_response(response=_response("<!-- doctomd:page=1 -->\n<script>alert('x')</script>"))

    def test_rejects_response_truncation(self) -> None:
        with self.assertRaises(CloudMarkdownValidationError) as raised:
            validate_cloud_markdown_response(response={"status": "incomplete", "incomplete_details": {"reason": "max_output_tokens"}})

        self.assertEqual(raised.exception.code, "CLOUD_RESPONSE_TRUNCATED")

    def test_rejects_unexpected_page_count(self) -> None:
        with self.assertRaises(CloudMarkdownValidationError) as raised:
            validate_cloud_markdown_response(
                response=_response("<!-- doctomd:page=1 -->\nText"),
                expected_page_count=2,
            )

        self.assertEqual(raised.exception.code, "CLOUD_MARKDOWN_PAGE_COUNT")

    def test_accepts_original_page_numbers_for_a_batch(self) -> None:
        result = validate_cloud_markdown_response(
            response=_response("<!-- doctomd:page=7 -->\nText\n\n<!-- doctomd:page=8 -->\nText"),
            expected_page_numbers=(7, 8),
        )

        self.assertEqual(result.page_numbers, (7, 8))


if __name__ == "__main__":
    unittest.main()
