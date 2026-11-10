"""The honesty check (pass B) for deep clips: does a clip joined from moments far apart keep what the
speaker meant?

    python run.py honesty <project>     1st time: one packet per deep clip (deep/honesty/<id>.txt);
                                        run again when the judges have answered: merges them

Three fresh judges read every packet, each in its own role (.claude/agents/clipkaro-honesty.md):
the rules auditor, the speaker's advocate, and a viewer who then watches the full video. When two
or three of them say "fail" or "unsure", the clip is rejected. When only one does, the clip is kept
with a "check" note quoting that judge, for the owner to look at before posting: in testing, every
honest clip that a single judge rejected had at most a mild problem, while misleading clips were
caught by two or more judges (the owner decided: being too strict only costs good clips).

A packet holds the stitched words as viewers will hear them; each piece inside its original
stretch (from 75 s before, or from the question it answers, to 60 s after); what was cut between
pieces (word for word when short, else a scan for corrections, jokes, negations and the same
names, as quotes: summaries drop exactly the softener that matters); other moments of the video
about the same names; and flags found by code (a piece opening on a pointer word or an answer word,
a possible softener right after a piece). Packets stay small (research: long inputs blur judges).
The judges never learn who made the clip or what the critic thought of it.
"""
import argparse
import json
import re

from .common import die, fmt_ts, load_json, norm_token, project_dir, save_json
from .parts import est_tokens
from . import topics as tp

ROLES = ('auditor', 'advocate', 'viewer')
VERDICTS = {'pass', 'fail', 'unsure'}
REJECT_AT = 2                    # this many judges saying fail / unsure reject a clip; one gives a note
BEFORE, AFTER = 75.0, 60.0       # seconds of the original shown around each piece
VERBATIM_GAP = 180.0             # gaps up to this long are shown word for word
SOFT_AFTER = 20.0                # look this far after a piece for a softener or correction
POINTERS = {'he', 'she', 'they', 'it', 'that', 'this', 'those', 'so', 'and', 'but', 'because', 'which',
            'वो', 'वह', 'वे', 'उसने', 'उसको', 'उसे', 'उनका', 'उनकी', 'उनको', 'इसलिए', 'लेकिन', 'और', 'तो',
            'यह', 'ये', 'इसका', 'इसको', 'उसका', 'wo', 'woh', 'isliye', 'lekin', 'toh', 'aur', 'ye', 'yeh'}
ANSWERS = {'yes', 'yeah', 'yep', 'no', 'nope', 'exactly', 'right', 'absolutely', 'sure', 'correct',
           'हाँ', 'हां', 'जी', 'बिल्कुल', 'बिलकुल', 'नहीं', 'सही', 'haan', 'han', 'bilkul', 'nahi', 'sahi', 'ji'}
SOFT = re.compile(r"just kidding|joking|i'?m kidding|not really|i mean|actually|sorry|to be fair|but seriously|"
                  r"correction|i was wrong|मज़ाक|मजाक|मजा़क|गलत|सच में नहीं|ऐसा नहीं|नहीं नहीं|लेकिन|बट |"
                  r"\bbut\b|however|though|\bnot\b|\bnever\b|नहीं|कभी नहीं|मत", re.I)


def ts(t):
    return fmt_ts(t).split('.')[0]


def lines_between(tr, a, b):
    return [ln for ln in tr.lines if ln['e'] > a + 0.01 and ln['s'] < b - 0.01]


def fmt_lines(lines, mark=None):
    out = []
    for ln in lines:
        inside = mark and any(ln['s'] < e and ln['e'] > s for s, e in mark)
        out.append(f"{'>>> ' if inside else ''}[{ln['s']:.1f}] {ln['text']}{' <<<' if inside else ''}")
    return out


def first_word(tr, t):
    i = tr.word_range(t - 0.005, t + 30)[0]
    return tr.words[i]['w'].strip() if i < len(tr.words) else ''


def flags(tr, ranges):
    out = []
    for k, (a, b) in enumerate(ranges, 1):
        w = norm_token(first_word(tr, a))
        if w in {norm_token(x) for x in POINTERS}:
            out.append(f'piece {k} opens on "{first_word(tr, a)}", a word that may point at something said before it')
        if w in {norm_token(x) for x in ANSWERS}:
            prev = [ln for ln in tr.lines if ln['e'] <= a + 0.01][-3:]
            q = next((ln for ln in reversed(prev) if ln['text'].rstrip().endswith('?')), None)
            out.append(f'piece {k} opens on the answer word "{first_word(tr, a)}"' +
                       (f'; the question before it: [{q["s"]:.1f}] "{q["text"]}" '
                        f'({"in the clip" if any(s <= q["s"] < e for s, e in ranges) else "NOT in the clip"})'
                        if q else ''))
        for ln in lines_between(tr, b, b + SOFT_AFTER):
            if SOFT.search(ln['text']) and not any(s <= ln['s'] < e for s, e in ranges):
                out.append(f'within {SOFT_AFTER:.0f} s after piece {k}: [{ln["s"]:.1f}] "{ln["text"]}" '
                           f'(a possible softener, correction or "but": is it cut off?)')
                break
    return out


