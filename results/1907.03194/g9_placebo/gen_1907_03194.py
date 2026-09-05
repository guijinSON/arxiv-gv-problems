"""Shipping-only wrapper for the script-owned G9 placebo-hint arm."""
import importlib.util
import os

_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "gen_1907_03194.py")
_spec = importlib.util.spec_from_file_location("g9_base_placebo", _path)
_base = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_base)
for _name in dir(_base):
    if not _name.startswith("__"):
        globals()[_name] = getattr(_base, _name)
DIFFICULTY = {"hard": dict(_base.DIFFICULTY[_base.SHIPPING_DIFFICULTY])}
SHIPPING_DIFFICULTY = "hard"
