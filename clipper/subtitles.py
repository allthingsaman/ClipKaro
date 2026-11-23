"""The game's own subtitles on screen (v2.8): which lines a game character says, also when the streamer speaks English.

    python run.py subtitles <project>             the lines of the picked clips (cut runs it by itself)
    python run.py subtitles <project> --fresh     read them again

Why: game characters' lines get no captions (the game shows its own subtitles: two subtitles on screen look
broken, the owner's rule). With a Hindi / Hinglish streamer the language and the voice tell the game apart
(voices.game_words); with an English streamer both speak English, so that rule is off. The strongest clue left
is the game's own subtitle: a transcript line whose words are on screen, in the subtitle area, while it is said
is the game talking.

How: for the lines of the picked clips (at least MIN_WORDS words) one frame at PROBES of the line is read with
a text reader, PP-OCRv5 (the English reader, en_PP-OCRv5_rec_mobile, and the English text finder,
en_PP-OCRv3_det_mobile; rapidocr on onnxruntime, Apache 2.0, about 10 MB, downloaded the first time), on the
lower middle of the picture (SUB_TOP to SUB_BOTTOM, the middle SUB_WIDTH, the webcam blacked out). A line is
a game line when at least MATCH of its words, and at least MIN_HITS, are in the text read (spelling slips
allowed). First the lines least like the streamer's voice are tried (the likely game lines): when none of the
first PRECHECK of them matches, the video shows no subtitles and the rest is skipped. About a second per frame
on the CPU (frames read at READ_HEIGHT); only English gameplay and streams (Hinglish keeps its own rule, at no cost).
Results are kept in transcript/subtitles.json; voices.game_words reads them (cut, the caption check and the
word check all go through it). "game_subtitles": false skips the reading; "game_voice_captions": true shows
game lines' captions again.
"""
import argparse
import difflib
import re
import subprocess

from .common import die, load_json, project_dir, save_json, settings

SUBS_V = 1
SUB_TOP, SUB_BOTTOM = 0.62, 0.97     # the part of the picture height where games put subtitles
SUB_WIDTH = 0.84                     # the middle part of the width (subtitles are centred)
PROBES = (0.35, 0.75)                # where in a line its frames are read
MIN_WORDS = 3                        # shorter lines can't be judged safely: they keep their captions
MATCH = 0.6                          # this share of the line's words must be on screen ...
MIN_HITS = 3                         # ... and at least this many of them
CLOSE = 0.8                          # a word read on screen this like the heard word is the same word
MIN_SCORE = 0.6                      # text the reader is less sure of is ignored
PRECHECK = 10                        # lines least like the streamer tried first; none matching = no subtitles
READ_HEIGHT = 650                    # frames are read as if this many pixels high: 40 % faster than 1080, the
                                     # same words (subtitles 36 px high at 1080p, tested 23 November 2026)
_ENGINE = {}


def wanted(project):
    """English (not Hindi / Hinglish) gameplay and live streams, unless switched off."""
    from .fetch import is_hindi
    from .kind import is_irregular
    if not settings().get('game_subtitles', True) or settings().get('game_voice_captions', False):
        return False
    return is_irregular(project) and not is_hindi((project or {}).get('language') or '')


def engine():
    """The text reader with the English models only (None when rapidocr isn't installed)."""
    if 'ocr' in _ENGINE:
        return _ENGINE['ocr']
    try:
        from rapidocr import LangDet, LangRec, ModelType, OCRVersion, RapidOCR
        from .speakers import CACHE
        root = CACHE / 'ocr'
        root.mkdir(parents=True, exist_ok=True)
        _ENGINE['ocr'] = RapidOCR(params={
            'Global.use_cls': False, 'Global.model_root_dir': str(root), 'Global.log_level': 'warning',
            'EngineConfig.onnxruntime.intra_op_num_threads': 2,
            'Det.lang_type': LangDet.EN, 'Det.ocr_version': OCRVersion.PPOCRV4, 'Det.model_type': ModelType.MOBILE,
            'Rec.lang_type': LangRec.EN, 'Rec.ocr_version': OCRVersion.PPOCRV5, 'Rec.model_type': ModelType.MOBILE})
    except Exception as e:                       # not installed, or the models can't be downloaded
        print(f'   (game subtitles not read: the text reader is not available: {type(e).__name__})')
        _ENGINE['ocr'] = None
    return _ENGINE['ocr']


