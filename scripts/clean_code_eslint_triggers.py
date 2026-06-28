from __future__ import annotations

from clean_code_trigger_catalog import load_trigger_catalog

ESLINT_TRIGGERS = load_trigger_catalog()["eslint"]