def gap_text(tr, a, b, names):
    """What was cut between two pieces: word for word when short, else a scan (quotes, not a summary)."""
    if b - a <= VERBATIM_GAP:
        return ['(word for word)'] + fmt_lines(lines_between(tr, a, b))
    hits = []
    for ln in lines_between(tr, a, b):
        toks = {norm_token(x) for x in ln['text'].split()}
        if SOFT.search(ln['text']) and (ln['s'] - a < 120 or b - ln['e'] < 120):
            hits.append(ln)
        elif names & toks:
            hits.append(ln)
    hits = sorted(hits, key=lambda ln: min(ln['s'] - a, b - ln['e']))[:10]
    return [f'({ts(b - a)} cut; the lines below were found by a scan for corrections, jokes, negations near '
            f'the pieces and the same names; most of the cut is not shown)'] + fmt_lines(sorted(hits, key=lambda x: x['s']))


MAX_TOKENS = 6500               # long inputs blur judges (NoLiMa): shrink the windows until it fits


def build_packet(pdir, tr, doc, cid, ranges, title=''):
    for before, after in ((BEFORE, AFTER), (60.0, 45.0), (45.0, 30.0), (30.0, 20.0)):
        text, n = _packet(tr, doc, cid, ranges, before, after)
        if n <= MAX_TOKENS:
            break
    return text, n


def _packet(tr, doc, cid, ranges, BEFORE, AFTER):
    ranges = [list(r) for r in ranges]
    topics = (doc or {}).get('topics') or []
    mine = [t for t in topics if any(t['start'] < b and a < t['end'] for a, b in ranges)]
    names = {norm_token(x) for t in mine for x in t.get('terms') or [] if len(norm_token(x)) >= 3}
    rows = [f'# ClipKaro honesty check: clip {cid}. Who made it does not matter. Judge it as your role says.',
            '', '## THE CLIP AS VIEWERS WILL HEAR IT (pieces in this order)']
    for k, (a, b) in enumerate(ranges, 1):
        if k > 1:
            gap = a - ranges[k - 2][1]
            rows.append(f'[--- a jump: {ts(gap)} {"later" if gap > 0 else "EARLIER (moved before)"} in the video ---]')
        words = ' '.join(w['w'].strip() for w in tr.words[slice(*tr.word_range(a - 0.005, b))] if w['e'] <= b + 0.01)
        rows.append(f'piece {k} ({ts(a)}-{ts(b)}): {words}')
    rows += ['', '## THE ORIGINAL AROUND EACH PIECE (word for word; >>> <<< marks the piece; [seconds] are video times)']
    for k, (a, b) in enumerate(ranges, 1):
        lo = a - BEFORE
        prev_q = [ln for ln in lines_between(tr, a - 2 * BEFORE, a) if ln['text'].rstrip().endswith('?')]
        if prev_q:
            lo = min(lo, prev_q[-1]['s'])
        rows.append(f'### piece {k} ({ts(a)}-{ts(b)})')
        rows += fmt_lines(lines_between(tr, max(0.0, lo), b + AFTER), mark=[(a, b)])
    if len(ranges) > 1:
        rows += ['', '## WHAT WAS CUT BETWEEN THE PIECES']
        for k in range(1, len(ranges)):
            a, b = ranges[k - 1][1] + AFTER, ranges[k][0] - BEFORE
            rows.append(f'### between piece {k} and piece {k + 1}')
            rows += gap_text(tr, a, b, names) if b > a else ['(already shown above)']
    others = [t for t in topics if t not in mine and names & {norm_token(x) for x in t.get('terms') or []}][:3]
    if others:
        rows += ['', '## OTHER MOMENTS OF THE VIDEO ABOUT THE SAME NAMES (key lines, word for word)']
        for t in others:
            rows.append(f"{t['id']} {ts(t['start'])} \"{t['title']}\"")
            rows += [f"   [{kl['start']:.1f}] \"{kl['words']}\" ({kl['voice']})" for kl in t.get('key_lines') or []]
    fl = flags(tr, ranges)
    rows += ['', '## FLAGS FROM CODE (facts about the words; they can be false alarms)'] + ([f'- {f}' for f in fl] or ['- none'])
    text = '\n'.join(rows) + '\n'
    return text, est_tokens(text)


