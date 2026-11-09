"""Step 1: get the video's audio and transcribe it with word timestamps.

    python run.py fetch "https://www.youtube.com/watch?v=..."
    python run.py fetch "C:/videos/my-podcast.mp4"            # a video file on your computer
    options: --lang auto|hinglish|en|hi|...   --model auto|large-v3-turbo|large-v3|medium|small.en|...
             --device auto|cuda|cpu   --cookies-from-browser chrome   --retranscribe

Hindi / Hinglish is detected automatically (force it with --lang hinglish). Whisper then writes Hindi
in Devanagari and English words in Roman ("आज हम business की बात करेंगे।"); `run.py romanize`
turns the picked clips into Roman Hinglish captions later. Defaults come from settings.json.

Creates output/<slug>/ with project.json, source/audio.*, transcript/words.json and transcript.txt.
Only the audio is downloaded here; the video is downloaded by `cut`, once clips are picked.
"""
import argparse
import hashlib
import os
import re
import shutil
import sys
import time
from pathlib import Path

from . import gpu
from .models import is_network_error, model_path, network_help
from .common import (OUTPUT, die, ffmpeg, fmt_ts, has_devanagari, is_sentence_end, load_json, norm_token, probe,
                     save_json, settings, slugify)

YTDLP_BASE = ['--no-progress', '--no-playlist', '--retries', '5', '--sleep-requests', '1']

HINGLISH = 'hinglish'
HINDI_LIKE = ('hi', 'ur')      # Whisper often labels spoken Hindi as Urdu; both are decoded as Hindi
LANG_ALIASES = {'hinglish': HINGLISH, 'hi-en': HINGLISH, 'hindi-english': HINGLISH, 'hindi': 'hi', 'english': 'en'}
# Whisper copies the style of the text it is primed with: Hindi in Devanagari, English words in Roman,
# with punctuation. Given as "hotwords" it primes every 30 s window, not only the first one.
HINGLISH_PROMPT = 'मैंने ये video पिछले week record किया था, और इसमें काफी important points हैं।'
MAX_WORD_S = 1.2       # no spoken word lasts longer; a longer one means Whisper skipped audio after it
MIN_GAP_S = 1.0        # uncovered speech at least this long gets transcribed again
# Whisper turns all the audio it is given into one big table first: ~7 GB of memory for 3 hours, enough
# to crash a 16 GB laptop. Audio longer than LONG_S is therefore transcribed in pieces of at most
# PIECE_S, cut in a pause, so memory stays the same for any length.
SR = 16000
LONG_S = 30 * 60
PIECE_S = 20 * 60
OVERLAP_S = 45         # more than one 30 s Whisper window, even after VAD drops some silence


def ytdlp(args, cookies_browser=None):
    import subprocess
    cmd = [sys.executable, '-m', 'yt_dlp', *YTDLP_BASE]
    if shutil.which('node'):
        cmd += ['--js-runtimes', 'node']
    if cookies_browser:
        cmd += ['--cookies-from-browser', cookies_browser]
    r = subprocess.run(cmd + args, capture_output=True, text=True, encoding='utf-8', errors='replace')
    if r.returncode != 0:
        err = r.stderr.strip().splitlines()[-8:]
        msg = '\n'.join(err)
        if "not a bot" in msg or 'Sign in to confirm' in msg:
            msg += ('\n\nYouTube asked for a sign-in check. Retry with your browser cookies, e.g.\n'
                    '  python run.py fetch <url> --cookies-from-browser chrome   (or firefox / edge)')
        die(f'yt-dlp failed:\n{msg}')
    return r.stdout


def is_url(s):
    return s.startswith('http://') or s.startswith('https://')


def video_extras(meta):
    """What the video page itself says, kept for reading long videos in parts: the description,
    the creator's own chapters, and YouTube's "most replayed" curve (when the site has them)."""
    out = {}
    desc = (meta.get('description') or '').strip()
    if desc:
        out['description'] = desc[:3000]
    chapters = [{'start': round(float(c.get('start_time') or 0), 2), 'end': round(float(c.get('end_time') or 0), 2),
                 'title': (c.get('title') or '').strip()} for c in meta.get('chapters') or [] if c.get('title')]
    if chapters:
        out['chapters'] = chapters
    heat = [[round(float(h['start_time']), 2), round(float(h['end_time']), 2), round(float(h['value']), 4)]
            for h in meta.get('heatmap') or [] if h.get('value') is not None]
    if heat:
        out['heatmap'] = heat
    return out


