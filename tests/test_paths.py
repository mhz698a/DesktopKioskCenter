"""Regression tests for paths used by source and PyInstaller builds."""
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import const
from const import resource_path
from css.apply_qss import apply_css_sheet


class ResourcePathTests(unittest.TestCase):
    def test_uses_source_directory_when_not_bundled(self):
        expected = Path(const.__file__).resolve().parent / "icon.png"
        with patch.object(sys, "_MEIPASS", None, create=True):
            self.assertEqual(resource_path("icon.png"), expected)

    def test_uses_pyinstaller_bundle_directory_when_bundled(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            expected = Path(temp_dir) / "icon.png"
            with patch.object(sys, "_MEIPASS", temp_dir, create=True):
                self.assertEqual(resource_path("icon.png"), expected)

    def test_stylesheet_loader_reads_from_bundle_directory(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            css_file = Path(temp_dir) / "css" / "qmainwin.css"
            css_file.parent.mkdir()
            css_file.write_text("QWidget { color: white; }", encoding="utf-8")
            with patch.object(sys, "_MEIPASS", temp_dir, create=True):
                self.assertEqual(
                    apply_css_sheet("css/qmainwin.css"),
                    "QWidget { color: white; }",
                )


if __name__ == "__main__":
    unittest.main()