def check_answer(ans, cid, role):
    if not isinstance(ans, dict):
        return 'not a JSON object'
    if ans.get('verdict') not in VERDICTS:
        return 'verdict must be pass, fail or unsure'
    if not isinstance(ans.get('rules'), dict):
        return '"rules" must be an object with the rules 1-9'
    return None


def merge(hdir, clips):
    out, probs, missing = [], [], []
    for c in clips:
        judges = {}
        for role in ROLES:
            f = hdir / f"{c['id']}-{role}.json"
            if not f.exists():
                missing.append(f.name)
                continue
            ans = load_json(f)
            err = check_answer(ans, c['id'], role)
            if err:
                probs.append(f'{f.name}: {err}')
                continue
            judges[role] = ans
        if len(judges) < len(ROLES):
            continue
        verdicts = {r: j['verdict'] for r, j in judges.items()}
        bad = [r for r, v in verdicts.items() if v != 'pass']
        reason = '; '.join(f"{r}: {judges[r].get('reason', '')}" for r in bad)
        verdict = 'fail' if len(bad) >= REJECT_AT else 'check' if bad else 'pass'
        out.append({'id': c['id'], 'verdict': verdict, 'judges': verdicts, 'reason': reason})
    return out, probs, missing


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('project')
    ap.add_argument('--fresh', action='store_true', help='write new packets (earlier answers are kept)')
    a = ap.parse_args()
    pdir = project_dir(a.project)
    cands = load_json(pdir / 'deep' / 'candidates.json')
    if not cands:
        die(f'no deep/candidates.json: run  python run.py deep {pdir.name}  first')
    crit = load_json(pdir / 'deep' / 'critic' / 'critic.json')
    score = {x['id']: x['clip_score'] for x in (crit or {}).get('clips', [])}
    deep = [c for c in cands if c['kind'] == 'deep']
    if crit:                                     # only clips that tie or beat their own continuous version
        deep = [c for c in deep if c['id'] in score and score[c['id']] >= score.get(c.get('twin'), -1)]
    hdir = pdir / 'deep' / 'honesty'
    hdir.mkdir(parents=True, exist_ok=True)
    words = load_json(pdir / 'transcript' / 'words.json')
    lines = load_json(pdir / 'transcript' / 'sentences.json')
    tr = tp.Transcript(words, lines)
    doc = load_json(pdir / 'topics.json')
    if not deep:
        save_json(pdir / 'deep' / 'honesty.json', {'clips': []})
        print('-> no deep clip to check (none scored at least as high as its continuous version).')
        return
    # packets for clips that have none yet (all of them with --fresh); a clip judged earlier keeps its
    # verdicts, so a repaired clip added later is the only one judged again
    new = [c for c in deep if a.fresh or not (hdir / f"{c['id']}.txt").exists()]
    if new:
        for c in new:
            text, n = build_packet(pdir, tr, doc, c['id'], c['ranges'], c.get('title', ''))
            (hdir / f"{c['id']}.txt").write_text(text, encoding='utf-8')
            print(f"   {c['id']}.txt  ({n:,} tokens)")
        rel = hdir.relative_to(pdir.parent.parent).as_posix()
        print(f'-> {len(new)} new packet(s). next: for EACH new packet start 3 `clipkaro-honesty` helpers at once, '
              f'one per role (prompt e.g. "Role: advocate. Packet: {rel}/{new[0]["id"]}.txt"); each writes '
              f'<id>-<role>.json next to it. Then run  python run.py honesty {pdir.name}  again')
        return
    out, probs, missing = merge(hdir, deep)
    for p in probs:
        print(f'   ! {p}')
    if missing:
        print(f"-> waiting for: {', '.join(missing)}")
        if not out:
            raise SystemExit(1)
    save_json(pdir / 'deep' / 'honesty.json', {'clips': out})
    for x in out:
        print(f"   {x['id']:<7} {x['verdict'].upper():<5} " + ' '.join(f'{r}:{v}' for r, v in x['judges'].items())
              + (f"  ({x['reason'][:150]})" if x['reason'] else ''))
    print(f'next: python run.py deep {pdir.name}  for the report')


if __name__ == '__main__':
    main()
