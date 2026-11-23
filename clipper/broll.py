"""B-roll over the speaker (v2.14, only when the user asks: "add b-roll"): when the words name something (a film,
a place, a person, a thing), a short clip or picture of it covers the speaker for 2-3 seconds, then it cuts back.

    python run.py broll <project> [--clips 2,5]     find candidates for the clips' "broll" marks -> contact sheets
    (Claude looks at broll/NN-M.jpg and writes each mark's "pick": a candidate id, or "none")
    python run.py edit <project> --clips 2           the picked b-roll is cut in, with its credit

A mark in clips.json (Claude writes it while picking; source seconds like "ranges"):
    "broll": [{"at": 4815.2, "len": 2.5, "kind": "film", "what": "Animal (2023), the climax", "query": "Animal 2023"},
              {"at": 4830.0, "len": 2.0, "kind": "place", "what": "Kedarnath valley in snow", "query": "Kedarnath snow"}]
Kinds: film (its official trailer on YouTube), place / person / thing (pictures from Wikimedia Commons, free to use
with credit), stock (free stock video, Pexels / Pixabay, only with your free key in settings.json "pexels_key" /
"pixabay_key").

The owner's rules (23 November 2026): trailers are allowed, but no trailer piece longer than TRAILER_MAX (5 s);
more cover means more short pieces from different parts, never one long stretch; the channel is credited on screen
("Trailer: <channel>"); pictures carry their author and licence. Nothing found or nothing right: no guessing, the
mark gets "pick": "none" and the report says so. Copyright: a warning, never a block (a trailer can get a Content ID
claim; the review studio can take a piece out).
"""
import argparse
import html
import json
import re
import subprocess
import sys
import urllib.parse
import urllib.request
from pathlib import Path

from .common import OUTPUT, die, fmt_ts, load_json, project_dir, save_json, settings

TRAILER_MAX = 5.0          # seconds: the owner's limit for one trailer piece
LEN_MAX = 3.0              # a picture or stock clip covers at most this long
SHEET_N = 12               # candidates on one contact sheet
UA = 'ClipKaro/2.14 (local video tool; https://github.com/allthingsaman/ClipKaro)'
CACHE = OUTPUT / '.cache' / 'broll'
KINDS = ('film', 'place', 'person', 'thing', 'stock')
FIT_TOP = 0.16             # a "fit" picture sits this far down (under the credit), above the captions


def _get(url, params=None, timeout=30):
    if params:
        url += '?' + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={'User-Agent': UA})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


# ---------------------------------------------------------------- sources

def trailer(query):
    """(file, title, channel, url) of the film's official trailer on YouTube, downloaded once (720p), or None."""
    from .fetch import ytdlp_cmd
    CACHE.mkdir(parents=True, exist_ok=True)
    r = subprocess.run([*ytdlp_cmd(), '--flat-playlist', '--print', '%(id)s\t%(title)s\t%(channel)s\t%(duration)s',
                        f'ytsearch5:{query} official trailer'], capture_output=True, text=True, timeout=120,
                       encoding='utf-8', errors='replace')
    for line in r.stdout.splitlines():
        parts = line.split('\t')
        if len(parts) < 4:
            continue
        vid, title, channel, dur = parts
        try:
            dur = float(dur)
        except ValueError:
            dur = 0
        if 'trailer' not in title.lower() or not 30 <= dur <= 400:
            continue
        f = CACHE / f'trailer-{vid}.mp4'
        if not f.exists():
            d = subprocess.run([*ytdlp_cmd(), '-q', '-f', 'bv*[vcodec^=avc1][height<=720]+ba/b[height<=720]',
                                '--merge-output-format', 'mp4', '-o', str(f), f'https://www.youtube.com/watch?v={vid}'],
                               capture_output=True, text=True, timeout=600)
            if d.returncode != 0 or not f.exists():
                continue
        return {'file': str(f), 'title': title, 'channel': channel, 'url': f'https://www.youtube.com/watch?v={vid}',
                'duration': dur}
    return None


