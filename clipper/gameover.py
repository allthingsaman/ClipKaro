"""Game-over screens in gameplay (v2.9): WASTED, FAILED, BUSTED, GAME OVER ... as lines of their own in the transcript.

    python run.py gameover <project>            (fetch runs it for gameplay and live streams)
    python run.py gameover <project> --fresh    read the video again

Why: the owner's favourite gameplay clips are "boast, then fail": a friend promises to do a mission "like a
boss" and minutes later the game says FAILED (clip 161 of the GTA stream, made by hand on 21 November). The
fail is often only on screen, so Claude needs to see it in what it reads:
    [5437.50-5441.70] [on screen: FAILED - THE PHOENIX WAS DESTROYED.]
A line of its own (never tucked onto a spoken line), so a story clip can take it as a piece by its times.

How: only the video's keyframes are read (ffmpeg -skip_frame nokey: one every 2-4 s in a stream, read fast),
the middle of the picture (BOX, the webcam blacked out), shrunk to WIDTH pixels, by the English text reader
(subtitles.engine, never enlarged). A keyframe is a game-over screen when a fail phrase (FAIL_WORDS) is written
BIG (at least BIG of the box's height: the screen's title, not a line of small text). Neighbouring keyframes
with the same title are one screen; the smaller text under it (the reason) goes with it. Measured on the
GTA stream: 6-11 ms a keyframe without text, ~35 ms with: about a minute for 4 hours.
Saves transcript/gameover.json: {"v": 1, "screens": [[start, end, "FAILED", "THE PHOENIX WAS DESTROYED."], ...]}.
"game_over_screens": false in settings.json skips it.
"""
import argparse
import re
import subprocess
import threading
import time

import numpy as np

from .common import die, load_json, project_dir, save_json, settings

GAMEOVER_V = 1
BOX = (0.15, 0.15, 0.85, 0.80)       # left, top, right, bottom of the part of the picture read (centre titles)
WIDTH = 480                          # ... shrunk to this many pixels wide (FAILED read the same at 320-960)
BIG = 0.08                           # a title is at least this share of the box's height (FAILED: 0.29)
JOIN_S = 6.0                         # keyframes with the same title this close are one screen
HOLD_S = 4.0                         # a screen lasts until the next keyframe, at most this long after the last
LEAD_S = 0.5                         # ... and starts a little before the first keyframe that shows it
FAIL_WORDS = re.compile(r'\b(mission failed|failed|wasted|busted|game over|you died|you are dead|defeated|defeat|'
                        r'eliminated|knocked out|you lose|you lost)\b')


def wanted(project):
    from .kind import is_irregular
    return bool(settings().get('game_over_screens', True)) and is_irregular(project)


def plain(text):
    return re.sub(r'\s+', ' ', re.sub(r'[^a-z ]', ' ', (text or '').lower())).strip()


def title_of(texts, heights):
    """(the game-over title, the smaller reason text) of one keyframe's text lines, or None."""
    big = [(t, h) for t, h in zip(texts, heights) if h >= BIG]
    for t, h in sorted(big, key=lambda x: -x[1]):
        m = FAIL_WORDS.search(plain(t))
        if m:
            reason = next((x for x, hh in zip(texts, heights) if hh < BIG and len(plain(x)) >= 6), '')
            return m.group(1).upper(), reason.strip()[:60]
    return None


