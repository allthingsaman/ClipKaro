"""Who speaks when, and when people laugh: the signals the two-person framing ("director") needs.

Only used for clips with a two-person shot (two faces too far apart for one crop). Everything is
optional: if a model can't be downloaded or sherpa-onnx isn't installed, ClipKaro frames those shots
the way it always did.

Models (downloaded once into ~/.cache/clipkaro/models, about 50 MB in total):
- pyannote segmentation 3.0 (MIT licence) and 3D-Speaker ERes2Net, trained on VoxCeleb (Apache 2.0),
  run by sherpa-onnx (Apache 2.0), for voice diarization. On our tests ERes2Net separated a host and
  a guest cleanly, where three other voice models mixed them up.
- YAMNet (Google, Apache 2.0) for laughter: 0.48 s frames, classes Laughter / Giggle / Snicker /
  Belly laugh / Chuckle. It scored 0.00 on serious talk and fired on every joke we checked.
"""
import os
import tarfile
import time
import urllib.request
from pathlib import Path

import numpy as np

CACHE = Path(os.environ.get('CLIPKARO_CACHE', Path.home() / '.cache' / 'clipkaro')) / 'models'
MODELS = {
    'segmentation': ('https://github.com/k2-fsa/sherpa-onnx/releases/download/speaker-segmentation-models/'
                     'sherpa-onnx-pyannote-segmentation-3-0.tar.bz2',
                     'sherpa-onnx-pyannote-segmentation-3-0/model.onnx'),
    'voice': ('https://github.com/k2-fsa/sherpa-onnx/releases/download/speaker-recongition-models/'
              '3dspeaker_speech_eres2net_sv_en_voxceleb_16k.onnx',
              '3dspeaker_speech_eres2net_sv_en_voxceleb_16k.onnx'),
    'laughter': ('https://huggingface.co/audiomagic/yamnet-onnx/resolve/main/yamnet.onnx', 'yamnet.onnx'),
}
LAUGH_CLASSES = [13, 15, 16, 17, 18]     # YAMNet: Laughter, Giggle, Snicker, Belly laugh, Chuckle
LAUGH_MIN = 0.15                         # a frame scoring at least this counts as laughter
YAMNET_HOP, YAMNET_WIN = 0.48, 0.96
VOICE_THRESHOLD = 0.7                    # clustering threshold for ERes2Net voice prints
CONTEXT = 10.0                           # seconds of audio around each clip part, for steadier voice prints
SR = 16000


def model_file(name):
    """Local path of a model, downloading it (with retries) the first time. None if it can't be had."""
    url, rel = MODELS[name]
    path = CACHE / rel
    if path.exists():
        return path
    CACHE.mkdir(parents=True, exist_ok=True)
    target = CACHE / url.rsplit('/', 1)[1]
    tmp = target.with_suffix(target.suffix + '.part')
    for attempt in range(1, 4):
        try:
            print(f'   downloading the {name} model (first time only) ...', flush=True)
            with urllib.request.urlopen(url, timeout=60) as r, open(tmp, 'wb') as f:
                while True:
                    chunk = r.read(1 << 20)
                    if not chunk:
                        break
                    f.write(chunk)
            tmp.replace(target)
            break
        except Exception as e:          # network trouble: retry, then give up quietly
            print(f'   ! {name} model download failed ({type(e).__name__}); retry {attempt}/3', flush=True)
            time.sleep(3 * attempt)
    else:
        return None
    if target.name.endswith('.tar.bz2'):
        with tarfile.open(target) as tar:
            try:
                tar.extractall(CACHE, filter='data')
            except TypeError:           # an older Python without extraction filters: check by hand
                base = CACHE.resolve()
                for m in tar.getmembers():
                    dest = (CACHE / m.name).resolve()
                    if base not in dest.parents or m.issym() or m.islnk():
                        raise ValueError(f'unsafe path in {target.name}: {m.name}')
                tar.extractall(CACHE)
        target.unlink(missing_ok=True)
    return path if path.exists() else None


