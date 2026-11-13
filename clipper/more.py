"""More clips later, without reading the video again.

    python run.py more <project>              # the good ideas that weren't cut yet, best first
    python run.py more <project> --add 3      # add the next 3 of them to clips.json
    python run.py more <project> --upto 12    # add enough of them for 12 clips in all
    python run.py more <project> --pick 2,5   # add exactly those (numbers from the list)

While choosing clips, the critic scores every clip idea of the video (often 15-30), and only the best
are cut. The others are good, already-scored moments with exact times. This lists them (best first,
none overlapping a clip that is already made or each other) and writes the list to
output/<project>/more.txt. With --add / --upto / --pick they are added to clips.json as new clips,
numbered after the last one, and their words are printed so Claude can write their posting text.
Then only the new clips are cut and edited.

Where the ideas come from: every critic round (critic/critic.json and the rounds before it in
critic/old/), then the long-video readers' candidates the critic never judged (candidates.json), then
the "spare" ideas Claude lists in clips.json in quick mode (no critic there).
"""
import argparse

from .common import die, fmt_ts, load_json, project_dir, save_json

OVERLAP_S = 1.0


def _overlaps(r1, r2):
    return any(min(b, d) - max(a, c) > OVERLAP_S for a, b in r1 for c, d in r2)


def _same(r1, r2):
    return len(r1) == len(r2) and all(abs(a - c) <= 1.0 and abs(b - d) <= 1.0 for (a, b), (c, d) in zip(r1, r2))


def ideas(pdir):
    """Every clip idea the video has, best first: [{id, ranges, title, score, scored_by, notes}]."""
    cdir = pdir / 'critic'
    rounds = sorted((cdir / 'old').glob('*/critic.json')) if (cdir / 'old').exists() else []
    rounds.append(cdir / 'critic.json')
    seen = {}                                     # id -> idea; a later round replaces an earlier one
    for f in rounds:
        doc = load_json(f) or {}
        for x in doc.get('clips', []):
            key = x.get('origin') or x['id']      # a repaired version replaces its original
            old = next((k for k, v in seen.items() if k == key or _same(v['ranges'], x['ranges'])), None)
            if old:
                seen.pop(old)
            seen[key] = {'id': key, 'ranges': x['ranges'], 'title': x.get('title') or '',
                         'score': x.get('clip_score'), 'rank': x.get('rank_score', x.get('clip_score')),
                         'band': x.get('band'), 'scored_by': 'critic',
                         'notes': [n for n in x.get('notes') or [] if isinstance(n, str)]}
    out = sorted(seen.values(), key=lambda v: (-(v['rank'] or 0), v['ranges'][0][0]))
    for c in sorted(load_json(pdir / 'candidates.json', []) or [], key=lambda c: -(c.get('score') or 0)):
        if c['id'] not in seen and not any(_same(c['ranges'], v['ranges']) for v in out):
            out.append({'id': c['id'], 'ranges': c['ranges'], 'title': c.get('title') or '',
                        'score': c.get('score'), 'rank': None, 'band': None, 'scored_by': 'reader',
                        'notes': [f"needs context: {c['needs_context']}"] if c.get('needs_context') else []})
    clips = load_json(pdir / 'clips.json', {}) or {}
    for k, s in enumerate(clips.get('spare') or [], 1):          # quick mode: Claude's runner-ups
        if s.get('ranges'):
            out.append({'id': s.get('id') or f'q{k}', 'ranges': s['ranges'], 'title': s.get('title') or '',
                        'score': s.get('score'), 'rank': None, 'band': None, 'scored_by': 'claude', 'notes': []})
    return out


def unused(pdir):
    """The ideas not cut yet: none overlapping a clip in clips.json, none overlapping a better one."""
    clips = (load_json(pdir / 'clips.json', {}) or {}).get('clips', [])
    taken = [c['ranges'] for c in clips]
    used_ids = {c.get('from') for c in clips if c.get('from')}
    out = []
    for x in ideas(pdir):
        if x['id'] in used_ids or any(_overlaps(x['ranges'], r) for r in taken):
            continue
        if any(_overlaps(x['ranges'], y['ranges']) for y in out):
            continue                                              # the better one of two is listed
        out.append(x)
    return out


def words_in(words, ranges):
    return ' … '.join(' '.join(w['w'] for w in words if a <= w['s'] < b and not w.get('unsure')) for a, b in ranges)


def span(ranges):
    return ' + '.join(f"{fmt_ts(a).split('.')[0]}-{fmt_ts(b).split('.')[0]}" for a, b in ranges)


def score_text(x):
    if x['scored_by'] == 'critic' and x['score'] is not None:
        return f"{x['score']:>4}/10 {x.get('band') or ''}"
    if x['score'] is not None:
        return f"reader {x['score']}/10" if x['scored_by'] == 'reader' else f"Claude {x['score']}/10"
    return 'not scored'


