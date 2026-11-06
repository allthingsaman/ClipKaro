"""Gameplay / screen recordings with a webcam overlay ("facecam").

`cut` stacks them into 9:16: the middle of the gameplay on top (cropped to fill the width, so it
stays tall), the cam enlarged at the bottom over a blurred copy of the game, and captions on the
line between the two (see `edit`).

The cam is found automatically: a small face that stays in the same spot near the side of the frame
in most sampled frames, unlike game characters or a presenter in a normal video. A round cam is
traced exactly (Hough circle) and drawn round; otherwise a box around the face is used. If it ever
picks the wrong spot, set the box yourself in settings.json, in fractions of the frame:
    "facecam": {"x": 0.80, "y": 0.35, "w": 0.19, "h": 0.34, "shape": "circle"}
"""
import cv2
import numpy as np

from .common import H, W
from .reframe import _faces

TOP_H = 1150                 # gameplay panel height (of 1920); the cam panel gets the rest
CAP_GAP = 10                 # caption line sits just below the seam
CAM_TOP_PAD, CAM_BOTTOM_PAD = 90, 30   # room for the captions above the cam


def _sample(video, duration, n=24):
    cap = cv2.VideoCapture(str(video))
    out = []
    for k in range(n):
        cap.set(cv2.CAP_PROP_POS_MSEC, duration * (k + 0.5) / n * 1000)
        ok, frame = cap.read()
        if ok:
            out.append(frame)
    cap.release()
    return out


def _faces_px(frame):
    scale = 640 / frame.shape[1]
    small = cv2.resize(frame, (640, int(frame.shape[0] * scale)))
    return [((x + w / 2) / scale, (y + h / 2) / scale, h / scale) for x, y, w, h in _faces(small)]


