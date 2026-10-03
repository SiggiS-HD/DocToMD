"""Tests für den getrennten Fortschrittskanal."""

from __future__ import annotations

import io
import json
import unittest

from app.progress import ProgressReporter


class ProgressReporterTests(unittest.TestCase):
    def test_jsonl_emits_machine_readable_event(self) -> None:
        stream = io.StringIO()
        reporter = ProgressReporter("jsonl", stream)

        reporter("cloud", "in_progress", "Cloud-Dokument wird verarbeitet.")

        event = json.loads(stream.getvalue())
        self.assertEqual(event["event"], "progress")
        self.assertEqual(event["phase"], "cloud")
        self.assertEqual(event["status"], "in_progress")
        self.assertGreaterEqual(event["elapsed_ms"], 0)

    def test_none_writes_nothing(self) -> None:
        stream = io.StringIO()
        ProgressReporter("none", stream)("write", "completed", "Fertig.")
        self.assertEqual(stream.getvalue(), "")


if __name__ == "__main__":
    unittest.main()