def keyframes(video, src_w, src_h, cam=None):
    """(time, small BGR picture of BOX) for every keyframe of the video. A generator."""
    x0, y0, x1, y1 = (int(BOX[0] * src_w), int(BOX[1] * src_h), int(BOX[2] * src_w), int(BOX[3] * src_h))
    w, h = x1 - x0, y1 - y0
    oh = int(round(h * WIDTH / w / 2)) * 2
    vf = f'crop={w}:{h}:{x0}:{y0},scale={WIDTH}:{oh},showinfo'
    p = subprocess.Popen(['ffmpeg', '-hide_banner', '-nostats', '-skip_frame', 'nokey', '-i', str(video), '-an',
                          '-vf', vf, '-fps_mode', 'passthrough', '-f', 'rawvideo', '-pix_fmt', 'bgr24', '-'],
                         stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    times = []

    def read_err():                    # showinfo writes each frame's time to stderr, in order
        for line in p.stderr:
            m = re.search(rb'pts_time:\s*([0-9.]+)', line)
            if m and b'showinfo' in line:
                times.append(float(m.group(1)))
    th = threading.Thread(target=read_err, daemon=True)
    th.start()
    size = WIDTH * oh * 3
    box = None
    if cam:                            # the webcam inside BOX, in the small picture's pixels
        k = WIDTH / w
        box = (max(0, int((cam['x'] - x0) * k)), max(0, int((cam['y'] - y0) * k)),
               min(WIDTH, int((cam['x'] + cam['w'] - x0) * k)), min(oh, int((cam['y'] + cam['h'] - y0) * k)))
    n = 0
    try:
        while True:
            buf = p.stdout.read(size)
            if len(buf) < size:
                break
            img = np.frombuffer(buf, np.uint8).reshape(oh, WIDTH, 3).copy()
            if box and box[2] > box[0] and box[3] > box[1]:
                img[box[1]:box[3], box[0]:box[2]] = 0
            for _ in range(200):       # its time comes on stderr a moment later
                if len(times) > n:
                    break
                time.sleep(0.005)
            t = times[n] if len(times) > n else None
            n += 1
            if t is not None:
                yield t, img
    finally:
        p.stdout.close()
        p.wait()


def screens_from(hits, key_times):
    """[(t, title, reason)] of the keyframes that show a game-over title -> merged screens
    [[start, end, title, reason]]. key_times: every keyframe's time (where a screen ends)."""
    import bisect
    out = []
    for t, title, reason in sorted(hits):
        if out and out[-1][2] == title and t - out[-1][4] <= JOIN_S:
            out[-1][4] = t
            out[-1][3] = out[-1][3] or reason
            continue
        out.append([t, None, title, reason, t])
    res = []
    for first, _, title, reason, last in out:
        j = bisect.bisect_right(key_times, last + 1e-3)
        nxt = key_times[j] if j < len(key_times) else last + HOLD_S
        res.append([round(max(0.0, first - LEAD_S), 2), round(min(nxt, last + HOLD_S), 2), title, reason])
    return res


def scan(pdir, quiet=False):
    project = load_json(pdir / 'project.json', {}) or {}
    from .kind import _video_file
    from .common import probe
    from . import subtitles
    video = _video_file(pdir, project)
    if not video:
        if not quiet:
            print('   (game-over screens later: the video is not downloaded yet)')
        return None
    ocr = subtitles.engine(WIDTH)
    if ocr is None:
        return None
    t0 = time.time()
    info = probe(video)
    rng = project.get('range')                 # only part of the video was asked for (v2.8)
    hits, key_times = [], []
    for t, img in keyframes(video, info['width'], info['height'], project.get('facecam') or None):
        key_times.append(t)
        if rng and not (rng[0] <= t <= (rng[1] if rng[1] is not None else 1e12)):
            continue
        res = ocr(img)
        if res is None or not getattr(res, 'txts', None):
            continue
        hs = [float(b[:, 1].max() - b[:, 1].min()) / img.shape[0] for b in res.boxes]
        found = title_of(list(res.txts), hs)
        if found:
            hits.append((t, *found))
    g = {'v': GAMEOVER_V, 'screens': screens_from(hits, key_times), 'keyframes': len(key_times),
         'seconds': round(time.time() - t0, 1)}
    save_json(pdir / 'transcript' / 'gameover.json', g)
    if not quiet:
        what = ', '.join(sorted({s[2] for s in g['screens']})) or 'none'
        print(f"-> game-over screens in {g['seconds']:.0f}s ({g['keyframes']} keyframes read): "
              f"{len(g['screens'])} ({what})")
    return g


def load(pdir):
    g = load_json(pdir / 'transcript' / 'gameover.json')
    return g if g and g.get('v') == GAMEOVER_V else None


def ensure(pdir, quiet=False):
    project = load_json(pdir / 'project.json', {}) or {}
    if not wanted(project):
        return None
    return load(pdir) or scan(pdir, quiet=quiet)


def screen_lines(pdir):
    """The transcript lines of the game-over screens: [{'s', 'e', 'note'}] (hints.silent_notes adds them)."""
    g = load(pdir)
    if not g or not settings().get('hints', True):
        return []
    return [{'s': a, 'e': b, 'note': f'[on screen: {title}' + (f' - {reason}' if reason else '') + ']'}
            for a, b, title, reason in g['screens']]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('project')
    ap.add_argument('--fresh', action='store_true', help='read the video again')
    a = ap.parse_args()
    pdir = project_dir(a.project)
    project = load_json(pdir / 'project.json', {}) or {}
    if not wanted(project):
        die('only for gameplay and live streams (or settings.json "game_over_screens" is false)')
    g = scan(pdir) if a.fresh or not load(pdir) else load(pdir)
    if g is None:
        die('no video yet (or no text reader): run cut once, or python install.py')
    from .fetch import render_transcript
    render_transcript(pdir, project, load_json(pdir / 'transcript' / 'sentences.json') or [])
    for a_, b_, title, reason in g['screens']:
        print(f'   {a_:9.2f}-{b_:9.2f}  {title}' + (f'  ({reason})' if reason else ''))


if __name__ == '__main__':
    main()
