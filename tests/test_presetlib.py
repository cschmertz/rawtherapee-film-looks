from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "bin"))

from presetlib import (  # noqa: E402
    load_look,
    materialize_profile,
    validate_repository,
)


class PresetLibraryTests(unittest.TestCase):
    def test_repository_contract(self) -> None:
        errors, warnings = validate_repository(ROOT)
        self.assertEqual(errors, [])
        self.assertLessEqual(len(warnings), 4)
        self.assertEqual(len(load_look(ROOT, "boardwalk").presets), 4)

    def test_materializes_clut_profile_without_changing_source(self) -> None:
        look = load_look(ROOT, "portra")
        preset = look.presets["01"]
        source_text = preset.path.read_text(encoding="utf-8")
        self.assertIn("ClutFilename=cluts/", source_text)
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / preset.path.name
            materialize_profile(preset, ROOT, output)
            materialized = output.read_text(encoding="utf-8")
            self.assertIn(f"ClutFilename={ROOT / 'cluts'}", materialized)
        self.assertEqual(preset.path.read_text(encoding="utf-8"), source_text)


if __name__ == "__main__":
    unittest.main()
