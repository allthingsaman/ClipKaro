"""Step 1: get the video's audio and transcribe it with word timestamps.

    python run.py fetch "https://www.youtube.com/watch?v=..."
    python run.py fetch "C:/videos/my-podcast.mp4"            # a video file on your computer
    options: --lang auto|hinglish|en|hi|...   --model auto|large-v3-turbo|large-v3|medium|small.en|...
             --device auto|cuda|cpu   --cookies-from-browser chrome   --retranscribe   --no-video

Hindi / Hinglish is detected automatically (force it with --lang hinglish). Whisper then writes Hindi
in Devanagari and English words in Roman ("आज हम business की बात करेंगे।"); `run.py romanize`
turns the picked clips into Roman Hinglish captions later. Defaults come from settings.json.

Creates output/<slug>/ with project.json, source/audio.*, transcript/words.json and transcript.txt.
For a YouTube link the video (max 1080p) downloads in the background while the audio is transcribed:
`cut` needs it anyway, and the picture shows what kind of video it is (`run.py kind`: a live stream?
gameplay with a facecam? break screens like "Starting soon" or "Be right back", whose lines are then
left out of the transcript). --no-video skips that; `cut` downloads the video later.
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


def page_facts(meta):
    """Whether it was a live stream, and YouTube's category: what `run.py kind` goes by."""
    return {'live_status': meta.get('live_status'), 'was_live': bool(meta.get('was_live')),
            'categories': meta.get('categories') or []}


def length_line(project):
    """'1:40:09, was a live stream' for the first line of fetch / info."""
    from .kind import live_info
    bits = [fmt_ts(project['duration']).split('.')[0]] if project.get('duration') else []
    if live_info(project)[0]:
        bits.append('was a live stream')
    if 'Gaming' in (project.get('categories') or []):
        bits.append('Gaming')
    return ', '.join(bits)


def download_audio(url, proj, cookies):
    import json
    meta = json.loads(ytdlp(['--dump-single-json', '--skip-download', url], cookies))
    title = meta.get('title') or 'video'
    slug = f"{slugify(title, 40)}-{meta.get('id', '')}".strip('-')
    pdir = proj or (OUTPUT / slug)
    src = pdir / 'source'
    src.mkdir(parents=True, exist_ok=True)
    existing = list(src.glob('audio.*'))
    facts = {'duration': meta.get('duration'), 'source': url, **page_facts(meta)}
    print(f'-> {title}  ({length_line(facts)})', flush=True)
    if not existing:
        print('-> downloading audio')
        ytdlp(['-f', 'ba[ext=m4a]/ba/b', '-o', str(src / 'audio.%(ext)s'), url], cookies)
        existing = list(src.glob('audio.*'))
    if not existing:
        die('audio download produced no file')
    project = load_json(pdir / 'project.json', {}) or {}
    project.update({
        'source': url, 'kind': 'youtube', 'id': meta.get('id'), 'title': title,
        'channel': meta.get('channel') or meta.get('uploader'), 'channel_url': meta.get('channel_url'),
        'duration': meta.get('duration'), 'slug': pdir.name, 'audio': existing[0].name,
        'width': meta.get('width'), 'height': meta.get('height'), **page_facts(meta),
    })
    project.update(video_extras(meta))
    if cookies:
        project['cookies_from_browser'] = cookies
    save_json(pdir / 'project.json', project)
    return pdir, project


VIDEO_FORMAT = 'bv*[height<=1080][vcodec^=avc1]+ba[ext=m4a]/bv*[height<=1080]+ba/b[height<=1080]/b'


def video_file(pdir):
    """source/video.mp4 (or .mkv/.webm) once it is complete. yt-dlp's half-done pieces
    (video.f137.mp4, video.mp4.part) never count."""
    found = [p for p in (pdir / 'source').glob('video.*') if p.stem == 'video' and p.suffix in ('.mp4', '.mkv', '.webm')]
    return found[0] if found else None


def video_download_cmd(pdir, project):
    import subprocess  # noqa: F401  (kept next to its use)
    cmd = [sys.executable, '-m', 'yt_dlp', *YTDLP_BASE]
    if shutil.which('node'):
        cmd += ['--js-runtimes', 'node']
    if project.get('cookies_from_browser'):
        cmd += ['--cookies-from-browser', project['cookies_from_browser']]
    return cmd + ['-f', VIDEO_FORMAT, '--merge-output-format', 'mp4',
                  '-o', str(pdir / 'source' / 'video.%(ext)s'), project['source']]


