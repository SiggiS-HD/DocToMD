"""Tests für den geheimnisfreien Wiederaufnahmezustand von Cloud-Läufen."""

from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from app.cloud_run_state import CloudBatchRunEntry, load_matching_cloud_batch_run_state, load_matching_cloud_run_state, write_cloud_batch_run_state, write_cloud_run_state
from app.source_fingerprint import fingerprint_source


class CloudRunStateTests(unittest.TestCase):
    def test_round_trips_only_matching_source_context_model_and_prompt(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            source_path = root / "Quelle.pdf"
            source_path.write_bytes(b"%PDF")
            source = fingerprint_source(source_path, media_type="application/pdf")
            state_path = root / "Quelle.cloud-run.json"

            write_cloud_run_state(
                path=state_path,
                source=source,
                local_markdown_sha256="local-markdown-sha256",
                model_id="gpt-5.6-terra",
                prompt_version="1.3",
                response_id="resp_test",
            )
            state = load_matching_cloud_run_state(
                path=state_path,
                source=source,
                local_markdown_sha256="local-markdown-sha256",
                model_id="gpt-5.6-terra",
                prompt_version="1.3",
            )

            self.assertIsNotNone(state)
            self.assertEqual(state.response_id, "resp_test")
            self.assertEqual(state.local_markdown_sha256, "local-markdown-sha256")
            self.assertNotIn("OPENAI_API_KEY", state_path.read_text(encoding="utf-8"))

    def test_rejects_state_when_context_model_or_prompt_differs(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            source_path = root / "Quelle.pdf"
            source_path.write_bytes(b"%PDF")
            source = fingerprint_source(source_path, media_type="application/pdf")
            state_path = root / "Quelle.cloud-run.json"
            write_cloud_run_state(
                path=state_path,
                source=source,
                local_markdown_sha256="context-a",
                model_id="model-a",
                prompt_version="prompt-a",
                response_id="resp_test",
            )

            for context_hash, model_id, prompt_version in (
                ("context-b", "model-a", "prompt-a"),
                ("context-a", "model-b", "prompt-a"),
                ("context-a", "model-a", "prompt-b"),
            ):
                self.assertIsNone(load_matching_cloud_run_state(
                    path=state_path,
                    source=source,
                    local_markdown_sha256=context_hash,
                    model_id=model_id,
                    prompt_version=prompt_version,
                ))

            source_path.write_bytes(b"%PDF-changed")
            changed_source = fingerprint_source(source_path, media_type="application/pdf")
            self.assertIsNone(load_matching_cloud_run_state(
                path=state_path,
                source=changed_source,
                local_markdown_sha256="context-a",
                model_id="model-a",
                prompt_version="prompt-a",
            ))

    def test_batch_state_requires_the_exact_bound_plan(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            source_path = root / "Quelle.pdf"
            source_path.write_bytes(b"%PDF")
            source = fingerprint_source(source_path, media_type="application/pdf")
            state_path = root / "Quelle.cloud-run.json"
            plan = (("batch-001-pages-001-002", (1, 2)), ("batch-002-pages-003-003", (3,)))
            entries = tuple(CloudBatchRunEntry(batch_id, pages) for batch_id, pages in plan)
            write_cloud_batch_run_state(
                path=state_path, source=source, local_markdown_sha256="context-a",
                model_id="model-a", prompt_version="prompt-a", plan=plan, entries=entries,
            )

            self.assertIsNotNone(load_matching_cloud_batch_run_state(
                path=state_path, source=source, local_markdown_sha256="context-a",
                model_id="model-a", prompt_version="prompt-a", plan=plan,
            ))
            self.assertIsNone(load_matching_cloud_batch_run_state(
                path=state_path, source=source, local_markdown_sha256="context-a",
                model_id="model-a", prompt_version="prompt-a",
                plan=(("batch-001-pages-001-003", (1, 2, 3)),),
            ))
            source_path.write_bytes(b"%PDF-changed")
            changed_source = fingerprint_source(source_path, media_type="application/pdf")
            self.assertIsNone(load_matching_cloud_batch_run_state(
                path=state_path, source=changed_source, local_markdown_sha256="context-a",
                model_id="model-a", prompt_version="prompt-a", plan=plan,
            ))


if __name__ == "__main__":
    unittest.main()
