"""Frame sheets, step 1 (v2.7, gameplay and live streams): the overview, one frame every 10 seconds.

    python run.py watch <project>    (fetch does it by itself; this is for videos fetched before v2.7)

Then `parts` gives each reading helper the sheets of its stretch. See clipper/watch.py.
"""
import argparse

from .common import load_json, project_dir


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('project')
    a = ap.parse_args()
    from . import watch
    pdir = project_dir(a.project)
    project = load_json(pdir / 'project.json', {}) or {}
    ok, why = watch.wanted(project)
    if not ok:
        print(f'-> frame sheets: no ({why})')
        return
    folder = watch.overview(pdir, project)
    n = (load_json(folder / 'meta.json') or {}).get('count', 0)
    print(f'-> frame overview: {n} frames ({why}); `parts` hands the sheets to the readers')


if __name__ == '__main__':
    main()
