"""Step 3: cut the clips Claude picked (clips.json) into vertical 1080x1920 shorts.

    python run.py cut <project>               # all clips
    python run.py cut <project> --clips 1,3   # only some
    python run.py cut <project> --horizontal  # keep 16:9 (no reframe)
    python run.py cut <project> --layout facecam   # gameplay on top, webcam overlay below (auto-detected)
    python run.py cut <project> --layout crop      # normal framing even if a facecam is found

Downloads the video the first time (max 1080p). Snaps every range to whole words so nothing is
cut mid-word, reframes each camera shot around the speaker's face, and writes
clips/NN-title.mp4 plus clips/NN-title.json (timing, words, focus point) used by `edit`.
"""
import argparse
import math
import re
import subprocess
import sys
from pathlib import Path

from . import facecam as fclib
from .common import (H, JUMP_FLASH, W, die, out_fps, ffmpeg, fmt_ts, is_sentence_end, load_json, norm_token, probe, project_dir, save_json,
                     open_video, overlap_mode, overlap_problem, ROOT, settings, slugify)
from .reframe import analyse_range, crop_width, crop_x, plan_shots, shot_filter, split_box

PAD_IN, PAD_OUT = 0.12, 0.30
MIN_PIECE = 0.25          # a framing boundary never leaves a sliver shorter than this
QUIET_GAP_S = 8.0         # live streams / gameplay: `--check` points out a silence this long inside a clip
HOWS = ('full', 'left', 'right', 'center', 'split', 'middle')


def framing_spans(clip):
    """The clip's framing overrides as [(a, b, how)] in source seconds. `show_full` spans mean "full";
    `framing` entries are [a, b, how], how = "full" | "left" | "right" | "center" | 0.0-1.0 (the crop
    centre as a share of the frame width)."""
    spans = [(float(a), float(b), 'full') for a, b in clip.get('show_full') or []]
    for item in clip.get('framing') or []:
        a, b, how = item
        if not (how in HOWS or (isinstance(how, (int, float)) and 0 <= how <= 1)):
            die(f'clip {clip.get("id")}: framing "{how}" must be one of {", ".join(HOWS)} or a number 0-1')
        spans.append((float(a), float(b), how))
    return spans


