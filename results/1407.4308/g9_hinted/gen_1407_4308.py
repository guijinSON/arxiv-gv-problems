"""Shipping-only wrapper for the structural-hint diagnostic."""

import importlib.util
import os


_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "gen_1407_4308.py")
_SPEC = importlib.util.spec_from_file_location("base_gen_1407_4308", _PATH)
_BASE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_BASE)

for _name in (
    "make_instance", "render", "parse_answer", "verify", "escalate",
    "random_candidate", "search_space", "enumerate_all", "canonical_key",
):
    globals()[_name] = getattr(_BASE, _name)

DIFFICULTY = {"hard": dict(_BASE.DIFFICULTY[_BASE.SHIPPING_DIFFICULTY])}
SHIPPING_DIFFICULTY = "hard"
