"""Learn from real views (v2.11): how your posted clips really did, and a critic tuned to your channels.

    python run.py learn            read the results from PostKaro, write output/_learn/report.md and the
                                   critic's learned weights (output/_learn/weights.json)
    python run.py learn --show     the report only; the critic's weights are left as they are

What counts as "did well" (the owner left it to Claude, plan item B): three numbers, read about 7 days after
posting, each compared only with the same channel's other clips (a channel with 30 followers and one with 3,000
can't be compared):
  1. reach: engaged views (YouTube) or views / plays (Instagram, Facebook);
  2. staying: the average part of the clip watched (over 100 % on YouTube: people watched it again);
  3. caring: shares per 1,000 views (the critic's "who would send this"); until shares can be read, likes and
     comments per 1,000 views stand in.
A clip's result is the average of its ranks on those (0 = its channel's weakest, 1 = its best), so a clip is in
its channel's top, middle or bottom third. What PostKaro can read depends on its logins (`run.py stats` there).

What it changes: the critic's five weights (hook 3, payoff 3, emotion 2, would-share 2, quotable 1), separately
for gameplay / streams and for talk videos, slowly: only with MIN_CLIPS clips that have both a critic score and a
result, at most HALF of a weight up or down, and more of the change the more clips there are. It only changes
the ranking; a clip is never dropped (the owner posts almost any decent clip). "learn_from_views": false in
settings.json puts the fixed weights back.
"""
import argparse
import json
import os
import statistics
import subprocess
import sys
import time
from pathlib import Path

from .common import OUTPUT, die, load_json, save_json, settings

LEARN = OUTPUT / '_learn'
MIN_AGE = 3.0              # days: younger clips are too early to judge
MIN_CLIPS = 30             # clips with a critic score and a result before a weight moves
HALF = 0.5                 # a weight moves at most this share of itself
FULL_AT = 150              # with this many clips the learned weights count fully
LENGTHS = [(0, 30, 'under 30 s'), (30, 45, '30-45 s'), (45, 60, '45-60 s'), (60, 10 ** 6, 'over 60 s')]


# ---------------------------------------------------------------- the results

def from_postkaro():
    """{'posts': [...], 'gaps': [...]} from PostKaro (`run.py stats --json`), or None when it isn't installed."""
    from .post import postkaro_app
    app = postkaro_app()
    if not app:
        return None
    root = Path(app['path'])
    py = root / '.venv' / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')
    r = subprocess.run([str(py) if py.exists() else sys.executable, str(root / 'run.py'), 'stats', '--json'],
                       capture_output=True, text=True, timeout=300, encoding='utf-8', errors='replace')
    for line in reversed(r.stdout.strip().splitlines()):
        try:
            return json.loads(line)
        except ValueError:
            continue
    die('PostKaro gave no results: ' + (r.stderr or r.stdout).strip()[-300:])


def project_of(kit):
    p = Path(kit)
    folder = p if p.is_dir() else p.parent
    return folder if (folder / 'clips.json').exists() else None


def clip_facts(pdir, clip_no, cache):
    """What we know about a posted clip: its critic scores and its kind."""
    if pdir not in cache:
        from .kind import is_irregular
        project = load_json(pdir / 'project.json', {}) or {}
        crit = {c['id']: c for c in (load_json(pdir / 'critic' / 'critic.json', {}) or {}).get('clips', [])}
        clips = {int(c.get('id', k)): c for k, c in enumerate((load_json(pdir / 'clips.json', {}) or {}).get('clips', []), 1)}
        cache[pdir] = (project, crit, clips, 'gameplay' if is_irregular(project) else 'talk')
    project, crit, clips, kind = cache[pdir]
    c = clips.get(int(clip_no))
    if not c:
        return None
    cr = crit.get(c.get('from')) or {}
    return {'kind': kind, 'title': c.get('title'), 'hook_type': c.get('hook_type'),
            'pieces': len(c.get('ranges') or []), 'story': bool(c.get('keep_whole')) or len(c.get('ranges') or []) >= 3,
            'deep': bool(c.get('deep')), 'compilation': bool(c.get('compilation')),
            'emoji': len(c.get('emoji') or []), 'sounds': len(c.get('sfx') or []),
            'clip_score': cr.get('clip_score') or c.get('clip_score'),
            'scores': {d: v['mean'] for d, v in (cr.get('scores') or {}).items()} or None,
            'language': project.get('language')}


def rank(values):
    """Percentile ranks 0..1 (ties share their place), None stays None."""
    have = sorted((v, i) for i, v in enumerate(values) if v is not None)
    out = [None] * len(values)
    if len(have) < 2:
        return out
    k = 0
    while k < len(have):
        j = k
        while j + 1 < len(have) and have[j + 1][0] == have[k][0]:
            j += 1
        r = ((k + j) / 2) / (len(have) - 1)
        for _, i in have[k:j + 1]:
            out[i] = round(r, 3)
        k = j + 1
    return out


