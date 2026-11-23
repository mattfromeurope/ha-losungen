"""Import-Smoke-Test: Alle Module der Integration müssen sich importieren lassen.

Läuft nur, wenn `homeassistant` installiert ist (CI installiert es; lokal
reicht `pip install homeassistant`). pytest.importorskip überspringt den Test
sauber, falls HA fehlt.
"""

from __future__ import annotations

import importlib

import pytest

pytest.importorskip("homeassistant")

# Alle Python-Module der Integration (Paket + Untermodule).
MODULES = (
    "custom_components.losungen",
    "custom_components.losungen.api",
    "custom_components.losungen.config_flow",
    "custom_components.losungen.const",
    "custom_components.losungen.coordinator",
    "custom_components.losungen.entity",
    "custom_components.losungen.parser",
    "custom_components.losungen.sensor",
)


@pytest.mark.parametrize("module", MODULES)
def test_import(module: str) -> None:
    """Jedes Modul muss ohne Importfehler laden (fängt Tippfehler/Syntaxfehler ab)."""
    importlib.import_module(module)
