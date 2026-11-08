"""The director: framing for shots where two people sit too far apart for one crop (podcast two-shots).

It decides, moment by moment, what a good editor would show:
- SPEAKER   one person talks, the other just listens  -> crop on the speaker
- BOTH      a laugh (and the punchline just before it, when the listener starts to crack up), the
            listener laughing while the other talks, both laughing, talking over each other, a quick
            back-and-forth, a wide room shot without a long single speaker, or anything unclear
            -> both people (stacked split-screen, the one who talks most on top)
plus the rules that keep it watchable: every framing holds for at least HOLD seconds (split-screen
HOLD_BOTH), switches happen between words, and when unsure it shows both people: that always looks
intentional and never shows the wrong face.

A single-person reaction shot (only the laughing listener) is left to the AI editor, who can see in
the frames sheet who is laughing and add it with "framing" in clips.json. From the sound alone a
laugh can't be told apart from who made it (tested on hand-labelled clips: in most laughs both people
laugh, and the person telling the joke laughs at it too).

Signals (see speakers.py): voices (who speaks when, from the audio), laughter (from the audio), and
which side each voice sits on, from the video's speaker register (learnt from calm moments in all
clips, never from a single funny clip).
"""


HOLD = 1.5             # no framing shorter than this (seconds)
HOLD_BOTH = 2.0        # split-screen at least this long (the captions move to the seam)
LAUGH_ON = 0.2         # laughter frames at least this strong count (0.00 on serious talk)
LAUGH_GAP = 0.5        # laughter frames closer than this are one laugh
PRE = 2.0              # the listener starts to crack up during the punchline, before the laugh is heard
POST = 2.0             # ... and is still laughing for a moment after it fades
WIDE_FACE = 0.15       # faces smaller than this share of the frame height: a wide room shot
WIDE_SOLO = 6.0        # in a wide shot, crop on one speaker only when they talk this long alone
MAX_WORD = 0.8         # a "word" longer than this is stretched over a laugh or a pause
SNAP = 0.35            # move a switch onto the nearest gap between words within this distance
FLOOR = 4.0            # a turn this long holds the floor; three shorter turns in a row are a quick
                       # back-and-forth, shown with both people instead of ping-pong crops


def _intervals(frames):
    """Laughs: [start, end] of laughter frames scoring at least LAUGH_ON, close ones joined."""
    out = []
    for s, e, score in sorted(frames or []):
        if score < LAUGH_ON:
            continue
        if out and s <= out[-1][1] + LAUGH_GAP:
            out[-1][1] = max(out[-1][1], e)
        else:
            out.append([s, e])
    return out


def _active(segs, t):
    return {v for s, e, v in segs if s <= t < e}


def _covers(ivs, t0, t1, share=0.4):
    return any(min(b, t1) - max(a, t0) >= share * (t1 - t0) for a, b in ivs)


def _label(t0, t1, voices, side_of, laughs, zones, words):
    """What happens in [t0, t1): returns (kind, side 'L' | 'R' or None)."""
    talking = any(t0 <= (w['s'] + w['e']) / 2 < t1 for w in words)
    if _covers(laughs, t0, t1) or _covers(zones, t0, t1):
        return 'BOTH', None              # a laugh, or the punchline / tail around it
    act = _active(voices, (t0 + t1) / 2)
    known = {side_of[v] for v in act if v in side_of}
    if len(act) >= 2 or len(known) > 1:
        return 'BOTH', None              # talking over each other
    if len(act) == 1 and len(known) == 1:
        return 'SPEAKER', known.pop()
    if not talking and not act:
        return 'QUIET', None
    return 'BOTH', None                  # someone talks but we can't tell who


