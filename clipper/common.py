"""Shared helpers: paths, json, settings, text helpers (incl. Hindi), ffmpeg/ffprobe wrappers."""
import json
import re
import shutil
import subprocess
import sys
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUTPUT = ROOT / 'output'
ASSETS = ROOT / 'assets'
FPS = 30          # default / maximum output frame rate
W, H = 1080, 1920
JUMP_FLASH = 20.0  # a join that skips more than this many seconds of the video is shown (flash, whoosh)

# settings.json at the repo root holds the user's defaults (all optional)
DEFAULT_SETTINGS = {
    'language': 'auto',            # auto | hinglish | en | hi | any whisper language code
    'model': 'auto',               # auto | large-v3-turbo | large-v3 | medium | small | ...
    'device': 'auto',              # auto (NVIDIA GPU if usable, else CPU) | cuda | cpu
    'hinglish_captions': 'roman',  # roman ("aaj hum baat karenge") | devanagari ("आज हम बात करेंगे")
    'layout': 'auto',              # auto (facecam layout when a webcam overlay is found) | facecam | crop
    'facecam': None,               # optional fixed cam box: {"x","y","w","h" (fractions), "shape": "circle"|"rect"}
    'jump_label': False,           # true: a small "27 MIN LATER" label where a joined clip jumps in time
}

SENT_END = '.?!।॥'                 # sentence ends, incl. the Hindi danda
_CLOSERS = '"\'”’)]»'


def die(msg):
    print(f'ERROR: {msg}', file=sys.stderr)
    sys.exit(1)


def settings():
    s = dict(DEFAULT_SETTINGS)
    try:
        s.update(load_json(ROOT / 'settings.json', {}) or {})
    except (ValueError, OSError) as e:
        print(f'   ! settings.json ignored ({e})')
    return s


def is_sentence_end(word):
    """True when a transcript word ends a sentence: '.', '?', '!' or the Hindi danda '।'."""
    return word.strip().rstrip(_CLOSERS)[-1:] in SENT_END


def has_devanagari(text):
    return any('ऀ' <= c <= 'ॿ' for c in text or '')


def norm_token(text):
    """Comparable form of a word: lower case, letters + Hindi vowel signs + digits only, and one
    spelling for nukta letters (ज़ = ज). 'करेंगे।' -> 'करेंगे', 'Business,' -> 'business'."""
    t = unicodedata.normalize('NFC', text or '').lower().replace('़', '')
    return ''.join(c for c in t if unicodedata.category(c)[0] in 'LMN' or c in "$%'")


def slugify(text, maxlen=50):
    text = unicodedata.normalize('NFC', text)
    # keep letters, digits and combining marks (Hindi vowel signs), drop punctuation
    text = ''.join(c for c in text if unicodedata.category(c)[0] in 'LMN' or c in ' \t_-').strip().lower()
    text = re.sub(r'[\s_-]+', '-', text)
    return text[:maxlen].strip('-') or 'video'


def load_json(path, default=None):
    path = Path(path)
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding='utf-8'))


def save_json(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding='utf-8')


def project_dir(name_or_path):
    """Accepts a project folder name (inside output/) or a path."""
    p = Path(name_or_path)
    if p.is_dir() and (p / 'project.json').exists():
        return p.resolve()
    q = OUTPUT / name_or_path
    if (q / 'project.json').exists():
        return q
    die(f'project not found: {name_or_path}  (look inside {OUTPUT})')


def need(tool):
    if not shutil.which(tool):
        die(f'{tool} is not installed or not on PATH. Run: python install.py')


def run(cmd, quiet=True, check=True):
    """Run a command; on failure print the tail of stderr."""
    r = subprocess.run([str(c) for c in cmd], capture_output=True, text=True,
                       encoding='utf-8', errors='replace')
    if check and r.returncode != 0:
        tail = '\n'.join((r.stderr or r.stdout).strip().splitlines()[-25:])
        die(f'command failed: {" ".join(str(c) for c in cmd[:6])} ...\n{tail}')
    if not quiet and r.stdout:
        print(r.stdout)
    return r


def ffmpeg(*args):
    need('ffmpeg')
    return run(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y', *args])


def probe(path):
    need('ffprobe')
    r = run(['ffprobe', '-v', 'error', '-print_format', 'json', '-show_format', '-show_streams', path])
    info = json.loads(r.stdout)
    v = next((s for s in info['streams'] if s['codec_type'] == 'video'), None)
    out = {'duration': float(info['format'].get('duration', 0))}
    if v:
        num, den = (v.get('avg_frame_rate') or '30/1').split('/')
        rot = 0
        for sd in v.get('side_data_list', []) or []:
            rot = int(sd.get('rotation', 0) or 0)
        w, h = int(v['width']), int(v['height'])
        if abs(rot) in (90, 270):
            w, h = h, w
        out.update(width=w, height=h, fps=float(num) / float(den or 1) if float(den or 1) else 30.0,
                   start_time=float(v.get('start_time') or 0.0))
    return out


def out_fps(src_fps):
    """Keep the source frame rate (24/25/30) so motion stays smooth; bring 50/60 fps down to 30."""
    for f in (24, 25, 30):
        if abs(src_fps - f) < 0.6 or abs(src_fps - f * 1000 / 1001) < 0.05:
            return f
    return FPS


def fmt_ts(t):
    m, s = divmod(max(0.0, t), 60)
    h, m = divmod(int(m), 60)
    return f'{h}:{m:02d}:{s:04.1f}' if h else f'{m}:{s:04.1f}'
