"""Compilations across videos (v2.9, advanced mode only): one clip made of moments from several videos on one topic.

    python run.py compile <name> --from <project>,<project>,...   1. a new compilation project and compile/sources.txt
                                                                     (each video's topics, clips, game-over screens
                                                                     and frame sheets: where Claude looks for moments)
    (Claude writes output/<name>/moments.json: the topic, a title and the moments in the order they play)
    python run.py compile <name> --check                          2. checks moments.json and makes a frame sheet per
                                                                     moment (compile/moment-NN.jpg): every moment is
                                                                     looked at on screen before it goes in
    python run.py compile <name> --build                          3. builds the project: frame-exact pieces with the
                                                                     loudness evened, joined into source/video.mp4; the
                                                                     checked words, Roman spellings and game-over
                                                                     screens carried over; clips.json with one clip
    python run.py compile <name> --at <project> <seconds>         a second of a source video on the compilation's clock
                                                                     (for "sfx" and "emoji" times in clips.json)

moments.json:
    {"topic": "every glitch", "title": "2 Billion Dollar Ki Game, Phir Bhi Ye Glitches",
     "moments": [{"project": "<project folder>", "ranges": [[3080.6, 3091.2], [3094.2, 3101.8]],
                  "what": "bag vanishes indoors"}, ...]}

Why advanced mode only (the owner's choice, 23 November 2026): finding the topic and every matching moment
across whole videos is Claude's job, and it costs usage; and every moment is checked on its frames, which takes
time (say so up front). Lessons of the hand-made compilation (22 November): pause cutting removed silent glitches
(a tree vanishing), so a compilation's pieces are never pause-cut and never trimmed to words (the clip's
"keep_whole" holds them all); the pieces are cut frame-exact and their loudness evened (-16 LUFS a moment,
limited), so the joins don't jump. Format: up to 1:30 a vertical Short; longer also a landscape copy
(`run.py landscape`).
"""
import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

from .common import OUTPUT, die, fmt_ts, load_json, probe, save_json

TARGET_LUFS = -16.0
MAX_GAIN = 12.0
SHEET_FRAMES = 12            # frames in a moment's frame sheet (one a second, or spread over a longer moment)
LANDSCAPE_FROM = 90.0        # longer compilations also get a landscape copy (the owner's choice)
COPY_KEYS = ('kind', 'channel', 'channel_url', 'width', 'height', 'live_status', 'was_live', 'categories',
             'language', 'asr_model', 'asr_device', 'facecam', 'video_kind')


def run(*cmd):
    r = subprocess.run([str(c) for c in cmd], capture_output=True, text=True)
    if r.returncode:
        die(f'failed: {" ".join(map(str, cmd))[:300]}\n{r.stderr[-1500:]}')
    return r


def source_video(proj):
    from .kind import _video_file
    pdir = OUTPUT / proj
    v = _video_file(pdir, load_json(pdir / 'project.json', {}) or {})
    if not v:
        die(f'{proj}: its video is not downloaded (run `python run.py cut {proj} --check` once, or fetch it)')
    return v


# ---------------------------------------------------------------- 1. the sources

def sources_text(projects):
    """compile/sources.txt: per source video its topics, clips, game-over screens and frame sheets."""
    from . import gameover
    rows = ['# ClipKaro compilation: the source videos. Find every moment that fits the topic in their topic maps,',
            '# transcripts and frame sheets; then write moments.json (format: python run.py compile --help).', '']
    for proj in projects:
        pdir = OUTPUT / proj
        p = load_json(pdir / 'project.json', {}) or {}
        rows += [f"## {proj}", f"# {p.get('title')} | {p.get('channel') or '-'} | {fmt_ts(p.get('duration') or 0)} | "
                 f"{p.get('language') or '-'}",
                 f"# transcript: output/{proj}/transcript/transcript.txt"]
        if (pdir / 'topics.txt').exists():
            rows.append(f"# topic map: output/{proj}/topics.txt")
        sheets = sorted((pdir / 'frames').glob('overview-*.jpg')) if (pdir / 'frames').is_dir() else []
        if sheets:
            rows.append(f"# frame sheets: output/{proj}/frames/overview-*.jpg ({len(sheets)})")
        doc = load_json(pdir / 'topics.json') or {}
        for t in doc.get('topics') or []:
            rows.append(f"  topic {fmt_ts(t['start']).split('.')[0]} {t.get('title')}: {t.get('summary') or ''}"[:200])
        for c in (load_json(pdir / 'clips.json', {}) or {}).get('clips', []):
            rows.append(f"  clip {c.get('id')} {json.dumps(c.get('ranges'))} {c.get('title')}")
        for a, b, title, reason in (gameover.load(pdir) or {}).get('screens', []):
            rows.append(f"  screen {a:.2f}-{b:.2f} {title}" + (f' ({reason})' if reason else ''))
        rows.append('')
    return '\n'.join(rows) + '\n'


