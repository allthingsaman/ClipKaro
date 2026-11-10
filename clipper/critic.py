"""The critic: a blind second opinion on every clip idea, before anything is cut.

    python run.py critic <project>            1st time: writes 3 packets; run again when the 3
                                              critic helpers have answered: merges them
    python run.py critic <project> --fresh    start over (earlier answers are kept in critic/old/)
    python run.py critic <project> --from clips   judge the clips in clips.json (a short video's
                                              shortlist) even if candidates.json exists

Pool: every candidate in candidates.json (long videos, from `run.py topics`) or, for a short video,
the shortlist Claude wrote to clips.json (about twice the clips wanted).

Packets: 3 runs, each with every clip in a different random order and with neutral labels (K7,
B2, ...). Each clip shows its exact words with times from its start, sound markers such as
"[laughter ~2 s]", and the next ~15 s marked as NOT IN THE CLIP (so a punchline that comes right
after the cut is noticed). The critic never sees the reader's score, title or reasons, the rank,
the part, the replay curve, the teaser, or anything about the channel: such hints pull an AI
judge's scores, and warnings don't undo that (research for phase 2).

The sheet (.claude/agents/clipkaro-critic.md): two pass/fail gates (stands alone, complete ending)
and five 0-5 scores (hook x3, payoff x3, emotion x2, send-ability x2, quotable x1).

Merging (here, in code): the clip score (the weighted mean, out of 10) ranks the clips of this one
video. A gate failed in 2 of 3 runs becomes a "fix?" note for the repair round (needs context, the
payoff comes after the cut), and a split gate a "check" note; neither throws a clip away. In the
user's blind check (Nov 2026) every clip the gates had dropped, and every clip under 5/10, was one
they would post. Replay peaks, the creator's teaser and the sound's liveliness are attached
afterwards and only break near-ties; a video without them loses nothing. Hard facts about the
words (a sentence that goes on after the clip, a false start) come from code and are shown to the
critic as facts.

The score judges how well-made a clip looks from its words and sound. It is not a prediction of
views. Every result is also logged to output/clip-log.csv, to tune the bar later from what the
user keeps.
"""
import argparse
import bisect
import csv
import hashlib
import random
import shutil
import statistics
import time

from . import sound
from .cut import boundary_warnings
from .common import OUTPUT, die, fmt_ts, load_json, norm_token, project_dir, save_json
from .parts import est_tokens

RUNS = 3
WEAK = 5.0              # below this the band is "Weak" (a label only: the user's blind check kept such clips)
WEIGHTS = {'hook': 3, 'payoff': 3, 'emotion': 2, 'share': 2, 'quote': 1}
DIMS = list(WEIGHTS)
GATES = {'alone': 'stands alone', 'ending': 'complete ending'}
VERDICTS = {'pass', 'fail', 'unsure'}
AFTER_S = 15.0            # seconds after the clip shown as NOT IN THE CLIP
AFTER_MAX = 25.0          # ... extended to the end of that sentence, up to this
FILE_TOKENS = 16000       # one packet file stays well inside one Read
BONUS_CAP = 0.3           # hints only reorder clips whose scores are this close
AGENT = 'clipkaro-critic'
LABEL_CHARS = 'ABCDEFGHJKLMNPQRSTUVWXYZ'
LOG = OUTPUT / 'clip-log.csv'
LANG_NOTE = {
    'hinglish': 'Hinglish: Hindi in Devanagari plus English words in Roman letters. Code-mixing is normal, '
                'not a flaw. Feelings and jokes often sit in the Hindi phrases: read them closely.',
    'hi': 'Hindi (Devanagari). Feelings and jokes often sit in turns of phrase: read them closely.',
}


def band(score):
    for lo, name in ((9, 'Standout'), (7, 'Strong'), (6, 'Good'), (WEAK, 'OK')):
        if score >= lo - 1e-9:
            return name
    return 'Weak'


# ---------------------------------------------------------------- the transcript

