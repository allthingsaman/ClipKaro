"""Join the part readers' answers into one topic map and one list of clip candidates.

    python run.py topics <project>            # after every parts/part-NN.json is written
    python run.py topics <project> --check    # check topics.json again after the AI edited it

Each reader (see .claude/skills/clip-video/references/reading-parts.md) quotes the transcript's
words and copies line times; it never writes a time of its own. This step does the mechanical
part: it finds every quote in the transcript (exact, or at least 80% of the words in order), takes
the exact word times from there, stores the transcript's own words instead of the quote, joins the
parts at their seams, and checks everything. An error names the part whose reader must run again.

Writes, in output/<project>/:
    topics.json      the topic map: topics in time order, no gaps, with roles, key lines, terms,
                     energy, honesty notes and open ends (chapters and threads come later)
    topics.txt       the same as a readable map, with what to check first
    candidates.json  every clip candidate with exact ranges, ready to copy into clips.json
    candidates.txt   the candidates in time order, with their exact words, for ranking them together
"""
import argparse
import bisect
import json
import re
import statistics
import sys
from difflib import SequenceMatcher

from .common import die, fmt_ts, load_json, norm_token, project_dir, save_json
from .parts import est_tokens

TOPIC_ROLES = {'story', 'explanation', 'argument', 'advice', 'debate', 'banter', 'reaction', 'digression',
               'teaser', 'sponsor', 'intro', 'outro', 'housekeeping', 'other'}
STRUCTURAL = {'teaser', 'sponsor', 'intro', 'outro', 'housekeeping'}
KEY_ROLES = {'hook', 'question', 'claim', 'example', 'setup', 'turn', 'punchline', 'conclusion', 'callback', 'reaction'}
VOICES = {'own', 'quoting', 'hypothetical', 'sarcasm', 'impression', 'game'}
ENERGY = {'low', 'medium', 'high'}
ENERGY_TAGS = {'humour', 'conflict', 'strong-claim', 'surprise', 'emotion', 'story-peak'}
SENSITIVE = {'politics', 'religion', 'caste-communal', 'accusation', 'crime', 'health', 'money', 'legal'}
OPEN_KINDS = {'setup', 'question', 'story'}
HOOKS = {'contrarian', 'question', 'fact', 'story', 'desire', 'reframe'}
LINK_TYPES = {'answers', 'pays_off', 'callback_to', 'continues'}
VAGUE = re.compile(r'^(story|part|topic|discussion|segment|chapter|conversation|talk)\s*\d*$', re.I)

NEAR = 60.0            # a quote is looked for within this many seconds of the line it cites
MERGE_GAP = 20.0       # topic starts closer than this are one topic
CAND_TOKENS = 18000    # candidates.txt is split above this
BRIEF_FOCUS = '.claude/skills/clip-video/references/reading-parts.md (section "Focus reads")'


class Transcript:
    """Words and lines, with the lookups the checks need."""

    def __init__(self, words, lines):
        self.words, self.lines = words, lines
        self.norm = [norm_token(w['w']) for w in words]
        self.starts = [w['s'] for w in words]
        self.line_at = {round(ln['s'], 2): i for i, ln in enumerate(lines)}

    def line_index(self, t):
        return self.line_at.get(round(float(t), 2)) if isinstance(t, (int, float)) else None

    def word_range(self, a, b):
        """Indexes of words with a <= start < b."""
        return bisect.bisect_left(self.starts, a), bisect.bisect_left(self.starts, b)

    def text(self, i0, i1):
        return ' '.join(w['w'].strip() for w in self.words[i0:i1 + 1])

    def find(self, quote, near, span=None, before=NEAR, after=NEAR):
        """(first word index, last word index, share of the quote's words matched in order), or None.
        Looks within `before`/`after` seconds of `near` (and inside span = (a, b) if given)."""
        q = [t for t in (norm_token(x) for x in str(quote or '').split()) if t]
        if not q or not isinstance(near, (int, float)):
            return None
        a, b = near - before, near + after
        if span:
            a, b = max(a, span[0] - 1.0), min(b, span[1] + 1.0)
        lo, hi = self.word_range(a, b)
        toks, L = self.norm[lo:hi], len(q)
        exact = [i for i in range(len(toks) - L + 1) if toks[i:i + L] == q]
        if exact:
            i = min(exact, key=lambda k: abs(self.words[lo + k]['s'] - near))
            return lo + i, lo + i + L - 1, 1.0
        qs, best = set(q), None
        for i in range(len(toks)):
            for w in range(max(1, L - 2), L + 3):
                win = toks[i:i + w]
                if len(win) < w or len(qs & set(win)) < 0.5 * L:
                    continue
                blocks = [m for m in SequenceMatcher(None, q, win, autojunk=False).get_matching_blocks() if m.size]
                r = sum(m.size for m in blocks) / L
                if r >= 0.8:
                    s_i, e_i = lo + i + blocks[0].b, lo + i + blocks[-1].b + blocks[-1].size - 1
                    key = (r, -abs(self.words[s_i]['s'] - near))
                    if best is None or key > best[0]:
                        best = (key, (s_i, e_i, round(r, 2)))
        return best[1] if best else None


class Problems:
    def __init__(self):
        self.errors, self.warnings = [], []

    def err(self, part, msg):
        self.errors.append((part, msg))

    def warn(self, where, msg):
        self.warnings.append((where, msg))


def _is_num(x):
    return isinstance(x, (int, float)) and not isinstance(x, bool)


def check_quote(tr, pb, part, what, quote, near, span=None, **kw):
    """The matched (i0, i1, ratio), reporting an error when the quote isn't in the transcript."""
    if not isinstance(quote, str) or not quote.strip():
        pb.err(part, f'{what}: the quote is missing')
        return None
    if not _is_num(near):
        pb.err(part, f'{what}: the line time is missing or not a number')
        return None
    m = tr.find(quote, near, span, **kw)
    if not m:
        pb.err(part, f'{what}: "{quote[:60]}" not found near {near} (copy the words exactly as the file has them)')
    elif m[2] < 1.0:
        pb.warn(f'part {part}', f'{what}: quote matched only {int(m[2] * 100)}% ("{quote[:40]}")')
    return m


