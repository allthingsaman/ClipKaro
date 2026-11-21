"""Frame sheets: ClipKaro watches gameplay, not just the words (v2.7; gameplay and live streams only).

In gameplay the best moment is often seen first and talked about after: the bike catches fire, the chair
breaks on camera, the bicycle flips. On a 4-hour GTA stream ClipKaro's clips all started when the talking
started, after the moment, and its action detector missed all of them; Claude found 11 by looking at
sheets of frames by hand. The owner's design (2026-11-20):

1. **Overview** (`fetch` makes it, about a minute for 4 hours): one frame every 10 seconds of the video,
   21 frames per sheet (7 across, 3 down), the time on each. A red border where the sound jumps (a shout,
   a crash, a big laugh: every event on that stream had one), and the reaction word where someone says
   "bhaag", "yah kya tha" ... `parts` gives each reading helper the sheets of its stretch, and the helper
   names the spots worth a closer look ("look_closer").
2. **Close-ups** (`run.py zoom`): for each of those spots, 21 frames, one per second, mostly before the
   spot (the event comes before the reaction). One `clipkaro-eventfinder` helper per batch decides which
   are clips and when exactly the event starts; `run.py zoom` again collects them (frames/events.json).
3. **Events into the clips** (`run.py events`, after the final clips.json): a picked clip that starts on
   the reaction now starts 1.5 s before its event; an event no clip has becomes a new clip; and a small
   exact-frame sheet (4 frames a second) lets Claude put the clip's start and its sound on the right frame.

Cost: about 1,550 Claude tokens per sheet; for 4 hours about 70 overview sheets and some 30-60 close-ups.
Normal videos (podcasts, talks) never get any of it. settings.json "watch_gameplay": false turns it off.
"""
import json
import re
import subprocess

import numpy as np

from .common import fmt_ts, imread, imwrite, load_json, norm_token, save_json, settings

EVERY = 10.0               # seconds between overview frames
PER_SHEET, COLS = 21, 7    # 21 frames, 7 across and 3 down (the owner's choice)
TILE_W, TILE_H = 320, 180
LOUD_DB = 8.0              # a red border needs at least this loudness jump ...
LOUD_SHARE = 0.15          # ... and to be among the loudest 15 % of the video's frames (at 6 dB, half the frames of a
                           # loud stream with friends were red, and the readers stopped trusting the mark)
LOUD_WINDOW = 60           # ... against the median loudness of this many seconds on each side
CLOSE_BEFORE, CLOSE_AFTER = 15, 6    # a close-up: 21 frames, one a second, mostly before the spot
MERGE_S = 12.0             # spots this close together share a close-up
LEAD_IN = 1.5              # an event clip starts this long before its event
MAX_CLIP_S = 90.0          # an event never makes a clip longer than this (the hard limit for a short)
PER_BATCH = 24             # close-up spots per eventfinder helper (fewer helpers: each carries its own instructions)
REACTIONS = re.compile(
    r"^(yah kya|ye kya|kya ho gaya|kya hua|kya tha|kya kar|bhaag|bhago|mar gaya|mar gae|mar gayi|aag|toot|tooti|"
    r"phat|gir gaya|gira|bach|bachao|oh my god|what the|vaah|wow|shit|are bhai bhai)", re.I)


def wanted(project, cfg=None):
    """(True, why) for gameplay and live streams, unless settings.json "watch_gameplay" is false."""
    import os
    from .kind import GAMEPLAY_WORDS, is_irregular, stream_hint
    cfg = settings() if cfg is None else cfg
    if cfg.get('watch_gameplay', True) is False:
        return False, 'off in settings.json ("watch_gameplay": false)'
    if os.environ.get('CLIPKARO_LIVE'):
        return False, 'not while live clipping runs (clips go out fast; the graphics card belongs to OBS)'
    # a game or console named in the title alone is not enough ("PS5 Pro review", "gaming addiction podcast"): the
    # picture check, the link, YouTube's category or a title that says "gameplay" / "live stream" must (v2.7.1 review)
    why = [w for w in stream_hint(project) if 'title' not in w]
    if not why and GAMEPLAY_WORDS.search(str((project or {}).get('title') or '')):
        why = ['the title says gameplay or a stream']
    if is_irregular(project) or why:
        return True, ', '.join(why) or 'gameplay or a live stream'
    return False, 'a normal video (no gameplay or stream)'


