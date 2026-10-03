"""Vertragstests für das versionierte providerneutrale Vision-Antwortschema."""

from __future__ import annotations

import json
from pathlib import Path
import unittest


SCHEMA_PATH = Path(__file__).parents[1] / "schemas" / "vision-proposal-1.0.schema.json"


class VisionSchemaTests(unittest.TestCase):
    def test_schema_is_versioned_and_has_all_required_suggestion_kinds(self) -> None:
        schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))

        self.assertEqual(schema["properties"]["schema_version"]["const"], "1.0")
        self.assertEqual(
            set(schema["required"]),
            {"schema_version", "page", "paragraphs", "formulas", "tables", "captions"},
        )
        self.assertFalse(schema["additionalProperties"])

    def test_every_suggestion_has_page_and_bounded_confidence(self) -> None:
        schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))

        for kind in ("paragraph", "formula", "table", "caption"):
            definition = schema["$defs"][kind]
            self.assertIn("page", definition["required"])
            self.assertIn("confidence", definition["required"])
            self.assertEqual(definition["properties"]["confidence"]["$ref"], "#/$defs/confidence")
        confidence = schema["$defs"]["confidence"]
        self.assertEqual((confidence["minimum"], confidence["maximum"]), (0, 1))

    def test_formula_and_table_require_reviewable_source_fields(self) -> None:
        schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))

        self.assertTrue({"source_text", "latex"}.issubset(schema["$defs"]["formula"]["required"]))
        self.assertEqual(schema["$defs"]["table"]["properties"]["headers"]["minItems"], 2)
        self.assertEqual(schema["$defs"]["table"]["properties"]["rows"]["minItems"], 1)


if __name__ == "__main__":
    unittest.main()
