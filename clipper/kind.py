"""What kind of video this is (live stream? gameplay?), and where its break screens are.

    python run.py kind <project>              # fetch runs it by itself at the end
    python run.py kind <project> --redo       # look at the video again
    python run.py kind <project> --keep 2     # break 2 is real video after all: show its lines again

Live streams and gameplay videos need a few extra rules, so ClipKaro finds out on its own:
  * live stream: YouTube says it was live (or it is a /live/ link). For a file on your computer, a
    break screen in the middle of it gives it away.
  * gameplay: YouTube's category is Gaming, or a webcam overlay (facecam) sits near a side.
  * break screens ("Starting soon", "Be right back", "Stream ending"): the picture stands nearly
    still for 30 seconds or more and nobody is on the cam. A pause menu or a map with the streamer
    talking in the cam is NOT a break. In a video that never shows a face, a still picture counts
    as a break only when almost nothing is said over it.

The lines said during a break (often song lyrics from the break music) are left out of
transcript.txt and of the parts: one marker line shows where the break was, so no clip comes from
it, and `cut --check` warns if a clip still touches one. output/<project>/breaks.jpg shows one
picture of each break, for a quick look.

How the stillness is measured: only the video's keyframes are decoded (one every few seconds, about
25 s for a 100-minute 1080p stream), each shrunk to 64x36 grey, and neighbours compared. On a real
stream, gameplay changed by 15-60 per keyframe, animated break screens by 4-6, and pause menus by
about 1 (those had the streamer in the cam).
"""
import argparse
import re
import subprocess

import numpy as np

from .common import ROOT, die, fmt_ts, load_json, probe, project_dir, save_json, settings

STILL = 8.0                # mean change per keyframe (0-255 grey, 64x36) below which the picture "stands still"
MIN_BREAK_S = 30.0         # a break screen lasts at least this long
EDGE_S = 60.0              # a break that starts in the first minute is the starting screen; the last minute, the ending
FACE_SAMPLES = 4           # pictures checked for a face inside each still stretch
QUIET = 0.30               # without any faces to go by: a break has words over less than this share of its time
SCAN_V = 1                 # bump when the scan changes, so old results are redone


# ---------------------------------------------------------------- what the video page says

def live_info(project):
    """(True/False, why) from YouTube's own data, or the link itself."""
    status = project.get('live_status')
    if status in ('was_live', 'post_live', 'is_live') or project.get('was_live'):
        return True, 'YouTube says it was a live stream'
    if re.search(r'youtube\.com/live/|twitch\.tv/', str(project.get('source') or '')):
        return True, 'the link is a live-stream link'
    return False, None


def refresh_metadata(project):
    """Older projects have no live/category data: ask YouTube once (a few seconds). Never fatal."""
    if project.get('kind') != 'youtube' or 'live_status' in project:
        return
    try:
        import json
        from .fetch import ytdlp, page_facts
        meta = json.loads(ytdlp(['--dump-single-json', '--skip-download', project['source']],
                                project.get('cookies_from_browser')))
        project.update(page_facts(meta))
    except SystemExit:
        project['live_status'] = None
    except Exception as e:                      # offline: the link and the picture still tell a lot
        print(f'   (could not ask YouTube whether it was live: {type(e).__name__})')
        project['live_status'] = None


# ---------------------------------------------------------------- the picture

def keyframe_strip(video):
    """(times, frames as float32 [n, 36, 64]) of the video's keyframes, at most one per 2 s."""
    cmd = ['ffmpeg', '-hide_banner', '-v', 'info', '-skip_frame', 'nokey', '-i', str(video), '-an', '-sn',
           '-vf', "select='isnan(prev_selected_t)+gte(t-prev_selected_t\\,2)',scale=64:36:flags=area,format=gray,showinfo",
           '-fps_mode', 'passthrough', '-f', 'rawvideo', '-']
    r = subprocess.run(cmd, capture_output=True)
    frames = np.frombuffer(r.stdout, np.uint8)
    n = len(frames) // (64 * 36)
    times = [float(m) for m in re.findall(rb'pts_time:\s*([0-9.]+)', r.stderr)]
    n = min(n, len(times))
    if n < 3:
        return np.zeros(0), np.zeros((0, 36, 64), np.float32)
    return np.array(times[:n]), frames[:n * 64 * 36].reshape(n, 36, 64).astype(np.float32)