def read_part(tr, pb, plan_part, ans, first_line_s):
    """Check one reader's answer. Returns (topics owned by this part, candidates, blocks, lead_in)."""
    k = plan_part['part']
    a, b = plan_part['stretch']
    ctx = plan_part['context']
    if not isinstance(ans, dict):
        pb.err(k, 'the answer is not a JSON object')
        return [], [], [], None
    for key in ('topics', 'blocks', 'candidates'):
        if not isinstance(ans.get(key), list):
            pb.err(k, f'"{key}" is missing or not a list')
            return [], [], [], None

    topics = []
    for n, t in enumerate(ans['topics'], 1):
        what = f'topic {n}'
        if not isinstance(t, dict):
            pb.err(k, f'{what} is not an object')
            continue
        start = t.get('start')
        li = tr.line_index(start)
        if li is None:
            pb.err(k, f'{what}: start {start} is not the start of a line (copy the number at the start of the line)')
            continue
        start = tr.lines[li]['s']
        if not (a - 0.01 <= start < b) and not (k == 1 and start < a):
            if ctx[0] <= start <= ctx[1]:
                pb.warn(f'part {k}', f'{what} starts at {fmt_ts(start)}, in the context, not in its stretch: left to the other part')
            else:
                pb.err(k, f'{what}: start {fmt_ts(start)} is outside this part')
            continue
        flags = []
        cue = t.get('cue')
        if cue:
            m = tr.find(cue, start, (tr.lines[max(0, li - 1)]['s'], tr.lines[min(len(tr.lines) - 1, li + 1)]['e']))
            if not m:
                pb.err(k, f'{what}: the cue "{str(cue)[:50]}" is not at its start line {start}')
                continue
            cue_line = next(i for i, ln in enumerate(tr.lines) if ln['i0'] <= m[0] <= ln['i1'])
            if cue_line != li:
                flags.append('snapped')
                li, start = cue_line, tr.lines[cue_line]['s']
            cue = tr.text(m[0], m[1])
            if m[2] < 1.0:
                flags.append('fuzzy_quote')
        else:
            cue = None
            flags.append('no_cue')
        role = t.get('role')
        if role not in TOPIC_ROLES:
            pb.err(k, f'{what}: role "{role}" is not one of {sorted(TOPIC_ROLES)}')
            continue
        key_lines = []
        for j, kl in enumerate(t.get('key_lines') or [], 1):
            if not isinstance(kl, dict):
                pb.err(k, f'{what} key line {j} is not an object')
                continue
            m = check_quote(tr, pb, k, f'{what} key line {j}', kl.get('words'), kl.get('line'), ctx)
            if not m:
                continue
            if kl.get('role') not in KEY_ROLES:
                pb.err(k, f'{what} key line {j}: role "{kl.get("role")}" is not one of {sorted(KEY_ROLES)}')
            if kl.get('voice') not in VOICES:
                pb.err(k, f'{what} key line {j}: voice "{kl.get("voice")}" is not one of {sorted(VOICES)}')
            soft = kl.get('softened_by')
            soft_out = None
            if soft:
                sm = tr.find(soft, tr.words[m[1]]['e'], ctx, before=30, after=90)
                if sm:
                    soft_out = {'words': tr.text(sm[0], sm[1]), 'start': tr.words[sm[0]]['s'], 'end': tr.words[sm[1]]['e']}
                else:
                    pb.warn(f'part {k}', f'{what} key line {j}: its softener "{str(soft)[:40]}" was not found')
            key_lines.append({'words': tr.text(m[0], m[1]), 'start': tr.words[m[0]]['s'], 'end': tr.words[m[1]]['e'],
                              'role': kl.get('role'), 'voice': kl.get('voice'), 'softened_by': soft_out,
                              **({'fuzzy': m[2]} if m[2] < 1.0 else {})})
        if len(key_lines) > 4:
            pb.warn(f'part {k}', f'{what}: more than 4 key lines')
        for fld, allowed in (('energy_tags', ENERGY_TAGS), ('sensitive', SENSITIVE)):
            bad = [x for x in t.get(fld) or [] if x not in allowed]
            if bad:
                pb.err(k, f'{what}: {fld} {bad} not in {sorted(allowed)}')
        if t.get('energy') not in ENERGY:
            pb.err(k, f'{what}: energy "{t.get("energy")}" is not low, medium or high')
        refs = []
        for q in t.get('refers_back') or []:
            m = tr.find(q, start, ctx, before=0, after=8 * 60)
            if m:
                refs.append({'words': tr.text(m[0], m[1]), 'start': tr.words[m[0]]['s'], 'to': None})
            else:
                pb.warn(f'part {k}', f'{what}: back-reference "{str(q)[:40]}" not found')
        opens = []
        for o in t.get('open') or []:
            if not isinstance(o, dict) or o.get('kind') not in OPEN_KINDS:
                pb.err(k, f'{what}: an open item needs kind setup, question or story')
                continue
            m = tr.find(o.get('words'), o.get('line'), ctx)
            if m:
                opens.append({'kind': o['kind'], 'words': tr.text(m[0], m[1]), 'start': tr.words[m[0]]['s'],
                              'resolved_by': None})
            else:
                pb.warn(f'part {k}', f'{what}: open {o.get("kind")} "{str(o.get("words"))[:40]}" not found')
        title = str(t.get('title') or '').strip()
        summary = str(t.get('summary') or '').strip()
        if not title:
            pb.err(k, f'{what}: no title')
            continue
        terms = [str(x) for x in t.get('terms') or []]
        topics.append({'part': k, 'start': round(start, 2), 'title': title, 'summary': summary, 'role': role,
                       'cue': cue, 'key_lines': key_lines, 'terms': terms[:8], 'energy': t.get('energy'),
                       'energy_tags': t.get('energy_tags') or [], 'sensitive': t.get('sensitive') or [],
                       'self_contained': bool(t.get('self_contained')), 'needs': t.get('needs') or None,
                       'refers_back': refs, 'open': opens, 'flags': flags, '_line': li,
                       '_title_long': len(title.split()) > 8, '_summary_long': len(summary.split()) > 40,
                       '_terms_many': len(terms) > 8})

    # the best moment of every 5-minute block
    blocks = []
    want = [x for x, _ in plan_part['blocks']]
    got = {}
    for n, bl in enumerate(ans['blocks'], 1):
        if not isinstance(bl, dict) or not _is_num(bl.get('from')):
            pb.err(k, f'block {n}: needs "from" (the block start as printed)')
            continue
        f = min(want, key=lambda x: abs(x - bl['from']))
        if abs(f - bl['from']) > 1.0:
            pb.err(k, f'block {n}: from {bl["from"]} is not one of the block starts {want}')
            continue
        best = bl.get('best')
        if isinstance(best, str) and best.strip().lower() in ('', 'none', 'null'):
            best = None
        if best is not None and not isinstance(best, dict):
            pb.err(k, f'block {fmt_ts(f)}: "best" must be an object or null')
            continue
        end = next(e for s, e in plan_part['blocks'] if s == f)
        if best:
            m = check_quote(tr, pb, k, f'block {fmt_ts(f)}', best.get('words'), best.get('line'), (f - 5, end + 5))
            got[f] = {'from': f, 'best': {'words': tr.text(m[0], m[1]), 'start': tr.words[m[0]]['s'],
                                          'end': tr.words[m[1]]['e'], 'why': best.get('why')} if m else None,
                      'why': bl.get('why')}
        else:
            if not bl.get('why'):
                pb.err(k, f'block {fmt_ts(f)}: "best" is null without a "why"')
            got[f] = {'from': f, 'best': None, 'why': bl.get('why')}
    for f in want:
        if f not in got:
            pb.err(k, f'the 5-minute block starting {fmt_ts(f)} ({f}) has no entry')
    blocks = [got[f] for f in want if f in got]

    # clip candidates
    cands, seen = [], set()
    for n, c in enumerate(ans['candidates'], 1):
        cid = str(c.get('id') or f'c{n}') if isinstance(c, dict) else f'c{n}'
        what = f'candidate {cid}'
        if not isinstance(c, dict) or not isinstance(c.get('pieces'), list) or not c['pieces']:
            pb.err(k, f'{what}: needs "pieces"')
            continue
        if cid in seen:
            pb.err(k, f'{what}: the id is used twice')
            continue
        seen.add(cid)
        ranges, ok = [], True
        for j, pc in enumerate(c['pieces'][:3], 1):
            if not isinstance(pc, dict):
                ok = False
                break
            m1 = check_quote(tr, pb, k, f'{what} piece {j} first words', pc.get('first'), pc.get('first_line'), ctx)
            m2 = check_quote(tr, pb, k, f'{what} piece {j} last words', pc.get('last'), pc.get('last_line'), ctx,
                             before=NEAR, after=NEAR + 90)
            if not m1 or not m2:
                ok = False
                break
            s, e = tr.words[m1[0]]['s'], tr.words[m2[1]]['e']
            if e <= s:
                pb.err(k, f'{what} piece {j}: its last words come before its first words')
                ok = False
                break
            ranges.append([round(s, 2), round(e, 2)])
        if not ok:
            continue
        if len(c['pieces']) > 3:
            pb.err(k, f'{what}: at most 3 pieces')
            continue
        dur = sum(e - s for s, e in ranges)
        main = max(ranges, key=lambda r: r[1] - r[0])
        mid = (main[0] + main[1]) / 2
        if not (a - 0.01 <= mid < b + 0.01):
            pb.err(k, f'{what}: its middle ({fmt_ts(mid)}) is not in this part\'s stretch')
            continue
        for j, ((s1, e1), (s2, e2)) in enumerate(zip(ranges, ranges[1:])):
            cold_open = j == 0 and e1 - s1 <= 6.5 and all(s1 >= e or e1 <= s for s, e in ranges[1:])
            if s2 < e1 and not cold_open:
                pb.err(k, f'{what}: pieces must play in the order they were said (one cold-open line of ~5 s may go first)')
                ok = False
                break
        if not ok:
            continue
        if dur < 10 or dur > 100:
            pb.err(k, f'{what}: {dur:.0f} s long (clips are 15-90 s)')
            continue
        if not (15 <= dur <= 90):
            pb.warn(f'part {k}', f'{what}: {dur:.0f} s (15-90 s is the limit)')
        if c.get('hook_type') not in HOOKS:
            pb.err(k, f'{what}: hook_type "{c.get("hook_type")}" is not one of {sorted(HOOKS)}')
        sc = c.get('score')
        if not _is_num(sc) or not 1 <= sc <= 10:
            pb.err(k, f'{what}: score must be 1-10')
            continue
        cands.append({'id': f'p{k}-{cid}', 'part': k, 'ranges': ranges, 'duration': round(dur, 1),
                      'title': str(c.get('title') or '').strip(), 'hook_type': c.get('hook_type'), 'score': sc,
                      'why': c.get('why'), 'needs_context': c.get('needs_context') or None,
                      'text': ' … '.join(words_text(tr, s, e) for s, e in ranges)})
    if len(cands) > 5:
        pb.warn(f'part {k}', f'{len(cands)} candidates (up to 5 asked)')
    lead = ans.get('lead_in') if isinstance(ans.get('lead_in'), dict) else {}
    return topics, cands, blocks, (lead.get('summary') or None)


