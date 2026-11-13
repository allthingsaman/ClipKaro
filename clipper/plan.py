"""Builds the edit plan for one clip: camera zooms, caption groups and sound-effect cues.

Both render engines (python and remotion) read the same plan, so they produce the same edit:
the camera is pre-computed per frame here, captions carry exact word times, and the audio mix
is shared. Only the drawing differs.

Zoom style (adapted from a tested short-form editing engine):
  * open on motion: 1.18 -> wide, a fast ease-out snap over 9 frames
  * every 3-5 s (on sentence ends) the framing alternates wide <-> punched-in, as a hard cut
  * camera cuts / spliced ranges always get a framing change (hides the jump)
  * one or two smooth "snap" zooms for emphasis
  * between changes a slow +0.03 push so the frame is never dead
  * scale is always around the speaker's face, so the face stays in place
"""
import math
import re
import struct
from pathlib import Path

from .common import FPS, H, JUMP_FLASH, W, has_devanagari, is_sentence_end, norm_token
from . import sfx as sfxlib

# caption fonts (assets/fonts): Montserrat has no Hindi letters, so captions that contain Devanagari
# switch to Poppins, which has both Devanagari and Latin in the same bold geometric style
FONTS = Path(__file__).resolve().parent.parent / 'assets' / 'fonts'
# a caption line never gets wider than this (the frame is 1080 wide; 70 px stay free on each side)
MAX_CAPTION_W = W - 140
LATIN_FONT = ('Montserrat ExtraBold', 'Montserrat-ExtraBold.ttf')
HINDI_FONT = ('Poppins ExtraBold', 'Poppins-ExtraBold.ttf')

WIDE = [1.0, 1.04, 1.02]
PUNCH = [1.16, 1.22, 1.13, 1.2]
DRIFT = 0.03
OPEN_SCALE, OPEN_FRAMES = 1.18, 9
SNAP_FRAMES = 8
CUT_GAP = 2.8      # a camera cut changes the zoom only this long after the last change, like any other beat;
                   # sooner (anime, trailers: a cut every second) the framing just follows the new face

# ---------- easing (cubic-bezier, same curves as CSS / Remotion Easing.bezier) ----------


def bezier(x1, y1, x2, y2):
    def sample(a1, a2, t):
        return ((1 - 3 * a2 + 3 * a1) * t + (3 * a2 - 6 * a1)) * t * t + 3 * a1 * t

    def ease(x):
        if x <= 0:
            return 0.0
        if x >= 1:
            return 1.0
        lo, hi = 0.0, 1.0
        for _ in range(40):
            mid = (lo + hi) / 2
            if sample(x1, x2, mid) < x:
                lo = mid
            else:
                hi = mid
        return sample(y1, y2, (lo + hi) / 2)
    return ease


EASE_OUT = bezier(0.16, 1, 0.3, 1)     # "snap": fast then settles
EASE_IN_OUT = bezier(0.65, 0, 0.35, 1)
EASES = {'snap': EASE_OUT, 'smooth': EASE_IN_OUT}


def cam_at(keys, f):
    """Camera {s, x, y} at frame f from keyframes. A key's `ease` says how we ARRIVE at it:
    cut = jump at its frame, linear = glide from the previous key, snap/smooth = move during
    the `dur` frames that end at the key."""
    pi = 0
    for i, k in enumerate(keys):
        if k['f'] <= f:
            pi = i
    p = keys[pi]
    n = keys[pi + 1] if pi + 1 < len(keys) else None
    if n is None or f < p['f']:
        return p['s'], p['x'], p['y']
    k = 0.0
    if n['ease'] == 'linear':
        k = (f - p['f']) / max(1, n['f'] - p['f'])
    elif n['ease'] in EASES:
        d = n.get('dur', 12)
        r = min(1.0, max(0.0, (f - (n['f'] - d)) / d))
        k = EASES[n['ease']](r)
    return tuple(a + (b - a) * k for a, b in ((p['s'], n['s']), (p['x'], n['x']), (p['y'], n['y'])))


# ---------- helpers ----------

def focus_at(shots, t):
    for s in shots:
        if s['t0'] <= t < s['t1']:
            return s['focus']
    return shots[-1]['focus'] if shots else [W / 2, H * 0.4]


def mode_at(shots, t):
    for s in shots:
        if s['t0'] <= t < s['t1']:
            return s.get('mode')
    return shots[-1].get('mode') if shots else None


