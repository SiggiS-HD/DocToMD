"""Regressionen für portable Links in versionierter Dokumentation."""

from __future__ import annotations

from pathlib import Path
import re
import unittest
from urllib.parse import urlparse


REPOSITORY_ROOT = Path(__file__).resolve().parent.parent
TOP_LEVEL_DOCUMENTS = (
    "AGENTS.md",
    "ENGINEERING_NOTES.md",
    "PROJECT.md",
    "README.md",
    "TASKS.md",
)
WIKI_LINK_PATTERN = re.compile(r"\[\[[^\]]+\]\]")
MARKDOWN_LINK_PATTERN = re.compile(
    r"(?<!!)\[[^\]]*\]\((?P<destination><[^>]+>|[^)\s]+)(?:\s+\"[^\"]*\")?\)"
)


def _versioned_documentation_files() -> tuple[Path, ...]:
    top_level = tuple(REPOSITORY_ROOT / name for name in TOP_LEVEL_DOCUMENTS)
    documentation = tuple(sorted((REPOSITORY_ROOT / "docs").glob("*.md")))
    fixtures = tuple(sorted((REPOSITORY_ROOT / "tests" / "fixtures").glob("*.md")))
    return top_level + documentation + fixtures


class DocumentationLinkTests(unittest.TestCase):
    def test_versioned_documentation_uses_no_wiki_links(self) -> None:
        offenders = [
            str(path.relative_to(REPOSITORY_ROOT))
            for path in _versioned_documentation_files()
            if WIKI_LINK_PATTERN.search(path.read_text(encoding="utf-8"))
        ]

        self.assertEqual(offenders, [])

    def test_relative_markdown_link_targets_exist(self) -> None:
        missing_targets: list[str] = []

        for document in _versioned_documentation_files():
            text = document.read_text(encoding="utf-8")
            for match in MARKDOWN_LINK_PATTERN.finditer(text):
                destination = match.group("destination").strip("<>")
                parsed = urlparse(destination)
                if parsed.scheme or parsed.netloc or destination.startswith("#"):
                    continue

                target = document.parent / parsed.path
                if not target.is_file():
                    source = document.relative_to(REPOSITORY_ROOT)
                    missing_targets.append(f"{source}: {destination}")

        self.assertEqual(missing_targets, [])


if __name__ == "__main__":
    unittest.main()
