"""Compatibility import for the shared analysis engine."""
import sys

from src.common import engine as _engine

sys.modules[__name__] = _engine