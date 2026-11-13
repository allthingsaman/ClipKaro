"""Split a long transcript into parts the AI editor can read carefully, one helper per part.

    python run.py parts <project>                 # plan the parts and write them
    python run.py parts <project> --minutes 21    # each part's own stretch (default 21 minutes)
    python run.py parts <project> --at-least 10   # the user asked for a number of clips (also --at-most N,
                                                  # --clips N for exactly N, --any-count to forget it)
    python run.py parts <project> --deep yes      # the user's answer about deep clips (yes / no)
    python run.py parts <project> --mode quick    # quick mode, only when the user asked for it

A 2-hour transcript is too big to read well in one go (the AI's file reader stops at 256 KB, and
long inputs get skimmed). So the transcript is cut into parts of at most ~25 minutes: each part has
its own STRETCH (about 21 minutes) plus 2 minutes of context on each side, so a clip (90 s at most)
never falls into a gap between two parts. Cuts go where the speaker pauses longest, never inside a
line. A short video (about 28 minutes of Hinglish or less) stays one part.

Writes output/<project>/parts/part-NN.txt (the lines exactly as in transcript.txt, with a header
and the task at the end) and parts/plan.json. Each part is read by one helper, which writes
parts/part-NN.json (see .claude/skills/clip-video/references/reading-parts.md); then
`python run.py topics <project>` checks and joins them.

How many clips: unless the user asked for a number, every decent moment, from 3 up to 8 (what v1.1
made) or about one per 7 minutes of real video for long videos (break screens don't count), whichever
is more, at most "max_clips" from settings.json (20). A number the user asked for always wins and is
remembered in project.json ("wish"), so running parts again keeps it. Each part's reader is asked for
enough ideas (about 2.5 per clip at the top of the range, spread over the parts).

Modes: standard is the default (reader helpers, the critic, the repair round). Deep adds deep clips
(the user said so, or answered yes to the question for videos over 21 minutes). Quick, only when the
user asks for it ("quick", "use fewer tokens"): Claude reads the transcript or the parts itself, one at
a time, and picks straight into clips.json: no helpers, no critic, about v1.1's Claude usage.
Everything after picking is the same in every mode.

Live streams and gameplay (see `run.py kind`): lines said during break screens are replaced by one
marker line, and every part's header carries the stream rules.

Test-only options: --no-chapters hides the creator's chapters, --shift 0.5 moves every cut by half
a stretch (the seam test), --dir parts-test writes somewhere else.
"""
import argparse
import math
import re
import shutil
import time
import unicodedata

from . import kind, sound
from .common import ROOT, die, fmt_ts, load_json, project_dir, save_json, settings

TOKEN_CAP = 20000          # estimated tokens per part file: one default Read (25k) with room to spare
BYTE_CAP = 240_000         # the Read tool refuses whole files over 256 KB
SNAP_WINDOW = 60.0         # a cut moves to the longest pause within this many seconds
BLOCK = 300.0              # "the best moment in every 5 minutes"
BRIEF = '.claude/skills/clip-video/references/reading-parts.md'
MINUTES_PER_CLIP = 7.0     # long videos: up to about one clip per 7 minutes of real video
MIN_CLIPS = 3
V11_MAX = 8                # v1.1 made 3-8 clips; the default never offers fewer than that
IDEAS_PER_CLIP = 2.5       # clip ideas the readers bring per clip wanted (the critic ranks them all)
DEEP_ASK_MIN = 21.0        # longer than one part's stretch: worth asking about deep clips


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
    if 'marker' in ln:                          # a break screen's lines, left out (run.py kind)
        return ln['marker']
    return f"[{ln['s']:.2f}-{ln['e']:.2f}] {ln['text']}"


def clip_target(project, first, last, wish, max_clips):
    """How many clips to make: {'lo', 'hi', 'at_least', 'at_most', 'usable_min'}. Every decent moment
    between lo and hi, best first. By default lo = 3 and hi = 8 (v1.1's range) or, for long videos,
    about one per 7 minutes of real video, whichever is more (at most max_clips). The user's own
    numbers always win: "at least 10" raises lo (and hi, if needed), "at most 5" lowers hi."""
    usable_min = kind.usable_seconds(project, first, last) / 60
    hi = max(min(V11_MAX, int(max_clips)), min(int(max_clips), round(usable_min / MINUTES_PER_CLIP)))
    lo = MIN_CLIPS
    want_lo, want_hi = wish.get('at_least'), wish.get('at_most')
    if want_lo:
        lo, hi = want_lo, max(hi, want_lo)
    if want_hi:
        hi, lo = want_hi, min(lo, want_hi)
    return {'lo': lo, 'hi': hi, 'aim': hi, 'at_least': want_lo, 'at_most': want_hi,
            'usable_min': round(usable_min, 1)}