def _video(pdir, project):
    from .cut import ensure_video
    return ensure_video(pdir, project)


INSET = {'overview': (116, 65), 'game': (100, 56), 'webcam': (154, 87)}   # the webcam inset (bottom-left) per use:
# small where the game matters (at 154 px wide it hid a burning rider on the GTA stream), large for a webcam spot


def cam_box(project):
    """The webcam's box in pixels (project.json "facecam", or settings.json "facecam" in fractions), or None."""
    fc = (project or {}).get('facecam')
    if isinstance(fc, dict):
        return {k: int(fc[k]) // 2 * 2 for k in ('x', 'y', 'w', 'h')}
    box = settings().get('facecam')
    w, h = (project or {}).get('width'), (project or {}).get('height')
    if isinstance(box, dict) and w and h:
        return {'x': int(box['x'] * w) // 2 * 2, 'y': int(box['y'] * h) // 2 * 2,
                'w': int(box['w'] * w) // 2 * 2, 'h': int(box['h'] * h) // 2 * 2}
    return None


def _tile_filter(crop=None, inset=None, size=INSET['overview']):
    """One frame as a 320x180 tile: the whole frame (or a crop of it), and with `inset` (a webcam box) that
    webcam twice its size in the bottom-left corner, so a fall in the room shows on the sheet (on the GTA
    stream the chair broke inside a webcam 77 pixels wide)."""
    c = f"crop={crop['w']}:{crop['h']}:{crop['x']}:{crop['y']}," if crop else ''
    fit = (f'scale={TILE_W}:{TILE_H}:force_original_aspect_ratio=decrease,'
           f'pad={TILE_W}:{TILE_H}:(ow-iw)/2:(oh-ih)/2')
    if not inset or crop:
        return c + fit
    iw, ih = size
    return (f"split=2[g][c];[c]crop={inset['w']}:{inset['h']}:{inset['x']}:{inset['y']},"
            f"scale={iw}:{ih},pad={iw + 4}:{ih + 4}:2:2:white[cam];"
            f"[g]{fit}[bg];[bg][cam]overlay=0:{TILE_H - ih - 4}")


# ---------------------------------------------------------------- what marks a frame

def loudness(pdir):
    """Per second: how many dB louder than the minute around it (frames/loud.npy, cached)."""
    out = pdir / 'frames' / 'loud.npy'
    if out.exists():
        return np.load(out)
    import wave
    from .hearing import _wav
    db = []
    with wave.open(str(_wav(pdir))) as w:
        sr = w.getframerate()
        while True:
            x = w.readframes(sr * 60)
            if not x:
                break
            a = np.frombuffer(x, dtype=np.int16).astype(np.float32) / 32768.0
            k = len(a) // sr
            if k:
                db += list(20 * np.log10(np.sqrt((a[:k * sr].reshape(k, sr) ** 2).mean(1) + 1e-12)))
    db = np.array(db, dtype=np.float32)
    med = np.array([np.median(db[max(0, i - LOUD_WINDOW):i + LOUD_WINDOW]) for i in range(len(db))], dtype=np.float32)
    jump = db - med
    out.parent.mkdir(exist_ok=True)
    np.save(out, jump)
    return jump


def reactions(pdir):
    """{second: reaction words} where a transcript line starts with a reaction ("bhaag", "yah kya tha" ...)."""
    words = load_json(pdir / 'transcript' / 'words.json') or []
    lines = load_json(pdir / 'transcript' / 'sentences.json') or []
    out = {}
    for ln in lines:
        if 'i0' not in ln:
            continue
        ws = [w for w in words[ln['i0']:ln['i0'] + 4] if not w.get('unsure')]
        text = ' '.join(norm_token(w['w']) for w in ws)
        m = REACTIONS.match(text)
        if m and ws:
            out[int(ws[0]['s'])] = m.group(1)
    return out


def loud_level(jump):
    """The loudness jump a frame needs for a red border in this video: LOUD_DB, or more on a loud video, so
    only about the loudest LOUD_SHARE of its 10-second stretches get one."""
    slots = [float(jump[t:t + int(EVERY)].max()) for t in range(0, len(jump), int(EVERY)) if len(jump[t:t + int(EVERY)])]
    return max(LOUD_DB, float(np.percentile(slots, 100 * (1 - LOUD_SHARE)))) if slots else LOUD_DB


def _marks(t0, t1, jump, react, laughs, level=LOUD_DB):
    """What happened in [t0, t1): (loud, reaction word or '', laugh)."""
    a, b = max(0, int(t0)), max(int(t0) + 1, int(t1))
    loud = bool(len(jump[a:b]) and float(jump[a:b].max()) >= level)
    word = next((react[s] for s in range(a, b) if s in react), '')
    laugh = any(x < t1 and t0 < y for x, y, *_ in laughs)
    return loud, word, laugh


# ---------------------------------------------------------------- sheets

def compose(tiles, out, cols=COLS):
    """tiles: [(image path, label, loud, word, laugh)] -> one sheet (cols across), the label on each frame; None
    when there are no frames (a spot past the video's end)."""
    import cv2
    if not tiles:
        return None
    rows = -(-len(tiles) // cols)
    sheet = np.zeros((rows * TILE_H, cols * TILE_W, 3), np.uint8)
    for k, (path, label, loud, word, laugh) in enumerate(tiles):
        img = imread(path)                             # safe with Hindi letters in the path on Windows
        if img is None:
            continue
        img = cv2.resize(img, (TILE_W, TILE_H))
        if loud:                                       # the sound jumps here: a red border
            cv2.rectangle(img, (0, 0), (TILE_W - 1, TILE_H - 1), (0, 0, 255), 6)
        cv2.rectangle(img, (0, 0), (8 + 11 * len(label), 24), (0, 0, 0), -1)
        cv2.putText(img, label, (4, 18), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 1, cv2.LINE_AA)
        tag = ' '.join(x for x in (word.upper(), 'LAUGH' if laugh else '') if x)
        if tag:
            cv2.rectangle(img, (0, TILE_H - 26), (8 + 11 * len(tag), TILE_H), (0, 0, 0), -1)
            cv2.putText(img, tag, (4, TILE_H - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 255, 255), 1, cv2.LINE_AA)
        r, c = divmod(k, cols)
        sheet[r * TILE_H:(r + 1) * TILE_H, c * TILE_W:(c + 1) * TILE_W] = img
    out.parent.mkdir(parents=True, exist_ok=True)
    return out if imwrite(out, sheet, [cv2.IMWRITE_JPEG_QUALITY, 85]) else None


def overview(pdir, project=None, quiet=False):
    """One frame every EVERY seconds of the whole video (frames/overview/), from its keyframes: fast."""
    project = project or load_json(pdir / 'project.json', {}) or {}
    folder = pdir / 'frames' / 'overview'
    video = _video(pdir, project)
    meta = load_json(folder / 'meta.json') or {}
    inset = cam_box(project)
    if meta.get('video') == video.name and meta.get('every') == EVERY and meta.get('count') \
            and meta.get('inset') == inset and meta.get('inset_size') == list(INSET['overview']):
        return folder
    folder.mkdir(parents=True, exist_ok=True)
    for old in folder.glob('f*.jpg'):
        old.unlink()
    if not quiet:
        print('-> frame overview: one frame every 10 s of the video (about a minute per 4 hours) ...', flush=True)
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-skip_frame', 'nokey', '-i', str(video), '-vf',
                    f'fps=1/{EVERY:g},{_tile_filter(inset=inset)}', '-fps_mode', 'vfr', '-q:v', '4',
                    str(folder / 'f%05d.jpg')], check=True)
    save_json(folder / 'meta.json', {'video': video.name, 'every': EVERY, 'inset': inset,
                                     'inset_size': list(INSET['overview']),
                                     'count': len(list(folder.glob('f*.jpg')))})
    loudness(pdir)
    return folder


def part_sheets(pdir, k, stretch):
    """The overview sheets of part k's own stretch: [(path relative to the project, first s, last s)]."""
    folder = pdir / 'frames' / 'overview'
    if not (folder / 'meta.json').exists():
        return []
    a, b = stretch
    frames = sorted(folder.glob('f*.jpg'))
    times = [(int(p.stem[1:]) - 1) * EVERY for p in frames]
    own = [(t, p) for t, p in zip(times, frames) if a <= t < b]
    if not own:
        return []
    jump, react = loudness(pdir), reactions(pdir)
    level = loud_level(jump)
    laughs = (load_json(pdir / 'transcript' / 'cues.json', {}) or {}).get('laughter', [])
    out = []
    for n in range(0, len(own), PER_SHEET):
        chunk = own[n:n + PER_SHEET]
        tiles = [(p, fmt_ts(t).split('.')[0], *_marks(t - EVERY / 2, t + EVERY / 2, jump, react, laughs, level))
                 for t, p in chunk]
        f = pdir / 'frames' / f'part-{k:02d}-{n // PER_SHEET + 1}.jpg'
        if compose(tiles, f):
            out.append((str(f.relative_to(pdir)), chunk[0][0], chunk[-1][0]))
    return out


SHEET_NOTE = ('# FRAME SHEETS (gameplay): one frame every 10 s of your stretch, the time on each: {files}. A RED BORDER: '
              'the sound jumps there (a shout, a crash, a big laugh); a YELLOW WORD: someone reacts ("BHAAG", '
              '"YAH KYA"). In a video with a webcam, the webcam shows enlarged in each frame\'s bottom-left corner. '
              'Look at every sheet. In gameplay the best moment is often SEEN first and talked about '
              'after: a crash, fire, a fall, a fight, a funny glitch, someone falling in the webcam. For each spot '
              'worth a closer look, add to your JSON "look_closer": [{{"at": <seconds>, "where": "game" or "webcam", '
              '"why": "<what you see or hear>"}}]: only where something visible happens (a red border or a reaction '
              'word alone is not enough: most loud moments are friends laughing), at most about one per 4 minutes, '
              'none is fine.')


# ---------------------------------------------------------------- close-ups of the spots the readers named

def requests(pdir):
    """The look_closer spots of every part (and frames/look_closer.json, Claude's own in quick mode), merged."""
    spots = []
    for f in sorted((pdir / 'parts').glob('part-*.json')) + [pdir / 'frames' / 'look_closer.json']:
        doc = load_json(f) or {}
        for x in (doc.get('look_closer') if isinstance(doc, dict) else doc) or []:
            try:
                spots.append({'at': float(x['at']), 'where': 'webcam' if str(x.get('where', '')).lower() in
                              ('webcam', 'cam', 'facecam') else 'game', 'why': str(x.get('why') or '')})
            except (KeyError, TypeError, ValueError):
                continue
    spots.sort(key=lambda s: s['at'])
    out = []
    for s in spots:
        if out and s['where'] == out[-1]['where'] and s['at'] - out[-1]['at'] <= MERGE_S:
            out[-1]['why'] += ' / ' + s['why']
        else:
            out.append(dict(s))
    return out


def close_up(pdir, project, spot, n, video):
    """21 frames, one a second, from 15 s before the spot to 5 s after: frames/zoom-NN.jpg."""
    t0 = max(0.0, spot['at'] - CLOSE_BEFORE)
    cam = cam_box(project)
    crop = None          # always the game with the webcam inset: on the GTA test two "webcam" spots were game crashes
    tmp = pdir / 'frames' / '.zoom'
    tmp.mkdir(parents=True, exist_ok=True)
    for old in tmp.glob('*.jpg'):
        old.unlink()
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-ss', f'{t0:.3f}', '-i', str(video), '-t',
                    f'{CLOSE_BEFORE + CLOSE_AFTER:g}', '-vf', f'fps=1,{_tile_filter(crop, cam, INSET[spot["where"]])}',
                    '-q:v', '4',
                    str(tmp / 'z%02d.jpg')], check=True)
    jump, react = loudness(pdir), reactions(pdir)
    level = loud_level(jump)
    laughs = (load_json(pdir / 'transcript' / 'cues.json', {}) or {}).get('laughter', [])
    tiles = []
    for p in sorted(tmp.glob('z*.jpg'))[:PER_SHEET]:
        t = t0 + int(p.stem[1:]) - 1
        tiles.append((p, fmt_ts(t).split('.')[0], *_marks(t, t + 1, jump, react, laughs, level)))
    return compose(tiles, pdir / 'frames' / f'zoom-{n:02d}.jpg')


