"""Preview what the vertical crop will keep, before cutting, and spot moments that need the whole frame.

    python run.py frames <project>               # every clip in clips.json
    python run.py frames <project> --clips 1,3   # only some
    python run.py frames <project> --every 1.5   # seconds between pictures (default 2)

For each clip it writes output/<project>/frames/NN-title.jpg: a sheet of frames from the source
video, each labelled with its time in seconds (the same seconds clips.json uses), with a GREEN box
showing what the 9:16 crop keeps. Frames already shown whole (slides, b-roll, `show_full` spans)
get a BLUE border and the label FULL. An ORANGE dot marks words that point at something
("maine dikhaya", "itna bada", "look at this").

It also measures movement outside the crop box compared with inside it. When something outside the
crop moves a lot (a box lifted up, a product shown, a screen pointed at), those frames get a RED
border and the time span is printed. Open the sheets: if what the speaker shows or talks about lies
outside the green box, add it to that clip in clips.json, in source seconds, at sentence edges:

    "show_full": [[656.32, 674.26]]

`cut` then shows the whole landscape frame over a blurred background for exactly that stretch,
without zooming in. The movement check is only a hint: something held still (a console held up,
a whiteboard) doesn't move, so always look at the sheets.
"""
import argparse
import re

import cv2
import numpy as np

from .common import load_json, probe, project_dir, settings, slugify
from .cut import apply_framing, ensure_video, framing_spans, range_shots, two_person
from .reframe import crop_width

TILE_W, TILE_H = 320, 180
COLS = 6
STEP = 0.5                 # seconds between frames for the movement check
WINDOW = 2.0               # movement is averaged over this many seconds
OUTSIDE_MIN = 12.0         # mean pixel change (0-255) outside the crop that counts as "a lot"
OUTSIDE_VS_INSIDE = 0.7    # ... and it must be at least this share of the change inside the crop

# Words that point at something the viewer should see ("I showed", "this big", "as you can see").
# Checked on each word plus the next one. A hint only: Claude confirms by looking at the sheet.
SHOW_WORDS = re.compile(
    r'^(दिखा\S*'                                       # दिखाया, दिखाऊं, दिखाता, दिखाना: showing
    r'|(इतना|इतनी|इतने) (बड़|छोट|लंब|मोट)\S*'           # "itna bada": this big / small / long
    r'|यह[ाँं]* तक'                                    # "yahan tak": up to here
    r'|देख (रहे|सकते)\S*'                              # "dekh rahe ho": as you can see
    r'|look\b|see\b|show\S*|watch\b'
    r'|(this|that) (big|small|one|thing|box|screen)\b'
    r'|right here\b|check (this|it)\b)', re.I)


def _gray(frame):
    small = cv2.resize(frame, (TILE_W, TILE_H))
    return small, cv2.GaussianBlur(cv2.cvtColor(small, cv2.COLOR_BGR2GRAY), (5, 5), 0).astype(np.float32)


def outside_activity(cap, start, dur, shots, src_w):
    """[(t_abs, inside, outside)] movement per STEP inside vs outside the crop box (crop shots only)."""
    rows, prev, t = [], None, 0.0
    while t < dur:
        cap.set(cv2.CAP_PROP_POS_MSEC, (start + t) * 1000)
        ok, fr = cap.read()
        if not ok:
            break
        _, g = _gray(fr)
        sh = next((s for s in shots if s['a'] <= t < s['b']), shots[-1])
        if prev is not None and sh['mode'] == 'crop':
            a = int(sh['x0'] / src_w * TILE_W)
            b = int((sh['x0'] + sh['cw']) / src_w * TILE_W)
            d = np.abs(g - prev)
            outside = np.concatenate([d[:, :a], d[:, b:]], axis=1)
            if outside.size:
                rows.append((start + t, float(d[:, a:b].mean()), float(outside.mean())))
        prev = g
        t += STEP
    return rows


def flagged_spans(rows):
    """Merge windows where the outside of the crop moves a lot into [(t0, t1)] spans."""
    n = max(1, int(WINDOW / STEP))
    hot = []
    for i in range(len(rows)):
        win = rows[max(0, i - n + 1):i + 1]
        ins = sum(r[1] for r in win) / len(win)
        out = sum(r[2] for r in win) / len(win)
        if out >= OUTSIDE_MIN and out >= OUTSIDE_VS_INSIDE * ins:
            hot.append((win[0][0], rows[i][0]))
    spans = []
    for a, b in hot:
        if spans and a <= spans[-1][1] + STEP:
            spans[-1][1] = max(spans[-1][1], b)
        else:
            spans.append([a, b])
    return [(round(a, 1), round(b, 1)) for a, b in spans if b - a >= 1.0]


