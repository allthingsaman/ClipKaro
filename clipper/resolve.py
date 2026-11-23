"""Open a clip in DaVinci Resolve (free) to finish it by hand (v2.8, only when asked: "export to resolve").

    python run.py resolve <project>               every cut clip
    python run.py resolve <project> --clips 2,5   only some

What you get, per clip, in output/<project>/resolve/NN-title/:
  NN-title.xml   the timeline (Final Cut Pro 7 XML). In Resolve: File > Import > Timeline..., pick this file.
                 Track V1: the standing clip, cut into its pieces (each pause cut is a visible cut you can move).
                 A1: its sound. A2: the sound effects at their moments, at the loudness the edit used.
  captions.srt   the captions, word groups with their times. In Resolve: File > Import > Subtitle..., then drag
                 it onto the timeline.
  media/         the files the timeline uses (Linux: edit copies, see below).
  HOW-TO.txt     these steps in short.
Not included: the zooms, the caption style, the emojis, the logo, the credit and the outro (Resolve can't take
them from a file; the finished clip in edited/ has them all, to compare).

EDIT COPIES (Linux): the free DaVinci Resolve on Linux can't read the normal H.264 picture and AAC sound, so on
Linux the clip is copied as DNxHR LB picture with PCM sound in a .mov (about 6 MB a second of clip); on Windows and
macOS the timeline points at clips/ directly. Sound effects always become WAV files, with the edit's loudness
baked in. settings.json "resolve_copies": "yes" / "no" overrides the automatic choice.
The same way EditKaro (the owner's editing tool) hands its timelines to Resolve.
"""
import argparse
import os
import shutil
import subprocess
import sys
import urllib.parse
from fractions import Fraction
from pathlib import Path
from xml.sax.saxutils import escape

from .common import ROOT, die, load_json, project_dir, settings

COPY_ARGS = ['-c:v', 'dnxhd', '-profile:v', 'dnxhr_lb', '-pix_fmt', 'yuv422p', '-c:a', 'pcm_s16le', '-ar', '48000']
HOW_TO = """Open this clip in DaVinci Resolve (free)

1. Resolve: File > Import > Timeline...  and pick {xml}
   (if it asks, let it import the media too). The timeline opens: the clip in its pieces on V1, its sound on A1,
   the sound effects on A2.
2. Captions: File > Import > Subtitle...  and pick captions.srt, then drag it from the Media Pool onto the
   timeline (it becomes a subtitle track you can restyle and edit).
3. Edit, then Deliver. On Linux the free Resolve can't make an MP4: render a .mov and turn it into an MP4 with
   ffmpeg -i clip.mov -c:v libx264 -crf 18 -pix_fmt yuv420p -c:a aac -b:a 192k clip.mp4

The finished ClipKaro clip (zooms, captions, emojis, logo, credit) is in edited/, to compare.
"""


def copies_wanted():
    want = str(settings().get('resolve_copies', 'auto')).lower()
    if want in ('yes', 'true', 'on'):
        return True
    if want in ('no', 'false', 'off'):
        return False
    return sys.platform.startswith('linux')


def file_url(path):
    """FCP 7 XML wants file://localhost/... with spaces and Hindi letters %-encoded."""
    p = Path(path).resolve().as_posix()
    if os.name == 'nt' or (len(p) > 1 and p[1] == ':'):
        return 'file://localhost/' + urllib.parse.quote(p, safe='/:')
    return 'file://localhost' + urllib.parse.quote(p, safe='/')


def rate_of(path):
    r = subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries', 'stream=r_frame_rate',
                        '-of', 'default=nw=1:nk=1', str(path)], capture_output=True, text=True)
    try:
        f = Fraction(r.stdout.strip())
        return f if f > 0 else Fraction(30)
    except (ValueError, ZeroDivisionError):
        return Fraction(30)


def rate_xml(fps):
    fps = Fraction(fps)
    if fps.denominator == 1001:
        return f'<rate><timebase>{round(fps.numerator / 1000)}</timebase><ntsc>TRUE</ntsc></rate>'
    return f'<rate><timebase>{round(float(fps))}</timebase><ntsc>FALSE</ntsc></rate>'


def frames(t, fps):
    return int(round(Fraction(t).limit_denominator(100000) * Fraction(fps)))


