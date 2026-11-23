#!/usr/bin/env python3
"""Validiert die Integration OHNE dass Home Assistant installiert sein muss.

Prüft:
  - manifest.json: Domain stimmt mit dem Ordnernamen überein, Pflicht-Keys da,
    config_flow aktiviert
  - hacs.json: name + homeassistant (Mindestversion) vorhanden
  - strings.json und translations/*.json: gültiges JSON, gleiche Sensor-Keys
  - sensor.py: jeder verwendete translation_key existiert in strings.json
  - alle Python-Dateien (Integration, Tests, dieses Skript) kompilieren

Aufruf: python scripts/validate_integration.py  (Exit-Code 0 = OK, 1 = Fehler)
"""

from __future__ import annotations

import json
import py_compile
import re
import sys
from pathlib import Path

# Root des Repos = eine Ebene über scripts/.
ROOT = Path(__file__).resolve().parent.parent
# Pfad zum Integrationsmodul.
COMPONENT = ROOT / "custom_components" / "losungen"

# Keys, die das HA-Manifest für Custom Integrations zwingend braucht.
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
    """Gibt eine Fehlermeldung aus und beendet das Skript mit Exit-Code 1."""
    print(f"FAIL: {message}")
    sys.exit(1)


def main() -> None:
    # --- manifest.json -----------------------------------------------------
    manifest = json.loads((COMPONENT / "manifest.json").read_text(encoding="utf-8"))
    # Die Domain muss exakt dem Verzeichnisnamen entsprechen, sonst lädt HA
    # die Integration nicht.
    if manifest.get("domain") != COMPONENT.name:
        fail(f"manifest domain {manifest.get('domain')!r} != Ordner {COMPONENT.name!r}")
    missing = REQUIRED_MANIFEST_KEYS - manifest.keys()
    if missing:
        fail(f"manifest.json fehlen Keys: {sorted(missing)}")
    if manifest.get("config_flow") is not True:
        fail("manifest.json muss config_flow=true setzen (Einrichtung über die UI)")

    # --- hacs.json ----------------------------------------------------------
    hacs = json.loads((ROOT / "hacs.json").read_text(encoding="utf-8"))
    if "name" not in hacs or "homeassistant" not in hacs:
        fail("hacs.json braucht 'name' und 'homeassistant' (Mindestversion)")

    # --- strings.json + Übersetzungen ---------------------------------------
    strings = json.loads((COMPONENT / "strings.json").read_text(encoding="utf-8"))
    # Alle *.json im translations/-Ordner laden; Dateiname = Sprachcode.
    translations = {
        path.stem: json.loads(path.read_text(encoding="utf-8"))
        for path in (COMPONENT / "translations").glob("*.json")
    }
    for lang, data in translations.items():
        entity = data.get("entity", {})
        if "sensor" not in entity:
            fail(f"translations/{lang}.json: entity.sensor fehlt")
        # Jede Übersetzung muss dieselben Sensor-Keys wie strings.json haben.
        if set(entity["sensor"]) != set(strings.get("entity", {}).get("sensor", {})):
            fail(f"translations/{lang}.json: entity.sensor-Keys weichen von strings.json ab")

    # --- sensor.py: translation_keys vs. strings.json ------------------------
    sensor_py = (COMPONENT / "sensor.py").read_text(encoding="utf-8")
    # Alle translation_key="..." aus sensor.py per Regex auslesen.
    keys = set(re.findall(r'translation_key="([^"]+)"', sensor_py))
    declared = set(strings.get("entity", {}).get("sensor", {}))
    if keys != declared:
        fail(f"translation_keys in sensor.py {sorted(keys)} != strings.json {sorted(declared)}")

    # --- Python-Dateien kompilieren ------------------------------------------
    # py_compile prüft Syntax (und Importe auf oberster Ebene nicht, aber
    # Tippfehler/Syntaxfehler fliegen hier auf). doraise=True -> Exception bei Fehler.
    for py_file in sorted(COMPONENT.rglob("*.py")):
        py_compile.compile(str(py_file), doraise=True)
    for test_file in sorted((ROOT / "tests").glob("*.py")):
        py_compile.compile(str(test_file), doraise=True)
    py_compile.compile(str(ROOT / "scripts" / "validate_integration.py"), doraise=True)

    print("OK: Integration valid")
    print(f"  Sensoren: {sorted(keys)}")
    print(f"  Übersetzungen: {sorted(translations)}")


if __name__ == "__main__":
    main()
