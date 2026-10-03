"""Unit-Tests für den Export eingebetteter Rasterbilder."""

from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from app.image_export import export_embedded_images


class _FakeStream:
    def __init__(self, data: bytes | None, *, decoded_data: bytes | None = None, attrs: dict | None = None) -> None:
        self.data = data
        self.decoded_data = decoded_data if decoded_data is not None else data
        self.attrs = attrs or {}

    def get_rawdata(self) -> bytes | None:
        return self.data

    def get_data(self) -> bytes:
        return self.decoded_data


class _FakePage:
    def __init__(self, images: list[dict], words: list[dict] | None = None) -> None:
        self.images = images
        self.words = words or []

    def extract_words(self, **_kwargs) -> list[dict]:
        return self.words


class _FakePdf:
    def __init__(self, pages: list[_FakePage]) -> None:
        self.pages = pages

    def __enter__(self):
        return self

    def __exit__(self, *_args) -> None:
        return None


class _FakePalette:
    def get_data(self) -> bytes:
        return bytes((255, 0, 0, 0, 255, 0))


class ImageExportTests(unittest.TestCase):
    def setUp(self) -> None:
        self.directory = TemporaryDirectory()
        self.root = Path(self.directory.name)
        self.source = self.root / "Quelle.pdf"
        self.source.write_bytes(b"%PDF")

    def tearDown(self) -> None:
        self.directory.cleanup()

    @patch("app.image_export.pdfplumber.open")
    def test_exports_jpegs_with_stable_page_and_figure_names(self, open_pdf) -> None:
        open_pdf.return_value = _FakePdf([
            _FakePage([{"stream": _FakeStream(b"\xff\xd8\xfferste")}]),
            _FakePage([{"stream": _FakeStream(b"\xff\xd8\xffzweite")}, {"stream": _FakeStream(b"\xff\xd8\xffdritte")}]),
        ])

        outcome = export_embedded_images(source_path=self.source, asset_directory=self.root / "Quelle.assets")

        self.assertEqual([asset.relative_path.as_posix() for asset in outcome.assets], [
            "Quelle.assets/page-001-figure-01.jpg",
            "Quelle.assets/page-002-figure-01.jpg",
            "Quelle.assets/page-002-figure-02.jpg",
        ])
        self.assertEqual((self.root / "Quelle.assets" / "page-002-figure-02.jpg").read_bytes(), b"\xff\xd8\xffdritte")
        description_path = self.root / "Quelle.assets" / "page-002-figure-02-description.md"
        self.assertEqual(
            description_path.read_text(encoding="utf-8"),
            "<!-- doctomd:image-description-template -->\n"
            "# Bildbeschreibung\n\n"
            "## Kurzbeschreibung\n\n"
            "<!-- Was ist auf dem Bild zu sehen? -->\n\n"
            "## Fachliche Einordnung\n\n"
            "<!-- Welche Aussage, welcher Ablauf oder welche Entscheidung ist für die Suche relevant? -->\n\n"
            "## Sichtbare Details\n\n"
            "<!-- Beschrifte Achsen, Legende, Abkürzungen, Werte oder relevante Bildelemente nur, wenn sie klar erkennbar sind. -->\n\n"
            "## Unsicherheiten\n\n"
            "<!-- Fehlende, unlesbare oder nicht sicher interpretierbare Informationen festhalten. -->\n",
        )
        self.assertEqual(
            outcome.assets[2].description_path.as_posix(),
            "Quelle.assets/page-002-figure-02-description.md",
        )
        self.assertEqual(outcome.warnings, ())

    @patch("app.image_export.pdfplumber.open")
    def test_reports_non_jpeg_image_without_creating_asset_directory(self, open_pdf) -> None:
        open_pdf.return_value = _FakePdf([_FakePage([{"stream": _FakeStream(b"not-a-jpeg")}])])

        outcome = export_embedded_images(source_path=self.source, asset_directory=self.root / "Quelle.assets")

        self.assertEqual(outcome.assets, ())
        self.assertEqual([warning.code for warning in outcome.warnings], ["UNSUPPORTED_EMBEDDED_IMAGE"])
        self.assertFalse((self.root / "Quelle.assets").exists())

    @patch("app.image_export.pdfplumber.open")
    def test_creates_no_asset_directory_when_pdf_has_no_embedded_images(self, open_pdf) -> None:
        open_pdf.return_value = _FakePdf([_FakePage([])])

        outcome = export_embedded_images(source_path=self.source, asset_directory=self.root / "Quelle.assets")

        self.assertEqual(outcome.assets, ())
        self.assertFalse((self.root / "Quelle.assets").exists())

    @patch("app.image_export.pdfplumber.open")
    def test_assigns_only_a_nearby_explicit_caption(self, open_pdf) -> None:
        open_pdf.return_value = _FakePdf([_FakePage(
            [{"stream": _FakeStream(b"\xff\xd8\xffbild"), "bottom": 100}],
            [{"text": "Figure", "top": 112, "x0": 10}, {"text": "1: Ablauf", "top": 112, "x0": 55}],
        )])

        outcome = export_embedded_images(source_path=self.source, asset_directory=self.root / "Quelle.assets")

        self.assertEqual(outcome.assets[0].caption, "Figure 1: Ablauf")

    @patch("app.image_export.pdfplumber.open")
    def test_exports_simple_flate_rgb_image_as_png(self, open_pdf) -> None:
        stream = _FakeStream(
            b"compressed",
            decoded_data=bytes((255, 0, 0)) * 60_000,
            attrs={"Filter": "/'FlateDecode'", "ColorSpace": "/'DeviceRGB'", "BitsPerComponent": 8, "Width": 300, "Height": 200},
        )
        open_pdf.return_value = _FakePdf([_FakePage([{"stream": stream}])])

        outcome = export_embedded_images(source_path=self.source, asset_directory=self.root / "Quelle.assets")

        image_path = self.root / "Quelle.assets" / "page-001-figure-01.png"
        self.assertEqual(outcome.warnings, ())
        self.assertEqual(outcome.assets[0].relative_path.as_posix(), "Quelle.assets/page-001-figure-01.png")
        self.assertTrue(image_path.read_bytes().startswith(b"\x89PNG\r\n\x1a\n"))

    @patch("app.image_export.pdfplumber.open")
    def test_handles_missing_raw_data_and_uses_safe_flate_decode(self, open_pdf) -> None:
        stream = _FakeStream(
            None,
            decoded_data=bytes((255, 0, 0)) * 60_000,
            attrs={"Filter": "/'FlateDecode'", "ColorSpace": "/'DeviceRGB'", "BitsPerComponent": 8, "Width": 300, "Height": 200},
        )
        open_pdf.return_value = _FakePdf([_FakePage([{"stream": stream}])])

        outcome = export_embedded_images(source_path=self.source, asset_directory=self.root / "Quelle.assets")

        self.assertEqual(outcome.warnings, ())
        self.assertTrue((self.root / "Quelle.assets" / "page-001-figure-01.png").is_file())

    @patch("app.image_export.pdfplumber.open")
    def test_exports_decoded_jpeg_from_filter_chain(self, open_pdf) -> None:
        stream = _FakeStream(
            b"flate-wrapped-data",
            decoded_data=b"\xff\xd8\xffdecoded-jpeg",
            attrs={"Filter": "[/'FlateDecode', /'DCTDecode']", "Width": 600, "Height": 400},
        )
        open_pdf.return_value = _FakePdf([_FakePage([{"stream": stream}])])

        outcome = export_embedded_images(source_path=self.source, asset_directory=self.root / "Quelle.assets")

        self.assertEqual(outcome.warnings, ())
        self.assertEqual((self.root / "Quelle.assets" / "page-001-figure-01.jpg").read_bytes(), b"\xff\xd8\xffdecoded-jpeg")

    @patch("app.image_export.pdfplumber.open")
    def test_skips_small_decorative_images_without_warning(self, open_pdf) -> None:
        stream = _FakeStream(b"\xff\xd8\xfflogo", attrs={"Width": 219, "Height": 108})
        open_pdf.return_value = _FakePdf([_FakePage([{"stream": stream}])])

        outcome = export_embedded_images(source_path=self.source, asset_directory=self.root / "Quelle.assets")

        self.assertEqual(outcome.assets, ())
        self.assertEqual(outcome.warnings, ())

    @patch("app.image_export.resolve1", return_value=_FakePalette())
    @patch("app.image_export.pdfplumber.open")
    def test_exports_simple_indexed_flate_image_as_png(self, open_pdf, _resolve_palette) -> None:
        stream = _FakeStream(
            b"compressed",
            decoded_data=bytes((0, 1)) * 30_000,
            attrs={"Filter": "/'FlateDecode'", "ColorSpace": ["/'Indexed'", "/'DeviceRGB'", 1, object()], "BitsPerComponent": 8, "Width": 300, "Height": 200},
        )
        open_pdf.return_value = _FakePdf([_FakePage([{"stream": stream}])])

        outcome = export_embedded_images(source_path=self.source, asset_directory=self.root / "Quelle.assets")

        self.assertEqual(outcome.warnings, ())
        self.assertTrue((self.root / "Quelle.assets" / "page-001-figure-01.png").read_bytes().startswith(b"\x89PNG\r\n\x1a\n"))
