"""Step 3: cut the clips Claude picked (clips.json) into vertical 1080x1920 shorts.

    python run.py cut <project>               # all clips
    python run.py cut <project> --clips 1,3   # only some
    python run.py cut <project> --horizontal  # keep 16:9 (no reframe)
    python run.py cut <project> --layout facecam   # gameplay on top, webcam overlay below (auto-detected)
    python run.py cut <project> --layout crop      # normal framing even if a facecam is found

Downloads the video the first time (max 1080p). Snaps every range to whole words so nothing is
cut mid-word, reframes each camera shot around the speaker's face, and writes
clips/NN-title.mp4 plus clips/NN-title.json (timing, words, focus point) used by `edit`.
"""
import argparse
import math
import sys
from pathlib import Path

from . import facecam as fclib
from .common import (H, W, die, out_fps, ffmpeg, fmt_ts, is_sentence_end, load_json, norm_token, probe, project_dir, save_json,
                     settings, slugify)
from .reframe import analyse_range, crop_width, crop_x, plan_shots, shot_filter, split_box

PAD_IN, PAD_OUT = 0.12, 0.30
MIN_PIECE = 0.25          # a framing boundary never leaves a sliver shorter than this
HOWS = ('full', 'left', 'right', 'center', 'split')
JUMP_FLASH = 20.0        # a join that skips more than this many seconds of the video gets a short flash


def framing_spans(clip):
    """The clip's framing overrides as [(a, b, how)] in source seconds. `show_full` spans mean "full";
    `framing` entries are [a, b, how], how = "full" | "left" | "right" | "center" | 0.0-1.0 (the crop
    centre as a share of the frame width)."""
    spans = [(float(a), float(b), 'full') for a, b in clip.get('show_full') or []]
    for item in clip.get('framing') or []:
        a, b, how = item
        if not (how in HOWS or (isinstance(how, (int, float)) and 0 <= how <= 1)):
            die(f'clip {clip.get("id")}: framing "{how}" must be one of {", ".join(HOWS)} or a number 0-1')
        spans.append((float(a), float(b), how))
    return spans


def _framed(sh, how, src_w, src_h):
    """One shot piece re-framed the way an override asks."""
    if how == 'full':
        return {**sh, 'mode': 'fit', 'x0': 0, 'focus': [round(W / 2), round(H * 0.42)]}
    if how == 'split':                  # both people stacked: the one who talks most on top
        faces = sh.get('pair') or sorted(sh.get('faces') or [], key=lambda f: -f[2] * 1.0)[:2]
        if len(faces) < 2:
            return _framed(sh, 'full', src_w, src_h)
        left, right = sorted(faces, key=lambda f: f[0])
        # people sitting either side of the middle (a side-by-side composite, or a wide two-shot):
        # each half stays on its own side, so no strip of the other camera shows at its edge
        mid = src_w / 2 if left[0] < 0.5 < right[0] else None
        boxes = {'L': split_box(left, src_w, src_h, 0, mid) if mid else split_box(left, src_w, src_h),
                 'R': split_box(right, src_w, src_h, mid, src_w) if mid else split_box(right, src_w, src_h)}
        up, down = ('R', 'L') if sh.get('star') == 'R' else ('L', 'R')
        return {**sh, 'mode': 'split', 'x0': 0, 'top': boxes[up], 'bottom': boxes[down],
                'focus': [round(W / 2), round(H / 2)]}
    # the two people of a two-person shot (seen together), else every subject found
    subjects = [f[0] for f in sh['pair']] if sh.get('pair') else (sh.get('subjects') or ([sh['face'][0]] if sh.get('face') else []))
    if how == 'left':
        cx = min(subjects) if subjects else 0.0       # the face on the left, else the left edge
    elif how == 'right':
        cx = max(subjects) if subjects else 1.0       # the face on the right, else the right edge
    elif how == 'center':
        cx = 0.5
    else:
        cx = float(how)
    cy = sh['face'][1] if sh.get('face') else 0.42
    cw = crop_width(src_w, src_h)
    x0 = crop_x(cx, src_w, src_h)
    return {**sh, 'mode': 'crop', 'x0': x0, 'focus': [round((cx * src_w - x0) / cw * W), round(cy * H)]}


