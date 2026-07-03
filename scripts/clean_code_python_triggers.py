from __future__ import annotations

from clean_code_trigger_catalog import load_trigger_catalog

TRIGGER_CATALOG = load_trigger_catalog()
PYLINT_TRIGGERS = TRIGGER_CATALOG["pylint"]
RUFF_TRIGGERS = TRIGGER_CATALOG["ruff"]
