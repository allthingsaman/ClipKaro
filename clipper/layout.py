"""Where text goes on a 9:16 clip: clear of faces, and clear of the apps' own buttons.

Shorts, Reels and TikTok draw their buttons and texts over the video. None of them publishes safe
zones for normal posts (only for ads), and guides disagree, so we use the strictest common numbers:
TikTok's ad template keeps the bottom 484 px and the right 140 px of 1080x1920 free (its like/comment
column and the caption text), and Shorts and Reels cover about the top 210 px. Captions stay between
SAFE_TOP and SAFE_BOTTOM and no wider than SAFE_W, centred.

Faces: a few frames of each shot of the cut clip are checked for faces (the same detector as the
framing), and every face's box, grown by the strongest zoom and with room for the chin, is a
keep-out area. Captions keep their usual line unless it would cover a face; then they move to the
nearest line that doesn't (once per shot, so they don't jump around). The hook title goes in the
upper part of the frame, above or below the faces.
"""
import cv2

from .common import H, W

SAFE_TOP, SAFE_BOTTOM = 230, 1436       # px of 1920: Shorts / Reels top bar; TikTok's bottom 484 px
SAFE_RIGHT = 940                        # TikTok's button column starts here
SAFE_W = 2 * (SAFE_RIGHT - W // 2)      # centred text no wider than this (800 px)
CAP_H = 130                             # one caption line (96 px text, outline included)
MAX_ZOOM = 1.22                         # the strongest punch-in of the edit (plan.PUNCH)
CHIN = 0.30                             # room below a face box for the chin and mouth (share of its height)
SAMPLES = 4                             # frames checked per shot


def face_boxes(clip_mp4, shots):
    """{shot index: [(x0, y0, x1, y1)]} in output pixels, faces seen in the cut clip (union over a
    few frames of the shot), grown for the zoom and the chin."""
    from .reframe import _faces
    cap = cv2.VideoCapture(str(clip_mp4))
    out = {}
    for i, sh in enumerate(shots):
        t0, t1 = sh['t0'], sh['t1']
        fx, fy = (sh.get('focus') or [W / 2, H / 2])[:2]
        boxes = []
        for k in range(SAMPLES):
            cap.set(cv2.CAP_PROP_POS_MSEC, (t0 + (t1 - t0) * (k + 0.5) / SAMPLES) * 1000)
            ok, frame = cap.read()
            if not ok:
                continue
            h, w = frame.shape[:2]
            small = cv2.resize(frame, (w // 2, h // 2))
            for x, y, bw, bh in _faces(small):
                x, y, bw, bh = 2 * x * W / w, 2 * y * H / h, 2 * bw * W / w, 2 * bh * H / h
                if bh < 0.04 * H:               # a face in the background, a poster: not what we keep clear
                    continue
                y1 = y + bh * (1 + CHIN)
                # the zoom scales around the focus point: the box grows with it
                z = MAX_ZOOM
                boxes.append((fx + (x - fx) * z, fy + (y - fy) * z, fx + (x + bw - fx) * z, fy + (y1 - fy) * z))
        out[i] = boxes
    cap.release()
    return out


def _overlap(band, boxes, half_w):
    """Area of a text band (centre y, height) that covers face boxes."""
    y, h = band
    a0, a1, x0, x1 = y - h / 2, y + h / 2, W / 2 - half_w, W / 2 + half_w
    return sum(max(0.0, min(a1, b[3]) - max(a0, b[1])) * max(0.0, min(x1, b[2]) - max(x0, b[0])) for b in boxes)


def place(default_y, h, boxes, candidates, half_w=SAFE_W / 2, avoid=()):
    """The y (text centre) nearest default_y, inside the safe zone, that covers no face (nor the
    `avoid` bands, (y, h) pairs); else the one covering the least."""
    ok = [y for y in candidates if SAFE_TOP + h / 2 <= y <= SAFE_BOTTOM - h / 2]
    if not ok:
        return default_y
    def cost(y):
        hits = _overlap((y, h), boxes, half_w)
        hits += sum(max(0.0, min(y + h / 2, ay + ah / 2) - max(y - h / 2, ay - ah / 2)) * 2 * half_w
                    for ay, ah in avoid)
        return (round(hits), abs(y - default_y))
    return min(ok, key=cost)


def caption_lines(default_y, mode):
    """Lines a caption may move to, nearest first. Split screen: around the seam; facecam: its seam."""
    if mode in ('split', 'facecam'):
        return [default_y, default_y + 40, default_y - 40]
    return [default_y, default_y + 60, default_y - 90, default_y - 180, default_y - 270, default_y - 360]


TITLE_LINES = [400, 320, 500, 620, 760]     # hook title centre lines, top part of the frame first
