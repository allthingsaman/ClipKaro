"""The deep pass: stories spread across a whole video, joined into one short (roadmap item 17).

Only when the user asks ("deep clip this", "do a deep pass"), after the regular clips. Run it again
after each helper step; it does the next stage by itself:

    python run.py deep <project>    1. writes deep/map.txt (the compact topic map + seeds) for the
                                       thread finder, which writes deep/threads.json
                                    2. checks the threads and writes deep/thread-NN.txt (the real
                                       words around each one) for the composers, which write
                                       deep/thread-NN.json
                                    3. checks the joined clips and writes deep/candidates.json (each
                                       with its best continuous twin), then: critic --from deep,
                                       honesty
                                    4. after the critic and the honesty check: deep/report.txt
    python run.py deep <project> --fresh    start over (earlier files go to deep/old/)

Rules (references/picking-moments.md, "Never change what someone meant"): 2-3 pieces in the order
they were said (one cold-open line may go first), whole sentences, 30-75 s, a guest's answer keeps
the host's question. The narrator's own spoken intro may open a clip; a montage teaser (lines that
come again later in the video) never. A deep clip is kept only if the blind critic scores it at
least as high as its own best continuous version, and at most one of the three honesty judges
objects (that judge's reason then goes with the clip as a "check" note for the owner).
"No deep clip" is a normal answer: research found real long-distance threads are hard to find.
"""
import argparse
import json
import re
import shutil
import time
from difflib import SequenceMatcher

from .common import die, fmt_ts, load_json, norm_token, project_dir, save_json
from .parts import est_tokens, line_text
from . import topics as tp
from .cut import boundary_warnings

MAX_THREADS = 8
CONTEXT = 90.0                 # seconds of transcript shown around each topic of a thread
MIN_GAP = 60.0                 # a deep clip joins moments at least this far apart (else it's a regular clip)
STRUCT_BAN = {'sponsor', 'outro', 'housekeeping'}
OPENERS = {'teaser', 'intro'}   # only the narrator's own spoken words, never a montage of later lines
BRIEF = '.claude/skills/clip-video/references/deep-clips.md'


def ts(t):
    return fmt_ts(t).split('.')[0]


# ---------------------------------------------------------------- stage 1: the map

def seeds(doc, project):
    """Possible thread ends, found by code: unlinked open items and back-references, teaser lines
    found again later, and rare names shared by topics far apart (a weak seed: read them)."""
    topics = doc['topics']
    out = []
    for t in topics:
        for o in t.get('open') or []:
            if not o.get('resolved_by'):
                out.append(f"OPEN {o['kind']} in {t['id']} at {ts(o['start'])}: \"{o['words']}\"")
        for r in t.get('refers_back') or []:
            if not r.get('to'):
                out.append(f"REFERS BACK in {t['id']} at {ts(r['start'])}: \"{r['words']}\"")
    teaser = [t for t in topics if t['role'] == 'teaser']
    teased = {}
    for at in doc.get('teaser_lines_found_later') or []:
        later = next((t for t in topics if t['start'] <= at < t['end']), None)
        if later and teaser:
            teased.setdefault(later['id'], []).append(at)
    for tid, times in teased.items():
        out.append(f"TEASED: lines of the opening teaser come again in {tid} at " + ', '.join(ts(x) for x in times[:6]))
    where = {}
    for t in topics:
        for term in t.get('terms') or []:
            key = norm_token(term)
            if len(key) >= 4:
                where.setdefault(key, (term, []))[1].append(t)
    shared = []
    for key, (term, ts_) in where.items():
        if 2 <= len(ts_) <= 3 and ts_[-1]['start'] - ts_[0]['start'] >= 10 * 60:
            shared.append((ts_[-1]['start'] - ts_[0]['start'], term, ts_))
    for _, term, ts_ in sorted(shared, reverse=True)[:15]:
        out.append(f"SHARED NAME \"{term}\": " + ', '.join(f"{t['id']} ({ts(t['start'])})" for t in ts_))
    return out


