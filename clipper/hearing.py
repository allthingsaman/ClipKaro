"""Careful listening for noisy streams (v2.7): three voices and game sound garble the transcript.

On a 4-hour GTA stream with three friends on voice chat, the first transcript was so garbled that Claude
did by hand what this module now does by itself, for Hindi / Hinglish gameplay and live streams on an
NVIDIA graphics card (settings.json "careful_listening": false turns it off):

1. `run.py hear <project>` (fetch starts it by itself): a second speech model hears the whole video
   (SECOND: Hindi in Devanagari, English in Roman, much clearer on mixed voices). `parts` gives each
   reading helper its stretch of it next to the part file: to understand garbled lines, never to quote.
2. `run.py rehear <project>`: after the clips are picked, two more models hear every clip again (SECOND
   and THIRD, Roman Hinglish), and word-check packets are written (wordcheck/batch-NN.txt).
3. One `clipkaro-wordcheck` helper per packet compares the three hearings: fixes where they agree, doubts
   where they don't, players' English lines the game-voice rule hid, game lines it let through.
4. `run.py wordcheck <project>` applies them: the fixes (never one that adds or drops a "nahin": that word
   is hidden instead), no captions on the doubts (settings.json "unsure_words": "ask" writes them to
   word-check.json for the owner instead), and show_captions / hide_captions in clips.json.

Tested on that stream: 583 caption words fixed, 176 doubtful spots hidden, about 25 minutes of graphics
card for the second hearing and ~8 minutes per 100 clips for the re-hearing (RTX 3050, 4 GB).
Models: Trelis Research's Hinglish Whisper and Oriserve's Hindi2Hinglish-Swift (Apache-2.0).
"""
import gc
import json
import os
import re
import shutil
import time
import wave

import numpy as np

from .common import fmt_ts, load_json, norm_token, save_json, settings

SECOND = 'nikh360pro/capsbro-hinglish-ct2'                 # Hindi in Devanagari, English in Roman
THIRD = 'MSpider3/whisper-hindi2hinglish-swift-ct2'         # Roman Hinglish
SHORT = {SECOND: 'capsbro', THIRD: 'swift'}
BATCH = 2                  # batch size on the graphics card (8 ran out of memory on a 4 GB card)
CHUNK_S = 600.0            # the second hearing reads the audio in 10-minute chunks (memory)
PER_PACKET = 20            # clips per word-check packet
HEAR_V = 3                 # how clips are heard; a clip heard an older way is heard again
LEAD_S = 5.0               # a clip is heard from this long before it: with less, the batch mode missed its first line
FIX_WINDOW = (-4.0, 12.0)  # a fix's words are looked for this far around its time
WINDOW_S = 28.0            # without its speech detector the batch mode hears at most 30 s at once: a longer piece
                           # is heard in windows of at most this long, split at its quietest moment (v2.7.1 review)
# every spelling of a "no": a fix that changes how many of them a line has would flip its meaning (never applied);
# a fix that only respells one (nahi -> nahin, नहीं -> nahin) keeps the meaning and is applied
NEGATIONS = {'nahin', 'nahi', 'nahee', 'naheen', 'nahim', 'nhin', 'nhi', 'nai', 'na', 'mat', 'not', 'no', 'never',
             'dont', 'didnt', 'doesnt', 'cant', 'cannot', 'wont', 'isnt', 'wasnt', 'arent', 'werent', 'havent', 'hasnt',
             'hadnt', 'shouldnt', 'couldnt', 'wouldnt', 'aint', 'nothing', 'nobody', 'nope', 'nah', 'नहीं', 'नही',
             'नहि', 'नहिं', 'न', 'ना', 'मत'}