def commons(query, n=8):
    """Pictures from Wikimedia Commons: [{'file', 'author', 'license', 'url'}] (downloaded, 1280 px wide)."""
    CACHE.mkdir(parents=True, exist_ok=True)
    try:
        j = json.loads(_get('https://commons.wikimedia.org/w/api.php', {
            'action': 'query', 'format': 'json', 'generator': 'search', 'gsrsearch': f'{query} filetype:bitmap',
            'gsrnamespace': 6, 'gsrlimit': n, 'prop': 'imageinfo', 'iiprop': 'url|extmetadata|mime',
            'iiurlwidth': 1280}))
    except Exception:
        return []
    out = []
    for p in sorted((j.get('query') or {}).get('pages', {}).values(), key=lambda p: p.get('index', 0)):
        ii = (p.get('imageinfo') or [{}])[0]
        if ii.get('mime') not in ('image/jpeg', 'image/png'):
            continue
        meta = ii.get('extmetadata') or {}
        author = html.unescape(re.sub(r'<[^>]+>', '', (meta.get('Artist') or {}).get('value', ''))).strip() or 'unknown'
        lic = (meta.get('LicenseShortName') or {}).get('value', '')
        url = ii.get('thumburl') or ii.get('url')
        f = CACHE / ('commons-' + re.sub(r'[^A-Za-z0-9._-]', '_', p['title'][5:])[:80])
        try:
            if not f.exists():
                f.write_bytes(_get(url, timeout=60))
        except Exception:
            continue
        out.append({'file': str(f), 'author': author[:60], 'license': lic, 'url': ii.get('descriptionurl') or url})
    return out


def stock(query, n=8):
    """Free stock video clips (Pexels, else Pixabay) when a key is in settings.json; [] without one."""
    cfg = settings()
    CACHE.mkdir(parents=True, exist_ok=True)
    out = []
    try:
        if cfg.get('pexels_key'):
            req = urllib.request.Request('https://api.pexels.com/videos/search?' + urllib.parse.urlencode(
                {'query': query, 'per_page': n, 'orientation': 'portrait'}), headers={'Authorization': cfg['pexels_key'],
                                                                                      'User-Agent': UA})
            with urllib.request.urlopen(req, timeout=30) as r:
                j = json.loads(r.read())
            for v in j.get('videos', []):
                fs = sorted((x for x in v.get('video_files', []) if x.get('file_type') == 'video/mp4'),
                            key=lambda x: abs((x.get('height') or 0) - 1280))
                if fs:
                    out.append({'url': fs[0]['link'], 'author': (v.get('user') or {}).get('name', 'Pexels'),
                                'license': 'Pexels', 'id': f"pexels-{v['id']}"})
        elif cfg.get('pixabay_key'):
            j = json.loads(_get('https://pixabay.com/api/videos/', {'key': cfg['pixabay_key'], 'q': query, 'per_page': n}))
            for v in j.get('hits', []):
                vs = v.get('videos') or {}
                pick = vs.get('medium') or vs.get('small') or {}
                if pick.get('url'):
                    out.append({'url': pick['url'], 'author': v.get('user', 'Pixabay'), 'license': 'Pixabay',
                                'id': f"pixabay-{v['id']}"})
    except Exception:
        return []
    for c in out:
        f = CACHE / f"{c['id']}.mp4"
        try:
            if not f.exists():
                f.write_bytes(_get(c['url'], timeout=120))
            c['file'] = str(f)
        except Exception:
            c['file'] = None
    return [c for c in out if c.get('file')]


# ---------------------------------------------------------------- contact sheets