def pieces(meta):
    """The clip's pieces in clip seconds [(start, end)], from its source parts (after pause cuts)."""
    out, t = [], 0.0
    for a, b in meta.get('parts') or [[0.0, meta['duration']]]:
        d = b - a
        out.append((t, min(meta['duration'], t + d)))
        t += d
    if out:                                   # rounding: the last piece ends with the clip
        out[-1] = (out[-1][0], meta['duration'])
    return [(a, b) for a, b in out if b - a > 0.02]


def timeline_xml(name, clip_file, dur, fps, parts, sfx, size=(1080, 1920)):
    """The clip as Final Cut Pro 7 XML: V1/A1 the clip in its pieces, A2 the sound effects [(wav, at, length)]."""
    rt, W, H = rate_xml(fps), *size
    total = frames(dur, fps)
    clip_file = Path(clip_file)
    file_full = (f'<file id="file-1"><name>{escape(clip_file.name)}</name><pathurl>{escape(file_url(clip_file))}</pathurl>'
                 f'{rt}<duration>{total}</duration>'
                 f'<timecode>{rt}<string>00:00:00:00</string><frame>0</frame><displayformat>NDF</displayformat></timecode>'
                 f'<media><video><samplecharacteristics>{rt}<width>{W}</width><height>{H}</height>'
                 f'<pixelaspectratio>square</pixelaspectratio></samplecharacteristics></video>'
                 f'<audio><samplecharacteristics><depth>16</depth><samplerate>48000</samplerate></samplecharacteristics>'
                 f'<channelcount>2</channelcount></audio></media></file>')
    file_ref = '<file id="file-1"/>'
    vids, auds = [], []
    for k, (a, b) in enumerate(parts, 1):
        fa, fb = frames(a, fps), frames(b, fps)
        links = (f'<link><linkclipref>v-{k}</linkclipref><mediatype>video</mediatype><trackindex>1</trackindex>'
                 f'<clipindex>{k}</clipindex></link>'
                 f'<link><linkclipref>a-{k}</linkclipref><mediatype>audio</mediatype><trackindex>1</trackindex>'
                 f'<clipindex>{k}</clipindex><groupindex>1</groupindex></link>')
        common = (f'<name>{escape(clip_file.name)}</name><enabled>TRUE</enabled><duration>{total}</duration>{rt}'
                  f'<start>{fa}</start><end>{fb}</end><in>{fa}</in><out>{fb}</out>')
        vids.append(f'<clipitem id="v-{k}">{common}{file_full if k == 1 else file_ref}{links}</clipitem>')
        auds.append(f'<clipitem id="a-{k}">{common}<file id="file-1"/>'
                    f'<sourcetrack><mediatype>audio</mediatype><trackindex>1</trackindex></sourcetrack>{links}</clipitem>')
    fx = []
    for k, (wav, at, length) in enumerate(sfx, 1):
        n = max(1, frames(length, fps))
        s0 = frames(at, fps)
        fx.append(f'<clipitem id="sfx-{k}"><name>{escape(Path(wav).name)}</name><enabled>TRUE</enabled>'
                  f'<duration>{n}</duration>{rt}<start>{s0}</start><end>{s0 + n}</end><in>0</in><out>{n}</out>'
                  f'<file id="sfx-file-{k}"><name>{escape(Path(wav).name)}</name><pathurl>{escape(file_url(wav))}</pathurl>'
                  f'{rt}<duration>{n}</duration><media><audio><samplecharacteristics><depth>16</depth>'
                  f'<samplerate>48000</samplerate></samplecharacteristics><channelcount>2</channelcount></audio></media>'
                  f'</file><sourcetrack><mediatype>audio</mediatype><trackindex>1</trackindex></sourcetrack></clipitem>')
    markers = ''.join(f'<marker><name>pause cut</name><comment>ClipKaro cut a pause here</comment><color>Blue</color>'
                      f'<in>{frames(a, fps)}</in><out>-1</out></marker>' for a, _ in parts[1:])
    return ('<?xml version="1.0" encoding="UTF-8"?>\n<!DOCTYPE xmeml>\n<xmeml version="5">'
            f'<sequence id="sequence-1"><name>{escape(name)}</name><duration>{total}</duration>{rt}'
            f'<timecode>{rt}<string>00:00:00:00</string><frame>0</frame><displayformat>NDF</displayformat></timecode>'
            '<media><video><format><samplecharacteristics>'
            f'{rt}<width>{W}</width><height>{H}</height><pixelaspectratio>square</pixelaspectratio>'
            '<fielddominance>none</fielddominance></samplecharacteristics></format>'
            f'<track>{"".join(vids)}</track></video>'
            '<audio><numOutputChannels>2</numOutputChannels><format><samplecharacteristics><depth>16</depth>'
            '<samplerate>48000</samplerate></samplecharacteristics></format>'
            f'<track>{"".join(auds)}</track>' + (f'<track>{"".join(fx)}</track>' if fx else '') +
            f'</audio></media>{markers}</sequence></xmeml>\n')