def wanted(project, cfg=None, device=None):
    """(True, why) when careful listening is for this video, else (False, why). `device`: the one fetch was told
    to use ("cpu": the extra models stay off the graphics card too)."""
    from . import gpu
    from .fetch import is_hindi
    from .kind import is_irregular
    cfg = settings() if cfg is None else cfg
    if cfg.get('careful_listening', True) is False:
        return False, 'off in settings.json ("careful_listening": false)'
    if os.environ.get('CLIPKARO_LIVE'):
        return False, 'not while live clipping runs (the graphics card belongs to OBS, and clips go out fast)'
    if str(device or cfg.get('device') or 'auto').lower() == 'cpu':
        return False, 'the processor was chosen for this video ("device": "cpu")'
    if not is_hindi((project or {}).get('language') or ''):
        return False, 'only for Hindi / Hinglish videos'
    if not is_irregular(project):
        return False, 'only for gameplay and live streams (several voices and game sound)'
    if gpu.cuda_device_count() < 1:
        return False, 'needs an NVIDIA graphics card (on the processor it would take hours)'
    return True, 'Hindi / Hinglish gameplay or stream, NVIDIA graphics card'


def _pipeline(name):
    from . import gpu
    gpu.enable_nvidia_libs()
    from faster_whisper import BatchedInferencePipeline, WhisperModel
    from .models import model_path
    m = WhisperModel(model_path(name, progress=True), device='cuda', compute_type='int8_float16')
    return m, BatchedInferencePipeline(m)


def _wav(pdir):
    f = pdir / 'source' / 'audio16k.wav'
    if not f.exists():
        from .cut import audio16k, ensure_video
        audio16k(pdir, ensure_video(pdir, load_json(pdir / 'project.json', {}) or {}))
    return f


def _windows(audio, sr=16000, most=WINDOW_S, least=18.0):
    """None when the batch mode can hear the audio whole (up to most + 1 s: the way clips were always heard);
    else [{'start', 'end'}] in seconds, each at most `most` long, split at the quietest tenth of a second
    between `least` and `most` into the window (a pause between words, so no word is cut in two)."""
    total = len(audio) / sr
    if total <= most + 1.0:
        return None
    end = int(total * 1000) / 1000           # rounded down: a window past the audio's last sample is refused
    out, a, step = [], 0.0, int(0.1 * sr)
    while total - a > most:
        lo, hi = int((a + least) * sr), int((a + most) * sr)
        n = (hi - lo) // step
        rms = np.sqrt((audio[lo:lo + n * step].reshape(n, step) ** 2).mean(axis=1))
        cut = (lo + (int(np.argmin(rms)) + 0.5) * step) / sr
        out.append({'start': round(a, 3), 'end': round(cut, 3)})
        a = cut
    if end - a < 1.0:                         # a sliver at the end joins the window before it (still under 30 s)
        out[-1]['end'] = end
    else:
        out.append({'start': round(a, 3), 'end': end})
    return out


def _read(w, s, e):
    sr = w.getframerate()
    w.setpos(max(0, int(s * sr)))
    n = max(0, int((e - max(0.0, s)) * sr))
    return np.frombuffer(w.readframes(n), dtype=np.int16).astype(np.float32) / 32768.0


# ---------------------------------------------------------------- 1. the second hearing of the whole video

def hear_full(pdir, quiet=False):
    """The second hearing of the whole video: second-hearing/full.json {'model', 'segments': [{s, e, t}]}."""
    out = pdir / 'second-hearing' / 'full.json'
    out.parent.mkdir(exist_ok=True)
    done = load_json(out) or {}
    if done.get('model') == SECOND and done.get('complete'):
        return out
    m, bp = _pipeline(SECOND)
    segs, t0 = [], time.time()
    with wave.open(str(_wav(pdir))) as w:
        total = w.getnframes() / w.getframerate()
        a = 0.0
        while a < total:
            b = min(total, a + CHUNK_S)
            audio = _read(w, a, b)
            res, _ = bp.transcribe(audio, language='en', batch_size=BATCH, beam_size=5, vad_filter=True)
            segs += [{'s': round(a + s.start, 2), 'e': round(a + s.end, 2), 't': s.text.strip()} for s in res
                     if s.text.strip()]
            save_json(out, {'model': SECOND, 'segments': segs, 'complete': False})
            if not quiet:
                print(f'   second hearing: {fmt_ts(b).split(".")[0]} of {fmt_ts(total).split(".")[0]} '
                      f'({time.time() - t0:.0f} s)', flush=True)
            a = b
    save_json(out, {'model': SECOND, 'segments': segs, 'complete': True})
    del bp, m
    gc.collect()
    return out


