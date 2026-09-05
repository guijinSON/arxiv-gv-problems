"""Scratch wrapper exposing only the intended hard preset for the G9 placebo arm."""
import importlib.util
import os

_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "gen_2511_06843.py")
_SPEC = importlib.util.spec_from_file_location("gen_2511_06843_base", _PATH)
_BASE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_BASE)
for _NAME in dir(_BASE):
    if not _NAME.startswith("__"):
        globals()[_NAME] = getattr(_BASE, _NAME)
DIFFICULTY = {"hard": dict(_BASE.DIFFICULTY["hard"])}
SHIPPING_DIFFICULTY = "hard"
