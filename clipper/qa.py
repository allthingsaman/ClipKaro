"""The automatic quality check: every finished clip, checked by code before anyone watches it.

    python run.py qa <project>              # every edited clip
    python run.py qa <project> --clips 2,5  # only these

Not the clip's content (the critic judges that), but the craft of the file, like an editor watching the
export before handing it over:
  FAIL (fix it before showing the user):
    * Hindi letters left in Roman Hinglish captions (a word missing from romanize.json);
    * a caption wider than the safe zone, or outside it (under the apps' buttons or top bar);
    * a cut inside a word (the clip starts or ends in the middle of one);
    * the sound far too loud or quiet (3 dB or more off -14 LUFS), or peaks above -1 dBTP;
    * a black stretch (0.3 s or more);
    * the edited clip is older than its cut (cut again, then not edited: stale);
  CHECK (look at it):
    * a caption over a face; a frozen picture for 2 s or more; a flash of another shot in the last
      frames; the loudness 1.5 dB off; a length outside 15-90 s; a quarter or more of the words without
      captions (unclear speech); no posting text in clips.json.
A cut counts as inside a word when it is 0.12 s or more into it (Whisper's word times are +-0.1 s).
Writes output/<project>/qa.txt. Exit status 1 when anything FAILs.
"""
import argparse
import re
import subprocess
import sys

import numpy as np

from .common import H, W, die, fmt_ts, has_devanagari, load_json, project_dir, settings
from . import layout, plan as planlib

LUFS_TARGET, LUFS_CHECK, LUFS_FAIL, MAX_TP = -14.0, 1.5, 3.0, -1.0
INSIDE = 0.12             # a cut this far inside a word (both ends) is a cut word; Whisper's times are +-0.1 s


def media_stats(path):
    """Loudness, true peak, black and frozen stretches, duration: one ffmpeg pass."""
    r = subprocess.run(['ffmpeg', '-hide_banner', '-nostats', '-i', str(path),
                        '-vf', 'blackdetect=d=0.3:pix_th=0.10,freezedetect=n=0.002:d=2',
                        '-af', 'ebur128=peak=true', '-f', 'null', '-'], capture_output=True, text=True)
    err = r.stderr
    lufs = re.findall(r'I:\s+(-?[\d.]+) LUFS', err)
    peak = re.findall(r'Peak:\s+(-?[\d.]+|-inf) dBFS', err)
    black = [(float(a), float(b)) for a, b in re.findall(r'black_start:([\d.]+) black_end:([\d.]+)', err)]
    frozen = [float(x) for x in re.findall(r'freeze_duration: ([\d.]+)', err)]
    dur = re.findall(r'Duration: (\d+):(\d+):([\d.]+)', err)
    seconds = (int(dur[0][0]) * 3600 + int(dur[0][1]) * 60 + float(dur[0][2])) if dur else None
    return {'lufs': float(lufs[-1]) if lufs else None,
            'peak': float(peak[-1]) if peak and peak[-1] != '-inf' else None,
            'black': black, 'frozen': frozen, 'duration': seconds}


def end_flash(path, duration):
    """True when one of the last 3 frames is a different shot from the frames just before it."""
    r = subprocess.run(['ffmpeg', '-v', 'error', '-sseof', '-0.6', '-i', str(path), '-vf',
                        'scale=64:114,format=gray', '-f', 'rawvideo', '-'], capture_output=True)
    fr = np.frombuffer(r.stdout, np.uint8)
    n = len(fr) // (64 * 114)
    if n < 6:
        return False
    fr = fr[:n * 64 * 114].reshape(n, 114, 64).astype(np.float32)
    d = np.abs(np.diff(fr, axis=0)).mean(axis=(1, 2))
    before = d[:-3]
    return bool(d[-3:].max() > max(25.0, 4 * (np.median(before) if len(before) else 0)))


def caption_faces(clip_mp4, meta, plan):
    """Caption groups that cover a face (face boxes as the edit shows them, no margins)."""
    faces = layout.face_boxes(clip_mp4, meta.get('shots', []))
    keys = plan.get('camera_keys') or []
    fps = plan.get('fps', 30)
    cam = [planlib.cam_at(keys, f) for f in range(int(plan['duration'] * fps) + 1)] if keys else None
    st = plan['caption_style']
    hits = []
    for g in plan['captions']:
        i = next((k for k, sh in enumerate(meta.get('shots', [])) if sh['t0'] <= g['start'] < sh['t1']), None)
        if i is None:
            continue
        boxes = layout.zoomed(faces.get(i, []), cam, fps, g['start'], g['end'])
        half = planlib.caption_width(' '.join(w['text'] for w in g['words']), st) * g.get('scale', 1) / 2
        if layout.covers((g.get('y', st['y']), layout.CAP_H * 0.8), boxes, half_w=half):
            hits.append(g['start'])
    return hits


