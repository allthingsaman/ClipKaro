"""Frame sheets, step 3 (v2.7, gameplay and live streams): the events seen in the close-ups, into the clips.

    python run.py events <project>          after the final clips.json
    python run.py events <project> --dry    only show what would change

A picked clip that starts on the reaction now starts 1.5 s before its event (and keeps the event whole: no
pause cutting inside it); an event no clip shows becomes a new clip (write its posting text). For each, an
exact-frame sheet frames/exact-<id>.jpg (4 frames a second) to put the start and the sound on the right
frame: set "event_at" and the clip's "sfx" from it. See clipper/watch.py.
"""
import argparse

from .common import die, project_dir


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('project')
    ap.add_argument('--dry', action='store_true', help='only show what would change')
    a = ap.parse_args()
    from . import watch
    pdir = project_dir(a.project)
    if not (pdir / 'frames' / 'events.json').exists():
        die(f'no events yet: python run.py zoom {pdir.name} (twice, with the eventfinder helpers between)')
    done = watch.apply_events(pdir, dry=a.dry)
    if not done:
        print('-> no events to add')
        return
    for what, cid, ev in done:
        print(f"   clip {cid}: {what}  ({ev['event_at']:.1f} s, {ev['where']}: {ev['title'] or ev['why']})")
    if not a.dry:
        print('-> look at each frames/exact-<id>.jpg: set the clip\'s "event_at" to the frame where it starts and put '
              'its "sfx" cue there; new clips need their posting text (title, caption, post). Then cut and edit.')


if __name__ == '__main__':
    main()