class Transcript:
    def __init__(self, pdir):
        self.words = load_json(pdir / 'transcript' / 'words.json') or []
        self.lines = load_json(pdir / 'transcript' / 'sentences.json') or []
        self.starts = [ln['s'] for ln in self.lines]
        if not self.words:
            die(f'no transcript in {pdir}: run `python run.py fetch` first')

    def words_in(self, a, b):
        return [w for w in self.words if w['s'] >= a - 0.005 and w['e'] <= b + 0.01]

    def lines_in(self, a, b):
        """The words of [a, b] grouped by transcript line: [(start, text)]."""
        out = []
        for w in self.words_in(a, b):
            li = bisect.bisect_right(self.starts, w['s'] + 1e-6) - 1
            if out and out[-1][0] == li:
                out[-1][2].append(w['w'].strip())
            else:
                out.append([li, w['s'], [w['w'].strip()]])
        return [(t0, ' '.join(t)) for _, t0, t in out]

    def after(self, b):
        """Words heard right after b: AFTER_S seconds, to the end of that sentence (at most AFTER_MAX)."""
        ws = [w for w in self.words if b + 0.01 < w['s'] <= b + AFTER_MAX]
        out = []
        for w in ws:
            out.append(w['w'].strip())
            if w['s'] > b + AFTER_S and w['w'].strip()[-1:] in '.?!।॥':
                break
        return ' '.join(out)


def mmss(t):
    t = max(0.0, t)
    return f'{int(t // 60)}:{int(t % 60):02d}'


def clip_block(tr, cues, label, ranges):
    """The text the critic reads for one clip."""
    dur = sum(b - a for a, b in ranges)
    rows = [f'## {label} ({dur:.0f} s)']
    off = 0.0
    for k, (a, b) in enumerate(ranges):
        if k:
            rows.append('[--- cut: the next piece comes from later in the video ---]')
        lines = tr.lines_in(a, b)
        marks = sound.markers(cues, a, b)
        starts = [t0 for t0, _ in lines]
        at = {}                                  # a marker goes after the line during which it starts
        for t, m in marks:
            at.setdefault(max(0, bisect.bisect_right(starts, t) - 1), []).append(m)
        for i, (t0, text) in enumerate(lines):
            here = ' '.join(at.get(i, []))
            rows.append(f'[{mmss(off + t0 - a)}] {text}' + (f' {here}' if here else ''))
        off += b - a
    facts = boundary_warnings(ranges, tr.words)
    if facts:
        rows.append('CHECKED BY CODE (facts): ' + '; '.join(facts))
    rows.append(f'AFTER THE CLIP (NOT IN THE CLIP, the viewer never hears this): {tr.after(ranges[-1][1]) or "(the video ends)"}')
    return '\n'.join(rows)


# ---------------------------------------------------------------- the pool

def load_pool(pdir, source):
    if source == 'deep':                          # deep clips and their continuous twins (run.py deep)
        cands = load_json(pdir / 'deep' / 'candidates.json') or []
        if not cands:
            die(f'no deep/candidates.json in {pdir.name}: run  python run.py deep {pdir.name}  first')
        return 'deep', [{'id': c['id'], 'ranges': c['ranges'], 'title': c.get('title'), 'kind': c.get('kind'),
                         'twin': c.get('twin')} for c in cands]
    cands = load_json(pdir / 'candidates.json')
    if source != 'clips' and cands:
        return 'candidates', [{'id': c['id'], 'ranges': c['ranges'], 'title': c.get('title'),
                               'topic': c.get('topic'), 'sensitive': c.get('sensitive')} for c in cands]
    clips = load_json(pdir / 'clips.json')
    if not clips:
        die(f'nothing to judge in {pdir.name}: write a shortlist to clips.json (short video) or run '
            f'`python run.py topics` (long video) first')
    clips = clips.get('clips', clips) if isinstance(clips, dict) else clips
    return 'clips', [{'id': f's{i + 1}', 'ranges': c['ranges'], 'title': c.get('title'), 'clip_index': i}
                     for i, c in enumerate(clips)]


def signature(pool):
    raw = '|'.join(f"{c['id']}:{c['ranges']}" for c in pool)
    return hashlib.sha1(raw.encode()).hexdigest()[:12]