def download_audio(url, proj, cookies):
    import json
    meta = json.loads(ytdlp(['--dump-single-json', '--skip-download', url], cookies))
    title = meta.get('title') or 'video'
    slug = f"{slugify(title, 40)}-{meta.get('id', '')}".strip('-')
    pdir = proj or (OUTPUT / slug)
    src = pdir / 'source'
    src.mkdir(parents=True, exist_ok=True)
    existing = list(src.glob('audio.*'))
    if not existing:
        print(f'-> downloading audio: {title}')
        ytdlp(['-f', 'ba[ext=m4a]/ba/b', '-o', str(src / 'audio.%(ext)s'), url], cookies)
        existing = list(src.glob('audio.*'))
    if not existing:
        die('audio download produced no file')
    project = load_json(pdir / 'project.json', {}) or {}
    project.update({
        'source': url, 'kind': 'youtube', 'id': meta.get('id'), 'title': title,
        'channel': meta.get('channel') or meta.get('uploader'), 'channel_url': meta.get('channel_url'),
        'duration': meta.get('duration'), 'slug': pdir.name, 'audio': existing[0].name,
        'width': meta.get('width'), 'height': meta.get('height'),
    })
    project.update(video_extras(meta))
    if cookies:
        project['cookies_from_browser'] = cookies
    save_json(pdir / 'project.json', project)
    return pdir, project


def local_source(path):
    p = Path(path.strip().strip('"\'')).expanduser().resolve()
    if not p.exists():
        die(f'file not found: {p}\n(tip: put the path in quotes if it has spaces)')
    if p.is_dir():
        die(f'{p} is a folder. Give the path of the video file itself.')
    info = probe(p)
    if not info.get('width'):
        die(f'{p.name} has no video track. Clipping needs a video file (mp4, mov, mkv, webm, ...).')
    pdir = OUTPUT / slugify(p.stem, 50)
    old = load_json(pdir / 'project.json')
    if old and old.get('source') != str(p):
        # another file with the same name already has a project: keep them apart
        pdir = pdir.with_name(f'{pdir.name}-{hashlib.sha1(str(p).encode()).hexdigest()[:6]}')
    (pdir / 'source').mkdir(parents=True, exist_ok=True)
    project = load_json(pdir / 'project.json', {}) or {}
    project.update({'source': str(p), 'kind': 'local', 'title': p.stem, 'channel': None,
                    'duration': info['duration'], 'slug': pdir.name, 'video': str(p),
                    'width': info.get('width'), 'height': info.get('height')})
    save_json(pdir / 'project.json', project)
    return pdir, project


def to_wav16k(src, dst):
    if not dst.exists():
        ffmpeg('-i', src, '-vn', '-ac', '1', '-ar', '16000', '-c:a', 'pcm_s16le', dst)
    return dst


# ---------------- language ----------------