def band(img, cam=None):
    """The lower middle of a frame, where subtitles are, with the webcam box blacked out."""
    h, w = img.shape[:2]
    y0, y1 = int(h * SUB_TOP), int(h * SUB_BOTTOM)
    x0 = int(w * (1 - SUB_WIDTH) / 2)
    out = img[y0:y1, x0:w - x0].copy()
    if cam:
        ax, ay = max(0, cam['x'] - x0), max(0, cam['y'] - y0)
        bx, by = min(out.shape[1], cam['x'] + cam['w'] - x0), min(out.shape[0], cam['y'] + cam['h'] - y0)
        if bx > ax and by > ay:
            out[ay:by, ax:bx] = 0
    return out


def smaller(img, height):
    """The band shrunk to what it would be in a frame READ_HEIGHT pixels high (never enlarged)."""
    import cv2
    k = min(1.0, READ_HEIGHT / height)
    return img if k >= 1.0 else cv2.resize(img, None, fx=k, fy=k, interpolation=cv2.INTER_AREA)


def prepare(img, cam=None):
    """A frame -> the part the text reader reads."""
    return smaller(band(img, cam), img.shape[0])


def frame_at(video, t):
    """One frame of the video at t seconds (BGR), or None."""
    import cv2
    import numpy as np
    r = subprocess.run(['ffmpeg', '-v', 'error', '-ss', f'{max(0.0, t):.3f}', '-i', str(video), '-frames:v', '1',
                        '-f', 'image2pipe', '-vcodec', 'png', '-'], capture_output=True)
    if r.returncode != 0 or not r.stdout:
        return None
    return cv2.imdecode(np.frombuffer(r.stdout, np.uint8), cv2.IMREAD_COLOR)


def read_text(img, ocr):
    res = ocr(img)
    if not res or not getattr(res, 'txts', None):
        return ''
    return ' '.join(t for t, s in zip(res.txts, res.scores) if s >= MIN_SCORE)


def tokens(text):
    return [t.replace("'", '') for t in re.findall(r"[a-z0-9']+", (text or '').lower()) if t.replace("'", '')]


def on_screen(heard, read):
    """(share of the heard words found in the text read, how many)."""
    pool = set(tokens(read))
    if not heard or not pool:
        return 0.0, 0
    hits = sum(1 for w in heard if w in pool
               or max(difflib.SequenceMatcher(None, w, p).ratio() for p in pool) >= CLOSE)
    return hits / len(heard), hits


def is_game(share, hits):
    return share >= MATCH and hits >= MIN_HITS


def line_key(ln):
    return f"{ln['i0']}-{ln['i1']}"


def heard_words(words, ln):
    from .common import norm_token
    return [t for w in words[ln['i0']:ln['i1'] + 1] if not w.get('unsure') for t in tokens(norm_token(w['w']))]


def load(pdir):
    s = load_json(pdir / 'transcript' / 'subtitles.json')
    return s if s and s.get('v') == SUBS_V else None


def game_lines(pdir, lines):
    """Indexes of the sentence lines the game's subtitles show (from subtitles.json; empty without it)."""
    s = load(pdir)
    if not s or s.get('none'):
        return set()
    found = {k for k, (share, hits, _) in (s.get('lines') or {}).items() if is_game(share, hits)}
    return {i for i, ln in enumerate(lines) if 'i0' in ln and line_key(ln) in found}