def show_cues(words):
    """[(time, 'words')] where the speaker points at something with words."""
    out = []
    for i, w in enumerate(words):
        pair = (w['w'] + ' ' + words[i + 1]['w']) if i + 1 < len(words) else w['w']
        pair = re.sub(r'[.,!?।॥"]', '', pair).strip()
        m = SHOW_WORDS.match(pair)
        if m:
            out.append((w['s'], m.group(0)))
    return out


def sheet(cap, clip, video, info, every, words, planned, auto):
    src_w, src_h = info['width'], info['height']
    cw = crop_width(src_w, src_h)
    tiles, flags, hints, faces = [], [], [], []
    for s, dur, shots in planned:
        e = s + dur
        shots = apply_framing(shots, auto or [], s, dur, src_w, src_h)
        shots = apply_framing(shots, framing_spans(clip), s, dur, src_w, src_h)
        for sh in shots:
            sh['cw'] = cw
            if sh.get('ambiguous') and sh['mode'] == 'crop' and not auto:
                faces.append((s + sh['a'], s + sh['b'], sh.get('subjects') or [], sh['face'][0] if sh.get('face') else None))
        spans = flagged_spans(outside_activity(cap, s, dur, shots, src_w))
        flags += spans
        cues = [c for c in show_cues(words) if s <= c[0] <= e]
        hints += cues
        t = 0.0
        while t < dur:
            cap.set(cv2.CAP_PROP_POS_MSEC, (s + t) * 1000)
            ok, fr = cap.read()
            if not ok:
                break
            sh = next((x for x in shots if x['a'] <= t < x['b']), shots[-1])
            tile, _ = _gray(fr)
            for cx in sh.get('subjects') or []:          # a cyan mark above every face found
                x = int(cx * TILE_W)
                cv2.drawMarker(tile, (x, 12), (255, 255, 0), cv2.MARKER_TRIANGLE_DOWN, 14, 3)
            directed = any(a <= s + t < b for a, b, _ in auto or [])
            if sh['mode'] == 'split':
                for (bx, by, bw, bh), col in ((sh['top'], (255, 0, 255)), (sh['bottom'], (0, 200, 255))):
                    cv2.rectangle(tile, (int(bx / src_w * TILE_W), int(by / src_h * TILE_H)),
                                  (int((bx + bw) / src_w * TILE_W), int((by + bh) / src_h * TILE_H)), col, 3)
                cv2.putText(tile, 'BOTH (split)', (8, TILE_H - 12), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 0, 255), 2)
            elif directed and sh['mode'] == 'crop':
                cv2.putText(tile, 'SPEAKER', (8, TILE_H - 12), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 230, 0), 2)
            elif sh.get('ambiguous') and sh['mode'] == 'crop':
                cv2.putText(tile, '2 FACES', (8, TILE_H - 12), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 0, 255), 2)
            if sh['mode'] == 'crop':
                a = int(sh['x0'] / src_w * TILE_W)
                cv2.rectangle(tile, (a, 1), (int(a + cw / src_w * TILE_W), TILE_H - 2), (0, 220, 0), 3)
            elif sh['mode'] == 'fit':
                cv2.rectangle(tile, (1, 1), (TILE_W - 2, TILE_H - 2), (255, 140, 0), 5)
                cv2.putText(tile, 'FULL', (TILE_W - 70, TILE_H - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 140, 0), 2)
            if any(abs(c[0] - (s + t)) <= every / 2 + 0.5 for c in cues):
                cv2.circle(tile, (TILE_W - 18, 18), 10, (0, 165, 255), -1)
            if any(a <= s + t <= b for a, b in spans):
                cv2.rectangle(tile, (6, 6), (TILE_W - 7, TILE_H - 7), (0, 0, 255), 3)
            cv2.putText(tile, f'{s + t:.1f}s', (8, 26), cv2.FONT_HERSHEY_SIMPLEX, 0.75, (0, 0, 0), 4)
            cv2.putText(tile, f'{s + t:.1f}s', (8, 26), cv2.FONT_HERSHEY_SIMPLEX, 0.75, (0, 255, 255), 2)
            tiles.append(tile)
            t += every
    if not tiles:
        return None, flags, hints, faces
    while len(tiles) % COLS:
        tiles.append(np.zeros_like(tiles[0]))
    return np.vstack([np.hstack(tiles[i:i + COLS]) for i in range(0, len(tiles), COLS)]), flags, hints, faces


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('project')
    ap.add_argument('--clips', default=None, help='comma list of clip ids, e.g. 1,3')
    ap.add_argument('--every', type=float, default=2.0, help='seconds between pictures on the sheet')
    a = ap.parse_args()

    pdir = project_dir(a.project)
    project = load_json(pdir / 'project.json')
    picks = load_json(pdir / 'clips.json')
    if not picks or not picks.get('clips'):
        print(f'no clips.json in {pdir} yet. Pick the clips first.')
        return
    video = ensure_video(pdir, project)
    info = probe(video)
    if info['width'] / info['height'] < 1.2:
        print('-> this video is already vertical or square: nothing gets cropped away, no sheets needed')
        return
    if project.get('facecam') and (settings().get('layout', 'auto') != 'crop'):
        print('-> facecam layout: the gameplay is shown on top, so the crop sheets do not apply')
    want = {int(x) for x in a.clips.split(',')} if a.clips else None
    words = load_json(pdir / 'transcript' / 'words.json') or []
    out_dir = pdir / 'frames'
    out_dir.mkdir(exist_ok=True)
    plans = {}
    for i, clip in enumerate(picks['clips'], 1):
        cid = int(clip.get('id', i))
        if not want or cid in want:
            plans[cid] = (clip, range_shots(video, info, clip, words))
    auto = two_person(pdir, video, plans, words)
    cap = cv2.VideoCapture(str(video))
    for i, clip in enumerate(picks['clips'], 1):
        cid = int(clip.get('id', i))
        if cid not in plans:
            continue
        img, flags, hints, faces = sheet(cap, clip, video, info, a.every, words, plans[cid][1], auto.get(cid))
        if img is None:
            continue
        path = out_dir / f'{cid:02d}-{slugify(clip.get("title", "clip"), 40)}.jpg'
        cv2.imwrite(str(path), img, [cv2.IMWRITE_JPEG_QUALITY, 82])
        note = ''
        if flags:
            note = ('  <- movement outside the crop at ' + ', '.join(f'{x:.1f}-{y:.1f}s' for x, y in flags) +
                    ': if that is what is shown or talked about, add "show_full"')
        full = f"  (show_full: {clip['show_full']})" if clip.get('show_full') else ''
        print(f'   clip {cid}: {path}{full}{note}')
        if hints:
            print('      words that point at something: ' + ', '.join(f'{x:.1f}s "{y}"' for x, y in hints))
        for x, y, subjects, picked in faces:
            side = 'left' if picked is not None and picked <= min(subjects) + 0.01 else 'right'
            other = 'right' if side == 'left' else 'left'
            print(f'      faces too far apart for one crop at {x:.1f}-{y:.1f}s (x = '
                  + ', '.join(f'{c:.2f}' for c in sorted(subjects)) + f'): kept the {side} one. '
                  f'Other choices: "framing": [[{x:.1f}, {y:.1f}, "{other}"]] or "full"')
    cap.release()
    print('\nLook at each sheet: GREEN = what the vertical crop keeps, BLUE/FULL = shown whole, '
          'CYAN marks = faces found, SPEAKER = the two-person framing shows the one talking, '
          'BOTH (split) = both people stacked (MAGENTA box on top), '
          '"2 FACES" = two faces too far apart for one crop and no voice models: check from the '
          'transcript who is speaking and pick that side with "framing", '
          'RED = movement outside the crop, ORANGE dot = words that point at something (hints).')
    print('If what the speaker shows or talks about is outside the green box, add it to that clip in clips.json, e.g.\n'
          '  "show_full": [[656.32, 674.26]]   (source seconds, at sentence edges)  then run cut again.\n'
          'If the listener visibly laughs or reacts while the other talks, show both people there:\n'
          '  "framing": [[5492.9, 5501.08, "split"]]')


if __name__ == '__main__':
    main()