def labels(rng, n):
    width = 2 if n <= 150 else 3
    out = set()
    while len(out) < n:
        out.add(rng.choice(LABEL_CHARS) + ''.join(rng.choice('23456789') for _ in range(width - 1)))
    lst = sorted(out)
    rng.shuffle(lst)
    return lst


def where(pdir, source):
    """The critic's folder and its readable list: deep clips are judged apart from the regular ones."""
    if source == 'deep':
        return pdir / 'deep' / 'critic', pdir / 'deep' / 'critic.txt'
    return pdir / 'critic', pdir / 'critic.txt'


def prepare(pdir, source, runs):
    project = load_json(pdir / 'project.json', {}) or {}
    kind, pool = load_pool(pdir, source)
    if len(pool) < 2:
        die('the critic needs at least 2 clip ideas to judge')
    tr = Transcript(pdir)
    cues = sound.ensure(pdir, quiet=True)
    sig = signature(pool)
    cdir = where(pdir, source)[0]
    cdir.mkdir(parents=True, exist_ok=True)
    lang = (project.get('language') or '').lower()
    note = LANG_NOTE.get(lang) or LANG_NOTE.get('hinglish' if lang.startswith('hi') else '', '')
    key, files = {}, {}
    for r in range(1, runs + 1):
        rng = random.Random(f'{pdir.name}-{sig}-run{r}')
        order = list(range(len(pool)))
        rng.shuffle(order)
        labs = labels(rng, len(pool))
        key[str(r)] = {labs[i]: {'id': pool[j]['id'], 'pos': i} for i, j in enumerate(order)}
        blocks = [clip_block(tr, cues, labs[i], pool[j]['ranges']) for i, j in enumerate(order)]
        chunks, cur, cur_t = [], [], 0
        for b in blocks:
            t = est_tokens(b)
            if cur and cur_t + t > FILE_TOKENS:
                chunks.append(cur)
                cur, cur_t = [], 0
            cur.append(b)
            cur_t += t
        chunks.append(cur)
        names = [f'run-{r}' + (f'-{chr(97 + k)}' if len(chunks) > 1 else '') + '.txt' for k in range(len(chunks))]
        answer = (cdir / f'run-{r}.json').relative_to(pdir.parent.parent).as_posix()
        for k, (name, chunk) in enumerate(zip(names, chunks)):
            if k == 0:
                head = [f'# ClipKaro critic: run {r} of {runs}. {len(pool)} clip ideas from ONE video, in random order.',
                        f'# Read every file of this run: {", ".join(names)}. Then write {answer} as your '
                        f'instructions say, with one entry for each of the {len(pool)} labels.',
                        '# Times like [0:12] count from the start of the clip.']
                if note:
                    head.append(f'# Language: {note}')
                if cues:
                    head.append('# Markers like [laughter ~2 s] or [both talk at once] come from a sound detector and '
                                'can be wrong. A laugh in the room is not proof that viewers will laugh, and no marker '
                                'does not mean the moment is dull.')
            else:
                head = [f'# ClipKaro critic: run {r} of {runs}, file {k + 1} of {len(chunks)} (continued).']
            (cdir / name).write_text('\n'.join(head) + '\n\n' + '\n\n'.join(chunk) + '\n', encoding='utf-8')
        files[str(r)] = names
    save_json(cdir / 'plan.json', {'project': pdir.name, 'pool': kind, 'signature': sig, 'runs': runs,
                                   'clips': pool, 'key': key, 'files': files,
                                   'made': time.strftime('%Y-%m-%d %H:%M')})
    print(f'-> {len(pool)} clip ideas from {kind}.json, {runs} blind runs in {cdir.relative_to(pdir.parent.parent)}')
    for r in range(1, runs + 1):
        print(f"   run {r}: {', '.join(files[str(r)])}")
    print(f'\nnext: start {runs} `{AGENT}` helpers at once, one per run (prompt e.g. "Run 2 of {runs}: '
          f'{(cdir / files["2" if runs > 1 else "1"][0]).relative_to(pdir.parent.parent).as_posix()}"). '
          f'Then run again:  python run.py critic {pdir.name}')


