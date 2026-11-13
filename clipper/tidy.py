"""Cleaner captions: nothing during laughter, no made-up loops.

    python run.py tidy <project>          # for a video transcribed before (fetch does it by itself)
    python run.py tidy <project> --dry    # only show what would change

Whisper makes up words where nobody speaks clearly: during laughter, game sounds and music. This
step marks those words "unsure", so they get no captions (no captions beat wrong ones). The words
stay in the transcript with their times, so cutting is not affected. It marks:

  * words during a laugh (found by the sound pass) that Whisper was unsure of (under 0.6), and
    laugh sounds written out as words ("ha ha", "हा हा"); clear words said while laughing stay;
  * "झाल", a word nobody says: Whisper writes it for noise, music and game sounds in Hindi videos
    (119 times in 13 test videos, next to "ओक ओक ओक" and "खाल खाल");
  * loops: a phrase of 1-4 words said 3 or more times in a row when it is a known made-up loop
    ("कर दो कर दो कर दो", up to 8 times in a gameplay video) or Whisper was unsure of it (mean under
    0.6); and of a phrase said 8 or more times in a row ("ये रास्ता" x21), everything after the
    first 3. Real repetition stays: "let's go, let's go, let's go" (x6, mean 0.76) keeps its captions.

words.json is backed up once to words-before-tidy.json. Then cut and edit the clips it names again.
"""
import argparse
import re
import shutil

from .common import die, fmt_ts, load_json, norm_token, project_dir

LAUGH_P = 0.6            # during a laugh, words under this confidence get no captions
LOOP_P = 0.6             # a loop Whisper was this unsure of is made up
LONG_LOOP = 8            # a phrase said this often in a row is a loop past its first KEEP_OF_LONG
KEEP_OF_LONG = 3
JUNK = {'झाल'}                                   # never a real word in these videos
JUNK_LOOPS = {('कर', 'दो'), ('झाला', 'है'), ('झाल',)}
LAUGH_WORD = re.compile(r'^(ha|haha+|ah?ha+|he+he+|hi+hi+|हा+|हाहा+|हे+हे+|ही+ही+|lol)$')


def _loops(words):
    """[(start, n, repeats)]: a phrase of n words said `repeats` times in a row (3 or more)."""
    toks = [norm_token(w['w']) for w in words]
    out, i = [], 0
    while i < len(toks):
        best = None
        for n in (1, 2, 3, 4):
            g = toks[i:i + n]
            if len(g) < n or not all(g):
                continue
            k = 1
            while toks[i + k * n:i + (k + 1) * n] == g:
                k += 1
            if k >= (4 if n == 1 else 3) and (best is None or k * n > best[1] * best[2]):
                best = (i, n, k)
        if best:
            out.append(best)
            i += best[1] * best[2]
        else:
            i += 1
    return out


def tidy_words(words, cues=None):
    """(words with "unsure" marks added, {reason: count}). Never removes or moves a word."""
    out = [dict(w) for w in words]
    why = {}

    def mark(i, reason):
        if not out[i].get('unsure'):
            out[i]['unsure'] = True
            why[reason] = why.get(reason, 0) + 1

    toks = [norm_token(w['w']) for w in out]
    for i, t in enumerate(toks):
        if t in JUNK:
            mark(i, 'noise word')
    laughs = [(s, e) for s, e, *_ in (cues or {}).get('laughter', [])]
    for i, w in enumerate(out):
        mid = (w['s'] + w['e']) / 2
        in_laugh = any(s <= mid <= e for s, e in laughs)
        laughy = bool(LAUGH_WORD.match(toks[i])) and (
            in_laugh or (i > 0 and LAUGH_WORD.match(toks[i - 1])) or
            (i + 1 < len(toks) and LAUGH_WORD.match(toks[i + 1])))
        if laughy or (in_laugh and w.get('p', 1.0) < LAUGH_P):
            mark(i, 'laughter')
    for i, n, k in _loops(out):
        seg = out[i:i + n * k]
        phrase = tuple(toks[i:i + n])
        mean = sum(w.get('p', 1.0) for w in seg) / len(seg)
        if phrase in JUNK_LOOPS or mean < LOOP_P:
            for j in range(i, i + n * k):
                mark(j, 'loop')
        elif k >= LONG_LOOP:
            for j in range(i + n * KEEP_OF_LONG, i + n * k):
                mark(j, 'loop')
    return out, why


def report(why):
    if not why:
        return 'nothing to tidy'
    return ', '.join(f'{v} word(s) {k}' for k, v in why.items()) + ': no captions there'


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('project')
    ap.add_argument('--dry', action='store_true', help='only show what would change')
    a = ap.parse_args()
    pdir = project_dir(a.project)
    tdir = pdir / 'transcript'
    words = load_json(tdir / 'words.json')
    if not words:
        die(f'no transcript in {pdir}: run `python run.py fetch` first')
    from . import sound
    new, why = tidy_words(words, sound.load(pdir))
    print(f'-> {report(why)}')
    changed = [w for w, o in zip(new, words) if w.get('unsure') != o.get('unsure')]
    clips = (load_json(pdir / 'clips.json', {}) or {}).get('clips', [])
    hit = sorted({int(c.get('id', k + 1)) for k, c in enumerate(clips) for r0, r1 in c['ranges']
                  for w in changed if r0 <= w['s'] < r1})
    for w in changed[:12]:
        print(f"   {fmt_ts(w['s'])}  {w['w']}")
    if a.dry or not changed:
        if hit:
            print(f'   in clip(s) {", ".join(map(str, hit))}')
        return
    if not (tdir / 'words-before-tidy.json').exists():
        shutil.copy2(tdir / 'words.json', tdir / 'words-before-tidy.json')
    from .fetch import write_transcript
    write_transcript(pdir, new, load_json(pdir / 'project.json', {}) or {})
    print('   words.json, sentences.json and transcript.txt updated (backup: words-before-tidy.json)')
    if hit:
        ids = ','.join(map(str, hit))
        print(f'next: python run.py cut {pdir.name} --clips {ids}   then   python run.py edit {pdir.name} --clips {ids}')


if __name__ == '__main__':
    main()
