from __future__ import annotations

import hashlib
import os
import subprocess
import tempfile
import textwrap
import unittest
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
PROCESS = ROOT / "bin" / "process.sh"


FAKE_RTCLI = """\
#!/usr/bin/env python3
import os
import sys
from pathlib import Path
from PIL import Image, ImageCms

if os.environ.get("FAKE_RT_FAIL"):
    print("synthetic RawTherapee failure", file=sys.stderr)
    raise SystemExit(17)
if "-v" in sys.argv:
    print("RawTherapee, version 5.12-test")
    raise SystemExit(0)
destination = Path(sys.argv[sys.argv.index("-o") + 1])
profile = Path(sys.argv[sys.argv.index("-p") + 1])
if "ClutFilename=cluts/" in profile.read_text():
    print("profile was not materialized", file=sys.stderr)
    raise SystemExit(18)
icc = ImageCms.ImageCmsProfile(ImageCms.createProfile("sRGB")).tobytes()
Image.new("RGB", (96, 64), (210, 160, 90)).save(
    destination, format="TIFF", compression="tiff_deflate", icc_profile=icc
)
"""


class ProcessTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.directory = Path(self.temporary.name)
        self.cli = self.directory / "fake-rtcli"
        self.cli.write_text(textwrap.dedent(FAKE_RTCLI), encoding="utf-8")
        self.cli.chmod(0o755)
        self.environment = os.environ.copy()
        self.environment["RAWTHERAPEE_CLI"] = str(self.cli)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def run_process(self, *arguments: str, environment: dict[str, str] | None = None):
        return subprocess.run(
            [str(PROCESS), *arguments],
            cwd=ROOT,
            env=environment or self.environment,
            capture_output=True,
            text=True,
            check=False,
        )

    def test_rejects_empty_folder_and_unknown_variant(self) -> None:
        empty = self.directory / "empty"
        empty.mkdir()
        result = self.run_process(str(empty))
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("no .NEF files", result.stderr)

        photos = self.directory / "photos"
        photos.mkdir()
        (photos / "photo.NEF").write_bytes(b"raw")
        result = self.run_process(str(photos), "99")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("has no variant 99", result.stderr)

    def test_selected_variant_is_deterministic_and_clears_stale_derivatives(self) -> None:
        photos = self.directory / "photos"
        photos.mkdir()
        (photos / "photo.NEF").write_bytes(b"stable fake raw content")
        output = photos / "renders" / "boardwalk"
        contact = output / "contact" / "photo_contact.jpg"
        web = output / "web" / "photo_01.jpg"
        contact.parent.mkdir(parents=True)
        web.parent.mkdir(parents=True)
        Image.new("RGB", (10, 10)).save(contact)
        Image.new("RGB", (10, 10)).save(web)

        first = self.run_process(str(photos), "01")
        self.assertEqual(first.returncode, 0, first.stderr)
        rendered = output / "photo_01.jpg"
        with Image.open(rendered) as image:
            pixel_digest = hashlib.sha256(image.tobytes()).digest()
        self.assertFalse(contact.exists())
        self.assertFalse(web.exists())

        second = self.run_process(str(photos), "01")
        self.assertEqual(second.returncode, 0, second.stderr)
        with Image.open(rendered) as image:
            self.assertEqual(hashlib.sha256(image.tobytes()).digest(), pixel_digest)

    def test_multi_variant_run_builds_current_contact_sheet_and_web_exports(self) -> None:
        photos = self.directory / "photos"
        photos.mkdir()
        (photos / "photo.NEF").write_bytes(b"fake raw")
        result = self.run_process(str(photos), "cinema", "all", "--web")
        self.assertEqual(result.returncode, 0, result.stderr)
        output = photos / "renders" / "cinema"
        variant_count = len(list((ROOT / "cinema" / "rawtherapee").glob("*.pp3")))
        self.assertEqual(len(list(output.glob("photo_*.jpg"))), variant_count)
        self.assertEqual(
            len(list((output / "web").glob("photo_*.jpg"))), variant_count
        )
        self.assertTrue((output / "contact" / "photo_contact.jpg").is_file())

    def test_clut_profile_is_materialized_before_rawtherapee(self) -> None:
        photos = self.directory / "photos"
        photos.mkdir()
        (photos / "photo.NEF").write_bytes(b"fake raw")
        result = self.run_process(str(photos), "portra", "01")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue((photos / "renders" / "portra" / "photo_01.jpg").is_file())

    def test_rawtherapee_failure_keeps_diagnostics(self) -> None:
        photos = self.directory / "photos"
        photos.mkdir()
        (photos / "photo.NEF").write_bytes(b"fake raw")
        environment = self.environment.copy()
        environment["FAKE_RT_FAIL"] = "1"
        result = self.run_process(str(photos), "01", environment=environment)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("synthetic RawTherapee failure", result.stderr)
        self.assertIn("exit 17", result.stderr)


if __name__ == "__main__":
    unittest.main()
