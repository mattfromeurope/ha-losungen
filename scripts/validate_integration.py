#!/usr/bin/env python3
"""Validate the losungen custom integration without requiring Home Assistant.

Checks: manifest, JSON files, that every translation_key used in sensor.py exists in
strings.json/translations, and that all Python files compile.
"""

from __future__ import annotations

import json
import py_compile
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
COMPONENT = ROOT / "custom_components" / "losungen"

REQUIRED_MANIFEST_KEYS = {
    "domain",
    "name",
    "version",
    "config_flow",
    "iot_class",
    "documentation",
    "issue_tracker",
    "codeowners",
}


def fail(message: str) -> None:
    print(f"FAIL: {message}")
    sys.exit(1)


def main() -> None:
    manifest = json.loads((COMPONENT / "manifest.json").read_text(encoding="utf-8"))
    if manifest.get("domain") != COMPONENT.name:
        fail(f"manifest domain {manifest.get('domain')!r} != folder {COMPONENT.name!r}")
    missing = REQUIRED_MANIFEST_KEYS - manifest.keys()
    if missing:
        fail(f"manifest.json missing keys: {sorted(missing)}")
    if manifest.get("config_flow") is not True:
        fail("manifest.json must enable config_flow")

    hacs = json.loads((ROOT / "hacs.json").read_text(encoding="utf-8"))
    if "name" not in hacs or "homeassistant" not in hacs:
        fail("hacs.json must contain 'name' and 'homeassistant'")

    strings = json.loads((COMPONENT / "strings.json").read_text(encoding="utf-8"))
    translations = {
        path.stem: json.loads(path.read_text(encoding="utf-8"))
        for path in (COMPONENT / "translations").glob("*.json")
    }
    for lang, data in translations.items():
        entity = data.get("entity", {})
        if "sensor" not in entity:
            fail(f"translations/{lang}.json: entity.sensor missing")
        if set(entity["sensor"]) != set(strings.get("entity", {}).get("sensor", {})):
            fail(f"translations/{lang}.json: entity.sensor keys differ from strings.json")

    sensor_py = (COMPONENT / "sensor.py").read_text(encoding="utf-8")
    keys = set(re.findall(r'translation_key="([^"]+)"', sensor_py))
    declared = set(strings.get("entity", {}).get("sensor", {}))
    if keys != declared:
        fail(f"translation_keys in sensor.py {sorted(keys)} != strings.json {sorted(declared)}")

    for py_file in sorted(COMPONENT.rglob("*.py")):
        py_compile.compile(str(py_file), doraise=True)

    for test_file in sorted((ROOT / "tests").glob("*.py")):
        py_compile.compile(str(test_file), doraise=True)
    py_compile.compile(str(ROOT / "scripts" / "validate_integration.py"), doraise=True)

    print("OK: integration valid")
    print(f"  sensors: {sorted(keys)}")
    print(f"  translations: {sorted(translations)}")


if __name__ == "__main__":
    main()