def beat_bounds(words, shots, splices, duration):
    """(times where the framing changes, the must-cuts among them, camera cuts the framing only follows).
    Must-cuts: splices, cuts into or out of a whole-frame / split shot, and camera cuts at least CUT_GAP
    after the last change. A camera cut that comes sooner keeps the zoom and only re-centres on the new
    shot's face: an anime clip with a cut every second got 48 zoom changes in 68 seconds."""
    wide = ('fit', 'split')
    cuts = {round(s['t0'], 3) for s in shots if s['t0'] > 0.3}
    always = {sp for sp in splices if sp > 0.3}
    for prev, sh in zip(shots, shots[1:]):            # the zoom must switch off (or on) there
        if sh['t0'] > 0.3 and (prev.get('mode') in wide) != (sh.get('mode') in wide):
            always.add(round(sh['t0'], 3))
    must = sorted(cuts | always)
    soft, follow = [], []
    for i, w in enumerate(words[:-1]):
        nxt = words[i + 1]
        if is_sentence_end(w['w']) or nxt['s'] - w['e'] > 0.45:
            soft.append(round(nxt['s'] - 0.03, 3))
    bounds, last = [], 0.0
    cands = sorted(set(must) | set(soft))
    for c in cands:
        if c >= duration - 1.2:
            break
        if c in must:
            if c - last >= (0.5 if c in always else CUT_GAP):
                bounds.append(c)
                last = c
            else:
                follow.append(c)
            continue
        nxt_must = next((m for m in must if m > c), duration)
        if c - last >= 2.8 and nxt_must - c >= 1.5:
            bounds.append(c)
            last = c
        elif c - last > 6.0 and nxt_must - c >= 0.5:      # (never just before a real cut, which would lose it)
            bounds.append(c)
            last = c
    # very long stretches with no sentence end: cut on a word start every ~4.5 s
    filled, prev = [], 0.0
    for b in bounds + [duration]:
        while b - prev > 7.0:
            target = prev + 4.5
            ws = min((w['s'] for w in words if w['s'] > prev + 3.0), key=lambda s: abs(s - target), default=None)
            if ws is None or ws >= b - 1.5:
                break
            filled.append(round(ws - 0.03, 3))
            prev = ws
        if b < duration:
            filled.append(b)
        prev = b
    return sorted(set(filled)), set(b for b in filled if b in set(must)), sorted(set(follow) - set(filled))


def build_camera(meta):
    words, shots, dur = meta['words'], meta['shots'], meta['duration']
    fps = meta.get('fps', FPS)
    frames = int(round(dur * fps))
    bounds, must, follow = beat_bounds(words, shots, meta.get('splices', []), dur)
    exact = exact_frames(meta)
    starts = [0.0] + bounds
    ends = bounds + [dur]
    keys, transitions = [], []
    wi = pi = 0
    snaps_left = 2 if dur > 25 else 1
    snap_after = dur * 0.3
    for b, (t0, t1) in enumerate(zip(starts, ends)):
        fx, fy = focus_at(shots, t0 + 0.05)
        is_must = any(abs(t0 - m) < 0.05 for m in must)
        # a zoom change that goes with a camera cut lands on the frame where the cut really shows:
        # recorded exactly by cut (when it could), else the nearest frame
        f0 = exact.get(round(t0, 3), int(round(t0 * fps))) if is_must else int(round(t0 * fps))
        f1 = max(f0 + 1, int(round(t1 * fps)) - 1)
        # 'fit' shots show the whole frame (slides, b-roll, show_full moments): zooming in would
        # crop away exactly what they are there to show, so the camera stays wide and still
        full = mode_at(shots, t0 + 0.05) in ('fit', 'split')
        punched = b % 2 == 1
        if punched:
            s = PUNCH[pi % len(PUNCH)]
            pi += 1
        else:
            s = WIDE[wi % len(WIDE)]
            wi += 1
        if full:            # override after the level rotation advanced, so later beats stay unchanged
            s, punched = 1.0, False
        if b == 0:
            keys.append({'f': 0, 's': 1.06 if full else OPEN_SCALE, 'x': fx, 'y': fy, 'ease': 'cut'})
            keys.append({'f': OPEN_FRAMES, 's': s, 'x': fx, 'y': fy, 'ease': 'snap', 'dur': OPEN_FRAMES})
            transitions.append({'t': 0.0, 'kind': 'open'})
        else:
            if punched and not is_must and snaps_left and t0 >= snap_after:
                keys.append({'f': f0 + SNAP_FRAMES, 's': s, 'x': fx, 'y': fy, 'ease': 'snap', 'dur': SNAP_FRAMES})
                transitions.append({'t': t0, 'kind': 'snap'})
                snaps_left -= 1
                snap_after = t0 + dur * 0.3
            else:
                keys.append({'f': f0, 's': s, 'x': fx, 'y': fy, 'ease': 'cut'})
                transitions.append({'t': t0, 'kind': 'cut'})
        s_end = s + (0 if full else DRIFT)
        lo = t0 + (OPEN_FRAMES / fps + 0.1 if b == 0 else 0.2)
        for t in [t for t in follow if lo < t < t1 - 0.2]:    # a fast camera cut: same zoom, new face
            ff = exact.get(round(t, 3), int(round(t * fps)))
            if ff <= keys[-1]['f']:
                continue
            st = round(s + (s_end - s) * (t - t0) / max(1e-6, t1 - t0), 4)
            keys.append({'f': ff - 1, 's': st, 'x': fx, 'y': fy, 'ease': 'linear'})
            fx, fy = focus_at(shots, t + 0.05)
            keys.append({'f': ff, 's': st, 'x': fx, 'y': fy, 'ease': 'cut'})
        keys.append({'f': f1, 's': round(s_end, 4), 'x': fx, 'y': fy, 'ease': 'linear'})
    cam = []
    for f in range(frames):
        s, x, y = cam_at(keys, f)
        cam.append([round(s, 4), round(x, 1), round(y, 1)])
    return keys, cam, transitions, list(zip(starts, ends))


