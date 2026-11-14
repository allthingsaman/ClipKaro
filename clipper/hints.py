"""Hints for Claude: facts about HOW something is said and shown, written next to the words it reads.

    python run.py hints <project>        (fetch runs it by itself; this is for older videos)

Some of the best moments live in a laugh, a shout or an explosion, not in the words. So the lines
Claude reads (transcript.txt, the parts of a long video, the critic's clip texts) carry short notes:

    [12.40-15.10] (other voice) You call it whatever you want to call it.      a game character, not the streamer
    [15.20-18.00] bhai ye kya ho gaya [voice raised]                            higher and louder than usual
    [18.10-21.40] arre arre arre [shouting] [explosion]                          (gameplay)
    [30.00-33.00] tu bhi na yaar [laughter ~2 s]
    [41.00-44.20] chalo chalo nikal [big action on screen ~4 s]                  (gameplay)

They are measurements, never verdicts: they show where to look, the words decide. A hint never makes a
clip by itself, and no hint does not mean a moment is weak (most good moments have none). Kept rare on
purpose: only the clearest few per 10 minutes, so they stay worth a look.

Where they come from (research, Nov 2026; docs/architecture.md):
- laughter, applause (and cheering), game sound bursts (explosion, gunfire, crash): YAMNet in sound.py;
- a raised voice: the line's pitch (SwiftF0, MIT, ~40 s of CPU per hour) and loudness against the same
  speaker's own normal over the minutes around it (voices.py tells the speakers apart). A shout is
  about +9 to +16 semitones and +18 dB over normal speech (Raitio et al. 2013); "voice raised" needs
  +4 semitones and +6 dB, "shouting" +8 and +10. AudioSet's own "Shout" and "Yell" labels are right only
  about half the time, so they are not used;
- big action on screen (gameplay only): motion.py;
- (other voice): voices.py, gameplay and live streams only.

Saves transcript/hints.json (the raised-voice lines); notes() puts everything together per line.
"""
import argparse
import math
import re
import time

import numpy as np

from .common import die, load_json, project_dir, save_json

HINTS_V = 1
SR = 16000
RAISED_ST, RAISED_DB = 4.0, 6.0      # "voice raised": at least this much higher (semitones) and louder (dB)
SHOUT_ST, SHOUT_DB = 8.0, 10.0       # "shouting"
MAX_ST = 14.0                        # more than this over normal is a pitch-tracker slip, not a voice
# Measured on the test videos (Nov 2026): podcast sound is compressed (Khan Sir's loudest 1 % of lines are
# only 1.6 dB over his normal), and lines that are only higher are mostly questions; so both higher AND
# louder are needed, and a podcast rarely gets this hint, which is right: a hint must be sure.
BASE_WINDOW = 300.0                  # the speaker's normal: their lines within +-150 s ...
BASE_MIN_LINES = 8                   # ... at least this many, else all their lines in the video
MIN_VOICED = 0.5                     # seconds of voiced speech a line needs to be judged
PER_10_MIN = 6                       # at most this many raised-voice hints per 10 minutes (the clearest)
HINT_RE = re.compile(r'\[(?:voice raised|shouting|laughter[^\]]*|applause|explosion|gunfire|crash|'
                     r'big action on screen[^\]]*|both talk at once)\]|\(other voice\)')

READER_NOTE = ('Notes in [brackets] like [laughter ~2 s], [voice raised], [shouting], [explosion] or '
               '[big action on screen], and "(other voice)" before a line, are measurements of the sound and '
               'picture, not words: never quote them. They show where to look; the words decide. A note never '
               'makes a clip by itself, and no note does not mean a moment is weak.')


def strip_hints(text):
    """The text without hint notes (for matching quotes against the words)."""
    return HINT_RE.sub(' ', str(text or ''))


# ---------- a raised voice ----------

def pitch_track(audio):
    """(times, pitch in semitones over 100 Hz or nan, loudness dB) every 16 ms, for the whole audio."""
    from swift_f0 import SwiftF0
    det = SwiftF0(threads=1)
    ts, st, db = [], [], []
    block = 60 * SR
    for i in range(0, len(audio), block):
        x = audio[i:i + block]
        if len(x) < SR // 4:
            break
        r = det.detect(x, SR)
        voiced = r.confidence >= 0.5
        ts.append(r.timestamps + i / SR)
        st.append(np.where(voiced, 12 * np.log2(np.maximum(r.pitch_hz, 1.0) / 100.0), np.nan))
        db.append(r.loudness_db)
    if not ts:
        return np.zeros(0), np.zeros(0), np.zeros(0)
    return np.concatenate(ts), np.concatenate(st), np.concatenate(db)