# ---------------------------------------------------------------- reading the answers

def check_run(plan, r, ans):
    """Problems in one run's answer (empty when it's fine)."""
    probs = []
    if not isinstance(ans, dict) or not isinstance(ans.get('clips'), list):
        return [f'run {r}: the file must be {{"run": {r}, "clips": [...]}}']
    want = set(plan['key'][str(r)])
    seen = {}
    for c in ans['clips']:
        lab = c.get('id') if isinstance(c, dict) else None
        if lab not in want:
            probs.append(f'run {r}: unknown label {lab!r}')
            continue
        if lab in seen:
            probs.append(f'run {r}: {lab} answered twice')
        seen[lab] = c
        for g in GATES:
            v = c.get(g)
            if not (isinstance(v, list) and len(v) == 2 and v[0] in VERDICTS and isinstance(v[1], str)):
                probs.append(f'run {r}: {lab} "{g}" must be ["pass" | "fail" | "unsure", "reason"]')
        for d in DIMS:
            v = c.get(d)
            if not (isinstance(v, list) and len(v) == 2 and isinstance(v[0], int) and not isinstance(v[0], bool)
                    and 0 <= v[0] <= 5 and isinstance(v[1], str)):
                probs.append(f'run {r}: {lab} "{d}" must be [0-5, "reason"]')
    for lab in sorted(want - set(seen)):
        probs.append(f'run {r}: label {lab} is missing')
    return probs


def locate(tr, ranges, quote):
    """Start time of a quoted line inside the clip, or None."""
    q = [t for t in (norm_token(x) for x in quote.split()) if t]
    if len(q) < 2:
        return None
    ws = [w for a, b in ranges for w in tr.words_in(a, b)]
    toks = [norm_token(w['w']) for w in ws]
    n = min(len(q), 6)
    for i in range(len(toks) - n + 1):
        if toks[i:i + n] == q[:n]:
            return ws[i]['s']
    return None


def peaks(project, topics):
    """Strong "most replayed" regions, or [] for a video without a curve.
    Bins of 1% of the video; the first bin and structural topics (teaser, intro, sponsor, outro) are
    left out; a peak is a local maximum at least half the highest remaining bin and 1.5x the median
    (a flat curve gives none); neighbours are merged; at most 5. Both thresholds are our own starting
    values, to be tuned."""
    heat = project.get('heatmap')
    if not heat:
        return []
    struct = [(t['start'], t['end'], t['role']) for t in (topics or {}).get('topics', [])
              if t.get('role') in ('teaser', 'intro', 'sponsor', 'outro', 'housekeeping')]
    bins = [(s, e, v) for i, (s, e, v) in enumerate(heat)
            if i > 0 and not any(e > a and s < b for a, b, _ in struct)]
    if len(bins) < 5:
        return []
    top, med = max(v for _, _, v in bins), statistics.median(v for _, _, v in bins)
    if top <= 0:
        return []
    good = [i for i, (s, e, v) in enumerate(bins) if v >= 0.5 * top and v >= 1.5 * med
            and (i == 0 or v >= bins[i - 1][2]) and (i == len(bins) - 1 or v >= bins[i + 1][2])]
    regions = []
    for i in good:
        lo = hi = i                               # grow over neighbours that also clear the bar
        while lo > 0 and bins[lo - 1][2] >= 0.5 * top:
            lo -= 1
        while hi < len(bins) - 1 and bins[hi + 1][2] >= 0.5 * top:
            hi += 1
        reg = [bins[lo][0], bins[hi][1], round(bins[i][2] / top, 2)]
        if regions and reg[0] <= regions[-1][1]:
            regions[-1][1] = max(regions[-1][1], reg[1])
            regions[-1][2] = max(regions[-1][2], reg[2])
        else:
            regions.append(reg)
    width = heat[1][1] - heat[1][0] if len(heat) > 1 else 0
    chapters = [c['start'] for c in project.get('chapters') or []]
    sponsors = [b for a, b, role in struct if role == 'sponsor']
    out = []
    for a, b, st in sorted(regions, key=lambda x: -x[2])[:5]:
        flags = []
        if any(abs(a - c) <= width for c in chapters):          # it starts right at a chapter start:
            flags.append('at a chapter start')                  # people may be jumping there
        if any(a - width <= e <= a + 1 for e in sponsors):
            flags.append('just after a sponsor')
        out.append({'start': a, 'end': b, 'strength': st, 'flags': flags})
    return out


