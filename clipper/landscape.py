"""A landscape (16:9) copy of finished clips (v2.8): the same clip, wide, for YouTube or a compilation.

    python run.py landscape <project>               every edited clip
    python run.py landscape <project> --clips 2,5   only some

Only when asked ("landscape copy"), and for compilations longer than 1:30 (the owner's choice, 23 November
2026). How:
- `cut --landscape-copy` cuts the clip again without reframing, into clips-landscape/: the same pieces and pause
  cuts as the standing clip, so both share one timeline;
- the standing edit's plan (.work/<clip>.plan.json) is drawn again for a 1920x1080 frame: the captions in the
  lower part of the picture, the "(c) source" credit and the logo in their corners, the emojis above the caption;
- the sound is the standing edit's (sound effects, loudness), so both copies sound the same.
No zooms (the whole picture is shown) and no outro (it is standing). Writes edited/NN-title-landscape.mp4.
On the 22 November glitch compilation this was done by hand (output/...-landscape/work/finish.py).
"""
import argparse
import subprocess
import sys
from pathlib import Path

from .common import die, load_json, probe, project_dir, settings

FW, FH = 1920, 1080
CAP_Y = 900                # caption centre: the lower part of the picture, above most games' own subtitles
TEXT_SCALE = 0.75          # caption size against the standing clip's (a wide frame is 1080 px high, not 1920)
CREDIT_SCALE = 0.62
HOOK_Y = 170
JUMP_Y = 140
EMOJI_SIZE = 110
EMOJI_Y = CAP_Y - 140      # above the caption line


