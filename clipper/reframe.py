"""Shot-aware 16:9 -> 9:16 reframing: find camera cuts, find the speaker's face in each shot,
and build an ffmpeg filter that crops each shot around the face (static crop per shot, like a
human editor would, with no jittery tracking)."""
import re
import subprocess

import cv2
import numpy as np

from .common import ASSETS, FPS, H, W

# YuNet face detector (OpenCV Zoo, MIT licence): small, fast, and handles turned heads and small faces
YUNET = ASSETS / 'models' / 'face_detection_yunet_2023mar.onnx'
_DET = {}
try:
    cv2.utils.logging.setLogLevel(cv2.utils.logging.LOG_LEVEL_ERROR)
except Exception:
    pass


def _detector(w, h):
    if 'yunet' not in _DET:
        _DET['yunet'] = cv2.FaceDetectorYN.create(str(YUNET), '', (w, h), 0.6, 0.3, 5000)
    d = _DET['yunet']
    d.setInputSize((w, h))
    return d


def scene_cuts(video, start, dur, threshold=0.30, min_shot=0.8, floor=0.08, ratio=4.0, around=12):
    """Return shot boundaries [(a, b), ...] in seconds relative to `start`.

    A frame starts a new shot when its scene score (how much the picture changed) reaches
    `threshold`, or when it reaches `floor` and is `ratio` times the median score of the `around`
    frames on each side: in dark footage (a black studio) real cuts score only 0.1-0.2 while still
    frames score ~0.001, so a fixed threshold missed every cut (the idea of PySceneDetect's adaptive
    detector). In bright footage this finds the same cuts as before."""
    cmd = ['ffmpeg', '-hide_banner', '-ss', f'{start:.3f}', '-t', f'{dur:.3f}', '-i', str(video),
           '-vf', "scale=320:-2,select='gte(scene,0)',metadata=print", '-an', '-f', 'null', '-']
    r = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='replace')
    ts = [float(m) for m in re.findall(r'pts_time:([0-9.]+)', r.stderr)]
    ss = [float(m) for m in re.findall(r'scene_score=([0-9.]+)', r.stderr)]
    sc = list(zip(ts, ss))
    times = []
    for i, (t, s) in enumerate(sc):
        if s >= threshold:
            times.append(t)
        elif s >= floor:
            near = sorted(x for _, x in sc[max(0, i - around):i] + sc[i + 1:i + 1 + around])
            if near and s >= ratio * max(near[len(near) // 2], 0.005):
                times.append(t)
    bounds = [0.0]
    for t in times:
        if t - bounds[-1] >= min_shot and dur - t >= min_shot:
            bounds.append(t)
    bounds.append(dur)
    return list(zip(bounds[:-1], bounds[1:]))


def _faces(img):
    """All face boxes (x, y, w, h) in a BGR image."""
    h, w = img.shape[:2]
    _, faces = _detector(w, h).detect(img)
    if faces is None:
        return []
    return [tuple(float(v) for v in f[:4]) for f in faces if f[2] >= 18]


def face_in_shot(cap, t0, t1, samples=5):
    """Median face centre (cx, cy as 0..1) and size (0..1 of frame height), or None."""
    pts = []
    for k in range(samples):
        t = t0 + (t1 - t0) * (k + 0.5) / samples
        cap.set(cv2.CAP_PROP_POS_MSEC, t * 1000)
        ok, frame = cap.read()
        if not ok:
            continue
        h0, w0 = frame.shape[:2]
        scale = 640 / w0
        small = cv2.resize(frame, (640, int(h0 * scale)))
        faces = _faces(small)
        if faces:
            x, y, w, h = max(faces, key=lambda b: b[2] * b[3])
            sh = small.shape[0]
            pts.append(((x + w / 2) / 640, (y + h / 2) / sh, h / sh))
    if len(pts) < max(2, samples // 3):
        return None
    a = np.array(pts)
    return tuple(float(v) for v in np.median(a, axis=0))


SAMPLE_STEP = 0.4        # seconds between the frames checked for faces inside a shot
LAYOUT_JUMP = 0.12       # a face this far (share of the width) from where it was is somewhere else
LAYOUT_MIN_RUN = 0.8     # a new layout must last at least this long (seconds)
VISUAL_CHANGE = 25.0     # mean pixel change (0-255) between checks that means the picture itself changed
CLUSTER_TOL = 0.08       # faces within this share of the width are the same subject
MINOR_FACE = 0.5         # faces under half the size of the biggest one in a frame are background
RIVAL = 0.6              # a second subject scoring at least this share of the first one is a real rival
TOGETHER = 0.5           # ... and seen in the same frame at least this share of the time (else it's one person)


def sample_faces(cap, t0, t1, step=SAMPLE_STEP):
    """[(t, [(cx, cy, h), ...], thumb)] every significant face (shares of the frame) every `step`
    seconds, read in one pass, plus a tiny grey picture to measure layout changes. Small background
    faces (posters, people far behind) are left out."""
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    every = max(1, int(round(step * fps)))
    cap.set(cv2.CAP_PROP_POS_MSEC, t0 * 1000)
    out, n = [], 0
    while True:
        if not cap.grab():
            break
        t = cap.get(cv2.CAP_PROP_POS_MSEC) / 1000
        if t >= t1:
            break
        if n % every == 0:
            ok, frame = cap.retrieve()
            if ok:
                h0, w0 = frame.shape[:2]
                small = cv2.resize(frame, (640, int(h0 * 640 / w0)))
                sh = small.shape[0]
                faces = [((x + w / 2) / 640, (y + h / 2) / sh, h / sh) for x, y, w, h in _faces(small)]
                big = max((f[2] for f in faces), default=0)
                thumb = cv2.resize(cv2.cvtColor(small, cv2.COLOR_BGR2GRAY), (64, 36)).astype(np.float32)
                out.append((t, [f for f in faces if f[2] >= MINOR_FACE * big], thumb))
        n += 1
    return out


def _main(faces):
    return max(faces, key=lambda f: f[2]) if faces else None


def _layout_change(prev, cur):
    """True when the picture changes a lot AND the main face is gone at that moment (replaced by
    other faces, or by none): an inserted photo, slide or B-roll clip. Two people swapping which
    face is biggest, a turned head or a person moving around are not layout changes."""
    if float(np.abs(cur[2] - prev[2]).mean()) < VISUAL_CHANGE:
        return False
    main = _main(prev[1])
    if main is None:
        return bool(cur[1])
    return not any(abs(f[0] - main[0]) < LAYOUT_JUMP for f in cur[1])


def layout_splits(samples, t0, t1):
    """Split one camera shot where its layout changes and stays changed, for cuts the scene
    detector misses (soft or similar-looking cuts to a photo, slide or B-roll). Returns [(a, b)]
    absolute times; pieces shorter than LAYOUT_MIN_RUN join the piece before them."""
    starts = [0] + [i for i in range(1, len(samples)) if _layout_change(samples[i - 1], samples[i])]
    pieces = []
    for k, i in enumerate(starts):
        j = starts[k + 1] - 1 if k + 1 < len(starts) else len(samples) - 1
        dur = samples[j][0] - samples[i][0] + SAMPLE_STEP
        if pieces and dur < LAYOUT_MIN_RUN - 1e-6:      # (1e-6: 0.4 + 0.4 must count as 0.8)
            pieces[-1][1] = j
        else:
            pieces.append([i, j])
    if len(pieces) > 1 and samples[pieces[0][1]][0] - samples[pieces[0][0]][0] + SAMPLE_STEP < LAYOUT_MIN_RUN - 1e-6:
        pieces[1][0] = pieces[0][0]
        pieces.pop(0)
    bounds = [t0] + [(samples[p[0]][0] + samples[p[0] - 1][0]) / 2 for p in pieces[1:]] + [t1]
    return list(zip(bounds[:-1], bounds[1:]))


def choose_subject(samples, crop_frac, min_hits):
    """Where the crop should look for one piece of a shot. Faces are grouped by position across the
    sampled frames (never averaged across different people). Returns (face or None, info):
      one subject           -> centre on it
      two that fit together -> centre between them (both stay in frame)
      two far apart         -> the bigger / more present one; info['ambiguous'] = True
    face = (cx, cy, size) as shares of the frame; info['subjects'] lists every subject found."""
    clusters = []                      # [cx_ref, [faces...], set(sample indexes), size_ref]
    for i, (_, faces, *_rest) in enumerate(samples):
        for f in faces:
            # big faces (close-ups) wobble more: two detections less than ~a face-width apart are one person
            c = next((c for c in clusters if abs(c[0] - f[0]) < max(CLUSTER_TOL, 0.3 * max(f[2], c[3]))), None)
            if c is None:
                clusters.append([f[0], [f], {i}, f[2]])
            else:
                c[1].append(f)
                c[2].add(i)
    clusters = _same_person([c for c in clusters if len(c[2]) >= min_hits])
    subj = []
    for _, fs, hits, _size in clusters:
        if len(hits) >= min_hits:
            med = tuple(float(v) for v in np.median(np.array(fs), axis=0))
            subj.append({'face': med[:3], 'hits': len(hits), 'seen': hits, 'score': len(hits) * med[2]})
    subj.sort(key=lambda s: -s['score'])
    info = {'subjects': [round(s['face'][0], 3) for s in subj], 'ambiguous': False,
            'faces': [tuple(round(v, 4) for v in s['face']) for s in subj]}
    if not subj:
        return None, info
    best = subj[0]
    # a rival is a second person only if both are seen in the same frames: two places one person was
    # in (leaning, or two layouts the cut detection missed) are never on screen together
    rival = next((s for s in subj[1:] if s['score'] >= RIVAL * best['score']
                  and len(s['seen'] & best['seen']) >= TOGETHER * min(len(s['seen']), len(best['seen']))), None)
    if rival is None:
        return best['face'], info
    a, b = sorted([best['face'], rival['face']], key=lambda f: f[0])
    # both fit when the left face's left edge and the right face's right edge fit in one crop
    span = (b[0] - a[0]) + (a[2] + b[2]) * 0.5 * 9 / 16
    if span <= crop_frac * 0.9:
        return ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2, max(a[2], b[2])), info
    # too far apart for one crop. Who is talking can't be told reliably from the picture alone (a
    # laughing listener moves more than the talker), so keep the bigger / more present one, flag it,
    # and let the AI editor (who reads who says what) override with "framing" in clips.json.
    info['ambiguous'] = True
    info['pair'] = [tuple(round(v, 4) for v in a), tuple(round(v, 4) for v in b)]     # left, right person
    pick = best if best['score'] > 1.1 * rival['score'] else min(best, rival, key=lambda s: s['face'][0])
    return pick['face'], info


def _same_person(clusters):
    """Join groups of face detections that are one person who moved: never seen in the same frame
    and less than about one and a half face-widths apart (a laugh, a lean, a turned head)."""
    out = []
    for c in sorted(clusters, key=lambda c: -len(c[2])):
        cx, size = float(np.median([f[0] for f in c[1]])), float(np.median([f[2] for f in c[1]]))
        home = None
        for o in out:
            ox, osize = float(np.median([f[0] for f in o[1]])), float(np.median([f[2] for f in o[1]]))
            near = abs(cx - ox) <= max(CLUSTER_TOL, 1.5 * max(size, osize) * 9 / 16)
            if near and len(c[2] & o[2]) <= 0.1 * min(len(c[2]), len(o[2])):
                home = o
                break
        if home is None:
            out.append([c[0], list(c[1]), set(c[2]), c[3]])
        else:
            home[1].extend(c[1])
            home[2] |= c[2]
    return out


def refine_split(cap, t_prev, t_next, new_pos):
    """The exact time between two sampled frames where the new layout begins: the first frame whose
    main face is at the new position (or has no face, when the new layout has none)."""
    cap.set(cv2.CAP_PROP_POS_MSEC, t_prev * 1000)
    while cap.grab():
        t = cap.get(cv2.CAP_PROP_POS_MSEC) / 1000
        if t >= t_next:
            break
        if t <= t_prev:
            continue
        ok, frame = cap.retrieve()
        if not ok:
            continue
        h0, w0 = frame.shape[:2]
        small = cv2.resize(frame, (640, int(h0 * 640 / w0)))
        m = _main([((x + w / 2) / 640, 0, h / small.shape[0]) for x, y, w, h in _faces(small)])
        if (m is None and new_pos is None) or (m is not None and new_pos is not None and abs(m[0] - new_pos) < LAYOUT_JUMP):
            return t
    return (t_prev + t_next) / 2


def analyse_range(video, start, dur, src_w, src_h):
    """Shots for one source range: [{'a','b','face': (cx,cy,size)|None, 'subjects', 'ambiguous'}]
    (times relative to start). A camera shot with one steady subject keeps the classic 5-frame median;
    shots whose layout changes are split, and shots with several subjects get choose_subject()."""
    shots = scene_cuts(video, start, dur)
    cap = cv2.VideoCapture(str(video))
    crop_frac = crop_width(src_w, src_h) / src_w
    out = []
    for a, b in shots:
        samples = sample_faces(cap, start + a, start + b)
        pieces = layout_splits(samples, start + a, start + b) if samples else [(start + a, start + b)]
        if len(pieces) > 1:            # move each split onto the exact frame where the layout changes
            edges = [pieces[0][0]]
            for pa, pb in pieces[1:]:
                before = [s for s in samples if s[0] < pa]
                after = [s for s in samples if s[0] >= pa]
                if before and after:
                    m = _main(after[0][1])
                    pa = refine_split(cap, before[-1][0], after[0][0], m[0] if m else None)
                edges.append(pa)
            edges.append(pieces[-1][1])
            pieces = list(zip(edges[:-1], edges[1:]))
        found = []
        for pa, pb in pieces:
            face, info = _subject_between(samples, pa, pb, crop_frac)
            # a split that changes nothing (the face is back where it was after a flash or a blur)
            # is not a new layout: join it to the piece before
            if found and _same_framing(found[-1], face, info, pb - pa):
                pa = found[-1]['a']
                face, info = _subject_between(samples, pa, pb, crop_frac)
                found.pop()
            found.append({'a': pa, 'b': pb, 'face': face, 'info': info})
        for f in found:
            face, info = f['face'], f['info']
            if len(found) == 1:
                # no layout change inside this camera shot: keep the classic 5-frame median, so
                # ordinary shots frame exactly as before (the subjects found are still reported)
                face = face_in_shot(cap, start + a, start + b)
            out.append({'a': f['a'] - start, 'b': f['b'] - start, 'face': face, 'subjects': info['subjects'],
                        'faces': info['faces'], 'pair': info.get('pair'),
                        'ambiguous': info['ambiguous']})
    cap.release()
    return out


def _subject_between(samples, pa, pb, crop_frac):
    ps = [s for s in samples if pa <= s[0] < pb]
    return choose_subject(ps, crop_frac, max(2, len(ps) // 3))


def _same_framing(prev, face, info, dur):
    """True when a piece would be framed just like the piece before it: one plain subject at the
    same spot, no face in either, or a faceless moment too short to be anything but a missed
    detection (plan_shots gives those the face before them anyway)."""
    if prev['info']['ambiguous'] or info['ambiguous']:
        return False
    if face is None and prev['face'] is not None:
        return dur < 1.0
    if prev['face'] is None or face is None:
        return prev['face'] is None and face is None
    return abs(prev['face'][0] - face[0]) <= 0.03 and abs(prev['face'][2] - face[2]) <= 0.25 * max(prev['face'][2], face[2])


def crop_width(src_w, src_h):
    return min(src_w, int(src_h * 9 / 16) // 2 * 2)


def crop_x(cx, src_w, src_h):
    cw = crop_width(src_w, src_h)
    return int(min(max(cx * src_w - cw / 2, 0), src_w - cw)) // 2 * 2


def plan_shots(shots, src_w, src_h, min_fit=1.0):
    """Decide a crop (or 'fit' layout) for each shot. A shot with no face (quote card, slide, screen
    recording, wide b-roll) is shown whole over a blurred background, so no text gets cut off.
    Very short faceless shots (< min_fit s, usually a missed detection) reuse the nearest face."""
    is_vertical = src_w / src_h < 0.75
    known = [s['face'] for s in shots if s['face']]
    plan, last = [], (known[0] if known else None)
    for s in shots:
        face = s['face'] or (last if s['b'] - s['a'] < min_fit else None)
        if s['face']:
            last = s['face']
        if is_vertical:
            mode, x0, fx, fy = 'vertical', 0, (face[0] if face else 0.5) * W, (face[1] if face else 0.4) * H
        elif face is None:
            mode, x0, fx, fy = 'fit', 0, W / 2, H * 0.42
        else:
            cw = crop_width(src_w, src_h)
            x0 = crop_x(face[0], src_w, src_h)
            mode = 'crop'
            fx = (face[0] * src_w - x0) / cw * W
            fy = face[1] * H
        plan.append({**s, 'mode': mode, 'x0': x0, 'focus': [round(fx), round(fy)]})
    return plan


def split_box(face, src_w, src_h, x_lo=0, x_hi=None):
    """Source rectangle (x, y, w, h) for one half of the split-screen layout: a 9:8 box around a face
    (cx, cy, size as shares of the frame) with room for the shoulders, kept inside the frame, and
    inside [x_lo, x_hi] when given (the person's own side of a side-by-side picture, so no strip of
    the other camera shows at the edge)."""
    cx, cy, fh = face
    x_lo = (int(x_lo) + 1) // 2 * 2
    x_hi = src_w if x_hi is None else int(x_hi)
    bh = min(src_h, max(fh * src_h * 2.4, src_h * 0.45))
    bw = min(x_hi - x_lo, bh * W / (H / 2))
    bh = bw * (H / 2) / W
    x = min(max(cx * src_w - bw / 2, x_lo), x_hi - bw)
    y = min(max(cy * src_h - bh * 0.42, 0), src_h - bh)
    return int(x) // 2 * 2, int(y) // 2 * 2, int(bw) // 2 * 2, int(bh) // 2 * 2


def shot_filter(inp, shot, src_w, src_h, label, fps=FPS):
    """ffmpeg filter chain turning one shot of input `inp` into 1080x1920 [label]."""
    trim = f"trim=start={shot['a']:.3f}:end={shot['b']:.3f},setpts=PTS-STARTPTS"
    tail = f'setsar=1,fps={fps},format=yuv420p'
    if shot['mode'] == 'split':                  # two people stacked: top half and bottom half
        (tx, ty, tw, th), (bx, by, bw, bh) = shot['top'], shot['bottom']
        half = H // 2
        return (f"[{inp}]{trim},split[{label}t][{label}u];"
                f"[{label}t]crop={tw}:{th}:{tx}:{ty},scale={W}:{half}:flags=lanczos,setsar=1[{label}tt];"
                f"[{label}u]crop={bw}:{bh}:{bx}:{by},scale={W}:{half}:flags=lanczos,setsar=1[{label}uu];"
                f"[{label}tt][{label}uu]vstack=inputs=2,{tail}[{label}]")
    if shot['mode'] == 'vertical':
        return (f"[{inp}]{trim},scale={W}:{H}:force_original_aspect_ratio=increase:flags=lanczos,"
                f"crop={W}:{H},{tail}[{label}]")
    if shot['mode'] == 'fit':
        return (f"[{inp}]{trim},split[{label}b][{label}f];"
                f"[{label}b]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},"
                f"boxblur=30:3,eq=brightness=-0.08[{label}bb];"
                f"[{label}f]scale={W}:-2:flags=lanczos[{label}ff];"
                f"[{label}bb][{label}ff]overlay=0:(H-h)/2*0.85,{tail}[{label}]")
    cw = crop_width(src_w, src_h)
    return (f"[{inp}]{trim},crop={cw}:{src_h}:{shot['x0']}:0,scale={W}:{H}:flags=lanczos,"
            f"{tail}[{label}]")