def part_text(pdir, k, total, stretch, context):
    """The second hearing of one part, as the reading helper gets it next to the part file, or None."""
    full = load_json(pdir / 'second-hearing' / 'full.json') or {}
    if not full.get('segments'):
        return None
    a, b = stretch
    lo, hi = context
    rows = [f"[{s['s']:.1f}-{s['e']:.1f}] {s['t']}" for s in full['segments'] if s['e'] > lo and s['s'] < hi]
    head = [f'# SECOND HEARING of part {k} of {total} (another speech model on the same audio): Hindi in Devanagari, '
            f'English in Roman.',
            '# Times are rough (a few seconds). It is usually clearer than the part file where voices and game sound '
            'mix, but it also mishears, and it SKIPS some speech: where it is silent or thin, rely on the part file.',
            '# Use it to UNDERSTAND what was said (jokes, names, punchlines, who is talking to whom).',
            '# Never quote it: every time and quote in your answer is copied from the part file exactly.',
            f'# YOUR STRETCH: {fmt_ts(a).split(".")[0]}-{fmt_ts(b).split(".")[0]} ({a:.2f}-{b:.2f} s). Lines outside '
            f'it are context only.', '']
    return '\n'.join(head + rows) + '\n'


# ---------------------------------------------------------------- 2. every picked clip heard again

def hear_clips(pdir, ids=None, quiet=False):
    """Two more hearings of every picked clip: second-hearing/clips/<model>.json {clip id: [{range, words}]}."""
    clips = (load_json(pdir / 'clips.json', {}) or {}).get('clips', [])
    todo = [c for k, c in enumerate(clips, 1) if not ids or int(c.get('id', k)) in ids]
    folder = pdir / 'second-hearing' / 'clips'
    folder.mkdir(parents=True, exist_ok=True)
    with wave.open(str(_wav(pdir))) as w:
        for name in (SECOND, THIRD):
            out = folder / f'{SHORT[name]}.json'
            heard = load_json(out) or {}
            need = [c for c in todo if [p['range'] for p in heard.get(str(c['id']), [])] != c['ranges']
                    or any(p.get('v') != HEAR_V for p in heard.get(str(c['id']), []))]
            if not need:
                continue
            m, bp = _pipeline(name)
            t0 = time.time()
            for n, c in enumerate(need, 1):
                pieces = []
                for s, e in c['ranges']:
                    a0 = max(0.0, s - LEAD_S)
                    # no speech detector on a clip: with it, the Roman model looped ("bhai, bhai, bhai ...") and
                    # missed words on a GTA stream; without it, it heard more, just as fast
                    audio = _read(w, a0, e + 0.6)
                    res, _ = bp.transcribe(audio, language='en', batch_size=BATCH, beam_size=5, word_timestamps=True,
                                           vad_filter=False, clip_timestamps=_windows(audio))
                    ws = no_loops([[x.word.strip(), round(a0 + x.start, 2), round(a0 + x.end, 2)]
                                   for sg in res for x in (sg.words or []) if x.word.strip()])
                    pieces.append({'range': [s, e], 'words': ws, 'v': HEAR_V})
                heard[str(c['id'])] = pieces
                save_json(out, heard)
                if not quiet and (n % 10 == 0 or n == len(need)):
                    print(f'   {SHORT[name]}: {n} of {len(need)} clip(s) heard again ({time.time() - t0:.0f} s)',
                          flush=True)
            del bp, m                                 # free the card before the next model loads
            gc.collect()
    return folder