def hints(c, pk, teased, cues):
    main = c['ranges']
    h = {}
    hit = [p for p in pk if any(p['end'] > a and p['start'] < b for a, b in main)]
    if hit:
        p = max(hit, key=lambda x: x['strength'])
        h['replay'] = {'strength': p['strength'], 'flags': p['flags']}
    if any(a <= t < b for t in teased for a, b in main):
        h['teased'] = True
    if cues:
        laugh = sum(max(0.0, min(e, b) - max(s, a)) for s, e, _ in cues.get('laughter', []) for a, b in main)
        both = sum(max(0.0, min(e, b) - max(s, a)) for s, e in cues.get('overlap', []) for a, b in main)
        if laugh >= 1 or both >= 1.5:
            h['lively'] = {'laughter_s': round(laugh, 1), 'both_talk_s': round(both, 1)}
    return h


def bonus(h):
    """A small, capped bonus that only reorders near-ties. Never negative."""
    b = 0.0
    if h.get('teased'):
        b += 0.15
    if h.get('replay'):
        b += 0.15 if not h['replay']['flags'] else 0.05
    if h.get('lively'):
        b += 0.1
    return min(BONUS_CAP, b)


def spearman(x, y):
    if len(x) < 8:
        return None
    rx, ry = sound._ranks(x), sound._ranks(y)
    mx, my = sum(rx) / len(rx), sum(ry) / len(ry)
    num = sum((a - mx) * (b - my) for a, b in zip(rx, ry))
    den = (sum((a - mx) ** 2 for a in rx) * sum((b - my) ** 2 for b in ry)) ** 0.5
    return round(num / den, 2) if den else None


