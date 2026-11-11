"""Split a long transcript into parts the AI editor can read carefully, one helper per part.

    python run.py parts <project>                 # plan the parts and write them
    python run.py parts <project> --minutes 21    # each part's own stretch (default 21 minutes)

A 2-hour transcript is too big to read well in one go (the AI's file reader stops at 256 KB, and
long inputs get skimmed). So the transcript is cut into parts of at most ~25 minutes: each part has
its own STRETCH (about 21 minutes) plus 2 minutes of context on each side, so a clip (90 s at most)
never falls into a gap between two parts. Cuts go where the speaker pauses longest, never inside a
line. A short video (about 28 minutes of Hinglish or less) stays one part.

Writes output/<project>/parts/part-NN.txt (the lines exactly as in transcript.txt, with a header
and the task at the end) and parts/plan.json. Each part is read by one helper, which writes
parts/part-NN.json (see .claude/skills/clip-video/references/reading-parts.md); then
`python run.py topics <project>` checks and joins them.

Test-only options: --no-chapters hides the creator's chapters, --shift 0.5 moves every cut by half
a stretch (the seam test), --dir parts-test writes somewhere else.
"""
import argparse
import math
import re
import shutil
import time
import unicodedata

from . import sound
from .common import ROOT, die, fmt_ts, load_json, project_dir, save_json

TOKEN_CAP = 20000          # estimated tokens per part file: one default Read (25k) with room to spare
BYTE_CAP = 240_000         # the Read tool refuses whole files over 256 KB
SNAP_WINDOW = 60.0         # a cut moves to the longest pause within this many seconds
BLOCK = 300.0              # "the best moment in every 5 minutes"
BRIEF = '.claude/skills/clip-video/references/reading-parts.md'


def est_tokens(text):
    """Tokens the AI's reader will count, from weights measured on Hinglish transcripts:
    0.73 per Devanagari (or other non-Latin) letter, 0.29 per Latin letter, 0.78 per digit,
    0.28 per space or punctuation mark, plus 6 per line."""
    n = 6.0 * (text.count('\n') + 1)
    for c in text:
        cat = unicodedata.category(c)
        if cat[0] in 'LM':
            n += 0.29 if ord(c) < 0x250 else 0.73
        elif cat == 'Nd':
            n += 0.78
        elif c != '\n':
            n += 0.28
    return int(n)


def clean_about(desc, limit=600):
    """The prose part of a video description: no links, timestamps, promo or disclaimer lines."""
    promo = re.compile(r'^(disclaimer|t&c|subscribe|follow|order|download|stream|watch|join|buy|use code|'
                       r'timestamps?|chapters?|business|contact|instagram|twitter|facebook|linkedin|my gear|'
                       r'sponsor|thanks to|check out|get \d|book|enrol|enroll)\b', re.I)
    keep = []
    for line in (desc or '').splitlines():
        s = re.sub(r'^[\W_]+', '', line).strip()          # leading emoji, bullets and dashes
        if (len(s) < 30 or s.endswith(':') or re.search(r'https?://|www\.|\.com\b|@\w', s)
                or re.match(r'^\(?\d{1,2}:\d{2}', s) or promo.match(s) or sum(c.isalpha() for c in s) < 3):
            continue
        keep.append(s)
    text = ' · '.join(keep)
    return (text[:limit].rsplit(' ', 1)[0] + ' ...') if len(text) > limit else text


def line_text(ln):
    return f"[{ln['s']:.2f}-{ln['e']:.2f}] {ln['text']}"


def plan_stretches(lines, n, shift=0.0):
    """Cut points (line indexes) for n stretches of equal length, each moved to the line with the
    longest pause before it within SNAP_WINDOW seconds. shift moves every cut by that share of a stretch."""
    t0, t1 = lines[0]['s'], lines[-1]['e']
    size = (t1 - t0) / n
    targets = [t0 + (k + shift) * size for k in range(1, n)] if not shift else \
        [t0 + (k + shift) * size for k in range(0, n)]
    cuts = []
    for t in targets:
        if not (t0 < t < t1):
            continue
        best = None
        for i in range(1, len(lines)):
            gs, ge = lines[i - 1]['e'], lines[i]['s']          # the pause before line i
            if ge < t - SNAP_WINDOW or gs > t + SNAP_WINDOW:
                continue
            dist = 0.0 if gs <= t <= ge else min(abs(gs - t), abs(ge - t))
            key = (round(ge - gs, 2), -dist)
            if best is None or key > best[0]:
                best = (key, i)
        if best is None:                                       # never drop a cut
            best = (None, min(range(1, len(lines)), key=lambda i: abs(lines[i]['s'] - t)))
        if not cuts or best[1] > cuts[-1]:
            cuts.append(best[1])
    return [0] + cuts + [len(lines)]