def no_loops(ws, keep=3, phrase_loop=4):
    """Heard words without a model's loop: the same word more than `keep` times in a row is cut to `keep`, and
    a stretch of 2-10 words said `phrase_loop` times or more in a row is kept once (the Roman model repeated
    "Raahul gaandhi kaary maal kar rahe the" ten times over 17 s of other talk on a GTA stream; a chant said
    two or three times stays)."""
    out, run = [], 0
    for w in ws:
        run = run + 1 if out and norm_token(out[-1][0]) == norm_token(w[0]) else 1
        if run <= keep:
            out.append(w)
    toks = [norm_token(w[0]) for w in out]
    res, i = [], 0
    while i < len(out):
        for n in range(2, 11):
            reps = 1
            while toks[i + reps * n:i + (reps + 1) * n] == toks[i:i + n] and i + (reps + 1) * n <= len(out):
                reps += 1
            if reps >= phrase_loop:
                res += out[i:i + n]
                i += n * reps
                break
        else:
            res.append(out[i])
            i += 1
    return res


def _rows(ws, every=12):
    """Heard words as short lines: '[start] words ...'."""
    out, cur = [], []
    for w in ws:
        cur.append(w)
        if len(cur) >= every or w[0].endswith(('.', '?', '!', '।')):
            out.append(f'[{cur[0][1]:.2f}] ' + ' '.join(x[0] for x in cur))
            cur = []
    if cur:
        out.append(f'[{cur[0][1]:.2f}] ' + ' '.join(x[0] for x in cur))
    return out