def pause_before(lines, topic):
    i = topic['_line']
    return lines[i]['s'] - lines[i - 1]['e'] if i else 0.0


def words_text(tr, s, e):
    i0, i1 = tr.word_range(s - 0.005, e)
    return ' '.join(w['w'].strip() for w in tr.words[i0:i1] if w['e'] <= e + 0.01)


def replay_peak(heat, a, b):
    """How much the "most replayed" curve rises over [a, b] above its own neighbourhood, or None."""
    if not heat:
        return None
    inside = [v for s, e, v in heat if e > a and s < b]
    near = [v for s, e, v in heat if e > a - 300 and s < b + 300]
    if not inside or not near:
        return None
    return round(max(inside) - statistics.median(near), 3)


def teaser_hits(tr, topics):
    """Topics later in the video that hold a line the creator also put in the cold-open teaser
    (a hint of the creator's own highlights). A teaser line counts as found when at least 70% of
    its words appear again, in order, later in the video."""
    teaser = [t for t in topics if t['role'] == 'teaser']
    if not teaser:
        for t in topics:
            t['teased'] = None
        return 0
    where = {}                                   # word -> its positions, for fast lookups
    for i, tok in enumerate(tr.norm):
        if tok:
            where.setdefault(tok, []).append(i)
    hits = {}
    for t in teaser:
        after = bisect.bisect_left(tr.starts, t['end'] + 30)
        for li in range(t['_line'], len(tr.lines)):
            ln = tr.lines[li]
            if ln['s'] >= t['end']:
                break
            toks = [x for x in tr.norm[ln['i0']:ln['i1'] + 1] if x]
            if len(toks) < 5:
                continue
            # long teaser lines are often two re-cut sentences: match overlapping chunks of ~9 words
            chunks = [toks] if len(toks) <= 12 else [toks[i:i + 9] for i in range(0, len(toks) - 4, 5)]
            for q in chunks:
                if len(q) < 5:
                    continue
                votes = {}
                for off, tok in enumerate(q):
                    for pos in where.get(tok, ()):
                        if pos >= after:
                            votes[pos - off] = votes.get(pos - off, 0) + 1
                best = None
                for st in sorted(votes):
                    near = sum(votes.get(st + d, 0) for d in range(-2, 3))   # one word more or less
                    if near < 0.6 * len(q) or st < after:
                        continue
                    lo = max(after, st - 2)
                    win = tr.norm[lo:st + len(q) + 2]
                    blocks = [m for m in SequenceMatcher(None, q, win, autojunk=False).get_matching_blocks() if m.size]
                    r = sum(m.size for m in blocks) / len(q)
                    if r >= (0.8 if len(chunks) > 1 else 0.7) and (best is None or r > best[0]):
                        best = (r, lo + blocks[0].b)
                if best:
                    hits.setdefault(tr.words[best[1]]['s'], ln['s'])
    for t in topics:
        t['teased'] = any(t['start'] <= s < t['end'] for s in hits) or None
    topics_hits = sorted(hits)
    return topics_hits


