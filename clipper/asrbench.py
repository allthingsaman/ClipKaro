"""A small speech-to-text test on your own videos, to decide whether a new model is worth switching to.

    python run.py asr-bench make             cut ~3-minute snippets from a few of your projects into
                                             output/_asrbench/ and write a draft reference text for each
    (correct output/_asrbench/refs/*.txt by ear once: they are the "right answers")
    python run.py asr-bench run [model]      transcribe every snippet with a model (default: the current one)
                                             and score it against the references
    python run.py asr-bench report           all models tried so far, best first

Hindi, Hinglish and English only. A model is a faster-whisper (CTranslate2) model name, e.g.
large-v3-turbo (ClipKaro's default), large-v3, medium, or a Hugging Face repo id of a CTranslate2
conversion. A model not downloaded yet is downloaded on its first run (large ones are 1.5-3 GB).

The score: words are compared by how they sound, not how they are spelled, so "क्या", "kya" and "kyaa"
count as the same word and a model that writes Roman Hinglish is not punished for it (Devanagari is
turned into simple Roman first). Lower is better: the share of words wrong (sound-alike word error rate).
Snippets and references stay in output/ (never committed).
"""
import argparse
import json
import re
import time
from pathlib import Path

from .common import OUTPUT, load_json, save_json

BENCH = OUTPUT / '_asrbench'
SR = 16000

# ---------- sounds-alike comparison ----------

CONS = {'क': 'k', 'ख': 'kh', 'ग': 'g', 'घ': 'gh', 'ङ': 'n', 'च': 'ch', 'छ': 'chh', 'ज': 'j', 'झ': 'jh', 'ञ': 'n',
        'ट': 't', 'ठ': 'th', 'ड': 'd', 'ढ': 'dh', 'ण': 'n', 'त': 't', 'थ': 'th', 'द': 'd', 'ध': 'dh', 'न': 'n',
        'प': 'p', 'फ': 'ph', 'ब': 'b', 'भ': 'bh', 'म': 'm', 'य': 'y', 'र': 'r', 'ल': 'l', 'व': 'v', 'श': 'sh',
        'ष': 'sh', 'स': 's', 'ह': 'h', 'क़': 'q', 'ख़': 'kh', 'ग़': 'g', 'ज़': 'z', 'फ़': 'f', 'ड़': 'r', 'ढ़': 'rh',
        'य़': 'y', 'ळ': 'l'}
VOW = {'अ': 'a', 'आ': 'aa', 'इ': 'i', 'ई': 'ee', 'उ': 'u', 'ऊ': 'oo', 'ए': 'e', 'ऐ': 'ai', 'ओ': 'o', 'औ': 'au',
       'ऋ': 'ri', 'ऑ': 'o', 'ऍ': 'e'}
MATRA = {'ा': 'aa', 'ि': 'i', 'ी': 'ee', 'ु': 'u', 'ू': 'oo', 'े': 'e', 'ै': 'ai', 'ो': 'o', 'ौ': 'au', 'ृ': 'ri',
         'ॉ': 'o', 'ॅ': 'e'}
NUKTA = '़'


def roman(word):
    """Devanagari -> plain Roman (k, kh, aa ...), the inherent 'a' dropped at the end of a word."""
    word = word.replace('क' + NUKTA, 'क़').replace('ज' + NUKTA, 'ज़').replace('फ' + NUKTA, 'फ़') \
        .replace('ड' + NUKTA, 'ड़').replace('ढ' + NUKTA, 'ढ़').replace(NUKTA, '')
    out, i = [], 0
    while i < len(word):
        ch = word[i]
        nxt = word[i + 1] if i + 1 < len(word) else ''
        if ch in CONS:
            out.append(CONS[ch])
            if nxt in MATRA:
                out.append(MATRA[nxt])
                i += 1
            elif nxt == '्':
                i += 1
            elif nxt and (nxt in CONS or nxt in 'ंँ'):
                out.append('a')
            else:
                out.append('a#')                       # an inherent 'a' at the end: dropped below
        elif ch in VOW:
            out.append(VOW[ch])
        elif ch in 'ंँ':
            out.append('n')
        elif ch == 'ः':
            out.append('h')
        elif ch in MATRA:
            out.append(MATRA[ch])
        else:
            out.append(ch)
        i += 1
    s = ''.join(out)
    return re.sub(r'a#$', '', s).replace('a#', 'a')