def transcript_near(pdir, a, b):
    words = load_json(pdir / 'transcript' / 'words.json') or []
    lines = load_json(pdir / 'transcript' / 'sentences.json') or []
    rows = []
    for ln in lines:
        if 'i0' in ln and ln['e'] > a and ln['s'] < b:
            shown = [w['w'] for w in words[ln['i0']:ln['i1'] + 1] if not w.get('unsure')]
            if shown:
                rows.append(f"  [{ln['s']:.1f}-{ln['e']:.1f}] {' '.join(shown)}")
    return rows or ['  (nobody talks)']


def zoom(pdir, quiet=False):
    """Close-up sheets and helper packets for every spot (frames/zoom-batch-NN.txt). Returns the packets."""
    project = load_json(pdir / 'project.json', {}) or {}
    video = _video(pdir, project)
    spots = requests(pdir)
    for old in list((pdir / 'frames').glob('zoom-*.jpg')) + list((pdir / 'frames').glob('zoom-batch-*')):
        old.unlink()
    save_json(pdir / 'frames' / 'spots.json', spots)
    packets = []
    for b in range(0, len(spots), PER_BATCH):
        rows = [f'# ClipKaro close-ups, packet {b // PER_BATCH + 1}: "{project.get("title") or pdir.name}". Instructions: '
                f'.claude/agents/clipkaro-eventfinder.md. Write frames/zoom-batch-{b // PER_BATCH + 1:02d}.json.', '']
        for n, s in enumerate(spots[b:b + PER_BATCH], b + 1):
            sheet = close_up(pdir, project, s, n, video)
            t0 = max(0.0, s['at'] - CLOSE_BEFORE)
            seen = (f'sheet: {sheet.relative_to(pdir)} (one frame a second, {t0:.0f}-{t0 + 20:.0f} s; red border: the '
                    f'sound jumps; yellow word: a reaction)') if sheet else 'sheet: none (no frames there: past the end?)'
            rows += ['=' * 90, f'## SPOT {n} at {fmt_ts(s["at"]).split(".")[0]} ({s["at"]:.1f} s), {s["where"]}',
                     f'reader: {s["why"] or "-"}', seen,
                     'what is said around it (seconds in the video):'] + transcript_near(pdir, s['at'] - 25, s['at'] + 35)
            rows.append('')
        f = pdir / 'frames' / f'zoom-batch-{b // PER_BATCH + 1:02d}.txt'
        f.write_text('\n'.join(rows) + '\n', encoding='utf-8')
        packets.append(f)
        if not quiet:
            print(f'   close-ups: {min(len(spots), b + PER_BATCH)} of {len(spots)} spot(s)', flush=True)
    return packets