def new(name, projects):
    for proj in projects:
        if not (OUTPUT / proj / 'project.json').exists():
            die(f'no project "{proj}" in output/ (use the folder names)')
    pdir = OUTPUT / name
    if (pdir / 'source' / 'video.mp4').exists():
        die(f'{name} is already built; pick another name, or edit its moments.json and --build again')
    (pdir / 'compile').mkdir(parents=True, exist_ok=True)
    (pdir / 'compile' / 'sources.txt').write_text(sources_text(projects), encoding='utf-8')
    if not (pdir / 'moments.json').exists():
        save_json(pdir / 'moments.json', {'topic': '', 'title': '', 'sources': projects, 'moments': []})
    print(f'-> output/{name}/compile/sources.txt: {len(projects)} source video(s)')
    print(f'   next: find the moments, write output/{name}/moments.json, then python run.py compile {name} --check')


# ---------------------------------------------------------------- 2. the check

def read_moments(pdir):
    m = load_json(pdir / 'moments.json')
    if not m or not m.get('moments'):
        die(f'no moments in {pdir.name}/moments.json yet')
    errs = []
    for k, mo in enumerate(m['moments'], 1):
        proj = mo.get('project')
        p = load_json(OUTPUT / str(proj) / 'project.json', {}) if proj else None
        if not p:
            errs.append(f'moment {k}: unknown project "{proj}"')
            continue
        rs = mo.get('ranges') or []
        if not rs or any(not (isinstance(r, list) and len(r) == 2 and 0 <= r[0] < r[1]) for r in rs):
            errs.append(f'moment {k}: "ranges" must be [[start, end], ...] in seconds')
            continue
        if p.get('duration') and rs[-1][1] > p['duration'] + 0.5:
            errs.append(f'moment {k}: ends after the video ({fmt_ts(p["duration"])})')
        if any(r2[0] < r1[1] for r1, r2 in zip(rs, rs[1:])):
            errs.append(f'moment {k}: its ranges must be in time order without overlap')
    seen = []
    for k, mo in enumerate(m['moments'], 1):
        for a, b in mo.get('ranges') or []:
            for j, proj, x, y in seen:
                if proj == mo.get('project') and a < y and x < b and j != k:
                    errs.append(f'moments {j} and {k} share seconds ({fmt_ts(max(a, x))})')
            seen.append((k, mo.get('project'), a, b))
    if errs:
        die('moments.json:\n  ' + '\n  '.join(errs))
    return m


def total_length(m):
    return sum(b - a for mo in m['moments'] for a, b in mo['ranges'])


def check(pdir):
    m = read_moments(pdir)
    out = pdir / 'compile'
    out.mkdir(exist_ok=True)
    for old in out.glob('moment-*.jpg'):
        old.unlink()
    for k, mo in enumerate(m['moments'], 1):
        video = source_video(mo['project'])
        span = sum(b - a for a, b in mo['ranges'])
        n = min(SHEET_FRAMES, max(2, int(span) + 1))
        times, step = [], span / n
        for i in range(n):                      # spread over the moment's ranges, on the source's clock
            t, left = (i + 0.5) * step, None
            for a, b in mo['ranges']:
                if t <= b - a:
                    left = a + t
                    break
                t -= b - a
            times.append(left if left is not None else mo['ranges'][-1][1] - 0.1)
        tiles = []
        for i, t in enumerate(times):
            f = out / f'.m{k:02d}-{i:02d}.jpg'
            run('ffmpeg', '-v', 'error', '-y', '-ss', f'{t:.2f}', '-i', video, '-frames:v', '1', '-vf',
                f"scale=480:-2,drawtext=fontfile=assets/fonts/Montserrat-ExtraBold.ttf:"
                f"text='{fmt_ts(t).split('.')[0].replace(':', chr(92) + ':')}':x=8:y=8:"
                f"fontsize=22:fontcolor=white:box=1:boxcolor=black@0.6", f)
            tiles.append(f)
        cols, args = 4, []
        for f in tiles:
            args += ['-i', f]
        layout = '|'.join(f'{(i % cols) * 480}_{(i // cols) * 270}' for i in range(len(tiles)))
        run('ffmpeg', '-v', 'error', '-y', *args, '-filter_complex',
            ''.join(f'[{i}:v]scale=480:270[t{i}];' for i in range(len(tiles)))
            + ''.join(f'[t{i}]' for i in range(len(tiles))) + f'xstack=inputs={len(tiles)}:layout={layout}:fill=black',
            out / f'moment-{k:02d}.jpg')
        for f in tiles:
            f.unlink()
        print(f"   moment {k:2d}: {mo['project'][:40]} {fmt_ts(mo['ranges'][0][0]).split('.')[0]} "
              f"({span:.1f} s) {mo.get('what') or ''}  -> compile/moment-{k:02d}.jpg")
    total = total_length(m)
    fmt = 'vertical' if total <= LANDSCAPE_FROM else 'vertical AND landscape (longer than 1:30)'
    print(f"-> {len(m['moments'])} moment(s), {total:.1f} s in all: {fmt}")
    print(f'   look at every sheet: is the moment really there, from its start? Then python run.py compile '
          f'{pdir.name} --build')