def landscape_plan(plan):
    """The standing edit's plan, placed for a 1920x1080 frame (a new dict; the old one is left alone)."""
    land = dict(plan)
    st = dict(plan['caption_style'])
    st['size'] = round(st['size'] * TEXT_SCALE)
    st['y'] = CAP_Y
    land['caption_style'] = st
    # moved-off-a-face heights and shrink-to-fit are about the standing frame: a wide frame has room
    land['captions'] = [{k: v for k, v in g.items() if k not in ('y', 'scale')} for g in plan.get('captions', [])]
    if plan.get('hook'):
        land['hook'] = dict(plan['hook'], y=HOOK_Y)
    cr = plan.get('credit')
    if cr:
        an = cr.get('an', 1)                      # 1 bottom-left, 3 bottom-right, 7 top-left, 9 top-right
        land['credit'] = dict(cr, size=round(cr['size'] * CREDIT_SCALE), x=FW if an in (3, 9) else 0,
                              y=FH if an in (1, 3) else 0)
    lg = plan.get('logo')
    if lg:
        corner = str(lg.get('corner') or 'bottom-right')
        land['logo'] = dict(lg, x=FW - lg['w'] if 'right' in corner else 0, y=FH - lg['h'] if 'bottom' in corner else 0)
    land['emoji'] = [dict(e, x=FW // 2, y=EMOJI_Y, size=EMOJI_SIZE) for e in plan.get('emoji') or []]
    land['outro'] = None
    return land


def duration(path):
    try:
        return float(probe(str(path))['duration'])
    except (SystemExit, Exception):
        return 0.0


def render(cut_mp4, land, audio_from, out_mp4, ass, encoder):
    """The wide cut + captions (ASS) + logo + emojis, with the sound of `audio_from`."""
    import os
    from .common import ROOT
    work = Path(ass).parent                 # run from the work folder with short relative paths, as the edit does
    fonts = os.path.relpath(ROOT / 'assets' / 'fonts', work).replace('\\', '/')
    inputs, chains = ['-i', str(Path(cut_mp4).resolve()), '-i', str(Path(audio_from).resolve())], []
    chains.append(f"[0:v]ass={Path(ass).name}:fontsdir={fonts}[c0]")
    cur, n = 'c0', 2
    lg = land.get('logo')
    if lg:
        inputs += ['-i', str(Path(lg['file']).resolve())]
        chains.append(f"[{n}:v]scale={lg['w']}:{lg['h']},format=rgba,colorchannelmixer=aa={lg['alpha']}[lg]")
        chains.append(f"[{cur}][lg]overlay={lg['x']}:{lg['y']}:format=auto[c1]")
        cur, n = 'c1', n + 1
    for k, e in enumerate(land.get('emoji') or []):
        if not e.get('png'):
            continue
        inputs += ['-i', str(Path(e['png']).resolve())]
        size = e['size']
        chains.append(f"[{n}:v]scale={size}:{size}[e{k}]")
        chains.append(f"[{cur}][e{k}]overlay={e['x'] - size // 2}:{e['y'] - size // 2}:"
                      f"enable='between(t,{e['t0']:.2f},{e['t1']:.2f})'[ce{k}]")
        cur, n = f'ce{k}', n + 1
    chains.append(f'[{cur}]format=yuv420p[out]')
    cmd = ['ffmpeg', '-v', 'error', '-y', *inputs, '-filter_complex', ';'.join(chains), '-map', '[out]', '-map', '1:a',
           *encoder, '-c:a', 'aac', '-b:a', '192k', '-shortest', '-movflags', '+faststart', str(Path(out_mp4).resolve())]
    r = subprocess.run(cmd, capture_output=True, text=True, cwd=work)
    if r.returncode != 0:
        die('landscape render failed: ' + (r.stderr or '')[-600:])


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('project')
    ap.add_argument('--clips', default=None, help='comma list of clip ids, e.g. 2,5')
    a = ap.parse_args()
    from . import edit
    pdir = project_dir(a.project)
    picks = (load_json(pdir / 'clips.json', {}) or {}).get('clips', [])
    want = {int(x) for x in a.clips.split(',')} if a.clips else None
    todo = []
    for k, c in enumerate(picks, 1):
        cid = int(c.get('id', k))
        if want and cid not in want:
            continue
        found = sorted((pdir / 'edited').glob(f'{cid:02d}-*.mp4'))
        found = [f for f in found if not f.stem.endswith('-landscape')]
        if not found:
            print(f'   clip {cid}: not edited yet (run edit first): skipped')
            continue
        name = found[0].stem
        if not (pdir / '.work' / f'{name}.plan.json').exists():
            print(f'   clip {cid}: no edit plan in .work (edit it again): skipped')
            continue
        todo.append((cid, name, found[0]))
    if not todo:
        die('no edited clips to copy')
    def stale(name):                    # no wide cut yet, or one older than the standing cut (the clip changed)
        wide, standing = pdir / 'clips-landscape' / f'{name}.mp4', pdir / 'clips' / f'{name}.mp4'
        return not wide.exists() or (standing.exists() and wide.stat().st_mtime < standing.stat().st_mtime)
    missing = [str(cid) for cid, name, _ in todo if stale(name)]
    if missing:
        print(f"-> cutting the wide copies of clip(s) {', '.join(missing)} (same pieces as the standing clips) ...",
              flush=True)
        r = subprocess.run([sys.executable, '-m', 'clipper.cut', pdir.name, '--landscape-copy', '--clips',
                            ','.join(missing)])
        if r.returncode != 0:
            die('the wide cut failed (see above)')
    encoder = edit.video_encoder(settings())[0]
    work = pdir / '.work'
    for cid, name, edited in todo:
        wide = pdir / 'clips-landscape' / f'{name}.mp4'
        if not wide.exists():
            print(f'   clip {cid}: the wide cut is missing: skipped')
            continue
        plan = load_json(work / f'{name}.plan.json')
        land = landscape_plan(plan)
        ass = work / f'{name}-landscape.ass'
        edit.write_ass(land, ass, frame=(FW, FH), jump_y=JUMP_Y)
        standing = pdir / 'clips' / f'{name}.mp4'
        same = abs(duration(wide) - duration(standing)) < 0.05
        if not same:
            print(f'   ! clip {cid}: the wide cut is not the same length as the standing one: its own sound '
                  f'(no sound effects)')
        out = pdir / 'edited' / f'{name}-landscape.mp4'
        render(wide, land, edited if same else wide, out, ass, encoder)
        print(f'   ok {out.name}  ({duration(out):.1f} s, 1920x1080)')


if __name__ == '__main__':
    main()