def collect(pdir):
    """The eventfinder answers -> frames/events.json [{spot, event_at, end, where, title, why}] (clips only)."""
    spots = load_json(pdir / 'frames' / 'spots.json') or []
    events = []
    for f in sorted((pdir / 'frames').glob('zoom-batch-*.json')):
        for x in load_json(f) or []:
            if str(x.get('verdict', '')).lower() != 'clip':
                continue
            try:
                at, end = float(x['event_at']), float(x['end'])
            except (KeyError, TypeError, ValueError):
                continue
            n = int(x.get('spot', 0) or 0)
            where = str(x.get('where') or (spots[n - 1]['where'] if 0 < n <= len(spots) else 'game')).lower()
            where = 'webcam' if where in ('webcam', 'cam', 'facecam') else 'game'
            if end - at >= 5:
                events.append({'spot': n, 'event_at': round(at, 2), 'end': round(end, 2), 'where': where,
                               'title': str(x.get('title') or ''), 'why': str(x.get('why') or '')})
    events.sort(key=lambda e: e['event_at'])
    save_json(pdir / 'frames' / 'events.json', events)
    return events


# ---------------------------------------------------------------- events into the clips

def exact_sheet(pdir, project, clip_id, at, where, video):
    """12 frames, 4 a second, from 1 s before the event to 2 s after: frames/exact-<id>.jpg."""
    cam = cam_box(project)
    crop = cam if where == 'webcam' else None
    tmp = pdir / 'frames' / '.exact'
    tmp.mkdir(parents=True, exist_ok=True)
    for old in tmp.glob('*.jpg'):
        old.unlink()
    t0 = max(0.0, at - 1.0)
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-ss', f'{t0:.3f}', '-i', str(video), '-t', '3', '-vf',
                    f'fps=4,{_tile_filter(crop, cam, INSET["game"])}', '-q:v', '4', str(tmp / 'e%02d.jpg')], check=True)
    tiles = [(p, f'{t0 + (int(p.stem[1:]) - 1) / 4:.2f}', False, '', False) for p in sorted(tmp.glob('e*.jpg'))[:12]]
    return compose(tiles, pdir / 'frames' / f'exact-{clip_id}.jpg', cols=6)