def write_map(pdir, doc, project, regular):
    rows = [f"# ClipKaro deep pass: the topic map of ONE video, for finding stories spread across it.",
            f"# video: {project.get('title') or pdir.name} | {project.get('channel') or '-'} | "
            f"{ts(project.get('duration') or doc['topics'][-1]['end'])} | {project.get('language') or '-'}",
            f"# Write {(pdir / 'deep' / 'threads.json').relative_to(pdir.parent.parent).as_posix()} "
            f"as your instructions say (up to {MAX_THREADS} threads, or none).",
            '# Regular clips already made (a deep clip must not reuse their core): ' +
            (' · '.join(f"{ts(r[0][0])}-{ts(r[-1][1])}" for r in regular) or 'none'), '',
            '## SEEDS (found by code: possible ends of a thread; read them, they can be wrong)']
    rows += [f'- {s}' for s in seeds(doc, project)] or ['- none']
    rows += ['', '## TOPICS (time order)']
    for t in doc['topics']:
        extra = []
        if t.get('teased'):
            extra.append('in the opening teaser')
        if t.get('sensitive'):
            extra.append('sensitive: ' + ', '.join(t['sensitive']))
        if t.get('needs'):
            extra.append(f"needs: {t['needs']}")
        rows.append(f"{t['id']} {ts(t['start'])}-{ts(t['end'])} {t['role']:<11} \"{t['title']}\""
                    + (f"  [{'; '.join(extra)}]" if extra else ''))
        rows.append(f"    {t.get('summary') or ''}")
        for kl in t.get('key_lines') or []:
            soft = f" (softened by: \"{kl['softened_by']}\")" if kl.get('softened_by') else ''
            rows.append(f"    [{kl['role']}/{kl['voice']}] {ts(kl['start'])} ({kl['start']:.2f}) \"{kl['words']}\"{soft}")
        for o in t.get('open') or []:
            rows.append(f"    OPEN {o['kind']} {ts(o['start'])} ({o['start']:.2f}) \"{o['words']}\"")
        for r in t.get('refers_back') or []:
            rows.append(f"    REFERS BACK {ts(r['start'])} ({r['start']:.2f}) \"{r['words']}\"")
    text = '\n'.join(rows) + '\n'
    (pdir / 'deep' / 'map.txt').write_text(text, encoding='utf-8')
    return est_tokens(text)


# ---------------------------------------------------------------- stage 2: thread packets

def check_threads(tr, doc, ans):
    """The thread finder's answer: errors, and the threads that are fine."""
    ids = {t['id']: t for t in doc['topics']}
    errs, good = [], []
    if not isinstance(ans, dict) or not isinstance(ans.get('threads'), list):
        return ['threads.json must be {"threads": [...]}'], []
    for n, th in enumerate(ans['threads'][:MAX_THREADS], 1):
        name = th.get('id') or f'T{n}'
        tids = th.get('topics') or []
        bad = [x for x in tids if x not in ids]
        if bad or len(tids) < 2:
            errs.append(f'{name}: topics {tids} must be 2 or more known topic ids')
            continue
        starts = [ids[x]['start'] for x in tids]
        if starts != sorted(starts):
            errs.append(f'{name}: topics must be in time order')
            continue
        if starts[-1] - ids[tids[0]]['end'] < MIN_GAP:
            errs.append(f'{name}: its topics are too close together for a deep clip (a regular clip can hold it)')
            continue
        marks = {}
        for key in ('setup', 'payoff'):
            m = th.get(key) or {}
            topic = ids.get(m.get('topic'))
            if not topic or not m.get('words'):
                errs.append(f'{name}: "{key}" needs a topic and its exact words')
                break
            near = m['line'] if isinstance(m.get('line'), (int, float)) else topic['start']
            found = tr.find(m['words'], near, (topic['start'] - 30, topic['end'] + 30),
                            before=60, after=max(60.0, topic['end'] - near + 30))
            if not found:
                errs.append(f'{name}: {key} words "{str(m["words"])[:50]}" not found in {topic["id"]}')
                break
            marks[key] = tr.words[found[0]]['s']
        else:
            good.append({**th, 'id': name, 'marks': marks})
    return errs, good


