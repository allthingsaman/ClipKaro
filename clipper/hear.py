"""The second hearing of the whole video, for careful listening (v2.7; fetch starts it by itself).

    python run.py hear <project>            when careful listening is for this video (it says why not)
    python run.py hear <project> --force    also for other videos (Hindi / Hinglish, NVIDIA card)

See clipper/hearing.py for the whole idea. `parts` then gives each reading helper its stretch of it.
"""
import argparse

from .common import die, load_json, project_dir


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('project')
    ap.add_argument('--force', action='store_true', help='also when it is not a gameplay video or stream')
    a = ap.parse_args()
    from . import hearing
    pdir = project_dir(a.project)
    project = load_json(pdir / 'project.json', {}) or {}
    ok, why = hearing.wanted(project)
    if not ok and not (a.force and 'graphics card' not in why and 'settings' not in why):
        print(f'-> careful listening: no ({why})')
        return
    print('-> careful listening: a second speech model hears the whole video (about 6 minutes per hour of video '
          'on the graphics card) ...', flush=True)
    try:
        out = hearing.hear_full(pdir)
    except Exception as e:
        die(f'the second hearing failed ({type(e).__name__}: {e}). Clipping works without it; '
            f'`python run.py hear {pdir.name}` tries again.')
    n = len((load_json(out) or {}).get('segments', []))
    print(f'-> second hearing: {n} stretches of speech in {out.relative_to(pdir)}; `parts` hands it to the readers')


if __name__ == '__main__':
    main()
