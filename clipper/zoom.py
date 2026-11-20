"""Frame sheets, step 2 (v2.7, gameplay and live streams): close-ups of the spots the reading helpers named.

    python run.py zoom <project>           1st time: close-up sheets and packets (frames/zoom-batch-NN.txt);
                                            run again when every packet has its answer: frames/events.json
    python run.py zoom <project> --fresh   make the close-ups again (the readers named new spots)

Start one clipkaro-eventfinder helper per packet, all at once, between the two runs. See clipper/watch.py.
"""
import argparse

from .common import load_json, project_dir


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('project')
    ap.add_argument('--fresh', action='store_true', help='make the close-ups again')
    a = ap.parse_args()
    from . import watch
    pdir = project_dir(a.project)
    ok, why = watch.wanted(load_json(pdir / 'project.json', {}) or {})
    if not ok:
        print(f'-> frame sheets: no ({why})')
        return
    packets = sorted((pdir / 'frames').glob('zoom-batch-*.txt'))
    answered = [p for p in packets if p.with_suffix('.json').exists()]
    if packets and not a.fresh:
        if len(answered) < len(packets):
            todo = [str(p.relative_to(pdir)) for p in packets if p not in answered]
            print(f'-> waiting for {len(todo)} eventfinder answer(s): ' + ', '.join(todo))
            return
        events = watch.collect(pdir)
        print(f'-> {len(events)} event(s) worth a clip (frames/events.json):')
        for e in events:
            print(f"   {e['event_at']:9.1f} s  to {e['end']:9.1f}  {e['where']:6s}  {e['title']}  ({e['why']})")
        print(f'next: after the final clips.json, python run.py events {pdir.name}')
        return
    spots = watch.requests(pdir)
    if not spots:
        print('-> no spots to look at closer: the readers named none (look_closer in parts/part-NN.json)')
        return
    print(f'-> close-ups of {len(spots)} spot(s) the readers named (one frame a second) ...', flush=True)
    packets = watch.zoom(pdir)
    print(f'-> {len(packets)} packet(s): ' + ', '.join(str(p.relative_to(pdir)) for p in packets))
    print(f'next: one clipkaro-eventfinder helper per packet, all at once (prompt: the packet\'s path), then '
          f'python run.py zoom {pdir.name} again')


if __name__ == '__main__':
    main()