def start_video_download(pdir, project):
    """Start downloading the video in the background (YouTube only). Returns the process, or None."""
    import subprocess
    if project.get('kind') != 'youtube' or video_file(pdir):
        return None
    log = open(pdir / 'source' / 'video-download.log', 'w', encoding='utf-8')
    print('-> downloading the video in the background (max 1080p; cut needs it, and the picture shows '
          'break screens and the facecam)', flush=True)
    return subprocess.Popen(video_download_cmd(pdir, project), stdout=log, stderr=subprocess.STDOUT)


def finish_video_download(pdir, proc):
    """Wait for the background download. Returns the video path, or None (never fatal)."""
    if proc is None:
        return video_file(pdir)
    if proc.poll() is None:
        print('-> waiting for the video download to finish ...', flush=True)
    code = proc.wait()
    if code != 0 or not video_file(pdir):
        tail = (pdir / 'source' / 'video-download.log').read_text(encoding='utf-8', errors='replace').strip()
        tail = '\n'.join('     ' + ln for ln in tail.splitlines()[-4:])
        print(f'   ! the video download failed (cut tries again later):\n{tail}')
        return None
    return video_file(pdir)


def download_video(pdir, project):
    """Download the video now and wait for it (what `cut` does when fetch didn't)."""
    print('-> downloading video (max 1080p, first time only) ...', flush=True)
    ytdlp(['-f', VIDEO_FORMAT, '--merge-output-format', 'mp4', '-o', str(pdir / 'source' / 'video.%(ext)s'),
           project['source']], project.get('cookies_from_browser'))
    found = video_file(pdir)
    if not found:
        die('video download produced no file')
    return found


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
    print(f"-> {p.name}  ({fmt_ts(info['duration']).split('.')[0]})", flush=True)
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


UNSURE_P = 0.45       # mean word confidence below this over a stretch: the recogniser was guessing


BRIDGE_WORDS, BRIDGE_S, BRIDGE_P = 6, 2.5, 0.75   # a short, shaky gap between two unsure cores joins them


def _cores(vals, lo, hi, out):
    """Stretches of vals[lo:hi] with the largest positive sum (= mean confidence under the threshold),
    best first, then the same left and right of it."""
    if hi - lo <= 0:
        return
    best, cur, cur_lo, b_lo, b_hi = 0.0, 0.0, lo, None, None
    for k in range(lo, hi):
        if cur <= 0:
            cur, cur_lo = 0.0, k
        cur += vals[k]
        if cur > best:
            best, b_lo, b_hi = cur, cur_lo, k + 1
    if b_lo is None:
        return
    out.append((b_lo, b_hi - 1))
    _cores(vals, lo, b_lo, out)
    _cores(vals, b_hi, hi, out)


def _greedy_stretches(words, thr, min_words, min_s):
    """The first version's runs: grown word by word while the mean stays under thr + 0.08, kept when
    the whole run's mean is under thr. Finds short runs well; misses a run whose clear words after
    it push the mean over thr (see unsure_stretches)."""
    out, i = [], 0
    while i < len(words):
        if words[i].get('p', 1.0) >= 0.5:
            i += 1
            continue
        j = i
        while j + 1 < len(words) and words[j + 1]['s'] - words[j]['e'] < 1.0 and \
                sum(w.get('p', 1.0) for w in words[i:j + 2]) / (j + 2 - i) < thr + 0.08:
            j += 1
        run = words[i:j + 1]
        if len(run) >= min_words and run[-1]['e'] - run[0]['s'] >= min_s and \
                sum(w.get('p', 1.0) for w in run) / len(run) < thr:
            out.append((i, j))
        i = j + 1
    return out