FOCUS_BEFORE, FOCUS_AFTER = 90.0, 60.0     # a focused re-read looks this far around a hint (our own choice)
FOCUS_CONTEXT = 60.0
FOCUS_MAX = 3                              # at most this many re-reads per kind of hint


def uncovered_hints(project, doc, cands):
    """Hints with no candidate at all: a line from the creator's own teaser found later in the video,
    or a strong "most replayed" peak. Videos without these hints simply get none."""
    from .critic import peaks
    out = []
    hits, groups = sorted(doc.get('teaser_lines_found_later') or []), []
    for t in hits:
        if groups and t - groups[-1][-1] < 60:
            groups[-1].append(t)
        else:
            groups.append([t])
    covered = lambda a, b: any(e > a and s < b for c in cands for s, e in c['ranges'])
    # the teaser moments where most of a teaser line comes back first (more matched pieces)
    open_groups = [g for g in groups if not covered(g[0] - 10, g[-1] + 10)]
    for g in sorted(open_groups, key=lambda g: (-len(g), g[0]))[:FOCUS_MAX]:
        out.append({'kind': 'teaser', 't': g[0], 'end': g[-1],
                    'why': "the creator used this line in the video's opening teaser"})
    n = 0
    for p in peaks(project, doc):
        if n < FOCUS_MAX and not covered(p['start'], p['end']) and len(p['flags']) < 2:
            out.append({'kind': 'replay', 't': p['start'], 'end': p['end'],
                        'why': 'viewers replayed this stretch more than the rest' +
                               (f" ({', '.join(p['flags'])}: maybe navigation, not interest)" if p['flags'] else '')})
            n += 1
    return sorted(out, key=lambda h: h['t'])


def write_focus(pdir, out, hints, lines):
    """One small file per uncovered hint, for a part reader: 90 s before to 60 s after it."""
    from .parts import line_text
    plan = []
    for k, h in enumerate(hints, 1):
        a, b = max(lines[0]['s'], h['t'] - FOCUS_BEFORE), min(lines[-1]['e'], h['end'] + FOCUS_AFTER)
        ctx = [ln for ln in lines if ln['e'] > a - FOCUS_CONTEXT and ln['s'] < b + FOCUS_CONTEXT]
        num = f'{k:02d}'
        rel = (out / f'focus-{num}.json').relative_to(pdir.parent.parent).as_posix()
        body = [f'# ClipKaro FOCUS READ {k} of {len(hints)}: a second, careful look at one stretch.',
                f'# Why: {h["why"]}, at {fmt_ts(h["t"]).split(".")[0]}. No clip idea covers it yet.',
                f'# YOUR STRETCH: {fmt_ts(a).split(".")[0]}-{fmt_ts(b).split(".")[0]} ({a:.2f}-{b:.2f} s). '
                f'Lines outside it are context only.', '# format: [start_seconds-end_seconds] text', '']
        state = 'before'
        for ln in ctx:
            if state == 'before' and ln['s'] >= a - 0.01:
                body.append(f'# ===== YOUR STRETCH STARTS ({a:.2f}) =====')
                state = 'in'
            if state == 'in' and ln['s'] >= b:
                body.append(f'# ===== YOUR STRETCH ENDS ({b:.2f}) =====')
                state = 'after'
            body.append(line_text(ln) + ('   <== HINT' if ln['s'] <= h['t'] < ln['e'] + 0.5 else ''))
        if state == 'in':
            body.append(f'# ===== YOUR STRETCH ENDS ({b:.2f}) =====')
        body += ['', f'# TASK (full brief: {BRIEF_FOCUS})',
                 '# Up to 2 clip candidates that include the line marked HINT, with the setup and the payoff it needs,',
                 '# or none if no good, self-contained clip exists here. Same candidate format and rules as a part.',
                 f'# Write {rel} as {{"topics": [], "blocks": [], "candidates": [...]}}, then reply in at most 3 lines.']
        (out / f'focus-{num}.txt').write_text('\n'.join(body) + '\n', encoding='utf-8')
        plan.append({'part': f'f{k}', 'file': f'focus-{num}.txt', 'json': f'focus-{num}.json',
                     'stretch': [round(a, 2), round(b, 2)],
                     'context': [round(ctx[0]['s'], 2), round(ctx[-1]['e'], 2)], 'hint': h})
    save_json(out / 'focus.json', {'focus': plan})
    return plan