# ---------- captions ----------

STRIP = re.compile(r'[.,;:।॥]+$')


def display(word, upper):
    w = STRIP.sub('', word.strip())
    w = w.replace('"', '')
    return w.upper() if upper else w


def merge_tokens(words):
    """Whisper splits things like "$500" ",000" / "e" "-commerce" / "100" "%" into separate tokens."""
    out = []
    for w in words:
        t = w['w'].strip()
        if out and (t[:1] in ',%-&' or t.startswith('.0') or out[-1]['w'].endswith('-')) and len(t) > 0 \
                and w['s'] - out[-1]['e'] < 0.3:
            out[-1] = {**out[-1], 'w': (out[-1]['w'] + t).replace(' ', ''), 'e': w['e']}
        else:
            out.append(dict(w))
    return out


_METRICS = {}


def font_advances(font_file):
    """({character: advance width}, units per em) read straight from the TTF file, or None. Used to keep
    caption lines inside the frame (no extra library needed)."""
    if font_file in _METRICS:
        return _METRICS[font_file]
    res = None
    try:
        data = (FONTS / font_file).read_bytes()
        u16 = lambda o: struct.unpack('>H', data[o:o + 2])[0]                 # noqa: E731
        u32 = lambda o: struct.unpack('>I', data[o:o + 4])[0]                 # noqa: E731
        tables = {data[12 + 16 * i:16 + 16 * i]: u32(20 + 16 * i) for i in range(u16(4))}
        upm = u16(tables[b'head'] + 18)
        n_h = u16(tables[b'hhea'] + 34)
        hm = tables[b'hmtx']
        adv = [u16(hm + 4 * i) for i in range(n_h)]
        cm = tables[b'cmap']
        subs = {(u16(cm + 4 + 8 * i), u16(cm + 6 + 8 * i)): cm + u32(cm + 8 + 8 * i) for i in range(u16(cm + 2))}
        cmap = {}
        sub = subs.get((3, 10)) or subs.get((0, 4))
        if sub and u16(sub) == 12:
            for g in range(u32(sub + 12)):
                o = sub + 16 + 12 * g
                start, end, gid = u32(o), u32(o + 4), u32(o + 8)
                for cp in range(start, min(end, 0x2FFFF) + 1):
                    cmap[cp] = gid + cp - start
        else:
            sub = subs.get((3, 1)) or subs.get((0, 3))
            seg = u16(sub + 6) // 2
            ends, starts = sub + 14, sub + 16 + 2 * seg
            deltas, ranges = starts + 2 * seg, starts + 4 * seg
            for i in range(seg):
                e, s, d, r = u16(ends + 2 * i), u16(starts + 2 * i), u16(deltas + 2 * i), u16(ranges + 2 * i)
                for cp in range(s, min(e, 0xFFFE) + 1):
                    if r == 0:
                        gid = (cp + d) & 0xFFFF
                    else:
                        gid = u16(ranges + 2 * i + r + 2 * (cp - s))
                        gid = (gid + d) & 0xFFFF if gid else 0
                    if gid:
                        cmap[cp] = gid
        res = ({chr(cp): adv[min(g, n_h - 1)] for cp, g in cmap.items()}, upm)
    except Exception:
        res = None
    _METRICS[font_file] = res
    return res


