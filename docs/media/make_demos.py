"""Makes the README's demo GIFs: the real video on the left (with a timeline of the whole video and
where the clip comes from), the clip ClipKaro made on the right, playing in step.

    .venv/bin/python docs/media/make_demos.py            (needs the test projects in output/)

The clips are real ClipKaro output from the owner's test videos; the GIFs credit each source. GIFs are
silent, so the burned-in captions carry the words and short labels say what happens ("the host laughs
-> both on screen"). Made with ffmpeg only (drawtext, palettegen): about 2-5 MB each.
"""
import glob
import json
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
FONT = ROOT / 'assets' / 'fonts' / 'Montserrat-ExtraBold.ttf'
BODY = ROOT / 'assets' / 'fonts' / 'Poppins-ExtraBold.ttf'
W, H = 800, 480                     # the GIF (GitHub shows a README about 830 px wide)
SRC_W, SRC_H, SRC_X, SRC_Y = 480, 270, 16, 92
CLIP_W, CLIP_H, CLIP_X = 270, 480, 530
BAR_Y = SRC_Y + SRC_H + 26
BG, ACCENT, GREY = '0x0d1117', '0xFFD60A', '0x30363d'
FPS = 10


def project(tail):
    return Path(glob.glob(str(ROOT / 'output' / f'*{tail}'))[0])


def clip_meta(pdir, cid):
    return json.loads(Path(glob.glob(str(pdir / 'clips' / f'{cid:02d}-*.json'))[0]).read_text(encoding='utf-8'))


def edited(pdir, cid):
    return glob.glob(str(pdir / 'edited' / f'{cid:02d}-*.mp4'))[0]


def pieces(meta, t0, t1):
    """The source stretches shown during clip time [t0, t1]: [(source start, length, gif time)]."""
    out, acc = [], 0.0
    for a, b in meta['parts']:
        d = b - a
        lo, hi = max(t0, acc), min(t1, acc + d)
        if hi > lo:
            out.append((a + lo - acc, hi - lo, lo - t0))
        acc += d
    return out


def mmss(s):
    s = int(round(s))
    return f'{s // 3600}:{s // 60 % 60:02d}:{s % 60:02d}' if s >= 3600 else f'{s // 60}:{s % 60:02d}'


def esc(path):
    return str(path).replace('\\', '/').replace(':', r'\:')


def text(tmp, name, s, x, y, size=18, color='white', font=FONT, enable=None):
    f = Path(tmp) / f'{name}.txt'
    f.write_text(s, encoding='utf-8')
    e = f":enable='{enable}'" if enable else ''
    return f"drawtext=fontfile='{esc(font)}':textfile='{esc(f)}':x={x}:y={y}:fontsize={size}:fontcolor={color}{e}"


