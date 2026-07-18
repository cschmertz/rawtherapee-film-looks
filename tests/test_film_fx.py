from __future__ import annotations

import hashlib
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np
from PIL import Image, ImageCms


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "bin"))

from film_fx import add_grain, process_image  # noqa: E402


class FilmEffectsTests(unittest.TestCase):
    def test_grain_is_repeatable_with_a_seed(self) -> None:
        rgb = np.full((40, 60, 3), 128, dtype=np.uint8)
        first = add_grain(rgb, strength=12, size=1.7, seed=42)
        second = add_grain(rgb, strength=12, size=1.7, seed=42)
        different = add_grain(rgb, strength=12, size=1.7, seed=43)
        np.testing.assert_array_equal(first, second)
        self.assertFalse(np.array_equal(first, different))

    def test_process_image_is_deterministic_and_preserves_icc(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            source = directory / "source.tif"
            first = directory / "first.jpg"
            second = directory / "second.jpg"
            icc = ImageCms.ImageCmsProfile(ImageCms.createProfile("sRGB")).tobytes()
            Image.new("RGB", (96, 64), (210, 160, 90)).save(
                source, format="TIFF", icc_profile=icc
            )
            for destination in (first, second):
                process_image(
                    source,
                    destination,
                    grain_strength=8,
                    grain_size=1.6,
                    halation=0.4,
                    seed=12345,
                )
            self.assertEqual(
                hashlib.sha256(first.read_bytes()).digest(),
                hashlib.sha256(second.read_bytes()).digest(),
            )
            with Image.open(first) as result:
                self.assertEqual(result.size, (96, 64))
                self.assertTrue(result.info.get("icc_profile"))


if __name__ == "__main__":
    unittest.main()