def read_focus(tr, pb, out):
    """Candidates from the focused re-reads that have answered (ids f1-c1, ...)."""
    plan = (load_json(out / 'focus.json') or {}).get('focus', [])
    got = []
    for fp in plan:
        f = out / fp['json']
        if not f.exists():
            continue
        try:
            ans = json.loads(f.read_text(encoding='utf-8'))
        except json.JSONDecodeError as e:
            pb.err(fp['part'], f'{fp["json"]} is not valid JSON ({e})')
            continue
        if isinstance(ans, dict):                # a focus read has no topics or 5-minute blocks
            ans = {**ans, 'topics': [], 'blocks': []}
        # quotes are checked as for a part, but a focus candidate may reach anywhere in the context;
        # what it must do is include the hinted line. Its problems only skip that candidate.
        fpb = Problems()
        _, cands, _, _ = read_part(tr, fpb, {**fp, 'stretch': fp['context'], 'blocks': []}, ans,
                                   tr.lines[0]['s'] if tr.lines else 0.0)
        for where, msg in fpb.errors:
            pb.warn(f"focus {fp['part']}", f'{msg} (skipped)')
        h = fp['hint']
        for c in cands[:2]:
            if not any(e > h['t'] - 1 and s < h['end'] + 1 for s, e in c['ranges']):
                pb.warn(f"focus {fp['part']}", f"candidate {c['id']} doesn't include the hinted line (skipped)")
                continue
            c['id'] = c['id'].replace(f"p{fp['part']}-", f"{fp['part']}-")
            c['focus'] = h['kind']
            got.append(c)
    return plan, got