def merge(pdir, plan, answers):
    project = load_json(pdir / 'project.json', {}) or {}
    topics = load_json(pdir / 'topics.json')
    tr = Transcript(pdir)
    cues = sound.load(pdir)
    pk = peaks(project, topics)
    teased = (topics or {}).get('teaser_lines_found_later') or []
    by_id = {c['id']: dict(c, runs=[]) for c in plan['clips']}
    for r, ans in answers.items():
        key = plan['key'][r]
        for a in ans['clips']:
            k = key[a['id']]
            by_id[k['id']]['runs'].append(dict(a, run=int(r), pos=k['pos'], n=len(key)))
    out = []
    for c in by_id.values():
        runs = c.pop('runs')
        res = {**c, 'duration': round(sum(b - a for a, b in c['ranges']), 1), 'runs': len(runs)}
        gates = {}
        for g in GATES:
            vs = [x[g][0] for x in runs]
            gates[g] = {'pass': vs.count('pass'), 'fail': vs.count('fail'), 'unsure': vs.count('unsure'),
                        'why': [x[g][1] for x in runs if x[g][0] != 'pass']}
        scores, spread_big = {}, []
        for d in DIMS:
            vals = [x[d][0] for x in runs]
            mean = sum(vals) / len(vals)
            near = min(runs, key=lambda x: abs(x[d][0] - mean))
            scores[d] = {'mean': round(mean, 2), 'runs': vals, 'why': near[d][1]}
            if max(vals) - min(vals) >= 2:
                spread_big.append(d)
        total = sum(WEIGHTS[d] * scores[d]['mean'] for d in DIMS) / sum(WEIGHTS.values())
        res.update(gates=gates, scores=scores, clip_score=round(2 * total, 1),
                   position=round(statistics.mean(x['pos'] / max(1, x['n'] - 1) for x in runs), 2))
        res['band'] = band(res['clip_score'])
        tags = {}
        for x in runs:
            for t in x.get('tags') or []:
                tags[t] = tags.get(t, 0) + 1
        res['tags'] = sorted(t for t, n in tags.items() if 2 * n >= len(runs))
        fixes = {}
        for x in runs:                           # misheard words for the captions: any run may spot one
            for f in x.get('fixes') or []:
                if isinstance(f, list) and len(f) == 2 and all(isinstance(v, str) and v.strip() for v in f):
                    fixes.setdefault(f[0].strip(), f[1].strip())
        res['fixes'] = [[k, v] for k, v in fixes.items()]
        starts = [x.get('better_start') for x in runs if x.get('better_start') and x['hook'][0] <= 1]
        res['better_start'] = None
        for q in starts:
            t = locate(tr, c['ranges'], q)
            if t is not None:
                res['better_start'] = {'t': round(t, 2), 'text': q}
                break
        # The gates are notes for the repair round, never a reason to throw a clip away: in the
        # user's blind check (Nov 2026) every clip the gates had dropped was one they'd post.
        need = len(runs) // 2 + 1
        failed = [g for g in GATES if gates[g]['fail'] >= need]
        split = [g for g in GATES if g not in failed and (gates[g]['fail'] or gates[g]['unsure'])]
        notes = [f"fix? {GATES[g]}: {gates[g]['why'][0] if gates[g]['why'] else 'failed'}" for g in failed]
        notes += [f"check {GATES[g]} ({gates[g]['pass']} of {len(runs)} runs passed): {gates[g]['why'][0]}"
                  for g in split]
        res['status'] = 'fix' if failed else 'check' if split else 'clean'
        res['notes'] = notes
        res['reason'] = '; '.join(notes)
        res['hints'] = hints(c, pk, teased, cues)
        res['rank_score'] = round(res['clip_score'] + bonus(res['hints']), 2)
        out.append(res)
    out.sort(key=lambda x: (-x['rank_score'], x['ranges'][0][0]))
    checks = {
        'score_vs_length': spearman([x['clip_score'] for x in out], [x['duration'] for x in out]),
        'score_vs_position': spearman([x['clip_score'] for x in out], [x['position'] for x in out]),
        'gate_agreement': round(sum(1 for x in out for g in GATES
                                    if x['gates'][g]['pass'] in (0, x['runs']) and not x['gates'][g]['unsure'])
                                / max(1, 2 * len(out)), 2),
        'mean_spread': round(statistics.mean(max(x['scores'][d]['runs']) - min(x['scores'][d]['runs'])
                                             for x in out for d in DIMS), 2),
    }
    return {'project': pdir.name, 'pool': plan['pool'], 'weights': WEIGHTS, 'runs': len(answers),
            'peaks': pk, 'checks': checks, 'clips': out, 'made': time.strftime('%Y-%m-%d %H:%M')}


# ---------------------------------------------------------------- output

def hint_text(h):
    out = []
    if h.get('teased'):
        out.append("in the creator's teaser")
    if h.get('replay'):
        r = h['replay']
        out.append('viewers replayed this' + (f" ({', '.join(r['flags'])})" if r['flags'] else ''))
    if h.get('lively'):
        lv = h['lively']
        bits = []
        if lv['laughter_s'] >= 1:
            bits.append(f"laughter {lv['laughter_s']:.0f} s")
        if lv['both_talk_s'] >= 1.5:
            bits.append(f"both talk at once {lv['both_talk_s']:.0f} s")
        out.append(', '.join(bits))
    return ' · '.join(out)


