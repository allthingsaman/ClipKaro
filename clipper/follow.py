"""Following a person who moves (v2.15): the crop pans with someone walking across a still camera's picture.

Before, every camera shot got one fixed crop around the speaker's face (a human editor's choice for people who sit
still). A teacher walking along the board, a speaker crossing a stage or a vlogger stepping aside walked out of that
crop. Now, when the person in a shot moves so far that the fixed crop would lose them, the crop follows them like a
camera operator: it holds still while they move a little, and pans smoothly to centre them again when they move
away. Shots where the person stays put keep their fixed crop, exactly as before.

How (research, November 2026):
  - where the person is: the face finder's faces (already read every 0.4 s for each shot); when the face can't be
    seen (turned to the board, too small, a hand in front), a person detector finds the body: YOLOX-Nano (Megvii,
    Apache 2.0, 3.6 MB, downloaded the first time; not the AGPL Ultralytics models). Each sample takes the face or
    body nearest to where the person was (they can't jump across the picture between samples);
  - the camera: a dead zone (small moves don't move it), then a smooth, eased pan (smoothed forwards and backwards,
    so it starts gently), with a top speed; written as a moving crop for FFmpeg (no new tools);
  - the way back: settings.json "follow_moving": false keeps one fixed crop per shot; a hand-picked framing in
    clips.json ("left", "right", a number) is always a fixed crop.
"""
import numpy as np

from .common import settings

MODEL = ('https://github.com/Megvii-BaseDetection/YOLOX/releases/download/0.1.1rc0/yolox_nano.onnx', 'yolox_nano.onnx')
SIZE = 416                 # the detector's input (pixels, square)
PERSON_ON = 0.45           # a person box at least this sure
NMS_IOU = 0.45
MIN_PERSON = 0.25          # a body shorter than this share of the picture is someone in the background
SPOT = 0.03               # faces this close (share of the width) are at one spot (pictures: they never move)
UNSEEN = 0.25              # a shot whose face is missing this share of the time is checked with the bodies too
EDGE = 0.30                # the fixed crop loses the person when they are this far (share of the crop's width) from
                           # its middle ...
EDGE_FOR = 0.8             # ... for at least this long (seconds): then the crop follows
JUMP = 0.22                # a face or body this far (share of the picture's width) from the last place is someone else
DEAD = 0.12                # the camera holds while the person stays within this share of the crop's width of its aim
SMOOTH = 0.45              # seconds: how gently the camera eases into a pan
SPEED = 0.55               # the camera's top speed: this share of the picture's width per second
_SESSION = {}


def wanted():
    return settings().get('follow_moving', True) is not False


def session():
    """The person detector (onnxruntime), or None when it can't be had (offline the first time)."""
    if 'm' in _SESSION:
        return _SESSION['m']
    try:
        import onnxruntime as ort
        from . import speakers
        speakers.MODELS.setdefault('people', MODEL)
        path = speakers.model_file('people')
        _SESSION['m'] = ort.InferenceSession(str(path), providers=['CPUExecutionProvider']) if path else None
    except Exception:
        _SESSION['m'] = None
    return _SESSION['m']


def _grids():
    if 'g' not in _SESSION:
        grids, strides = [], []
        for s in (8, 16, 32):
            n = SIZE // s
            yv, xv = np.meshgrid(np.arange(n), np.arange(n), indexing='ij')
            grids.append(np.stack((xv, yv), 2).reshape(-1, 2))
            strides.append(np.full((n * n, 1), s))
        _SESSION['g'] = (np.concatenate(grids).astype(np.float32), np.concatenate(strides).astype(np.float32))
    return _SESSION['g']


def people(img, sess=None):
    """[(cx, top, w, h, score)] of the people in a BGR picture, as shares of its width and height, biggest first."""
    import cv2
    sess = sess or session()
    if sess is None:
        return []
    h, w = img.shape[:2]
    r = min(SIZE / h, SIZE / w)
    pad = np.full((SIZE, SIZE, 3), 114, np.uint8)
    pad[:int(h * r), :int(w * r)] = cv2.resize(img, (int(w * r), int(h * r)), interpolation=cv2.INTER_LINEAR)
    x = pad.transpose(2, 0, 1)[None].astype(np.float32)
    out = sess.run(None, {sess.get_inputs()[0].name: x})[0][0]
    grids, strides = _grids()
    xy = (out[:, :2] + grids) * strides
    wh = np.exp(out[:, 2:4]) * strides
    score = out[:, 4] * out[:, 5]                     # object x "person" (COCO class 0)
    keep = score >= PERSON_ON
    if not keep.any():
        return []
    xy, wh, score = xy[keep] / r, wh[keep] / r, score[keep]
    boxes = [[float(a - c / 2), float(b - d / 2), float(c), float(d)] for (a, b), (c, d) in zip(xy, wh)]
    idx = cv2.dnn.NMSBoxes(boxes, [float(s) for s in score], PERSON_ON, NMS_IOU)
    found = []
    for i in np.array(idx).reshape(-1):
        bx, by, bw, bh = boxes[i]
        if bh / h >= MIN_PERSON:
            found.append(((bx + bw / 2) / w, max(0.0, by / h), bw / w, bh / h, float(score[i])))
    return sorted(found, key=lambda p: -p[3])