def _circle(frames, cx, cy, fh, src_w, src_h):
    """Median circle around the face (a round cam), or None."""
    found = []
    r0, r1 = int(0.9 * fh), int(2.4 * fh)
    pad = r1 + 10
    x0, y0 = max(0, int(cx - pad)), max(0, int(cy - pad))
    x1, y1 = min(src_w, int(cx + pad)), min(src_h, int(cy + pad))
    for f in frames:
        roi = cv2.medianBlur(cv2.cvtColor(f[y0:y1, x0:x1], cv2.COLOR_BGR2GRAY), 5)
        c = cv2.HoughCircles(roi, cv2.HOUGH_GRADIENT, dp=1.2, minDist=10 * r1, param1=120, param2=40,
                             minRadius=r0, maxRadius=r1)
        if c is None:
            continue
        for x, y, r in c[0]:
            if np.hypot(x + x0 - cx, y + y0 - cy) < 0.6 * fh:
                found.append((x + x0, y + y0, r))
                break
    if len(found) < max(2, len(frames) // 3):
        return None
    return [float(v) for v in np.median(np.array(found), axis=0)]


def detect(video, duration, src_w, src_h):
    """{'x','y','w','h' (px), 'shape': 'circle'|'rect'} for a webcam overlay, or None."""
    frames = _sample(video, duration)
    if len(frames) < 6:
        return None
    per_frame = [_faces_px(f) for f in frames]
    tol = 0.03 * src_w
    best, best_hits = None, []
    for faces in per_frame:
        for c in faces:
            hits = []
            for i, fs in enumerate(per_frame):
                near = [f for f in fs if abs(f[0] - c[0]) < tol and abs(f[1] - c[1]) < tol]
                if near:
                    hits.append((i, near[0]))
            if len(hits) > len(best_hits):
                best, best_hits = c, hits
    if not best or len(best_hits) < max(4, 0.5 * len(frames)):
        return None
    cx, cy, fh = (float(v) for v in np.median(np.array([h[1] for h in best_hits]), axis=0))
    # a cam overlay is small and sits towards a side; a presenter's face in a normal video isn't both
    if fh > 0.2 * src_h or 0.28 * src_w < cx < 0.72 * src_w:
        return None
    circle = _circle([frames[i] for i, _ in best_hits], cx, cy, fh, src_w, src_h)
    if circle:
        x, y, r = circle
        r += 3                                      # keep the cam's own ring/border
        return {'x': x - r, 'y': y - r, 'w': 2 * r, 'h': 2 * r, 'shape': 'circle'}
    bh = min(src_h, 3.0 * fh)                       # a typical rectangular cam around the face
    bw = min(src_w, bh * 4 / 3)
    return {'x': cx - bw / 2, 'y': cy - bh * 0.45, 'w': bw, 'h': bh, 'shape': 'rect'}


def from_settings(box, src_w, src_h):
    """settings.json "facecam" (fractions of the frame) -> px box."""
    return {'x': box['x'] * src_w, 'y': box['y'] * src_h, 'w': box['w'] * src_w, 'h': box['h'] * src_h,
            'shape': box.get('shape', 'rect')}


def clamp(cam, src_w, src_h):
    x, y = max(0, int(cam['x'])), max(0, int(cam['y']))
    w, h = min(src_w - x, int(cam['w'])) // 2 * 2, min(src_h - y, int(cam['h'])) // 2 * 2
    return {**cam, 'x': x, 'y': y, 'w': w, 'h': h}


def geometry(cam, src_w, src_h):
    """Where everything goes in the 1080x1920 frame."""
    bot_h = H - TOP_H
    gw = min(src_w, int(src_h * W / TOP_H) // 2 * 2)          # gameplay crop, full height
    gx = (src_w - gw) // 2
    if cam['x'] < gx + gw and cam['x'] + cam['w'] > gx:       # don't show the cam twice
        right = cam['x'] + cam['w'] / 2 > src_w / 2
        gx = max(0, min(int(cam['x']) - gw, gx)) if right else min(src_w - gw, max(int(cam['x'] + cam['w']), gx))
    gx = gx // 2 * 2
    room_w, room_h = W - 2 * 60, bot_h - CAM_TOP_PAD - CAM_BOTTOM_PAD
    s = min(room_w / cam['w'], room_h / cam['h'])
    cw, ch = int(cam['w'] * s) // 2 * 2, int(cam['h'] * s) // 2 * 2
    return {'gx': gx, 'gw': gw, 'bot_h': bot_h, 'cam_w': cw, 'cam_h': ch,
            'cam_x': (W - cw) // 2, 'cam_y': CAM_TOP_PAD + (room_h - ch) // 2,
            'caption_y': TOP_H + CAP_GAP}


def mask_png(path, w, h):
    """Round mask for a round cam (white circle, anti-aliased edge)."""
    m = np.zeros((h, w), np.uint8)
    cv2.ellipse(m, (w // 2, h // 2), (w // 2 - 1, h // 2 - 1), 0, 0, 360, 255, -1, lineType=cv2.LINE_AA)
    cv2.imwrite(str(path), m)
    return path


def filter_chain(inp, label, cam, g, src_w, src_h, fps, mask_label=None):
    """ffmpeg filter: one range of input `inp` -> stacked 1080x1920 [label]."""
    p = f'{label}_'
    bot_h = g['bot_h']
    cam_crop = f"crop={cam['w']}:{cam['h']}:{cam['x']}:{cam['y']},scale={g['cam_w']}:{g['cam_h']}:flags=lanczos"
    parts = [
        f'[{inp}]split=3[{p}g][{p}b][{p}c]',
        f"[{p}g]crop={g['gw']}:{src_h}:{g['gx']}:0,scale={W}:{TOP_H}:flags=lanczos,setsar=1[{p}top]",
        f'[{p}b]scale={W}:{bot_h}:force_original_aspect_ratio=increase,crop={W}:{bot_h},'
        f'boxblur=30:3,eq=brightness=-0.12,setsar=1[{p}bg]',
    ]
    if mask_label:
        parts.append(f'[{p}c]{cam_crop},format=rgba[{p}cam0]')
        parts.append(f'[{p}cam0][{mask_label}]alphamerge[{p}cam]')
    else:
        parts.append(f'[{p}c]{cam_crop},setsar=1[{p}cam]')
    parts.append(f"[{p}bg][{p}cam]overlay={g['cam_x']}:{g['cam_y']}:shortest=1[{p}bot]")
    parts.append(f'[{p}top][{p}bot]vstack=inputs=2,setsar=1,fps={fps},format=yuv420p[{label}]')
    return ';'.join(parts)
