"""ClipKaro's own tests: python run.py test

Runs tests/ (fast: no video, model or internet). Run them after changing the code: they protect
v1.1's behaviour and the upgrades since (docs/since-v1.1.md).
"""
import sys
import unittest

from .common import ROOT


def main():
    suite = unittest.defaultTestLoader.discover(str(ROOT / 'tests'), top_level_dir=str(ROOT))
    result = unittest.TextTestRunner(verbosity=1).run(suite)
    sys.exit(0 if result.wasSuccessful() else 1)


if __name__ == '__main__':
    main()