def write_thread(pdir, tr, doc, th, k, regular):
    ids = {t['id']: t for t in doc['topics']}
    spans = []
    for tid in th['topics']:
        t = ids[tid]
        a, b = max(0.0, t['start'] - CONTEXT), t['end'] + CONTEXT
        if spans and a <= spans[-1][1]:
            spans[-1][1] = max(spans[-1][1], b)
        else:
            spans.append([a, b])
    rel = (pdir / 'deep' / f'thread-{k:02d}.json').relative_to(pdir.parent.parent).as_posix()
    rows = [f"# ClipKaro deep pass, thread {k}: compose a short from moments far apart in ONE video.",
            f"# Read your full instructions ({BRIEF}, section \"Composer\") first.",
            f"# Pattern: {th.get('pattern')}. Why these belong together: {th.get('why')}",
            f"# SETUP at {ts(th['marks']['setup'])}: \"{th['setup']['words']}\"",
            f"# PAYOFF at {ts(th['marks']['payoff'])}: \"{th['payoff']['words']}\"",
            '# Regular clips already made (do not reuse their core): ' +
            (' · '.join(f"{ts(r[0][0])}-{ts(r[-1][1])}" for r in regular) or 'none'),
            '# format: [start_seconds-end_seconds] text', '']
    for n, (a, b) in enumerate(spans):
        if n:
            rows.append(f'# [... {ts(a - spans[n - 1][1])} later in the video ...]')
        for ln in tr.lines:
            if ln['e'] > a and ln['s'] < b:
                mark = ''
                if ln['s'] - 0.01 <= th['marks']['setup'] < ln['e'] + 0.5:
                    mark = '   <== SETUP'
                elif ln['s'] - 0.01 <= th['marks']['payoff'] < ln['e'] + 0.5:
                    mark = '   <== PAYOFF'
                rows.append(line_text(ln) + mark)
    rows += ['', f'# TASK: up to 2 deep clips (2-3 pieces each) and the best continuous clip around the payoff,',
             f'# or none with a reason. Write {rel}, then reply in at most 4 lines.']
    text = '\n'.join(rows) + '\n'
    (pdir / 'deep' / f'thread-{k:02d}.txt').write_text(text, encoding='utf-8')
    return {'thread': th['id'], 'file': f'thread-{k:02d}.txt', 'json': f'thread-{k:02d}.json',
            'spans': spans, 'tokens': est_tokens(text), 'pattern': th.get('pattern')}


# ---------------------------------------------------------------- stage 3: candidates

def montage(tr, a, b, after):
    """True when the words of [a, b] come again later in the video (a re-cut teaser line)."""
    i0, i1 = tr.word_range(a - 0.005, b)
    toks = [x for x in tr.norm[i0:i1] if x]
    if len(toks) < 5:
        return False
    q = toks[:12]
    j0 = tr.word_range(after, after)[0]
    hay = tr.norm[j0:]
    for i in range(0, max(0, len(hay) - len(q)) + 1, 3):
        win = hay[i:i + len(q) + 2]
        r = sum(m.size for m in SequenceMatcher(None, q, win, autojunk=False).get_matching_blocks()) / len(q)
        if r >= 0.7:
            return True
    return False


def overlap_share(ranges, other):
    o = sum(max(0.0, min(b, y) - max(a, x)) for a, b in ranges for x, y in other)
    return o / max(1e-6, sum(b - a for a, b in ranges))