def apply_framing(shots, spans, start, dur, src_w, src_h):
    """Apply the AI's (or the user's) framing choices for parts of a clip: show the whole frame
    (blurred-background layout) where what's shown or talked about lies outside the 9:16 crop, or
    pick the left / right face or the centre where the automatic choice is wrong. `spans` are
    [(a, b, how)] in source seconds, like `ranges`; `shots` are relative to `start` and get split at
    the span edges. Vertical sources are left as they are."""
    rel = [(max(0.0, a - start), min(dur, b - start), how) for a, b, how in spans or []
           if b - start > 0 and a - start < dur]
    rel = [r for r in rel if r[1] - r[0] >= MIN_PIECE]
    if not rel:
        return shots
    out = []
    for sh in shots:
        if sh['mode'] not in ('crop', 'fit', 'split'):
            out.append(sh)
            continue
        cuts = sorted({sh['a'], sh['b'], *[x for a, b, _ in rel for x in (a, b) if sh['a'] < x < sh['b']]})
        for a, b in zip(cuts, cuts[1:]):
            if b - a < MIN_PIECE and out and out[-1]['b'] == a:     # merge a sliver into the previous piece
                out[-1] = {**out[-1], 'b': b}
                continue
            mid = (a + b) / 2
            how = next((h for fa, fb, h in reversed(rel) if fa <= mid <= fb), None)   # the last one listed wins
            piece = {**sh, 'a': a, 'b': b}
            out.append(_framed(piece, how, src_w, src_h) if how is not None else piece)
    return out


def ensure_video(pdir, project):
    if project.get('video') and Path(project['video']).exists():
        return Path(project['video'])
    if project.get('kind') == 'local':
        die(f"the original video file is gone: {project.get('video')}\n"
            'Put it back at that path, or run fetch again with its new path.')
    existing = [p for p in (pdir / 'source').glob('video.*') if p.suffix in ('.mp4', '.mkv', '.webm')]
    if existing:
        return existing[0]
    from .fetch import ytdlp
    print('-> downloading video (max 1080p, first time only) ...')
    fmt = ('bv*[height<=1080][vcodec^=avc1]+ba[ext=m4a]/bv*[height<=1080]+ba/b[height<=1080]/b')
    ytdlp(['-f', fmt, '--merge-output-format', 'mp4', '-o', str(pdir / 'source' / 'video.%(ext)s'),
           project['source']], project.get('cookies_from_browser'))
    existing = list((pdir / 'source').glob('video.*'))
    if not existing:
        die('video download produced no file')
    return existing[0]


def snap_range(s, e, words):
    """Expand/shrink [s, e] to whole words and add small natural handles."""
    inside = [i for i, w in enumerate(words) if w['e'] > s + 0.05 and w['s'] < e - 0.05]
    if not inside:
        return None
    i0, i1 = inside[0], inside[-1]
    start = words[i0]['s'] - PAD_IN
    if i0 > 0:
        start = max(start, words[i0 - 1]['e'] + 0.02)
    end = words[i1]['e'] + PAD_OUT
    if i1 + 1 < len(words):
        end = min(end, max(words[i1]['e'] + 0.08, words[i1 + 1]['s'] - 0.04))
    return max(0.0, start), end, i0, i1


def boundary_warnings(ranges, words):
    """Flag clips that start or end mid-sentence (the most common clipping mistake)."""
    warns = []
    for s, e in ranges:
        snapped = snap_range(s, e, words)
        if not snapped:
            continue
        _, _, i0, i1 = snapped
        prev, last = (words[i0 - 1] if i0 > 0 else None), words[i1]
        nxt = words[i1 + 1] if i1 + 1 < len(words) else None
        if prev and not is_sentence_end(prev['w']) and words[i0]['s'] - prev['e'] < 0.6:
            warns.append(f'starts mid-sentence, right after "...{" ".join(w["w"] for w in words[max(0, i0 - 5):i0])}"')
        if nxt and not is_sentence_end(last['w']) and nxt['s'] - last['e'] < 0.6:
            warns.append(f'ends mid-sentence: "...{" ".join(w["w"] for w in words[max(0, i1 - 5):i1 + 1])}" '
                         f'is followed by "{" ".join(w["w"] for w in words[i1 + 1:i1 + 7])}..."')
        fs = false_start(words, i0, i1)
        if fs:
            warns.append(f'may start with a false start: "{fs[0]}" is said again {fs[1]:.1f} s later; if it is '
                         f'a restart, begin at the second one ({fs[2]:.2f})')
    return warns


