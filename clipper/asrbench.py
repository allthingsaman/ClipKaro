"""A small speech-to-text test on your own videos, to decide whether a new model is worth switching to.

    python run.py asr-bench make             cut ~3-minute snippets from a few of your projects into
                                             output/_asrbench/ and write a draft reference text for each
    (correct output/_asrbench/refs/*.txt by ear once: they are the "right answers")
    python run.py asr-bench run [model]      transcribe every snippet with a model (default: the current one)
                                             and score it against the references
    python run.py asr-bench public           also download two public test sets with checked texts (about
                                             1 hour of audio, ~150 MB): CoSHE-500 (Hinglish conversation)
                                             and MonsoonASR (everyday spoken Hindi, every right spelling listed)
    python run.py asr-bench report           all models tried so far, best first, per test set

A model can also be one folder of a repo: "owner/repo:int8".

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


def lattice_wer(ref, hyp):
    """Word error rate against a reference that lists every right spelling of each word (a set of keys
    per spoken word): a word is right when its key is any of them."""
    r, h = ref, hyp
    prev = list(range(len(h) + 1))
    for i in range(1, len(r) + 1):
        cur = [i] + [0] * len(h)
        for j in range(1, len(h) + 1):
            cur[j] = min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (h[j - 1] not in r[i - 1]))
        prev = cur
    return prev[-1] / max(1, len(r))


def lattice_keys(lattice):
    """[[spelling, ...], ...] -> [set of keys, ...] (a word with no usable spelling is left out)."""
    out = []
    for alts in lattice:
        ks = {k for k in (sound_key(t) for alt in alts for t in alt.split()[:1]) if k}
        if ks:
            out.append(ks)
    return out


# ---------- public test sets (checked texts, downloaded once; never committed) ----------

PUBLIC = {  # name: (Hugging Face dataset, split, clips to take, what it is, licence)
    'coshe': ('Trelis/CoSHE-500', 'eval', 60, 'Hinglish conversation, ~30 s clips', 'CC BY-NC 4.0: for testing only'),
    'monsoon': ('VoiceArena/MonsoonASR-Open-ASR-leaderboard-hi-IN', 'test', 300,
                'everyday spoken Hindi, every right spelling listed', 'CC BY 4.0'),
}
ROWS_API = 'https://datasets-server.huggingface.co/rows'


def public(a):
    """Download a slice of each public test set: 16 kHz wav + the checked text (or spelling lattice)."""
    import subprocess
    import urllib.parse
    import urllib.request
    sets = [m for m in (load_json(BENCH / 'set.json') or []) if m.get('set', 'own') == 'own']
    for name, (ds, split, want, what, lic) in PUBLIC.items():
        d = BENCH / 'public' / name
        d.mkdir(parents=True, exist_ok=True)
        got, off = [], 0
        print(f'-> {name}: {what} ({lic})', flush=True)
        while len(got) < want:
            q = urllib.parse.urlencode({'dataset': ds, 'config': 'default', 'split': split, 'offset': off,
                                        'length': 100})
            rows = None
            for attempt in range(6):            # the dataset server sometimes answers 502 for a while
                try:
                    with urllib.request.urlopen(f'{ROWS_API}?{q}', timeout=60) as r:
                        rows = json.loads(r.read().decode('utf-8')).get('rows') or []
                    break
                except Exception as e:
                    print(f'   ! {type(e).__name__}: {e}; trying again in {10 * (attempt + 1)} s', flush=True)
                    time.sleep(10 * (attempt + 1))
            if rows is None:
                print(f'   ! gave up on {name} after {len(got)} clips', flush=True)
                break
            if not rows:
                break
            for row in rows:
                x, i = row['row'], row['row_idx']
                if name == 'monsoon' and (x.get('audio_length_s') or 0) < 2.0:
                    continue                      # one or two words: too short to say much
                wav, ref = d / f'{i:04d}.wav', d / f'{i:04d}.json'
                if not wav.exists():
                    src = x['audio'][0]['src']
                    r = subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', src, '-ac', '1', '-ar', str(SR), str(wav)],
                                       timeout=180)
                    if r.returncode or not wav.exists():
                        continue                  # this clip couldn't be fetched: skip it
                save_json(ref, {'text': x.get('transcription')} if name == 'coshe' else {'lattice': x['lattice']})
                got.append({'name': f'{name}-{i:04d}', 'set': name, 'language': 'hinglish',
                            'wav': str(wav.relative_to(BENCH)), 'ref': str(ref.relative_to(BENCH))})
                if len(got) >= want:
                    break
            off += 100
        sets += got
        print(f'   {len(got)} clips', flush=True)
    save_json(BENCH / 'set.json', sets)
    print('next: python run.py asr-bench run <model>')


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
        made.append({'name': name, 'set': 'own', 'project': pdir.name, 'start': s, 'end': e, 'language': lang})
    save_json(BENCH / 'set.json', made + [m for m in (load_json(BENCH / 'set.json') or []) if m.get('set', 'own') != 'own'])
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
    compute = a.compute or ('float16' if device == 'cuda' else 'int8')
    res = load_json(BENCH / 'results.json', {}) or {}
    t0 = time.time()
    (BENCH / 'out').mkdir(exist_ok=True)
    tag = model.replace('/', '_').replace(':', '_')
    own = [m for m in sets if m.get('set', 'own') == 'own']
    pub = [m for m in sets if m.get('set', 'own') != 'own']
    for m in own:                               # your own videos: the whole transcription, as fetch does it
        audio, _ = sf.read(str(BENCH / 'snippets' / f"{m['name']}.wav"), dtype='float32')
        try:
            words = _transcribe_once(audio, model, m['language'], device, compute, None)
        except RuntimeError as e:               # too big for the graphics card: 8-bit weights, as fetch does
            if 'out of memory' not in str(e).lower() or device != 'cuda':
                raise
            compute = 'int8_float16'
            print(f'   (out of graphics memory: {model} runs with 8-bit weights)', flush=True)
            words = _transcribe_once(audio, model, m['language'], device, compute, None)
        hyp = ' '.join(w['w'] for w in words if not w.get('unsure'))
        (BENCH / 'out' / f"{m['name']}.{tag}.txt").write_text(hyp, encoding='utf-8')
    if pub:                                     # short public clips: the same decode, the model loaded once
        from faster_whisper import WhisperModel
        from .fetch import HINGLISH, HINGLISH_PROMPT, is_hindi
        from .models import model_path
        if device == 'cuda':
            gpu.enable_nvidia_libs()
        import gc
        gc.collect()
        try:
            wm = WhisperModel(model_path(model), device=device, compute_type=compute)
        except Exception:                       # a large model on a small graphics card: 8-bit weights
            wm = WhisperModel(model_path(model), device=device, compute_type='int8_float16' if device == 'cuda' else 'int8')
        print(f'-> {len(pub)} public clips ...', flush=True)
        for k, m in enumerate(pub):
            out = BENCH / 'out' / f"{m['name']}.{tag}.txt"
            if out.exists() and not a.again:
                continue
            audio, _ = sf.read(str(BENCH / m['wav']), dtype='float32')
            lang = m['language']
            segs, _ = wm.transcribe(audio, language='hi' if is_hindi(lang) else lang, beam_size=5, vad_filter=True,
                                    condition_on_previous_text=False, temperature=0.0,
                                    hotwords=HINGLISH_PROMPT if lang == HINGLISH else None)
            out.write_text(' '.join(s.text.strip() for s in segs), encoding='utf-8')
            if k % 50 == 49:
                print(f'   {k + 1}/{len(pub)}', flush=True)
    by_set = {}
    for name in sorted({m.get('set', 'own') for m in sets}):
        total, rows = score(model, [m for m in sets if m.get('set', 'own') == name])
        by_set[name] = {'wer': round(total, 3), 'words': sum(r['ref_words'] for r in rows), 'clips': len(rows)}
        print(f"   {name:<8} {total:6.1%} of {by_set[name]['words']} words wrong ({len(rows)} clips)")
    res[model] = {'sets': by_set, 'device': device, 'seconds': round(time.time() - t0),
                  'when': time.strftime('%Y-%m-%d')}
    save_json(BENCH / 'results.json', res)
    print(f'{model}: {res[model]["seconds"]} s on {device}')


def score(model, sets):
    """-> (overall share of words wrong, per-snippet rows), from the model's saved output and the references
    as they are now."""
    rows = []
    for m in sets:
        out = BENCH / 'out' / f"{m['name']}.{model.replace('/', '_').replace(':', '_')}.txt"
        if not out.exists():
            out = BENCH / 'out' / f"{m['name']}.{model.replace('/', '_')}.txt"      # runs before "repo:folder"
        if not out.exists():
            continue
        hyp = keys(out.read_text(encoding='utf-8'))
        if m.get('set', 'own') == 'own':
            ref = keys('\n'.join(l for l in (BENCH / 'refs' / f"{m['name']}.txt").read_text(encoding='utf-8')
                                 .splitlines() if not l.startswith('#')))
            err = wer(ref, hyp)
        else:
            r = load_json(BENCH / m['ref'])
            ref = keys(r['text']) if 'text' in r else lattice_keys(r['lattice'])
            err = wer(ref, hyp) if 'text' in r else lattice_wer(ref, hyp)
        rows.append({'name': m['name'], 'wer': round(err, 3), 'ref_words': len(ref)})
    total = sum(r['wer'] * r['ref_words'] for r in rows) / max(1, sum(r['ref_words'] for r in rows))
    return total, rows


def report(a):
    """Every model run so far, scored against the references as they are now: correct a reference and the
    scores follow, without running the models again."""
    res = load_json(BENCH / 'results.json', {}) or {}
    sets = load_json(BENCH / 'set.json') or []
    if not res:
        raise SystemExit('nothing run yet: python run.py asr-bench run')
    names = sorted({m.get('set', 'own') for m in sets})
    print(f"{'model':<44}" + ''.join(f'{n:>10}' for n in names) + '   (share of words wrong; lower is better)')
    for model in sorted(res, key=lambda n: score(n, [m for m in sets if m.get('set', 'own') != 'own'])[0]):
        cells = []
        for n in names:
            total, rows = score(model, [m for m in sets if m.get('set', 'own') == n])
            cells.append(f'{total:9.1%}' if rows else f"{'-':>9}")
        r = res[model]
        print(f'{model:<44}' + ' '.join(cells) + f"   ({r['seconds']} s on {r['device']}, {r['when']})")
    if 'own' in names:
        print("own = your videos; their texts are drafts until corrected by ear (output/_asrbench/refs)")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest='cmd', required=True)
    sub.add_parser('make')
    r = sub.add_parser('run')
    r.add_argument('model', nargs='?')
    r.add_argument('--again', action='store_true', help='transcribe the public clips again')
    r.add_argument('--compute', default=None,
                   help='int8_float16 for a large model on a small graphics card (default: float16 on the GPU)')
    sub.add_parser('public')
    sub.add_parser('report')
    a = ap.parse_args()
    {'make': make, 'run': run_model, 'public': public, 'report': report}[a.cmd](a)


if __name__ == '__main__':
    main()