def build(pdir, plan, args):
    pb = Problems()
    words = load_json(pdir / 'transcript' / 'words.json')
    lines = load_json(pdir / 'transcript' / 'sentences.json')
    project = load_json(pdir / 'project.json', {}) or {}
    tr = Transcript(words, lines)
    out = pdir / args.dir
    all_topics, all_cands, per_part = [], [], []
    for pp in plan['parts']:
        f = out / pp['json']
        if not f.exists():
            pb.err(pp['part'], f'no answer yet ({args.dir}/{pp["json"]}): run its reader')
            continue
        try:
            ans = json.loads(f.read_text(encoding='utf-8'))
        except json.JSONDecodeError as e:
            pb.err(pp['part'], f'{pp["json"]} is not valid JSON ({e})')
            continue
        topics, cands, blocks, lead = read_part(tr, pb, pp, ans, lines[0]['s'])
        if not topics:
            pb.err(pp['part'], 'no topic starts in its stretch')
        all_topics += topics
        all_cands += cands
        per_part.append({'part': pp['part'], 'stretch': pp['stretch'], 'lead_in': lead, 'blocks': blocks,
                         'note': ans.get('note') if isinstance(ans, dict) else None,
                         'n_topics': len(topics), 'n_candidates': len(cands)})
    focus_plan, focus_cands = read_focus(tr, pb, out)
    all_cands += focus_cands
    if pb.errors:
        return None, pb

    # one list of topics in time order, starts closer than MERGE_GAP joined, no gaps
    all_topics.sort(key=lambda t: t['start'])
    merged = []
    for t in all_topics:
        close = merged and t['start'] - merged[-1]['start'] < MERGE_GAP
        if close and (merged[-1]['role'] in STRUCTURAL) != (t['role'] in STRUCTURAL):
            close = False                                    # an ad or intro next to real content: keep both
        if close:
            prev = merged[-1]
            if bool(prev['cue']) != bool(t['cue']):          # the one with an opening cue wins,
                keep = prev if prev['cue'] else t
            else:                                            # else the one after the longer pause
                keep = prev if pause_before(lines, prev) >= pause_before(lines, t) else t
            drop = t if keep is prev else prev
            pb.warn(fmt_ts(keep['start']), f'topics "{drop["title"]}" and "{keep["title"]}" start {abs(t["start"] - prev["start"]):.0f} s apart: kept one')
            keep['key_lines'] = (keep['key_lines'] + drop['key_lines'])[:4]
            keep['terms'] = list(dict.fromkeys(keep['terms'] + drop['terms']))[:8]
            for fld in ('sensitive', 'energy_tags'):
                keep[fld] = list(dict.fromkeys(keep[fld] + drop[fld]))
            keep['open'] = keep['open'] + drop['open']
            keep['refers_back'] = keep['refers_back'] + drop['refers_back']
            order = ['low', 'medium', 'high']
            keep['energy'] = max(keep['energy'], drop['energy'], key=lambda e: order.index(e) if e in order else 0)
            if not drop['self_contained']:
                keep['self_contained'] = False
                keep['needs'] = keep['needs'] or drop['needs']
            merged[-1] = keep
        else:
            merged.append(t)
    first = lines[0]['s']
    if merged and merged[0]['start'] > first + 0.01:
        if merged[0]['start'] - first <= 60:
            merged[0]['start'] = round(first, 2)
            merged[0]['_line'] = 0
            merged[0]['flags'].append('snapped')
        else:
            pb.err(1, f'the first {fmt_ts(merged[0]["start"] - first)} of the video have no topic (start one at {first:.2f})')
            return None, pb
    last_end = words[-1]['e']
    for i, t in enumerate(merged):
        t['end'] = round(merged[i + 1]['start'] if i + 1 < len(merged) else last_end, 2)
        t['id'] = f't{i + 1:03d}'
    # a part whose stretch begins inside an earlier topic: that topic continues there
    for pp in per_part:
        if pp['lead_in']:
            host = next((t for t in merged if t['start'] <= pp['stretch'][0] < t['end']), None)
            if host and host['part'] != pp['part']:
                host['summary_cont'] = pp['lead_in']
                host['flags'].append('crosses_seam')

    heat = project.get('heatmap')
    for t in merged:
        t['replay'] = replay_peak(heat, t['start'], t['end'])
    n_teased = teaser_hits(tr, merged)

    # candidates: their topic, replay hint, sensitive tags; never in a structural topic
    for c in all_cands:
        main = max(c['ranges'], key=lambda r: r[1] - r[0])
        mid = (main[0] + main[1]) / 2
        topic = next((t for t in merged if t['start'] <= mid < t['end']), merged[-1])
        c['topic'] = topic['id']
        c['sensitive'] = topic['sensitive']
        c['replay'] = replay_peak(heat, main[0], main[1])
        for s, e in c['ranges']:
            for t in merged:
                if t['role'] in STRUCTURAL and t['start'] < e and s < t['end']:
                    pb.err(c['part'], f'candidate {c["id"]} uses the {t["role"]} at {fmt_ts(t["start"])} (never clip ads, teasers, intros or outros)')
    if pb.errors:
        return None, pb
    all_cands.sort(key=lambda c: c['ranges'][0][0])

    # warnings that point at weak spots
    hours = max(1e-6, (last_end - first) / 3600)
    per_hour = len(merged) / hours
    if not 8 <= per_hour <= 40:
        pb.warn('map', f'{per_hour:.0f} topics an hour (usually 8-40)')
    for t in merged:
        d = t['end'] - t['start']
        if d > 8 * 60:
            pb.warn(t['id'], f'{fmt_ts(t["start"])} {fmt_ts(d)} long: needs one split point')
        if d < 30 and t['role'] not in STRUCTURAL:
            pb.warn(t['id'], f'{fmt_ts(t["start"])} only {d:.0f} s long')
        if 'no_cue' in t['flags']:
            pb.warn(t['id'], f'{fmt_ts(t["start"])} no opening cue: check where it starts')
        if t['_title_long'] or VAGUE.match(t['title']) or t['title'].lower() in ('intro', 'introduction') and t['start'] > 60:
            pb.warn(t['id'], f'title "{t["title"]}" is vague or too long')
        if t['_summary_long']:
            pb.warn(t['id'], 'summary over 40 words')
        if t['_terms_many']:
            pb.warn(t['id'], 'more than 8 terms')
    titles = [t['title'].lower() for t in merged]
    for t in merged:
        if titles.count(t['title'].lower()) > 1:
            pb.warn(t['id'], f'title "{t["title"]}" is used twice')
    for pp in per_part:
        a, b = pp['stretch']
        if pp['n_topics'] < (b - a) / 360:
            pb.warn(f'part {pp["part"]}', f'only {pp["n_topics"]} topics in {fmt_ts(b - a)}: skimmed?')
        mids = [((c['ranges'][0][0] + c['ranges'][-1][1]) / 2) for c in all_cands if c['part'] == pp['part']]
        mids += [bl['best']['start'] for bl in pp['blocks'] if bl.get('best')]
        if len(mids) >= 3 and all(m < (a + b) / 2 for m in mids):
            pb.warn(f'part {pp["part"]}', 'all its candidates and best moments are in the first half of its stretch: skimmed?')
        if not pp['n_candidates'] and not any(bl.get('best') for bl in pp['blocks']):
            pb.warn(f'part {pp["part"]}', 'no candidate and no best moment at all')

    for t in merged:
        for k in ('_line', '_title_long', '_summary_long', '_terms_many'):
            t.pop(k, None)
    doc = {'video': {'title': project.get('title'), 'channel': project.get('channel'),
                     'duration': project.get('duration'), 'language': project.get('language'), 'project': pdir.name},
           'parts': [{k: v for k, v in pp.items()} for pp in per_part],
           'chapters': [], 'topics': merged, 'threads': [],
           'warnings': [f'{w}: {m}' for w, m in pb.warnings],
           'teaser_lines_found_later': [round(x, 2) for x in n_teased] if n_teased else []}
    return (doc, all_cands), pb