def needs_follow(pos, cx_fixed, crop_frac, step):
    """True when, with the fixed crop centred at cx_fixed, the person (pos: x shares, None where unknown) is out
    towards its edge for EDGE_FOR seconds in a row."""
    run = 0.0
    for p in pos:
        if p is not None and abs(p - cx_fixed) > EDGE * crop_frac:
            run += step
            if run >= EDGE_FOR - 1e-6:
                return True
        else:
            run = 0.0
    return False


def fill(pos):
    """Unknown positions filled in: in between, from the two sides; at the ends, the nearest known one."""
    known = [i for i, p in enumerate(pos) if p is not None]
    if not known:
        return None
    out = list(pos)
    for i in range(len(out)):
        if out[i] is None:
            a = max((k for k in known if k < i), default=None)
            b = min((k for k in known if k > i), default=None)
            if a is None or b is None:
                out[i] = pos[a if b is None else b]
            else:
                out[i] = pos[a] + (pos[b] - pos[a]) * (i - a) / (b - a)
    return out


def camera(pos, step, crop_frac):
    """The crop's centre (shares of the width) at each sample, for the filled positions: a dead zone, then a smooth
    pan forwards and backwards (no lag, eased start and stop), at most SPEED."""
    med = [float(np.median(pos[max(0, i - 1):i + 2])) for i in range(len(pos))]   # one wrong sample: ignored
    aim, out = med[0], []
    for p in med:
        if abs(p - aim) > DEAD * crop_frac:
            aim = p
        out.append(aim)
    k = 1 - np.exp(-step / SMOOTH)
    for order in (range(len(out)), range(len(out) - 1, -1, -1)):
        v = None
        for i in order:
            v = out[i] if v is None else v + k * (out[i] - v)
            out[i] = v
    top = SPEED * step
    for i in range(1, len(out)):
        out[i] = out[i - 1] + max(-top, min(top, out[i] - out[i - 1]))
    lo, hi = crop_frac / 2, 1 - crop_frac / 2
    return [min(max(c, lo), hi) for c in out]


def simplify(points, tol):
    """Fewer keyframes for a path [(t, x)], none further than tol from the line between its neighbours."""
    if len(points) < 3:
        return list(points)
    (t0, x0), (t1, x1) = points[0], points[-1]
    worst, at = 0.0, 0
    for i in range(1, len(points) - 1):
        t, x = points[i]
        d = abs(x - (x0 + (x1 - x0) * (t - t0) / (t1 - t0 or 1)))
        if d > worst:
            worst, at = d, i
    if worst <= tol:
        return [points[0], points[-1]]
    return simplify(points[:at + 1], tol)[:-1] + simplify(points[at:], tol)


def track(samples, start_x):
    """The person's x (shares of the width) at each sample [(t, faces, ...)] from the faces alone: the face nearest
    the last place (None where there is none near)."""
    last, out = start_x, []
    for s in samples:
        near = min(s[1], key=lambda f: abs(f[0] - last), default=None)
        x = near[0] if near and abs(near[0] - last) <= JUMP else None
        out.append(x)
        if x is not None:
            last = x
    return out


def bodies(cap, times):
    """{t: [people]} at the given times of an open video, read in one pass (pictures 640 px wide, like the faces)."""
    import cv2
    out = {}
    if not times or session() is None:
        return out
    want = sorted(times)
    cap.set(cv2.CAP_PROP_POS_MSEC, want[0] * 1000)
    k = 0
    while k < len(want):
        if not cap.grab():
            break
        t = cap.get(cv2.CAP_PROP_POS_MSEC) / 1000
        if t + 1e-3 < want[k]:
            continue
        ok, frame = cap.retrieve()
        while k < len(want) and want[k] <= t + 1e-3:
            if ok:
                h0, w0 = frame.shape[:2]
                out[want[k]] = people(cv2.resize(frame, (640, int(h0 * 640 / w0))))
            k += 1
    return out


def pictures(samples, found):
    """Spots (x // SPOT) where a face is a picture (on a wall, a board, a screen): seen there again and again, almost
    never with a body under it."""
    spots = {}
    for s in samples:
        bs = found.get(s[0])
        if bs is None:
            continue
        for f in s[1]:
            c = spots.setdefault(round(f[0] / SPOT), [0, 0])
            c[0] += 1
            c[1] += any(abs(f[0] - b[0]) <= b[2] / 2 for b in bs)
    return {k for k, (n, with_body) in spots.items() if n >= 5 and with_body < 0.3 * n}


