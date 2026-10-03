"""Tests für die opt-in Vision-Ausführung ohne Netzwerkanfrage."""

from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from app.pdf_extract import ExtractedPage
from app.vision_config import VisionConfig, VisionMode, VisionProvider
from app.vision_service import execute_vision_proposals


class VisionServiceTests(unittest.TestCase):
    @patch("app.vision_service.request_page_proposal")
    @patch("app.vision_service.render_page")
    def test_writes_only_validated_page_proposal(self, render_page, request) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            image = root / "page-001.png"; image.write_bytes(b"png")
            render_page.return_value = image
            request.return_value = json.dumps({"schema_version": "1.0", "page": {"page_number": 1}, "paragraphs": [], "formulas": [], "tables": [], "captions": []})
            config = VisionConfig(provider=VisionProvider.OPENAI, mode=VisionMode.AUTO, model_id="gpt-5.6-terra")
            paths, warnings = execute_vision_proposals(source_path=root / "Quelle.pdf", pages=(ExtractedPage(1, "Text", 1, 1),), page_numbers=(1,), config=config, proposal_dir=root / "Quelle.vision-proposals", schema={})
            self.assertEqual(warnings, ())
            self.assertEqual(paths[0].name, "page-001.proposal.json")
            self.assertEqual(json.loads(paths[0].read_text(encoding="utf-8"))["page"]["page_number"], 1)


if __name__ == "__main__":
    unittest.main()