def write_map(pdir, doc, cands, path):
    v, topics = doc['video'], doc['topics']
    dur = v.get('duration') or (topics[-1]['end'] if topics else 0)
    hours = max(1e-6, dur / 3600)
    L = [f"{v.get('title') or pdir.name} · {fmt_ts(dur)} · {len(doc['parts'])} part(s) · "
         f"{len(topics)} topics ({len(topics) / hours:.0f} an hour)"]
    warn = doc.get('warnings') or []
    if warn:
        L.append(f'CHECK FIRST ({len(warn)})')
        L += [f'  {w}' for w in warn]
    L.append('PARTS  stretch               topics  candidates  5-min blocks with a best moment   note')
    for pp in doc['parts']:
        a, b = pp['stretch']
        best = sum(1 for bl in pp['blocks'] if bl.get('best'))
        note = (pp.get('note') or '').replace('\n', ' ')
        L.append(f"  {pp['part']:<4} {fmt_ts(a):>9}-{fmt_ts(b):<9}  {pp['n_topics']:>6}  {pp['n_candidates']:>10}  "
                 f"{best:>3} of {len(pp['blocks']):<26}  {note[:90]}")
    thirds = [0, 0, 0]
    for c in cands:
        mid = (c['ranges'][0][0] + c['ranges'][-1][1]) / 2
        thirds[min(2, int(3 * mid / max(dur, 1)))] += 1
    L.append(f'CANDIDATES BY THIRD   first {thirds[0]} · middle {thirds[1]} · last {thirds[2]}')
    chapters = doc.get('chapters') or []
    for t in topics:
        ch = next((c for c in chapters if c.get('start') == t['start']), None)
        if ch:
            L.append(f"CHAPTER  {ch.get('title')} ({fmt_ts(ch['start'])}-{fmt_ts(ch.get('end', t['end']))})")
        extra = [f"energy {t.get('energy', '-')}"]
        if t.get('replay') is not None and t['replay'] >= 0.05:
            extra.append(f"replay peak +{t['replay']:.2f}")
        if t.get('teased'):
            extra.append('in the cold open')
        if t.get('sensitive'):
            extra.append('sensitive: ' + ', '.join(t['sensitive']))
        L.append(f"  {fmt_ts(t['start']):>9}  {t['id']}  {t['role']:<12} {t['title']}   " + ' · '.join(extra))
        bits = []
        if t.get('cue'):
            bits.append(f'cue "{t["cue"][:60]}"')
        for kl in (t.get('key_lines') or [])[:2]:
            bits.append(f"[{kl['role']}{'' if kl['voice'] == 'own' else ', ' + kl['voice']}] \"{kl['words'][:70]}\"")
        if bits:
            L.append('             ' + ' · '.join(bits))
    opens = [(t, o) for t in topics for o in (t.get('open') or []) if not o.get('resolved_by')]
    if opens:
        L.append('OPEN ENDS')
        for t, o in opens:
            L.append(f"  {t['id']} {fmt_ts(o['start'])} {o['kind']} \"{o['words'][:70]}\"")
    if doc.get('threads'):
        L.append('THREADS')
        for th in doc['threads']:
            L.append(f"  {th.get('title')}: " + ', '.join(th.get('topics', [])))
    path.write_text('\n'.join(L) + '\n', encoding='utf-8')


def write_candidates(pdir, cands):
    def block(c):
        times = ' + '.join(f'{fmt_ts(s)}-{fmt_ts(e)}' for s, e in c['ranges'])
        hints = []
        if c.get('replay') is not None and c['replay'] >= 0.05:
            hints.append(f"replay peak +{c['replay']:.2f}")
        if c.get('sensitive'):
            hints.append('sensitive: ' + ', '.join(c['sensitive']))
        if c.get('needs_context'):
            hints.append(f"needs: {c['needs_context']}")
        return '\n'.join([
            f"{c['id']}  {times} ({c['duration']:.0f} s)  score {c['score']}  {c['hook_type']}  \"{c['title']}\"  [{c['topic']}]"
            + (('  · ' + ' · '.join(hints)) if hints else ''),
            f"  ranges: {json.dumps(c['ranges'])}",
            f"  why: {c.get('why') or ''}",
            f"  text: {c['text']}", ''])
    blocks = [block(c) for c in cands]
    head = (f'# {len(cands)} clip candidates in time order. Rank them all together; copy "ranges" and add '
            f'"from": "<id>" in clips.json.\n\n')
    files, cur = [], head
    for bl in blocks:
        if est_tokens(cur + bl) > CAND_TOKENS and cur != head:
            files.append(cur)
            cur = head
        cur += bl + '\n'
    files.append(cur)
    for old in pdir.glob('candidates*.txt'):
        old.unlink()
    names = ['candidates.txt'] if len(files) == 1 else [f'candidates-{i + 1}.txt' for i in range(len(files))]
    for name, text in zip(names, files):
        (pdir / name).write_text(text, encoding='utf-8')
    if len(files) > 1:
        (pdir / 'candidates.txt').write_text(
            f'# {len(cands)} clip candidates, too many for one file: read ALL of '
            + ', '.join(names) + ' before ranking.\n', encoding='utf-8')
        names = ['candidates.txt'] + names
    return names