# ---------------------------------------------------------------- 3. the build

def loudness(video, a, d):
    r = subprocess.run(['ffmpeg', '-hide_banner', '-ss', f'{a:.3f}', '-t', f'{d:.3f}', '-i', str(video), '-vn',
                        '-af', f'loudnorm=I={TARGET_LUFS}:TP=-1.5:print_format=json', '-f', 'null', '-'],
                       capture_output=True, text=True)
    m = re.findall(r'\{[^{}]*"input_i"[^{}]*\}', r.stderr, re.S)
    try:
        v = float(json.loads(m[-1])['input_i']) if m else None
    except (ValueError, KeyError):
        v = None
    return v if v is not None and v > -70 else None


def pieces_of(m, fps):
    """The pieces in play order: {'moment', 'what', 'project', 'a', 'b', 'd', 'frames', 'T'} (b, d frame-exact;
    T counted in whole frames, so one piece ends exactly where the next begins)."""
    out, done = [], 0
    for mi, mo in enumerate(m['moments'], 1):
        for a, b in mo['ranges']:
            n = max(1, round((b - a) * fps))
            out.append({'moment': mi, 'what': mo.get('what') or '', 'project': mo['project'], 'a': a,
                        'b': round(a + n / fps, 4), 'd': n / fps, 'frames': n, 'T': round(done / fps, 4)})
            done += n
    return out, done / fps


def carry_words(pieces):
    """The source projects' (checked) words on the compilation's clock; a word cut by a piece edge is left out."""
    cache, words = {}, []
    for pc in pieces:
        if pc['project'] not in cache:
            cache[pc['project']] = load_json(OUTPUT / pc['project'] / 'transcript' / 'words.json') or []
        for w in cache[pc['project']]:
            if w['s'] >= pc['a'] - 0.02 and w['e'] <= pc['b'] + 0.02:
                words.append(dict(w, s=round(max(w['s'], pc['a']) - pc['a'] + pc['T'], 3),
                                  e=round(min(w['e'], pc['b']) - pc['a'] + pc['T'], 3)))
    return sorted(words, key=lambda w: w['s'])


def carry_screens(pieces):
    from . import gameover
    out = []
    for pc in pieces:
        for a, b, title, reason in (gameover.load(OUTPUT / pc['project']) or {}).get('screens', []):
            if a < pc['b'] and pc['a'] < b:
                out.append([round(max(a, pc['a']) - pc['a'] + pc['T'], 2), round(min(b, pc['b']) - pc['a'] + pc['T'], 2),
                            title, reason])
    return out


def carry_voices(pieces, lines):
    """voices.json for the compilation from the source projects' own (measured on the whole video): each line
    gets the row of the source line it came from: the main voice (the streamer) or another, and how alike it is.
    A short compilation has too few lines to tell voices apart by itself. None when no source has voices."""
    from . import voices
    src, rows, any_src = {}, [], False
    for ln in lines:
        if 's' not in ln:
            rows.append(None)
            continue
        mid = (ln['s'] + ln['e']) / 2
        pc = next((p for p in pieces if p['T'] <= mid < p['T'] + p['d']), None)
        row = None
        if pc:
            if pc['project'] not in src:
                v = voices.load(OUTPUT / pc['project'])
                src[pc['project']] = v
            v = src[pc['project']]
            if v:
                any_src = True
                t = mid - pc['T'] + pc['a']
                hit = next((r for r in v['lines'] if r and r[0] <= t < r[1]), None)
                if hit:
                    row = [round(ln['s'], 2), round(ln['e'], 2), 0 if hit[2] == v['main'] else 1, hit[3]]
        rows.append(row or [round(ln['s'], 2), round(ln['e'], 2), None, None])
    if not any_src:
        return None
    secs = {}
    for r in rows:
        if r and r[2] is not None:
            secs.setdefault(r[2], [0.0, 0])
            secs[r[2]][0] += r[1] - r[0]
            secs[r[2]][1] += 1
    return {'v': voices.VOICES_V, 'main': 0, 'from': 'the source projects',
            'voices': {str(k): {'seconds': round(x[0], 1), 'lines': x[1]} for k, x in sorted(secs.items())},
            'lines': rows}


