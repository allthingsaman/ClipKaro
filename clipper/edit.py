"""Step 4 (optional): a simple, clean edit of each cut clip: smooth zooms, word-by-word captions
in the video's brand colours, and 1-2 subtle whooshes. Loudness normalised for phones.

    python run.py edit <project>                         # every clip, python engine
    python run.py edit <project> --clips 2               # one clip
    python run.py edit <project> --engine remotion       # same edit drawn by Remotion (python install.py --remotion)
    options: --no-zoom  --no-captions  --sfx auto|light|none  --no-upper  --caption-y 1270  --size 96

Writes edited/NN-title.mp4 (+ .srt captions file for platforms that want one).
"""
import argparse
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

import cv2
import numpy as np

from . import brand as brandlib
from . import emoji as emojilib
from . import music as musiclib
from . import layout as layoutlib
from . import plan as planlib
from . import romanize
from .common import ASSETS, H, ROOT, W, die, ffmpeg, has_devanagari, load_json, need, project_dir, save_json, settings
from .sfx import path_of

FONTS = ASSETS / 'fonts'
JUMP_SIZE, JUMP_Y = 50, 250       # the optional "27 MIN LATER" label: size (CSS px) and centre line


# ---------------- shared: audio mix ----------------

def mix_audio(clip_mp4, cues, out_wav, duration, music=None):
    """Voice + SFX cues (+ a music bed, ducked under the voice) -> loudness-normalised stereo wav
    (-14 LUFS, -1.5 dBTP)."""
    inputs = ['-i', str(clip_mp4)]
    chains = ['[0:a]aresample=48000,aformat=channel_layouts=stereo,'
              'highpass=f=70,acompressor=threshold=-20dB:ratio=2.5:attack=8:release=120:makeup=2'
              + (',asplit=2[v][vkey]' if music else '[v]')]
    labels = ['[v]']
    if music:                                # the bed: from the track's start, looped if short
        k = len(cues) + 1
        fade_out = max(0.0, duration - 1.2)
        chains.append(f"[{k}:a]atrim=0:{duration:.3f},asetpts=PTS-STARTPTS,aresample=48000,"
                      f"aformat=channel_layouts=stereo,loudnorm=I={musiclib.BED_LUFS}:TP=-6:LRA=11,"
                      f"aresample=48000[mraw];[mraw][vkey]sidechaincompress=threshold=0.03:ratio=4:attack=40:"
                      f"release=400[mduck];[mduck]afade=t=in:d=0.8,afade=t=out:st={fade_out:.3f}:d=1.2[mus]")
        labels.append('[mus]')
    for k, c in enumerate(cues, 1):
        inputs += ['-i', str(path_of(c))]
        delay = int(c['at'] * 1000)
        vol = c['gain_db'] + c.get('norm_db', 0)
        chains.append(f"[{k}:a]atrim=start={c['offset']:.3f}:duration={c['length']:.3f},asetpts=PTS-STARTPTS,"
                      f"aresample=48000,aformat=channel_layouts=stereo,volume={vol:.2f}dB,"
                      f"afade=t=out:st={max(0, c['length'] - 0.06):.3f}:d=0.06,adelay={delay}|{delay}[s{k}]")
        labels.append(f'[s{k}]')
    if music:
        inputs += ['-stream_loop', '-1', '-i', str(music)]
    chains.append(''.join(labels) + f'amix=inputs={len(labels)}:normalize=0:duration=first,'
                  f'loudnorm=I=-14:TP=-1.5:LRA=11,aresample=48000,atrim=0:{duration:.3f}[out]')
    ffmpeg(*inputs, '-filter_complex', ';'.join(chains), '-map', '[out]', '-c:a', 'pcm_s16le', out_wav)