def still_runs(times, frames):
    """[(first index, last index)] of stretches where the picture stands nearly still for MIN_BREAK_S
    or more. A single odd keyframe inside (a flicker, a passing animation) doesn't break a stretch."""
    n = len(times)
    if n < 3:
        return []
    d1 = np.abs(np.diff(frames, axis=0)).mean(axis=(1, 2))            # d1[j-1]: frame j-1 -> j
    link = list(d1 < STILL)
    for j in range(1, n - 1):                                          # j is a one-frame flicker
        if not link[j - 1] and not link[j] and np.abs(frames[j + 1] - frames[j - 1]).mean() < STILL:
            link[j - 1] = link[j] = True
    runs, start = [], 0
    for j in range(1, n + 1):
        if j == n or not link[j - 1]:
            if j - 1 - start >= 2 and times[j - 1] - times[start] >= MIN_BREAK_S:
                runs.append((start, j - 1))
            start = j
    return runs


def _face_found(frame, box):
    import cv2
    from .reframe import _faces
    if box:
        pad_w, pad_h = 0.1 * box['w'], 0.1 * box['h']
        x0, y0 = max(0, int(box['x'] - pad_w)), max(0, int(box['y'] - pad_h))
        x1 = min(frame.shape[1], int(box['x'] + box['w'] + pad_w))
        y1 = min(frame.shape[0], int(box['y'] + box['h'] + pad_h))
        frame = frame[y0:y1, x0:x1]
        width = 320
    else:
        width = 640
    if frame.size == 0:
        return False
    scale = width / frame.shape[1]
    small = cv2.resize(frame, (width, max(1, int(frame.shape[0] * scale))))
    return bool(_faces(small))


def face_share(cap, a, b, box, n=FACE_SAMPLES):
    """Share of n pictures inside [a, b] with a face (in the cam box when there is one), or None."""
    import cv2
    got = hits = 0
    for k in range(n):
        cap.set(cv2.CAP_PROP_POS_MSEC, (a + (b - a) * (k + 0.5) / n) * 1000)
        ok, frame = cap.read()
        if ok:
            got += 1
            hits += _face_found(frame, box)
    return hits / got if got else None


def faces_common(cap, duration, n=12):
    """True when faces show up in a good share of the whole video (a person on camera)."""
    share = face_share(cap, 0, duration, None, n)
    return bool(share and share >= 0.3)


def speech_share(words, a, b):
    """Share of [a, b] covered by clearly heard words."""
    said = sum(max(0.0, min(w['e'], b) - max(w['s'], a)) for w in words
               if not w.get('unsure') and w['e'] > a and w['s'] < b)
    return said / max(1e-6, b - a)


def find_breaks(pdir, project, video, words):
    """Scan the picture. Returns (breaks, facts) and stores the facecam like `cut` does."""
    import cv2
    from . import facecam as fclib
    info = probe(video)
    dur, src_w, src_h = info['duration'], info['width'], info['height']
    box = settings().get('facecam')
    if box:
        cam = fclib.from_settings(box, src_w, src_h)
    else:
        if 'facecam' not in project:
            project['facecam'] = fclib.detect(video, dur, src_w, src_h) or False
        cam = project['facecam'] or None
    times, frames = keyframe_strip(video)
    runs = still_runs(times, frames)
    cap = cv2.VideoCapture(str(video))
    if cam:
        how = 'cam'
    elif faces_common(cap, dur):
        how = 'face'
    else:
        how = 'speech'
    breaks, kept_still = [], 0
    for i0, i1 in runs:
        a = 0.0 if i0 == 0 else float(times[i0])
        b = dur if i1 == len(times) - 1 else float(times[i1])
        talk = speech_share(words, a, b)
        faces = face_share(cap, float(times[i0]), float(times[i1]), cam) if how != 'speech' else None
        if how == 'cam':
            is_break = faces is not None and faces < 0.5
        elif how == 'face':
            is_break = faces is not None and faces < 0.5 and talk < QUIET
        else:
            is_break = talk < QUIET
        if not is_break:
            kept_still += 1
            continue
        where = 'start' if a < EDGE_S else ('end' if b > dur - EDGE_S else 'middle')
        breaks.append({'n': len(breaks) + 1, 'start': round(a, 2), 'end': round(b, 2), 'where': where,
                       'talk': round(talk, 2), 'faces': None if faces is None else round(faces, 2)})
    cap.release()
    facts = {'v': SCAN_V, 'video': video.name, 'how': how, 'keyframes': int(len(times)),
             'still_kept': kept_still, 'cam': bool(cam)}
    return breaks, facts


NAMES = {'start': 'starting screen', 'middle': 'break screen (be right back)', 'end': 'ending screen'}


