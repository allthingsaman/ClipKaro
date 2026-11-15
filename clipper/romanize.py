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

# The Hinglish speech model (v2.3) writes Hindi in English letters in a textbook spelling ("nahin",
# "achchha", "kyonki", "vahaan"). These are its most common words (counted on 11,800 words of its output,
# Nov 2026) in the way creators type them (docs/hinglish.md). Words that are also English ("the" for थे,
# "lie" for लिए, "main", "is", "do", "us", "niche") are left out. romanize.json wins over this table, and Claude
# adds the rarer ones (run.py romanize lists them).
ROMAN_RESPELL = {
    'nahin': 'nahi', 'nahi': 'nahi', 'vah': 'wo', 'vo': 'wo', 'yah': 'ye', 'ham': 'hum', 'kuchh': 'kuch',
    'achchha': 'accha', 'achchhi': 'acchi', 'achchhe': 'acche', 'mainne': 'maine', 'kyonki': 'kyunki',
    'kyon': 'kyun', 'pahle': 'pehle', 'pahla': 'pehla', 'pahli': 'pehli', 'zyaada': 'zyada',
    'vahaan': 'wahan', 'yahaan': 'yahan', 'jahaan': 'jahan', 'kahaan': 'kahan', 'hamen': 'humein',
    'hamaare': 'hamare', 'hamaara': 'hamara', 'hamaari': 'hamari', 'hamne': 'humne', 'hamko': 'humko',
    'tumhaara': 'tumhara', 'tumhaare': 'tumhare', 'tumhaari': 'tumhari', 'shaayad': 'shayad', 'thik': 'theek',
    'chiz': 'cheez', 'chizen': 'cheezein', 'chizon': 'cheezon', 'kaaphi': 'kaafi', 'chaahie': 'chahiye',
    'jaega': 'jayega', 'jaegi': 'jayegi', 'jaenge': 'jayenge', 'vagairah': 'wagairah', 'ismen': 'ismein',
    'usmen': 'usmein', 'jismen': 'jismein', 'inmen': 'inmein', 'unmen': 'unmein', 'vaala': 'wala',
    'vaali': 'wali', 'vaale': 'wale', 'vaise': 'waise', 'vaisa': 'waisa', 'vahi': 'wahi', 'vajah': 'wajah',
    'vaapas': 'wapas', 'baahar': 'bahar', 'daadi': 'dadi', 'unhonne': 'unhone', 'inhonne': 'inhone',
    'oopar': 'upar', 'dikhaaya': 'dikhaya', 'bataaya': 'bataya', 'gaanv': 'gaon', 'islie': 'isliye',
    'isilie': 'isliye', 'khaana': 'khana', 'khaane': 'khane', 'bachche': 'bacche', 'bachchon': 'bacchon',
    'dekhana': 'dekhna', 'aavaaz': 'awaaz', 'sirph': 'sirf', 'taraph': 'taraf', 'jivan': 'jeevan',
    'shuroo': 'shuru', 'chaahoonga': 'chahunga', 'chaahta': 'chahta', 'chaahti': 'chahti',
    'chaahte': 'chahte', 'pichhe': 'peeche', 'mahsoos': 'mehsoos', 'bachapan': 'bachpan',
    'dauraan': 'dauran', 'dhyaan': 'dhyan', 'baaten': 'baatein', 'pitaaji': 'pitaji', 'ajib': 'ajeeb',
    'kahaani': 'kahani', 'mitha': 'meetha', 'nae': 'naye', 'niklata': 'nikalta', 'khatm': 'khatam',
    'unhen': 'unhe', 'inhen': 'inhe', 'sochate': 'sochte', 'rakhata': 'rakhta', 'karib': 'kareeb',
    'donon': 'dono', 'dhire': 'dheere', 'karoonga': 'karunga', 'dekhie': 'dekhiye', 'karie': 'kariye',
    'lijie': 'lijiye', 'dijie': 'dijiye', 'boliye': 'boliye', 'gae': 'gaye', 'gai': 'gayi', 'aae': 'aaye',
    'aai': 'aayi', 'rupe': 'rupaye', 'jaata': 'jata', 'jaati': 'jati', 'jaate': 'jate', 'jaana': 'jana',
    'aata': 'aata', 'raavan': 'Ravan', 'raam': 'Ram', 'bhaarat': 'Bharat', 'hanumaan': 'Hanuman',
    'zindagi': 'zindagi', 'ekdam': 'ekdum', 'vagaira': 'wagaira', 'hamesha': 'hamesha', 'baare': 'baare',
    'saare': 'saare', 'saari': 'saari', 'poora': 'poora', 'poori': 'poori', 'kahte': 'kehte', 'kah': 'keh',
    'kahna': 'kehna', 'kaha': 'kaha', 'samajh': 'samajh', 'aaainge': 'aayenge', 'aaenge': 'aayenge',
    'sakoonga': 'sakunga', 'hoonga': 'hunga', 'loonga': 'lunga', 'doonga': 'dunga', 'boloon': 'bolun',
}


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
    """{key: spelling}: Devanagari words as written, English-letter words in lower case (the built-in
    respellings of the Hinglish model first, romanize.json over them)."""
    m = load_json(pdir / 'romanize.json', {}) or {}
    if not isinstance(m, dict):
        die('romanize.json must be one JSON object: {"देवनागरी": "roman", ...}')
    from .fetch import writes_roman
    # the built-in respellings only for a video the Hinglish model wrote down: in a large-v3-turbo
    # transcript, words in English letters are English words
    roman = writes_roman((load_json(pdir / 'project.json', {}) or {}).get('asr_model'))
    table = {k: v for k, v in ROMAN_RESPELL.items() if v != k} if roman else {}
    for k, v in m.items():
        if isinstance(v, str) and v.strip() and not k.startswith('_'):
            table[key_of(k)] = v.strip()
    return table