def build_candidates(pdir, tr, doc, plan, regular):
    ids = {t['id']: t for t in doc['topics']}
    end = tr.lines[-1]['e']
    first_content = next((t['start'] for t in doc['topics'] if t['role'] not in OPENERS | STRUCT_BAN), 0.0)
    pb = tp.Problems()
    out, notes = [], []
    for k, th in enumerate(plan['threads'], 1):
        f = pdir / 'deep' / th['json']
        if not f.exists():
            notes.append(f"thread {k}: no answer yet ({th['json']})")
            continue
        try:
            ans = json.loads(f.read_text(encoding='utf-8'))
        except json.JSONDecodeError as e:
            pb.err(f'thread {k}', f'{th["json"]} is not valid JSON ({e})')
            continue
        if not isinstance(ans, dict):
            pb.err(f'thread {k}', 'the answer must be a JSON object')
            continue
        if not ans.get('candidates'):
            notes.append(f"thread {k}: no deep clip ({ans.get('none_because') or 'no reason given'})")
            continue
        cands = [dict(c, id=f"c{n}") for n, c in enumerate(ans['candidates'][:2], 1) if isinstance(c, dict)]
        if isinstance(ans.get('continuous'), dict):
            cands.append(dict(ans['continuous'], id='x'))
        fake = {'topics': [], 'blocks': [], 'candidates': cands}
        part = {'part': f'd{k}', 'stretch': [0.0, end], 'context': [0.0, end], 'blocks': []}
        tpb = tp.Problems()
        _, got, _, _ = tp.read_part(tr, tpb, part, fake, tr.lines[0]['s'])
        for where, msg in tpb.errors:
            pb.err(f'thread {k}', msg)
        twin = next((c for c in got if c['id'].endswith('-x')), None)
        for c in got:
            c['id'] = c['id'].replace(f'pd{k}-', f'd{k}-')
            c['thread'] = th['thread']
            c['pattern'] = th.get('pattern')
            if c['id'].endswith('-x'):
                c['kind'] = 'continuous'
                if len(c['ranges']) != 1:
                    pb.err(f'thread {k}', 'the continuous twin must be one piece')
                    continue
                out.append(c)
                continue
            c['kind'] = 'deep'
            c['twin'] = twin['id'].replace(f'pd{k}-', f'd{k}-') if twin else None
            rs = c['ranges']
            if len(rs) < 2:
                pb.err(f'thread {k}', f"{c['id']}: a deep clip has 2-3 pieces (one piece is a regular clip)")
                continue
            if max(rs[j + 1][0] - rs[j][1] for j in range(len(rs) - 1)) < MIN_GAP:
                pb.warn(f'thread {k}', f"{c['id']}: its pieces are less than {MIN_GAP:.0f} s apart")
            bad = None
            for a, b in rs:
                for t in doc['topics']:
                    if t['start'] < b and a < t['end'] and t['role'] in STRUCT_BAN:
                        bad = f"uses the {t['role']} at {ts(t['start'])}"
                    elif t['start'] < b and a < t['end'] and t['role'] in OPENERS:
                        if (a, b) != tuple(rs[0]):
                            bad = f"uses the {t['role']} at {ts(t['start'])} after the start (only an opening line may come from it)"
                        elif montage(tr, a, b, first_content):
                            bad = f"its opening comes from a montage teaser (the line comes again at a later time): use that later line"
            if bad:
                pb.err(f'thread {k}', f"{c['id']}: {bad}")
                continue
            for r in regular:
                if overlap_share(rs, r) > 0.5:
                    pb.err(f'thread {k}', f"{c['id']}: more than half of it is a regular clip already made")
                    bad = True
                    break
            if bad:
                continue
            c['moments'] = [ts(a) for a, _ in rs]
            for w in boundary_warnings(rs, tr.words):     # Hindi transcripts have few full stops
                pb.warn(f'thread {k}', f"{c['id']}: {w}")
            out.append(c)
    return out, pb, notes


# ---------------------------------------------------------------- stage 4: report