def break_sheet(video, breaks, out):
    """One picture of each break, labelled, in one image (for a quick look)."""
    import cv2
    if not breaks:
        if out.exists():
            out.unlink()
        return None
    cap = cv2.VideoCapture(str(video))
    tiles = []
    for b in breaks:
        cap.set(cv2.CAP_PROP_POS_MSEC, (b['start'] + b['end']) / 2 * 1000)
        ok, frame = cap.read()
        tile = cv2.resize(frame, (480, 270)) if ok else np.zeros((270, 480, 3), np.uint8)
        label = f"{b['n']}  {fmt_ts(b['start']).split('.')[0]}-{fmt_ts(b['end']).split('.')[0]}  {b['where']}"
        cv2.rectangle(tile, (0, 0), (480, 34), (0, 0, 0), -1)
        cv2.putText(tile, label, (8, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2, cv2.LINE_AA)
        tiles.append(tile)
    cap.release()
    while len(tiles) % 3 and len(tiles) > 3:
        tiles.append(np.zeros((270, 480, 3), np.uint8))
    rows = [np.hstack(tiles[k:k + 3]) for k in range(0, len(tiles), 3)]
    cv2.imwrite(str(out), np.vstack(rows) if len(rows) > 1 else rows[0], [cv2.IMWRITE_JPEG_QUALITY, 80])
    return out


# ---------------------------------------------------------------- shared with parts, fetch and cut

def active_breaks(project):
    """The breaks whose lines are left out (not the ones the user kept)."""
    return [b for b in (project or {}).get('breaks') or [] if not b.get('kept')]


def in_break(a, b, breaks):
    """The break that covers at least half of [a, b], or None."""
    for br in breaks:
        over = min(b, br['end']) - max(a, br['start'])
        if over > 0 and over >= 0.5 * max(1e-6, b - a):
            return br
    return None


def touching(a, b, breaks, min_s=1.0):
    """Breaks that overlap [a, b] by at least min_s seconds."""
    return [br for br in breaks if min(b, br['end']) - max(a, br['start']) >= min_s]


def marker_text(br, hidden):
    lines = f'its {hidden} line(s) are left out' if hidden else 'nothing is said there'
    return (f"# ===== {NAMES[br['where']].upper()} {fmt_ts(br['start']).split('.')[0]}-"
            f"{fmt_ts(br['end']).split('.')[0]}: a still screen, nobody on cam; {lines}. No clips from here =====")


def hide_breaks(lines, breaks):
    """The transcript lines with each break's lines replaced by one marker line: a dict with 's', 'e'
    and 'marker' (the text) instead of 'text'. Lines outside breaks are the same objects as before."""
    if not breaks:
        return list(lines)
    out, hidden, shown = [], {}, set()
    todo = sorted(breaks, key=lambda b: b['start'])
    for ln in lines:
        while todo and todo[0]['end'] <= ln['s'] and todo[0]['n'] not in shown:   # a break with no words in it
            br = todo.pop(0)
            out.append({'s': br['start'], 'e': br['end'], 'marker': marker_text(br, 0), '_n': br['n']})
            shown.add(br['n'])
        br = in_break(ln['s'], ln['e'], breaks)
        if br is None:
            out.append(ln)
            continue
        hidden[br['n']] = hidden.get(br['n'], 0) + 1
        if br['n'] not in shown:
            out.append({'s': br['start'], 'e': br['end'], 'marker': '', '_n': br['n']})
            shown.add(br['n'])
            todo = [t for t in todo if t['n'] != br['n']]
    for br in todo:
        out.append({'s': br['start'], 'e': br['end'], 'marker': marker_text(br, 0), '_n': br['n']})
    by_n = {b['n']: b for b in breaks}
    for ln in out:
        if 'marker' in ln and not ln['marker']:
            ln['marker'] = marker_text(by_n[ln['_n']], hidden.get(ln['_n'], 0))
    return out


def usable_seconds(project, first, last):
    """Seconds of real video between first and last, without the break screens."""
    gone = sum(max(0.0, min(last, b['end']) - max(first, b['start'])) for b in active_breaks(project))
    return max(0.0, last - first - gone)


def describe(project):
    """One line: what kind of video this is, and why."""
    vk = project.get('video_kind') or {}
    if not vk:
        return 'not checked yet (python run.py kind <project>)'
    bits = []
    if vk.get('live'):
        bits.append('live stream')
    if vk.get('gaming'):
        bits.append('gameplay with a facecam' if vk.get('facecam') else 'gameplay')
    elif vk.get('facecam'):
        bits.append('screen recording with a facecam')
    what = ' + '.join(bits) if bits else 'a normal video'
    return f"{what} ({'; '.join(vk.get('why') or [])})" if vk.get('why') else what


def is_irregular(project):
    vk = (project or {}).get('video_kind') or {}
    return bool(vk.get('live') or vk.get('gaming') or vk.get('facecam'))


RULES = ('build clips around the streamer\'s own talk and reactions (game characters\' lines are not the '
         'streamer); quiet gameplay between lines is normal, not a dead spot (end a clip before a long '
         'silence rather than inside it); leave out stream housekeeping: hello chat, "is the audio OK", '
         'viewer counts, subscribe requests, "I\'m back", reading donations')


# ---------------------------------------------------------------- the step

def run(pdir, project, redo=False, keep=(), quiet=False):
    """Work out the kind of video and its breaks, save them in project.json, mark transcript.txt."""
    refresh_metadata(project)
    words = load_json(pdir / 'transcript' / 'words.json') or []
    video = _video_file(pdir, project)
    scanned = project.get('break_scan') or {}
    old = [(b['start'], b['end'], bool(b.get('kept'))) for b in project.get('breaks') or []]
    if video and (redo or scanned.get('v') != SCAN_V or scanned.get('video') != video.name):
        if not quiet:
            print('-> looking at the picture: break screens, facecam (about half a minute per hour of video) ...',
                  flush=True)
        try:
            breaks, facts = find_breaks(pdir, project, video, words)
            project['breaks'], project['break_scan'] = breaks, facts
            break_sheet(video, breaks, pdir / 'breaks.jpg')
        except Exception as e:                  # never fatal: the clips can still be picked from the words
            print(f'   (picture check skipped: {type(e).__name__}: {e})')
    for b in project.get('breaks') or []:
        if b['n'] in keep:
            b['kept'] = True
    live, why_live = live_info(project)
    why = [why_live] if why_live else []
    if not live and any(b['where'] == 'middle' for b in active_breaks(project)):
        live, why = True, ['a break screen in the middle']
    gaming = 'Gaming' in (project.get('categories') or [])
    if gaming:
        why.append("YouTube's category is Gaming")
    cam = bool(project.get('facecam')) or bool(settings().get('facecam'))
    if cam:
        why.append('a webcam overlay near the side')
    project['video_kind'] = {'live': live, 'gaming': gaming or cam, 'facecam': cam, 'why': why,
                             'checked_picture': bool(project.get('break_scan'))}
    save_json(pdir / 'project.json', project)
    new = [(b['start'], b['end'], bool(b.get('kept'))) for b in project.get('breaks') or []]
    tx = pdir / 'transcript' / 'transcript.txt'
    marked = tx.exists() and 'SCREEN ' in tx.read_text(encoding='utf-8')
    if tx.exists() and (new != old or bool(active_breaks(project)) != marked):
        from .fetch import render_transcript
        render_transcript(pdir, project, load_json(pdir / 'transcript' / 'sentences.json') or [])
    if not quiet:
        report(pdir, project, video)
    return project


def _video_file(pdir, project):
    from pathlib import Path
    if project.get('video') and Path(project['video']).exists():
        return Path(project['video'])
    found = [p for p in (pdir / 'source').glob('video.*') if p.stem == 'video' and p.suffix in ('.mp4', '.mkv', '.webm')]
    return found[0] if found else None


def report(pdir, project, video):
    print(f'-> video: {describe(project)}')
    if not project.get('break_scan'):
        print('   (break screens not checked yet: no video file. Run  python run.py kind '
              f'{pdir.name}  once the video is there)')
        return
    brs = project.get('breaks') or []
    if brs:
        print(f'-> break screens: {len(active_breaks(project))} left out of the transcript '
              f'(one picture of each: {(pdir / "breaks.jpg").relative_to(ROOT)})')
        for b in brs:
            span = f"{fmt_ts(b['start']).split('.')[0]}-{fmt_ts(b['end']).split('.')[0]}"
            state = '  KEPT (shown as normal video)' if b.get('kept') else ''
            print(f"   {b['n']:>3}  {span:<17} {NAMES[b['where']]}, {(b['end'] - b['start']) / 60:.1f} min{state}")
    else:
        print('-> break screens: none')
    still = (project.get('break_scan') or {}).get('still_kept')
    if still:
        print(f'   {still} still stretch(es) with someone on cam (a pause menu, a map) stay in: they are real video')
    if is_irregular(project):
        print('-> stream / gameplay rules on: ' + RULES)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('project')
    ap.add_argument('--redo', action='store_true', help='look at the video again')
    ap.add_argument('--keep', default='', help='break numbers that are real video after all, e.g. 2 or 2,3')
    a = ap.parse_args()
    pdir = project_dir(a.project)
    project = load_json(pdir / 'project.json')
    if not project:
        die(f'no project.json in {pdir}: run `python run.py fetch` first')
    keep = {int(x) for x in a.keep.split(',') if x.strip()}
    run(pdir, project, redo=a.redo, keep=keep)


if __name__ == '__main__':
    main()