def false_start(words, i0, i1, max_k=3, within=3.5, gap_words=5):
    """A clip that opens with a restarted phrase ("1992 se leke, 1992 peak ho gaya"): the first 1-3
    words come again within a few seconds. Returns (words, gap, start of the repeat) or None."""
    toks = [norm_token(w['w']) for w in words[i0:i1 + 1]]
    for k in range(max_k, 0, -1):
        head = toks[:k]
        if not all(head) or (k == 1 and len(head[0]) < 3):
            continue                             # one short word ("to", "ki") repeats by chance
        for j in range(k, min(len(toks) - k + 1, 2 * k + gap_words + 1)):
            if toks[j:j + k] == head and words[i0 + j]['s'] - words[i0]['s'] <= within:
                return ' '.join(w['w'].strip() for w in words[i0:i0 + k]), \
                    words[i0 + j]['s'] - words[i0]['s'], words[i0 + j]['s'] - 0.12
    return None


def drift_warnings(clip, cands):
    """A clip picked from a candidate list (long videos read in parts) or from the critic's list
    should keep its exact ranges; say so when they differ, or when the id doesn't exist."""
    src = clip.get('from')
    if not src:
        return []
    c = cands.get(src)
    if not c:
        return [f'"from": "{src}" is not in candidates.json or the critic\'s list']
    mine, theirs = clip['ranges'], c['ranges']
    if len(mine) != len(theirs) or any(abs(a - x) > 1.0 or abs(b - y) > 1.0
                                       for (a, b), (x, y) in zip(mine, theirs)):
        return [f'ranges differ from candidate {src} {theirs}: on purpose?']
    return []


def range_shots(video, info, clip, words):
    """[(start, dur, shots)] for each range of a clip, snapped to words and analysed (no framing yet)."""
    out = []
    for s, e in clip['ranges']:
        snapped = snap_range(s, e, words)
        if not snapped:
            continue
        start, end, _, _ = snapped
        dur = end - start
        out.append((start, dur, plan_shots(analyse_range(video, start, dur, info['width'], info['height']),
                                           info['width'], info['height'])))
    return out


def _two_shot(sh):
    return sh.get('ambiguous') and sh['mode'] == 'crop' and len(sh.get('faces') or []) >= 2


def two_shot_pieces(planned):
    """(a, b) source times of the stretches where two people sit too far apart for one crop."""
    return [(start + sh['a'], start + sh['b']) for start, _, shots in planned for sh in shots if _two_shot(sh)]


def _wide_pieces(planned):
    """{(a, b): True} for two-person stretches filmed as a wide room shot (small faces)."""
    from .director import WIDE_FACE
    out = {}
    for start, _, shots in planned:
        for sh in shots:
            if _two_shot(sh):
                two = sh.get('pair') or sorted(sh['faces'], key=lambda f: -f[2])[:2]
                out[(start + sh['a'], start + sh['b'])] = max(f[2] for f in two) < WIDE_FACE
    return out


