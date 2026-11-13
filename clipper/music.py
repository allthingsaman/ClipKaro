"""Background music: your own tracks, sorted by mood, quietly under the voice.

    python run.py music                              # every mood, how many tracks it has, where the folder is
    python run.py music add "C:/Downloads/lofi.mp3" chill      # add a track (or a folder of them) to a mood
    python run.py music remove lofi.mp3              # take one out again

Your tracks live in the `music` folder inside the ClipKaro folder, one folder per mood: music/chill/,
music/upbeat/, music/hype/ ... (`python run.py music` creates them; a new folder is a new mood). Claude
picks a mood for a clip that suits one (clips.json "music": "chill"); the edit plays a track of that
mood from its start, about 10 dB under the voice (a -25 LUFS bed), dipping further while someone
speaks (ducking), fading in and out. Without tracks, clips have no music, as before.

ClipKaro ships no music: songs are copyrighted, and YouTube, Instagram and Facebook mute or block clips
with music you have no right to use. Free sources that allow it: the YouTube Audio Library (for
YouTube; check each track's licence before posting elsewhere), Pixabay Music, or a paid library such as
Epidemic Sound.
"""
import argparse
import hashlib
import shutil

from .common import ROOT, die

MUSIC = ROOT / 'music'
EXTS = ('.mp3', '.wav', '.m4a', '.ogg', '.flac', '.aac')
MOODS = {
    'chill': 'calm talk, explanations, a relaxed story (lo-fi, soft beats)',
    'upbeat': 'light, positive, quick (pop, happy beats)',
    'hype': 'gaming wins, sport, big energy (trap, EDM, rock)',
    'suspense': 'mystery, tension, true crime (dark ambient, pulses)',
    'emotional': 'sad or touching stories (piano, strings)',
    'funny': 'comedy, awkward moments (quirky, playful)',
    'inspiring': 'motivation, success stories (cinematic, uplifting)',
}
BED_LUFS = -21            # the music's loudness before ducking (the voice sits around -14 to -16)


def tracks(mood=None):
    """{mood: [paths]} of every track (or only one mood's)."""
    out = {}
    if not MUSIC.exists():
        return out
    for d in sorted(x for x in MUSIC.iterdir() if x.is_dir() and not x.name.startswith('.')):
        if mood and d.name.lower() != mood:
            continue
        files = [p for p in sorted(d.rglob('*')) if p.suffix.lower() in EXTS]
        if files:
            out[d.name.lower()] = files
    return out


def pick(mood, salt=''):
    """A track of the mood (varied by `salt`, a clip's name), or None."""
    files = tracks(mood).get(str(mood or '').lower())
    if not files:
        return None
    return files[int(hashlib.md5(salt.encode()).hexdigest(), 16) % len(files)]


GUIDE = """Background music for ClipKaro, sorted by mood: one folder per mood.

Put a track in the folder of its mood (any file name: .mp3, .wav, .m4a, .ogg, .flac):
{moods}
A new folder (for example "romantic") becomes a new mood. Or, from the ClipKaro folder:
    python run.py music add "<path to the track>" chill
or just tell Claude: "add this music as chill: <path>".

Use only music you are allowed to use: YouTube, Instagram and Facebook mute or block clips with
copyrighted songs. Free sources: the YouTube Audio Library (check each track's licence), Pixabay Music.
"""


def make_folders():
    MUSIC.mkdir(exist_ok=True)
    for m in MOODS:
        (MUSIC / m).mkdir(exist_ok=True)
    lines = ''.join(f'    music/{m}/  {desc}\n' for m, desc in MOODS.items())
    (MUSIC / 'README.txt').write_text(GUIDE.format(moods=lines), encoding='utf-8')


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest='cmd')
    ad = sub.add_parser('add', help='add tracks (or a folder of them) to a mood')
    ad.add_argument('paths', nargs='+', help='music files or folders, then the mood as the last word')
    rm = sub.add_parser('remove', help='take a track out')
    rm.add_argument('name', help='its file name, as `python run.py music` lists it')
    a = ap.parse_args()
    make_folders()
    from pathlib import Path
    from .common import probe
    if a.cmd == 'add':
        if len(a.paths) < 2:
            die('give the track(s) and then the mood, e.g.  python run.py music add "lofi.mp3" chill')
        *srcs, mood = a.paths
        mood = mood.strip().lower()
        if not mood.replace('-', '').replace('_', '').isalnum():
            die(f'"{mood}" is not a mood name: use one word, e.g. chill, hype, suspense')
        todo = []
        for s in srcs:
            p = Path(s.strip().strip('"\'')).expanduser()
            if p.is_dir():
                todo += [x for x in sorted(p.rglob('*')) if x.suffix.lower() in EXTS]
            elif p.exists():
                todo.append(p)
            else:
                die(f'not found: {p}')
        (MUSIC / mood).mkdir(exist_ok=True)
        n = 0
        for p in todo:
            if p.suffix.lower() not in EXTS:
                print(f'   skipped {p.name}: not a music file ({", ".join(EXTS)})')
                continue
            if not (probe(p).get('duration') or 0) > 5:
                print(f'   skipped {p.name}: shorter than 5 seconds (a sound effect? `python run.py sfx add`)')
                continue
            shutil.copy2(p, MUSIC / mood / p.name)
            n += 1
            print(f'   + {mood}/{p.name}')
        print(f"-> {n} track(s) added to {mood}{'' if mood in MOODS else ' (a new mood)'}")
    elif a.cmd == 'remove':
        hits = [p for files in tracks().values() for p in files if p.name == a.name]
        if not hits:
            die(f'no track is called "{a.name}" (`python run.py music` lists them)')
        for p in hits:
            p.unlink()
            print(f'   - {p.relative_to(MUSIC)}')
    have = tracks()
    print(f'\nYour music: {MUSIC}   (one folder per mood; any file name)')
    for m, desc in MOODS.items():
        print(f"   {m:<10} {len(have.get(m, [])):>3} track(s)   {desc}")
    for m in sorted(set(have) - set(MOODS)):
        print(f"   {m:<10} {len(have[m]):>3} track(s)   (your own mood)")
    print('Add one:  python run.py music add "<path to the track>" chill   (or tell Claude: "add this music as chill: <path>")')


if __name__ == '__main__':
    main()