def report(pdir, cands):
    crit = load_json(pdir / 'deep' / 'critic' / 'critic.json')
    hon = load_json(pdir / 'deep' / 'honesty.json')
    if not crit or not hon:
        return None
    score = {x['id']: x for x in crit['clips']}
    verdict = {x['id']: x for x in hon.get('clips', [])}
    rows, kept = ['# Deep clips: kept only when the critic scores them at least as high as their own continuous',
                  '# version AND at most one of the three honesty judges objects (that one becomes a note).', ''], []
    for c in [c for c in cands if c['kind'] == 'deep']:
        me, tw = score.get(c['id']), score.get(c.get('twin'))
        h = verdict.get(c['id'])
        why = []
        if not me:
            why.append('not scored')
        elif tw and me['clip_score'] < tw['clip_score']:
            why.append(f"its continuous version scores higher ({tw['clip_score']} vs {me['clip_score']})")
        if not h:
            why.append('no honesty verdict')
        elif h['verdict'] == 'fail':
            why.append(f"honesty: {h['verdict']} ({h.get('reason') or ''})")
        ok = not why
        note = h.get('reason') if ok and h and h['verdict'] == 'check' else None
        line = (f"{'KEEP' if ok else 'no  '} {c['id']:<7} {me['clip_score'] if me else '-':>4}/10 "
                f"(continuous {tw['clip_score'] if tw else '-'})  \"{c.get('title') or ''}\"  "
                f"moments {' · '.join(c['moments'])}")
        rows.append(line)
        rows.append(f"     ranges: {c['ranges']}" + ('' if ok else f"   why not: {'; '.join(why)}"))
        if note:
            rows.append(f"     CHECK before posting, one honesty judge objected: {note}")
        if ok:
            kept.append({**c, 'clip_score': me['clip_score'], **({'honesty_note': note} if note else {}),
                         'source_line': f"From {len(c['ranges'])} moments of the full video: " + ' · '.join(c['moments'])})
    best = {}                     # one deep clip per thread: the best score, then no honesty note, then the shorter
    for c in kept:
        b = best.get(c['thread'])
        rank = lambda x: (x['clip_score'], not x.get('honesty_note'), -x['duration'])
        if not b or rank(c) > rank(b):
            best[c['thread']] = c
    dropped = [c['id'] for c in kept if best[c['thread']] is not c]
    kept = list(best.values())
    if dropped:
        rows.append(f"(same story, a weaker version, left out: {', '.join(dropped)})")
    rows += ['', f'{len(kept)} deep clip(s) kept.' if kept else 'No deep clip passed: a normal answer.']
    (pdir / 'deep' / 'report.txt').write_text('\n'.join(rows) + '\n', encoding='utf-8')
    save_json(pdir / 'deep' / 'kept.json', kept)
    return kept, rows