def _framed(sh, how, src_w, src_h):
    """One shot piece re-framed the way an override asks."""
    if how == 'full':
        return {**sh, 'mode': 'fit', 'x0': 0, 'focus': [round(W / 2), round(H * 0.42)]}
    if how == 'split' and len(sh.get('group') or []) >= 3:      # three people (v2.13): all stacked, left to right
        boxes = [split_box(f, src_w, src_h, rows=len(sh['group'])) for f in sh['group']]
        return {**sh, 'mode': 'split', 'x0': 0, 'panels': boxes, 'top': boxes[0], 'bottom': boxes[-1],
                'focus': [round(W / 2), round(H / 2)]}
    if how == 'split':                  # both people stacked: the one who talks most on top
        faces = sh.get('pair') or sorted(sh.get('faces') or [], key=lambda f: -f[2] * 1.0)[:2]
        if len(faces) < 2:
            return _framed(sh, 'full', src_w, src_h)
        left, right = sorted(faces, key=lambda f: f[0])
        # people sitting either side of the middle (a side-by-side composite, or a wide two-shot):
        # each half stays on its own side, so no strip of the other camera shows at its edge
        mid = src_w / 2 if left[0] < 0.5 < right[0] else None
        boxes = {'L': split_box(left, src_w, src_h, 0, mid) if mid else split_box(left, src_w, src_h),
                 'R': split_box(right, src_w, src_h, mid, src_w) if mid else split_box(right, src_w, src_h)}
        up, down = ('R', 'L') if sh.get('star') == 'R' else ('L', 'R')
        return {**sh, 'mode': 'split', 'x0': 0, 'top': boxes[up], 'bottom': boxes[down],
                'focus': [round(W / 2), round(H / 2)]}
    # the people of a group shot, the two of a two-person shot (seen together), else every subject found
    subjects = [f[0] for f in sh['group']] if len(sh.get('group') or []) >= 3 else \
        [f[0] for f in sh['pair']] if sh.get('pair') else (sh.get('subjects') or ([sh['face'][0]] if sh.get('face') else []))
    if how == 'middle':                 # the person in the middle of a group (v2.13), else the centre
        cx = sorted(subjects)[len(subjects) // 2] if len(subjects) >= 3 else 0.5
    elif how == 'left':
        cx = min(subjects) if subjects else 0.0       # the face on the left, else the left edge
    elif how == 'right':
        cx = max(subjects) if subjects else 1.0       # the face on the right, else the right edge
    elif how == 'center':
        cx = 0.5
    else:
        cx = float(how)
    cy = sh['face'][1] if sh.get('face') else 0.42
    cw = crop_width(src_w, src_h)
    x0 = crop_x(cx, src_w, src_h)
    return {**sh, 'mode': 'crop', 'x0': x0, 'focus': [round((cx * src_w - x0) / cw * W), round(cy * H)]}


def apply_framing(shots, spans, start, dur, src_w, src_h):
    """Apply the AI's (or the user's) framing choices for parts of a clip: show the whole frame
    (blurred-background layout) where what's shown or talked about lies outside the 9:16 crop, or
    pick the left / right face or the centre where the automatic choice is wrong. `spans` are
    [(a, b, how)] in source seconds, like `ranges`; `shots` are relative to `start` and get split at
    the span edges. Vertical sources are left as they are."""
    rel = [(max(0.0, a - start), min(dur, b - start), how) for a, b, how in spans or []
           if b - start > 0 and a - start < dur]
    rel = [r for r in rel if r[1] - r[0] >= MIN_PIECE]
    if not rel:
        return shots
    out = []
    for sh in shots:
        if sh['mode'] not in ('crop', 'fit', 'split'):
            out.append(sh)
            continue
        cuts = sorted({sh['a'], sh['b'], *[x for a, b, _ in rel for x in (a, b) if sh['a'] < x < sh['b']]})
        for a, b in zip(cuts, cuts[1:]):
            if b - a < MIN_PIECE and out and out[-1]['b'] == a:     # merge a sliver into the previous piece
                out[-1] = {**out[-1], 'b': b}
                continue
            mid = (a + b) / 2
            how = next((h for fa, fb, h in reversed(rel) if fa <= mid <= fb), None)   # the last one listed wins
            piece = {**sh, 'a': a, 'b': b}
            out.append(_framed(piece, how, src_w, src_h) if how is not None else piece)
    return out


def ensure_video(pdir, project):
    if project.get('video') and Path(project['video']).exists():
        return Path(project['video'])
    if project.get('kind') == 'local':
        die(f"the original video file is gone: {project.get('video')}\n"
            'Put it back at that path, or run fetch again with its new path.')
    from .fetch import download_video, video_file
    return video_file(pdir) or download_video(pdir, project)


def snap_range(s, e, words, pad_in=PAD_IN, pad_out=PAD_OUT):
    """Expand/shrink [s, e] to whole words and add small natural handles."""
    inside = [i for i, w in enumerate(words) if w['e'] > s + 0.05 and w['s'] < e - 0.05]
    if not inside:
        return None
    i0, i1 = inside[0], inside[-1]
    start = words[i0]['s'] - pad_in
    if i0 > 0:
        start = max(start, words[i0 - 1]['e'] + 0.02)
    end = words[i1]['e'] + pad_out
    if i1 + 1 < len(words):
        end = min(end, max(words[i1]['e'] + 0.08, words[i1 + 1]['s'] - 0.04))
    return max(0.0, start), end, i0, i1


# ---------- jump cuts: long pauses and filler sounds inside a clip are cut out ----------
# Shorts editors and silence-cutting tools keep about 0.1-0.2 s around a cut and leave gaps under
# ~0.25 s alone, or word endings get clipped. A pause of JUMP_PAUSE or more keeps JUMP_PAD_OUT after the
# word before it and JUMP_PAD_IN before the next one (~0.22 s of quiet). Never across a laugh or
# applause; in gameplay and live streams only pauses up to GAME_PAUSE (a longer one may be the action).
JUMP_PAUSE = 0.55
JUMP_PAD_IN, JUMP_PAD_OUT = 0.08, 0.14
JUMP_MIN_PIECE = 0.7       # a piece between two cuts never shorter than this (no flicker)
GAME_PAUSE = 2.0
EVENT_HOLD = 10.0          # an event clip (frame sheets, v2.7): no pause cut in the event's first seconds (5-9 s on a GTA stream)
FILLERS = {'um', 'uh', 'umm', 'uhh', 'uhm', 'hmm', 'hm', 'mm', 'er', 'erm', 'ah',
           'उम्म', 'उम', 'अं', 'हम्म', 'उह', 'उंह'}


def jump_pieces(s, e, words, quiet_ok, max_pause=None):
    """[s, e] split at its long pauses and filler sounds: [[a, b], ...] in source seconds."""
    snapped = snap_range(s, e, words)
    if not snapped:
        return [[s, e]]
    _, _, i0, i1 = snapped
    seg = words[i0:i1 + 1]
    keep = [w for w in seg if norm_token(w['w']) not in FILLERS]
    if len(keep) < 2:
        return [[s, e]]
    pieces = [[s, None]]
    said = keep[0]['e']                          # the latest end of any word so far: a stretched word that
    for a, b in zip(keep, keep[1:]):             # runs past the next one is never cut while still being said
        said = max(said, a['e'])
        fill = [w for w in seg if a['s'] < w['s'] < b['s'] and norm_token(w['w']) in FILLERS]
        gap = b['s'] - said
        if not fill and (gap < JUMP_PAUSE or (max_pause and gap > max_pause)):
            continue
        c0 = max(said + 0.02, min(said + JUMP_PAD_OUT, fill[0]['s'] - 0.02 if fill else 1e9))
        c1 = min(b['s'] - 0.02, max(b['s'] - JUMP_PAD_IN, fill[-1]['e'] + 0.02 if fill else -1e9))
        if c1 - c0 < 0.2 or not quiet_ok(c0, c1):
            continue
        pieces[-1][1] = round(c0, 3)
        pieces.append([round(c1, 3), None])
    pieces[-1][1] = e
    out = [pieces[0]]
    for pc in pieces[1:]:                        # a sliver between two cuts: keep the pause instead
        if out[-1][1] - out[-1][0] < JUMP_MIN_PIECE or pc[1] - pc[0] < JUMP_MIN_PIECE:
            out[-1][1] = pc[1]
        else:
            out.append(pc)
    return out


# ---------- gameplay: a quiet second where something happens on screen stays ----------
# Pause cutting goes by the sound. In gameplay the cause of a reaction often happens in a quiet second
# (a takedown, a crash, a fall) and the shout comes after: clip 143 of the GTA stream lost a police
# takedown that way (the picture changed about twice as much as usual in that second, the sound stayed
# low). So the picture change is measured MOTION_FPS times a second on a small grey copy, the webcam box
# left out, and a pause whose picture changes MOTION_RATIO times the clip's usual change (its median) or
# more, and at least MOTION_MIN, for at least half a second (MOTION_LASTS readings), is not cut. From the
# pixels a takedown and a fast camera swing look alike (cancelling the camera's movement didn't separate
# them on the GTA stream); both stay, and a jump in the middle of a camera swing looks like a glitch
# anyway. On that stream: 117 of 575 pauses stay (107 of 459 s), 76 of 160 clips 1.4 s longer on average.
# Calm stretches, menus and talking stay cut as before.
MOTION_FPS = 4
MOTION_SIZE = (160, 90)
MOTION_RATIO = 1.5
MOTION_MIN = 8.0           # grey levels (0-255): a near-still scene never counts as action
MOTION_LASTS = 2           # readings (1/MOTION_FPS s each): a single flicker is not action


def picture_change(video, s, e, cam=None, src=(1920, 1080)):
    """[(t0, t1, change)] for [s, e] in source seconds: the mean grey-level change between frames
    1/MOTION_FPS s apart, the webcam box (source pixels {'x','y','w','h'}) left out."""
    import numpy as np
    w, h = MOTION_SIZE
    r = subprocess.run(['ffmpeg', '-v', 'error', '-ss', f'{s:.3f}', '-t', f'{e - s:.3f}', '-i', str(video),
                        '-vf', f'fps={MOTION_FPS},scale={w}:{h},format=gray', '-an', '-f', 'rawvideo', '-'],
                       capture_output=True)
    f = np.frombuffer(r.stdout, np.uint8)
    if f.size < 2 * w * h:
        return []
    f = f[:f.size // (w * h) * w * h].reshape(-1, h, w).astype(np.float32)
    keep = np.ones((h, w), bool)
    if cam:
        sx, sy = w / src[0], h / src[1]
        keep[max(0, int(cam['y'] * sy) - 1):int((cam['y'] + cam['h']) * sy) + 2,
             max(0, int(cam['x'] * sx) - 1):int((cam['x'] + cam['w']) * sx) + 2] = False
    step = 1.0 / MOTION_FPS
    return [(round(s + i * step, 3), round(s + (i + 1) * step, 3), float(np.abs(f[i + 1] - f[i])[keep].mean()))
            for i in range(len(f) - 1)]


def action_check(clip, video, cam=None, src=(1920, 1080)):
    """A function (a, b) -> True when the picture changes a lot in [a, b] (gameplay: that pause stays)."""
    import statistics
    rows = [r for s, e in clip['ranges'] for r in picture_change(video, s, e, cam, src)]
    if len(rows) < 8:
        return lambda a, b: False
    usual = statistics.median(r[2] for r in rows)
    level = max(MOTION_MIN, usual * MOTION_RATIO)

    def moving(a, b):
        inside = [c for t0, t1, c in rows if t0 < b and a < t1]
        return bool(inside) and sum(c >= level for c in inside) >= min(MOTION_LASTS, len(inside))
    moving.level, moving.usual = level, usual
    return moving


# v2.8, the smarter check: a camera swing also changes the picture a lot, so in gameplay (the camera always
# moves) the picture alone kept too many pauses (124 on the GTA stream). A pause now stays only when the
# picture changes a lot AND something shows an event happened: a game sound burst (explosion, gunfire, crash)
# around it, or a reaction right after it: a laugh, a raised voice or shout, a reaction word ("ye kya ho
# gaya", "bhaag") or an exclamation ("arre", "oye"; even when careful listening marked its spelling unsure),
# or anyone's voice suddenly louder than the talk around it (a friend's shout, which the raised-voice hints
# don't mark). A swing with none of these is cut like any pause. No Claude usage.
EVENT_AROUND = 0.5         # a game sound this close to the pause counts
EVENT_AFTER = 2.5          # a reaction starting this soon after the pause counts
LOUD_AFTER_S = 1.5         # ... or a voice this soon after it that is
LOUD_AFTER_DB = 6.0        # this much louder than the words around it: a shout. Measured on the GTA stream, 46 %
                           # of ordinary pauses in the clips reach +3 dB (excited talk), only 14 % reach +6 dB
LOUD_REF_S = 20.0          # the words this far around the pause are "the talk around it"
EXCLAIM = {'arre', 'are', 'arey', 'arrey', 'oye', 'oy', 'abe', 'abey', 'oh', 'ohh', 'ooh', 'whoa', 'woah', 'ruk',
           'ruko', 'अरे', 'ओए', 'अबे', 'ओह', 'रुक', 'रुको'}


def _rms_db(w, a, b):
    import numpy as np
    sr = w.getframerate()
    w.setpos(max(0, int(a * sr)))
    x = np.frombuffer(w.readframes(max(1, int((b - a) * sr))), np.int16).astype(np.float32) / 32768.0
    return 20 * math.log10(float(np.sqrt((x ** 2).mean())) + 1e-9) if x.size else -120.0


def event_signs(pdir, words, lines):
    """A function (a, b) -> True when a game sound burst falls around [a, b] or a reaction starts right after it."""
    from . import sound
    from .watch import reaction_word
    cues = sound.load(pdir) or {}
    hints = load_json(pdir / 'transcript' / 'hints.json') or {}
    bursts = [(x, y) for x, y, *_ in cues.get('bursts', [])]
    starts = [x for x, *_ in hints.get('raised', [])] + [x for x, *_ in cues.get('laughter', [])]
    for ln in lines or []:
        if 'i0' in ln:
            first = words[ln['i0']:ln['i0'] + 4]            # unsure words too: the sound is there, only the spelling isn't
            plain = [norm_token(w['w']) for w in first]
            if first and (reaction_word(' '.join(plain)) or plain[0] in EXCLAIM):
                starts.append(first[0]['s'])
    import bisect
    import statistics
    import wave
    wav = pdir / 'source' / 'audio16k.wav'
    times = [w['s'] for w in words]

    def louder_after(a, b):
        if not wav.exists():
            return False
        lo, hi = bisect.bisect_left(times, a - LOUD_REF_S), bisect.bisect_right(times, b + LOUD_REF_S)
        near = [w for w in words[lo:hi] if w['e'] - w['s'] > 0.1]
        if len(near) < 5:
            return False
        with wave.open(str(wav)) as f:
            ref = statistics.median(_rms_db(f, w['s'], w['e']) for w in near)
            peak = max(_rms_db(f, t, t + 0.5) for t in (b, b + 0.4, b + 0.8, b + LOUD_AFTER_S - 0.5))
        return peak >= ref + LOUD_AFTER_DB

    def happened(a, b):
        return (any(x < b + EVENT_AROUND and a - EVENT_AROUND < y for x, y in bursts)
                or any(b - EVENT_AROUND <= x <= b + EVENT_AFTER for x in starts)
                or louder_after(a, b))
    return happened


def smart_moving(moving, happened):
    """moving(a, b) and happened(a, b): the picture changes a lot and an event shows (v2.8)."""
    if moving is None:
        return None

    def both(a, b):
        return moving(a, b) and happened(a, b)
    both.level, both.usual = getattr(moving, 'level', None), getattr(moving, 'usual', None)
    return both


def with_jump_cuts(clip, words, cues, gameplay, moving=None):
    """The clip with each range split at its long pauses (clips.json keeps the ranges as picked).
    Adds 'jump_edges' (piece edges made by a jump cut: they get small handles) and 'jump_saved'.
    moving(a, b): True when something happens on screen in that pause (gameplay): it stays."""
    noisy = [(a, b) for kind in ('laughter', 'applause') for a, b, *_ in (cues or {}).get(kind, [])]
    noisy += [tuple(x[:2]) for x in clip.get('keep_whole') or []]     # kept whole: no pause cut inside (v2.9)
    kept = []

    def quiet_ok(a, b):
        if moving and moving(a, b):
            kept.append((a, b))
            return False
        return not any(x < b and a < y for x, y in noisy)
    ranges, edges, saved = [], set(), 0.0
    for k, (s, e) in enumerate(clip['ranges']):
        pcs = jump_pieces(s, e, words, quiet_ok, GAME_PAUSE if gameplay else None)
        if k == 0 and clip.get('event_at') is not None:    # the event plays whole: no pause cut in it (v2.7)
            hold = float(clip['event_at']) + EVENT_HOLD
            n = max(1, sum(1 for p in pcs if p[0] < hold))
            pcs = [[pcs[0][0], pcs[n - 1][1]]] + pcs[n:]
        for x, y in zip(pcs, pcs[1:]):
            edges |= {round(x[1], 3), round(y[0], 3)}
            saved += y[0] - x[1]
        ranges += pcs
    extra = {'action_kept': len(kept)} if kept else {}
    if not edges:
        return dict(clip, **extra) if extra else clip
    return dict(clip, ranges=ranges, jump_edges=edges, jump_saved=round(saved, 1), **extra)


def in_keep(t, spans):
    """True when second t lies in (or on the edge of) a keep_whole span."""
    return any(a - 0.05 <= t <= b + 0.05 for a, b in spans or ())


def snap_piece(clip, s, e, words):
    """snap_range, with small handles at the edges a jump cut made, and an edge moved off a camera cut
    that would flash (edge_trims). v2.9: a piece without words is kept exactly as given (a crash, a game-over
    screen: (s, e, None, None)), and an edge inside a "keep_whole" span stays where it is (no trimming to the
    words: the picture is the point there)."""
    edges = clip.get('jump_edges') or ()
    r = snap_range(s, e, words, JUMP_PAD_IN if round(s, 3) in edges else PAD_IN,
                   JUMP_PAD_OUT if round(e, 3) in edges else PAD_OUT)
    keep = clip.get('keep_whole') or ()
    if r is None:
        return (s, e, None, None) if e - s >= JUMP_MIN_PIECE else None
    if in_keep(s, keep):                     # exactly as given: never trimmed, never grown into the next piece
        r = (s,) + tuple(r[1:])
    if in_keep(e, keep):
        r = (r[0], e) + tuple(r[2:])
    if r and clip.get('event_at') is not None and clip.get('ranges') and abs(s - clip['ranges'][0][0]) < 1e-3:
        r = (min(s, r[0]),) + tuple(r[1:])        # an event clip starts on its event, before anyone talks (v2.7)
    trim = (clip.get('edge_trims') or {}).get(f'{s:.3f}-{e:.3f}')
    return (trim['s'], trim['e'], r[2], r[3]) if r and trim else r


# ---------- no flash of another shot at a piece's edge ----------
# A camera cut in a piece's last frames shows a few frames of the next shot: a flicker of another face
# as the clip ends (5 of the 106 test clips, found by qa). The shot detector ignores cuts that close to
# an edge (a shot that short can't be framed), so, like an editor:
# - a cut in the quiet handle after the last word: the piece ends just before it;
# - a cut while the last word is still being said (within EDGE_HOLD of the end): the sound plays on
#   to the end of the word and the picture holds the old shot's last frame (5-12 frames, barely seen);
# the same at a piece's start (a cut in its first frames: start after it, or hold the new shot's
# first frame). No word is ever cut.
EDGE_SCORE = 0.30          # the scene score of a clear camera cut (the shot detector's threshold)
EDGE_WORD_GAP = 0.03       # a moved edge stays at least this far from the word
EDGE_HOLD = 0.50           # at most this much of a still frame at an edge
EDGE_MIN_SHOT = 0.6        # a framing switch (split <-> speaker) never leaves a piece's first / last shot shorter


def scene_scores(video, t0, dur):
    """[(source seconds, scene score)] for every frame from t0 for dur seconds (the first frame scores 0)."""
    r = subprocess.run(['ffmpeg', '-hide_banner', '-ss', f'{t0:.3f}', '-t', f'{dur:.3f}', '-i', str(video),
                        '-vf', "scale=160:-2,select='gte(scene,0)',metadata=print", '-an', '-f', 'null', '-'],
                       capture_output=True, text=True, encoding='utf-8', errors='replace')
    ts = [float(m) for m in re.findall(r'pts_time:([0-9.]+)', r.stderr)]
    ss = [float(m) for m in re.findall(r'scene_score=([0-9.]+)', r.stderr)]
    return [(t0 + t, s) for t, s in zip(ts, ss)]


def edge_trims(clip, words, fps, scores):
    """{"s-e": {s, e, hold_in, hold_out}} for the pieces of a clip with a camera cut in their first or
    last frames: the new start and end, and the seconds of still frame at each edge.
    `scores(t0, dur)` gives the frames' scene scores (scene_scores on the video)."""
    out = {}
    frame = 1.0 / max(fps, 1.0)
    for s, e in clip['ranges']:
        snapped = snap_piece(clip, s, e, words)
        if not snapped or snapped[2] is None:      # a piece without words is shown as given
            continue
        start, end, i0, i1 = snapped
        new_s, new_e, hold_in, hold_out = start, end, 0.0, 0.0
        last_e, first_s = words[i1]['e'], words[i0]['s']
        t0 = min(last_e, end - EDGE_HOLD)
        # from two frames earlier: the first frame of a scan always scores 0, so a cut on t0 needs one before it
        cuts = [t for t, sc in scores(t0 - 2 * frame, end - t0 + 3 * frame)
                if sc >= EDGE_SCORE and max(t0 - 0.5 * frame, start + 1.0) < t < end - 0.5 * frame]
        if cuts:
            after = [t for t in cuts if t > last_e + EDGE_WORD_GAP]
            if after:                              # in the quiet handle: end just before it
                new_e = after[0] - 0.5 * frame
            else:                                  # while the last word is said: hold the old shot
                # from half a frame before the cut: frame times are not exact, and the new shot's
                # first frame must not be the one that is held
                hold_out = end - cuts[0] + 0.5 * frame
        t1 = max(first_s, start + EDGE_HOLD)
        cuts = [t for t, sc in scores(start, t1 - start)
                if sc >= EDGE_SCORE and start + 0.5 * frame < t < min(t1, new_e - 1.0)]
        if cuts:
            before = [t for t in cuts if t < first_s - EDGE_WORD_GAP]
            if before:                             # in the quiet handle: start right on the new shot
                new_s = before[-1]
            elif cuts[-1] - start <= EDGE_HOLD:      # while the first word is said: hold the new shot
                hold_in = max(0.0, cuts[-1] - start - 0.5 * frame)
        if (new_s, new_e) != (start, end) or hold_in or hold_out:
            out[f'{s:.3f}-{e:.3f}'] = {'s': round(new_s, 3), 'e': round(new_e, 3),
                                       'hold_in': round(hold_in, 3), 'hold_out': round(hold_out, 3)}
    return out


def merge_edge_slivers(shots, min_s=EDGE_MIN_SHOT):
    """A piece's first or last shot shorter than min_s comes from a framing switch (the shot detector
    never makes one that short): it flashes like a cut, so the next / previous framing covers it."""
    if len(shots) > 1 and shots[-1]['b'] - shots[-1]['a'] < min_s:
        shots = shots[:-2] + [dict(shots[-2], b=shots[-1]['b'])]
    if len(shots) > 1 and shots[0]['b'] - shots[0]['a'] < min_s:
        shots = [dict(shots[1], a=shots[0]['a'])] + shots[2:]
    return shots


def edge_hold_filter(src, trim, dur, out):
    """A filter that replaces a piece's first / last frames by a still of the frame next to them."""
    hi, ho = trim.get('hold_in', 0.0), trim.get('hold_out', 0.0)
    return (f'[{src}]trim=start={hi:.3f}:end={dur - ho:.3f},setpts=PTS-STARTPTS,'
            f'tpad=start_mode=clone:start_duration={hi:.3f}:stop_mode=clone:stop_duration={ho:.3f}[{out}]')


def with_edge_trims(clip, video, words, fps):
    trims = edge_trims(clip, words, fps, lambda t0, dur: scene_scores(video, t0, dur))
    return dict(clip, edge_trims=trims) if trims else clip


# a later piece of a joined clip that opens on one of these may point at (or answer) words that were cut
PIECE_POINTERS = {'he', 'she', 'they', 'him', 'her', 'his', 'their', 'them', 'it', 'its', 'that', 'this', 'those',
                  'these', 'which', 'जो', 'जिसने', 'जिसको', 'जिसका', 'जिसकी', 'जिन्होंने',
                  'वो', 'वह', 'वे', 'उसने', 'उसको', 'उसे', 'उसका', 'उसकी', 'उनका', 'उनकी', 'उनको', 'उन्होंने',
                  'यह', 'ये', 'इसका', 'इसकी', 'इसको', 'इसलिए', 'वही', 'उसी', 'wo', 'woh', 'isliye', 'usne', 'unhone'}
PIECE_ANSWERS = {'yes', 'yeah', 'yep', 'no', 'nope', 'exactly', 'absolutely', 'correct',
                 'हाँ', 'हां', 'जी', 'बिल्कुल', 'बिलकुल', 'नहीं', 'haan', 'han', 'bilkul', 'nahi', 'ji'}


def boundary_warnings(ranges, words):
    """Flag clips that start or end mid-sentence (the most common clipping mistake), and a later
    piece of a joined clip that opens on a word pointing at (or answering) words that were cut."""
    warns = []
    for k, (s, e) in enumerate(ranges):
        snapped = snap_range(s, e, words)
        if not snapped:
            continue
        _, _, i0, i1 = snapped
        prev, last = (words[i0 - 1] if i0 > 0 else None), words[i1]
        nxt = words[i1 + 1] if i1 + 1 < len(words) else None
        if prev and not is_sentence_end(prev['w']) and words[i0]['s'] - prev['e'] < 0.6:
            warns.append(f'starts mid-sentence, right after "...{" ".join(w["w"] for w in words[max(0, i0 - 5):i0])}"')
        if nxt and not is_sentence_end(last['w']) and nxt['s'] - last['e'] < 0.6:
            warns.append(f'ends mid-sentence: "...{" ".join(w["w"] for w in words[max(0, i1 - 5):i1 + 1])}" '
                         f'is followed by "{" ".join(w["w"] for w in words[i1 + 1:i1 + 7])}..."')
        first = norm_token(words[i0]['w'])
        if k > 0 and (first in PIECE_POINTERS or first in PIECE_ANSWERS):
            what = 'answer a question' if first in PIECE_ANSWERS else 'point at words'
            warns.append(f'piece {k + 1} opens on "{words[i0]["w"].strip()}", which may {what} that were cut out: '
                         f'start it earlier, or make sure the clip still says what was meant')
        fs = false_start(words, i0, i1)
        if fs:
            warns.append(f'may start with a false start: "{fs[0]}" is said again {fs[1]:.1f} s later; if it is '
                         f'a restart, begin at the second one ({fs[2]:.2f})')
    return warns


def false_start(words, i0, i1, max_k=3, within=3.5, gap_words=5):
    """A clip that opens with a restarted phrase ("1992 se leke, 1992 peak ho gaya"): the first 1-3
    words come again within a few seconds. Returns (words, gap, start of the repeat) or None."""
    toks = [norm_token(w['w']) for w in words[i0:i1 + 1]]
    for k in range(max_k, 0, -1):
        head = toks[:k]
        if not all(head) or (k == 1 and len(head[0]) < 3):
            continue                             # one short word ("to", "ki") repeats by chance
        for j in range(k, min(len(toks) - k + 1, 2 * k + gap_words + 1)):
            if toks[j:j + k] == head and words[i0 + j]['s'] - words[i0]['s'] <= within:
                return ' '.join(w['w'].strip() for w in words[i0:i0 + k]), \
                    words[i0 + j]['s'] - words[i0]['s'], words[i0 + j]['s'] - 0.12
    return None


def _same_ranges(mine, theirs):
    return len(mine) == len(theirs) and all(abs(a - x) <= 1.0 and abs(b - y) <= 1.0
                                            for (a, b), (x, y) in zip(mine, theirs))


def drift_warnings(clip, cands, repairs=None):
    """A clip picked from a candidate list (long videos read in parts) or from the critic's list
    should keep its exact ranges; say so when they differ, or when the id doesn't exist. A repaired
    version the critic judged in the repair round (its shortlist entry named the same "from") is
    on purpose: no warning."""
    src = clip.get('from')
    if not src:
        return []
    c = cands.get(src)
    if not c:
        return [f'"from": "{src}" is not in candidates.json or the critic\'s list']
    mine, theirs = clip['ranges'], c['ranges']
    if _same_ranges(mine, theirs) or any(_same_ranges(mine, r) for r in (repairs or {}).get(src, [])):
        return []
    return [f'ranges differ from candidate {src} {theirs}: on purpose?']


def range_shots(video, info, clip, words):
    """[(start, dur, shots)] for each range of a clip, snapped to words and analysed (no framing yet)."""
    out = []
    for s, e in clip['ranges']:
        snapped = snap_piece(clip, s, e, words)
        if not snapped:
            continue
        start, end, _, _ = snapped
        dur = end - start
        out.append((start, dur, plan_shots(analyse_range(video, start, dur, info['width'], info['height']),
                                           info['width'], info['height'])))
    return out


def _two_shot(sh):
    """A stretch for the director: two people too far apart for one crop, or three people (v2.13)."""
    return bool(sh.get('ambiguous') or _group(sh)) and sh['mode'] == 'crop' and len(sh.get('faces') or []) >= 2


def _group(sh):
    return len(sh.get('group') or []) >= 3


def two_shot_pieces(planned):
    """(a, b) source times of the stretches where two people sit too far apart for one crop."""
    return [(start + sh['a'], start + sh['b']) for start, _, shots in planned for sh in shots if _two_shot(sh)]


def _wide_pieces(planned):
    """{(a, b): True} for two-person stretches filmed as a wide room shot (small faces)."""
    from .director import WIDE_FACE
    out = {}
    for start, _, shots in planned:
        for sh in shots:
            if _two_shot(sh):
                two = sh['group'] if _group(sh) else sh.get('pair') or sorted(sh['faces'], key=lambda f: -f[2])[:2]
                out[(start + sh['a'], start + sh['b'])] = max(f[2] for f in two) < WIDE_FACE
    return out


def audio16k(pdir, video):
    """The 16 kHz voice track the director listens to. A project tidied up after posting may have kept
    only the video: then it is made again from the video (a few seconds), so its clips keep the
    speaker framing instead of falling back to the classic one."""
    wav = pdir / 'source' / 'audio16k.wav'
    if not wav.exists() and video and Path(video).exists():
        print('   (no 16 kHz audio kept: making it again from the video)', flush=True)
        wav.parent.mkdir(parents=True, exist_ok=True)
        ffmpeg('-i', str(video), '-vn', '-ac', '1', '-ar', '16000', '-c:a', 'pcm_s16le', str(wav))
    return wav


def two_person(pdir, video, plans, words):
    """The director's framing for every clip with a two-person shot: {clip id: [(a, b, how)]}.
    Voices, laughter and mouth movement are measured once per clip (cached in .work/), the video's
    speaker register (speakers.json) learns which side each voice sits on from the calm moments of
    all clips, and the director turns that into speaker / both-people framing. Clips without a
    two-person shot, or a computer without the speaker models, keep the classic framing."""
    from . import director, speakers
    todo = {cid: two_shot_pieces(planned) for cid, (clip, planned) in plans.items()}
    todo = {cid: pieces for cid, pieces in todo.items() if pieces}
    if not todo:
        return {}
    print('-> two-person shots found: working out who speaks when (voices, laughter) ...', flush=True)
    try:
        audio = speakers.load_audio(audio16k(pdir, video))
    except Exception as e:
        print(f'   ! no 16 kHz audio to analyse ({e}); classic framing for those shots')
        return {}
    import cv2
    cap = open_video(video)
    work = pdir / '.work'
    work.mkdir(exist_ok=True)
    signals = {}
    for cid, pieces in todo.items():
        clip, planned = plans[cid]
        parts = [[round(start, 3), round(start + dur, 3)] for start, dur, _ in planned]
        cache = work / f'signals-{cid:02d}.json'
        old = load_json(cache)
        if old and old.get('parts') == parts and old.get('pieces') == [list(x) for x in pieces] \
                and old.get('v') == speakers.SIGNALS_V:
            signals[cid] = old
            continue
        vo = speakers.voices(audio, parts)
        if vo is None:
            print('   ! speaker models not available; classic framing for two-person shots')
            cap.release()
            return {}
        la = speakers.laughter(audio, parts) or []
        act, act_g = [], []
        for (start, _, shots) in planned:
            for sh in shots:
                if _two_shot(sh) and _group(sh):          # three people (v2.13): measured apart, other labels
                    act_g += speakers.face_activity(cap, start + sh['a'], start + sh['b'], [f[0] for f in sh['group']])
                elif _two_shot(sh):
                    two = sorted(f[0] for f in (sh.get('pair') or sorted(sh['faces'], key=lambda f: -f[2])[:2]))
                    act += speakers.face_activity(cap, start + sh['a'], start + sh['b'], two)
        signals[cid] = {'v': speakers.SIGNALS_V, 'parts': parts, 'pieces': [list(x) for x in pieces],
                        'voices': vo, 'laughter': la, 'activity': act, 'group_activity': act_g,
                        'prints': speakers.voice_prints(audio, vo) or {}}
        save_json(cache, signals[cid])
    cap.release()
    if settings().get('silent_reactions', True):       # v2.12: faces that laugh or look shocked, read once a clip
        from . import reactions as rx
        for cid, sg in signals.items():
            if 'reactions' in sg:
                continue
            found = []
            for (start, _, shots) in plans[cid][1]:
                for sh in shots:
                    if _two_shot(sh):
                        two = sorted(f[0] for f in (sh.get('pair') or sorted(sh['faces'], key=lambda f: -f[2])[:2]))
                        got = rx.read(video, start + sh['a'], start + sh['b'], two=two)
                        if got is None:                          # no expression model: nothing more to read
                            break
                        found += rx.strong(got)
            sg['reactions'] = [list(r) for r in found]
            save_json(work / f'signals-{cid:02d}.json', sg)
    reg = speakers.Register(load_json(pdir / 'speakers.json'))
    who = {}
    for cid, sg in signals.items():
        secs = {}
        for a, b, v in sg['voices']:
            secs[v] = secs.get(v, 0) + b - a
        # long, clean voices first, so a short disturbed one is compared with good prints
        for v, prnt in sorted(sg['prints'].items(), key=lambda kv: -secs.get(kv[0], 0)):
            person = reg.place(prnt, secs.get(v, 0))
            if person is not None:
                who[(cid, v)] = person
    for cid, sg in signals.items():
        rows = {}
        for v, row in speakers.calm_moments(sg['activity'], sg['voices'], sg['laughter'], words):
            if (cid, v) in who:
                rows.setdefault(who[(cid, v)], []).append(row)
        for person, rs in rows.items():
            reg.vote(person, cid, rs)
    save_json(pdir / 'speakers.json', reg.to_json())
    sides = reg.sides()
    out = {}
    for cid, sg in signals.items():
        side_of = {v: sides[pi][0] for (c, v), pi in who.items() if c == cid and pi in sides}
        # in the split-screen layout the person who talks most in this clip sits on top, right above
        # the captions (and away from the app buttons at the bottom); marked on the clip's shots
        talk = {}
        for a, b, v in sg['voices']:
            if v in side_of:
                inside = sum(max(0.0, min(b, pb) - max(a, pa)) for pa, pb in sg['parts'])
                talk[side_of[v]] = talk.get(side_of[v], 0) + inside
        if talk:
            star = max(talk, key=talk.get)
            for _, _, shots in plans[cid][1]:
                for sh in shots:
                    sh['star'] = star
        wide = _wide_pieces(plans[cid][1])
        # a listener's silent laugh or shock (v2.12): not heard as a laugh, and not the person talking then
        from . import reactions as rx
        heard = director._intervals(sg['laughter'])

        def talking(s, e, side, sg=sg, side_of=side_of):
            return any(side_of.get(v) == side and min(e, b) - max(s, a) >= 0.5 * (e - s) for a, b, v in sg['voices'])
        silent = rx.silent([tuple(r) for r in sg.get('reactions') or []], heard, talking)
        if silent:
            print(f"   clip {cid}: {len(silent)} silent reaction(s) of the listener: both people shown then", flush=True)
        group_side = speakers.group_sides(sg.get('group_activity') or [], sg['voices'], sg['laughter'], words)
        groups = {(start + sh['a'], start + sh['b']) for start, _, shots in plans[cid][1] for sh in shots if _group(sh)}
        spans = []
        for a, b in todo[cid]:
            sides_here = group_side if (a, b) in groups else side_of      # left / middle / right in a group shot
            spans += director.direct((a, b), words, sg['voices'], sg['laughter'], sides_here, wide=wide.get((a, b), False),
                                     reactions=[(r[0], r[1]) for r in silent])
        out[cid] = spans
        kinds = {}
        for a, b, how in spans:
            kinds[how] = kinds.get(how, 0) + b - a
        print(f"   clip {cid}: " + ', '.join(f'{k} {v:.0f}s' for k, v in sorted(kinds.items())), flush=True)
    return out


def join_fade(gap):
    """(fade in, fade out) seconds at a join that skips `gap` seconds of the video. Dialogue editors
    use a few ms at a plain cut and 20-100 ms where the room sound changes (more is heard)."""
    if abs(gap) > JUMP_FLASH:
        return 0.06, 0.08
    if abs(gap) > 2.0:
        return 0.03, 0.05
    return 0.01, 0.03


def piece_fades(ranges, k, start, end, dur, first_word, last_word):
    """The afade filters of piece k: a click-free start and end, kept inside the quiet before the
    first word and after the last one, so a fade never touches speech. A clip of one piece (and the
    clip's own start and end) fades exactly as before."""
    last = k == len(ranges) - 1
    f_in, f_out, curve = 0.01, (0.12 if last else 0.03), ''
    room_in = first_word['s'] - start - 0.01 if first_word else dur / 4      # a piece without words (v2.9)
    room_out = end - last_word['e'] - 0.01 if last_word else dur / 4
    if k > 0:
        f_in = max(0.01, min(join_fade(ranges[k][0] - ranges[k - 1][1])[0], room_in))
        curve = ':curve=qsin'
    if not last:
        f_out = max(0.03, min(join_fade(ranges[k + 1][0] - ranges[k][1])[1], room_out))
    return (f'afade=t=in:d={f_in:.3f}{curve},'
            f'afade=t=out:st={max(0, dur - f_out):.3f}:d={f_out:.3f}{":curve=qsin" if not last else ""}')


def build_clip(video, info, clip, words, out_mp4, horizontal=False, fc=None, planned=None, auto=None, game=()):
    src_w, src_h = info['width'], info['height']
    planned_by_start = {round(p[0], 3): p[2] for p in planned or []}
    fps = out_fps(info.get('fps', 30))
    parts, inputs, chains, labels, masks = [], [], [], [], []
    timeline = 0.0
    clip_words, shots_out, splices, splice_frames = [], [], [], []
    # with the same frame rate in and out, the frame where each shot begins is known exactly: the
    # edit puts zoom changes and caption moves on that frame (a part starting between two source
    # frames shifts the whole part's frame grid by a fraction of a frame)
    exact = abs(info.get('fps', 0) - fps) < 0.01
    frame_base, video_end, st0 = 0, 0, info.get('start_time', 0.0)
    jump_splices = []
    for k, (s, e) in enumerate(clip['ranges']):
        snapped = snap_piece(clip, s, e, words)
        if not snapped:
            print(f'   ! range {s}-{e} has no words, skipped')
            continue
        start, end, i0, i1 = snapped
        end = min(end, info.get('duration') or end)       # never past the video's end (a handle after its last word)
        dur = end - start
        inputs += ['-ss', f'{start:.3f}', '-t', f'{dur:.3f}', '-i', str(video)]
        n = len(parts)
        src = f'{n}:v'
        trim = (clip.get('edge_trims') or {}).get(f'{s:.3f}-{e:.3f}')
        if trim and (trim.get('hold_in') or trim.get('hold_out')):     # a still frame instead of a flash
            chains.append(edge_hold_filter(src, trim, dur, f'{n}h'))
            src = f'{n}h'
        if fc:
            ml = f'mask{n}' if fc['mask'] else None
            masks += [ml] if ml else []
            chains.append(fclib.filter_chain(src, f'v{n}', fc['cam'], fc['g'], src_w, src_h, fps, ml))
            shots = [{'a': 0, 'b': dur, 'mode': 'facecam', 'focus': [W / 2, fclib.TOP_H / 2]}]
        elif horizontal:
            chains.append(f'[{src}]fps={fps},setsar=1,format=yuv420p[v{n}]')
            shots = [{'a': 0, 'b': dur, 'mode': 'horizontal', 'focus': [src_w / 2, src_h * 0.4]}]
        else:
            shots = planned_by_start.get(round(start, 3)) or plan_shots(
                analyse_range(video, start, dur, src_w, src_h), src_w, src_h)
            shots = apply_framing(shots, auto or [], start, dur, src_w, src_h)           # the director
            shots = apply_framing(shots, framing_spans(clip), start, dur, src_w, src_h)   # hand-picked wins
            shots = merge_edge_slivers(shots)
            if len(shots) == 1:
                chains.append(shot_filter(src, shots[0], src_w, src_h, f'v{n}', fps))
            else:
                sub = ''.join(f'[{n}s{j}]' for j in range(len(shots)))
                chains.append(f'[{src}]split={len(shots)}{sub}')
                for j, sh in enumerate(shots):
                    chains.append(shot_filter(f'{n}s{j}', sh, src_w, src_h, f'v{n}_{j}', fps))
                chains.append(''.join(f'[v{n}_{j}]' for j in range(len(shots))) +
                              f'concat=n={len(shots)}:v=1:a=0[v{n}]')
        chains.append(f'[{n}:a]aresample=48000,{piece_fades(clip["ranges"], k, start, end, dur, words[i0] if i0 is not None else None, words[i1] if i1 is not None else None)}[a{n}]')
        labels.append(f'[v{n}][a{n}]')
        for k, w in enumerate(words[i0:i1 + 1] if i0 is not None else [], i0 or 0):
            cw = {**w, 's': round(w['s'] - start + timeline, 3), 'e': round(w['e'] - start + timeline, 3)}
            # a game character: no caption (the game shows its own); clips.json "show_captions" /
            # "hide_captions" ([[start, end], ...] in the video) overrule the rule (v2.7)
            if any(a <= w['s'] < b for a, b in clip.get('hide_captions') or []) or (
                    k in game and not any(a <= w['s'] < b for a, b in clip.get('show_captions') or [])):
                cw['game'] = True
            clip_words.append(cw)
        offset = (math.ceil((start - st0) * fps - 1e-6) / fps + st0 - start) if exact else 0.0
        for sh in shots:
            out_sh = {'t0': round(sh['a'] + timeline, 3), 't1': round(sh['b'] + timeline, 3),
                      'mode': sh['mode'], 'focus': sh['focus'],
                      **({'panels': sh['panels']} if sh.get('panels') else {})}   # three people stacked (v2.13)
            if exact:
                j = max(0, math.ceil((sh['a'] - offset) * fps - 1e-6))
                # a part's first frame shows right after the previous part's last one (when the
                # encoder fills a gap there, it repeats this first frame)
                out_sh['f0'] = video_end if j == 0 else frame_base + j
            shots_out.append(out_sh)
        if timeline > 0:
            splices.append(round(timeline, 3))
            splice_frames.append(video_end)
            if round(s, 3) in (clip.get('jump_edges') or ()):
                jump_splices.append(round(timeline, 3))     # a jump cut, not a join of two moments
        parts.append((start, end))
        timeline += dur
        # the next part starts after this part's video or its audio, whichever ends later; the encoder
        # puts it on the nearest frame (half a frame rounds up), repeating a frame to fill a gap
        if exact:
            video_end = frame_base + math.ceil((dur - offset) * fps - 1e-6)
            frame_base = max(video_end, frame_base + math.floor(dur * fps + 0.5 + 1e-6))
        else:
            frame_base += int(round(dur * fps))
    if not parts:
        return None
    n = len(parts)
    if masks:                       # the round-cam mask image, shared by every range of the clip
        inputs += ['-loop', '1', '-t', f'{timeline + 1:.3f}', '-i', str(fc['mask'])]
        chains.append(f'[{n}:v]format=gray,split={len(masks)}' + ''.join(f'[{m}]' for m in masks))
    # joins across time (deep clips, long splices) are shown, not hidden: a short white flash
    jumps = [{'t': splices[i], 'gap': round(parts[i + 1][0] - parts[i][1], 1)} for i in range(len(splices))]
    flashes = [j['t'] for j in jumps if abs(j['gap']) > JUMP_FLASH]
    out_v = 'outv'
    if flashes:
        out_v = 'outvf'
    chains.append(''.join(labels) + f'concat=n={n}:v=1:a=1[outv][outa]')
    if flashes:
        boxes = []
        for t in flashes:                         # about 4 frames: soft, bright, soft
            boxes.append(f"drawbox=x=0:y=0:w=iw:h=ih:color=white@0.45:t=fill:enable='between(t,{t - 0.09:.3f},{t + 0.12:.3f})'")
            boxes.append(f"drawbox=x=0:y=0:w=iw:h=ih:color=white@0.55:t=fill:enable='between(t,{t - 0.04:.3f},{t + 0.06:.3f})'")
        chains.append('[outv]' + ','.join(boxes) + '[outvf]')
    tmp = out_mp4.with_suffix('.part.mp4')
    ffmpeg(*inputs, '-filter_complex', ';'.join(chains), '-map', f'[{out_v}]', '-map', '[outa]',
           '-c:v', 'libx264', '-preset', 'fast', '-crf', '17', '-pix_fmt', 'yuv420p', '-r', str(fps),
           '-c:a', 'aac', '-b:a', '192k', '-ar', '48000', '-movflags', '+faststart', tmp)
    tmp.replace(out_mp4)
    meta = {'fps': fps, 'parts': [[round(a, 3), round(b, 3)] for a, b in parts], 'duration': round(timeline, 3),
            'shots': shots_out, 'splices': splices, 'jumps': jumps, 'words': clip_words,
            'jump_cuts': jump_splices}
    if exact:
        meta['splice_frames'] = splice_frames
    if fc:
        meta.update(layout='facecam', caption_y=fc['g']['caption_y'])
    if auto:
        meta['director'] = [[a, b, how] for a, b, how in auto]
    return meta


def facecam_layout(pdir, project, video, info, layout):
    """The facecam layout to use ({'cam', 'g', 'mask'}), or None for the normal framing."""
    src_w, src_h = info['width'], info['height']
    if layout == 'crop' or src_w / src_h < 1.2:            # vertical/square sources keep the normal path
        return None
    box = settings().get('facecam')
    if box:
        cam, how = fclib.from_settings(box, src_w, src_h), 'from settings.json'
    else:
        if 'facecam' not in project:
            print('-> looking for a webcam overlay (facecam) ...', flush=True)
            from .kind import stream_hint      # the two-person finder: only for gameplay and streams (v2.7)
            project['facecam'] = fclib.detect(video, info['duration'], src_w, src_h,
                                              framed=bool(stream_hint(project))) or False
            save_json(pdir / 'project.json', project)
        cam, how = project['facecam'], 'auto-detected'
    if not cam:
        if layout == 'facecam':
            die('no webcam overlay found. Set its box in settings.json, e.g.\n'
                '  "facecam": {"x": 0.80, "y": 0.35, "w": 0.19, "h": 0.34, "shape": "circle"}\n'
                '(fractions of the frame: left, top, width, height)')
        return None
    cam = fclib.clamp(cam, src_w, src_h)
    g = fclib.geometry(cam, src_w, src_h, fclib.margins(settings().get('facecam_margins')))
    mask = None
    if cam.get('shape') == 'circle':
        (pdir / '.work').mkdir(exist_ok=True)
        mask = fclib.mask_png(pdir / '.work' / f"cam_mask_{g['cam_w']}x{g['cam_h']}.png", g['cam_w'], g['cam_h'])
    print(f"-> layout: facecam ({how}: {cam['shape']} cam at x={cam['x']} y={cam['y']} {cam['w']}x{cam['h']}). "
          f"Gameplay on top, cam below, captions between. Normal framing: --layout crop")
    if fclib.is_tall(cam):          # taller than a 4:3 camera picture: maybe a strip of game in it, so the faces shrink
        sheet = fclib.box_sheet(video, cam, info['duration'] / 2, pdir / 'frames' / 'facecam-box.jpg')
        print(f"   ! the webcam box is taller than a camera picture ({cam['w']}x{cam['h']}): look at "
              f"{sheet.relative_to(ROOT) if sheet.is_relative_to(ROOT) else sheet}. If it holds game picture too, set the "
              f'right box in project.json "facecam" (pixels: x, y, w, h) and cut again')
    return {'cam': cam, 'g': g, 'mask': mask}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('project')
    ap.add_argument('--clips', default=None, help='comma list of clip ids, e.g. 1,3')
    ap.add_argument('--horizontal', action='store_true', help='keep the original 16:9 framing')
    ap.add_argument('--landscape-copy', action='store_true',
                    help='a 16:9 copy next to the standing clips, in clips-landscape/, on the same timeline (for '
                         '`run.py landscape`)')
    ap.add_argument('--check', action='store_true', help='only check clip boundaries, cut nothing')
    ap.add_argument('--jump-cuts', action=argparse.BooleanOptionalAction, default=None,
                    help='cut long pauses and filler sounds out of each clip (default: settings.json "jump_cuts", on)')
    ap.add_argument('--layout', default=None, choices=['auto', 'facecam', 'crop'],
                    help='auto (default, from settings.json): facecam layout when a webcam overlay is found')
    a = ap.parse_args()

    pdir = project_dir(a.project)
    project = load_json(pdir / 'project.json')
    picks = load_json(pdir / 'clips.json')
    if not picks or not picks.get('clips'):
        die(f'no clips.json in {pdir}. Claude writes it after reading transcript/transcript.txt')
    words = load_json(pdir / 'transcript' / 'words.json')
    want = {int(x) for x in a.clips.split(',')} if a.clips else None

    flagged = 0
    cands = {c['id']: c for c in load_json(pdir / 'candidates.json', []) or []}
    repairs = {}
    for c in (load_json(pdir / 'critic' / 'plan.json') or {}).get('clips', []):
        cands.setdefault(c['id'], c)             # a short video's shortlist ("s3") judged by the critic
        if c.get('origin'):                      # a repaired version of an earlier idea
            repairs.setdefault(c['origin'], []).append(c['ranges'])
    for c in load_json(pdir / 'deep' / 'candidates.json', []) or []:
        cands.setdefault(c['id'], c)             # a deep clip ("d1-c1") from the deep pass
    from .kind import active_breaks, is_irregular, NAMES
    breaks = active_breaks(project)
    quiet_s = QUIET_GAP_S if is_irregular(project) else None
    taken = []                                   # (clip id, start, end) of every range so far
    picked, overlap = [], overlap_mode(project)  # settings.json "overlap_clips" (v2.7)
    from . import private
    secret_spans = private.spans(words) if private.wanted(project) else []
    for i, clip in enumerate(picks['clips'], 1):
        cid = int(clip.get('id', i))
        if want and cid not in want:
            continue
        snapped = [snap_range(s, e, words) for s, e in clip['ranges']]
        total = sum(x[1] - x[0] if x else e - s for x, (s, e) in zip(snapped, clip['ranges']))
        msgs = boundary_warnings(clip['ranges'], words)
        for k, (x, (s, e)) in enumerate(zip(snapped, clip['ranges']), 1):   # v2.9: shown as given, not skipped
            if x is None:
                msgs.append(f'piece {k} ({fmt_ts(s)}-{fmt_ts(e)}) has no words: it is shown exactly as given (a '
                            f'crash, a game-over screen); fine when that is the point, else check its times')
        if total and not 15 <= total <= 90:
            msgs.append(f'length {total:.0f}s is outside 15-90 s')
        msgs += drift_warnings(clip, cands, repairs)
        for r0, r1 in clip['ranges']:            # unclear speech (relisten marked it): no captions there
            uw = [w for w in words if w.get('unsure') and r0 <= w['s'] < r1]
            if uw:
                msgs.append(f"no captions at {fmt_ts(uw[0]['s'])}-{fmt_ts(uw[-1]['e'])} ({len(uw)} words): the "
                            f"speech there was unclear (a game voice, music or noise). Fine if the game shows "
                            f"its own subtitles")
        for r0, r1 in clip['ranges']:            # live streams: "Starting soon", "Be right back" ...
            for br in breaks:
                if min(r1, br['end']) - max(r0, br['start']) >= 1.0:
                    msgs.append(f"touches the {NAMES[br['where']]} at {fmt_ts(br['start']).split('.')[0]}-"
                                f"{fmt_ts(br['end']).split('.')[0]} (break {br['n']}): a still screen, nobody on "
                                f"cam. Move the range off it (or `run.py kind <project> --keep {br['n']}` if it "
                                f"is real video)")
        for s, e, what in secret_spans:           # v2.7: cut takes these seconds out by itself
            if any(r0 < e and s < r1 for r0, r1 in clip['ranges']):
                msgs.append(f'takes in private details at {fmt_ts(s)}-{fmt_ts(e)} ({what} said out loud): cut '
                            f'leaves those seconds out; better end the clip before them')
        if quiet_s:                              # gameplay: long quiet stretches inside a clip lose viewers
            for r0, r1 in clip['ranges']:
                inside = [w for w in words if r0 <= w['s'] < r1 and not w.get('unsure')]
                for w0, w1 in zip(inside, inside[1:]):
                    if w1['s'] - w0['e'] >= quiet_s:
                        msgs.append(f"{w1['s'] - w0['e']:.0f} s without talk at {fmt_ts(w0['e'])}: fine if the "
                                    f"gameplay there is the point (a chase, a crash), else end before it or "
                                    f"join the pieces around it")
        if overlap == 'avoid':
            for r0, r1 in clip['ranges']:
                for other, x, y in taken:
                    if r0 < y - 1.0 and x < r1 - 1.0:
                        msgs.append(f'overlaps clip {other} ({x:.1f}-{y:.1f}): the same words twice')
        else:                                    # overlaps are fine; near-copies and a 4th clip of a moment aren't
            why = overlap_problem(clip['ranges'], picked, 'allow')
            if why:
                msgs.append(why)
        taken += [(cid, r0, r1) for r0, r1 in clip['ranges']]
        picked.append((f'clip {cid}', clip['ranges']))
        for m in msgs:
            print(f'   WARNING clip {cid} "{clip.get("title")}": {m}')
        flagged += bool(msgs)
    if a.check:
        print('check: all clip boundaries look clean' if not flagged else
              f'check: {flagged} clip(s) need a look. Fix the ranges with `run.py find`, '
              'unless the cut is intentional')
        from . import sfx as sfxlib                  # v2.7: which sound moods the clips ask for
        wanted, missing = sfxlib.needed([c for i, c in enumerate(picks['clips'], 1)
                                         if not want or int(c.get('id', i)) in want])
        if wanted:
            have = sfxlib.moods_available()
            print('sounds: ' + ', '.join(f'{m} {n} cue(s) ({have.get(m, 0)} sound(s))'
                                         for m, n in sorted(wanted.items(), key=lambda x: -x[1])))
            if missing:
                print(f"sounds: no sound yet for {', '.join(missing)}: those cues stay silent. "
                      f"`python run.py sfx starter` downloads free ones, or add your own to sounds/<mood>/")
        return

    video = ensure_video(pdir, project)
    info = probe(video)
    print(f'-> source: {info["width"]}x{info["height"]} {info["fps"]:.2f}fps, {fmt_ts(info["duration"])}')
    if a.landscape_copy:            # v2.8: the same pieces as the standing clip, framed 16:9, in their own folder
        a.horizontal = True
    out_dir = pdir / ('clips-landscape' if a.landscape_copy else 'clips')
    out_dir.mkdir(exist_ok=True)
    layout = a.layout or settings().get('layout', 'auto')
    fc = None if a.horizontal else facecam_layout(pdir, project, video, info, layout)

    # jump cuts: each clip's long pauses and filler sounds are cut out (clips.json keeps its ranges)
    jc_on = settings().get('jump_cuts', True) if a.jump_cuts is None else a.jump_cuts
    prepared = {}
    if jc_on:
        from . import sound
        from .kind import is_irregular
        cues, game = sound.load(pdir), is_irregular(project) or bool(fc)   # facecam layout: gameplay
        if a.landscape_copy:          # the standing cut counted a found webcam as gameplay: the same pauses here
            game = game or bool(project.get('facecam'))
        act_mode = str(settings().get('action_pauses', 'smart')).lower()       # smart | keep | cut
        act_on = act_mode != 'cut'
        happened = event_signs(pdir, words, load_json(pdir / 'transcript' / 'sentences.json') or []) \
            if act_on and act_mode != 'keep' else None
        cam_box = fc['cam'] if fc else (project.get('facecam') or None)
    from . import private                        # an email or phone number said out loud never ends up in a clip
    secret = private.spans(words) if private.wanted(project) else []
    from . import gameover                       # a game-over screen in a clip is always shown whole (v2.9)
    screens = [s_[:2] for s_ in (gameover.load(pdir) or {}).get('screens', [])]
    for i, clip in enumerate(picks['clips'], 1):
        on = [x for x in screens if any(r0 < x[1] and x[0] < r1 for r0, r1 in clip['ranges'])]
        if on:
            picks['clips'][i - 1] = clip = dict(clip, keep_whole=list(clip.get('keep_whole') or []) + on)
        cid = int(clip.get('id', i))
        hits = [sp for sp in secret for a, b in clip['ranges'] if a < sp[1] and sp[0] < b]
        if hits:
            clip = dict(clip, ranges=private.subtract(clip['ranges'], secret))
            if not want or cid in want:
                for s, e, what in dict.fromkeys(hits):
                    print(f'   clip {cid}: {fmt_ts(s)}-{fmt_ts(e)} left out ({what} said out loud)')
        moving = None                            # gameplay: a quiet second with action on screen stays (v2.7.1)
        if jc_on and game and act_on and (not want or cid in want):
            moving = action_check(clip, video, cam_box, (info['width'], info['height']))
            if happened is not None:                 # the smarter check (v2.8); "keep" = the picture alone
                moving = smart_moving(moving, happened)
        prepared[cid] = with_jump_cuts(clip, words, cues, game, moving) if jc_on else clip
        if not want or cid in want:     # no flash of another shot at a piece's edge
            prepared[cid] = with_edge_trims(prepared[cid], video, words, info.get('fps', 30))

    plans = {}
    if not a.horizontal and not fc:
        for i, clip in enumerate(picks['clips'], 1):
            cid = int(clip.get('id', i))
            if not want or cid in want:
                plans[cid] = (prepared[cid], range_shots(video, info, prepared[cid], words))
    auto = two_person(pdir, video, plans, words) if plans else {}

    # gameplay with a Hindi / Hinglish streamer: game characters' lines get no captions (the game
    # shows its own subtitles; "game_voice_captions": true shows them again)
    game = set()
    if not settings().get('game_voice_captions', False):
        from . import subtitles, voices
        subtitles.scan(pdir, project, [c for k, c in enumerate(picks['clips'], 1) if not want or int(c.get('id', k)) in want],
                       words, load_json(pdir / 'transcript' / 'sentences.json') or [], video,
                       (fc['cam'] if fc else None) or project.get('facecam'))   # English gameplay (v2.8)
        game = voices.game_words(pdir, project, words)

    done = []
    for i, clip in enumerate(picks['clips'], 1):
        cid = int(clip.get('id', i))
        if want and cid not in want:
            continue
        name = f'{cid:02d}-{slugify(clip.get("title", "clip"), 40)}'
        out = out_dir / f'{name}.mp4'
        print(f'-> clip {cid}: "{clip.get("title")}"  ranges={clip["ranges"]}')
        pc = prepared[cid]
        if pc.get('jump_edges'):
            print(f"   jump cuts: {len(pc['ranges']) - len(clip['ranges'])}, {pc['jump_saved']} s of pauses taken out")
        if pc.get('action_kept'):
            print(f"   {pc['action_kept']} pause(s) kept: something happens on screen there")
        meta = build_clip(video, info, pc, words, out, a.horizontal, fc,
                          plans.get(cid, (None, None))[1], auto.get(cid), game)
        n_game = sum(1 for w in meta['words'] if w.get('game')) if meta else 0
        if n_game:
            print(f'   {n_game} word(s) of game characters without captions (the game shows its own subtitles)')
        if not meta:
            print('   ! skipped (no words in its ranges)')
            continue
        meta.update({'id': cid, 'name': name, 'title': clip.get('title'), 'hook': clip.get('hook'),
                     'emphasis': clip.get('emphasis', []), 'file': out.name})
        save_json(out_dir / f'{name}.json', meta)
        modes = sorted({s['mode'] for s in meta['shots']})
        print(f'   ok {out.name}  {meta["duration"]:.1f}s, {len(meta["shots"])} shot(s), {"/".join(modes)}')
        done.append(out)

    print(f'\nDONE: {len(done)} clip(s) in {out_dir}')
    if not a.landscape_copy:                          # `landscape` goes on by itself
        print('next (optional simple edit):  python run.py edit ' + pdir.name)


if __name__ == '__main__':
    main()