def line_levels(track, words, lines):
    """Per line: (median pitch in semitones, loud level dB) over its words, or None."""
    ts, st, db = track
    out = []
    for ln in lines:
        if 'i0' not in ln or not len(ts):
            out.append(None)
            continue
        mask = np.zeros(len(ts), bool)
        for w in words[ln['i0']:ln['i1'] + 1]:
            a, b = np.searchsorted(ts, [w['s'], w['e']])
            mask[a:b] = True
        voiced = mask & ~np.isnan(st)
        if voiced.sum() * 0.016 < MIN_VOICED:
            out.append(None)
            continue
        out.append((float(np.median(st[voiced])), float(np.percentile(db[mask], 90))))
    return out


def raised_lines(levels, lines, voice_rows, busy, judge=lambda i: True):
    """[[start, end, 'voice raised' | 'shouting', +semitones, +dB]] for lines clearly higher and louder
    than the same voice's lines around them. `busy(a, b)` is True during laughter or cross-talk; only
    lines with judge(i) are judged (a known voice, clear words; in gameplay only the streamer's)."""
    by_voice = {}
    for i, (lv, row) in enumerate(zip(levels, voice_rows or [None] * len(levels))):
        if lv is not None and 's' in lines[i] and judge(i):
            by_voice.setdefault(row[2] if row else None, []).append(i)
    out = []
    for v, idx in by_voice.items():
        starts = np.array([lines[i]['s'] for i in idx])
        P = np.array([levels[i][0] for i in idx])
        L = np.array([levels[i][1] for i in idx])
        for k, i in enumerate(idx):
            near = np.abs(starts - starts[k]) <= BASE_WINDOW / 2
            near[k] = False
            if near.sum() < BASE_MIN_LINES:
                near = np.ones(len(idx), bool)
                near[k] = False
            if near.sum() < BASE_MIN_LINES:
                continue
            d_st, d_db = P[k] - np.median(P[near]), L[k] - np.median(L[near])
            if d_st > MAX_ST:                 # an octave slip of the pitch tracker (game sound), not a voice
                continue
            if d_st >= RAISED_ST and d_db >= RAISED_DB and not busy(lines[i]['s'], lines[i]['e']):
                kind = 'shouting' if d_st >= SHOUT_ST and d_db >= SHOUT_DB else 'voice raised'
                out.append([round(lines[i]['s'], 2), round(lines[i]['e'], 2), kind, round(d_st, 1), round(d_db, 1)])
    return rare(sorted(out), lambda r: r[3] / RAISED_ST + r[4] / RAISED_DB)