def two_person(pdir, video, plans, words):
    """The director's framing for every clip with a two-person shot: {clip id: [(a, b, how)]}.
    Voices, laughter and mouth movement are measured once per clip (cached in .work/), the video's
    speaker register (speakers.json) learns which side each voice sits on from the calm moments of
    all clips, and the director turns that into speaker / both-people framing. Clips without a
    two-person shot, or a computer without the speaker models, keep the classic framing."""
    from . import director, speakers
    todo = {cid: two_shot_pieces(planned) for cid, (clip, planned) in plans.items()}
    todo = {cid: pieces for cid, pieces in todo.items() if pieces}
    if not todo:
        return {}
    print('-> two-person shots found: working out who speaks when (voices, laughter) ...', flush=True)
    try:
        audio = speakers.load_audio(pdir / 'source' / 'audio16k.wav')
    except Exception as e:
        print(f'   ! no 16 kHz audio to analyse ({e}); classic framing for those shots')
        return {}
    import cv2
    cap = cv2.VideoCapture(str(video))
    work = pdir / '.work'
    work.mkdir(exist_ok=True)
    signals = {}
    for cid, pieces in todo.items():
        clip, planned = plans[cid]
        parts = [[round(start, 3), round(start + dur, 3)] for start, dur, _ in planned]
        cache = work / f'signals-{cid:02d}.json'
        old = load_json(cache)
        if old and old.get('parts') == parts and old.get('pieces') == [list(x) for x in pieces] \
                and old.get('v') == speakers.SIGNALS_V:
            signals[cid] = old
            continue
        vo = speakers.voices(audio, parts)
        if vo is None:
            print('   ! speaker models not available; classic framing for two-person shots')
            cap.release()
            return {}
        la = speakers.laughter(audio, parts) or []
        act = []
        for (start, _, shots) in planned:
            for sh in shots:
                if _two_shot(sh):
                    two = sorted(f[0] for f in (sh.get('pair') or sorted(sh['faces'], key=lambda f: -f[2])[:2]))
                    act += speakers.face_activity(cap, start + sh['a'], start + sh['b'], two)
        signals[cid] = {'v': speakers.SIGNALS_V, 'parts': parts, 'pieces': [list(x) for x in pieces],
                        'voices': vo, 'laughter': la,
                        'activity': act, 'prints': speakers.voice_prints(audio, vo) or {}}
        save_json(cache, signals[cid])
    cap.release()
    reg = speakers.Register(load_json(pdir / 'speakers.json'))
    who = {}
    for cid, sg in signals.items():
        secs = {}
        for a, b, v in sg['voices']:
            secs[v] = secs.get(v, 0) + b - a
        # long, clean voices first, so a short disturbed one is compared with good prints
        for v, prnt in sorted(sg['prints'].items(), key=lambda kv: -secs.get(kv[0], 0)):
            person = reg.place(prnt, secs.get(v, 0))
            if person is not None:
                who[(cid, v)] = person
    for cid, sg in signals.items():
        rows = {}
        for v, row in speakers.calm_moments(sg['activity'], sg['voices'], sg['laughter'], words):
            if (cid, v) in who:
                rows.setdefault(who[(cid, v)], []).append(row)
        for person, rs in rows.items():
            reg.vote(person, cid, rs)
    save_json(pdir / 'speakers.json', reg.to_json())
    sides = reg.sides()
    out = {}
    for cid, sg in signals.items():
        side_of = {v: sides[pi][0] for (c, v), pi in who.items() if c == cid and pi in sides}
        # in the split-screen layout the person who talks most in this clip sits on top, right above
        # the captions (and away from the app buttons at the bottom); marked on the clip's shots
        talk = {}
        for a, b, v in sg['voices']:
            if v in side_of:
                inside = sum(max(0.0, min(b, pb) - max(a, pa)) for pa, pb in sg['parts'])
                talk[side_of[v]] = talk.get(side_of[v], 0) + inside
        if talk:
            star = max(talk, key=talk.get)
            for _, _, shots in plans[cid][1]:
                for sh in shots:
                    sh['star'] = star
        wide = _wide_pieces(plans[cid][1])
        spans = []
        for a, b in todo[cid]:
            spans += director.direct((a, b), words, sg['voices'], sg['laughter'], side_of, wide=wide.get((a, b), False))
        out[cid] = spans
        kinds = {}
        for a, b, how in spans:
            kinds[how] = kinds.get(how, 0) + b - a
        print(f"   clip {cid}: " + ', '.join(f'{k} {v:.0f}s' for k, v in sorted(kinds.items())), flush=True)
    return out