def update_wish(project, a):
    """The user's own numbers (and deep-clip answer) from the flags, merged into project.json's "wish"."""
    wish = dict(project.get('wish') or {})
    if a.any_count:
        wish.pop('at_least', None)
        wish.pop('at_most', None)
    if a.clips:
        wish['at_least'] = wish['at_most'] = a.clips
    if a.at_least is not None:
        wish['at_least'] = a.at_least or None
    if a.at_most is not None:
        wish['at_most'] = a.at_most or None
    if a.deep:
        wish['deep'] = a.deep == 'yes'
    if a.mode:
        wish['mode'] = a.mode
    if wish.get('at_least') and wish.get('at_most') and wish['at_least'] > wish['at_most']:
        die(f"at least {wish['at_least']} and at most {wish['at_most']} can't both hold")
    return {k: v for k, v in wish.items() if v is not None}


def deep_line(project, wish, minutes):
    """What to do about deep clips, for the summary."""
    if wish.get('mode') == 'quick' and not wish.get('deep'):
        return 'no (quick mode; deep clips need the standard read)'
    if 'deep' in wish:
        return 'yes (the user said so)' if wish['deep'] else 'no (the user said so)'
    mode = str(settings().get('deep_clips', 'ask')).lower()
    if mode == 'always':
        return 'yes (settings.json "deep_clips": "always")'
    if mode == 'never':
        return 'no (settings.json "deep_clips": "never")'
    if minutes > DEEP_ASK_MIN:
        return (f'not decided: the video is longer than {DEEP_ASK_MIN:.0f} minutes, so ask the user once, unless '
                f'their message already said; record the answer with  --deep yes|no')
    return f'no (a short video; only when the user asks)'


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