def unsure_stretches(words, thr=UNSURE_P, min_words=4, min_s=1.5):
    """[(first word index, last word index)] of stretches the recogniser was unsure of: at least 4
    words and 1.5 s, mean confidence under 0.45. Mostly a second voice in another language (a game
    character, a film clip, a song), music or noise. Measured (Nov 2026): podcasts and talking-head
    videos have 0-2 such stretches; a 44-minute gameplay video had 91 (its game cutscenes).

    Each stretch is the run of words (no pause of 1 s or more inside) whose confidence sums furthest
    below the threshold, so clear words next to it can't hide it. (The first version grew a stretch
    word by word and dropped all of it when the clear words after it pushed the mean over 0.45: a game
    character's English line, heard as Devanagari nonsense, kept its wrong captions. Its runs are
    still taken too, so nothing it found is missed.) Two stretches with only a short, shaky bit
    between them (6 words, 2.5 s, mean confidence under 0.75: a hallucinated "कर दो कर दो") become one."""
    groups, g0 = [], 0
    for k in range(1, len(words) + 1):
        if k == len(words) or words[k]['s'] - words[k - 1]['e'] >= 1.0:
            groups.append((g0, k))
            g0 = k
    found = []
    for lo, hi in groups:
        vals = [thr - w.get('p', 1.0) for w in words[lo:hi]]
        cores = []
        _cores(vals, 0, len(vals), cores)
        found += [(lo + a, lo + b) for a, b in cores]
    found = sorted((i, j) for i, j in found if j > i)          # one odd word alone is no stretch
    merged = []
    for i, j in found:
        if merged:
            pi, pj = merged[-1]
            between = words[pj + 1:i]
            if (len(between) <= BRIDGE_WORDS and words[i]['s'] - words[pj]['e'] <= BRIDGE_S
                    and all(b['s'] - a['e'] < 1.0 for a, b in zip(words[pj:i], words[pj + 1:i + 1]))
                    and (not between or sum(w.get('p', 1.0) for w in between) / len(between) < BRIDGE_P)):
                merged[-1] = (pi, j)
                continue
        merged.append((i, j))
    joined = []                                 # + the first version's runs, overlaps joined
    for i, j in sorted(merged + _greedy_stretches(words, thr, min_words, min_s)):
        if joined and i <= joined[-1][1] + 1:
            joined[-1] = (joined[-1][0], max(joined[-1][1], j))
        else:
            joined.append((i, j))
    out = []
    for i, j in joined:
        # take in unsure words right next to it (the tail of a game line: "वह राइज हैं")
        while i > 0 and words[i - 1].get('p', 1.0) < 0.5 and words[i]['s'] - words[i - 1]['e'] < 1.2 \
                and not (out and i - 1 <= out[-1][1]):
            i -= 1
        while j + 1 < len(words) and words[j + 1].get('p', 1.0) < 0.5 and words[j + 1]['s'] - words[j]['e'] < 1.2:
            j += 1
        if out and i <= out[-1][1]:
            i = out[-1][1] + 1
        run = words[i:j + 1]
        if len(run) >= min_words and run[-1]['e'] - run[0]['s'] >= min_s and \
                sum(w.get('p', 1.0) for w in run) / len(run) < thr + 0.05:     # mostly unsure, even when joined
            out.append((i, j))
    return out


# a second language the captions can show and the audience reads: English in a Hindi/Hinglish video.
# Other languages (a Japanese anime line, game audio heard as Korean) stay without captions; in tests
# their "recognised" words were loops and made-up text.
SECOND_LANGS = {'hi': {'en'}, 'en': set()}


RELISTEN_P = 0.6        # a second listen must be at least this sure (and 0.15 surer than the first)


def _looping(words):
    """Whisper's own test for a decode stuck in a loop ("कर दो कर दो कर दो ..."): the text
    compresses more than 2.4 times."""
    import zlib
    text = ' '.join(w['w'] for w in words).encode('utf-8')
    return len(text) >= 40 and len(text) / len(zlib.compress(text)) > 2.4


def _decode(model, audio, windows, lang, beam_size, keep, prompt=None):
    """Words heard in `lang` in each (lo, hi) window, kept only inside keep=(lo, hi). One fixed
    decode (temperature 0): the random retries Whisper makes otherwise gave a different answer each
    run. -> (words, mean confidence)."""
    got = []
    for lo, hi in windows:
        try:
            # only this window's audio: given the whole video (clip_timestamps), Whisper prepares all
            # of it again for every window (18 minutes for 105 stretches of an 83-minute video)
            segs, _ = model.transcribe(audio[int(lo * SR):int(hi * SR)], language=lang, beam_size=beam_size,
                                       word_timestamps=True, condition_on_previous_text=False,
                                       temperature=0.0, hotwords=prompt)
            got += [{**_word(w), 's': round(lo + w.start, 3), 'e': round(lo + w.end, 3)}
                    for s in segs for w in (s.words or [])
                    if w.word.strip() and keep[0] <= lo + (w.start + w.end) / 2 <= keep[1]]
        except Exception:
            pass
    got = clean_words(got)                 # loops and broken characters out first
    if _looping(got):                      # stuck in a loop: heard nothing usable
        return [], 0.0
    return got, (sum(w['p'] for w in got) / len(got) if got else 0.0)


