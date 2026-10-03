"""Regressionen für die lokale Inhaltsdichteprüfung von Cloud-Markdown."""

from __future__ import annotations

import unittest

from app.cloud_content_completeness import CloudContentCompletenessError, verify_cloud_content_completeness


class CloudContentCompletenessTests(unittest.TestCase):
    def test_accepts_substantive_cloud_content_for_each_local_page(self) -> None:
        verify_cloud_content_completeness(
            local_markdown=(
                "<!-- doctomd:page=1 -->\n# Titel\n\nDies ist ein lokaler Absatz mit mehreren belegten Wörtern.\n\n"
                "<!-- doctomd:page=2 -->\n\n$$x = y + 1$$\n"
            ),
            cloud_markdown=(
                "<!-- doctomd:page=1 -->\n# Titel\n\nEin Cloud-Absatz bewahrt mehrere fachliche Wörter.\n\n"
                "<!-- doctomd:page=2 -->\n\n$$x = y + 1$$\n"
            ),
        )

    def test_rejects_heading_and_warning_only_derivative(self) -> None:
        with self.assertRaises(CloudContentCompletenessError) as raised:
            verify_cloud_content_completeness(
                local_markdown="<!-- doctomd:page=1 -->\n# Titel\n\nLokaler Absatz mit ausreichend fachlichem Inhalt.\n",
                cloud_markdown="<!-- doctomd:page=1 -->\n# Titel\n\n> [!warning]\n> Nicht lesbar.\n",
            )

        self.assertIn("Seite 1", str(raised.exception))

    def test_rejects_missing_table_or_formula_structure(self) -> None:
        with self.assertRaisesRegex(CloudContentCompletenessError, "Tabelle"):
            verify_cloud_content_completeness(
                local_markdown="<!-- doctomd:page=1 -->\n| A | B |\n| --- | --- |\n| 1 | 2 |\n",
                cloud_markdown="<!-- doctomd:page=1 -->\nDie Werte sind eins und zwei.\n",
            )

    def test_does_not_interpret_pdf_formula_pipe_characters_as_a_gfm_table(self) -> None:
        verify_cloud_content_completeness(
            local_markdown="<!-- doctomd:page=40 -->\n|5| 5\n\nLokaler Rechenschritt mit Inhalt.\n",
            cloud_markdown="<!-- doctomd:page=40 -->\nCloud-Rechenschritt mit ausreichend Inhalt.\n",
        )
        with self.assertRaisesRegex(CloudContentCompletenessError, "Formelstruktur"):
            verify_cloud_content_completeness(
                local_markdown="<!-- doctomd:page=1 -->\n$$x = y + 1$$\n",
                cloud_markdown="<!-- doctomd:page=1 -->\nDie Gleichung wird erklärt.\n",
            )

    def test_allows_warning_for_a_locally_empty_page(self) -> None:
        verify_cloud_content_completeness(
            local_markdown="<!-- doctomd:page=1 -->\n",
            cloud_markdown="<!-- doctomd:page=1 -->\n> [!warning]\n> Kein Text.\n",
        )


if __name__ == "__main__":
    unittest.main()
