"""Sound cues for the whole video: laughter, applause, music, two people talking at once, and how
loud and how fast people talk.

Every video has these, unlike YouTube's "most replayed" curve (which most small channels never
get), so they give every video the same hints of lively moments. They are used in two ways:
- **Lively spots**: a short list of moments for the readers to check. A recall aid only: a spot
  becomes a clip only if its words make a good clip.
- **Markers** like "[laughter ~2 s]" inside the clip text the critic reads, so a joke that is funny
  because of how it is said isn't missed. Facts, never verdicts.
Nothing here ever lowers a clip: a calm solo review without laughter is not "dull".

Evidence (research for phase 2): in recorded meetings, laughter was the strongest single cue for
lively stretches, then the words, then who-talks-when, then loudness and pitch (Makhervaks et al.,
ICASSP 2020). All comparisons are within the same video, never between videos.

Models: YAMNet (laughter, applause, music) and pyannote segmentation 3.0 (two people talking at
once), both already used by the two-person framing; run with onnxruntime, no sherpa-onnx needed.
The audio is read in 60 s blocks, so memory stays small for any length (about 1 minute of CPU for
a 3-hour video). If a model is missing, that cue is simply left out.

    python run.py sound <project>        (fetch runs it by itself after transcribing)
"""
import argparse
import math
import os
import time

import numpy as np

from .common import die, fmt_ts, load_json, project_dir, save_json
from . import speakers

CUES_V = 1               # raise when the cues change: older cues.json files are made again
SR = 16000
BLOCK = 60.0             # seconds of audio read at a time
STEP = 10.0              # loudness, speed, turns and overlap are summed per 10 s step
WINDOW = 30.0            # lively spots are 30 s windows
LAUGH_MARK = 0.30        # a laughter marker needs one frame at least this sure (the director uses 0.15) ...
LAUGH_MIN_S = 1.2        # ... and at least two YAMNet frames in a row (one frame alone is too unsure)
APPLAUSE_MIN = 0.30
APPLAUSE_MIN_S = 1.0
MUSIC_MIN = 0.30         # laughter / applause frames with this much music don't count (game sound, jingles)
MUSIC_SPAN = 0.50        # music stretches: frames at least this musical ...
MUSIC_SPAN_S = 5.0       # ... for at least this long
OVERLAP_MIN_S = 1.0      # "both talk at once" marker: at least this long
APPLAUSE_CLASSES = [58, 61, 62]          # YAMNet: Clapping, Cheering, Applause
# game sound bursts (hints for gameplay; AudioSet rates these labels 100 % right): the kind they show as
BURST_CLASSES = {'explosion': [420, 430, 424],          # Explosion, Boom, Artillery fire
                 'gunfire': [421, 422, 423],            # Gunshot/gunfire, Machine gun, Fusillade
                 'crash': [463, 437, 306]}              # Smash/crash, Shatter, Skidding
BURST_MIN = 0.40         # a frame this sure of a burst class ...
BURST_GAP = 3.0          # ... bursts closer than this are one (a firefight is one hint, not twenty)
MUSIC_CLASS = 132                        # YAMNet: Music
SEG_WIN = 10.0                           # pyannote segmentation 3.0 reads 10 s windows
SEG_FRAME = 270 / SR                     # one output frame per 270 samples (16.9 ms)


# ---------------------------------------------------------------- reading the audio in blocks

def blocks(wav, block=BLOCK):
    """(start_seconds, samples) for consecutive blocks of the 16 kHz wav, never the whole file at once."""
    import soundfile as sf
    with sf.SoundFile(str(wav)) as f:
        if f.samplerate != SR:
            raise ValueError(f'{wav} is {f.samplerate} Hz, expected {SR}')
        n, t = int(block * SR), 0.0
        while True:
            x = f.read(n, dtype='float32', always_2d=True)
            if not len(x):
                break
            yield t, x[:, 0].copy()
            t += len(x) / SR


def spans(times, flags, frame, min_len, gap=0.5):
    """Merge frames that are on (start times + one frame length) into [start, end] stretches."""
    out = []
    for t, on in zip(times, flags):
        if not on:
            continue
        if out and t <= out[-1][1] + gap:
            out[-1][1] = max(out[-1][1], t + frame)
        else:
            out.append([t, t + frame])
    return [[round(a, 2), round(b, 2)] for a, b in out if b - a >= min_len]


# ---------------------------------------------------------------- the cues

def zscores(vals):
    """z-scores of the numbers in vals (None stays None), within this one video."""
    xs = [v for v in vals if v is not None]
    if len(xs) < 3:
        return [None] * len(vals)
    mu, sd = float(np.mean(xs)), float(np.std(xs)) or 1.0
    return [None if v is None else round((v - mu) / sd, 2) for v in vals]