def at(pieces, proj, t):
    """A second of a source video on the compilation's clock (None when no piece holds it)."""
    for pc in pieces:
        if pc['project'] == proj and pc['a'] <= t < pc['b']:
            return round(t - pc['a'] + pc['T'], 2)
    return None


def same_cam(a, b, width):
    if not a or not b:
        return a == b
    return all(abs(a[k] - b[k]) <= 0.03 * width for k in ('x', 'y', 'w', 'h'))


def build(pdir):
    from .fetch import write_transcript
    from . import gameover, voices
    m = read_moments(pdir)
    first = m['moments'][0]['project']
    base = load_json(OUTPUT / first / 'project.json', {}) or {}
    from .resolve import rate_of                   # the stream's own rate (60/1, 30000/1001), not the average
    info = probe(source_video(first))
    rate = rate_of(source_video(first))
    fps, W, H = float(rate), info['width'], info['height']
    pieces, T = pieces_of(m, fps)
    warns = []
    for proj in dict.fromkeys(pc['project'] for pc in pieces):
        p = load_json(OUTPUT / proj / 'project.json', {}) or {}
        if not same_cam(p.get('facecam'), base.get('facecam'), W):
            warns.append(f'{proj}: its webcam is somewhere else than in {first}: the webcam layout follows {first} '
                         f'(cut --layout crop turns it off)')
        if (p.get('language') or '') != (base.get('language') or ''):
            warns.append(f'{proj}: another language ({p.get("language")}) than {first} ({base.get("language")})')
    work = pdir / 'compile' / 'pieces'
    work.mkdir(parents=True, exist_ok=True)
    gains = {}
    for mi, mo in enumerate(m['moments'], 1):     # one gain a moment: its pieces stay alike
        video = source_video(mo['project'])
        vals = [x for x in (loudness(video, a, b - a) for a, b in mo['ranges']) if x is not None]
        lvl = sum(vals) / len(vals) if vals else TARGET_LUFS
        gains[mi] = max(-MAX_GAIN, min(MAX_GAIN, TARGET_LUFS - lvl))
    listing = []
    for k, pc in enumerate(pieces, 1):
        src = source_video(pc['project'])
        sinfo = probe(src)
        fit = '' if (sinfo['width'], sinfo['height']) == (W, H) else \
            f'scale={W}:{H}:force_original_aspect_ratio=decrease,pad={W}:{H}:(ow-iw)/2:(oh-ih)/2,setsar=1,'
        n, d = pc['frames'], pc['d']
        f = work / f'p{k:03d}.mkv'
        run('ffmpeg', '-v', 'error', '-y', '-ss', f"{pc['a']:.3f}", '-i', src, '-t', f'{d + 0.5:.3f}', '-filter_complex',
            f"[0:v]{fit}fps={rate.numerator}/{rate.denominator},tpad=stop_mode=clone:stop_duration=1,trim=end_frame={n},setpts=PTS-STARTPTS[v];"
            f"[0:a]aresample=48000,volume={gains[pc['moment']]:.2f}dB,alimiter=limit=0.89:level=disabled:attack=5:"
            f"release=80,apad=whole_dur={d:.6f},atrim=end_sample={round(n * 48000 / fps)},asetpts=PTS-STARTPTS[a]",
            '-map', '[v]', '-map', '[a]', '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '15', '-pix_fmt', 'yuv420p',
            '-g', str(round(fps)), '-c:a', 'pcm_s16le', '-ac', '2', f)
        listing.append(f"file '{f.name}'")
        print(f'   piece {k}/{len(pieces)}', flush=True)
    (work / 'list.txt').write_text('\n'.join(listing) + '\n', encoding='utf-8')
    (pdir / 'source').mkdir(exist_ok=True)
    video = pdir / 'source' / 'video.mp4'
    run('ffmpeg', '-v', 'error', '-y', '-f', 'concat', '-safe', '0', '-i', work / 'list.txt', '-c:v', 'copy',
        '-c:a', 'aac', '-b:a', '192k', '-movflags', '+faststart', video)
    run('ffmpeg', '-v', 'error', '-y', '-i', video, '-vn', '-c:a', 'copy', pdir / 'source' / 'audio.mp4')
    run('ffmpeg', '-v', 'error', '-y', '-i', video, '-vn', '-ac', '1', '-ar', '16000', '-c:a', 'pcm_s16le',
        pdir / 'source' / 'audio16k.wav')
    shutil.rmtree(work, ignore_errors=True)

    project = {k: base[k] for k in COPY_KEYS if k in base}
    title = m.get('title') or m.get('topic') or pdir.name
    project.update(source=base.get('channel_url') or base.get('source'), id=pdir.name, audio='audio.mp4',
                   title=f"{title} (compilation of {len({pc['project'] for pc in pieces})} videos)",
                   slug=pdir.name, duration=round(T, 3), chapters=[], breaks=[],
                   compilation=[{k: pc[k] for k in ('moment', 'what', 'project', 'a', 'b', 'T')} for pc in pieces])
    save_json(pdir / 'project.json', project)
    if (OUTPUT / first / 'brand.json').exists():
        shutil.copyfile(OUTPUT / first / 'brand.json', pdir / 'brand.json')
    table = {}
    for proj in dict.fromkeys(pc['project'] for pc in pieces):       # the Roman spellings already filled in
        for k, v in ((load_json(OUTPUT / proj / 'romanize.json') or {}).items()):
            if isinstance(v, str) and v and k not in table:
                table[k] = v
    if table:
        save_json(pdir / 'romanize.json', table)
    (pdir / 'transcript').mkdir(exist_ok=True)
    save_json(pdir / 'transcript' / 'gameover.json', {'v': gameover.GAMEOVER_V, 'screens': carry_screens(pieces),
                                                      'from': 'the source projects'})
    words = carry_words(pieces)
    write_transcript(pdir, words, project)
    v = carry_voices(pieces, load_json(pdir / 'transcript' / 'sentences.json') or [])
    if v:                                          # who speaks each line: game lines lose their captions as usual
        save_json(pdir / 'transcript' / 'voices.json', v)
        write_transcript(pdir, words, project)     # again, now with the "(other voice)" notes
    else:
        voices.scan(pdir, quiet=True)
    ranges = [[pc['T'], round(pc['T'] + pc['frames'] / fps, 4)] for pc in pieces]
    old = load_json(pdir / 'clips.json', {}) or {}
    clip = (old.get('clips') or [{}])[0]
    clip.update({'id': 1, 'from': 'compilation', 'title': clip.get('title') or title, 'ranges': ranges,
                 'keep_whole': ranges, 'compilation': True})
    save_json(pdir / 'clips.json', {'clips': [clip]})
    save_json(pdir / 'compile' / 'pieces.json', pieces)
    for w in warns:
        print(f'   ! {w}')
    print(f'-> {pdir.name}: {len(pieces)} pieces from {len(m["moments"])} moments, {T:.1f} s, {len(words)} words carried over')
    print(f"   clips.json has the clip (every piece kept whole: no pause cuts). Next: write its caption and post texts "
          f"(sfx / emoji times: python run.py compile {pdir.name} --at <project> <seconds>), then captions, cut, edit, "
          f"qa, post" + (', and the landscape copy (longer than 1:30): python run.py landscape ' + pdir.name
                         if T > LANDSCAPE_FROM else ''))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('name', help='the compilation project (a new folder in output/)')
    ap.add_argument('--from', dest='sources', default=None, help='comma list of source project folders')
    ap.add_argument('--check', action='store_true', help='check moments.json and make the frame sheets')
    ap.add_argument('--build', action='store_true', help='build the compilation project')
    ap.add_argument('--at', nargs=2, metavar=('PROJECT', 'SECONDS'), help='a source second on the compilation clock')
    a = ap.parse_args()
    from .common import slugify
    name = slugify(a.name, 60) if a.sources else a.name
    pdir = OUTPUT / name
    if a.sources:
        new(name, [x.strip() for x in a.sources.split(',') if x.strip()])
    elif a.check:
        check(pdir)
    elif a.build:
        build(pdir)
    elif a.at:
        pieces = load_json(pdir / 'compile' / 'pieces.json')
        if not pieces:
            die('not built yet: --build first')
        t = at(pieces, a.at[0], float(a.at[1]))
        print(t if t is not None else 'that second is in no piece of the compilation')
    else:
        die('say what to do: --from (new), --check, --build or --at')


if __name__ == '__main__':
    main()