def check_clip(pdir, project, cfg, words, picked, meta, plan, edited, clip_mp4):
    fail, check = [], []
    st = plan['caption_style']
    from .romanize import wants_roman
    caps = plan.get('captions', [])
    if wants_roman(project, cfg):
        hindi = [(g['start'], w['text']) for g in caps for w in g['words'] if has_devanagari(w['text'])]
        if hindi:
            fail.append(f"Hindi letters in Roman captions: {', '.join(f'{t!r} at {s:.1f} s' for s, t in hindi[:4])}"
                        f" -> fill romanize.json (python run.py romanize {pdir.name}), then edit again")
    if plan.get('safe', False):
        for g in caps:
            wid = planlib.caption_width(' '.join(w['text'] for w in g['words']), st) * g.get('scale', 1)
            y = g.get('y', st['y'])
            if wid > layout.SAFE_W + 6:
                fail.append(f"caption at {g['start']:.1f} s is {wid:.0f} px wide (the safe zone is {layout.SAFE_W})")
                break
            if y - layout.CAP_H / 2 < layout.SAFE_TOP - 6 or y + layout.CAP_H / 2 > layout.SAFE_BOTTOM + 6:
                fail.append(f"caption at {g['start']:.1f} s sits outside the safe zone (y {y})")
                break
    for k, (a, b) in enumerate(meta.get('parts', [])):
        for t, side in ((a, 'starts'), (b, 'ends')):
            w = next((w for w in words if w['s'] + INSIDE < t < w['e'] - INSIDE and not w.get('unsure')), None)
            if w:
                fail.append(f"piece {k + 1} {side} inside the word \"{w['w']}\" ({fmt_ts(w['s'])}): cut again "
                            f"(python run.py cut {pdir.name} --clips {meta['id']})")
    ms = media_stats(edited)
    if ms['lufs'] is not None and abs(ms['lufs'] - LUFS_TARGET) > LUFS_FAIL:
        fail.append(f"loudness {ms['lufs']:.1f} LUFS (should be about {LUFS_TARGET:.0f}): edit again")
    elif ms['lufs'] is not None and abs(ms['lufs'] - LUFS_TARGET) > LUFS_CHECK:
        check.append(f"loudness {ms['lufs']:.1f} LUFS, a little off {LUFS_TARGET:.0f} (much game sound or music?)")
    if ms['peak'] is not None and ms['peak'] > MAX_TP:
        fail.append(f"peaks at {ms['peak']:.1f} dBFS (the limit is {MAX_TP:.0f}): edit again")
    if ms['black']:
        a, b = ms['black'][0]
        fail.append(f"black picture {a:.1f}-{b:.1f} s")
    if ms['duration'] and not 15 <= ms['duration'] <= 90:
        check.append(f"{ms['duration']:.0f} s long (the usual limits are 15-90 s): on purpose?")
    if edited.stat().st_mtime < clip_mp4.stat().st_mtime - 1:
        fail.append(f"the edited clip is older than its cut: python run.py edit {pdir.name} --clips {meta['id']}")
    if ms['frozen']:
        check.append(f"the picture stands still for {max(ms['frozen']):.1f} s (a pause in the video, or a slide?)")
    if ms['duration'] and end_flash(edited, ms['duration']):
        check.append('a flash of another shot in the last frames: end the clip a little earlier')
    covered = caption_faces(clip_mp4, meta, plan) if plan.get('safe', False) else []
    if covered:
        check.append(f"captions cover a face at {', '.join(f'{t:.1f}' for t in covered[:4])} s")
    unsure = [w for w in meta.get('words', []) if w.get('unsure')]
    if meta.get('words') and len(unsure) >= 0.25 * len(meta['words']):
        check.append(f"{len(unsure)} of {len(meta['words'])} words without captions (unclear speech: game voices, "
                     f"music): fine if the game shows its own subtitles")
    if not picked.get('caption') or not (picked.get('post') or {}).get('youtube', {}).get('title'):
        check.append('no posting text in clips.json (caption / post.youtube.title)')
    return fail, check, ms


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('project')
    ap.add_argument('--clips', default=None, help='only these clip numbers, e.g. 2,5')
    a = ap.parse_args()
    pdir = project_dir(a.project)
    project = load_json(pdir / 'project.json', {}) or {}
    cfg = settings()
    words = load_json(pdir / 'transcript' / 'words.json') or []
    picks = {int(c.get('id', k + 1)): c for k, c in enumerate((load_json(pdir / 'clips.json', {}) or {}).get('clips', []))}
    want = {int(x) for x in a.clips.split(',')} if a.clips else None
    metas = sorted((pdir / 'clips').glob('*.json'))
    if not metas:
        die(f'no cut clips in {pdir.name}: run cut and edit first')
    rows, n_fail, n_check, n = [], 0, 0, 0
    for mp in metas:
        meta = load_json(mp)
        if want and meta['id'] not in want:
            continue
        edited = pdir / 'edited' / meta['file']
        plan = load_json(pdir / '.work' / f"{meta['name']}.plan.json")
        if not edited.exists() or not plan:
            rows.append(f"clip {meta['id']:>2}  NOT EDITED  {meta['file']}")
            continue
        n += 1
        fail, check, ms = check_clip(pdir, project, cfg, words, picks.get(meta['id'], {}), meta, plan, edited,
                                     pdir / 'clips' / meta['file'])
        state = 'FAIL' if fail else 'CHECK' if check else 'ok'
        n_fail += bool(fail)
        n_check += bool(check) and not fail
        loud = f"{ms['lufs']:.1f} LUFS" if ms['lufs'] is not None else '?'
        rows.append(f"clip {meta['id']:>2}  {state:<5}  {ms['duration'] or 0:4.0f} s  {loud}  {meta['file']}")
        rows += [f'          FAIL  {x}' for x in fail] + [f'          check {x}' for x in check]
    head = f"# Quality check of {pdir.name}: {n} clip(s), {n_fail} to fix, {n_check} to look at"
    (pdir / 'qa.txt').write_text('\n'.join([head, ''] + rows) + '\n', encoding='utf-8')
    print(head.lstrip('# '))
    for r in rows:
        print('   ' + r)
    print(f"-> {(pdir / 'qa.txt')}")
    sys.exit(1 if n_fail else 0)


if __name__ == '__main__':
    main()