def direct(piece, words, voices, laughs, side_of, wide=False):
    """Framing spans [(a, b, how)] for one two-person stretch `piece` = (a, b) in source seconds.
    side_of = {voice id: 'L' | 'R'} from the speaker register (voices it can't place are left out);
    wide = the faces are small (a wide room shot). how = 'left' | 'right' | 'split'."""
    a0, b0 = piece
    voices = voices or []
    laugh_iv = _intervals(laughs)
    zones = [[s - PRE, e + POST] for s, e in laugh_iv]
    # words, with the part stretched over a laugh or a pause cut off
    ws = [{**w, 'e': min(w['e'], w['s'] + MAX_WORD)} for w in words if a0 - 0.2 <= w['s'] < b0]
    # cut the stretch at every change of voice and laughter
    cuts = {a0, b0}
    for s, e, _ in voices:
        cuts.update(x for x in (s, e) if a0 < x < b0)
    for s, e in laugh_iv + zones:
        cuts.update(x for x in (s, e) if a0 < x < b0)
    times = sorted(cuts)
    units = []
    for t0, t1 in zip(times, times[1:]):
        if t1 - t0 < 0.05:
            continue
        kind, side = _label(t0, t1, voices, side_of, laugh_iv, zones, ws)
        units.append([t0, t1, kind, side])
    if not units:
        return [(round(a0, 3), round(b0, 3), 'split')]
    # quiet moments keep the framing around them (the one before, else the one after)
    for i, u in enumerate(units):
        if u[2] == 'QUIET':
            near = next((v for v in reversed(units[:i]) if v[2] != 'QUIET'), None) or \
                next((v for v in units[i + 1:] if v[2] != 'QUIET'), None)
            u[2], u[3] = (near[2], near[3]) if near else ('BOTH', None)
    spans = _exchanges(_smooth(units))
    if wide:
        # a wide room shot is the source editor showing both people: crop on one of them only for a
        # long stretch of them talking alone
        for u in spans:
            if u[2] == 'SPEAKER' and u[1] - u[0] < WIDE_SOLO:
                u[2], u[3] = 'BOTH', None
        spans = _smooth(spans)
    # switches go to real gaps between words: a stretched word's capped end is not a gap (snapping
    # there could land the switch in the middle of a phrase)
    spans = _snap(spans, [w for w in words if a0 - 0.2 <= w['s'] < b0], a0, b0)
    out = []
    for s, e, kind, side in spans:
        how = 'split' if kind == 'BOTH' or side is None else ('left' if side == 'L' else 'right')
        out.append((round(s, 3), round(e, 3), how))
    return out


def _exchanges(spans):
    """Quick back-and-forth: three or more short speaker turns in a row become both people."""
    out = [list(s) for s in spans]
    i = 0
    while i < len(out):
        j = i
        while j < len(out) and out[j][2] == 'SPEAKER' and out[j][1] - out[j][0] < FLOOR:
            j += 1
        if j - i >= 3:
            for k in range(i, j):
                out[k][2], out[k][3] = 'BOTH', None
        i = max(j, i + 1)
    return _smooth(out) if out != spans else out


def _same(u, v):
    return u[2] == v[2] and (u[3] == v[3] or u[2] == 'BOTH')


def _min_len(u):
    return HOLD_BOTH if u[2] == 'BOTH' else HOLD


def _smooth(units):
    """Merge neighbours that show the same thing, then fold every piece shorter than its minimum
    into a neighbour (showing both people wins; else the longer one), until nothing flickers."""
    us = [list(u) for u in units]
    while True:
        merged = [us[0]]
        for u in us[1:]:
            if _same(merged[-1], u):
                merged[-1][1] = u[1]
            else:
                merged.append(u)
        us = merged
        short = [i for i, u in enumerate(us) if u[1] - u[0] < _min_len(u)]
        if not short or len(us) < 2:
            return us
        i = min(short, key=lambda k: us[k][1] - us[k][0])
        left = us[i - 1] if i > 0 else None
        right = us[i + 1] if i + 1 < len(us) else None
        if left and right:
            if 'BOTH' in (left[2], right[2]) and left[2] != right[2]:
                target = left if left[2] == 'BOTH' else right
            else:
                target = left if left[1] - left[0] >= right[1] - right[0] else right
        else:
            target = left or right
        if target is left:
            left[1] = us[i][1]
        else:
            right[0] = us[i][0]
        del us[i]


def _snap(spans, words, a0, b0):
    """Move each switch to the middle of the nearest gap between words (within SNAP seconds)."""
    gaps = [((w['e'] + n['s']) / 2) for w, n in zip(words, words[1:]) if n['s'] - w['e'] > 0.05]
    out = [list(s) for s in spans]
    for i in range(1, len(out)):
        t = out[i][0]
        near = min(gaps, key=lambda g: abs(g - t), default=None)
        if near is not None and abs(near - t) <= SNAP and out[i - 1][0] + 0.5 < near < out[i][1] - 0.5:
            out[i - 1][1] = out[i][0] = near
    out[0][0], out[-1][1] = a0, b0
    return out