def make(name, pdir, cid, t0, t1, title, credit, labels=(), moments_label=True, colors=128, fps=None):
    """labels: [(gif start, gif end, text)] shown under the timeline."""
    meta, project_info = clip_meta(pdir, cid), json.loads((pdir / 'project.json').read_text(encoding='utf-8'))
    src = pdir / 'source' / 'video.mp4'
    total = float(project_info.get('duration') or 1)
    ps = pieces(meta, t0, t1)
    dur = t1 - t0
    FPS = fps or globals()['FPS']
    with tempfile.TemporaryDirectory() as tmp:
        inputs, chains = [], []
        for k, (a, d, _) in enumerate(ps):
            inputs += ['-ss', f'{a:.3f}', '-t', f'{d:.3f}', '-i', str(src)]
            chains.append(f'[{k}:v]fps={FPS},scale={SRC_W}:{SRC_H}:flags=lanczos,setsar=1[s{k}]')
        n = len(ps)
        inputs += ['-ss', f'{t0:.3f}', '-t', f'{dur:.3f}', '-i', edited(pdir, cid)]
        chains.append(''.join(f'[s{k}]' for k in range(n)) + f'concat=n={n}:v=1:a=0[src]')
        chains.append(f'[{n}:v]fps={FPS},scale={CLIP_W}:{CLIP_H}:flags=lanczos,setsar=1[clip]')
        chains.append(f'color=c={BG}:s={W}x{H}:r={FPS}:d={dur:.3f}[bg]')
        draw = []
        # the timeline of the whole video, the clip's moments on it, and where the left picture is now
        draw.append(f'drawbox=x={SRC_X}:y={BAR_Y}:w={SRC_W}:h=10:color={GREY}:t=fill')
        groups = []
        for a, b in meta['parts']:
            x = SRC_X + int(SRC_W * a / total)
            draw.append(f'drawbox=x={x}:y={BAR_Y}:w={max(3, int(SRC_W * (b - a) / total))}:h=10:color={ACCENT}:t=fill')
            if groups and a - groups[-1][1] < 60:
                groups[-1][1] = b
            else:
                groups.append([a, b])
        pos = f'{ps[-1][0]:.3f}+(t-{ps[-1][2]:.3f})'
        for a, d, g in reversed(ps[:-1]):
            pos = f'if(lt(t,{g + d:.3f}),{a:.3f}+(t-{g:.3f}),{pos})'
        draw.append(f"drawbox=x='{SRC_X}+{SRC_W}*({pos})/{total:.3f}-1':y={BAR_Y - 5}:w=3:h=20:color=white:t=fill")
        draw.append(text(tmp, 'start', '0:00', SRC_X, BAR_Y + 16, 13, '0x8b949e', BODY))
        draw.append(text(tmp, 'end', mmss(total), f'{SRC_X + SRC_W}-tw', BAR_Y + 16, 13, '0x8b949e', BODY))
        if moments_label:
            for j, (a, b) in enumerate(groups):            # the clip's moments, above the bar
                x = min(max(SRC_X + int(SRC_W * a / total) - 18, SRC_X), SRC_X + SRC_W - 60)
                draw.append(text(tmp, f'm{j}', mmss(a), x, BAR_Y - 22, 15, ACCENT, BODY))
        draw.append(text(tmp, 'title', title, SRC_X, 18, 21))
        draw.append(text(tmp, 'credit', credit, SRC_X, 52, 13, '0x8b949e', BODY))
        draw.append(text(tmp, 'arrow', '→', f'{CLIP_X - 34}', CLIP_H // 2 - 22, 34, ACCENT))
        for j, (a, b, s) in enumerate(labels):
            draw.append(text(tmp, f'l{j}', s, SRC_X, BAR_Y + 44, 19, 'white', FONT, f'between(t,{a:.2f},{b:.2f})'))
        chains.append(f'[bg][src]overlay={SRC_X}:{SRC_Y}[b1]')
        # a little denoise first: film grain and game noise cost most of a GIF's size
        chains.append(f'[b1][clip]overlay={CLIP_X}:0,hqdn3d=2:2:6:6,' + ','.join(draw) + ',split[g1][g2]')
        chains.append(f'[g1]palettegen=max_colors={colors}:stats_mode=diff[pal]')
        chains.append('[g2][pal]paletteuse=dither=bayer:bayer_scale=5:diff_mode=rectangle')
        out = OUT / f'{name}.gif'
        subprocess.run(['ffmpeg', '-v', 'error', '-y', *inputs, '-filter_complex', ';'.join(chains),
                        '-loop', '0', str(out)], check=True)
    print(f'{out.name}: {out.stat().st_size / 1e6:.1f} MB, {dur:.0f} s')
    return out


def caption_still(name, shots, title):
    """Frames of finished clips side by side, the apps' own buttons and texts marked in red (the areas
    ClipKaro keeps captions out of: layout.SAFE_TOP / SAFE_BOTTOM / SAFE_RIGHT), a label under each."""
    fw, fh, gap, x0, y0 = 250, 444, 24, 16, 52
    sc = fh / 1920
    top, bottom, right = int(230 * sc), int(1436 * sc), int(940 * fw / 1080)
    with tempfile.TemporaryDirectory() as tmp:
        inputs, chains, draw = [], [], []
        for k, (tail, cid, t, label) in enumerate(shots):
            inputs += ['-ss', f'{t:.2f}', '-i', edited(project(tail), cid)]
            zones = [(0, 0, fw, top), (0, bottom, fw, fh - bottom), (right, top, fw - right, bottom - top)]
            boxes = ','.join(f'drawbox=x={x}:y={y}:w={w}:h={h}:color=0xff3b30@0.16:t=fill,'
                             f'drawbox=x={x}:y={y}:w={w}:h={h}:color=0xff3b30@0.9:t=2' for x, y, w, h in zones)
            chains.append(f'[{k}:v]trim=end_frame=1,setpts=PTS-STARTPTS,scale={fw}:{fh},setsar=1,format=rgb24,'
                          f'{boxes}[f{k}]')
            draw.append(text(tmp, f'lab{k}', label, x0 + k * (fw + gap), y0 + fh + 10, 15, 'white', BODY))
        cw = x0 * 2 + len(shots) * fw + (len(shots) - 1) * gap
        chains.append(f'color=c={BG}:s={cw}x{y0 + fh + 64}:d=1[bg]')
        cur = 'bg'
        for k in range(len(shots)):
            chains.append(f'[{cur}][f{k}]overlay={x0 + k * (fw + gap)}:{y0}[c{k}]')
            cur = f'c{k}'
        draw.append(text(tmp, 'title', title, x0, 16, 20))
        chains.append(f'[{cur}]' + ','.join(draw))
        out = OUT / f'{name}.png'
        subprocess.run(['ffmpeg', '-v', 'error', '-y', *inputs, '-filter_complex', ';'.join(chains),
                        '-frames:v', '1', str(out)], check=True)
    print(f'{out.name}: {out.stat().st_size / 1e3:.0f} KB')
    return out


def main():
    # 1. deep clip: two moments 27 minutes apart, joined (Sam Altman on Raj Shamani's podcast)
    sam = project('TjPPIf-M6KE')
    make('deep-clip', sam, 9, 18.5, 30.5,
         'A deep clip: 2 moments, 27 minutes apart',
         'Real ClipKaro output · source: Sam Altman on Figuring Out (Raj Shamani)',
         labels=[(0, 6.0, 'Minute 35: two ways AI could go wrong ...'),
                 (6.0, 12.0, '... minute 63: would he raise kids in that world?')])
    # 2. two people: the one talking, both when the other laughs (Khan Sir on Raj Shamani's podcast)
    khan = project('E3oG313_kps')
    make('two-people', khan, 11, 7.0, 18.0,
         'Two people: who talks, and both when one laughs',
         'Real ClipKaro output · source: Khan Sir on Figuring Out (Raj Shamani)',
         labels=[(0, 4.1, 'Khan Sir talks: the camera is on him'),
                 (4.1, 8.7, 'The host laughs: both, stacked'),
                 (8.7, 11.0, 'Back to the one talking')], moments_label=False, colors=64, fps=8)
    # 3. gameplay with a webcam: the game on top, the streamer below, captions in between (the owner's stream)
    wukong = project('PX-QnMGMUAc')
    make('gameplay', wukong, 1, 17.0, 26.0,
         'Gameplay with a webcam: game on top, you below',
         "Real ClipKaro output from the owner's own Black Myth: Wukong stream",
         labels=[(0, 9.0, 'Hinglish captions in English letters')], moments_label=False, colors=64, fps=8)
    # 4. captions: off faces, and out of the apps' buttons and texts (red)
    caption_still('captions-clear', [
        ('TjPPIf-M6KE', 2, 1.2, 'Close-up: below the chin,\nnext to the mic'),
        ('E3oG313_kps', 11, 12.3, 'Two people: on the seam,\noff both faces'),
        ('PX-QnMGMUAc', 1, 20.0, 'Gameplay: between the\ngame and the webcam')],
        "Captions stay off faces and out of the apps' buttons (red)")


if __name__ == '__main__':
    main()