def packets(pdir, per=PER_PACKET, ids=None):
    """wordcheck/batch-NN.txt: for each clip its captions now and the two other hearings. Returns the files."""
    project = load_json(pdir / 'project.json', {}) or {}
    clips = [c for k, c in enumerate((load_json(pdir / 'clips.json', {}) or {}).get('clips', []), 1)
             if not ids or int(c.get('id', k)) in ids]
    words = load_json(pdir / 'transcript' / 'words.json') or []
    lines = load_json(pdir / 'transcript' / 'sentences.json') or []
    heard = {k: load_json(pdir / 'second-hearing' / 'clips' / f'{k}.json') or {} for k in SHORT.values()}
    game = set()
    if not settings().get('game_voice_captions', False):
        from . import voices
        game = voices.game_words(pdir, project, words, lines)
    crit = {c['id']: c for c in (load_json(pdir / 'critic' / 'critic.json', {}) or {}).get('clips', [])}
    folder = pdir / 'wordcheck'
    folder.mkdir(exist_ok=True)
    for old in list(folder.glob('batch-*.txt')) + list(folder.glob('batch-*.json')):
        old.unlink()                                  # a new round: old packets and answers go
    files, total = [], -(-len(clips) // per)
    for b in range(total):
        group = clips[b * per:(b + 1) * per]
        out = [f'# ClipKaro word check, packet {b + 1} of {total}: "{project.get("title") or pdir.name}" '
               f'({project.get("channel") or "-"}). Instructions: .claude/agents/clipkaro-wordcheck.md. '
               f'Write wordcheck/batch-{b + 1:02d}.json.', '']
        for c in group:
            dur = sum(e - s for s, e in c['ranges'])
            out += ['=' * 100, f'## CLIP {c["id"]}  "{c.get("title", "")}"  {dur:.0f} s',
                    'ranges: ' + ' + '.join(f'{fmt_ts(s).split(".")[0]}-{fmt_ts(e).split(".")[0]} [{s}, {e}]'
                                            for s, e in c['ranges'])]
            for note in (crit.get(c.get('from')) or {}).get('notes', []):
                if isinstance(note, str):
                    out.append('critic note: ' + note)
            for i, (s, e) in enumerate(c['ranges']):
                out += [f'--- piece {i + 1}: {s} to {e}', 'CAPTIONS NOW (lines marked GAME get no caption: the '
                        'game-voice rule took them for a game character):']
                for ln in lines:
                    if 'i0' not in ln or not (ln['e'] > s + 0.05 and ln['s'] < e - 0.05):
                        continue
                    idx = range(ln['i0'], ln['i1'] + 1)
                    shown = [words[k]['w'] for k in idx if not words[k].get('unsure')]
                    if not shown:
                        continue
                    tag = 'GAME ' if all(k in game for k in idx if not words[k].get('unsure')) else ''
                    out.append(f"  {tag}[{ln['s']:.2f}-{ln['e']:.2f}] {' '.join(shown)}")
                for label, key in (('HEARING B (Hindi in Devanagari, English in Roman)', 'capsbro'),
                                   ('HEARING C (Roman Hinglish)', 'swift')):
                    pcs = heard[key].get(str(c['id']), [])
                    ws = pcs[i]['words'] if i < len(pcs) else []
                    ws = [w for w in ws if w[2] > s - 0.3 and w[1] < e + 0.3]
                    out += [label + ':'] + (['  ' + r for r in _rows(ws)] or ['  (nothing heard)'])
            out.append('')
        f = folder / f'batch-{b + 1:02d}.txt'
        f.write_text('\n'.join(out) + '\n', encoding='utf-8')
        files.append(f)
    return files


# ---------------------------------------------------------------- 3. the helpers' answers applied

def _is_negation(token):
    t = norm_token(token.replace('’', "'")).replace("'", '')
    return t in NEGATIONS or re.sub(r'(.)\1+$', r'\1', t) in NEGATIONS        # "nahiii", "naaa"


def _negations(text):
    """How many "no"s the words hold, in any spelling ("don't", "nahin-aaunga", "नहीं")."""
    return sum(_is_negation(t) for t in re.split(r'[\s\-]+', text or '') if t)


def _locate(words, at, phrase):
    """(index, count) of the phrase's words nearest `at`, exact or (when a fix rewrote a word since) the
    best same-length stretch with at least half of them the same; None when not found."""
    from .fixword import find_all
    hits, k = find_all(words, phrase)
    hits = [i for i in hits if FIX_WINDOW[0] <= words[i]['s'] - at <= FIX_WINDOW[1]]
    if hits:
        return min(hits, key=lambda i: abs(words[i]['s'] - at)), k
    want = [norm_token(t) for t in phrase.split() if norm_token(t)]
    if not want:
        return None
    best = None
    for i in range(len(words) - len(want) + 1):
        if not FIX_WINDOW[0] <= words[i]['s'] - at <= FIX_WINDOW[1]:
            continue
        got = sum(norm_token(words[i + j]['w']) == t for j, t in enumerate(want)) / len(want)
        if best is None or got > best[0] or (got == best[0] and abs(words[i]['s'] - at) < abs(words[best[1]]['s'] - at)):
            best = (got, i)
    return (best[1], len(want)) if best and best[0] >= 0.5 else None


def apply(pdir, dry=False):
    """Apply the word-check answers. Returns a summary dict; writes wordcheck/applied.txt."""
    from .fetch import write_transcript
    from .fixword import replace_at
    tdir = pdir / 'transcript'
    words = load_json(tdir / 'words.json') or []
    lines = load_json(tdir / 'sentences.json') or []
    doc = load_json(pdir / 'clips.json', {}) or {}
    by_id = {int(c['id']): c for c in doc.get('clips', []) if 'id' in c}
    answers = []
    for f in sorted((pdir / 'wordcheck').glob('batch-*.json')):
        for x in load_json(f) or []:
            answers.append(x)
    ask = str(settings().get('unsure_words', 'hide')).lower() == 'ask'
    log, done, asked = [], [], []
    n = {'fixed': 0, 'hidden': 0, 'not_found': 0, 'shown_lines': 0, 'hidden_lines': 0, 'meaning': 0}

    def hide(at, heard, why):
        if ask:
            asked.append({'time': fmt_ts(at), 'at': at, 'heard': heard, 'why': why, 'correct': ''})
            return
        hit = _locate(words, at, heard)
        if not hit:
            log.append(f'NOTFOUND {at:9.2f} doubt "{heard}"')
            n['not_found'] += 1
            return
        i, k = hit
        for w in words[i:i + k]:
            w['unsure'] = True
        n['hidden'] += 1
        log.append(f'hidden   {at:9.2f} {why}: ' + ' '.join(w['w'] for w in words[i:i + k]))

    def when(f):
        try:
            return float(f['at'])
        except (KeyError, TypeError, ValueError):
            return None
    fixes = sorted(((when(f), f['wrong'], f['right'], x.get('id')) for x in answers for f in x.get('fixes') or []
                    if f.get('wrong') and f.get('right') and when(f) is not None), key=lambda t: t[0])
    flips = []
    for at, wrong, right, cid in fixes:
        if norm_token(wrong) == norm_token(right) or not right.split():
            continue
        if _negations(wrong) != _negations(right):          # a meaning flip is never written: hidden instead,
            n['meaning'] += 1                               # after every other fix (one can't show it again)
            flips.append((at, wrong, f'clip {cid}: would flip the meaning ("{wrong}" -> "{right}")'))
            continue
        hit = _locate(words, at, wrong)
        if not hit or [norm_token(w['w']) for w in words[hit[0]:hit[0] + hit[1]]] != \
                [norm_token(t) for t in wrong.split() if norm_token(t)]:
            from .fixword import find_all
            already, _ = find_all(words, right)
            if any(FIX_WINDOW[0] <= words[i]['s'] - at <= FIX_WINDOW[1] for i in already):
                log.append(f'same     {at:9.2f} clip {cid}: "{wrong}" -> "{right}" (already says it)')
            else:
                log.append(f'NOTFOUND {at:9.2f} clip {cid}: "{wrong}" -> "{right}"')
                n['not_found'] += 1
            continue
        i, k = hit
        s0, e0 = words[i]['s'], words[i + k - 1]['e']
        if any(s0 < b - 0.01 and a < e0 - 0.01 for a, b in done):
            log.append(f'overlap  {at:9.2f} clip {cid}: "{wrong}" -> "{right}" (another fix rewrote these words)')
            continue
        words, k2 = replace_at(words, i, k, right)
        done.append((words[i]['s'], words[i + k2 - 1]['e']))
        n['fixed'] += 1
        log.append(f'fixed    {at:9.2f} clip {cid}: "{wrong}" -> "{right}"')

    for at, wrong, why in flips:
        hide(at, wrong, why)
    for x in answers:
        for d in x.get('doubts') or []:
            if d.get('heard') and when(d) is not None:
                hide(float(d['at']), d['heard'], f"clip {x.get('id')}: {d.get('context') or 'unsure'}")

    def line_at(t):
        """The line said at t: one that holds t first, else the nearest start (never the line before by mistake)."""
        near = [ln for ln in lines if 's' in ln and ln['s'] - 0.3 <= t <= ln['e'] + 0.3]
        return min(near, key=lambda ln: (not ln['s'] <= t <= ln['e'], abs(ln['s'] - t))) if near else None

    for x in answers:
        clip = by_id.get(int(x['id'])) if str(x.get('id', '')).isdigit() else None
        if not clip:
            continue
        for key, field, counter in (('friend_english', 'show_captions', 'shown_lines'),
                                    ('game_english', 'hide_captions', 'hidden_lines')):
            for t in x.get(key) or []:
                ln = line_at(float(t))
                if not ln:
                    continue
                span = [round(ln['s'] - 0.05, 2), round(ln['e'] + 0.05, 2)]
                if span not in clip.setdefault(field, []):
                    clip[field].append(span)
                    n[counter] += 1
        if x.get('problem'):
            log.append(f'problem  clip {x["id"]}: {x["problem"]}')
    (pdir / 'wordcheck').mkdir(exist_ok=True)
    (pdir / 'wordcheck' / 'applied.txt').write_text('\n'.join(log) + '\n', encoding='utf-8')
    if dry:
        return n
    if asked:
        save_json(pdir / 'word-check.json', {'how_to_use': 'Listen at each time; if "heard" is wrong, write what was '
                                             'really said in "correct", then tell Claude "word check done".',
                                             'doubts': asked})
    if not (tdir / 'words-before-wordcheck.json').exists():
        shutil.copy2(tdir / 'words.json', tdir / 'words-before-wordcheck.json')
    if not (tdir / 'words-before-fixes.json').exists():   # the words as first heard: what deep, topics and the
        shutil.copy2(tdir / 'words.json', tdir / 'words-before-fixes.json')  # caption check match quotes against
    write_transcript(pdir, words, load_json(pdir / 'project.json', {}) or {})
    save_json(pdir / 'clips.json', doc)
    n['asked'] = len(asked)
    return n