def write_srt(plan, path):
    def ts(t):
        ms = int(round(t * 1000))
        h, ms = divmod(ms, 3600000)
        m, ms = divmod(ms, 60000)
        s, ms = divmod(ms, 1000)
        return f'{h:02d}:{m:02d}:{s:02d},{ms:03d}'
    lines = []
    cues = []
    for g in plan['captions']:
        if g.get('cont') and cues:          # the same caption, continued after a layout switch
            cues[-1][1] = g['end']
        else:
            cues.append([g['start'], g['end'], ' '.join(w['text'] for w in g['words'])])
    for i, (a, b, text) in enumerate(cues, 1):
        lines += [str(i), f"{ts(a)} --> {ts(b)}", text, '']
    Path(path).write_text('\n'.join(lines), encoding='utf-8')


# ---------------- python engine ----------------

def ass_color(hex_rgb, alpha=0):
    r, g, b = brandlib.hex_to_rgb(hex_rgb)
    return f'&H{alpha:02X}{b:02X}{g:02X}{r:02X}'


def css_to_ass_size(px, font_file):
    """libass sizes text by (ascent + descent), CSS by the em box. Convert so both engines match."""
    import struct
    try:
        data = (FONTS / font_file).read_bytes()
        n = struct.unpack('>H', data[4:6])[0]
        tables = {data[12 + 16 * i:16 + 16 * i]: struct.unpack('>I', data[20 + 16 * i:24 + 16 * i])[0]
                  for i in range(n)}
        upm = struct.unpack('>H', data[tables[b'head'] + 18:tables[b'head'] + 20])[0]
        os2 = tables[b'OS/2']
        asc, desc = struct.unpack('>HH', data[os2 + 74:os2 + 78])   # usWinAscent / usWinDescent
        return round(px * (asc + desc) / upm)
    except Exception:
        return round(px * 1.2)


def mood_marks(marks, meta):
    """clips.json "sfx": [[source seconds, mood], ...] -> [(clip seconds, mood)], through the cut's
    pieces (jump cuts included). A mark outside the clip is skipped with a note."""
    out = []
    for m in marks or []:
        if not (isinstance(m, (list, tuple)) and len(m) == 2):
            continue
        t, mood = float(m[0]), str(m[1]).lower()
        at = 0.0
        for a, b in meta.get('parts', []):
            if a - 0.05 <= t <= b + 0.05:
                out.append((round(at + min(max(t, a), b) - a, 3), mood))
                break
            at += b - a
        else:
            print(f'   ! sfx "{mood}" at {t} s is not inside this clip (source seconds, as in the transcript)')
    return out


def cap_style(st, white, accent, outline):
    """The ASS caption style of the look: an outline (and a soft shadow), or a dark box (box look).
    Karaoke fills from white (SecondaryColour) to the accent (PrimaryColour) as each word is said."""
    primary, secondary = (accent, white) if st.get('karaoke') else (white, white)
    if st.get('box'):
        return (f"Style: Cap,{st['font']},{st['size']},{primary},{secondary},&H50000000,&H50000000,0,0,0,0,100,100,"
                f"{st.get('spacing', 1)},0,3,{st['outline']},0,5,60,60,0,1")
    return (f"Style: Cap,{st['font']},{st['size']},{primary},{secondary},{outline},&H64000000,0,0,0,0,100,100,"
            f"{st.get('spacing', 1)},0,1,{st['outline']},{st.get('shadow', 3)},5,60,60,0,1")


def hook_style(plan):
    """The ASS style of the hook title: the caption font on a box in the accent colour, text in black
    or white, whichever reads better on it."""
    hk = plan.get('hook')
    if not hk:
        return ''
    accent = plan['brand']['accent'].lstrip('#')
    r, g, b = (int(accent[i:i + 2], 16) for i in (0, 2, 4))
    light = 0.2126 * r + 0.7152 * g + 0.0722 * b > 150
    text = '&H00000000' if light else '&H00FFFFFF'
    box = ass_color('#' + accent)
    return (f"Style: Hook,{hk['font']},{css_to_ass_size(hk['size'], hk['font_file'])},{text},{text},{box},{box},"
            f"0,0,0,0,100,100,1,0,3,18,0,5,60,60,0,1")


