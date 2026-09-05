"""Isolated shipping-only wrapper for the structural-hint oracle arm."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from gen_1902_05467 import *  # noqa: F401,F403

DIFFICULTY = {"hard": {"n": 240, "colors": 5, "avg_degree": 14}}
SHIPPING_DIFFICULTY = "hard"