SAME = {'yah': 'ye', 'yeh': 'ye', 'vah': 'vo', 'voh': 'vo', 'woh': 'vo', 'wo': 'vo', 'nahin': 'nahi',
        'nahee': 'nahi', 'naheen': 'nahi', 'naheem': 'nahi'}   # everyday words with several spellings


def sound_key(word):
    """A spelling-free key, so one spoken word matches however it is written: "kyaa", "kya" and "क्या";
    "uska" and "उसका" (Hindi drops the inner a); "mein" and "में"; "ye" and "यह"."""
    w = roman(word.lower()) if re.search('[ऀ-ॿ]', word) else word.lower()
    w = re.sub(r'[^a-z]', '', w)
    w = SAME.get(w, w)
    for a, b in (('aa', 'a'), ('ee', 'i'), ('ii', 'i'), ('oo', 'u'), ('ai', 'e'), ('ei', 'e'), ('ae', 'e'),
                 ('au', 'o'), ('ou', 'o'), ('w', 'v'), ('z', 'j'), ('q', 'k'), ('ph', 'f'), ('ck', 'k'), ('c', 'k')):
        w = w.replace(a, b)
    w = w[:1] + w[1:].replace('h', '')                 # kh/bh/th -> k/b/t (aspiration is spelt either way)
    w = w[:1] + w[1:].replace('a', '')                 # the short a inside a word comes and goes in spelling
    if len(w) > 2 and w[-1] in 'nm' and w[-2] in 'eiou':
        w = w[:-1]                                     # a nasal ending: "mein" / "में", "nahin" / "nahi"
    w = re.sub(r'(.)\1+', r'\1', w)                    # doubled letters
    return SAME.get(w, w)


def wer(ref, hyp):
    """Word error rate between two key lists (edit distance / reference words)."""
    r, h = ref, hyp
    prev = list(range(len(h) + 1))
    for i in range(1, len(r) + 1):
        cur = [i] + [0] * len(h)
        for j in range(1, len(h) + 1):
            cur[j] = min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (r[i - 1] != h[j - 1]))
        prev = cur
    return prev[-1] / max(1, len(r))


def keys(text):
    return [k for k in (sound_key(t) for t in text.split()) if k]


# ---------- make the test set ----------

DEFAULT = [  # (project folder ending, start s, end s, language) : what your videos sound like
    ('NVzWAMY7zLg', 30, 210, 'hinglish'),           # anime narration
    ('82Sh5YB6dp4', 60, 240, 'hinglish'),           # talking to the camera (review)
    ('PX-QnMGMUAc', 900, 1080, 'hinglish'),         # gameplay with a game cutscene in English
    ('TjPPIf-M6KE', 600, 720, 'en'),                # an English podcast
]


def make(a):
    import soundfile as sf
    (BENCH / 'snippets').mkdir(parents=True, exist_ok=True)
    (BENCH / 'refs').mkdir(exist_ok=True)
    made = []
    for tail, s, e, lang in DEFAULT:
        hits = [d for d in OUTPUT.iterdir() if d.is_dir() and d.name.endswith(tail) and (d / 'source' / 'audio16k.wav').exists()]
        if not hits:
            print(f'   - skipped {tail}: no such project with audio here')
            continue
        pdir = hits[0]
        audio, _ = sf.read(str(pdir / 'source' / 'audio16k.wav'), dtype='float32')
        name = f'{len(made) + 1:02d}-{pdir.name[:30]}'
        sf.write(str(BENCH / 'snippets' / f'{name}.wav'), audio[s * SR:e * SR], SR)
        words = load_json(pdir / 'transcript' / 'words.json') or []
        roman_map = load_json(pdir / 'romanize.json', {}) or {}
        text = ' '.join(roman_map.get(w['w'].strip(), w['w'].strip()) for w in words
                        if s <= w['s'] < e and not w.get('unsure'))
        ref = BENCH / 'refs' / f'{name}.txt'
        if not ref.exists():                            # never overwrite a corrected reference
            ref.write_text('# Correct this by ear: write exactly what is said (Roman Hinglish is fine, any spelling).\n'
                           '# Leave out game music and noise; a game character speaking counts. Lines starting with # are ignored.\n'
                           + re.sub(r'(.{1,90})(\s|$)', r'\1\n', text), encoding='utf-8')
        made.append({'name': name, 'project': pdir.name, 'start': s, 'end': e, 'language': lang})
    save_json(BENCH / 'set.json', made)
    print(f'{len(made)} snippet(s), {sum(m["end"] - m["start"] for m in made) / 60:.0f} min, in {BENCH}')
    print(f'next: correct the draft texts in {BENCH / "refs"} by ear (they come from the current transcript),'
          ' then: python run.py asr-bench run')