def bars(video, at=None):
    """The picture inside black letterbox bands ("w:h:x:y" for ffmpeg's crop), or None when there are none: many
    trailers are wide-screen films inside a 16:9 frame, and the bands would show as black stripes."""
    from .common import probe
    try:
        info = probe(str(video))
        W, H, dur = int(info['width']), int(info['height']), float(info.get('duration') or 0)
    except (SystemExit, Exception):
        return None
    a = at if at is not None else max(0.0, min(30.0, dur / 3))
    r = subprocess.run(['ffmpeg', '-v', 'info', '-ss', f'{a:.1f}', '-t', '20', '-i', str(video), '-an',
                        '-vf', 'fps=2,cropdetect=limit=24:round=2:reset=0', '-f', 'null', '-'],
                       capture_output=True, text=True, errors='replace')
    found = re.findall(r'crop=(\d+):(\d+):(\d+):(\d+)', r.stderr)
    if not found:
        return None
    w, h, x, y = (int(v) for v in found[-1])
    if h >= H * 0.97 and w >= W * 0.97 or h < H * 0.4 or w < W * 0.4:
        return None                            # no bands, or a dark scene misread as one
    return f'{w}:{h}:{x}:{y}'


def frame_at(video, t, out, crop=None):
    vf = (f'crop={crop},' if crop else '') + 'scale=320:-2'
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-ss', f'{t:.2f}', '-i', str(video), '-frames:v', '1',
                    '-vf', vf, str(out)], capture_output=True)
    return Path(out).exists()


def sheet(tiles, out):
    """A numbered contact sheet: tiles = [(id, picture file, label)]."""
    import cv2
    import numpy as np
    cells = []
    for cid, f, label in tiles[:SHEET_N]:
        img = cv2.imread(str(f))
        if img is None:
            continue
        img = cv2.resize(img, (320, int(img.shape[0] * 320 / img.shape[1])))[:240]
        ww = int(img.shape[0] * 9 / 16)            # what fills the upright screen: the middle; the rest dimmed
        if ww < 320:
            x0 = (320 - ww) // 2
            img[:, :x0] = img[:, :x0] // 2
            img[:, x0 + ww:] = img[:, x0 + ww:] // 2
        pad = 240 - img.shape[0]
        img = cv2.copyMakeBorder(img, pad // 2, pad - pad // 2, 0, 0, cv2.BORDER_CONSTANT)
        cv2.rectangle(img, (0, 0), (320, 26), (0, 0, 0), -1)
        cv2.putText(img, f'{cid}  {label}'[:40], (6, 19), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 255, 255), 1)
        cells.append(img)
    if not cells:
        return False
    while len(cells) % 4:
        cells.append(np.zeros_like(cells[0]))
    rows = [np.hstack(cells[i:i + 4]) for i in range(0, len(cells), 4)]
    cv2.imwrite(str(out), np.vstack(rows))
    return True


def candidates(mark, folder, key):
    """Candidates for one mark, with a contact sheet folder/key.jpg: [{'id', ...}] (ids T1.. trailer frames,
    P1.. pictures, S1.. stock clips)."""
    kind = mark.get('kind', 'thing')
    q = mark.get('query') or mark.get('what') or ''
    tiles, cands = [], []
    if kind == 'film':
        tr = trailer(q)
        if tr:
            crop = bars(tr['file'])
            step = max(2.0, tr['duration'] / SHEET_N)
            for k in range(SHEET_N):
                t = round(4 + k * step, 1)
                if t >= tr['duration'] - 2:
                    break
                img = folder / f'.{key}-T{k + 1}.jpg'
                if frame_at(tr['file'], t, img, crop):
                    cid = f'T{k + 1}'
                    cands.append({'id': cid, 'type': 'video', 'file': tr['file'], 'start': t, 'crop': crop,
                                  'credit': f"Trailer: {tr['channel']}", 'source': tr['url']})
                    tiles.append((cid, img, fmt_ts(t).split('.')[0]))
    elif kind == 'stock':
        for k, c in enumerate(stock(q), 1):
            img = folder / f'.{key}-S{k}.jpg'
            crop = bars(c['file'], at=0.0)
            if frame_at(c['file'], 1.0, img, crop):
                cands.append({'id': f'S{k}', 'type': 'video', 'file': c['file'], 'start': 0.5, 'crop': crop,
                              'credit': f"Video: {c['author']} / {c['license']}", 'source': c.get('url')})
                tiles.append((f'S{k}', img, c['author']))
    else:
        for k, c in enumerate(commons(q), 1):
            cands.append({'id': f'P{k}', 'type': 'image', 'file': c['file'],
                          'credit': f"Photo: {c['author']}" + (f", {c['license']}" if c['license'] else '') + ', Wikimedia Commons',
                          'source': c['url']})
            tiles.append((f'P{k}', c['file'], c['license'] or ''))
    ok = sheet(tiles, folder / f'{key}.jpg')
    for img in folder.glob(f'.{key}-*.jpg'):
        img.unlink()
    return cands if ok else []