def load_audio(wav):
    import soundfile as sf
    audio, sr = sf.read(str(wav), dtype='float32')
    if audio.ndim > 1:
        audio = audio[:, 0]
    if sr != SR:
        raise ValueError(f'{wav} is {sr} Hz, expected {SR}')
    return audio


def windows(parts, duration):
    """Clip parts widened by CONTEXT seconds and merged: the audio stretches to analyse."""
    out = []
    for a, b in sorted(parts):
        a, b = max(0.0, a - CONTEXT), min(duration, b + CONTEXT)
        if out and a <= out[-1][1]:
            out[-1][1] = max(out[-1][1], b)
        else:
            out.append([a, b])
    return out


def voices(audio, parts):
    """[(start, end, voice_id)] in source seconds for the clip's parts (+ context), or None when
    diarization isn't available. Voice ids are only meaningful within one clip."""
    try:
        import sherpa_onnx
    except ImportError:
        return None
    seg, emb = model_file('segmentation'), model_file('voice')
    if not seg or not emb:
        return None
    threads = max(1, (os.cpu_count() or 4) - 1)
    cfg = sherpa_onnx.OfflineSpeakerDiarizationConfig(
        segmentation=sherpa_onnx.OfflineSpeakerSegmentationModelConfig(
            pyannote=sherpa_onnx.OfflineSpeakerSegmentationPyannoteModelConfig(model=str(seg)), num_threads=threads),
        embedding=sherpa_onnx.SpeakerEmbeddingExtractorConfig(model=str(emb), num_threads=threads),
        clustering=sherpa_onnx.FastClusteringConfig(num_clusters=-1, threshold=VOICE_THRESHOLD),
        min_duration_on=0.3, min_duration_off=0.5)
    sd = sherpa_onnx.OfflineSpeakerDiarization(cfg)
    out = []
    for k, (a, b) in enumerate(windows(parts, len(audio) / SR)):
        res = sd.process(audio[int(a * SR):int(b * SR)]).sort_by_start_time()
        # ids from separate windows are kept apart: window k, speaker n -> "k.n"
        out += [(round(r.start + a, 3), round(r.end + a, 3), f'{k}.{r.speaker}') for r in res]
    return out


def laughter(audio, parts):
    """[(start, end, score)] frames where the audio sounds like laughter, or None if unavailable."""
    path = model_file('laughter')
    if not path:
        return None
    try:
        import onnxruntime as ort
        sess = ort.InferenceSession(str(path), providers=['CPUExecutionProvider'])
    except Exception:
        return None
    out = []
    for a, b in windows(parts, len(audio) / SR):
        scores = sess.run(None, {'waveform': audio[int(a * SR):int(b * SR)]})[0]
        for i, row in enumerate(scores):
            s = float(row[LAUGH_CLASSES].max())
            if s >= LAUGH_MIN:
                t0 = a + i * YAMNET_HOP
                out.append((round(t0, 2), round(t0 + YAMNET_WIN, 2), round(s, 3)))
    return out


def face_activity(cap, t0, t1, subjects, step=0.25, gap=3):
    """How much each face's mouth area moves: [(t, {'L': motion, 'R': motion})] for one two-person
    stretch, where L / R are the left and right person. Moment to moment this can't tell talking from
    laughing; it is only used summed up over many calm moments, to learn which voice is which face."""
    left, right = sorted(subjects)[:1] + sorted(subjects)[-1:]
    side = {left: 'L', right: 'R'}
    import cv2
    from .reframe import _faces
    out = []
    t = t0
    while t < t1:
        cap.set(cv2.CAP_PROP_POS_MSEC, t * 1000)
        ok, a = cap.read()
        for _ in range(gap - 1):
            cap.grab()
        ok2, b = cap.read()
        if ok and ok2:
            sa, sb = cv2.resize(a, (640, 360)), cv2.resize(b, (640, 360))
            ga = cv2.cvtColor(sa, cv2.COLOR_BGR2GRAY).astype(np.float32)
            gb = cv2.cvtColor(sb, cv2.COLOR_BGR2GRAY).astype(np.float32)
            row, size = {}, {}
            for x, y, w, h in _faces(sa):
                cx = (x + w / 2) / 640
                near = min((left, right), key=lambda s: abs(s - cx))
                # per side only the biggest face: small faces in wall art or posters behind a person
                # never move, and measuring one of them made a talking guest look silent (seen)
                if abs(near - cx) > 0.12 or w * h <= size.get(side[near], 0):
                    continue
                y0, y1 = int(y + h * 0.55), int(min(360, y + h * 1.05))
                x0, x1 = int(max(0, x + w * 0.2)), int(min(640, x + w * 0.8))
                if y1 > y0 and x1 > x0:
                    row[side[near]] = float(np.abs(gb[y0:y1, x0:x1] - ga[y0:y1, x0:x1]).mean())
                    size[side[near]] = w * h
            if row:
                out.append((round(t, 3), row))
        t += step
    return out


