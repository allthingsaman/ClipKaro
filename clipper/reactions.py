"""Silent reactions (v2.12): a listener's strong laugh or shock that makes no sound.

    python run.py reactions <project>      the whole video, for the picking hints (fetch runs it for talk videos)

Why: in a podcast the listener often cracks up or looks shocked without a sound. ClipKaro hears laughs, so it
missed these: the moment wasn't marked for picking, and the camera stayed on the speaker. The owner's rule: only
STRONG reactions.

How (research, Nov 2026): faces are found with YuNet (already ClipKaro's face finder), and each face's expression
is read by EmotiEffLib's (HSEmotion) `enet_b0_8_best_vgaf` model (Apache 2.0; 16 MB, downloaded the first time;
trained on the AffectNet research dataset): 8 expressions, of which happiness and surprise are used. A face is
reacting strongly when happiness reaches HAPPY_ON (or surprise SURPRISE_ON) in at least MIN_RUN samples in a row
at SAMPLE_FPS (so a split-second grin or a blink doesn't count). It is SILENT when no laugh is heard then
(sound.py) and, at cut, when that face isn't the one talking.

It is used twice:
  - picking: a hint next to the words, "[a silent laugh on screen ~2 s]" / "[shock on a face ~1 s]"
    (transcript/reactions.json, talk videos only; gameplay has its own hints);
  - framing: in a two-person shot the director shows both people (a split screen) while the listener reacts
    silently, as it already does around a heard laugh (cut.two_person, director.direct `reactions`).
"""
import argparse
import subprocess
import time

import numpy as np

from .common import load_json, project_dir, save_json

REACTIONS_V = 1
MODEL = ('https://raw.githubusercontent.com/sb-ai-lab/EmotiEffLib/main/models/affectnet_emotions/onnx/'
         'enet_b0_8_best_vgaf.onnx', 'enet_b0_8_best_vgaf.onnx')
LABELS = ['anger', 'contempt', 'disgust', 'fear', 'happiness', 'neutral', 'sadness', 'surprise']
SAMPLE_FPS = 3.0             # faces read this often (2 for the whole video: the hints)
HAPPY_ON = 0.95              # a strong laugh: happiness at least this sure (a broad smile reaches 0.9: tested) ...
SURPRISE_ON = 0.85           # ... or a strong shock: surprise at least this sure (0.6 caught people mid-word: tested)
MIN_RUN = 2                  # ... in at least this many samples in a row
JOIN = 0.8                   # reactions of one face closer than this are one
HINT_FPS = 1.0               # the whole video is read once a second (2 readings in a row = a 2 s laugh): about
                             # 4 minutes per hour of a two-person podcast on the processor (2 a second took 8)
HINTS_PER_10_MIN = 4         # the whole video's hints: only the strongest few laughs (shock only at cut, where the
                             # person talking is known: a face asking a question reads as surprise)
MIN_FACE = 0.08              # faces smaller than this share of the frame height are too small to read
MARGIN = 0.12                # the face crop is the face box grown by this share on each side
_SESSION = {}


def session():
    """The expression model (onnxruntime), or None when it can't be had (offline the first time)."""
    if 'm' in _SESSION:
        return _SESSION['m']
    try:
        import onnxruntime as ort
        from . import speakers
        speakers.MODELS.setdefault('expressions', MODEL)
        path = speakers.model_file('expressions')
        _SESSION['m'] = ort.InferenceSession(str(path), providers=['CPUExecutionProvider']) if path else None
    except Exception:
        _SESSION['m'] = None
    return _SESSION['m']


