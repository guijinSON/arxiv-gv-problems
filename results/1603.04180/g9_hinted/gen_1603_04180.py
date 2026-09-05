"""Single-rung wrapper used only by scripts/harden.py for the hinted G9 arm."""
import importlib.util
import os

_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "gen_1603_04180.py")
_SPEC = importlib.util.spec_from_file_location("gen_1603_04180_base_hinted", _PATH)
_BASE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_BASE)
for _NAME in dir(_BASE):
    if not _NAME.startswith("__"):
        globals()[_NAME] = getattr(_BASE, _NAME)
DIFFICULTY = {"easy": dict(_BASE.DIFFICULTY[_BASE.SHIPPING_DIFFICULTY])}