def caption_width(text, style):
    """How wide a caption line is on screen (px of the 1080 frame), with outline and letter spacing."""
    m = font_advances(style.get('font_file', LATIN_FONT[1])) if style else None
    size = (style or {}).get('size', 96)
    if m:
        adv, upm = m
        em = sum(adv.get(ch, upm * 0.6) for ch in text) / upm
    else:
        em = 0.68 * len(text)                    # no font file: a fair estimate for bold capitals
    return em * size + (style or {}).get('spacing', 1) * len(text) + 2 * (style or {}).get('outline', 8)


def split_multi(words):
    """A word entry holding several words (a Roman spelling like "main na", or a fix of a misheard
    phrase) becomes one caption word per word, its time shared out by length. One entry holding a whole
    poem line used to make a caption far wider than the frame."""
    out = []
    for w in words:
        parts = w['w'].split()
        if len(parts) <= 1:
            out.append(w)
            continue
        total, t, dur = sum(len(p) for p in parts) or 1, w['s'], max(0.0, w['e'] - w['s'])
        for p in parts:
            d = dur * len(p) / total
            out.append({**w, 'w': p, 's': round(t, 3), 'e': round(t + d, 3)})
            t += d
    return out


def add_clarify(words, clarify):
    """clips.json "clarify": [[spoken words, noun], ...]. Where a clip says "इस movie" or "he" but never
    names who or what, the noun is shown in brackets right after the first time those words are said:
    IS MOVIE [RAMAYANA] KA (brackets: the usual mark of an editor's addition, so nothing is put in the
    speaker's mouth). Spoken words may be given in Devanagari or Roman. -> (words, phrases not found)."""
    out, missing = list(words), []
    for item in clarify or []:
        if not isinstance(item, (list, tuple)) or len(item) != 2 or not str(item[1]).strip():
            continue
        spoken, noun = str(item[0]), str(item[1]).strip().strip('[]')
        q = [t for t in (norm_token(x) for x in spoken.split()) if t]
        toks = [{norm_token(w['w']), norm_token(w.get('orig', ''))} for w in out]
        at = next((i for i in range(len(out) - len(q) + 1) if q and all(q[k] in toks[i + k] for k in range(len(q)))),
                  None)
        if at is None:
            missing.append(spoken)
            continue
        for k in range(at, at + len(q)):             # the words it explains stay in one caption with it
            out[k] = {**out[k], 'clar_phrase': True}
        last = out[at + len(q) - 1]
        out.insert(at + len(q), {'w': f'[{noun}]', 's': last['s'], 'e': last['e'], 'p': 1.0, 'clarify': True})
    return out, missing