def scan(pdir, project, clips, words, lines, video, cam=None, fresh=False, quiet=False):
    """Read the subtitle area for the picked clips' lines; returns the subtitles.json dict (or None)."""
    if not wanted(project) or not video or not lines:
        return None
    s = (None if fresh else load(pdir)) or {'v': SUBS_V, 'lines': {}, 'tried': []}
    if s.get('none'):
        return s
    spans = [(a, b) for c in clips for a, b in c.get('ranges', [])]
    todo = [i for i, ln in enumerate(lines) if 'i0' in ln and line_key(ln) not in s['lines']
            and any(ln['s'] < b and a < ln['e'] for a, b in spans) and len(heard_words(words, ln)) >= MIN_WORDS]
    if not todo:
        return s
    ocr = engine()
    if ocr is None:
        return None
    from . import voices
    v = voices.load(pdir)
    rows = voices.rows_for(v, lines) if v else [None] * len(lines)
    like = lambda i: rows[i][3] if rows[i] and rows[i][3] is not None else 1.0      # noqa: E731

    def check(i):
        ln = lines[i]
        read = []
        for p in PROBES:
            img = frame_at(video, ln['s'] + p * (ln['e'] - ln['s']))
            if img is not None:
                read.append(read_text(prepare(img, cam), ocr))
        text = ' '.join(t for t in read if t)
        share, hits = on_screen(heard_words(words, ln), text)
        s['lines'][line_key(ln)] = [round(share, 2), hits, text[:160]]
        return is_game(share, hits)

    found_any = any(is_game(x[0], x[1]) for x in s['lines'].values())
    others = sorted((i for i, ln in enumerate(lines) if 'i0' in ln and like(i) < voices.GAME_MAX_LIKE
                     and line_key(ln) not in s['lines'] and len(heard_words(words, ln)) >= MIN_WORDS),
                    key=lambda i: (i not in todo, like(i)))
    if not found_any and others and len(s.get('tried', [])) < PRECHECK:
        # does the video show subtitles at all? the lines least like the streamer's voice first, from the
        # whole video when the picked clips have few of them (without voice prints: just the picked lines)
        for i in others[:PRECHECK - len(s.get('tried', []))]:
            s.setdefault('tried', []).append(line_key(lines[i]))
            if check(i):
                break
        else:
            if len(s.get('tried', [])) >= PRECHECK:
                s['none'] = True
                save_json(pdir / 'transcript' / 'subtitles.json', s)
                if not quiet:
                    print('-> game subtitles: none on screen (lines in other voices checked): every line keeps '
                          'its captions')
                return s
    n0 = sum(1 for x in s['lines'].values() if is_game(x[0], x[1]))
    for i in todo:
        if line_key(lines[i]) not in s['lines']:
            check(i)
    save_json(pdir / 'transcript' / 'subtitles.json', s)
    n = sum(1 for x in s['lines'].values() if is_game(x[0], x[1]))
    if not quiet:
        print(f'-> game subtitles: {n} line(s) shown by the game on screen ({n - n0} new): no captions for them')
    return s


def scan_if_ready(pdir, project, clips, words, lines):
    """scan() when the video is already here (the caption check and the word check never download it)."""
    if not wanted(project):
        return None
    from .kind import _video_file
    video = _video_file(pdir, project)
    return scan(pdir, project, clips, words, lines, video, project.get('facecam')) if video else None


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('project')
    ap.add_argument('--fresh', action='store_true', help='read every line again')
    a = ap.parse_args()
    pdir = project_dir(a.project)
    project = load_json(pdir / 'project.json', {}) or {}
    if not wanted(project):
        die('only for English gameplay and live streams (Hinglish uses the voice and language rule); '
            'or settings.json "game_subtitles" / "game_voice_captions" switch it off')
    from .cut import ensure_video
    video = ensure_video(pdir, project)
    picks = (load_json(pdir / 'clips.json', {}) or {}).get('clips', [])
    words = load_json(pdir / 'transcript' / 'words.json') or []
    lines = load_json(pdir / 'transcript' / 'sentences.json') or []
    scan(pdir, project, picks, words, lines, video, project.get('facecam'), fresh=a.fresh)


if __name__ == '__main__':
    main()