def regular_ranges(pdir):
    clips = load_json(pdir / 'clips.json') or {}
    clips = clips.get('clips', clips) if isinstance(clips, dict) else clips
    return [c['ranges'] for c in clips if not c.get('deep')]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('project')
    ap.add_argument('--fresh', action='store_true', help='start over (earlier files go to deep/old/)')
    a = ap.parse_args()
    pdir = project_dir(a.project)
    ddir = pdir / 'deep'
    doc = load_json(pdir / 'topics.json')
    if not doc or not doc.get('topics'):
        die(f'no topic map yet: run  python run.py parts {pdir.name}  and the part reader(s), then  '
            f'python run.py topics {pdir.name}  (a short video has one part)')
    words = load_json(pdir / 'transcript' / 'words.json')
    lines = load_json(pdir / 'transcript' / 'sentences.json')
    tr = tp.Transcript(words, lines)
    project = load_json(pdir / 'project.json', {}) or {}
    regular = regular_ranges(pdir)
    if a.fresh and ddir.exists():
        keep = ddir / 'old' / time.strftime('%Y%m%d-%H%M%S')
        keep.mkdir(parents=True)
        for f in list(ddir.iterdir()):
            if f.name != 'old':
                shutil.move(str(f), str(keep / f.name))
        print(f'   (earlier deep files moved to {keep.relative_to(pdir)})')
    ddir.mkdir(exist_ok=True)

    # stage 1
    if not (ddir / 'map.txt').exists():
        n = write_map(pdir, doc, project, regular)
        print(f'-> deep/map.txt written ({len(doc["topics"])} topics, about {n:,} tokens)')
        print(f'next: start one `clipkaro-thread-finder` helper (prompt: "{(ddir / "map.txt").relative_to(pdir.parent.parent).as_posix()}"); '
              f'it writes deep/threads.json. Then run  python run.py deep {pdir.name}  again')
        return
    plan = load_json(ddir / 'plan.json')
    # stage 2
    if not plan:
        ans = load_json(ddir / 'threads.json')
        if ans is None:
            die('waiting for deep/threads.json from the thread finder')
        errs, good = check_threads(tr, doc, ans)
        for e in errs:
            print(f'   ! {e}')
        if not good:
            save_json(ddir / 'plan.json', {'threads': [], 'errors': errs})
            print('-> no usable thread: this video gets no deep clip (a normal answer).' if not errs else
                  '-> no usable thread. Fix the problems above with the thread finder and run again with --fresh, '
                  'or accept: no deep clip.')
            return
        threads = [write_thread(pdir, tr, doc, th, k, regular) for k, th in enumerate(good, 1)]
        save_json(ddir / 'plan.json', {'threads': threads, 'errors': errs})
        print(f'-> {len(threads)} thread(s):')
        for th in threads:
            print(f"   {th['file']}  {th['pattern']}  ({th['tokens']:,} tokens)")
        print(f'next: start one `clipkaro-composer` helper per thread file, all at once; each writes '
              f'deep/thread-NN.json. Then run  python run.py deep {pdir.name}  again')
        return
    if not plan['threads']:
        print('-> no thread: no deep clip for this video.')
        return
    # stage 3
    if not (ddir / 'candidates.json').exists() or any(
            (ddir / th['json']).stat().st_mtime > (ddir / 'candidates.json').stat().st_mtime
            for th in plan['threads'] if (ddir / th['json']).exists()):
        cands, pb, notes = build_candidates(pdir, tr, doc, plan, regular)
        for n in notes:
            print(f'   {n}')
        tp.report(pb, 'deep candidates')
        if pb.errors or pb.warnings:
            print('Run that thread\'s composer again and pass it the problem lines (a sentence cut in the middle '
                  'loses to its continuous twin), or accept fewer clips.')
        deep = [c for c in cands if c['kind'] == 'deep']
        save_json(ddir / 'candidates.json', cands)
        if not deep:
            print('-> no deep clip came out of the threads: a normal answer.')
            return
        print(f'-> {len(deep)} deep clip(s) and {len(cands) - len(deep)} continuous twin(s) in deep/candidates.json')
        for c in deep:
            print(f"   {c['id']:<6} {c['duration']:>4.0f} s  {' · '.join(c['moments'])}  \"{c.get('title') or ''}\"")
        print(f'next: the blind critic on deep clips and their twins:  python run.py critic {pdir.name} --from deep\n'
              f'      then the honesty check:  python run.py honesty {pdir.name}\n'
              f'      then  python run.py deep {pdir.name}  for the report')
        return
    # stage 4
    res = report(pdir, load_json(ddir / 'candidates.json'))
    if not res:
        print(f'waiting for the critic (python run.py critic {pdir.name} --from deep) and the honesty check '
              f'(python run.py honesty {pdir.name})')
        return
    kept, rows = res
    print('\n'.join(rows))
    if kept:
        print(f'\nnext: add the kept deep clips to clips.json with "deep": {{"moments": [...]}} and their "source_line" '
              f'in the caption (see deep/kept.json), then cut and edit as usual')


if __name__ == '__main__':
    main()
