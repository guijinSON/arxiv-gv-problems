"""Shipping-only wrapper for a G9 diagnostic run."""
import importlib.util
import os

_PARENT = os.path.join(os.path.dirname(os.path.dirname(__file__)), "gen_1005_4874.py")
_spec = importlib.util.spec_from_file_location("_main_generator", _PARENT)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)

make_instance = _mod.make_instance
render = _mod.render
parse_answer = _mod.parse_answer
verify = _mod.verify
DIFFICULTY = {"hard": dict(_mod.DIFFICULTY[_mod.SHIPPING_DIFFICULTY])}


def escalate(params):
    return None