def write_ass(plan, path):
    st, br = dict(plan['caption_style']), plan['brand']
    st['size'] = css_to_ass_size(st['size'], st['font_file'])
    white, accent, outline = ass_color(br['text']), ass_color(br['accent']), ass_color(br['outline'])
    head = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {W}
PlayResY: {H}
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
{cap_style(st, white, accent, outline)}
Style: Jump,{st['font']},{css_to_ass_size(JUMP_SIZE, st['font_file'])},&H00FFFFFF,&H00FFFFFF,&H5A000000,&H5A000000,0,0,0,0,100,100,1,0,3,14,0,5,60,60,0,1
{hook_style(plan)}

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

    def t(sec):
        cs = int(round(sec * 100))
        h, cs = divmod(cs, 360000)
        m, cs = divmod(cs, 6000)
        s, cs = divmod(cs, 100)
        return f'{h}:{m:02d}:{s:02d}.{cs:02d}'
    events = []
    fps = plan['fps']
    caps = plan['captions']
    # each caption shows one frame early, except where that frame is in the other layout: the
    # second part of a caption cut at a layout switch ('cont'), or one starting right at it ('nolead')
    starts = [g['start'] - (0 if g.get('cont') or g.get('nolead') else 1 / fps) for g in caps]
    for k, g in enumerate(caps):
        g0 = starts[k]
        # end where the next group begins, so two groups never share a frame (was a 1-frame overlap)
        g_end = min(g['end'], starts[k + 1]) if k + 1 < len(caps) else g['end']
        parts = []
        if st.get('karaoke'):               # the whole line at once, filling with the accent as it is said
            lead = max(0, int(round((g['words'][0]['s'] - g0) * 100)))
            parts.append(f'{{\\k{lead}}}' if lead else '')
            for i, w in enumerate(g['words']):
                nxt = g['words'][i + 1]['s'] if i + 1 < len(g['words']) else w['e']
                parts.append(f"{{\\kf{max(1, int(round((nxt - w['s']) * 100)))}}}" +
                             w['text'].replace('{', '(').replace('}', ')'))
            fs = f"\\fs{round(st['size'] * g['scale'])}" if g.get('scale') else ''
            events.append(f"Dialogue: 0,{t(g0)},{t(g_end)},Cap,,0,0,0,,"
                          f"{{\\pos({W // 2},{g.get('y', st['y'])}){fs}}}" + ''.join(
                              x if k < 2 else ' ' + x for k, x in enumerate(parts)))
            continue
        if not st.get('pop', True):         # minimal: the group fades in, key words in the accent colour
            words = [(f'{{\\1c{accent}}}' if w.get('emph') else '') + w['text'].replace('{', '(').replace('}', ')') +
                     (f'{{\\1c{white}}}' if w.get('emph') else '') for w in g['words']]
            fs = f"\\fs{round(st['size'] * g['scale'])}" if g.get('scale') else ''
            events.append(f"Dialogue: 0,{t(g0)},{t(g_end)},Cap,,0,0,0,,"
                          f"{{\\pos({W // 2},{g.get('y', st['y'])}){fs}\\fad(80,0)}}" + ' '.join(words))
            continue
        for i, w in enumerate(g['words']):
            a = max(0, int((w['s'] - 1 / fps - g0) * 1000))
            nxt = g['words'][i + 1]['s'] if i + 1 < len(g['words']) else None
            b = int(((nxt if nxt is not None else g['end'] + 1) - g0) * 1000)
            col = accent if w.get('emph') else white
            if w['s'] < g['start'] - 0.01:
                # already spoken when this caption part began (a caption continued after a layout
                # switch): shown at once, no pop
                tag = f'{{\\1c{accent}\\t({b},{b + 1},\\1c{col})}}' if b > 0 else f'{{\\1c{col}}}'
            elif a == 0:
                # the first word: visible from the first frame (hiding it for one frame made every
                # caption blink), then the pop
                tag = (f'{{\\fscy60\\1c{accent}\\t(0,110,0.6,\\fscy100)'
                       f'\\t({b},{b + 1},\\1c{col})}}')
            else:
                # hidden until spoken, then pops up (vertical squash -> full + fade), active word in accent colour
                tag = (f'{{\\alpha&HFF&\\fscy60\\1c{accent}'
                       f'\\t({a},{a + 1},\\alpha&H00&)\\t({a},{a + 110},0.6,\\fscy100)'
                       f'\\t({b},{b + 1},\\1c{col})}}')
            parts.append(tag + w['text'].replace('{', '(').replace('}', ')'))
        fs = f"\\fs{round(st['size'] * g['scale'])}" if g.get('scale') else ''   # shrunk to fit the frame
        tilt = f"\\frz{st['tilt']}" if st.get('tilt') else ''
        text = f"{{\\pos({W // 2},{g.get('y', st['y'])}){fs}{tilt}}}" + ' '.join(parts)
        events.append(f"Dialogue: 0,{t(g0)},{t(g_end)},Cap,,0,0,0,,{text}")
    hk = plan.get('hook')
    if hk:                                   # the hook title: a box in the upper part, pops in, fades out
        text = '\\N'.join(line.replace('{', '(').replace('}', ')') for line in hk['lines'])
        events.append(f"Dialogue: 2,{t(hk['start'])},{t(hk['end'])},Hook,,0,0,0,,"
                      f"{{\\pos({W // 2},{hk['y']})\\fad(90,260)\\fscx86\\fscy86\\t(0,170,0.5,\\fscx100\\fscy100)}}{text}")
    for lb in plan.get('labels', []):        # "27 MIN LATER" at a jump across time (optional)
        events.append(f"Dialogue: 1,{t(lb['start'])},{t(lb['end'])},Jump,,0,0,0,,"
                      f"{{\\pos({W // 2},{JUMP_Y})\\fad(120,250)}}{lb['text']}")
    Path(path).write_text(head + '\n'.join(events) + '\n', encoding='utf-8')