def key_of(core):
    """Lookup key of a word: Devanagari as written (no nukta), English letters in lower case."""
    return variant(core) if has_devanagari(core) else variant(core).lower()


def respelled(core, table):
    """The house spelling of an English-letter word, or None. Keeps a capital first letter (a name, or
    a sentence start that the captions show in capitals anyway)."""
    v = table.get(key_of(core))
    if not v or v == core:
        return None
    return v[:1].upper() + v[1:] if core[:1].isupper() and v[:1].islower() else v


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
            # an English word (or the Hinglish model's spelling of a Hindi word: respelled), or a number
            # with a Hindi full stop ("series।"): the danda becomes a "." (left as is, that one character
            # would switch the whole clip to the Devanagari font)
            core = respelled(core, table) or core
            fixed = ''.join(_PUNCT.get(c, c) for c in pre) + core + ''.join(_PUNCT.get(c, c) for c in post)
            out.append({**w, 'w': fixed, 'orig': w['w']} if fixed != w['w'] else dict(w))
    return out, missing


def wants_roman(project, cfg=None):
    cfg = cfg or settings()
    return (project or {}).get('language') in ROMAN_FOR and cfg.get('hinglish_captions', 'roman') == 'roman'


def for_captions(pdir, project, meta, cfg=None):
    """The clip's words as the captions should show them (Roman when the settings ask for it)."""
    if not wants_roman(project, cfg):
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
    ap.add_argument('--checked', action='store_true',
                    help='the English-letter words it listed are checked (respellings added to romanize.json)')
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
    known = {variant(k) for k in raw if not k.startswith('_')}
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

    # a project written down by the Hinglish model: its rarer English-letter words get a look too
    from .fetch import writes_roman
    if writes_roman(project.get('asr_model')):
        checked = set(raw.get('_checked') or [])
        latin = {}
        for cw in per_clip.values():
            for w in cw:
                core = split_word(w['w'])[1]
                k = key_of(core)
                if core and not has_devanagari(core) and k not in table and k not in checked \
                        and not any(ch.isdigit() for ch in core):
                    latin[k] = latin.get(k, 0) + 1
        if latin and not a.checked:
            words_list = sorted(latin, key=lambda k: -latin[k])
            print(f'{len(words_list)} word(s) in English letters to check (the Hinglish model spells Hindi like '
                  f'"nahin", "achchha"). Add the ones ClipKaro spells differently to romanize.json, e.g. '
                  f'"vahaan": "wahan"; English words and words already right need nothing:\n')
            print('  ' + ' '.join(words_list) + '\n')
            print(f'Then run:  python run.py romanize {pdir.name} --checked')
            return
        if latin and a.checked:
            raw['_checked'] = sorted(checked | set(latin))
            save_json(pdir / 'romanize.json', raw)
            table = load_table(pdir)

    odd = [f'{k} -> {v}' for k, v in raw.items() if isinstance(v, str) and has_devanagari(v)]
    print('All Hindi words in the picked clips have a Roman spelling. Captions will read:\n')
    for cid, cw in per_clip.items():
        rw, _ = apply(cw, table)
        print(f"  [{cid}] {' '.join(w['w'] for w in rw)}\n")
    if odd:
        print('   ! these values still contain Devanagari: ' + ', '.join(odd[:10]))
    print(f'next: python run.py cut {pdir.name}   (then edit; captions use the Roman spelling automatically)')


if __name__ == '__main__':
    main()