def _listen_again(model, audio, words, i0, i1, lang, beam_size):
    """The stretch heard again in `lang`: with a little room around it, then without, then as two
    halves split at its longest pause. Whisper sometimes drops a whole line for a window a few tenths
    of a second wider (a 13 s game line came back as just "Oh"), so a thin answer gets another try.
    -> (words, mean confidence), or ([], 0.0)."""
    a, b = words[i0]['s'], words[i1]['e']
    # new words only between the kept neighbours, so a word just outside is never heard twice
    keep = (max(a - 0.3, words[i0 - 1]['e']) if i0 > 0 else max(0.0, a - 0.3),
            min(b + 0.3, words[i1 + 1]['s']) if i1 + 1 < len(words) else b + 0.3)
    tries = [[(max(0.0, a - 0.3), b + 0.3)], [(a, b)]]
    if i1 > i0 + 3:
        k = max(range(i0 + 1, i1 + 1), key=lambda m: words[m]['s'] - words[m - 1]['e'])
        tries.append([(max(0.0, a - 0.2), words[k - 1]['e'] + 0.1), (words[k]['s'] - 0.1, b + 0.2)])
    best = ([], 0.0)
    for windows in tries:
        got, p = _decode(model, audio, windows, lang, beam_size, keep)
        same = lambda x, y: norm_token(x['w']) == norm_token(y['w'])
        if got and i1 + 1 < len(words) and same(got[-1], words[i1 + 1]):
            got = got[:-1]                                  # "How am" + the kept "am I meant ..."
        if got and i0 > 0 and same(got[0], words[i0 - 1]):
            got = got[1:]
        full = len(got) >= max(2, 0.25 * (b - a))          # speech is 2-3 words a second
        if full and p >= RELISTEN_P:
            return got, p
        if full and p > best[1]:
            best = (got, p)
    return best


def relisten(model, audio, words, base_lang, beam_size, sr=16000):
    """Listen again to each unsure stretch. A video transcribed as Hindi whose game character speaks
    English got that English forced into Devanagari nonsense, which became wrong captions.
    - Whisper hears English there: the stretch is decoded in English, and it replaces the nonsense
      when it is sure (0.6, and 0.15 surer than the first listen). One check first: forced into
      English, a streamer's own Hinglish comes back *translated* ("usko ghar jaana hai" -> "I have to
      go to his house"). So the stretch is also decoded in the video's own language: English speech
      comes back in English letters there ("don't push me ..."), Hinglish in Hindi letters ("इसको घर
      जाना है"). Mostly Hindi letters, heard surer than the English: no English. That decode is only
      a check, never used for captions (alone, it loops: "कर दो कर दो ...").
    - Otherwise the words are marked "unsure" and get no captions (no captions beat wrong ones; a
      game shows its own subtitles). -> (words, summary dict)."""
    found = unsure_stretches(words)
    if not found:
        return words, {}
    info = {'stretches': len(found), 'fixed': 0, 'unsure': 0, 'langs': {}}
    res, last = [], 0
    for i0, i1 in found:
        a, b = words[i0]['s'], words[i1]['e']
        lo, hi = max(0.0, a - 0.3), b + 0.3
        old_p = sum(w.get('p', 1.0) for w in words[i0:i1 + 1]) / (i1 + 1 - i0)
        new = None
        try:
            lang, prob, _ = model.detect_language(audio=audio[int(lo * sr):int(hi * sr)])
        except Exception:
            lang, prob = None, 0.0
        # English must be Whisper's top guess for the stretch (Hindi speech is guessed as Hindi, so it
        # is never turned into English); a game line mixed with music can guess as low as 0.49
        if lang and lang != base_lang and prob >= 0.3 and lang in SECOND_LANGS.get(base_lang, set()):
            got, p = _listen_again(model, audio, words, i0, i1, lang, beam_size)
            if got and p >= RELISTEN_P and p >= old_p + 0.15:
                own, own_p = _listen_again(model, audio, words, i0, i1, base_lang, beam_size)
                hindi = sum(has_devanagari(w['w']) for w in own) / len(own) if own else 0.0
                if hindi >= 0.5 and own_p > p:     # Hindi words, heard surer: the English is a translation
                    info['own'] = info.get('own', 0) + 1
                else:
                    new = [{**w, 'lang': lang} for w in got]
                    info['langs'][lang] = info['langs'].get(lang, 0) + 1
        res += words[last:i0]
        if new:
            res += new
            info['fixed'] += 1
        else:
            res += [{**w, 'unsure': True} for w in words[i0:i1 + 1]]
            info['unsure'] += 1
        last = i1 + 1
    res += words[last:]
    for cur, nxt in zip(res, res[1:]):                 # a word never runs into the next one
        if cur['e'] > nxt['s']:
            cur['e'] = round(max(cur['s'] + 0.05, nxt['s']), 3)
    return res, info