def build(pdir, project, lines, n, margin, shift, chapters, out_dir='parts', cues=None):
    """The part files' text for n stretches: [(header-free info, text)]."""
    idx = plan_stretches(lines, n, shift)
    total = len(idx) - 1
    about = clean_about(project.get('description'))
    head_video = (f"# video: {project.get('title') or pdir.name} | {project.get('channel') or '-'} | "
                  f"{fmt_ts(project.get('duration') or lines[-1]['e'])} | {project.get('language') or '-'}")
    chap = ''
    if chapters and project.get('chapters'):
        chap = '# creator chapters: ' + ' · '.join(f"{fmt_ts(c['start']).split('.')[0]} {c['title']}"
                                                    for c in project['chapters'])
    try:
        where = (pdir / out_dir).relative_to(ROOT).as_posix()
    except ValueError:
        where = (pdir / out_dir).as_posix()
    parts = []
    for k in range(total):
        a_i, b_i = idx[k], idx[k + 1]
        a = lines[a_i]['s']
        b = lines[b_i]['s'] if b_i < len(lines) else lines[-1]['e']
        # context grows outward to whole lines: any line that reaches into the margin is shown whole
        before = [ln for ln in lines[:a_i] if ln['e'] > a - margin]
        after = [ln for ln in lines[b_i:] if ln['s'] < b + margin]
        own = lines[a_i:b_i]
        blocks, s = [], a
        while s < b - 1e-6:
            e = min(s + BLOCK, b)
            if blocks and e - s < 90:          # a last sliver joins the block before it
                blocks[-1][1] = round(e, 2)
            else:
                blocks.append([round(s, 2), round(e, 2)])
            s = e
        num = f'{k + 1:02d}'
        head = [f'# ClipKaro part {k + 1} of {total}. Read the whole file before answering '
                f'(if the reader shows a PARTIAL view, keep reading with offset/limit).', head_video]
        if about:
            head.append(f'# about: {about}')
        if chap:
            head.append(chap)
        head += [f'# YOUR STRETCH: {fmt_ts(a).split(".")[0]}-{fmt_ts(b).split(".")[0]} ({a:.2f}-{b:.2f} s). '
                 f'Lines outside it are context only.',
                 '# 5-MINUTE BLOCKS (start seconds): ' + ', '.join(f'{x:.2f}' for x, _ in blocks)]
        spots = sound.spots_in(cues, a, b)
        if spots:
            head.append('# LIVELY SPOTS from the sound (laughs, both talking at once; the detector can be wrong): '
                        'look at the words there, and judge them only by the words: ' + sound.spots_line(spots))
        head += ['# format: [start_seconds-end_seconds] text', '']
        body = [line_text(ln) for ln in before]
        body += [f'# ===== YOUR STRETCH STARTS ({a:.2f}) =====']
        body += [line_text(ln) for ln in own]
        body += [f'# ===== YOUR STRETCH ENDS ({b:.2f}) =====']
        body += [line_text(ln) for ln in after]
        foot = ['', f'# TASK (full brief: {BRIEF})',
                '# 1. Topics that START in your stretch: copy the opening line\'s start time, quote its first words exactly.',
                '# 2. The best moment in each 5-minute block of your stretch, or "best": null with a "why".',
                '# 3. Up to 5 clip candidates whose middle is in your stretch. Quote first and last words exactly.',
                f'# Write {where}/part-{num}.json, then reply in at most 5 lines.']
        text = '\n'.join(head + body + foot) + '\n'
        parts.append({'part': k + 1, 'file': f'part-{num}.txt', 'json': f'part-{num}.json',
                      'stretch': [round(a, 2), round(b, 2)],
                      'context': [round((before[0] if before else own[0])['s'], 2),
                                  round((after[-1] if after else own[-1])['e'], 2)],
                      'lines': len(before) + len(own) + len(after), 'own_lines': len(own),
                      'blocks': blocks, 'tokens': est_tokens(text), 'bytes': len(text.encode('utf-8')),
                      'text': text})
    return parts


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('project')
    ap.add_argument('--minutes', type=float, default=21.0, help="each part's own stretch (default 21)")
    ap.add_argument('--margin', type=float, default=120.0, help='context seconds on each side (default 120)')
    ap.add_argument('--no-chapters', action='store_true', help="don't show the creator's chapters (tests)")
    ap.add_argument('--shift', type=float, default=0.0, help='move every cut by this share of a stretch (tests)')
    ap.add_argument('--dir', default='parts', help='folder for the parts inside the project (default parts)')
    a = ap.parse_args()

    pdir = project_dir(a.project)
    project = load_json(pdir / 'project.json', {}) or {}
    lines = load_json(pdir / 'transcript' / 'sentences.json')
    if not lines:
        die(f'no transcript in {pdir}: run `python run.py fetch` first')
    if a.margin < 45:
        die('--margin must be at least 45 s, so a 90 s clip always fits inside one part')

    cues = sound.load(pdir)
    whole = '\n'.join(line_text(ln) for ln in lines)
    whole_tokens = est_tokens(whole) + 400
    span_min = (lines[-1]['e'] - lines[0]['s']) / 60
    n = 1 if whole_tokens <= TOKEN_CAP and not a.shift else max(1, math.ceil(span_min / a.minutes))
    while True:
        parts = build(pdir, project, lines, n, a.margin, a.shift, not a.no_chapters, a.dir, cues)
        if all(p['tokens'] <= TOKEN_CAP and p['bytes'] <= BYTE_CAP for p in parts) or n >= 80:
            break
        n += 1                                      # a fast talker: one more, smaller part

    out = pdir / a.dir
    out.mkdir(exist_ok=True)
    old_plan = load_json(out / 'plan.json')
    new_cuts = [p['stretch'] for p in parts]
    stale = [f for f in sorted(out.glob('part-*.json'))]
    if stale and (not old_plan or [p['stretch'] for p in old_plan.get('parts', [])] != new_cuts):
        keep = out / 'old' / time.strftime('%Y%m%d-%H%M%S')
        keep.mkdir(parents=True, exist_ok=True)
        if (out / 'plan.json').exists():
            shutil.copy2(out / 'plan.json', keep / 'plan.json')       # which plan these answers belong to
        for f in stale:
            shutil.move(str(f), str(keep / f.name))
        print(f'   (the parts changed: {len(stale)} earlier answer(s) moved to {keep.relative_to(pdir)})')
    for f in out.glob('part-*.txt'):
        f.unlink()
    for p in parts:
        (out / p['file']).write_text(p.pop('text'), encoding='utf-8')
    save_json(out / 'plan.json', {'project': pdir.name, 'minutes': a.minutes, 'margin': a.margin, 'shift': a.shift,
                                  'chapters_shown': not a.no_chapters and bool(project.get('chapters')),
                                  'first': round(lines[0]['s'], 2), 'last': round(lines[-1]['e'], 2),
                                  'whole_tokens': whole_tokens, 'parts': parts})

    print(f'-> {pdir.name}: {fmt_ts(lines[-1]["e"])} of speech, about {whole_tokens:,} tokens in all')
    print(f'   {len(parts)} part(s) in {pdir / a.dir}')
    print('   part  stretch               lines  tokens  size')
    for p in parts:
        s, e = p['stretch']
        print(f"   {p['part']:>4}  {fmt_ts(s):>9}-{fmt_ts(e):<9}  {p['lines']:>5}  {p['tokens']:>6,}  {p['bytes'] / 1024:.0f} KB")
    if len(parts) == 1:
        spots = (cues or {}).get('lively') or []
        if spots:
            print('\nlively spots from the sound (laughs, both talking at once; the detector can be wrong). '
                  'Look at the words there, and judge them only by the words:')
            for sp in spots:
                print(f"   {fmt_ts(sp['start']).split('.')[0]:>8}  {sp['why']}")
        elif cues is None:
            print(f'\n(no sound cues yet: python run.py sound {pdir.name})')
        print('\nnext: one part. Read transcript.txt in full and write a SHORTLIST of about twice the clips '
              f'wanted to clips.json, then  python run.py critic {pdir.name}')
    else:
        print(f'\nnext: one reader per part, all at once (brief: {BRIEF}); each writes '
              f'{a.dir}/part-NN.json. Then:  python run.py topics {pdir.name}')


if __name__ == '__main__':
    main()