def rare(items, strength, per_10=PER_10_MIN):
    """At most per_10 items in any 10-minute block (the strongest), so hints stay worth a look."""
    blocks = {}
    for it in items:
        blocks.setdefault(int(it[0] // 600), []).append(it)
    keep = []
    for b in blocks.values():
        keep += sorted(b, key=strength, reverse=True)[:per_10]
    return sorted(keep)


# ---------- all the notes of a line ----------

def _overlaps(spans, a, b):
    return [sp for sp in spans if sp[0] < b and sp[1] > a]


def notes(pdir, project=None):
    """{round(line start, 2): (prefix or '', [notes after the line])} from what was measured."""
    from . import sound, voices
    from .common import settings
    from .kind import is_irregular
    if not settings().get('hints', True):          # the way back: the plain transcript, as in v1.1
        return {}
    project = project or load_json(pdir / 'project.json', {}) or {}
    lines = load_json(pdir / 'transcript' / 'sentences.json') or []
    cues = sound.load(pdir) or {}
    h = load_json(pdir / 'transcript' / 'hints.json') or {}
    mot = load_json(pdir / 'transcript' / 'motion.json') or {}
    v = voices.load(pdir) if is_irregular(project) else None
    other = voices.other_lines(v)
    out = {}
    for i, ln in enumerate(lines):
        if 's' not in ln:
            continue
        a, b = ln['s'], ln['e']
        post = []
        for s, e, *_ in cues.get('laughter', []):
            if a <= s < b:
                post.append(f'[laughter ~{max(1, round(e - s))} s]')
        for s, e in cues.get('applause', []):
            if a <= s < b:
                post.append('[applause]')
        for s, e, kind, *_ in h.get('raised', []):
            if abs(s - a) < 0.01:
                post.append(f'[{kind}]')
        for s, e, kind, *_ in cues.get('bursts', []):
            if a <= s < b:
                post.append(f'[{kind}]')
        for s, e, *_ in mot.get('action', []):
            if a <= s < b:
                post.append(f'[big action on screen ~{max(1, round(e - s))} s]')
        pre = '(other voice)' if i in other else ''
        if pre or post:
            out[round(a, 2)] = (pre, list(dict.fromkeys(post)))
    return out


def line_text(ln, nt=None):
    """A transcript line as Claude reads it, with its notes."""
    if 'marker' in ln:
        return ln['marker']
    pre, post = (nt or {}).get(round(ln['s'], 2), ('', []))
    return f"[{ln['s']:.2f}-{ln['e']:.2f}] " + (pre + ' ' if pre else '') + ln['text'] + \
        (' ' + ' '.join(post) if post else '')


# ---------- running it ----------

def scan(pdir, quiet=False):
    """Measure the raised-voice lines (and the voices and motion they need) and save hints.json."""
    from . import motion, sound, voices
    from .kind import is_irregular
    project = load_json(pdir / 'project.json', {}) or {}
    wav = pdir / 'source' / 'audio16k.wav'
    words = load_json(pdir / 'transcript' / 'words.json')
    lines = load_json(pdir / 'transcript' / 'sentences.json')
    if not wav.exists() or not words or not lines:
        return None
    t = time.time()
    v = voices.ensure(pdir, quiet=quiet)
    cues = sound.load(pdir) or {}
    busy_spans = [x[:2] for x in cues.get('laughter', [])] + [x[:2] for x in cues.get('overlap', [])]
    import soundfile as sf
    audio, _ = sf.read(str(wav), dtype='float32')
    try:
        track = pitch_track(audio)
    except ImportError:
        if not quiet:
            print('   (raised-voice hints skipped: swift-f0 is not installed; run python install.py)')
        track = None
    raised = []
    if track is not None:
        levels = line_levels(track, words, lines)
        rows = (v or {}).get('lines') or [None] * len(lines)
        game = is_irregular(project)

        def judge(i):
            # a voice that was recognised, mostly clear words (not game voices or noise Whisper guessed at),
            # and in gameplay only the streamer: a game character's shout is the game, not a reaction
            ln, row = lines[i], rows[i]
            if not row or row[2] is None or (game and row[2] != v['main']):
                return False
            ws = words[ln['i0']:ln['i1'] + 1]
            return sum(bool(w.get('unsure')) for w in ws) <= 0.3 * len(ws)
        raised = raised_lines(levels, lines, rows, lambda a, b: bool(_overlaps(busy_spans, a, b)), judge)
    h = {'v': HINTS_V, 'raised': raised, 'seconds': round(time.time() - t, 1)}
    save_json(pdir / 'transcript' / 'hints.json', h)
    if is_irregular(project):
        motion.ensure(pdir, quiet=quiet)
    if not quiet:
        n_sh = sum(r[2] == 'shouting' for r in raised)
        print(f"-> delivery hints in {h['seconds']:.0f}s: {len(raised) - n_sh} raised voice(s), {n_sh} shout(s)")
    return h


def ensure(pdir, quiet=False):
    from .common import settings
    if not settings().get('hints', True):
        return None
    h = load_json(pdir / 'transcript' / 'hints.json')
    return h if h and h.get('v') == HINTS_V else scan(pdir, quiet=quiet)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('project')
    a = ap.parse_args()
    pdir = project_dir(a.project)
    from . import sound
    from .fetch import render_transcript
    if sound.load(pdir) is None:
        sound.scan(pdir)
    if scan(pdir) is None:
        die(f'no audio or transcript in {pdir}: run `python run.py fetch` first')
    project = load_json(pdir / 'project.json', {}) or {}
    render_transcript(pdir, project, load_json(pdir / 'transcript' / 'sentences.json') or [])
    nt = notes(pdir, project)
    n = sum(len(p) for _, p in nt.values()) + sum(1 for pre, _ in nt.values() if pre)
    print(f'-> transcript.txt now carries {n} note(s) on {len(nt)} line(s)')


if __name__ == '__main__':
    main()