def track_both(samples, found, start_x):
    """The person's x at each sample from the faces and the bodies found ({t: [people]}): the body nearest the last
    place and the face on it (else the body's middle, moved by how far this person's face usually sits from it: a
    pointing arm widens the box); without a body, the face nearest the last place. Faces that are pictures (on a
    wall or a board) never count."""
    still = pictures(samples, found)
    def real(s):
        return [f for f in s[1] if round(f[0] / SPOT) not in still]
    pairs = []
    for s in samples:
        for f in real(s):
            b = min(found.get(s[0], []), key=lambda p: abs(p[0] - f[0]), default=None)
            if b and abs(b[0] - f[0]) < 0.15:
                pairs.append(f[0] - b[0])
    offs = float(np.median(pairs)) if pairs else 0.0
    last, out = start_x, []
    for s in samples:
        faces = real(s)
        body = min(found.get(s[0]) or [], key=lambda p: abs(p[0] + offs - last), default=None)
        if body and abs(body[0] + offs - last) <= JUMP:
            mid = body[0] + offs
            own = min(faces, key=lambda f: abs(f[0] - mid), default=None)
            x = own[0] if own and abs(own[0] - body[0]) <= body[2] / 2 else mid
        else:
            near = min(faces, key=lambda f: abs(f[0] - last), default=None)
            x = near[0] if near and abs(near[0] - last) <= JUMP else None
        out.append(x)
        if x is not None:
            last = x
    return out


def path_expr(path, a, b):
    """An FFmpeg expression for the crop's x at t (seconds from a) along path [(t, x pixels)] (times on the same
    clock as a and b): straight lines between the keyframes, written as a balanced sum of ramps (FFmpeg can't nest
    more than about 60 terms in a row)."""
    pts = sorted(path)
    inside = [(t - a, x) for t, x in pts if a < t < b]
    def x_at(t):
        if t <= pts[0][0]:
            return pts[0][1]
        for (t0, x0), (t1, x1) in zip(pts, pts[1:]):
            if t <= t1:
                return x0 + (x1 - x0) * (t - t0) / ((t1 - t0) or 1)
        return pts[-1][1]
    keys = [(0.0, x_at(a))] + inside + [(b - a, x_at(b))]
    keys = [k for i, k in enumerate(keys) if i == 0 or k[0] > keys[i - 1][0] + 1e-3]
    terms, slope = [f'{keys[0][1]:.1f}'], 0.0
    for (t0, x0), (t1, x1) in zip(keys, keys[1:]):
        s = (x1 - x0) / (t1 - t0)
        if abs(s - slope) > 1e-3:
            terms.append(f'{s - slope:.3f}*max(0\\,t-{t0:.3f})')
        slope = s
    def bal(ts):
        return ts[0] if len(ts) == 1 else f'({bal(ts[:len(ts) // 2])}+{bal(ts[len(ts) // 2:])})'
    return bal(terms)


def plan(cap, samples, pa, pb, face, start, src_w, src_h, step):
    """The moving crop for one shot piece (pa..pb, absolute seconds) with one person: keyframes [(t from the range
    start, crop x pixels)], or None when the fixed crop keeps them (most shots: nothing changes)."""
    from .reframe import crop_width, crop_x
    ps = [s for s in samples if pa <= s[0] < pb]
    if len(ps) < 5 or not wanted():
        return None
    cw = crop_width(src_w, src_h)
    crop_frac = cw / src_w
    if crop_frac >= 0.98:
        return None
    first = next((s for s in ps if s[1]), None)
    start_x = max(first[1], key=lambda f: f[2])[0] if first else face[0]
    fixed = (crop_x(face[0], src_w, src_h) + cw / 2) / src_w
    pos = track(ps, start_x)
    unseen = sum(p is None for p in pos) / len(pos)
    if not needs_follow(pos, fixed, crop_frac, step) and unseen < UNSEEN:
        return None
    pos = track_both(ps, bodies(cap, [s[0] for s in ps]), start_x)
    if not needs_follow(pos, fixed, crop_frac, step):
        return None
    cam = camera(fill(pos), step, crop_frac)
    pts = [(round(s[0] - start, 3), crop_x(c, src_w, src_h)) for s, c in zip(ps, cam)]
    return [list(p) for p in simplify(pts, 2.0)]


def x_at(sh, t):
    """The crop's left edge (pixels) of a shot at t (the shot's clock), moving or not."""
    path = sh.get('path')
    if not path:
        return sh['x0']
    if t <= path[0][0]:
        return path[0][1]
    for (t0, x0), (t1, x1) in zip(path, path[1:]):
        if t <= t1:
            return x0 + (x1 - x0) * (t - t0) / ((t1 - t0) or 1)
    return path[-1][1]