def caption_groups(meta, upper=True, max_words=3, max_chars=15, max_dur=1.6, style=None, max_w=MAX_CAPTION_W):
    words, _ = add_clarify(split_multi(merge_tokens(meta['words'])), meta.get('clarify'))
    splices = meta.get('splices', [])
    # in the split-screen layout the captions sit on the seam: a group never runs across a switch
    # into or out of it (it would cover a face)
    shots = meta.get('shots', [])
    seams = [s['t0'] for p, s in zip(shots, shots[1:]) if (p.get('mode') == 'split') != (s.get('mode') == 'split')]
    # emphasis words may be given as spoken (Devanagari) or as captioned (Roman Hinglish)
    emph = {norm_token(e) for e in meta.get('emphasis', [])} - {''}
    groups, cur = [], []

    def flush():
        if cur:
            groups.append(cur.copy())
            cur.clear()
    for i, w in enumerate(words):
        text = display(w['w'], upper)
        if not text:
            continue
        if w.get('unsure'):             # the recogniser was guessing (a game voice, music): no caption
            flush()
            continue
        if w.get('clarify') and cur:    # a [noun] always shows with the words it explains
            line = ' '.join([c['text'] for c in cur] + [text])
            if (caption_width(line, style) > max_w if style else len(line) > max_chars):
                k = len(cur)
                while k > 0 and cur[k - 1].get('phrase'):
                    k -= 1
                if 0 < k < len(cur):    # too wide together: the caption breaks before the phrase instead
                    groups.append(cur[:k])
                    del cur[:k]
            cur.append({'text': text, 's': w['s'], 'e': w['e'], 'emph': False, 'clarify': True})
            continue
        if cur:
            line = ' '.join([c['text'] for c in cur] + [text])
            too_wide = caption_width(line, style) > max_w if style else len(line) > max_chars
            gap = w['s'] - cur[-1]['e']
            crosses = any(cur[-1]['e'] <= s <= w['s'] + 0.01 for s in splices) or \
                any(cur[0]['s'] < s <= w['s'] + 0.01 for s in seams)
            spoken = sum(1 for c in cur if not c.get('clarify'))      # a [noun] doesn't count as a word
            if (spoken >= max_words and not w.get('clarify')) or too_wide or gap > 0.35 or \
                    w['e'] - cur[0]['s'] > max_dur or crosses:
                flush()
        cur.append({'text': text, 's': w['s'], 'e': w['e'],
                    'emph': bool(emph & {norm_token(w['w']), norm_token(w.get('orig', ''))})})
        if w.get('clar_phrase'):
            cur[-1]['phrase'] = True
        if is_sentence_end(w['w']):
            flush()
    flush()
    out = []
    for g, nxt in zip(groups, groups[1:] + [None]):
        end = g[-1]['e'] + 0.25
        if nxt is not None:
            end = nxt[0]['s'] if nxt[0]['s'] - g[-1]['e'] < 0.6 else min(end, nxt[0]['s'])
        end = min(end, meta['duration'])
        # (max 0: a first word that starts a hair before the clip would give a negative .srt time)
        grp = {'start': round(max(0.0, g[0]['s']), 3), 'end': round(end, 3), 'words': g}
        if style:                       # one word wider than the frame allows: shrink this caption to fit
            wd = caption_width(' '.join(c['text'] for c in g), style)
            if wd > max_w:
                grp['scale'] = round(max_w / wd, 3)
        out.append(grp)
    return out


def exact_frames(meta):
    """{clip time: frame} where a shot or a part really begins, as recorded by cut (if it could)."""
    out = {round(s['t0'], 3): s['f0'] for s in meta.get('shots', []) if 'f0' in s}
    out.update({round(t, 3): f for t, f in zip(meta.get('splices', []), meta.get('splice_frames', []))})
    return out


def cut_at_seams(caps, shots, fps=FPS):
    """In the split-screen layout the captions sit on the seam, elsewhere lower down. A caption
    still on screen when the layout switches (a word stretched over a laugh, or the short hold after
    the last word) is cut in two at the switch, so each part sits at the right height for its own
    layout and never covers a face. Both parts show the same words; the second part ('cont') starts
    exactly on the first frame of the new layout."""
    seams = [(s['f0'] if 'f0' in s else int(round(s['t0'] * fps))) / fps for p, s in zip(shots, shots[1:])
             if (p.get('mode') == 'split') != (s.get('mode') == 'split')]
    out = []
    for g in caps:
        inside = [s for s in seams if g['start'] + 0.02 < s < g['end'] - 0.02]
        edges = [g['start']] + inside + [g['end']]
        for k, (a, b) in enumerate(zip(edges, edges[1:])):
            part = {**g, 'start': round(a, 3), 'end': round(b, 3)}
            if k:
                part['cont'] = True
            out.append(part)
    return out


# ---------- sound effects ----------

