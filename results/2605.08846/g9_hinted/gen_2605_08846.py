"""One-rung G9 harness wrapper; the implementation remains in the parent."""
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

_path = Path(__file__).resolve().parents[1] / "gen_2605_08846.py"
_spec = spec_from_file_location("g9_parent_2605_08846", _path)
_parent = module_from_spec(_spec)
_spec.loader.exec_module(_parent)
for _name in dir(_parent):
    if not _name.startswith("__"):
        globals()[_name] = getattr(_parent, _name)
DIFFICULTY = {"easy": dict(_parent.DIFFICULTY["easy"])}

