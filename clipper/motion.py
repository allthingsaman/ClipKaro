"""Big action on screen, for gameplay videos: where the game picture moves the most.

    python run.py hints <project>     (runs this for gameplay and live streams)

A hint for Claude, next to the words: "[big action on screen ~4 s]". Like every hint it only shows
where to look; the streamer's words and reactions decide.

How (research, Nov 2026): in a study of game broadcasts, sound was the strongest single signal of a
highlight and the picture's motion the next (Autohighlight, 2022), so motion is a second hint next to
the game sound bursts of sound.py. The video is read at 4 frames a second, small (256x144, grey), with
the webcam overlay blacked out. Motion between frames is measured with OpenCV's DIS optical flow; the
camera's own pan (the median motion) is taken out, so turning the camera isn't "action"; the frame is
cut into 8x8 cells and the median cell counts, so a minimap or a HUD that always moves doesn't. The
moments above this video's 98th percentile for 2 s or more are kept, at most 3 per 10 minutes.
About 4 minutes of CPU per hour of 1080p60 gameplay (reading the video is nearly all of it).

Saves transcript/motion.json: {"v": 1, "action": [[start, end, peak], ...]}.
"""
import subprocess
import time

import numpy as np

from .common import load_json, probe, save_json

MOTION_V = 1
FPS = 4
W, H = 256, 144
GRID = 8
TOP = 98.0            # percentile of this video's motion above which a moment is "big action"
PER_10_MIN = 3        # at most this many per 10 minutes (the strongest): a few clear hints, not a list
MIN_S = 2.0           # ... for at least this long
GAP_S = 1.0           # moments closer than this are one


def frames(video, cam=None, src_w=1920, src_h=1080):
    """Small grey frames, FPS a second, with the webcam box blacked out. A generator."""
    vf = f'fps={FPS},scale={W}:{H},format=gray'
    # the processor decodes (it measured faster than the graphics card here: the full frames would have
    # to come back to memory for the scaling, and this ffmpeg can't scale on the card)
    p = subprocess.Popen(['ffmpeg', '-v', 'error', '-threads', '0', '-i', str(video), '-an', '-vf', vf,
                          '-f', 'rawvideo', '-'], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    while True:
        buf = p.stdout.read(W * H)
        if len(buf) < W * H:
            break
        f = np.frombuffer(buf, np.uint8).reshape(H, W).copy()
        if cam:
            x0 = max(0, int((cam['x'] - 0.1 * cam['w']) * W / src_w))
            y0 = max(0, int((cam['y'] - 0.1 * cam['h']) * H / src_h))
            x1 = min(W, int((cam['x'] + 1.1 * cam['w']) * W / src_w) + 1)
            y1 = min(H, int((cam['y'] + 1.1 * cam['h']) * H / src_h) + 1)
            f[y0:y1, x0:x1] = 0
        yield f
    p.wait()


def motion_track(video, cam=None, src_w=1920, src_h=1080):
    """Motion per frame (median over the grid cells of the flow left after the camera's own pan)."""
    import cv2
    dis = cv2.DISOpticalFlow_create(cv2.DISOPTICAL_FLOW_PRESET_ULTRAFAST)
    prev, out = None, []
    ch, cw = H // GRID, W // GRID
    for f in frames(video, cam, src_w, src_h):
        if prev is None:
            prev = f
            out.append(0.0)
            continue
        flow = dis.calc(prev, f, None)
        flow -= np.median(flow.reshape(-1, 2), axis=0)          # the camera's own pan
        mag = np.linalg.norm(flow, axis=2)
        cells = mag[:ch * GRID, :cw * GRID].reshape(GRID, ch, GRID, cw).mean(axis=(1, 3))
        out.append(float(np.median(cells)))
        prev = f
    return np.array(out, np.float32)


def action_spans(track, fps=FPS, top=TOP, min_s=MIN_S, gap_s=GAP_S):
    """[[start, end, peak]] where the smoothed motion stays above the video's `top` percentile."""
    if len(track) < fps * 30:
        return []
    k = max(1, int(fps))                                 # 1 s moving average
    sm = np.convolve(track, np.ones(k) / k, mode='same')
    thr = float(np.percentile(sm, top))
    on = sm > thr
    spans, start = [], None
    for i, x in enumerate(np.r_[on, False]):
        if x and start is None:
            start = i
        elif not x and start is not None:
            spans.append([start / fps, i / fps])
            start = None
    merged = []
    for a, b in spans:
        if merged and a - merged[-1][1] <= gap_s:
            merged[-1][1] = b
        else:
            merged.append([a, b])
    out = []
    for a, b in merged:
        if b - a >= min_s:
            peak = float(sm[int(a * fps):int(b * fps)].max() / (thr or 1.0))
            out.append([round(a, 2), round(b, 2), round(peak, 2)])
    from .hints import rare
    return rare(out, lambda r: r[2], PER_10_MIN)


def scan(pdir, quiet=False):
    project = load_json(pdir / 'project.json', {}) or {}
    from .fetch import video_file
    video = project.get('video') if project.get('kind') == 'local' else video_file(pdir)
    if not video:
        if not quiet:
            print('   (big-action hints skipped: the video is not downloaded yet; `cut` downloads it)')
        return None
    t = time.time()
    info = probe(video)
    track = motion_track(video, project.get('facecam') or None, info['width'], info['height'])
    m = {'v': MOTION_V, 'action': action_spans(track), 'seconds': round(time.time() - t, 1)}
    save_json(pdir / 'transcript' / 'motion.json', m)
    if not quiet:
        print(f"-> big action on screen in {m['seconds']:.0f}s: {len(m['action'])} moment(s)")
    return m


def ensure(pdir, quiet=False):
    m = load_json(pdir / 'transcript' / 'motion.json')
    return m if m and m.get('v') == MOTION_V else scan(pdir, quiet=quiet)