def relisten_report(info):
    if not info:
        return
    langs = ', '.join(f'{k}: {v}' for k, v in info['langs'].items())
    own = info.get('own', 0)
    print(f"   re-listened to {info['stretches']} unclear stretch(es): {info['fixed']} recognised in another "
          f"language{f' ({langs})' if langs else ''}, {info['unsure']} left without captions (game voices, "
          f"music or noise{f'; {own} of them sounded like translated speech' if own else ''})", flush=True)


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
    words, info = relisten(model, audio, clean_words(words), language, beam_size)
    relisten_report(info)
    return words


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
            text = ' '.join(x['w'] for x in cur)
            if 2 * sum(1 for x in cur if x.get('unsure')) >= len(cur):
                text = '(unclear: a game voice, music or noise) ' + text     # the recogniser was guessing
            out.append({'s': cur[0]['s'], 'e': cur[-1]['e'], 'i0': i - len(cur) + 1, 'i1': i, 'text': text})
            cur = []
    return out


def write_transcript(pdir, words, project):
    tdir = pdir / 'transcript'
    save_json(tdir / 'words.json', words)
    lines = sentences(words)
    save_json(tdir / 'sentences.json', lines)
    return render_transcript(pdir, project, lines), len(lines)


def render_transcript(pdir, project, lines):
    """transcript.txt from the sentence lines. Lines said during a break screen (see `run.py kind`)
    are replaced by one marker line, so no clip is picked from them."""
    from .kind import active_breaks, hide_breaks
    tdir = pdir / 'transcript'
    lang = project.get('language') or '-'
    if is_hindi(lang):
        lang += '  (Hindi in Devanagari, English words in Roman; captions: python run.py romanize <project>)'
    head = [f"# {project.get('title')}", f"# channel: {project.get('channel') or '-'}",
            f"# duration: {fmt_ts(project.get('duration') or (words[-1]['e'] if words else 0))}",
            f'# language: {lang}',
            '# format: [start_seconds-end_seconds] text   (seconds are what clips.json uses)', '']
    body = [s['marker'] if 'marker' in s else f"[{s['s']:.2f}-{s['e']:.2f}] {s['text']}"
            for s in hide_breaks(lines, active_breaks(project))]
    (tdir / 'transcript.txt').write_text('\n'.join(head + body) + '\n', encoding='utf-8')
    return tdir / 'transcript.txt'


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
    ap.add_argument('--no-video', action='store_true',
                    help="don't download the video now (cut does it later; break screens aren't checked then)")
    a = ap.parse_args()

    video_job = None
    if is_url(a.source):
        pdir, project = download_audio(a.source, None, a.cookies_from_browser)
        audio_src = pdir / 'source' / project['audio']
        if not a.no_video:
            video_job = start_video_download(pdir, project)
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
        del words
        import gc
        gc.collect()                    # the speech model's memory is free before the sound pass

    # laughter, applause, both talking at once, lively spots: hints every video has (about 1 minute
    # for 3 hours). Never fatal: without it, clips are picked from the words alone, as in v1.1.
    try:
        from . import sound
        to_wav16k(audio_src, pdir / 'source' / 'audio16k.wav')
        sound.ensure(pdir)
    except Exception as e:
        print(f'   (sound cues skipped: {type(e).__name__}: {e})')

    # no captions for words made up during laughter, noise ("झाल") or in loops ("कर दो कर दो ...")
    try:
        from . import sound, tidy
        words_now = load_json(pdir / 'transcript' / 'words.json') or []
        tidied, why = tidy.tidy_words(words_now, sound.load(pdir))
        if why:
            write_transcript(pdir, tidied, load_json(pdir / 'project.json', {}) or project)
            print(f'-> tidy: {tidy.report(why)}')
    except Exception as e:
        print(f'   (tidy skipped: {type(e).__name__}: {e})')

    # what kind of video: a live stream? gameplay with a facecam? break screens to leave out?
    if not a.no_video:
        finish_video_download(pdir, video_job)
    try:
        from . import kind
        project = kind.run(pdir, load_json(pdir / 'project.json', {}) or project)
    except Exception as e:
        print(f'   (video kind check skipped: {type(e).__name__}: {e})')

    print('\nDONE')
    print(f'project:    {pdir.name}')
    print(f"language:   {project.get('language')}")
    print(f'transcript: {tx}')
    print(f'next: python run.py parts {pdir.name}   (add --at-least N / --at-most N if the user asked for a number '
          'of clips, --deep yes|no for their deep-clip answer, --mode quick only if they asked for quick)')


if __name__ == '__main__':
    main()