def write_txt(pdir, doc, path):
    cl = doc['clips']
    count = {s: sum(1 for x in cl if x['status'] == s) for s in ('clean', 'check', 'fix')}
    rows = [f"# Clip scores for {len(cl)} clip ideas ({doc['runs']} blind runs), best first. "
            f"{count['fix']} have a note to fix, {count['check']} a note to check.",
            '# A clip score judges how well-made a clip looks from its words and sound (hook, payoff, feeling,',
            '# shareability), compared with the other moments of this video. It is not a prediction of views.',
            '# Pick from the top (the rank includes a tiny hint bonus that only reorders near-ties). A "fix?" note',
            '# (needs context, the payoff comes after the cut) is for the repair round, not a reason to drop a',
            '# clip. Phase-1 rules still apply: no overlap, one per topic, coverage.', '']
    for n, x in enumerate(cl, 1):
        span = ' + '.join(f'{fmt_ts(a).split(".")[0]}-{fmt_ts(b).split(".")[0]}' for a, b in x['ranges'])
        topic = f"  [{x['topic']}]" if x.get('topic') else ''
        rows.append(f"{n:>2}. {x['id']:<7} {x['clip_score']:>4}/10 {x['band']:<9} {span} ({x['duration']:.0f} s)  "
                    f"\"{x.get('title') or ''}\"{topic}")
        sc = x['scores']
        rows.append('    ' + ' · '.join(f"{d} {sc[d]['mean']:.1f} \"{sc[d]['why']}\"" for d in DIMS))
        for note in x.get('notes') or []:
            rows.append(f'    {note}')
        h = hint_text(x['hints'])
        if h:
            rows.append(f'    hints: {h}')
        if x['tags']:
            rows.append(f"    tags: {', '.join(x['tags'])}")
        if x.get('fixes'):
            rows.append('    caption fixes to check: ' + ' · '.join(f'"{a}" -> "{b}"' for a, b in x['fixes']))
        if x.get('sensitive'):
            rows.append(f"    sensitive: {', '.join(x['sensitive'])}")
        if x['better_start']:
            bs = x['better_start']
            rows.append(f"    a stronger start may be at {fmt_ts(bs['t'])}: \"{bs['text']}\"")
        rows.append(f"    ranges: {x['ranges']}")
    rows.append('')
    ck = doc['checks']
    rows.append('== CHECKS ==')
    warn = []
    for k, label in (('score_vs_length', 'score vs clip length'), ('score_vs_position', 'score vs place in the packet')):
        v = ck[k]
        rows.append(f"{label}: {'n/a' if v is None else v}" + ('  <- strong: a sign of bias' if v is not None and abs(v) >= 0.5 else ''))
        if v is not None and abs(v) >= 0.5:
            warn.append(label)
    rows.append(f"gates agreed in all runs: {ck['gate_agreement']:.0%}; mean spread of scores between runs: {ck['mean_spread']}")
    if doc['peaks']:
        rows.append('replay peaks: ' + ' · '.join(f"{fmt_ts(p['start']).split('.')[0]} ({p['strength']})" for p in doc['peaks']))
    path.write_text('\n'.join(rows) + '\n', encoding='utf-8')
    return count, warn


def log(pdir, doc):
    """One row per clip idea in output/clip-log.csv. Rows of this project and the same pool (regular or
    deep) are replaced; the user's verdicts on them are kept."""
    pool = 'deep' if doc['pool'] == 'deep' else 'regular'
    cols = ['date', 'project', 'pool', 'id', 'start', 'duration', 'language', 'clip_score', 'status', *DIMS,
            'alone_fail', 'ending_fail', 'laughter_s', 'both_talk_s', 'replay', 'teased', 'picked', 'user_decision']
    old, kept = [], {}
    if LOG.exists():
        with open(LOG, newline='', encoding='utf-8') as f:
            for r in csv.DictReader(f):
                if r.get('project') != pdir.name or (r.get('pool') or 'regular') != pool:
                    old.append(r)
                elif r.get('user_decision') or r.get('picked'):    # the user's verdicts survive a re-run
                    kept[(r.get('id'), str(r.get('start')))] = (r.get('picked', ''), r.get('user_decision', ''))
    lang = (load_json(pdir / 'project.json', {}) or {}).get('language', '')
    for x in doc['clips']:
        h = x['hints']
        old.append({'date': doc['made'][:10], 'project': pdir.name, 'pool': pool, 'id': x['id'],
                    'start': x['ranges'][0][0],
                    'duration': x['duration'], 'language': lang, 'clip_score': x['clip_score'], 'status': x['status'],
                    **{d: x['scores'][d]['mean'] for d in DIMS},
                    'alone_fail': x['gates']['alone']['fail'], 'ending_fail': x['gates']['ending']['fail'],
                    'laughter_s': (h.get('lively') or {}).get('laughter_s', 0),
                    'both_talk_s': (h.get('lively') or {}).get('both_talk_s', 0),
                    'replay': (h.get('replay') or {}).get('strength', ''), 'teased': int(bool(h.get('teased'))),
                    'picked': kept.get((x['id'], str(x['ranges'][0][0])), ('', ''))[0],
                    'user_decision': kept.get((x['id'], str(x['ranges'][0][0])), ('', ''))[1]})
    LOG.parent.mkdir(exist_ok=True)
    with open(LOG, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction='ignore')
        w.writeheader()
        w.writerows(old)