def detect_language(audio):
    """Whisper's language guess averaged over up to 4 windows spread through the speech
    (a single window can't tell Hinglish from English). Returns [(lang, prob), ...] best first."""
    import numpy as np
    from faster_whisper import WhisperModel
    from faster_whisper.audio import pad_or_trim
    from faster_whisper.vad import collect_chunks, get_speech_timestamps
    model = WhisperModel(model_path('base'), device='cpu', compute_type='int8')
    if len(audio) > LONG_S * SR:        # long audio: listen to 4 stretches of 2.5 min, not to all of it
        step, n = len(audio) // 4, 150 * SR
        audio = np.concatenate([audio[i * step + (step - n) // 2:][:n] for i in range(4)])
    try:
        chunks, _ = collect_chunks(audio, get_speech_timestamps(audio))
        speech = np.concatenate(chunks) if chunks else audio
    except Exception:
        speech = audio
    n = 16000 * 30
    starts = [0] if len(speech) <= n * 1.5 else [int(i * (len(speech) - n) / 3) for i in range(4)]
    probs = {}
    for s in starts:
        enc = model.encode(pad_or_trim(model.feature_extractor(speech[s:s + n])))
        for token, p in model.model.detect_language(enc)[0]:
            lang = token[2:-2]
            probs[lang] = probs.get(lang, 0.0) + p / len(starts)
    return sorted(probs.items(), key=lambda x: -x[1])


def resolve_language(requested, audio):
    """-> (language, detection ranking or None). 'hinglish' means: decode as Hindi, keep English in Roman."""
    lang = LANG_ALIASES.get(requested.lower(), requested.lower())
    if lang != 'auto':
        return lang, None
    ranked = detect_language(audio)
    probs = dict(ranked)
    top = ranked[0][0]
    hindi = sum(probs.get(k, 0.0) for k in HINDI_LIKE)
    if top in HINDI_LIKE or (top == 'en' and hindi >= 0.25):
        return HINGLISH, ranked
    return top, ranked


def is_hindi(lang):
    return lang == HINGLISH or lang in HINDI_LIKE


def pick_model(requested, lang, device):
    if requested and requested != 'auto':
        return requested[:-3] if lang != 'en' and requested.endswith('.en') else requested
    if device == 'cuda' or is_hindi(lang):
        return 'large-v3-turbo'      # far better Hindi than small; fast on an NVIDIA GPU
    return 'small.en' if lang == 'en' else 'small'


# ---------------- transcription ----------------

_LOOP = re.compile(r'(.{1,6}?)\1{3,}')


def clean_words(words):
    """Remove decoding glitches: half characters (�), a vowel sign/letter looping inside a Hindi
    word ("हूँँँँँ"), and the same word repeated 4+ times in a row."""
    out = []
    for w in words:
        t = w['w'].replace('\ufffd', '').strip()
        if has_devanagari(t):
            t = _LOOP.sub(r'\1', t)
        if not t:
            continue
        k = norm_token(t)
        if k and len(out) >= 3 and all(norm_token(o['w']) == k for o in out[-3:]):
            continue
        out.append({**w, 'w': t})
    return out


def _word(w):
    return {'w': w.word.strip(), 's': round(float(w.start), 3), 'e': round(float(w.end), 3),
            'p': round(float(w.probability), 3)}


def _uncovered(regions, words):
    """Stretches of speech (VAD regions) that no word covers."""
    covered = []
    for s, e in sorted((w['s'], min(w['e'], w['s'] + MAX_WORD_S)) for w in words):
        if covered and s <= covered[-1][1] + 0.3:
            covered[-1][1] = max(covered[-1][1], e)
        else:
            covered.append([s, e])
    gaps = []
    for a, b in regions:
        t = a
        for s, e in covered:
            if e <= t or s >= b:
                continue
            if s - t >= MIN_GAP_S:
                gaps.append((t, s))
            t = max(t, e)
        if b - t >= MIN_GAP_S:
            gaps.append((t, b))
    return gaps


def fill_gaps(model, audio, words, language, beam_size, rounds=2):
    """Whisper now and then skips a stretch of speech (in tests: 2-30% of Hinglish speech) and
    stretches the word before it over the hole. Find speech that no word covers and transcribe just
    those stretches again, as short separate clips, then merge the words in."""
    from faster_whisper.vad import VadOptions, get_speech_timestamps
    try:
        # speech regions of at most 12 s, split at natural pauses: short clips decode completely
        regions = [(c['start'] / 16000, c['end'] / 16000) for c in get_speech_timestamps(
            audio, VadOptions(min_silence_duration_ms=500, speech_pad_ms=100, max_speech_duration_s=12))]
    except Exception:
        return words
    for _ in range(rounds):
        gaps = _uncovered(regions, words)
        if not gaps:
            break
        print(f'   re-transcribing {len(gaps)} stretch(es) of speech that were skipped '
              f'({sum(b - a for a, b in gaps):.0f}s)', flush=True)
        clips = [x for a, b in gaps for x in (max(0.0, a - 0.2), b + 0.2)]
        segments, _ = model.transcribe(audio, language=language, beam_size=beam_size, word_timestamps=True,
                                       condition_on_previous_text=False, clip_timestamps=clips)
        new = []
        for seg in segments:
            if seg.no_speech_prob > 0.5 and seg.avg_logprob < -0.7:     # music / noise, not speech
                continue
            for w in seg.words or []:
                mid = (w.start + w.end) / 2
                if w.word.strip() and any(a - 0.2 <= mid <= b + 0.2 for a, b in gaps):
                    new.append(_word(w))
        if not new:
            break
        words = sorted(words + new, key=lambda w: w['s'])
        for cur, nxt in zip(words, words[1:]):          # a word never runs into the next one
            if cur['e'] > nxt['s']:
                cur['e'] = round(max(cur['s'] + 0.05, nxt['s']), 3)
        print(f'   recovered {len(new)} word(s)', flush=True)
    return words


def split_points(audio, piece_s=PIECE_S, search_s=90):
    """-> [(first sample, end sample), ...]: long audio in pieces of about piece_s seconds, each cut
    in the longest pause within search_s of the even split point. Short audio stays one piece."""
    import math
    import numpy as np
    from faster_whisper.vad import VadOptions, get_speech_timestamps
    n = len(audio)
    if n <= LONG_S * SR:
        return [(0, n)]
    k = math.ceil(n / (piece_s * SR))
    cuts = []
    for i in range(1, k):
        t = i * n // k
        a, b = max(0, t - search_s * SR), min(n, t + search_s * SR)
        try:
            speech = get_speech_timestamps(audio[a:b], VadOptions(min_silence_duration_ms=100, speech_pad_ms=0))
        except Exception:
            speech = []
        gaps = [(s['end'], e['start']) for s, e in zip(speech, speech[1:])]
        if gaps:            # the longest pause; of equal pauses, the one nearest the split point
            g0, g1 = max(gaps, key=lambda g: (g[1] - g[0], -abs(a + (g[0] + g[1]) // 2 - t)))
            cut = a + (g0 + g1) // 2
        else:               # no pause found: the quietest tenth of a second
            f = SR // 10
            frames = audio[a:a + (b - a) // f * f].reshape(-1, f)
            cut = a + int(np.argmin((frames ** 2).mean(axis=1))) * f + f // 2
        cuts.append(cut)
    bounds = [0] + cuts + [n]
    return list(zip(bounds, bounds[1:]))


def _transcribe_once(audio, model_name, lang, device, compute, beam):
    from faster_whisper import BatchedInferencePipeline, WhisperModel
    if device == 'cuda':
        gpu.enable_nvidia_libs()
    hindi = is_hindi(lang)
    if device == 'cuda':
        speed = 'a few minutes even for a long video'
    elif hindi:
        speed = 'on a laptop CPU 1-4x as long as the video'
    else:
        speed = 'on a laptop CPU roughly 1/5 of the video length'
    print(f'-> transcribing with whisper "{model_name}" on {device.upper()} ({speed}; '
          f'the first run also downloads the model) ...', flush=True)
    model = WhisperModel(model_path(model_name), device=device, compute_type=compute,
                         cpu_threads=max(1, (os.cpu_count() or 4) - 1))
    language = 'hi' if hindi else lang
    beam_size = beam or (5 if hindi or device == 'cuda' else 1)
    pipe = None if hindi else BatchedInferencePipeline(model=model)
    pieces = split_points(audio)
    if len(pieces) > 1:
        print(f'   long video: transcribing it in {len(pieces)} pieces of about '
              f'{len(audio) / SR / len(pieces) / 60:.0f} minutes (keeps memory use low)', flush=True)
    words, total, last_print = [], len(audio) / SR or 1, time.time()
    for a, b in pieces:
        # Whisper reads 30 s windows; in the last, shorter window of the audio it is given, it invents
        # words and misplaces times (tests: junk words, a lost sentence 5 s before the end). So each
        # piece hears OVERLAP_S past its cut and keeps only the words before the cut, which then lie
        # in a full window. The next piece starts right at the cut, in a pause (starts were clean).
        piece, off = audio[a:min(len(audio), b + OVERLAP_S * SR)], a / SR
        if hindi:
            # One window at a time. Hindi in Devanagari needs 3-4x the tokens of English, so a 30 s
            # window can hit Whisper's 448-token limit: here decoding resumes where it stopped instead
            # of dropping the rest (batched mode lost whole sentences in tests), and a looping window
            # is retried at a higher temperature. VAD skips silences, where Whisper tends to invent text.
            segments, _ = model.transcribe(
                piece, language=language, beam_size=beam_size, word_timestamps=True, vad_filter=True,
                condition_on_previous_text=False, hotwords=HINGLISH_PROMPT if lang == HINGLISH else None)
        else:
            # batched inference: ~2x faster than sequential on CPU with the same words (benchmarked)
            segments, _ = pipe.transcribe(piece, language=language, batch_size=8, word_timestamps=True,
                                          beam_size=beam_size)
        got = []
        for seg in segments:
            got += [_word(w) for w in seg.words or [] if w.word.strip()]
            if time.time() - last_print > 20:
                done = off + seg.end
                print(f'   {done / total:5.0%}  ({fmt_ts(done)} / {fmt_ts(total)})', flush=True)
                last_print = time.time()
        got = fill_gaps(model, piece, got, language, beam_size)
        if len(pieces) > 1:
            got = [{**w, 's': round(w['s'] + off, 3), 'e': round(min(w['e'] + off, b / SR), 3)} for w in got
                   if w['s'] + off < b / SR]
        words = join_pieces(words, got)
    return clean_words(words)


def join_pieces(words, got, max_dup=3, within=3.0):
    """Words of the next piece added to the words so far. If the last 1-3 words before the cut are the
    same as the first words after it (a word's time slipped across the cut, so both pieces have it),
    one copy is kept: the next piece's, which heard it from the pause on."""
    if not words or not got:
        return words + got
    for k in range(min(max_dup, len(words), len(got)), 0, -1):
        if [norm_token(w['w']) for w in words[-k:]] == [norm_token(w['w']) for w in got[:k]] \
                and got[0]['s'] - words[-k]['s'] < within:
            words = words[:-k]
            break
    if words and words[-1]['e'] > got[0]['s']:          # a word never runs into the next one
        words[-1] = {**words[-1], 'e': round(max(words[-1]['s'] + 0.05, got[0]['s']), 3)}
    return words + got


def transcribe(wav, model_req, lang_req, device_req, beam=None):
    """-> (words, language, model, device). Uses the NVIDIA GPU when it can and falls back to the CPU."""
    import soundfile as sf
    audio, sr = sf.read(str(wav), dtype='float32')
    try:
        lang, ranked = resolve_language(lang_req, audio)
    except Exception as e:
        if is_network_error(e):
            die(network_help('base', e))
        raise
    if ranked:
        top = ', '.join(f'{k} {p:.0%}' for k, p in ranked[:3])
        print(f'-> detected language: {lang}  ({top})')
        if lang == HINGLISH:
            print('   Hindi/Hinglish: Hindi is written in Devanagari, English words in Roman. '
                  'Not right? rerun with --lang en --retranscribe')
    device = gpu.pick_device(device_req)
    attempts = [('cuda', 'float16'), ('cuda', 'int8_float16'), ('cpu', 'int8')] if device == 'cuda' \
        else [('cpu', 'int8')]
    i = 0
    while True:
        dev, compute = attempts[i]
        model_name = pick_model(model_req, lang, dev)
        try:
            return _transcribe_once(audio, model_name, lang, dev, compute, beam), lang, model_name, dev
        except Exception as e:
            if is_network_error(e):          # the model download failed: no other device will help
                die(network_help(model_name, e))
            if dev == 'cpu':
                raise
            msg, hint = gpu.describe_error(e)
            print(f'   ! GPU transcription failed: {msg}\n     ({hint})')
            # only an out-of-memory error is worth a lighter retry on the GPU; anything else -> CPU
            i = i + 1 if compute == 'float16' and 'out of memory' in msg.lower() else len(attempts) - 1
            print(f'   -> retrying on {attempts[i][0].upper()} ({attempts[i][1]})', flush=True)


def sentences(words, soft_max=30, hard_max=60, gap=0.8):
    """Group words into sentence lines for Claude to read. Long sentences are only broken at a comma
    (or at hard_max), so a line end is never mistaken for a sentence end."""
    out, cur = [], []
    for i, w in enumerate(words):
        cur.append(w)
        nxt = words[i + 1] if i + 1 < len(words) else None
        end_punct = is_sentence_end(w['w'])
        long_gap = nxt is not None and nxt['s'] - w['e'] > gap
        comma_break = len(cur) >= soft_max and w['w'][-1:] in ',;:'
        if nxt is None or end_punct or long_gap or comma_break or len(cur) >= hard_max:
            out.append({'s': cur[0]['s'], 'e': cur[-1]['e'], 'i0': i - len(cur) + 1, 'i1': i,
                        'text': ' '.join(x['w'] for x in cur)})
            cur = []
    return out


def write_transcript(pdir, words, project):
    tdir = pdir / 'transcript'
    save_json(tdir / 'words.json', words)
    lines = sentences(words)
    save_json(tdir / 'sentences.json', lines)
    lang = project.get('language') or '-'
    if is_hindi(lang):
        lang += '  (Hindi in Devanagari, English words in Roman; captions: python run.py romanize <project>)'
    head = [f"# {project.get('title')}", f"# channel: {project.get('channel') or '-'}",
            f"# duration: {fmt_ts(project.get('duration') or (words[-1]['e'] if words else 0))}",
            f'# language: {lang}',
            '# format: [start_seconds-end_seconds] text   (seconds are what clips.json uses)', '']
    body = [f"[{s['s']:.2f}-{s['e']:.2f}] {s['text']}" for s in lines]
    (tdir / 'transcript.txt').write_text('\n'.join(head + body) + '\n', encoding='utf-8')
    return tdir / 'transcript.txt', len(lines)


def main():
    cfg = settings()
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('source', help='YouTube URL or local video file')
    ap.add_argument('--model', default=cfg['model'],
                    help='whisper model: auto (default: large-v3-turbo for Hindi/Hinglish or on a GPU, '
                         'else small.en), or e.g. large-v3, medium, small')
    ap.add_argument('--lang', default=cfg['language'], help='auto (default), hinglish, en, hi, ... ')
    ap.add_argument('--device', default=cfg['device'], help='auto (default: NVIDIA GPU if usable), cuda or cpu')
    ap.add_argument('--beam', type=int, default=None, help='beam size (default 5 for Hindi or on GPU, else 1)')
    ap.add_argument('--cookies-from-browser', default=None, help='chrome / firefox / edge (if YouTube blocks)')
    ap.add_argument('--retranscribe', action='store_true')
    a = ap.parse_args()

    if is_url(a.source):
        pdir, project = download_audio(a.source, None, a.cookies_from_browser)
        audio_src = pdir / 'source' / project['audio']
    else:
        pdir, project = local_source(a.source)
        audio_src = Path(project['video'])

    tx = pdir / 'transcript' / 'transcript.txt'
    if tx.exists() and not a.retranscribe:
        print('-> transcript already exists (use --retranscribe to redo)')
    else:
        wav = to_wav16k(audio_src, pdir / 'source' / 'audio16k.wav')
        t0 = time.time()
        words, lang, model_name, device = transcribe(wav, a.model, a.lang, a.device, a.beam)
        if not words:
            die('no speech found in this video')
        project.update({'language': lang, 'asr_model': model_name, 'asr_device': device})
        save_json(pdir / 'project.json', project)
        tx, n = write_transcript(pdir, words, project)
        print(f'-> {len(words)} words, {n} lines in {time.time() - t0:.0f}s')

    print('\nDONE')
    print(f'project:    {pdir.name}')
    print(f"language:   {project.get('language')}")
    print(f'transcript: {tx}')
    print('next: read the transcript, write clips.json, then  python run.py cut ' + pdir.name)


if __name__ == '__main__':
    main()