def build_clip(video, info, clip, words, out_mp4, horizontal=False, fc=None, planned=None, auto=None):
    src_w, src_h = info['width'], info['height']
    planned_by_start = {round(p[0], 3): p[2] for p in planned or []}
    fps = out_fps(info.get('fps', 30))
    parts, inputs, chains, labels, masks = [], [], [], [], []
    timeline = 0.0
    clip_words, shots_out, splices, splice_frames = [], [], [], []
    # with the same frame rate in and out, the frame where each shot begins is known exactly: the
    # edit puts zoom changes and caption moves on that frame (a part starting between two source
    # frames shifts the whole part's frame grid by a fraction of a frame)
    exact = abs(info.get('fps', 0) - fps) < 0.01
    frame_base, video_end, st0 = 0, 0, info.get('start_time', 0.0)
    for k, (s, e) in enumerate(clip['ranges']):
        snapped = snap_range(s, e, words)
        if not snapped:
            print(f'   ! range {s}-{e} has no words, skipped')
            continue
        start, end, i0, i1 = snapped
        dur = end - start
        inputs += ['-ss', f'{start:.3f}', '-t', f'{dur:.3f}', '-i', str(video)]
        n = len(parts)
        if fc:
            ml = f'mask{n}' if fc['mask'] else None
            masks += [ml] if ml else []
            chains.append(fclib.filter_chain(f'{n}:v', f'v{n}', fc['cam'], fc['g'], src_w, src_h, fps, ml))
            shots = [{'a': 0, 'b': dur, 'mode': 'facecam', 'focus': [W / 2, fclib.TOP_H / 2]}]
        elif horizontal:
            chains.append(f'[{n}:v]fps={fps},setsar=1,format=yuv420p[v{n}]')
            shots = [{'a': 0, 'b': dur, 'mode': 'horizontal', 'focus': [src_w / 2, src_h * 0.4]}]
        else:
            shots = planned_by_start.get(round(start, 3)) or plan_shots(
                analyse_range(video, start, dur, src_w, src_h), src_w, src_h)
            shots = apply_framing(shots, auto or [], start, dur, src_w, src_h)           # the director
            shots = apply_framing(shots, framing_spans(clip), start, dur, src_w, src_h)   # hand-picked wins
            if len(shots) == 1:
                chains.append(shot_filter(f'{n}:v', shots[0], src_w, src_h, f'v{n}', fps))
            else:
                sub = ''.join(f'[{n}s{j}]' for j in range(len(shots)))
                chains.append(f'[{n}:v]split={len(shots)}{sub}')
                for j, sh in enumerate(shots):
                    chains.append(shot_filter(f'{n}s{j}', sh, src_w, src_h, f'v{n}_{j}', fps))
                chains.append(''.join(f'[v{n}_{j}]' for j in range(len(shots))) +
                              f'concat=n={len(shots)}:v=1:a=0[v{n}]')
        fade = 0.12 if k == len(clip['ranges']) - 1 else 0.03   # softer tail on the clip's last word
        chains.append(f'[{n}:a]aresample=48000,afade=t=in:d=0.01,'
                      f'afade=t=out:st={max(0, dur - fade):.3f}:d={fade}[a{n}]')
        labels.append(f'[v{n}][a{n}]')
        for w in words[i0:i1 + 1]:
            clip_words.append({**w, 's': round(w['s'] - start + timeline, 3),
                               'e': round(w['e'] - start + timeline, 3)})
        offset = (math.ceil((start - st0) * fps - 1e-6) / fps + st0 - start) if exact else 0.0
        for sh in shots:
            out_sh = {'t0': round(sh['a'] + timeline, 3), 't1': round(sh['b'] + timeline, 3),
                      'mode': sh['mode'], 'focus': sh['focus']}
            if exact:
                j = max(0, math.ceil((sh['a'] - offset) * fps - 1e-6))
                # a part's first frame shows right after the previous part's last one (when the
                # encoder fills a gap there, it repeats this first frame)
                out_sh['f0'] = video_end if j == 0 else frame_base + j
            shots_out.append(out_sh)
        if timeline > 0:
            splices.append(round(timeline, 3))
            splice_frames.append(video_end)
        parts.append((start, end))
        timeline += dur
        # the next part starts after this part's video or its audio, whichever ends later; the encoder
        # puts it on the nearest frame (half a frame rounds up), repeating a frame to fill a gap
        if exact:
            video_end = frame_base + math.ceil((dur - offset) * fps - 1e-6)
            frame_base = max(video_end, frame_base + math.floor(dur * fps + 0.5 + 1e-6))
        else:
            frame_base += int(round(dur * fps))
    if not parts:
        return None
    n = len(parts)
    if masks:                       # the round-cam mask image, shared by every range of the clip
        inputs += ['-loop', '1', '-t', f'{timeline + 1:.3f}', '-i', str(fc['mask'])]
        chains.append(f'[{n}:v]format=gray,split={len(masks)}' + ''.join(f'[{m}]' for m in masks))
    # joins across time (deep clips, long splices) are shown, not hidden: a short white flash
    jumps = [{'t': splices[i], 'gap': round(parts[i + 1][0] - parts[i][1], 1)} for i in range(len(splices))]
    flashes = [j['t'] for j in jumps if abs(j['gap']) > JUMP_FLASH]
    out_v = 'outv'
    if flashes:
        out_v = 'outvf'
    chains.append(''.join(labels) + f'concat=n={n}:v=1:a=1[outv][outa]')
    if flashes:
        boxes = []
        for t in flashes:                         # about 4 frames: soft, bright, soft
            boxes.append(f"drawbox=x=0:y=0:w=iw:h=ih:color=white@0.45:t=fill:enable='between(t,{t - 0.09:.3f},{t + 0.12:.3f})'")
            boxes.append(f"drawbox=x=0:y=0:w=iw:h=ih:color=white@0.55:t=fill:enable='between(t,{t - 0.04:.3f},{t + 0.06:.3f})'")
        chains.append('[outv]' + ','.join(boxes) + '[outvf]')
    tmp = out_mp4.with_suffix('.part.mp4')
    ffmpeg(*inputs, '-filter_complex', ';'.join(chains), '-map', f'[{out_v}]', '-map', '[outa]',
           '-c:v', 'libx264', '-preset', 'fast', '-crf', '17', '-pix_fmt', 'yuv420p', '-r', str(fps),
           '-c:a', 'aac', '-b:a', '192k', '-ar', '48000', '-movflags', '+faststart', tmp)
    tmp.replace(out_mp4)
    meta = {'fps': fps, 'parts': [[round(a, 3), round(b, 3)] for a, b in parts], 'duration': round(timeline, 3),
            'shots': shots_out, 'splices': splices, 'jumps': jumps, 'words': clip_words}
    if exact:
        meta['splice_frames'] = splice_frames
    if fc:
        meta.update(layout='facecam', caption_y=fc['g']['caption_y'])
    if auto:
        meta['director'] = [[a, b, how] for a, b, how in auto]
    return meta