def expressions(img, box, sess=None):
    """{'happiness': p, 'surprise': p, ...} (probabilities) of the face in box (x, y, w, h) of a BGR image."""
    import cv2
    sess = sess or session()
    h, w = img.shape[:2]
    x, y, bw, bh = box
    mx, my = bw * MARGIN, bh * MARGIN
    x0, y0 = int(max(0, x - mx)), int(max(0, y - my))
    x1, y1 = int(min(w, x + bw + mx)), int(min(h, y + bh + my))
    face = img[y0:y1, x0:x1]
    if face.size == 0:
        return None
    rgb = cv2.cvtColor(cv2.resize(face, (224, 224)), cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0
    rgb = (rgb - np.array([0.485, 0.456, 0.406], np.float32)) / np.array([0.229, 0.224, 0.225], np.float32)
    x_in = rgb.transpose(2, 0, 1)[None]
    logits = sess.run(None, {sess.get_inputs()[0].name: x_in})[0][0]
    e = np.exp(logits - logits.max())
    p = e / e.sum()
    return {k: round(float(v), 3) for k, v in zip(LABELS, p)}


def frames(video, a, b, fps):
    """(time, BGR frame) from a to b seconds, fps a second (ffmpeg, scaled to 720 px high at most)."""
    from .common import probe
    try:
        info = probe(str(video))                 # (OpenCV can't open every codec: AV1 downloads)
        W, H = int(info['width']), int(info['height'])
    except (SystemExit, Exception):
        return
    if not W or not H:
        return
    k = min(1.0, 720 / H)
    w, h = int(W * k) // 2 * 2, int(H * k) // 2 * 2
    p = subprocess.Popen(['ffmpeg', '-v', 'error', '-ss', f'{a:.3f}', '-t', f'{b - a:.3f}', '-i', str(video), '-an',
                          '-vf', f'fps={fps},scale={w}:{h}', '-f', 'rawvideo', '-pix_fmt', 'bgr24', '-'],
                         stdout=subprocess.PIPE)
    size, n = w * h * 3, 0
    try:
        while True:
            buf = p.stdout.read(size)
            if len(buf) < size:
                break
            yield a + n / fps, np.frombuffer(buf, np.uint8).reshape(h, w, 3)
            n += 1
    finally:
        p.stdout.close()
        p.wait()


def side_of(box, width):
    return 'L' if box[0] + box[2] / 2 < width / 2 else 'R'


def read(video, a, b, fps=SAMPLE_FPS, two=None):
    """Samples [(t, {'L': {...}, 'R': {...}})] of the faces' expressions from a to b. two: the two faces' x
    centres (source pixels as fractions of the width) when known (a two-person shot), else left / right halves."""
    from .reframe import _faces
    sess = session()
    if sess is None:
        return None
    out = []
    for t, img in frames(video, a, b, fps):
        h, w = img.shape[:2]
        faces = [f for f in _faces(img) if f[3] >= MIN_FACE * h]
        faces = sorted(faces, key=lambda f: -f[2] * f[3])[:2]
        row = {}
        for f in faces:
            if two:
                cx = (f[0] + f[2] / 2) / w
                s = 'L' if abs(cx - min(two)) <= abs(cx - max(two)) else 'R'
            else:
                s = side_of(f, w)
            if s in row:
                continue
            ex = expressions(img, f[:4], sess)
            if ex:
                row[s] = ex
        out.append((round(t, 2), row))
    return out


def strong(samples, fps=SAMPLE_FPS):
    """[(start, end, side, 'laugh' | 'shock', strength)] of the strong reactions in the samples."""
    out = []
    for side in ('L', 'R'):
        for kind, key, on in (('laugh', 'happiness', HAPPY_ON), ('shock', 'surprise', SURPRISE_ON)):
            run = []
            for t, row in samples + [(None, {})]:
                v = (row.get(side) or {}).get(key, 0.0)
                if t is not None and v >= on:
                    run.append((t, v))
                    continue
                if len(run) >= MIN_RUN:
                    s, e = run[0][0], run[-1][0] + 1 / fps
                    peak = max(x for _, x in run)
                    if out and out[-1][2] == side and out[-1][3] == kind and s - out[-1][1] <= JOIN:
                        out[-1] = (out[-1][0], round(e, 2), side, kind, max(out[-1][4], round(peak, 3)))
                    else:
                        out.append((round(s, 2), round(e, 2), side, kind, round(peak, 3)))
                run = []
    return sorted(out)


def silent(reacts, laughs, talking=None):
    """The reactions with no laugh heard then (laughs: [(s, e)] from sound.py), and, when `talking(a, b, side)` is
    given, not by the person talking then."""
    keep = []
    for r in reacts:
        s, e, side = r[0], r[1], r[2]
        if any(x < e and s < y for x, y in laughs):
            continue
        if talking and talking(s, e, side):
            continue
        keep.append(r)
    return keep


# ---------------------------------------------------------------- the whole video (picking hints)

def wanted(project):
    from .kind import is_irregular
    from .common import settings
    return settings().get('silent_reactions', True) and not is_irregular(project)


def scan(pdir, quiet=False):
    """The whole video at HINT_FPS -> transcript/reactions.json (talk videos with the video here)."""
    from .kind import _video_file
    from . import sound
    project = load_json(pdir / 'project.json', {}) or {}
    video = _video_file(pdir, project)
    if not video or not wanted(project):
        return None
    t0 = time.time()
    dur = float(project.get('duration') or 0)
    if not dur:
        return None
    samples = read(video, 0.0, dur, fps=HINT_FPS)
    if samples is None:
        if not quiet:
            print('   (silent reactions skipped: the expression model is not available)')
        return None
    cues = sound.load(pdir) or {}
    laughs = [(a, b) for a, b, *_ in cues.get('laughter', [])]
    from .hints import rare
    found = rare([r for r in silent(strong(samples, fps=HINT_FPS), laughs) if r[3] == 'laugh'],
                 lambda r: r[4] * (r[1] - r[0]), HINTS_PER_10_MIN)
    r = {'v': REACTIONS_V, 'reactions': [list(x) for x in found], 'two_faces': round(
        sum(1 for _, row in samples if len(row) == 2) / max(1, len(samples)), 2), 'seconds': round(time.time() - t0, 1)}
    save_json(pdir / 'transcript' / 'reactions.json', r)
    if not quiet:
        print(f"-> silent reactions in {r['seconds']:.0f}s: {len(found)} strong one(s)")
    return r


def load(pdir):
    r = load_json(pdir / 'transcript' / 'reactions.json')
    return r if r and r.get('v') == REACTIONS_V else None


def ensure(pdir, quiet=False):
    return load(pdir) or scan(pdir, quiet=quiet)


def notes(pdir):
    """Hint events [(start, end, text)] for hints.event_notes."""
    r = load(pdir)
    out = []
    for s, e, side, kind, _ in (r or {}).get('reactions', []):
        n = max(1, round(e - s))
        out.append((s, e, f'[a silent laugh on screen ~{n} s]' if kind == 'laugh' else f'[shock on a face ~{n} s]'))
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('project')
    a = ap.parse_args()
    pdir = project_dir(a.project)
    if scan(pdir) is None:
        print('nothing read: a gameplay video, no video yet, or "silent_reactions": false')
        return
    from .fetch import render_transcript
    render_transcript(pdir, load_json(pdir / 'project.json', {}) or {},
                      load_json(pdir / 'transcript' / 'sentences.json') or [])


if __name__ == '__main__':
    main()
