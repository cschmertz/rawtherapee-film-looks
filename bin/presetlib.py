#!/usr/bin/env python3
"""Shared discovery, validation, and profile-materialization helpers."""

from __future__ import annotations

import configparser
import re
from dataclasses import dataclass
from pathlib import Path


VARIANT_RE = re.compile(r" (?P<number>\d{2}) - (?P<label>.+)\.pp3$")
CLUT_LINE_RE = re.compile(r"^ClutFilename=(.*)$", re.MULTILINE)
REQUIRED_SECTIONS = {
    "Version",
    "Exposure",
    "White Balance",
    "HLRecovery",
    "LensProfile",
    "Color Management",
    "RAW",
    "PostDemosaicSharpening",
}


class PresetError(ValueError):
    """A repository or look violates the preset contract."""


@dataclass(frozen=True)
class FxDose:
    grain_strength: float
    grain_size: float
    halation: float


@dataclass(frozen=True)
class Preset:
    number: str
    label: str
    path: Path
    clut_name: str | None


@dataclass(frozen=True)
class Look:
    name: str
    path: Path
    presets: dict[str, Preset]
    effects: dict[str, FxDose]


def repository_root() -> Path:
    return Path(__file__).resolve().parent.parent


def discover_look_names(root: Path) -> list[str]:
    return sorted(
        path.name
        for path in root.iterdir()
        if path.is_dir() and (path / "rawtherapee").is_dir()
    )


def _read_profile(path: Path) -> tuple[configparser.ConfigParser, str | None]:
    parser = configparser.ConfigParser(interpolation=None, strict=True)
    parser.optionxform = str
    try:
        with path.open(encoding="utf-8") as handle:
            parser.read_file(handle)
    except (OSError, configparser.Error) as exc:
        raise PresetError(f"cannot parse {path}: {exc}") from exc

    missing = sorted(REQUIRED_SECTIONS - set(parser.sections()))
    if missing:
        raise PresetError(f"{path}: missing sections: {', '.join(missing)}")

    try:
        auto = parser.getboolean("Exposure", "Auto", fallback=None)
        histogram = parser.getboolean("Exposure", "HistogramMatching", fallback=None)
    except ValueError as exc:
        raise PresetError(f"{path}: invalid exposure baseline boolean: {exc}") from exc
    if auto is None or histogram is None or auto == histogram:
        raise PresetError(
            f"{path}: Exposure Auto and HistogramMatching must be opposite booleans"
        )
    if auto and not parser.has_option("Exposure", "Clip"):
        raise PresetError(f"{path}: automatic exposure baseline requires Clip")

    clut_value = parser.get("Film Simulation", "ClutFilename", fallback="").strip()
    return parser, Path(clut_value).name if clut_value else None


def _read_effects(path: Path) -> dict[str, FxDose]:
    if not path.is_file():
        raise PresetError(f"missing effects file: {path}")

    effects: dict[str, FxDose] = {}
    for line_number, raw_line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = raw_line.split("#", 1)[0].strip()
        if not line:
            continue
        fields = line.split()
        if len(fields) != 4:
            raise PresetError(
                f"{path}:{line_number}: expected variant plus 3 numeric fields"
            )
        number, *raw_values = fields
        if not re.fullmatch(r"\d{2}", number):
            raise PresetError(f"{path}:{line_number}: invalid variant {number!r}")
        if number in effects:
            raise PresetError(f"{path}:{line_number}: duplicate variant {number}")
        try:
            grain_strength, grain_size, halation = map(float, raw_values)
        except ValueError as exc:
            raise PresetError(f"{path}:{line_number}: effect doses must be numeric") from exc
        if not 0 <= grain_strength <= 50:
            raise PresetError(f"{path}:{line_number}: grain strength must be 0..50")
        if not 0 < grain_size <= 10:
            raise PresetError(f"{path}:{line_number}: grain size must be >0 and <=10")
        if not 0 <= halation <= 2:
            raise PresetError(f"{path}:{line_number}: halation must be 0..2")
        effects[number] = FxDose(grain_strength, grain_size, halation)
    if not effects:
        raise PresetError(f"{path}: no effect doses found")
    return effects