def facecam_layout(pdir, project, video, info, layout):
    """The facecam layout to use ({'cam', 'g', 'mask'}), or None for the normal framing."""
    src_w, src_h = info['width'], info['height']
    if layout == 'crop' or src_w / src_h < 1.2:            # vertical/square sources keep the normal path
        return None
    box = settings().get('facecam')
    if box:
        cam, how = fclib.from_settings(box, src_w, src_h), 'from settings.json'
    else:
        if 'facecam' not in project:
            print('-> looking for a webcam overlay (facecam) ...', flush=True)
            project['facecam'] = fclib.detect(video, info['duration'], src_w, src_h) or False
            save_json(pdir / 'project.json', project)
        cam, how = project['facecam'], 'auto-detected'
    if not cam:
        if layout == 'facecam':
            die('no webcam overlay found. Set its box in settings.json, e.g.\n'
                '  "facecam": {"x": 0.80, "y": 0.35, "w": 0.19, "h": 0.34, "shape": "circle"}\n'
                '(fractions of the frame: left, top, width, height)')
        return None
    cam = fclib.clamp(cam, src_w, src_h)
    g = fclib.geometry(cam, src_w, src_h)
    mask = None
    if cam.get('shape') == 'circle':
        (pdir / '.work').mkdir(exist_ok=True)
        mask = fclib.mask_png(pdir / '.work' / f"cam_mask_{g['cam_w']}x{g['cam_h']}.png", g['cam_w'], g['cam_h'])
    print(f"-> layout: facecam ({how}: {cam['shape']} cam at x={cam['x']} y={cam['y']} {cam['w']}x{cam['h']}). "
          f"Gameplay on top, cam below, captions between. Normal framing: --layout crop")
    return {'cam': cam, 'g': g, 'mask': mask}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('project')
    ap.add_argument('--clips', default=None, help='comma list of clip ids, e.g. 1,3')
    ap.add_argument('--horizontal', action='store_true', help='keep the original 16:9 framing')
    ap.add_argument('--check', action='store_true', help='only check clip boundaries, cut nothing')
    ap.add_argument('--layout', default=None, choices=['auto', 'facecam', 'crop'],
                    help='auto (default, from settings.json): facecam layout when a webcam overlay is found')
    a = ap.parse_args()

    pdir = project_dir(a.project)
    project = load_json(pdir / 'project.json')
    picks = load_json(pdir / 'clips.json')
    if not picks or not picks.get('clips'):
        die(f'no clips.json in {pdir}. Claude writes it after reading transcript/transcript.txt')
    words = load_json(pdir / 'transcript' / 'words.json')
    want = {int(x) for x in a.clips.split(',')} if a.clips else None

    flagged = 0
    cands = {c['id']: c for c in load_json(pdir / 'candidates.json', []) or []}
    for c in (load_json(pdir / 'critic' / 'plan.json') or {}).get('clips', []):
        cands.setdefault(c['id'], c)             # a short video's shortlist ("s3") judged by the critic
    for c in load_json(pdir / 'deep' / 'candidates.json', []) or []:
        cands.setdefault(c['id'], c)             # a deep clip ("d1-c1") from the deep pass
    taken = []                                   # (clip id, start, end) of every range so far
    for i, clip in enumerate(picks['clips'], 1):
        cid = int(clip.get('id', i))
        if want and cid not in want:
            continue
        snapped = [snap_range(s, e, words) for s, e in clip['ranges']]
        total = sum(x[1] - x[0] for x in snapped if x)
        msgs = boundary_warnings(clip['ranges'], words)
        if total and not 15 <= total <= 90:
            msgs.append(f'length {total:.0f}s is outside 15-90 s')
        msgs += drift_warnings(clip, cands)
        for r0, r1 in clip['ranges']:
            for other, x, y in taken:
                if r0 < y - 1.0 and x < r1 - 1.0:
                    msgs.append(f'overlaps clip {other} ({x:.1f}-{y:.1f}): the same words twice')
        taken += [(cid, r0, r1) for r0, r1 in clip['ranges']]
        for m in msgs:
            print(f'   WARNING clip {cid} "{clip.get("title")}": {m}')
        flagged += bool(msgs)
    if a.check:
        print('check: all clip boundaries look clean' if not flagged else
              f'check: {flagged} clip(s) need a look. Fix the ranges with `run.py find`, '
              'unless the cut is intentional')
        return

    video = ensure_video(pdir, project)
    info = probe(video)
    print(f'-> source: {info["width"]}x{info["height"]} {info["fps"]:.2f}fps, {fmt_ts(info["duration"])}')
    out_dir = pdir / 'clips'
    out_dir.mkdir(exist_ok=True)
    layout = a.layout or settings().get('layout', 'auto')
    fc = None if a.horizontal else facecam_layout(pdir, project, video, info, layout)

    plans = {}
    if not a.horizontal and not fc:
        for i, clip in enumerate(picks['clips'], 1):
            cid = int(clip.get('id', i))
            if not want or cid in want:
                plans[cid] = (clip, range_shots(video, info, clip, words))
    auto = two_person(pdir, video, plans, words) if plans else {}

    done = []
    for i, clip in enumerate(picks['clips'], 1):
        cid = int(clip.get('id', i))
        if want and cid not in want:
            continue
        name = f'{cid:02d}-{slugify(clip.get("title", "clip"), 40)}'
        out = out_dir / f'{name}.mp4'
        print(f'-> clip {cid}: "{clip.get("title")}"  ranges={clip["ranges"]}')
        meta = build_clip(video, info, clip, words, out, a.horizontal, fc,
                          plans.get(cid, (None, None))[1], auto.get(cid))
        if not meta:
            print('   ! skipped (no words in its ranges)')
            continue
        meta.update({'id': cid, 'name': name, 'title': clip.get('title'), 'hook': clip.get('hook'),
                     'emphasis': clip.get('emphasis', []), 'file': out.name})
        save_json(out_dir / f'{name}.json', meta)
        modes = sorted({s['mode'] for s in meta['shots']})
        print(f'   ok {out.name}  {meta["duration"]:.1f}s, {len(meta["shots"])} shot(s), {"/".join(modes)}')
        done.append(out)

    print(f'\nDONE: {len(done)} clip(s) in {out_dir}')
    print('next (optional simple edit):  python run.py edit ' + pdir.name)


if __name__ == '__main__':
    main()
