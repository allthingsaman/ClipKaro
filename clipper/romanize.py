"""Roman Hinglish captions: give the Hindi (Devanagari) words of the picked clips a Roman spelling.

    python run.py romanize <project>              # check / prepare romanize.json for the picked clips
    python run.py romanize <project> --clips 2    # only some clips

Whisper writes Hindi in Devanagari ("आज हम business की बात करेंगे।"). This step lists every Hindi
word inside the clips of clips.json and adds it to output/<project>/romanize.json with an empty
value. Claude fills in the values (style guide: docs/hinglish.md):

    {"आज": "aaj", "हम": "hum", "की": "ki", "बात": "baat", "करेंगे": "karenge"}

Run it again: when every word has a spelling it prints each clip's caption text in Roman script.
`edit` applies the map to the captions (and the .srt) and keeps every word's timing. Words without a
spelling stay in Devanagari, drawn with a Hindi-capable font. Set "hinglish_captions": "devanagari"
in settings.json to skip this step altogether.
"""
import argparse
import unicodedata

from .common import die, has_devanagari, load_json, project_dir, save_json, settings

ROMAN_FOR = ('hinglish', 'hi', 'ur')
_PUNCT = {'।': '.', '॥': '.'}


def split_word(w):
    """'"करेंगे।' -> ('"', 'करेंगे', '।'): leading punctuation, the word, trailing punctuation."""
    t = unicodedata.normalize('NFC', w)
    i, j = 0, len(t)
    while i < j and unicodedata.category(t[i])[0] not in 'LMN':
        i += 1
    while j > i and unicodedata.category(t[j - 1])[0] not in 'LMN':
        j -= 1
    return t[:i], t[i:j], t[j:]


def variant(core):
    """Lookup key: NFC and without nukta, so ज़रूर / जरूर share one entry."""
    return unicodedata.normalize('NFC', core).replace('़', '')


def load_table(pdir):
    m = load_json(pdir / 'romanize.json', {}) or {}
    if not isinstance(m, dict):
        die('romanize.json must be one JSON object: {"देवनागरी": "roman", ...}')
    return {variant(k): str(v).strip() for k, v in m.items() if str(v or '').strip()}


def apply(words, table):
    """Words with their Hindi text replaced by the Roman spelling (original kept as 'orig').
    Returns (words, list of words that have no spelling yet)."""
    out, missing = [], []
    for w in words:
        pre, core, post = split_word(w['w'])
        roman = table.get(variant(core)) if has_devanagari(core) else None
        if roman:
            out.append({**w, 'w': pre + roman + ''.join(_PUNCT.get(c, c) for c in post), 'orig': w['w']})
        elif has_devanagari(core):
            missing.append(core)
            out.append(dict(w))
        else:
            # an English word or a number with a Hindi full stop ("series।"): the danda becomes a "."
            # (left as is, that one character would switch the whole clip to the Devanagari font)
            fixed = ''.join(_PUNCT.get(c, c) for c in pre) + core + ''.join(_PUNCT.get(c, c) for c in post)
            out.append({**w, 'w': fixed, 'orig': w['w']} if fixed != w['w'] else dict(w))
    return out, missing


def wants_roman(project, cfg=None):
    cfg = cfg or settings()
    return (project or {}).get('language') in ROMAN_FOR and cfg.get('hinglish_captions', 'roman') == 'roman'


def for_captions(pdir, project, meta, cfg=None):
    """The clip's words as the captions should show them (Roman when the settings ask for it)."""
    if not wants_roman(project, cfg) or not any(has_devanagari(w['w']) for w in meta['words']):
        return meta
    words, missing = apply(meta['words'], load_table(pdir))
    if missing:
        uniq = list(dict.fromkeys(missing))
        print(f'   ! {len(uniq)} Hindi word(s) have no Roman spelling yet, so they stay in Devanagari: '
              f'{" ".join(uniq[:12])}{" ..." if len(uniq) > 12 else ""}\n'
              f'     fix: python run.py romanize {pdir.name}  (then fill romanize.json and edit again)')
    return {**meta, 'words': words}


def clip_words(clip, words):
    """Transcript words inside a clip's ranges, snapped exactly like `cut` does."""
    from .cut import snap_range
    out = []
    for s, e in clip['ranges']:
        snapped = snap_range(s, e, words)
        if snapped:
            out += words[snapped[2]:snapped[3] + 1]
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('project')
    ap.add_argument('--clips', default=None, help='comma list of clip ids, e.g. 1,3')
    a = ap.parse_args()

    pdir = project_dir(a.project)
    project = load_json(pdir / 'project.json', {})
    picks = load_json(pdir / 'clips.json')
    if not picks or not picks.get('clips'):
        die(f'no clips.json in {pdir} yet. Pick the clips first.')
    words = load_json(pdir / 'transcript' / 'words.json')
    if not wants_roman(project):
        print(f"nothing to do: language is {project.get('language')!r} and settings.json hinglish_captions is "
              f"{settings().get('hinglish_captions')!r} (Roman captions are made for hinglish / hi projects).")
        return
    want = {int(x) for x in a.clips.split(',')} if a.clips else None

    raw = load_json(pdir / 'romanize.json', {}) or {}
    table = load_table(pdir)
    known = {variant(k) for k in raw}
    per_clip, todo, seen = {}, [], set()
    for i, clip in enumerate(picks['clips'], 1):
        cid = int(clip.get('id', i))
        if want and cid not in want:
            continue
        cw = clip_words(clip, words)
        per_clip[cid] = cw
        for w in cw:
            core = split_word(w['w'])[1]
            if has_devanagari(core) and variant(core) not in table and variant(core) not in seen:
                todo.append(core)
                seen.add(variant(core))

    if todo:
        for core in todo:                 # add the new words with empty values, in reading order
            if variant(core) not in known:
                raw[core] = ''
                known.add(variant(core))
        save_json(pdir / 'romanize.json', raw)
        print(f'{len(todo)} Hindi word(s) in the picked clips need a Roman spelling. They are listed in')
        print(f'  {pdir / "romanize.json"}  with empty values: fill every value, keep the keys as they are.\n')
        print('Clip text, for context:')
        for cid, cw in per_clip.items():
            print(f"  [{cid}] {' '.join(w['w'] for w in cw)}")
        print('\nStyle: write each word the way Hinglish creators type it ("hai", "nahi", "kyunki", "mein"), and '
              'English words in normal English spelling (वीडियो -> video). See docs/hinglish.md.')
        print(f'Then run:  python run.py romanize {pdir.name}')
        return

    odd = [f'{k} -> {v}' for k, v in raw.items() if has_devanagari(str(v))]
    print('All Hindi words in the picked clips have a Roman spelling. Captions will read:\n')
    for cid, cw in per_clip.items():
        rw, _ = apply(cw, table)
        print(f"  [{cid}] {' '.join(w['w'] for w in rw)}\n")
    if odd:
        print('   ! these values still contain Devanagari: ' + ', '.join(odd[:10]))
    print(f'next: python run.py cut {pdir.name}   (then edit; captions use the Roman spelling automatically)')


if __name__ == '__main__':
    main()
