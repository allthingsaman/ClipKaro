"""Careful listening, step 2 (v2.7): every picked clip heard again by two more speech models, and the
word-check packets for the `clipkaro-wordcheck` helpers.

    python run.py rehear <project>                 every clip in clips.json
    python run.py rehear <project> --clips 3,7     only some
    python run.py rehear <project> --packets-only  the packets again, without hearing anything

Then start one clipkaro-wordcheck helper per packet (wordcheck/batch-NN.txt), and `python run.py wordcheck
<project>` applies their answers. See clipper/hearing.py.
"""
import argparse

from .common import load_json, project_dir


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('project')
    ap.add_argument('--clips', default=None, help='comma list of clip ids, e.g. 1,3')
    ap.add_argument('--packets-only', action='store_true', help='only write the packets again')
    ap.add_argument('--force', action='store_true', help='also when careful listening is not for this video')
    a = ap.parse_args()
    from . import hearing
    pdir = project_dir(a.project)
    project = load_json(pdir / 'project.json', {}) or {}
    ok, why = hearing.wanted(project)
    if not ok and not a.force:
        print(f'-> careful listening: no ({why}); the usual caption check (`run.py captions`) is enough')
        return
    ids = {int(x) for x in a.clips.split(',')} if a.clips else None
    if not a.packets_only:
        print('-> every picked clip is heard again by two more speech models (about 5 s per clip) ...', flush=True)
        hearing.hear_clips(pdir, ids)
    files = hearing.packets(pdir, ids=ids)
    print(f'-> {len(files)} word-check packet(s): ' + ', '.join(str(f.relative_to(pdir)) for f in files))
    print(f'next: one clipkaro-wordcheck helper per packet, all at once (prompt: the packet\'s path), then '
          f'python run.py wordcheck {pdir.name}')


if __name__ == '__main__':
    main()
