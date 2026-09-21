"""Run the shared offline tests from any working directory."""

from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
# Prefer this checkout and its fake adapter, never another installed package.
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))


def run_checks(names=None):
    loader = unittest.TestLoader()
    suite = (
        loader.discover(str(ROOT / "tests")) if names is None else loader.loadTestsFromNames(names)
    )
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    raise SystemExit(0 if result.wasSuccessful() else 1)