# ---------- voice prints and the speaker register ----------
#
# Voice ids from diarization only mean something inside one clip. The register gives the same
# person the same id across all clips of a video (by comparing voice prints), and learns from calm
# moments in ANY clip which side of a two-person shot each person sits on. A funny clip, where the
# listener laughs and smiles the whole time, then still gets the right face for each voice.

SIGNALS_V = 2            # raise when voices / laughter / face_activity change: cached signals are redone
SAME_VOICE = 0.55       # voice prints at least this similar are the same person (Raj vs Khan Sir: <= 0.38)
SOFT_VOICE = 0.35        # a voice disturbed by laughter or talking-over still resembles its owner this much ...
SOFT_MARGIN = 0.2        # ... and clearly more than anyone else: treat it as that person (prints unchanged)
NEW_PERSON = 5.0         # a voice that matches nobody becomes a new person only with this many seconds
SIDE_RATIO = 1.3         # a person sits on the side whose mouth moves this much more while they talk
CLIP_MIN = 12            # a clip votes on someone's side only with at least this many calm moments


def voice_prints(audio, segs, longest=6, min_seconds=2.0):
    """{voice_id: unit-length voice print} from each voice's longest stretches (None if unavailable)."""
    try:
        import sherpa_onnx
    except ImportError:
        return None
    path = model_file('voice')
    if not path:
        return None
    ext = sherpa_onnx.SpeakerEmbeddingExtractor(sherpa_onnx.SpeakerEmbeddingExtractorConfig(
        model=str(path), num_threads=max(1, (os.cpu_count() or 4) - 1)))
    by = {}
    for a, b, v in segs:
        by.setdefault(v, []).append((a, b))
    out = {}
    for v, parts in by.items():
        if sum(b - a for a, b in parts) < min_seconds:
            continue
        st = ext.create_stream()
        for a, b in sorted(parts, key=lambda x: x[0] - x[1])[:longest]:
            st.accept_waveform(SR, audio[int(a * SR):int(b * SR)])
        st.input_finished()
        e = np.array(ext.compute(st), dtype=np.float32)
        out[v] = (e / (np.linalg.norm(e) or 1.0)).tolist()
    return out


def calm_moments(activity, segs, laughs, words):
    """[(voice, {'L': m, 'R': m})] moments where exactly one voice speaks, words are being said and
    nobody laughs: the only moments where mouth movement says who is talking."""
    import bisect
    laugh = [(a - 0.5, b + 0.5) for a, b, s in laughs or []]
    starts = sorted(w['s'] for w in words)
    out = []
    for t, row in activity:
        if 'L' not in row or 'R' not in row or any(a <= t <= b for a, b in laugh):
            continue
        act = {v for a, b, v in segs if a <= t < b}
        if len(act) != 1:
            continue
        i = bisect.bisect_left(starts, t - 0.6)
        if i >= len(starts) or starts[i] > t + 0.2:
            continue
        out.append((next(iter(act)), row))
    return out