# ---------- run a model ----------

def run_model(a):
    import soundfile as sf
    from . import gpu
    from .fetch import _transcribe_once
    sets = load_json(BENCH / 'set.json')
    if not sets:
        raise SystemExit('no test set yet: python run.py asr-bench make')
    model = a.model or 'large-v3-turbo'
    device = gpu.pick_device('auto')
    compute = 'float16' if device == 'cuda' else 'int8'
    res = load_json(BENCH / 'results.json', {}) or {}
    t0 = time.time()
    for m in sets:
        audio, _ = sf.read(str(BENCH / 'snippets' / f"{m['name']}.wav"), dtype='float32')
        words = _transcribe_once(audio, model, m['language'], device, compute, None)
        hyp = ' '.join(w['w'] for w in words if not w.get('unsure'))
        (BENCH / 'out').mkdir(exist_ok=True)
        (BENCH / 'out' / f"{m['name']}.{model.replace('/', '_')}.txt").write_text(hyp, encoding='utf-8')
    total, rows = score(model, sets)
    res[model] = {'wer': round(total, 3), 'device': device, 'seconds': round(time.time() - t0),
                  'when': time.strftime('%Y-%m-%d')}
    save_json(BENCH / 'results.json', res)
    for r in rows:
        print(f"   {r['name']:<42} {r['wer']:6.1%} of {r['ref_words']} words wrong")
    print(f'{model}: {total:.1%} of words wrong overall ({res[model]["seconds"]} s on {device})')


def score(model, sets):
    """-> (overall share of words wrong, per-snippet rows), from the model's saved output and the references
    as they are now."""
    rows = []
    for m in sets:
        out = BENCH / 'out' / f"{m['name']}.{model.replace('/', '_')}.txt"
        if not out.exists():
            continue
        ref = '\n'.join(l for l in (BENCH / 'refs' / f"{m['name']}.txt").read_text(encoding='utf-8').splitlines()
                        if not l.startswith('#'))
        rows.append({'name': m['name'], 'wer': round(wer(keys(ref), keys(out.read_text(encoding='utf-8'))), 3),
                     'ref_words': len(keys(ref))})
    total = sum(r['wer'] * r['ref_words'] for r in rows) / max(1, sum(r['ref_words'] for r in rows))
    return total, rows


def report(a):
    """Every model run so far, scored against the references as they are now: correct a reference and the
    scores follow, without running the models again."""
    res = load_json(BENCH / 'results.json', {}) or {}
    sets = load_json(BENCH / 'set.json') or []
    if not res:
        raise SystemExit('nothing run yet: python run.py asr-bench run')
    for name, total, rows in sorted(((n, *score(n, sets)) for n in res), key=lambda x: x[1]):
        r = res[name]
        print(f"{name:<40} {total:6.1%} words wrong   ({r['seconds']} s on {r['device']}, {r['when']})")
        for row in rows:
            print(f"     {row['name']:<40} {row['wer']:6.1%} of {row['ref_words']} words")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest='cmd', required=True)
    sub.add_parser('make')
    r = sub.add_parser('run')
    r.add_argument('model', nargs='?')
    sub.add_parser('report')
    a = ap.parse_args()
    {'make': make, 'run': run_model, 'report': report}[a.cmd](a)


if __name__ == '__main__':
    main()