def load_look(root: Path, name: str, *, require_cluts: bool = True) -> Look:
    if name not in discover_look_names(root):
        choices = ", ".join(discover_look_names(root))
        raise PresetError(f"unknown look {name!r}; choose one of: {choices}")

    look_path = root / name
    presets: dict[str, Preset] = {}
    profile_paths = sorted((look_path / "rawtherapee").glob("*.pp3"))
    if not profile_paths:
        raise PresetError(f"{look_path}: no .pp3 profiles found")

    for path in profile_paths:
        match = VARIANT_RE.search(path.name)
        if not match:
            raise PresetError(
                f"{path}: filename must contain ' NN - Label.pp3' with a two-digit ID"
            )
        number = match.group("number")
        if number in presets:
            raise PresetError(f"{look_path}: duplicate profile variant {number}")
        _, clut_name = _read_profile(path)
        if clut_name:
            raw_value = CLUT_LINE_RE.search(path.read_text(encoding="utf-8"))
            if raw_value is None:
                raise PresetError(f"{path}: malformed ClutFilename")
            configured = Path(raw_value.group(1).strip())
            if (
                configured.is_absolute()
                or ".." in configured.parts
                or len(configured.parts) != 2
                or configured.parts[0] != "cluts"
            ):
                raise PresetError(
                    f"{path}: ClutFilename must be portable (cluts/<filename>)"
                )
            clut_path = root / "cluts" / clut_name
            if require_cluts and not clut_path.is_file():
                raise PresetError(
                    f"{path}: missing CLUT {clut_path}; see README setup instructions"
                )
        presets[number] = Preset(number, match.group("label"), path, clut_name)

    effects = _read_effects(look_path / "fx.conf")
    preset_ids, effect_ids = set(presets), set(effects)
    if preset_ids != effect_ids:
        details = []
        if preset_ids - effect_ids:
            details.append(f"missing fx for {sorted(preset_ids - effect_ids)}")
        if effect_ids - preset_ids:
            details.append(f"orphan fx for {sorted(effect_ids - preset_ids)}")
        raise PresetError(f"{look_path}: {'; '.join(details)}")
    return Look(name, look_path, presets, effects)


def materialize_profile(preset: Preset, root: Path, destination: Path) -> Path:
    """Write a RawTherapee-ready profile with an absolute local CLUT path."""
    text = preset.path.read_text(encoding="utf-8")
    if preset.clut_name:
        clut_path = (root / "cluts" / preset.clut_name).resolve()
        if not clut_path.is_file():
            raise PresetError(f"missing CLUT: {clut_path}")
        text, count = CLUT_LINE_RE.subn(f"ClutFilename={clut_path}", text, count=1)
        if count != 1:
            raise PresetError(f"{preset.path}: could not materialize ClutFilename")
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(text, encoding="utf-8")
    return destination


def optional_clut_names(root: Path) -> set[str]:
    manifest = root / "cluts" / "OPTIONAL.txt"
    if not manifest.is_file():
        return set()
    return {
        line.strip()
        for line in manifest.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    }


def validate_repository(root: Path, *, strict_assets: bool = False) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    optional = optional_clut_names(root)
    versions: set[tuple[str, str]] = set()

    names = discover_look_names(root)
    if not names:
        errors.append("no look directories found")
        return errors, warnings

    for name in names:
        try:
            look = load_look(root, name, require_cluts=False)
        except PresetError as exc:
            errors.append(str(exc))
            continue
        for preset in look.presets.values():
            try:
                parser, _ = _read_profile(preset.path)
                app_version = parser.get("Version", "AppVersion", fallback="")
                profile_version = parser.get("Version", "Version", fallback="")
                if not app_version or not profile_version:
                    errors.append(f"{preset.path}: incomplete Version section")
                else:
                    versions.add((app_version, profile_version))
            except PresetError as exc:
                errors.append(str(exc))
            if preset.clut_name:
                clut_path = root / "cluts" / preset.clut_name
                if not clut_path.is_file():
                    message = f"missing CLUT: {clut_path}"
                    if preset.clut_name in optional and not strict_assets:
                        warnings.append(message)
                    else:
                        errors.append(message)

    if len(versions) > 1:
        errors.append(f"profiles use inconsistent RawTherapee versions: {sorted(versions)}")
    return errors, warnings