class Register:
    """The video's speakers: voice print, speaking time, and one side vote per clip.

    Each clip with enough calm moments votes for the side whose mouth moves more while the person
    talks (vote strength = how many calm moments, direction = log of the movement ratio). The
    weighted median of the votes decides, so one clip where the listener silently laughs throughout
    can't outvote several calm clips."""

    def __init__(self, data=None):
        self.people = (data or {}).get('people', [])

    def to_json(self):
        return {'people': self.people}

    def nearest(self, prnt):
        """(index, similarity, similarity of the runner-up) of the closest registered voice."""
        v = np.array(prnt)
        sims = sorted(((float(np.dot(v, np.array(p['print']))), i) for i, p in enumerate(self.people)), reverse=True)
        if not sims:
            return None, -1.0, -1.0
        return sims[0][1], sims[0][0], (sims[1][0] if len(sims) > 1 else -1.0)

    def place(self, prnt, seconds=0.0):
        """Who a clip's voice is: a close match joins that person (and refines their print); a voice
        disturbed by laughter or overlap that still clearly resembles one person counts as them
        without changing their print; a long unknown voice becomes a new person; else None."""
        i, sim, runner = self.nearest(prnt)
        if i is not None and sim >= SAME_VOICE:
            return self.match(prnt, seconds)
        if i is not None and sim >= SOFT_VOICE and sim - runner >= SOFT_MARGIN:
            return i
        if seconds >= NEW_PERSON:
            return self.match(prnt, seconds)
        return None

    def match(self, prnt, seconds=0.0):
        """Index of the registered person with this voice, adding a new person if nobody matches."""
        v = np.array(prnt)
        best, sim = None, -1.0
        for i, p in enumerate(self.people):
            s = float(np.dot(v, np.array(p['print'])))
            if s > sim:
                best, sim = i, s
        if best is not None and sim >= SAME_VOICE:
            p = self.people[best]
            n = p.get('n', 1)
            merged = (np.array(p['print']) * n + v) / (n + 1)
            p['print'] = (merged / (np.linalg.norm(merged) or 1.0)).tolist()
            p['n'] = n + 1
            p['seconds'] = round(p.get('seconds', 0.0) + seconds, 1)
            return best
        self.people.append({'id': f'P{len(self.people) + 1}', 'print': v.tolist(), 'n': 1,
                            'seconds': round(seconds, 1), 'votes': {}})
        return len(self.people) - 1

    def vote(self, person, clip, rows):
        """Record one clip's calm-moment evidence for a person: rows = [{'L': m, 'R': m}, ...]."""
        if len(rows) < CLIP_MIN:
            return
        ml = float(np.median([r['L'] for r in rows]))
        mr = float(np.median([r['R'] for r in rows]))
        self.people[person].setdefault('votes', {})[str(clip)] = [len(rows), round(ml, 2), round(mr, 2)]

    def sides(self):
        """{person_index: ('L' | 'R', confidence)} for people we can place. With two main people,
        placing one places the other on the opposite side."""
        out = {}
        for i, p in enumerate(self.people):
            votes = list((p.get('votes') or {}).values())
            if not votes:
                continue
            logs = sorted((float(np.log(max(mr, 1e-3) / max(ml, 1e-3))), n) for n, ml, mr in votes)
            half, acc, wm = sum(n for _, n in logs) / 2, 0, 0.0
            for lr, n in logs:                         # weighted median of the log ratios
                acc += n
                if acc >= half:
                    wm = lr
                    break
            if abs(wm) >= float(np.log(SIDE_RATIO)):
                out[i] = ('R' if wm > 0 else 'L', round(float(np.exp(abs(wm))), 2))
        for side in ('L', 'R'):                        # two people on one side: the clearer one keeps it
            claims = sorted(((c, i) for i, (s, c) in out.items() if s == side), reverse=True)
            for c, i in claims[1:]:
                del out[i]
        talkers = sorted(range(len(self.people)), key=lambda i: -self.people[i].get('seconds', 0))[:2]
        if len(talkers) == 2:                          # elimination between the two main people
            a, b = talkers
            if a in out and b not in out:
                out[b] = ('R' if out[a][0] == 'L' else 'L', 1.0)
            elif b in out and a not in out:
                out[a] = ('R' if out[b][0] == 'L' else 'L', 1.0)
        return out
