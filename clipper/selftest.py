"""ClipKaro's own tests.

    python run.py test           the fast tests (a second or two: no video, model or internet)
    python run.py test --full    also one tiny made-up video run from start to end: cut, edit and qa
                                 (about 30 seconds; needs ffmpeg)

Run them after changing the code: they protect v1.1's behaviour and the upgrades since
(docs/since-v1.1.md). Run --full before a release.
"""
import argparse
import sys
import unittest

from .common import ROOT


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--full', action='store_true', help='also run the tiny video from start to end')
    a = ap.parse_args()
    loader = unittest.defaultTestLoader
    suite = loader.discover(str(ROOT / 'tests'), pattern='test_clipkaro.py', top_level_dir=str(ROOT))
    if a.full:
        suite.addTests(loader.discover(str(ROOT / 'tests'), pattern='test_end_to_end.py', top_level_dir=str(ROOT)))
    result = unittest.TextTestRunner(verbosity=1).run(suite)
    sys.exit(0 if result.wasSuccessful() else 1)


if __name__ == '__main__':
    main()