def results(posts):
    """Each usable post with its result (0..1 on its own channel) and third."""
    from collections import defaultdict
    by_acct = defaultdict(list)
    for p in posts:
        n = p.get('numbers') or {}
        if p.get('age_days') is None or p['age_days'] < MIN_AGE or not n.get('reach'):
            continue
        by_acct[(p['platform'], p['account'])].append(p)
    out = []
    for key, ps in by_acct.items():
        cols = {}
        for name in ('reach', 'watched_pct', 'shares_per_1k', 'likes_per_1k'):
            cols[name] = rank([(p['numbers'] or {}).get(name) for p in ps])
        for k, p in enumerate(ps):
            care = cols['shares_per_1k'][k] if cols['shares_per_1k'][k] is not None else cols['likes_per_1k'][k]
            parts = [x for x in (cols['reach'][k], cols['watched_pct'][k], care) if x is not None]
            if not parts:
                continue
            res = sum(parts) / len(parts)
            out.append({**p, 'result': round(res, 3), 'third': 'top' if res >= 2 / 3 else 'middle' if res >= 1 / 3 else 'bottom',
                        'channel_size': len(ps)})
    return out


def spearman(xs, ys):
    pairs = [(x, y) for x, y in zip(xs, ys) if x is not None and y is not None]
    if len(pairs) < 5:
        return None
    rx, ry = rank([x for x, _ in pairs]), rank([y for _, y in pairs])
    mx, my = statistics.mean(rx), statistics.mean(ry)
    num = sum((a - mx) * (b - my) for a, b in zip(rx, ry))
    den = (sum((a - mx) ** 2 for a in rx) * sum((b - my) ** 2 for b in ry)) ** 0.5
    return round(num / den, 3) if den else None


def learn_weights(rows):
    """{kind: {'weights', 'n', 'rho', 'score_rho'}} from rows with critic scores and a result."""
    from .critic import WEIGHTS
    out = {}
    for kind in ('gameplay', 'talk'):
        rs = [r for r in rows if r['facts'] and r['facts']['kind'] == kind and r['facts']['scores']]
        rho = {d: spearman([r['facts']['scores'].get(d) for r in rs], [r['result'] for r in rs]) for d in WEIGHTS}
        score_rho = spearman([r['facts']['clip_score'] for r in rs], [r['result'] for r in rs])
        entry = {'n': len(rs), 'rho': rho, 'score_rho': score_rho, 'weights': None}
        if len(rs) >= MIN_CLIPS:
            a = min(1.0, len(rs) / FULL_AT)
            entry['weights'] = {d: round(w * (1 + a * max(-HALF, min(HALF, rho[d] or 0.0))), 2) for d, w in WEIGHTS.items()}
        out[kind] = entry
    return out


def learned_weights(project):
    """The critic's weights for this video's kind, when learned and wanted; else None (the fixed weights)."""
    if not settings().get('learn_from_views', True):
        return None
    w = load_json(LEARN / 'weights.json') or {}
    from .kind import is_irregular
    entry = (w.get('kinds') or {}).get('gameplay' if is_irregular(project) else 'talk') or {}
    if not entry.get('weights'):
        return None
    return entry['weights'], f"learned from {entry['n']} posted clips ({w.get('made', '')[:10]})"


# ---------------------------------------------------------------- the report

def median(xs):
    xs = [x for x in xs if x is not None]
    return round(statistics.median(xs), 2) if xs else None


def group_line(rows, label, pick):
    """'label: N clips, median result 0.62' for the rows `pick` chooses, or None."""
    rs = [r for r in rows if pick(r)]
    if len(rs) < 3:
        return None
    return f"{label}: {len(rs)} clips, typical result {median([r['result'] for r in rs])}"