# ---------------------------------------------------------------- what the edit gets

def pieces(clip, meta, found):
    """The picked b-roll of one clip on its own clock: [{'t0', 't1', 'type', 'file', 'start', 'credit'}]. A trailer
    piece is at most TRAILER_MAX seconds, a picture or stock clip LEN_MAX; a mark whose moment was cut out goes."""
    from .studio import to_clip
    out = []
    for k, m in enumerate(clip.get('broll') or []):
        pick = str(m.get('pick') or '')
        if not pick or pick == 'none' or m.get('off'):          # "off": switched off in the review studio
            continue
        c = next((x for x in _cands(found.get(str(k))) if x['id'] == pick), None)
        if not c:
            continue
        t0 = to_clip(meta['parts'], float(m['at']))
        if t0 is None:
            continue
        cap = TRAILER_MAX if c['type'] == 'video' and c['credit'].startswith('Trailer') else LEN_MAX
        ln = max(0.8, min(float(m.get('len') or 2.5), cap, meta['duration'] - t0))
        out.append({'t0': round(t0, 3), 't1': round(t0 + ln, 3), 'type': c['type'], 'file': c['file'],
                    'start': c.get('start', 0.0), 'credit': c['credit'], 'crop': c.get('crop'),
                    'fit': bool(m.get('fit'))})
    out.sort(key=lambda x: x['t0'])
    keep = []
    for p in out:                              # never two at once
        if not keep or p['t0'] >= keep[-1]['t1']:
            keep.append(p)
    return keep


def frames(piece, fps, size):
    """The piece's frames, W x H: a generator of BGR frames for its length. It fills the screen (the middle of a wide
    picture), or with "fit" the whole picture shows across the middle over a blurred, darker copy of itself (a title
    card, a wide shot). Letterbox bands are cut off first. A picture zooms in slowly."""
    import numpy as np
    W, H = size
    n = int(round((piece['t1'] - piece['t0']) * fps))
    pre = f"crop={piece['crop']}," if piece.get('crop') else ''
    if piece.get('fit'):
        look = (f"split[a][b];[a]scale={W // 4}:{H // 4}:force_original_aspect_ratio=increase,crop={W // 4}:{H // 4},"
                f"boxblur=12:2,eq=brightness=-0.12,scale={W}:{H}[bg];[b]scale={W}:{H}:force_original_aspect_ratio="
                f"decrease[fg];[bg][fg]overlay=(W-w)/2:min((H-h)/2\\,{int(H * FIT_TOP)})")
    else:
        look = f'scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H}'
    if piece['type'] == 'image' and not piece.get('fit'):
        vf = (f"{pre}scale={W * 2}:{H * 2}:force_original_aspect_ratio=increase,crop={W * 2}:{H * 2},"
              f"zoompan=z='min(1+0.0012*on,1.12)':d={n}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s={W}x{H}:fps={fps}")
        cmd = ['ffmpeg', '-v', 'error', '-loop', '1', '-i', piece['file'], '-vf', vf, '-frames:v', str(n),
               '-f', 'rawvideo', '-pix_fmt', 'bgr24', '-']
    elif piece['type'] == 'image':
        cmd = ['ffmpeg', '-v', 'error', '-loop', '1', '-i', piece['file'], '-vf', f'{pre}fps={fps},{look}',
               '-frames:v', str(n), '-f', 'rawvideo', '-pix_fmt', 'bgr24', '-']
    else:
        cmd = ['ffmpeg', '-v', 'error', '-ss', f"{piece['start']:.2f}", '-i', piece['file'], '-an',
               '-vf', f'fps={fps},{pre}{look}', '-frames:v', str(n), '-f', 'rawvideo', '-pix_fmt', 'bgr24', '-']
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE)
    last = None
    try:
        for _ in range(n):
            buf = p.stdout.read(W * H * 3)
            if len(buf) < W * H * 3:
                break
            last = np.frombuffer(buf, np.uint8).reshape(H, W, 3)
            yield last
    finally:
        p.stdout.close()
        p.wait()