def check_doc(pdir, doc, words):
    """Checks for topics.json after the AI's global pass (chapters, links, threads)."""
    pb = Problems()
    topics = doc.get('topics') or []
    ids = {t.get('id'): t for t in topics}
    end = words[-1]['e'] if words else 0
    seen_ids = set()
    for i, t in enumerate(topics):
        if not isinstance(t, dict):
            pb.err('topics', f'topic {i + 1} is not an object')
            return pb
        if not t.get('id') or t['id'] in seen_ids:
            pb.err(t.get('id'), 'a topic id is missing or used twice')
        seen_ids.add(t.get('id'))
        if not _is_num(t.get('start')) or not _is_num(t.get('end')):
            pb.err(t.get('id'), 'start and end must be numbers')
            return pb
        if not str(t.get('title') or '').strip():
            pb.err(t.get('id'), 'no title')
        if t.get('energy') not in ENERGY:
            pb.err(t.get('id'), f'energy "{t.get("energy")}" is not low, medium or high')
        for fld in ('key_lines', 'open', 'sensitive', 'refers_back'):
            if not isinstance(t.get(fld, []), list):
                pb.err(t.get('id'), f'"{fld}" must be a list')
        if t.get('role') not in TOPIC_ROLES:
            pb.err(t.get('id'), f'role "{t.get("role")}" not allowed')
        if not (0 <= t.get('start', -1) < t.get('end', -1) <= end + 1):
            pb.err(t.get('id'), 'start/end outside the video or in the wrong order')
        if i and abs(topics[i - 1].get('end', 0) - t.get('start', 0)) > 0.02:
            pb.err(t.get('id'), 'topics must follow each other with no gap or overlap')
        for ln in t.get('links') or []:
            to = ids.get(ln.get('to'))
            if ln.get('type') not in LINK_TYPES or not to:
                pb.err(t.get('id'), f'link {ln} has an unknown type or target')
            elif ln['type'] in ('answers', 'pays_off', 'callback_to', 'continues') and to['start'] >= t['start']:
                pb.err(t.get('id'), f'link {ln["type"]} must point back to an earlier topic')
        for o in t.get('open') or []:
            r = o.get('resolved_by')
            if r and (r not in ids or ids[r]['start'] < t['start']):
                pb.err(t.get('id'), f'open item resolved_by {r} must be this topic or a later one')
        for rb in t.get('refers_back') or []:
            to = rb.get('to')
            if to and (to not in ids or ids[to]['start'] >= t['start']):
                pb.err(t.get('id'), f'back-reference to {to} must point to an earlier topic')
    for th in doc.get('threads') or []:
        missing = [x for x in th.get('topics', []) if x not in ids]
        if missing:
            pb.err('threads', f'thread "{th.get("title")}" names unknown topics {missing}')
    for ch in doc.get('chapters') or []:
        if not any(t['start'] == ch.get('start') for t in topics):
            pb.err('chapters', f'chapter "{ch.get("title")}" must start where a topic starts')
    linked = any(t.get('links') for t in topics)
    for t in topics:
        if linked and not t.get('links') and any(kl.get('role') == 'callback' for kl in t.get('key_lines', [])):
            pb.warn(t['id'], 'a callback line, but no link to what it calls back to')
    return pb


def report(pb, header):
    if pb.errors:
        print(f'{header}: {len(pb.errors)} problem(s)')
        by = {}
        for part, msg in pb.errors:
            by.setdefault(part, []).append(msg)
        for part, msgs in by.items():
            label = f'part {part}' if isinstance(part, int) else str(part)
            print(f'  {label}:' + (' run its reader again' if isinstance(part, int) else ''))
            for m in msgs[:12]:
                print(f'     - {m}')
            if len(msgs) > 12:
                print(f'     - ... and {len(msgs) - 12} more')
    if pb.warnings:
        print(f'  {len(pb.warnings)} thing(s) to check (also listed at the top of topics.txt)')


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('project')
    ap.add_argument('--check', action='store_true', help='only check topics.json (after the AI edited it)')
    ap.add_argument('--rebuild', action='store_true', help='rebuild topics.json even if it has chapters/threads')
    ap.add_argument('--dir', default='parts', help='the parts folder inside the project (default parts)')
    a = ap.parse_args()
    pdir = project_dir(a.project)
    words = load_json(pdir / 'transcript' / 'words.json')
    if not words:
        die(f'no transcript in {pdir}')

    if a.check:
        doc = load_json(pdir / 'topics.json')
        if not doc:
            die('no topics.json yet: run  python run.py topics <project>  first')
        pb = check_doc(pdir, doc, words)
        report(pb, 'topics.json')
        if not pb.errors:
            write_map(pdir, doc, load_json(pdir / 'candidates.json', []) or [], pdir / 'topics.txt')
            print(f'ok: topics.json is consistent ({len(doc.get("topics", []))} topics, '
                  f'{len(doc.get("chapters") or [])} chapters, {len(doc.get("threads") or [])} threads); topics.txt updated')
        sys.exit(1 if pb.errors else 0)

    plan = load_json(pdir / a.dir / 'plan.json')
    if not plan:
        die(f'no {a.dir}/plan.json: run  python run.py parts {pdir.name}  first')
    old = load_json(pdir / 'topics.json')
    if old and (old.get('chapters') or old.get('threads')) and not a.rebuild and a.dir == 'parts':
        die('topics.json already has chapters/threads from a global pass; rebuilding would lose them. '
            'Use --rebuild to rebuild anyway.')
    result, pb = build(pdir, plan, a)
    if result is None:
        report(pb, 'not joined')
        sys.exit(1)
    doc, cands = result
    suffix = '' if a.dir == 'parts' else f'-{a.dir}'
    save_json(pdir / f'topics{suffix}.json', doc)
    save_json(pdir / f'candidates{suffix}.json', cands)
    write_map(pdir, doc, cands, pdir / f'topics{suffix}.txt')
    names = write_candidates(pdir, cands) if not suffix else []
    report(pb, 'joined')
    print(f'-> {len(doc["topics"])} topics, {len(cands)} candidates from {len(doc["parts"])} part(s)')
    out = pdir / a.dir
    focus_plan = (load_json(out / 'focus.json') or {}).get('focus')
    if focus_plan is None and not suffix:
        hints = uncovered_hints(load_json(pdir / 'project.json', {}) or {}, doc, cands)
        focus_plan = write_focus(pdir, out, hints, load_json(pdir / 'transcript' / 'sentences.json'))
        if focus_plan:
            print(f'\n{len(focus_plan)} hint(s) have no candidate yet (the creator\'s teaser or a replay peak): '
                  'start one `clipkaro-part-reader` per focus file, all at once:')
            for fp in focus_plan:
                print(f"   {out / fp['file']}   ({fp['hint']['why']}, {fmt_ts(fp['hint']['t']).split('.')[0]})")
            print(f'then run  python run.py topics {pdir.name}  again')
            return
    elif focus_plan:
        waiting = [fp['file'] for fp in focus_plan if not (out / fp['json']).exists()]
        if waiting:
            print(f"   (focus read(s) not answered yet: {', '.join(waiting)})")
    print(f'   map: {pdir / f"topics{suffix}.txt"}')
    if names:
        print('   candidates: ' + ', '.join(str(pdir / n) for n in names))
        print(f'next: let the critic judge all candidates:  python run.py critic {pdir.name}')


if __name__ == '__main__':
    main()
