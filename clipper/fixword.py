"""Fix a misheard caption word (or phrase) everywhere in one go.

    python run.py fixword <project> "farts" "fads"                 # every place it was heard
    python run.py fixword <project> "cycle path" "psychopath"      # a phrase, even into fewer words
    python run.py fixword <project> "bow" "boat" --at 2107.5       # only the one nearest that second
    python run.py fixword <project> "farts" "fads" --dry           # show what would change

It changes transcript/words.json (each word keeps its time; a phrase that becomes more or fewer words
shares the same stretch of time), and rebuilds sentences.json and transcript.txt from it, so captions,
the transcript and `find` all agree. The first fix copies words.json to words-before-fixes.json (the
words as first heard, which the deep pass and the topic map match against). Words are compared
without case and punctuation; the punctuation after the old words is kept ("fads?").

Then it names the clips that contain a changed word: cut and edit those again to see it in the
captions. A Hindi word in Devanagari needs its Roman spelling: run `romanize` again.
"""
import argparse
import shutil

from .common import (_CLOSERS, SENT_END, die, fmt_ts, has_devanagari, load_json, norm_token, project_dir,
                     save_json)

TRAIL = SENT_END + ',;:' + _CLOSERS


def _tail(word):
    """The punctuation at the end of a word: 'faced?' -> '?'."""
    w = word.rstrip()
    k = len(w)
    while k and w[k - 1] in TRAIL:
        k -= 1
    return w[k:]


def find_all(words, phrase):
    """Start indexes where the phrase's words follow each other (case and punctuation ignored)."""
    want = [norm_token(t) for t in phrase.split()]
    want = [t for t in want if t]
    if not want:
        return [], 0
    hits = [i for i in range(len(words) - len(want) + 1)
            if all(norm_token(words[i + k]['w']) == t for k, t in enumerate(want))]
    return hits, len(want)


def replace_at(words, i, n, new_text):
    """The n words from i replaced by new_text's words: one for one keeps each time; otherwise the
    new words share the old stretch by their length. The old last word's punctuation stays."""
    old = words[i:i + n]
    new = new_text.split()
    tail = _tail(old[-1]['w'])
    if tail and not new[-1].endswith(tail):
        new[-1] += tail
    keep = {k: v for k, v in old[0].items() if k == 'lang'} if all('lang' in w for w in old) else {}
    p = min(w.get('p', 1.0) for w in old)
    if len(new) == len(old):
        out = [{**{k: v for k, v in w.items() if k != 'unsure'}, 'w': t} for w, t in zip(old, new)]
    else:
        a, b = old[0]['s'], old[-1]['e']
        weights = [max(1, len(t)) for t in new]
        total, at, out = sum(weights), a, []
        for t, wt in zip(new, weights):
            e = at + (b - a) * wt / total
            out.append({'w': t, 's': round(at, 3), 'e': round(e, 3), 'p': p, **keep})
            at = e
    return words[:i] + out + words[i + n:], len(out)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('project')
    ap.add_argument('wrong', help='the word or phrase as it is in the transcript now')
    ap.add_argument('right', help='what it should say')
    ap.add_argument('--at', type=float, default=None, help='only the place nearest this second of the video')
    ap.add_argument('--dry', action='store_true', help='only show what would change')
    a = ap.parse_args()
    if not a.right.split():
        die('the new text is empty (to hide words from the captions, mark them "unsure" instead)')

    pdir = project_dir(a.project)
    tdir = pdir / 'transcript'
    words = load_json(tdir / 'words.json')
    if not words:
        die(f'no transcript in {pdir}: run `python run.py fetch` first')
    hits, n = find_all(words, a.wrong)
    if not hits:
        die(f'"{a.wrong}" is not in the transcript (words are compared without case and punctuation; '
            f'`python run.py find {pdir.name} "{a.wrong}"` searches more loosely)')
    if a.at is not None:
        hits = [min(hits, key=lambda i: abs(words[i]['s'] - a.at))]
    spans = [(words[i]['s'], words[i + n - 1]['e']) for i in hits]
    clips = (load_json(pdir / 'clips.json', {}) or {}).get('clips', [])
    touched = sorted({int(c.get('id', k + 1)) for k, c in enumerate(clips)
                      for r0, r1 in c['ranges'] for s, e in spans if s < r1 and r0 < e})
    for i, (s, e) in zip(hits, spans):
        before = ' '.join(w['w'] for w in words[max(0, i - 4):i + n + 4])
        print(f'   {fmt_ts(s)}  {before}')
    verb = 'would change' if a.dry else 'changed'
    print(f'-> "{a.wrong}" -> "{a.right}": {len(hits)} place(s) {verb}'
          + (f'; in clip(s) {", ".join(map(str, touched))}' if touched else '; in no picked clip'))
    if a.dry:
        return

    if not (tdir / 'words-before-fixes.json').exists():
        shutil.copy2(tdir / 'words.json', tdir / 'words-before-fixes.json')
    for i in sorted(hits, reverse=True):                 # from the end, so earlier indexes stay right
        words, _ = replace_at(words, i, n, a.right)
    from .fetch import write_transcript
    write_transcript(pdir, words, load_json(pdir / 'project.json', {}) or {})
    print('   words.json, sentences.json and transcript.txt updated (as first heard: words-before-fixes.json)')
    if has_devanagari(a.right):
        print(f'   a Hindi word: run  python run.py romanize {pdir.name}  for its Roman spelling')
    if touched:
        ids = ','.join(map(str, touched))
        print(f'next: python run.py cut {pdir.name} --clips {ids}   then   python run.py edit {pdir.name} --clips {ids}')


if __name__ == '__main__':
    main()