# The NVIDIA encoder, when it works, is 3x faster than libx264 at the same picture quality (measured on a
# 42 s clip: SSIM 0.9966 for libx264 -crf 18, 0.9967 at -cq 22 and 0.9960 at -cq 24, with adaptive
# quantisation and B-frames); files are about 1.3x bigger at -cq 23. Without one, libx264 as before.
X264 = ['-c:v', 'libx264', '-preset', 'medium', '-crf', '18']
NVENC = ['-c:v', 'h264_nvenc', '-preset', 'p6', '-tune', 'hq', '-rc', 'vbr', '-cq', '23', '-b:v', '0',
         '-spatial-aq', '1', '-temporal-aq', '1', '-bf', '3', '-b_ref_mode', 'middle']
_ENCODER = {}


def video_encoder(cfg):
    """(ffmpeg arguments, encoder name): settings.json "encoder": auto (NVIDIA if a test encode works) |
    nvenc | x264."""
    want = str(os.environ.get('CLIPKARO_ENCODER') or cfg.get('encoder', 'auto')).lower()
    if want not in _ENCODER:
        ok = False
        if want in ('auto', 'nvenc'):
            r = subprocess.run(['ffmpeg', '-v', 'error', '-f', 'lavfi', '-i', 'color=c=black:s=320x240:r=30:d=0.2',
                                '-c:v', 'h264_nvenc', '-f', 'null', '-'], capture_output=True)
            ok = r.returncode == 0
        _ENCODER[want] = (NVENC, 'h264_nvenc') if ok else (X264, 'libx264')
    return _ENCODER[want]


def load_emojis(marks):
    """The emoji pictures (BGRA, full size) for the frame loop."""
    out = []
    for e in marks:
        img = cv2.imread(e['png'], cv2.IMREAD_UNCHANGED)
        if img is not None and img.shape[2] == 4:
            out.append(dict(e, img=cv2.resize(img, (e['size'], e['size']), interpolation=cv2.INTER_AREA)))
    return out