def write_list(pdir, items, words):
    rows = [f'# More clips: the good ideas of this video that were not cut yet, best first ({len(items)}).',
            '# Ask for them: "3 more clips from this video", "clips 9-12 too", or "add idea 2 and 5".',
            f'# Then: python run.py more {pdir.name} --add 3   (or --upto 12, or --pick 2,5)', '']
    for n, x in enumerate(items, 1):
        dur = sum(b - a for a, b in x['ranges'])
        rows.append(f"{n:>2}. {score_text(x):<16} {span(x['ranges'])} ({dur:.0f} s)  \"{x['title']}\"  [{x['id']}]")
        text = words_in(words, x['ranges']).split()
        rows.append('    ' + (' '.join(text[:14]) + (' … ' + ' '.join(text[-8:]) if len(text) > 22 else
                                                       ' ' + ' '.join(text[14:]))).strip())
        for note in x['notes'][:3]:
            rows.append(f'    {note}')
    (pdir / 'more.txt').write_text('\n'.join(rows) + '\n', encoding='utf-8')
    return pdir / 'more.txt'


def summary_line(pdir):
    """One line for the end of a run (post): how many good ideas are still waiting, or None."""
    try:
        items = [x for x in unused(pdir) if x['scored_by'] != 'critic' or (x['score'] or 0) >= 4.0]
    except Exception:
        return None
    if not items:
        return None
    best = next((x['score'] for x in items if x['scored_by'] == 'critic'), None)
    return (f"{len(items)} more good idea(s) not cut yet{f' (the best {best}/10)' if best else ''}: "
            f"say \"more clips\" (python run.py more {pdir.name})")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('project')
    ap.add_argument('--add', type=int, default=None, help='add the next N ideas to clips.json')
    ap.add_argument('--upto', type=int, default=None, help='add ideas until clips.json has N clips')
    ap.add_argument('--pick', default='', help='add these ideas (numbers from the list), e.g. 2,5')
    a = ap.parse_args()
    pdir = project_dir(a.project)
    picks = load_json(pdir / 'clips.json')
    if not picks or not picks.get('clips'):
        die(f'no clips.json in {pdir.name} yet: clip the video first')
    words = load_json(pdir / 'transcript' / 'words.json') or []
    items = unused(pdir)
    txt = write_list(pdir, items, words)
    if not items:
        print(f'no ideas left that were not cut ({pdir.name} has {len(picks["clips"])} clips). For more, the video '
              'has to be read again: "find more clips in this video".')
        return

    clips = picks['clips']
    if a.pick:
        nums = [int(v) for v in a.pick.split(',') if v.strip()]
        bad = [n for n in nums if not 1 <= n <= len(items)]
        if bad:
            die(f'no idea number {bad[0]}: the list has 1-{len(items)} ({txt})')
        chosen = [items[n - 1] for n in nums]
    elif a.add or a.upto:
        want = a.add if a.add else max(0, a.upto - len(clips))
        chosen = items[:want]
    else:
        print(f'-> {len(items)} idea(s) not cut yet, best first ({txt.relative_to(pdir.parent.parent)}):')
        for n, x in enumerate(items, 1):
            print(f"   {n:>2}. {score_text(x):<16} {span(x['ranges']):<22} \"{x['title']}\"")
        print(f'\nadd them:  python run.py more {pdir.name} --add N   (or --upto N, or --pick 2,5)')
        return
    if not chosen:
        print(f'clips.json already has {len(clips)} clips: nothing to add')
        return
    if len(chosen) < (a.add or 0):
        print(f'   (only {len(chosen)} idea(s) left)')

    next_id = max(int(c.get('id', k + 1)) for k, c in enumerate(clips)) + 1
    added = []
    for x in chosen:
        text = words_in(words, x['ranges'])
        clip = {'id': next_id, 'title': x['title'], 'hook': ' '.join(text.split()[:12]), 'ranges': x['ranges'],
                'from': x['id'], 'added_later': True}
        if x['scored_by'] == 'critic' and x['score'] is not None:
            clip['clip_score'] = x['score']
        clips.append(clip)
        added.append((clip, x, text))
        next_id += 1
    save_json(pdir / 'clips.json', picks)
    ids = ','.join(str(c['id']) for c, _, _ in added)
    print(f'-> added {len(added)} clip(s) to clips.json as {ids}. Their words (write each one\'s "caption" and '
          f'"post", and a "clarify" note if it says "he" / "वो" without naming it):')
    for c, x, text in added:
        print(f"\n   clip {c['id']}  {score_text(x)}  {span(x['ranges'])}  \"{c['title']}\"  [from {x['id']}]")
        for note in x['notes']:
            print(f'      note: {note}')
        print(f'      {text}')
    print(f'\nnext: write their posting text in clips.json; then (Hindi/Hinglish) python run.py romanize {pdir.name}; '
          f'python run.py cut {pdir.name} --check --clips {ids}; python run.py cut {pdir.name} --clips {ids}; '
          f'python run.py edit {pdir.name} --clips {ids}; python run.py post {pdir.name}')


if __name__ == '__main__':
    main()