def _cands(entry):
    """The candidates of one mark in candidates.json ({'ask': what was searched, 'cands': [...]})."""
    return (entry or {}).get('cands', []) if isinstance(entry, dict) else (entry or [])


def _ask(m):
    return f"{m.get('kind')}|{m.get('query') or m.get('what') or ''}"


def credits(pdir, clip):
    """[(credit, source page)] of the b-roll picked for one clip, for the posting texts (a picture's licence asks for
    its author, licence and source wherever it is shown)."""
    found = load_found(pdir, clip.get('id'))
    out = []
    for k, m in enumerate(clip.get('broll') or []):
        pick = str(m.get('pick') or '')
        c = next((x for x in _cands(found.get(str(k))) if x['id'] == pick), None) \
            if pick != 'none' and not m.get('off') else None
        if c and (c['credit'], c.get('source')) not in out:
            out.append((c['credit'], c.get('source')))
    return out


def load_found(pdir, cid):
    return (load_json(pdir / 'broll' / 'candidates.json', {}) or {}).get(str(cid), {})


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('project')
    ap.add_argument('--clips', default=None)
    ap.add_argument('--fresh', action='store_true', help='search again even for marks searched before')
    a = ap.parse_args()
    pdir = project_dir(a.project)
    want = {int(x) for x in a.clips.split(',')} if a.clips else None
    picks = (load_json(pdir / 'clips.json', {}) or {}).get('clips', [])
    folder = pdir / 'broll'
    folder.mkdir(exist_ok=True)
    allc = load_json(folder / 'candidates.json', {}) or {}
    n = 0
    for k, c in enumerate(picks, 1):
        cid = int(c.get('id', k))
        if (want and cid not in want) or not c.get('broll'):
            continue
        found = allc.setdefault(str(cid), {})
        for m_i, m in enumerate(c['broll']):
            if m.get('kind') not in KINDS:
                print(f"   clip {cid} mark {m_i + 1}: kind \"{m.get('kind')}\" is not one of {', '.join(KINDS)}")
                continue
            key = f'{cid:02d}-{m_i + 1}'
            old = found.get(str(m_i))
            if a.fresh or not isinstance(old, dict) or old.get('ask') != _ask(m):
                print(f"-> clip {cid}, mark {m_i + 1}: {m.get('kind')} \"{m.get('what')}\" ...", flush=True)
                found[str(m_i)] = {'ask': _ask(m), 'cands': candidates(m, folder, key)}
            got = _cands(found[str(m_i)])
            n += 1
            if got:
                print(f"   {len(got)} candidate(s): {folder / (key + '.jpg')}  (write \"pick\": one of "
                      f"{', '.join(x['id'] for x in got)}, or \"none\")")
            else:
                print(f'   nothing found: no guessing (the mark stays without b-roll; say so in the report)')
    save_json(folder / 'candidates.json', allc)
    if n:
        print('   On the sheets, the bright middle of a tile is what fills the upright screen. When what matters lies '
              'outside it (a title card, a wide shot), also write "fit": true: the whole picture then shows across '
              'the middle over a blurred copy.')
        print('   Trailer pieces are at most 5 s and are credited on screen; a trailer can get a copyright claim '
              '(a warning, never a block).')
    else:
        print('no "broll" marks in clips.json (add them only when the user asked for b-roll)')


if __name__ == '__main__':
    main()