def draw_emojis(frame, emojis, t):
    """Pops each emoji in (0.6 -> 1.0 in 0.15 s) when its word is said, fades it out at the end."""
    out = None
    for e in emojis:
        if not e['t0'] <= t < e['t1']:
            continue
        k = min(1.0, (t - e['t0']) / 0.15)
        scale = 0.6 + 0.4 * (1 - (1 - k) ** 3)
        fade = min(1.0, (e['t1'] - t) / 0.18)
        n = max(8, int(e['size'] * scale))
        img = cv2.resize(e['img'], (n, n), interpolation=cv2.INTER_AREA)
        x0, y0 = int(e['x'] - n / 2), int(e['y'] - n / 2)
        x1, y1 = min(W, x0 + n), min(H, y0 + n)
        if x0 < 0 or y0 < 0 or x1 <= x0 or y1 <= y0:
            continue
        if out is None:
            out = frame.copy()
        sub = img[:y1 - y0, :x1 - x0]
        alpha = (sub[:, :, 3:4].astype(np.float32) / 255.0) * fade
        roi = out[y0:y1, x0:x1].astype(np.float32)
        out[y0:y1, x0:x1] = (roi * (1 - alpha) + sub[:, :, :3].astype(np.float32) * alpha).astype(np.uint8)
    return frame if out is None else out