def report(data, rows, learned, applied):
    from .critic import WEIGHTS
    L = ['# How your clips really did', '',
         f"Made {time.strftime('%Y-%m-%d %H:%M')} from PostKaro's numbers. A clip's **result** is its place on its own "
         'channel (0 = weakest, 1 = best), from reach, how much of it people watched, and shares (or likes and comments '
         'until shares can be read) per 1,000 views, read about 7 days after posting.', '']
    gaps = data.get('gaps') or []
    if gaps:
        L += ['## Numbers PostKaro cannot read yet', '']
        for g in gaps:
            how = {'enable': f"turn on the YouTube Analytics API ({g.get('link')}), then Reconnect YouTube once",
                   'reconnect': 'Reconnect it in PostKaro (Accounts) and allow everything'}.get(g['fix'], 'it will try again')
            L.append(f"- **{g['platform']}**: no {g['what']} ({g['posts']} posts): {how}.")
        L.append('')
    from collections import defaultdict
    by = defaultdict(list)
    for r in rows:
        by[(r['platform'], r.get('account_name') or r['account'])].append(r)
    for (plat, name), rs in sorted(by.items(), key=lambda x: -len(x[1])):
        L += [f'## {name} ({plat})', '', f"{len(rs)} clips with numbers; typical reach {median([(r['numbers'] or {}).get('reach') for r in rs])}"
              + (f", typical watched {median([(r['numbers'] or {}).get('watched_pct') for r in rs])} %" if any((r['numbers'] or {}).get('watched_pct') for r in rs) else '')
              + ('.' if len(rs) >= 10 else '. Few clips: treat everything below as a hint.'), '']
        best = sorted(rs, key=lambda r: -r['result'])[:3]
        L.append('Best: ' + '; '.join(f"\"{r['title']}\" ({(r['numbers'] or {}).get('reach')} views)" for r in best))
        lines = [group_line(rs, lab, lambda r, a=a, b=b: r.get('duration') and a <= r['duration'] < b) for a, b, lab in LENGTHS]
        lines += [group_line(rs, 'joined clips (several pieces)', lambda r: (r['facts'] or {}).get('pieces', 0) and r['facts']['pieces'] > 1),
                  group_line(rs, 'one piece', lambda r: (r['facts'] or {}).get('pieces') == 1),
                  group_line(rs, '"boast, then fail" / action stories', lambda r: (r['facts'] or {}).get('story') is True)]
        for ht in sorted({(r['facts'] or {}).get('hook_type') for r in rs} - {None}):
            lines.append(group_line(rs, f'hook: {ht}', lambda r, ht=ht: r['facts'] and r['facts']['hook_type'] == ht))
        lines = [x for x in lines if x]
        if lines:
            L += ['', *[f'- {x}' for x in lines]]
        L.append('')
    L += ['## The critic', '']
    allr = spearman([(r['facts'] or {}).get('clip_score') for r in rows], [r['result'] for r in rows])
    n_all = sum(1 for r in rows if (r['facts'] or {}).get('clip_score') is not None)
    if n_all >= 5:
        L.append(f"- All {n_all} posted clips with a clip score: score and real results "
                 + ('do not match yet' if allr is None or abs(allr) < 0.1 else 'match a little' if abs(allr) < 0.3
                    else 'match clearly' if allr > 0 else 'go the opposite way') + f" ({allr}).")
    for kind, e in learned.items():
        word = {'gameplay': 'Gameplay and streams', 'talk': 'Talk videos (podcasts, interviews)'}[kind]
        if not e['n']:
            L.append(f'- {word}: no posted clip with a critic score and a result yet.')
            continue
        sr = e['score_rho']
        match = ('no clear match yet' if sr is None or abs(sr) < 0.1 else 'a weak match' if abs(sr) < 0.3
                 else 'a clear match' if sr > 0 else 'the opposite (the higher the score, the worse it did)')
        L.append(f"- {word}: {e['n']} clips. The clip score and the real results: {match}"
                 f"{f' ({sr})' if sr is not None else ''}.")
        if e['weights']:
            moved = [f"{d} {WEIGHTS[d]} → {e['weights'][d]}" for d in WEIGHTS if abs(e['weights'][d] - WEIGHTS[d]) >= 0.05]
            L.append(f"  Weights {'now used' if applied else 'learned (not applied: --show)'}: "
                     + (', '.join(moved) if moved else 'no change worth making') + '.')
        else:
            L.append(f'  Weights unchanged: {MIN_CLIPS} clips with a critic score and a result are needed first.')
    L += ['', 'The clip score still only ranks clips; nothing is ever dropped because of it. '
          '`"learn_from_views": false` in settings.json puts the fixed weights back.']
    return '\n'.join(L) + '\n'


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--show', action='store_true', help='only the report; the critic keeps its weights')
    a = ap.parse_args()
    data = from_postkaro()
    if data is None:
        die('PostKaro (the posting app) is not installed: it reads how your posted clips did. '
            'See docs/postkaro.md.')
    cache, rows = {}, []
    for r in results(data.get('posts') or []):
        # what the clip was: kept by PostKaro since v2.11 (the project may be deleted), else the project's files,
        # else only its clip score (older posts whose project is gone)
        pdir = project_of(r['kit']) if r.get('kit') else None
        r['facts'] = r.get('facts') or (clip_facts(pdir, r['clip'], cache) if pdir else None) or \
            ({'clip_score': r['score'], 'scores': None, 'kind': None, 'pieces': None, 'story': None, 'hook_type': None}
             if r.get('score') is not None else None)
        rows.append(r)
    learned = learn_weights(rows)
    LEARN.mkdir(parents=True, exist_ok=True)
    if not a.show:
        save_json(LEARN / 'weights.json', {'made': time.strftime('%Y-%m-%dT%H:%M:%S'), 'kinds': learned})
    save_json(LEARN / 'results.json', [{k: v for k, v in r.items() if k != 'raw'} for r in rows])
    text = report(data, rows, learned, not a.show)
    (LEARN / 'report.md').write_text(text, encoding='utf-8')
    print(text)
    print(f'-> {LEARN / "report.md"}')


if __name__ == '__main__':
    main()
