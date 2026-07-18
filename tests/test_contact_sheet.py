from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

from PIL import Image, ImageCms


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "bin"))

from contact_sheet import build_contact_sheets  # noqa: E402


class ContactSheetTests(unittest.TestCase):
    def test_uses_only_supplied_renders_and_embeds_srgb(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            icc = ImageCms.ImageCmsProfile(ImageCms.createProfile("sRGB")).tobytes()
            current = []
            for number, color in (("01", (190, 80, 50)), ("02", (50, 100, 190))):
                path = directory / f"photo_{number}.jpg"
                Image.new("RGB", (120, 80), color).save(path, icc_profile=icc)
                current.append(path)
            Image.new("RGB", (120, 80), (0, 255, 0)).save(directory / "photo_03.jpg")

            outputs = build_contact_sheets(directory, renders=current)
            self.assertEqual(outputs, [directory / "contact" / "photo_contact.jpg"])
            with Image.open(outputs[0]) as sheet:
                self.assertTrue(sheet.info.get("icc_profile"))
                self.assertLess(sheet.width, 400)

    def test_single_variant_removes_an_affected_stale_sheet(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            current = directory / "photo_01.jpg"
            Image.new("RGB", (120, 80), (100, 100, 100)).save(current)
            stale = directory / "contact" / "photo_contact.jpg"
            stale.parent.mkdir()
            Image.new("RGB", (10, 10)).save(stale)

            outputs = build_contact_sheets(
                directory,
                renders=[current],
                replace_bases={"photo"},
            )
            self.assertEqual(outputs, [])
            self.assertFalse(stale.exists())


if __name__ == "__main__":
    unittest.main()