def sfx_cues(transitions, beats, duration, mode='auto', fps=FPS, jumps=()):
    """Sound cues: a whoosh on the opening zoom, and one on the emphasis zoom or, in a joined clip
    that jumps in time, a softer one at each jump (with the flash: a jump is heard, not hidden)."""
    if mode == 'none':
        return []
    cues, used = [], set()

    def add(role, peak_at, gain_db, prefer_len=None):
        it = sfxlib.pick(role, prefer_len, used)
        if not it:
            return
        used.add((it['file'], it['variant']))
        offset, length = it['start'], it['length']
        at = peak_at - it['peak']
        if at < 0:
            offset, length, at = offset - at, length + at, 0.0
        length = min(length, duration - at)
        if length <= 0.05:
            return
        cues.append({'file': it['file'], 'role': role, 'offset': round(offset, 3), 'length': round(length, 3),
                     'at': round(at, 3), 'gain_db': gain_db, 'norm_db': it.get('norm_db', 0)})

    add('whoosh', OPEN_FRAMES / fps * 0.5, -15, prefer_len=0.9)          # opening zoom
    if mode == 'light':
        return cues
    for t in jumps:                                                      # a jump across time
        if t > 0.5:
            add('whoosh', t, -19, prefer_len=0.7)
    snap = next((t for t in transitions if t['kind'] == 'snap'), None)
    if snap and not jumps:              # whoosh on the emphasis zoom (a clip with a jump has that one)
        add('whoosh', snap['t'] + SNAP_FRAMES / fps * 0.4, -17, prefer_len=0.9)
    return cues


def long_jumps(meta):
    """Joins that skip more than JUMP_FLASH seconds of the video (the ones cut shows with a flash)."""
    return [j for j in meta.get('jumps', []) if abs(j['gap']) > JUMP_FLASH]


def jump_labels(jumps, duration, upper=True):
    """Optional small labels at long jumps: "27 MIN LATER" for 1.6 s (off unless asked for)."""
    out = []
    for j in jumps:
        g, when = abs(j['gap']), ('later' if j['gap'] > 0 else 'earlier')
        if g >= 3600:
            h, m = int(g // 3600), int(round(g % 3600 / 60))
            txt = f'{h} hr {m} min {when}' if m else f'{h} hr {when}'
        elif g >= 90:
            txt = f'{int(round(g / 60))} min {when}'
        else:
            txt = f'{int(round(g))} sec {when}'
        out.append({'start': round(j['t'], 3), 'end': round(min(duration, j['t'] + 1.6), 3),
                    'text': txt.upper() if upper else txt})
    return out


# ---------- the plan ----------

def build(meta, brand, opts):
    fps = meta.get('fps', FPS)
    keys, cam, transitions, beats = build_camera(meta) if opts.get('zoom', True) else \
        ([], [[1.0, W / 2, H / 2]] * int(round(meta['duration'] * fps)), [], [(0, meta['duration'])])
    hindi = any(has_devanagari(w['w']) for w in meta['words'])
    # Devanagari has no capitals, so mixed captions stay in normal case (only Latin words would shout)
    upper = opts.get('uppercase', True) and not hindi
    font, font_file = (opts['font'], opts['font_file']) if opts.get('font') else (HINDI_FONT if hindi else LATIN_FONT)
    style = {'font': font, 'font_file': font_file, 'size': opts.get('size', 96), 'y': opts.get('caption_y', 1270),
             'outline': 8, 'uppercase': upper,
             # letter spacing splits Devanagari into loose letters (libass shapes glyph by glyph then)
             'spacing': 0 if hindi else 1}
    caps = caption_groups(meta, upper=upper, style=style) if opts.get('captions', True) else []
    caps = cut_at_seams(caps, meta.get('shots', []), fps)
    shot_frames = [(s.get('f0', int(round(s['t0'] * fps))), s.get('mode')) for s in meta.get('shots', [])]

    def split_at(f):                    # is frame f in the split-screen layout?
        mode = shot_frames[0][1] if shot_frames else None
        for f0, md in shot_frames:
            if f0 <= f:
                mode = md
        return mode == 'split'
    for g in caps:                      # in the split-screen layout the captions sit on the seam
        fs = int(math.ceil(g['start'] * fps - 1e-6))
        if split_at(fs):
            g['y'] = H // 2
        if fs > 0 and not g.get('cont') and split_at(fs - 1) != split_at(fs):
            g['nolead'] = True          # its one-frame early start would fall in the other layout
    return {
        'fps': fps, 'width': W, 'height': H,
        'duration': meta['duration'], 'frames': len(cam),
        'title': meta.get('title'),
        'camera_keys': keys, 'cam': cam,
        'captions': caps,
        'caption_style': style,
        'brand': brand,
        'sfx': sfx_cues(transitions, beats, meta['duration'], opts.get('sfx', 'auto'), fps,
                        jumps=[j['t'] for j in long_jumps(meta)]),
        'labels': jump_labels(long_jumps(meta), meta['duration'], upper) if opts.get('jump_label') else [],
        'transitions': transitions,
    }