def build(pdir, project, lines, n, margin, shift, chapters, out_dir='parts', cues=None, per_part=5):
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
        if kind.is_irregular(project):
            head.append(f'# VIDEO KIND: {kind.describe(project)}. Rules: {kind.RULES}.')
        if any('marker' in ln for ln in before + own + after):
            head.append('# BREAK SCREENS ("Starting soon", "Be right back", stream ending) are marked with ===== lines: '
                        'their words are left out. Never take a topic, best moment or clip from them.')
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
                f'# 3. Up to {per_part} clip candidates whose middle is in your stretch. Quote first and last words exactly.',
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
    ap.add_argument('--at-least', type=int, default=None, help='the user wants at least N clips (0 forgets it)')
    ap.add_argument('--at-most', type=int, default=None, help='the user wants at most N clips (0 forgets it)')
    ap.add_argument('--clips', type=int, default=None, help='the user wants exactly N clips')
    ap.add_argument('--any-count', action='store_true', help='forget a number asked for earlier')
    ap.add_argument('--deep', choices=['yes', 'no'], default=None, help="the user's answer about deep clips")
    ap.add_argument('--mode', choices=['standard', 'quick'], default=None,
                    help='standard (default) or quick (only when the user asks: one read by Claude, no critic)')
    a = ap.parse_args()

    pdir = project_dir(a.project)
    project = load_json(pdir / 'project.json', {}) or {}
    lines = load_json(pdir / 'transcript' / 'sentences.json')
    if not lines:
        die(f'no transcript in {pdir}: run `python run.py fetch` first')
    if a.margin < 45:
        die('--margin must be at least 45 s, so a 90 s clip always fits inside one part')

    wish = update_wish(project, a)
    if wish != (project.get('wish') or {}):
        project['wish'] = wish
        save_json(pdir / 'project.json', project)
    breaks = kind.active_breaks(project)
    target = clip_target(project, lines[0]['s'], lines[-1]['e'], wish, settings().get('max_clips', 20))
    lines = kind.hide_breaks(lines, breaks)
    cues = sound.load(pdir)
    if cues and breaks:                         # break music isn't a lively spot
        cues = dict(cues, lively=[sp for sp in cues.get('lively') or []
                                  if not kind.in_break(sp['start'], sp['end'], breaks)])
    whole = '\n'.join(line_text(ln) for ln in lines)
    whole_tokens = est_tokens(whole) + 400
    span_min = (lines[-1]['e'] - lines[0]['s']) / 60
    n = 1 if whole_tokens <= TOKEN_CAP and not a.shift else max(1, math.ceil(span_min / a.minutes))
    while True:
        per_part = max(5, min(10, math.ceil(IDEAS_PER_CLIP * target['hi'] / n)))
        parts = build(pdir, project, lines, n, a.margin, a.shift, not a.no_chapters, a.dir, cues, per_part)
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
                                  'whole_tokens': whole_tokens, 'clips': dict(target, per_part=per_part),
                                  'parts': parts})

    print(f'-> {pdir.name}: {fmt_ts(lines[-1]["e"])} of speech, about {whole_tokens:,} tokens in all')
    print(f'   {len(parts)} part(s) in {pdir / a.dir}')
    print('   part  stretch               lines  tokens  size')
    for p in parts:
        s, e = p['stretch']
        print(f"   {p['part']:>4}  {fmt_ts(s):>9}-{fmt_ts(e):<9}  {p['lines']:>5}  {p['tokens']:>6,}  {p['bytes'] / 1024:.0f} KB")
    print(f'\n-> video: {kind.describe(project)}')
    if breaks:
        gone = sum(b['end'] - b['start'] for b in breaks)
        print(f'-> break screens left out: {len(breaks)} ({gone / 60:.1f} min); {target["usable_min"]:.0f} min of real video')
    asked = [f"at least {target['at_least']}" if target['at_least'] else '',
             f"at most {target['at_most']}" if target['at_most'] else '']
    asked = ' and '.join(x for x in asked if x)
    if asked and target['at_least'] == target['at_most']:
        asked = f"exactly {target['at_least']}"
    span = str(target['lo']) if target['lo'] == target['hi'] else f"{target['lo']} to {target['hi']}"
    how = (f"the user asked for {asked}" if asked else
           f"by default: up to {V11_MAX} as in v1.1, or about one per {MINUTES_PER_CLIP:.0f} min of real video "
           f"for long videos, at most {settings().get('max_clips', 20)} (settings.json max_clips)")
    print(f"-> clips: {span} ({how}). Deep clips count too.")
    print(f"   every decent moment, best first: at least {target['lo']}, and more up to {target['hi']} "
          'when the video has them. Never pad with weak ones' if target['lo'] != target['hi'] else
          f"   exactly {target['lo']}, best first")
    quick = wish.get('mode') == 'quick' and not wish.get('deep')
    print('-> mode: ' + ('quick (the user asked): read it yourself and pick straight into clips.json; no helpers, '
                         'no critic, no repair round' if quick else
                         'standard' + (' + deep clips' if wish.get('deep') else '') + ' (quick only when the user asks)'))
    print(f'-> deep clips: {deep_line(project, wish, (lines[-1]["e"] - lines[0]["s"]) / 60)}')
    if quick:
        if len(parts) == 1:
            print('\nnext (quick): read transcript.txt in full and write the FINAL clips.json (every clip with its '
                  'caption and post texts), then romanize / cut --check / cut / edit as usual')
        else:
            print(f'\nnext (quick): read the {len(parts)} part files yourself, one at a time and in order '
                  f'({a.dir}/part-01.txt ...; only YOUR STRETCH of each is new), note the best moments as you go, '
                  'then write the FINAL clips.json (no part-NN.json, no topics), then romanize / cut --check / cut / edit')
    elif len(parts) == 1:
        spots = (cues or {}).get('lively') or []
        if spots:
            print('\nlively spots from the sound (laughs, both talking at once; the detector can be wrong). '
                  'Look at the words there, and judge them only by the words:')
            for sp in spots:
                print(f"   {fmt_ts(sp['start']).split('.')[0]:>8}  {sp['why']}")
        elif cues is None:
            print(f'\n(no sound cues yet: python run.py sound {pdir.name})')
        print(f"\nnext: one part. Read transcript.txt in full and write a SHORTLIST of up to {max(16, 2 * target['lo'])} "
              f'clip ideas (about twice the clips you will make) to clips.json, then  python run.py critic {pdir.name}')
    else:
        print(f'\nnext: one reader per part, all at once (brief: {BRIEF}); each writes '
              f'{a.dir}/part-NN.json. Then:  python run.py topics {pdir.name}')


if __name__ == '__main__':
    main()