def critic_for(pdir, clip):
    """The critic's result for a clip in clips.json (matched by "from" or by identical ranges), or None."""
    doc = load_json(pdir / 'critic' / 'critic.json')
    if not doc:
        return None
    for x in doc['clips']:
        if clip.get('from') == x['id'] or [list(map(float, r)) for r in clip.get('ranges', [])] == x['ranges']:
            return x
    return None


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('project')
    ap.add_argument('--fresh', action='store_true', help='start over (earlier packets and answers go to critic/old/)')
    ap.add_argument('--from', dest='source', choices=['auto', 'clips', 'candidates', 'deep'], default='auto',
                    help='judge candidates.json (default when it exists) or the clips.json shortlist')
    ap.add_argument('--runs', type=int, default=RUNS, help=f'blind runs (default {RUNS})')
    a = ap.parse_args()
    pdir = project_dir(a.project)
    cdir, txt = where(pdir, a.source)
    plan = load_json(cdir / 'plan.json')
    if plan and a.fresh:
        keep = cdir / 'old' / time.strftime('%Y%m%d-%H%M%S')
        keep.mkdir(parents=True)
        for f in list(cdir.glob('run-*')) + [cdir / 'plan.json', cdir / 'critic.json']:
            if f.exists():
                shutil.move(str(f), str(keep / f.name))
        print(f'   (earlier critic files moved to {keep.relative_to(pdir)})')
        plan = None
    if not plan:
        prepare(pdir, a.source, max(1, a.runs))
        return

    answers, probs, missing = {}, [], []
    for r in range(1, plan['runs'] + 1):
        f = cdir / f'run-{r}.json'
        if not f.exists():
            missing.append(r)
            continue
        ans = load_json(f)
        p = check_run(plan, r, ans)
        if p:
            probs += p
        else:
            answers[str(r)] = ans
    if missing:
        print(f"-> waiting for run(s) {', '.join(map(str, missing))} of {plan['runs']}: start a `{AGENT}` helper "
              f"for each (files: " + '; '.join(', '.join(plan['files'][str(r)]) for r in missing) + ')')
    if probs:
        print('PROBLEMS (run that helper again and pass it these lines):')
        for p in probs[:30]:
            print('   ' + p)
    if missing or probs:
        if len(answers) < max(2, plan['runs'] - 1) or missing:
            raise SystemExit(1)
        print(f"   (going on with {len(answers)} good runs of {plan['runs']})")
    doc = merge(pdir, plan, answers)
    save_json(cdir / 'critic.json', doc)
    count, warn = write_txt(pdir, doc, txt)
    log(pdir, doc)
    print(f"-> {len(doc['clips'])} clip ideas judged, best first ({count['fix']} with a note to fix, "
          f"{count['check']} to check):")
    for n, x in enumerate(doc['clips'][:15], 1):
        flag = {'fix': '  [fix?]', 'check': '  [check]'}.get(x['status'], '')
        print(f"   {n:>2}. {x['id']:<7} {x['clip_score']:>4}/10 {x['band']:<9} {x.get('title') or ''}{flag}")
    for w in warn:
        print(f'   WARNING: {w} is strongly linked to the score (possible bias)')
    if a.source == 'deep':
        print(f'\nnext: the honesty check:  python run.py honesty {pdir.name}')
        return
    print(f'\nnext: read {txt.relative_to(pdir.parent.parent)}, repair the top clips that have a '
          f'note (once), and write the final clips.json from the top, each with "from": "<id>"')


if __name__ == '__main__':
    main()
