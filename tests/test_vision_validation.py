"""Unit-Tests für lokale Ablehnung unsicherer Vision-Antworten."""

from __future__ import annotations

import json
import unittest

from app.vision_validation import backend_failure_warning, validate_vision_proposal


LOCAL_TEXT = "p(x) = sum_i w_i * x_i / n Table 1 precision 0.80 recall 0.75"


def _proposal() -> dict:
    page = {"page_number": 1}
    return {
        "schema_version": "1.0",
        "page": page,
        "paragraphs": [{"text": "Kurzer Absatz.", "page": page, "confidence": 0.95}],
        "formulas": [{"source_text": "p(x) = sum_i w_i * x_i / n", "latex": r"p(x) = \frac{\sum_i w_i x_i}{n}", "page": page, "confidence": 0.95}],
        "tables": [{"headers": ["Metric", "Value"], "rows": [["precision", "0.80"], ["recall", "0.75"]], "page": page, "confidence": 0.95}],
        "captions": [],
    }


class VisionValidationTests(unittest.TestCase):
    def test_accepts_a_complete_high_confidence_proposal_for_the_requested_page(self) -> None:
        outcome = validate_vision_proposal(response_text=json.dumps(_proposal()), requested_page=1, local_page_text=LOCAL_TEXT)

        self.assertIsNotNone(outcome.proposal)
        self.assertEqual(outcome.warnings, ())

    def test_reports_invalid_json_and_schema_mismatch(self) -> None:
        malformed = validate_vision_proposal(response_text="```json", requested_page=1, local_page_text=LOCAL_TEXT)
        wrong_version = _proposal(); wrong_version["schema_version"] = "2.0"
        mismatch = validate_vision_proposal(response_text=json.dumps(wrong_version), requested_page=1, local_page_text=LOCAL_TEXT)

        self.assertEqual(malformed.warnings[0].code, "VISION_INVALID_JSON")
        self.assertEqual(mismatch.warnings[0].code, "VISION_INVALID_JSON")

    def test_reports_low_confidence_and_unverifiable_content(self) -> None:
        low_confidence = _proposal(); low_confidence["formulas"][0]["confidence"] = 0.5
        foreign_formula = _proposal(); foreign_formula["formulas"][0]["source_text"] = "nicht auf der Seite"
        broken_table = _proposal(); broken_table["tables"][0]["rows"] = [["precision"]]

        self.assertEqual(validate_vision_proposal(response_text=json.dumps(low_confidence), requested_page=1, local_page_text=LOCAL_TEXT).warnings[0].code, "VISION_LOW_CONFIDENCE")
        self.assertEqual(validate_vision_proposal(response_text=json.dumps(foreign_formula), requested_page=1, local_page_text=LOCAL_TEXT).warnings[0].code, "VISION_UNVERIFIABLE_CONTENT")
        self.assertEqual(validate_vision_proposal(response_text=json.dumps(broken_table), requested_page=1, local_page_text=LOCAL_TEXT).warnings[0].code, "VISION_UNVERIFIABLE_CONTENT")

    def test_reports_page_mismatch_and_backend_failures_with_page_reference(self) -> None:
        foreign_page = _proposal(); foreign_page["formulas"][0]["page"] = {"page_number": 2}
        mismatch = validate_vision_proposal(response_text=json.dumps(foreign_page), requested_page=1, local_page_text=LOCAL_TEXT)

        self.assertEqual(mismatch.warnings[0].code, "VISION_UNVERIFIABLE_CONTENT")
        self.assertEqual(mismatch.warnings[0].page.page_number, 1)
        self.assertEqual(backend_failure_warning(failure="unreachable", page_number=3).code, "VISION_BACKEND_UNREACHABLE")
        self.assertEqual(backend_failure_warning(failure="timeout", page_number=3).code, "VISION_TIMEOUT")


if __name__ == "__main__":
    unittest.main()