def word_steps(words, n_steps):
    """Seconds of speech and number of words in each 10 s step (from the word times)."""
    speech, count = [0.0] * n_steps, [0] * n_steps
    for w in words:
        k = int(w['s'] // STEP)
        if 0 <= k < n_steps:
            count[k] += 1
        a, b = w['s'], w['e']
        while a < b:
            k = int(a // STEP)
            if k >= n_steps:
                break
            nxt = min(b, (k + 1) * STEP)
            speech[k] += nxt - a
            a = nxt
    return speech, count


def scan(pdir, quiet=False):
    """Measure the cues of a project's audio and save transcript/cues.json. Returns the cues, or
    None when there is no audio or transcript."""
    project = load_json(pdir / 'project.json', {}) or {}
    wav = pdir / 'source' / 'audio16k.wav'
    words = load_json(pdir / 'transcript' / 'words.json')
    if not wav.exists() or not words:
        return None
    import soundfile as sf
    duration = sf.info(str(wav)).duration
    n_steps = max(1, math.ceil(duration / STEP))
    t_start = time.time()

    yam = seg = None
    try:
        import onnxruntime as ort
        threads = max(1, min(4, (os.cpu_count() or 4) - 1))
        opts = ort.SessionOptions()
        opts.intra_op_num_threads = threads
        p = speakers.model_file('laughter')
        if p:
            yam = ort.InferenceSession(str(p), opts, providers=['CPUExecutionProvider'])
        p = speakers.model_file('segmentation')
        if p:
            seg = ort.InferenceSession(str(p), opts, providers=['CPUExecutionProvider'])
    except Exception as e:                       # onnxruntime missing or a broken model: no sound cues
        if not quiet:
            print(f'   (sound cues skipped: {type(e).__name__})')

    hop, win = speakers.YAMNET_HOP, speakers.YAMNET_WIN
    y_times, laugh, clap, music = [], [], [], []
    burst = {k: [] for k in BURST_CLASSES}
    seg_wins = []                                # (start time, pyannote class per frame) per 10 s window
    loud = [[] for _ in range(n_steps)]          # RMS dB of 0.5 s frames, per step
    for t0, x in blocks(wav):
        if yam is not None and len(x) >= int(win * SR):
            out = yam.run(None, {'waveform': x})[0]
            for i, row in enumerate(out):
                y_times.append(t0 + i * hop)
                laugh.append(float(row[speakers.LAUGH_CLASSES].max()))
                clap.append(float(row[APPLAUSE_CLASSES].max()))
                music.append(float(row[MUSIC_CLASS]))
                for k, cls in BURST_CLASSES.items():
                    burst[k].append(float(row[cls].max()))
        if seg is not None:
            n = int(SEG_WIN * SR)
            chunks = [x[i:i + n] for i in range(0, len(x), n)]
            full = [c for c in chunks if len(c) == n]
            if full:
                y = seg.run(None, {'x': np.stack(full)[:, None, :]})[0]      # (N, frames, 7)
                for k, frames in enumerate(y):
                    seg_wins.append((t0 + k * SEG_WIN, frames.argmax(axis=1).astype(np.int8)))
        # loudness: RMS in dB per 0.5 s frame
        m = int(0.5 * SR)
        for i in range(0, len(x) - m + 1, m):
            r = float(np.sqrt(np.mean(x[i:i + m] ** 2)) + 1e-9)
            k = int((t0 + i / SR) // STEP)
            if k < n_steps:
                loud[k].append((t0 + i / SR, 20 * math.log10(r)))

    cues = {'v': CUES_V, 'duration': round(duration, 2), 'step': STEP,
            'models': {'yamnet': yam is not None, 'segmentation': seg is not None},
            'laughter': [], 'applause': [], 'music': [], 'overlap': []}

    # sound events (YAMNet)
    if y_times:
        musical = [m >= MUSIC_MIN for m in music]
        cues['music'] = spans(y_times, [m >= MUSIC_SPAN for m in music], win, MUSIC_SPAN_S, gap=1.0)
        # laughter: merged frames at the director's level, kept when one frame is sure enough and
        # the laugh lasts long enough; never inside music
        on = [s >= speakers.LAUGH_MIN and not mu for s, mu in zip(laugh, musical)]
        for a, b in spans(y_times, on, win, LAUGH_MIN_S, gap=0.0):
            peak = max(s for t, s in zip(y_times, laugh) if a <= t < b)
            if peak >= LAUGH_MARK:
                # the frames overlap (0.96 s windows every 0.48 s): trim the last half window
                cues['laughter'].append([a, round(max(a + 0.48, b - 0.48), 2), round(peak, 2)])
        on = [s >= APPLAUSE_MIN and not mu for s, mu in zip(clap, musical)]
        cues['applause'] = spans(y_times, on, win, APPLAUSE_MIN_S, gap=0.5)
        # game sound bursts: [start, end, kind, peak], the strongest few per 10 minutes
        bursts = []
        for k, vals in burst.items():
            for a, b in spans(y_times, [x >= BURST_MIN for x in vals], win, 0.4, gap=BURST_GAP):
                peak = max(x for t, x in zip(y_times, vals) if a <= t < b)
                bursts.append([a, round(max(a + 0.48, b - 0.48), 2), k, round(peak, 2)])
        bursts.sort()
        one = []                       # an explosion and gunfire at the same moment: one hint, the surer kind
        for bu in bursts:
            if one and bu[0] <= one[-1][1]:
                if bu[3] > one[-1][3]:
                    one[-1] = [one[-1][0], max(one[-1][1], bu[1]), bu[2], bu[3]]
                else:
                    one[-1][1] = max(one[-1][1], bu[1])
            else:
                one.append(bu)
        from .hints import rare
        cues['bursts'] = rare(one, lambda r: r[3])

    # two people talking at once, and turn switches (pyannote powerset classes 4-6 = two speakers)
    overlap_s, turns = [0.0] * n_steps, [0] * n_steps
    if seg_wins:
        both = []
        need = int(0.5 / SEG_FRAME)
        for base, cls in seg_wins:
            on = cls >= 4
            k = int(base // STEP)
            if k < n_steps:
                overlap_s[k] += float(on.sum()) * SEG_FRAME
            # spans of both talking at once, in source seconds
            edges = np.flatnonzero(np.diff(np.r_[0, on.astype(np.int8), 0]))
            for a, b in zip(edges[::2], edges[1::2]):
                both.append([base + a * SEG_FRAME, base + b * SEG_FRAME])
            # turns: the single active speaker changes, each side lasting at least 0.5 s (speaker
            # ids are local to each 10 s window, so changes are only counted inside a window)
            run_cls, run_len, last = None, 0, None
            for c in cls:
                if c not in (1, 2, 3):
                    continue
                if c == run_cls:
                    run_len += 1
                else:
                    run_cls, run_len = c, 1
                if run_len == need:
                    if last is not None and last != c and k < n_steps:
                        turns[k] += 1
                    last = c
        merged = []
        for a, b in both:
            if merged and a <= merged[-1][1] + 0.3:
                merged[-1][1] = max(merged[-1][1], b)
            else:
                merged.append([a, b])
        cues['overlap'] = [[round(a, 2), round(b, 2)] for a, b in merged if b - a >= OVERLAP_MIN_S]

    # loudness of speech and speed of talking, per step, as z-scores within this video
    speech, count = word_steps(words, n_steps)
    wspans = [(w['s'], w['e']) for w in words]
    j, loud_db = 0, []
    for k in range(n_steps):
        vals = []
        for t, db in loud[k]:
            while j < len(wspans) and wspans[j][1] < t:
                j += 1
            if j < len(wspans) and wspans[j][0] < t + 0.5:          # a word is spoken in this frame
                vals.append(db)
        loud_db.append(float(np.mean(vals)) if len(vals) >= 4 else None)
    rate = [count[k] / speech[k] if speech[k] >= 3.0 else None for k in range(n_steps)]
    laugh_s = [0.0] * n_steps
    for a, b, _ in cues['laughter']:
        t = a
        while t < b:
            k = int(t // STEP)
            if k >= n_steps:
                break
            nxt = min(b, (k + 1) * STEP)
            laugh_s[k] += nxt - t
            t = nxt
    cues['steps'] = {'loud_z': zscores(loud_db), 'rate_z': zscores(rate),
                     'overlap_s': [round(v, 1) for v in overlap_s], 'turns': turns,
                     'laugh_s': [round(v, 1) for v in laugh_s],
                     'speech_s': [round(v, 1) for v in speech]}
    cues['lively'] = lively_spots(cues)
    cues['seconds'] = round(time.time() - t_start, 1)
    save_json(pdir / 'transcript' / 'cues.json', cues)
    if not quiet:
        got = [k for k in ('yamnet', 'segmentation') if cues['models'][k]]
        print(f"-> sound cues in {cues['seconds']:.0f}s ({', '.join(got) or 'no sound models'}): "
              f"{len(cues['laughter'])} laughs, {len(cues['applause'])} applause, "
              f"{len(cues['overlap'])} times both talk at once, {len(cues.get('bursts', []))} game sound bursts, "
              f"{len(cues['lively'])} lively spots")
    return cues


def _ranks(vals):
    """Average ranks (1 = lowest); None counts as the lowest."""
    xs = [(-1e9 if v is None else v) for v in vals]
    order = sorted(range(len(xs)), key=lambda i: xs[i])
    r = [0.0] * len(xs)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and xs[order[j + 1]] == xs[order[i]]:
            j += 1
        for k in range(i, j + 1):
            r[order[k]] = (i + j) / 2 + 1
        i = j + 1
    return r


def lively_spots(cues, share=0.10, max_spots=40):
    """The video's liveliest 30 s windows, by a simple rank sum of laughter, both-talk-at-once and
    turn switches, loudness and talking speed. Each spot needs at least one clear reason, and a
    spot is mostly speech (never a music stretch)."""
    st = cues['steps']
    n = len(st['speech_s'])
    w = int(WINDOW // STEP)
    if n < w:
        return []

    def mean(xs):
        xs = [x for x in xs if x is not None]
        return sum(xs) / len(xs) if xs else None

    wins = []
    for i in range(0, n - w + 1):
        sl = slice(i, i + w)
        wins.append({'i': i, 'laugh': sum(st['laugh_s'][sl]),
                     'talk': sum(st['overlap_s'][sl]) + 0.5 * sum(st['turns'][sl]),
                     'loud': mean(st['loud_z'][sl]), 'rate': mean(st['rate_z'][sl]),
                     'speech': sum(st['speech_s'][sl]),
                     'overlap': sum(st['overlap_s'][sl]), 'turns': sum(st['turns'][sl])})
    score = [sum(x) for x in zip(*(_ranks([v[k] for v in wins]) for k in ('laugh', 'talk', 'loud', 'rate')))]
    music = cues.get('music') or []
    picked, taken = [], set()
    want = max(1, min(max_spots, round(share * n / w)))
    for idx in sorted(range(len(wins)), key=lambda i: -score[i]):
        v = wins[idx]
        a, b = v['i'] * STEP, (v['i'] + w) * STEP
        if v['speech'] < 0.5 * WINDOW or any(min(b, mb) - max(a, ma) > WINDOW / 2 for ma, mb in music):
            continue
        if any(k in taken for k in range(v['i'], v['i'] + w)):
            continue
        why = []
        if v['laugh'] >= 1.0:
            why.append(f"laughter {v['laugh']:.0f} s")
        if v['overlap'] >= 1.5:
            why.append(f"both talk at once {v['overlap']:.0f} s")
        if v['turns'] >= 4:
            why.append(f"quick back-and-forth ({v['turns']} turns)")
        if v['loud'] is not None and v['loud'] >= 1.0:
            why.append('louder than usual')
        if v['rate'] is not None and v['rate'] >= 1.0:
            why.append('faster than usual')
        if not why:
            continue
        picked.append({'start': round(a, 1), 'end': round(min(b, cues['duration']), 1), 'why': ', '.join(why)})
        taken.update(range(v['i'], v['i'] + w))
        if len(picked) >= want:
            break
    return sorted(picked, key=lambda p: p['start'])


def load(pdir):
    """The project's cues if they are up to date, else None."""
    c = load_json(pdir / 'transcript' / 'cues.json')
    return c if c and c.get('v') == CUES_V else None


def ensure(pdir, quiet=False):
    """Cues for the project, measuring them first if they're missing or out of date."""
    return load(pdir) or scan(pdir, quiet=quiet)


def spots_in(cues, a, b):
    """Lively spots that overlap [a, b]."""
    return [s for s in (cues or {}).get('lively', []) if s['end'] > a and s['start'] < b]


def spots_line(spots):
    return ' · '.join(f"{fmt_ts(s['start']).split('.')[0]} ({s['why']})" for s in spots)


def markers(cues, a, b):
    """Sound events inside [a, b]: [(time, text)] such as (612.3, '[laughter ~2 s]'). Neutral facts
    for the critic's clip text."""
    if not cues:
        return []
    out = []
    for s, e, _ in cues.get('laughter', []):
        if a <= s < b:
            out.append((s, f'[laughter ~{max(1, round(e - s))} s]'))
    for s, e in cues.get('applause', []):
        if a <= s < b:
            out.append((s, '[applause]'))
    for s, e in cues.get('overlap', []):
        if a <= s < b and e - s >= 1.5:
            out.append((s, '[both talk at once]'))
    return sorted(out)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('project')
    a = ap.parse_args()
    pdir = project_dir(a.project)
    cues = scan(pdir)
    if cues is None:
        die(f'no audio or transcript in {pdir}: run `python run.py fetch` first')
    for s in cues['lively']:
        print(f"   {fmt_ts(s['start']).split('.')[0]:>8}  {s['why']}")


if __name__ == '__main__':
    main()