def sfx_wavs(plan, media):
    """The edit's sound effects as WAV files (their part of the sound file, at the edit's loudness):
    [(wav, at, length)]."""
    out = []
    for k, s in enumerate(plan.get('sfx') or [], 1):
        src = Path(s.get('path') or '')
        src = src if src.is_absolute() else ROOT / src
        if not src.exists():
            continue
        gain = float(s.get('gain_db', 0)) + float(s.get('norm_db', 0))
        dst = media / f"sfx-{k:02d}-{Path(s.get('file') or src.name).stem}.wav"
        r = subprocess.run(['ffmpeg', '-v', 'error', '-y', '-ss', f"{float(s.get('offset', 0)):.3f}", '-t',
                            f"{float(s.get('length', 1)):.3f}", '-i', str(src), '-af', f'volume={gain:.2f}dB',
                            '-ac', '2', '-ar', '48000', '-c:a', 'pcm_s16le', str(dst)], capture_output=True)
        if r.returncode == 0:
            out.append((dst, float(s.get('at', 0)), float(s.get('length', 1))))
    return out


def export(pdir, meta, copies):
    name = meta['name']
    cut = pdir / 'clips' / meta['file']
    folder = pdir / 'resolve' / name
    media = folder / 'media'
    media.mkdir(parents=True, exist_ok=True)
    clip_file = cut
    if copies:
        clip_file = media / f'{name}.mov'
        if not clip_file.exists() or clip_file.stat().st_mtime < cut.stat().st_mtime:
            r = subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', str(cut), *COPY_ARGS, str(clip_file)],
                               capture_output=True, text=True)
            if r.returncode != 0:
                die(f'edit copy of {cut.name} failed: ' + (r.stderr or '')[-400:])
    plan = load_json(pdir / '.work' / f'{name}.plan.json') or {}
    sfx = sfx_wavs(plan, media)
    srt = pdir / 'edited' / f'{name}.srt'
    if srt.exists():
        shutil.copyfile(srt, folder / 'captions.srt')
    fps = rate_of(cut)
    xml = folder / f'{name}.xml'
    xml.write_text(timeline_xml(f"{meta.get('title') or name} (ClipKaro)", clip_file, meta['duration'], fps,
                                pieces(meta), sfx), encoding='utf-8')
    (folder / 'HOW-TO.txt').write_text(HOW_TO.format(xml=xml.name), encoding='utf-8')
    return folder, len(pieces(meta)), len(sfx), srt.exists()


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('project')
    ap.add_argument('--clips', default=None, help='comma list of clip ids, e.g. 2,5')
    a = ap.parse_args()
    pdir = project_dir(a.project)
    want = {int(x) for x in a.clips.split(',')} if a.clips else None
    metas = [load_json(m) for m in sorted((pdir / 'clips').glob('*.json'))]
    metas = [m for m in metas if m and 'parts' in m and (not want or m.get('id') in want)
             and (pdir / 'clips' / m.get('file', '')).exists()]
    if not metas:
        die(f'no cut clips in {pdir.name}: run cut first')
    copies = copies_wanted()
    if copies:
        print('-> Linux: the free DaVinci Resolve reads only edit copies (DNxHR + PCM, about 6 MB a second)')
    for m in metas:
        folder, n, n_fx, has_srt = export(pdir, m, copies)
        print(f"   ok clip {m['id']}: {folder.relative_to(pdir)}/  {n} piece(s), {n_fx} sound effect(s)"
              + ('' if has_srt else '  (no captions.srt: run edit first)'))
    print(f'next: open DaVinci Resolve > File > Import > Timeline... and pick the .xml '
          f'(steps in each folder\'s HOW-TO.txt)')


if __name__ == '__main__':
    main()