def apply_events(pdir, dry=False):
    """Put the events into clips.json: a clip that starts on the reaction starts at its event; an event no clip
    has becomes a new clip. Returns [(what, clip id, event)]; writes an exact-frame sheet for each."""
    project = load_json(pdir / 'project.json', {}) or {}
    events = load_json(pdir / 'frames' / 'events.json') or []
    doc = load_json(pdir / 'clips.json', {}) or {}
    clips = doc.get('clips', [])
    done = []
    move = settings().get('event_lead_in', True) is not False
    duration = float(project.get('duration') or 0) or None
    length = lambda c: sum(b - a for a, b in c['ranges'])                       # noqa: E731
    for ev in events:
        at = ev['event_at']
        if duration and at >= duration - 1.0:     # past the video's end: nothing to show
            continue
        start = round(max(0.0, at - LEAD_IN), 2)
        # a clip that already starts at the event (up to 5 s before it, never after it: then its first seconds
        # would still be missing), or one that already holds it: another would only repeat it (v2.7.1 review)
        twin = next((c for c in clips if c.get('ranges') and at - 5 <= c['ranges'][0][0] <= at + 0.3), None)
        inside = twin or next((c for c in clips for a, b in c.get('ranges', []) if a <= at < b), None)
        if inside:
            done.append(('already shows it', inside.get('id'), ev))
            continue
        after = next((c for c in clips if c.get('event_at') is None and c.get('ranges')
                      and at < c['ranges'][0][0] <= at + 30), None)
        if after and move and length(after) + (after['ranges'][0][0] - start) <= MAX_CLIP_S:
            after['ranges'][0][0] = start         # the clip that starts on the reaction starts at its cause
            after['event_at'], after['event_where'] = at, ev['where']
            done.append(('starts at its event', after.get('id'), ev))
            continue
        if after:                                 # "event_lead_in": false, or it would get too long: left as it is,
            done.append(('reaction clip kept', after.get('id'), ev))   # never a near-copy next to it
            continue
        end = min(float(ev['end']), start + MAX_CLIP_S, duration or float('inf'))
        if end - start < 5:
            continue
        cid = max([int(c.get('id', 0)) for c in clips] + [0]) + 1
        clips.append({'id': cid, 'from': f"event-{ev['spot']}", 'title': ev['title'] or f'Event at {fmt_ts(at)}',
                      'ranges': [[start, round(end, 2)]], 'event_at': at,
                      'event_where': ev['where'], 'why': ev['why'], 'score': None, 'clip_score': None})
        done.append(('new clip', cid, ev))
    if dry or not done:
        return done
    import shutil
    if not (pdir / 'clips-before-events.json').exists() and (pdir / 'clips.json').exists():
        shutil.copy2(pdir / 'clips.json', pdir / 'clips-before-events.json')
    doc['clips'] = clips
    save_json(pdir / 'clips.json', doc)
    video = _video(pdir, project)
    for what, cid, ev in done:
        if what in ('starts at its event', 'new clip'):
            exact_sheet(pdir, project, cid, ev['event_at'], ev['where'], video)
    return done