def render_python(clip_mp4, plan, audio_wav, out_mp4, workdir):
    need('ffmpeg')
    ass = workdir / f'{out_mp4.stem}.ass'
    write_ass(plan, ass)
    fonts_rel = os.path.relpath(FONTS, workdir).replace('\\', '/')
    vf = f"ass={ass.name}:fontsdir={fonts_rel}" if plan['captions'] or plan.get('labels') else 'null'
    dec = subprocess.Popen(['ffmpeg', '-v', 'error', '-i', str(clip_mp4), '-f', 'rawvideo', '-pix_fmt', 'bgr24',
                            '-r', str(plan['fps']), '-s', f'{W}x{H}', '-'], stdout=subprocess.PIPE)
    tmp = out_mp4.with_suffix('.part.mp4')
    enc = subprocess.Popen(['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'bgr24', '-s', f'{W}x{H}',
                            '-r', str(plan['fps']), '-i', '-', '-i', str(audio_wav), '-vf', vf,
                            '-map', '0:v', '-map', '1:a', *(plan.get('encoder') or video_encoder(settings())[0]),
                            '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-b:a', '192k', '-shortest',
                            '-movflags', '+faststart', str(tmp.resolve())],
                           stdin=subprocess.PIPE, cwd=workdir)
    cam = plan['cam']
    size = W * H * 3
    emojis = load_emojis(plan.get('emoji', []))
    prev = None
    f = 0
    # frames where the camera cuts (and their neighbours): never blend two different shots
    cuts = {k['f'] + d for k in plan.get('camera_keys', []) if k.get('ease') == 'cut' and k['f'] > 0 for d in (-1, 0, 1)}
    while True:
        buf = dec.stdout.read(size)
        if len(buf) < size:
            break
        frame = np.frombuffer(buf, np.uint8).reshape(H, W, 3)
        s, x, y = cam[min(f, len(cam) - 1)]
        if abs(s - 1) > 1e-4:
            M = np.float32([[s, 0, x - x * s], [0, s, y - y * s]])
            out = cv2.warpAffine(frame, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
        else:
            out = frame
        # light motion blur only while the camera is moving fast (snap zooms)
        if prev is not None and f > 0 and f not in cuts:
            vel = abs(s - cam[min(f - 1, len(cam) - 1)][0])
            if 0.012 < vel < 0.08:
                out = cv2.addWeighted(out, 0.7, prev, 0.3, 0)
        prev = out
        if emojis:
            out = draw_emojis(out, emojis, f / plan['fps'])
        enc.stdin.write(out.tobytes())
        f += 1
    enc.stdin.close()
    dec.wait()
    if enc.wait() != 0:
        die('python engine: ffmpeg encode failed')
    tmp.replace(out_mp4)


# ---------------- remotion engine ----------------

REMOTION = ROOT / 'remotion'


def render_remotion(clip_mp4, plan, audio_wav, out_mp4, workdir):
    npx = shutil.which('npx')
    if not npx:
        die('Node.js is needed for --engine remotion. Install Node, then: python install.py --remotion')
    if not (REMOTION / 'node_modules').exists():
        die('Remotion is not installed yet. Run: python install.py --remotion')
    pub = REMOTION / 'public'
    pub.mkdir(exist_ok=True)
    tag = f'clip-{os.getpid()}-{out_mp4.stem[:20]}.mp4'
    shutil.copy2(clip_mp4, pub / tag)
    font_pub = pub / 'fonts'
    font_pub.mkdir(exist_ok=True)
    for ff in {plan['caption_style']['font_file'], (plan.get('hook') or {}).get('font_file')} - {None}:
        if not (font_pub / ff).exists():
            shutil.copy2(FONTS / ff, font_pub / ff)
    props = dict(plan, src=tag)
    props_file = workdir / f'{out_mp4.stem}.props.json'
    save_json(props_file, props)
    silent = workdir / f'{out_mp4.stem}.remotion.mp4'
    cmd = [npx, 'remotion', 'render', 'src/index.ts', 'Clip', str(silent.resolve()),
           f'--props={props_file.resolve()}', '--muted', '--codec=h264', '--crf=18',
           '--concurrency=50%', '--log=error']
    r = subprocess.run(cmd, cwd=REMOTION, shell=(os.name == 'nt'))
    (pub / tag).unlink(missing_ok=True)
    if r.returncode != 0 or not silent.exists():
        die('remotion render failed (see output above)')
    ffmpeg('-i', silent, '-i', audio_wav, '-map', '0:v', '-map', '1:a', '-c:v', 'copy', '-c:a', 'aac',
           '-b:a', '192k', '-shortest', '-movflags', '+faststart', out_mp4)
    silent.unlink(missing_ok=True)


# ---------------- main ----------------

def edit_one(job):
    """Edit one clip (run in a worker process when two clips render at once). -> (out file, messages)."""
    a, opts, cfg, brand = job['a'], job['opts'], job['cfg'], job['brand']
    pdir, out_dir, work, clips_dir = job['pdir'], job['out_dir'], job['work'], job['clips_dir']
    project = load_json(pdir / 'project.json')
    meta = load_json(job['meta'])
    msgs = []
    say = msgs.append
    clip_mp4 = clips_dir / meta['file']
    out = out_dir / meta['file']
    t0 = time.time()
    say(f"-> editing clip {meta['id']}: {meta['title']} ({a.engine} engine)")
    meta = romanize.for_captions(pdir, project, meta, cfg)
    picked = next((c for c in (load_json(pdir / 'clips.json', {}) or {}).get('clips', [])
                   if int(c.get('id', 0)) == meta['id']), {})
    meta['clarify'] = picked.get('clarify', [])
    _, missing = planlib.add_clarify(meta["words"], meta["clarify"])
    for m in missing:
        say(f'   ! clarify: "{m}" is not said in this clip (check the words, as in the transcript)')
    clip_opts = dict(opts, caption_y=a.caption_y or meta.get('caption_y') or 1270,
                     caption_y_fixed=a.caption_y is not None)
    safe = cfg.get('safe_zones', True) if a.safe_zones is None else a.safe_zones
    hook_on = cfg.get('hook_title', True) if a.hook_title is None else a.hook_title
    clip_opts['moods'] = mood_marks(picked.get('sfx'), meta)
    emoji_on = cfg.get('emoji', True) if a.emoji is None else a.emoji
    clip_opts['emoji'] = picked.get('emoji') if emoji_on else None
    clip_opts.update(safe=safe, hook=hook_on and opts['captions'],
                     hook_text=picked.get('hook_text') or picked.get('title'))
    if safe or clip_opts['hook']:
        clip_opts['faces'] = layoutlib.face_boxes(clip_mp4, meta.get('shots', []))
    if meta.get('layout') == 'facecam':
        clip_opts['zoom'] = False      # zooming would push the cam / gameplay split around
    plan = planlib.build(meta, brand, clip_opts)
    for m in plan.get('emoji_missing', []):
        say(f'   ! emoji left out: "{m}" (a word not said in this clip, or no free spot)')
    for e in plan.get('emoji', []):
        e['png'] = str(emojilib.png(e['char']) or '')
        if not e['png']:
            say(f"   ! emoji {e['char']}: its picture couldn't be downloaded (offline?), left out")
    plan['emoji'] = [e for e in plan.get('emoji', []) if e['png']]
    if a.engine == 'remotion' and (plan['emoji'] or plan['caption_style'].get('look') != 'classic'):
        say('   (the Remotion engine draws the classic caption look and no emojis: use the python engine for those)')
    if any(has_devanagari(w['text']) for g in plan['captions'] for w in g['words']):
        say(f"   captions include Devanagari -> font {plan['caption_style']['font']}")
    save_json(work / f"{meta['name']}.plan.json", {k: v for k, v in plan.items() if k != 'cam'})
    plan['encoder'] = video_encoder(cfg)[0]
    wav = work / f"{meta['name']}.mix.wav"
    track = None
    music_on = cfg.get('music', True) if a.music is None else a.music
    if music_on and picked.get('music') and opts['sfx'] != 'none':
        track = musiclib.pick(picked['music'], meta['name'])
        if not track:
            say(f"   ! music \"{picked['music']}\": no tracks in music/{picked['music']}/ (`python run.py music`)")
    mix_audio(clip_mp4, plan['sfx'], wav, plan['duration'], track)
    (render_remotion if a.engine == 'remotion' else render_python)(clip_mp4, plan, wav, out, work)
    if plan['captions']:
        write_srt(plan, out.with_suffix('.srt'))
    wav.unlink(missing_ok=True)
    sfx = ', '.join(f"{c['role']}@{c['at'] + 0:.1f}s" for c in plan['sfx']) or 'none'
    moved = len({g['y'] for g in plan['captions'] if g.get('y') not in (None, H // 2)})
    extra = (f"  hook: \"{' / '.join(plan['hook']['lines'])}\" at y={plan['hook']['y']}" if plan.get('hook') else '') + \
            (f"  captions moved off a face in {moved} place(s)" if moved and safe else '')
    if track:
        extra += f'  music: {track.parent.name}/{track.name}'
    say(f"   ok {out.name}  zooms:{len(plan['transitions'])}  captions:{len(plan['captions'])}  "
          f"sfx: {sfx}  ({time.time() - t0:.0f}s){extra}")
    return out, msgs


def workers(cfg, n_clips, engine):
    """How many clips render at once: 2 with 4+ CPU cores and 4+ GB of free memory (each render holds
    about 1 GB), else 1. settings.json "render_workers" can fix it."""
    want = cfg.get('render_workers', 'auto')
    if isinstance(want, int) and want > 0:
        return min(want, n_clips)
    if engine != 'python' or n_clips < 2 or (os.cpu_count() or 1) < 4:
        return 1
    free_gb = 0.0
    try:
        with open('/proc/meminfo') as f:
            free_gb = next(int(l.split()[1]) for l in f if l.startswith('MemAvailable')) / 1e6
    except (OSError, StopIteration):
        try:
            import psutil
            free_gb = psutil.virtual_memory().available / 1e9
        except Exception:
            return 1
    return 2 if free_gb >= 4 else 1


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('project')
    ap.add_argument('--clips', default=None)
    ap.add_argument('--engine', default='python', choices=['python', 'remotion'])
    ap.add_argument('--no-zoom', action='store_true')
    ap.add_argument('--no-captions', action='store_true')
    ap.add_argument('--sfx', default='auto', choices=['auto', 'light', 'none'])
    ap.add_argument('--no-upper', action='store_true', help='sentence case captions instead of UPPERCASE')
    ap.add_argument('--caption-y', type=int, default=None,
                    help='caption centre line in px (0-1920); default 1270, or the seam in the facecam layout')
    ap.add_argument('--size', type=int, default=None, help='caption font size in px (default: the look\'s own)')
    ap.add_argument('--look', default=None, choices=sorted(planlib.LOOKS),
                    help='caption look (default: settings.json "caption_look", classic)')
    ap.add_argument('--out', default=None, help='output folder (default <project>/edited)')
    ap.add_argument('--emoji', action=argparse.BooleanOptionalAction, default=None,
                    help='emojis on the words clips.json names (default: settings.json "emoji", on)')
    ap.add_argument('--encoder', default=None, choices=['auto', 'nvenc', 'x264'],
                    help='video encoder (default: settings.json "encoder", auto: the NVIDIA one if it works)')
    ap.add_argument('--workers', type=int, default=None, help='clips edited at once (default: auto)')
    ap.add_argument('--music', action=argparse.BooleanOptionalAction, default=None,
                    help='background music where clips.json names a mood (default: settings.json "music", on)')
    ap.add_argument('--hook-title', action=argparse.BooleanOptionalAction, default=None,
                    help='the hook title for the first seconds (default: settings.json "hook_title", on)')
    ap.add_argument('--safe-zones', action=argparse.BooleanOptionalAction, default=None,
                    help='captions clear of faces and the apps\' buttons (default: settings.json "safe_zones", on)')
    ap.add_argument('--jump-label', action=argparse.BooleanOptionalAction, default=None,
                    help='a small "27 MIN LATER" label where a joined clip jumps in time '
                         '(default: "jump_label" in settings.json, else off)')
    a = ap.parse_args()

    pdir = project_dir(a.project)
    clips_dir = pdir / 'clips'
    if a.encoder:
        os.environ['CLIPKARO_ENCODER'] = a.encoder
    metas = sorted(clips_dir.glob('*.json'))
    if not metas:
        die('no cut clips yet. Run: python run.py cut ' + pdir.name)
    want = {int(x) for x in a.clips.split(',')} if a.clips else None
    out_dir = Path(a.out) if a.out else pdir / 'edited'
    out_dir.mkdir(parents=True, exist_ok=True)
    work = pdir / '.work'
    work.mkdir(exist_ok=True)

    from .cut import ensure_video
    project = load_json(pdir / 'project.json')
    cfg = settings()
    # the colours are saved in brand.json after the first edit: no need for the video (it may be deleted)
    brand = load_json(pdir / 'brand.json') or brandlib.resolve(pdir, ensure_video(pdir, project))
    print(f"-> brand colours: accent {brand['accent']} ({brand['source']})")
    if romanize.wants_roman(project, cfg):
        print('-> captions: Roman Hinglish (romanize.json)')
    opts = {'zoom': not a.no_zoom, 'captions': not a.no_captions, 'sfx': a.sfx,
            'uppercase': not a.no_upper, 'caption_y': a.caption_y, 'size': a.size,
            'look': a.look or cfg.get('caption_look', 'classic'),
            'jump_label': a.jump_label if a.jump_label is not None else bool(cfg.get('jump_label', False))}
    jobs = []
    for mpath in metas:
        meta = load_json(mpath)
        if want and meta['id'] not in want:
            continue
        jobs.append({'a': a, 'opts': opts, 'cfg': cfg, 'brand': brand, 'pdir': pdir, 'out_dir': out_dir,
                     'work': work, 'clips_dir': clips_dir, 'meta': mpath})
    n = min(a.workers, len(jobs)) if a.workers else workers(cfg, len(jobs), a.engine)
    enc = 'the NVIDIA encoder' if video_encoder(cfg)[1] == 'h264_nvenc' else 'the processor (libx264)'
    print(f"-> {len(jobs)} clip(s), {n} at a time, encoded on {enc}")
    done = []
    if n > 1:
        from concurrent.futures import ProcessPoolExecutor
        with ProcessPoolExecutor(max_workers=n) as pool:
            for out, msgs in pool.map(edit_one, jobs):
                print('\n'.join(msgs), flush=True)
                done.append(out)
    else:
        for job in jobs:
            out, msgs = edit_one(job)
            print('\n'.join(msgs), flush=True)
            done.append(out)
    print(f'\nDONE: {len(done)} edited clip(s) in {out_dir}')


if __name__ == '__main__':
    main()
