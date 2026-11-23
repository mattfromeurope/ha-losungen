"""Import smoke test for all integration modules. Requires Home Assistant."""

from __future__ import annotations

import importlib

import pytest

pytest.importorskip("homeassistant")

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
    importlib.import_module(module)
