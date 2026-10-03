"""Vertragstests für vollständiges, seitenmarkiertes Cloud-Markdown."""

from __future__ import annotations

import unittest

from app.cloud_document_prompt import CLOUD_DOCUMENT_PROMPT_VERSION, build_batch_cloud_markdown_instructions, build_cloud_markdown_instructions


class CloudDocumentPromptTests(unittest.TestCase):
    def test_prompt_is_versioned_and_requires_the_complete_markdown_contract(self) -> None:
        instructions = build_cloud_markdown_instructions()

        self.assertEqual(CLOUD_DOCUMENT_PROMPT_VERSION, "1.5")
        self.assertIn("only UTF-8 Markdown", instructions)
        self.assertIn("<!-- doctomd:page=N -->", instructions)
        self.assertIn("strictly ascending, one-based order", instructions)
        self.assertIn("Markdown headings", instructions)
        self.assertIn("tables", instructions)
        self.assertIn("$...$", instructions)
        self.assertIn("$$...$$", instructions)
        self.assertIn("> [!warning]", instructions)
        self.assertIn("do not emit Markdown or HTML image references", instructions)

    def test_prompt_forbids_unverifiable_or_executable_output(self) -> None:
        instructions = build_cloud_markdown_instructions()

        self.assertIn("Do not add an introduction", instructions)
        self.assertIn("file command", instructions)
        self.assertIn("shell command", instructions)
        self.assertIn("do not invent", instructions)
        self.assertIn("Never claim", instructions)

    def test_batch_prompt_requires_the_original_first_page_marker(self) -> None:
        instructions = build_batch_cloud_markdown_instructions(page_numbers=(12, 13))

        self.assertIn("<!-- doctomd:page=12 -->", instructions)
        self.assertIn("physical page 1", instructions)


if __name__ == "__main__":
    unittest.main()
