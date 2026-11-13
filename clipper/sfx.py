"""Sound effects: the built-in whooshes, and your own sounds sorted by mood.

    python run.py sfx                            # every mood, how many sounds it has, where the folder is
    python run.py sfx add "C:/Downloads/boom.mp3" shock     # add a sound (or several files) to a mood
    python run.py sfx add "C:/Downloads/my sounds" funny    # every sound in that folder
    python run.py sfx remove boom.mp3            # take one of your sounds out again

Your own sounds live in the `sounds` folder inside the ClipKaro folder, one folder per mood:
sounds/shock/, sounds/funny/, sounds/fear/ ... (`python run.py sfx` creates them). Any file name
works inside a mood folder. A file dropped straight into `sounds/` works too when its name holds the
mood word ("shock-vine-boom.mp3"). A folder with a new name (sounds/romantic/) becomes a new mood.
Claude marks the moments in a clip that call for one (clips.json "sfx": [[seconds, "shock"]]); the edit
puts the loudest point of the sound right there, under the voice. Without sounds in a mood, nothing
is played for it.

Built in (assets/sfx/, shipped with ClipKaro): whoosh, hit and click, which the edit uses on its zooms.
A file that holds several sounds (a "pack") is split at the silences, and each part becomes a variant.
Use only sounds you are allowed to use: free sound sites such as Pixabay, Mixkit or the YouTube Audio
Library give permission for videos; a sound from someone else's video usually doesn't.
"""
import argparse
import hashlib
import shutil
import subprocess

import numpy as np

from .common import ASSETS, ROOT, die, load_json, save_json

SFX_DIR = ASSETS / 'sfx'                 # built in
MINE = ROOT / 'sounds'                   # the user's own, by mood (gitignored)
CATALOG = MINE / '.catalog.json'
SR = 48000
EXTS = ('.mp3', '.wav', '.ogg', '.m4a', '.flac', '.aac')
ROLES = {'whoosh': ('whoosh', 'swoosh', 'swish', 'swipe'),
         'hit': ('hit', 'impact', 'punch', 'thud'), 'click': ('click', 'pop', 'tick')}
# the moods Claude can mark, with words that give a file away and what each is for
MOODS = {
    'attention': (('attention', 'riser', 'ding', 'notif', 'alert', 'bell'),
                  'grab attention: a riser, a ding, a notification (a new point, "listen to this")'),
    'shock': (('shock', 'boom', 'vine', 'bass', 'drop', 'dun'),
              'a shocking line or reveal: a deep boom, a bass drop, "dun dun"'),
    'fear': (('fear', 'horror', 'scary', 'creepy', 'suspense', 'tension', 'drone'),
             'something scary or tense: a suspense sting, a horror hit'),
    'funny': (('funny', 'boing', 'cartoon', 'honk', 'bruh', 'scratch', 'laugh'),
              'a punchline or an awkward moment: a boing, a record scratch, "bruh"'),
    'sad': (('sad', 'violin', 'emotional', 'sorrow'), 'a sad or emotional moment: a soft piano or violin sting'),
    'hype': (('hype', 'airhorn', 'cheer', 'crowd', 'wow'), 'a big win or hype: an air horn, a crowd cheer'),
    'reveal': (('reveal', 'tada', 'magic', 'sparkle', 'success'), 'an answer or a result: a ta-da, a sparkle'),
    'fail': (('fail', 'wrong', 'buzzer', 'trombone', 'error'), 'a mistake or a fail: a wrong buzzer, a sad trombone'),
    'money': (('money', 'cash', 'coin', 'ching', 'register'), 'money talk: a cash register, coins'),
}
GAIN = {'shock': -11, 'funny': -12, 'fail': -12, 'money': -12, 'hype': -13, 'attention': -14, 'reveal': -14,
        'fear': -15, 'sad': -16}
MAX_LEN = 2.5                            # a mood sound plays at most this long (it fades out)


def role_of(name, folder=None):
    """The role of a sound: its mood folder's name, else a word in its file name."""
    if folder:
        return folder.lower()
    n = name.lower()
    for role, (keys, _) in MOODS.items():
        if any(k in n for k in keys):
            return role
    for role, keys in ROLES.items():
        if any(k in n for k in keys):
            return role
    return None


def decode(path):
    r = subprocess.run(['ffmpeg', '-v', 'error', '-i', str(path), '-ac', '1', '-ar', str(SR), '-f', 'f32le', '-'],
                       capture_output=True)
    return np.frombuffer(r.stdout, dtype=np.float32)


def segments(x, floor_db=-42, min_gap=0.25, min_len=0.15):
    """Split a file into separate sounds at silences; return [(start, end, peak)] in seconds."""
    hop = SR // 100
    n = len(x) // hop
    if n == 0:
        return []
    rms = np.sqrt(np.mean(x[:n * hop].reshape(n, hop) ** 2, axis=1) + 1e-12)
    db = 20 * np.log10(rms / (rms.max() + 1e-12))
    on = db > floor_db
    segs, i = [], 0
    while i < n:
        if not on[i]:
            i += 1
            continue
        j = i
        quiet = 0
        while j < n and quiet < min_gap * 100:
            quiet = quiet + 1 if not on[j] else 0
            j += 1
        end = j - quiet
        if (end - i) / 100 >= min_len:
            pk = i + int(np.argmax(rms[i:end]))
            segs.append((i / 100, end / 100, pk / 100))
        i = j
    return segs


def files():
    """[(path, folder or None)] of every sound: built in, then the user's (straight in sounds/ or in a mood folder)."""
    out = [(p, None) for p in sorted(SFX_DIR.glob('*')) if p.suffix.lower() in EXTS] if SFX_DIR.exists() else []
    if MINE.exists():
        out += [(p, None) for p in sorted(MINE.glob('*')) if p.suffix.lower() in EXTS]
        for d in sorted(x for x in MINE.iterdir() if x.is_dir() and not x.name.startswith('.')):
            out += [(p, d.name) for p in sorted(d.rglob('*')) if p.suffix.lower() in EXTS]
    return out


def scan():
    found = files()
    sig = [[str(p.relative_to(ROOT)), p.stat().st_size] for p, _ in found]
    cat = load_json(CATALOG)
    if cat and cat.get('sig') == sig:
        return cat
    items = []
    for p, folder in found:
        role = role_of(p.stem, folder)
        if not role:
            continue
        x = decode(p)
        segs = segments(x) if folder is None and role in ROLES else [(0.0, len(x) / SR, None)] if len(x) else []
        for k, (a, b, pk) in enumerate(segs[:12]):
            part = x[int(a * SR):int(b * SR)]
            if not len(part):
                continue
            amp = float(np.abs(part).max() or 1e-6)
            if pk is None:                       # one sound per file: its loudest point
                pk = a + int(np.argmax(np.abs(part))) / SR
            items.append({'file': p.name, 'path': str(p.relative_to(ROOT)), 'role': role, 'variant': k,
                          'start': round(a, 2), 'length': round(b - a, 2), 'peak': round(pk - a, 2),
                          'norm_db': round(-20 * np.log10(amp), 2)})
    cat = {'sig': sig, 'items': items}
    MINE.mkdir(exist_ok=True)
    save_json(CATALOG, cat)
    return cat


def pick(role, prefer_len=None, exclude=(), salt=''):
    """Choose a sound of a role, preferring a length close to prefer_len (seconds); among equals, `salt`
    (a clip's name) varies the choice, so clips don't all get the same sound."""
    items = [i for i in scan()['items'] if i['role'] == role and (i['file'], i['variant']) not in exclude]
    if not items:
        return None
    if prefer_len:
        items.sort(key=lambda i: abs(i['length'] - prefer_len))
        return items[0]
    return items[int(hashlib.md5(salt.encode()).hexdigest(), 16) % len(items)]


def path_of(cue):
    """The file of a sound cue (catalogs from before held only the file name of a built-in sound)."""
    return ROOT / cue['path'] if cue.get('path') else SFX_DIR / cue['file']


def moods_available():
    """{mood: number of sounds} for every mood that has sounds (the built-in roles left out)."""
    out = {}
    for it in scan()['items']:
        if it['role'] not in ROLES:
            out[it['role']] = out.get(it['role'], 0) + 1
    return out


GUIDE = """Your own sound effects for ClipKaro, sorted by mood: one folder per mood.

Put a sound in the folder of its mood (any file name: .mp3, .wav, .m4a, .ogg, .flac):
{moods}
A new folder (for example "romantic") becomes a new mood. Or, from the ClipKaro folder:
    python run.py sfx add "<path to the sound>" shock
or just tell Claude: "add this sound as shock: <path>".

Use only sounds you are allowed to use in videos (Pixabay, Mixkit, the YouTube Audio Library and
similar sites give permission; a sound taken from someone else's video usually is not allowed).
"""


def make_folders():
    MINE.mkdir(exist_ok=True)
    for m in MOODS:
        (MINE / m).mkdir(exist_ok=True)
    lines = ''.join(f'    sounds/{m}/  {desc}\n' for m, (_, desc) in MOODS.items())
    (MINE / 'README.txt').write_text(GUIDE.format(moods=lines), encoding='utf-8')


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest='cmd')
    ad = sub.add_parser('add', help='add sound files (or a folder of them) to a mood')
    ad.add_argument('paths', nargs='+', help='sound files or folders, then the mood as the last word')
    rm = sub.add_parser('remove', help='take one of your sounds out')
    rm.add_argument('name', help='its file name, as `python run.py sfx` lists it')
    a = ap.parse_args()
    make_folders()

    if a.cmd == 'add':
        if len(a.paths) < 2:
            die('give the sound file(s) and then the mood, e.g.  python run.py sfx add "boom.mp3" shock')
        *srcs, mood = a.paths
        mood = mood.strip().lower()
        if not mood.replace('-', '').replace('_', '').isalnum():
            die(f'"{mood}" is not a mood name: use one word, e.g. shock, funny, fear')
        from pathlib import Path
        todo = []
        for s in srcs:
            p = Path(s.strip().strip('"\'')).expanduser()
            if p.is_dir():
                todo += [x for x in sorted(p.rglob('*')) if x.suffix.lower() in EXTS]
            elif p.exists():
                todo.append(p)
            else:
                die(f'not found: {p}')
        dest = MINE / mood
        dest.mkdir(exist_ok=True)
        added = 0
        for p in todo:
            if p.suffix.lower() not in EXTS:
                print(f'   skipped {p.name}: not a sound file ({", ".join(EXTS)})')
                continue
            if len(decode(p)) < SR * 0.05:
                print(f'   skipped {p.name}: no sound in it')
                continue
            shutil.copy2(p, dest / p.name)
            added += 1
            print(f'   + {mood}/{p.name}')
        new = '' if mood in MOODS else ' (a new mood)'
        print(f'-> {added} sound(s) added to {mood}{new}: {dest}')
    elif a.cmd == 'remove':
        hits = [p for p, folder in files() if folder and p.name == a.name]
        if not hits:
            die(f'no sound of yours is called "{a.name}" (`python run.py sfx` lists them)')
        for p in hits:
            p.unlink()
            print(f'   - {p.relative_to(MINE)}')

    cat = scan()
    counts = {}
    for it in cat['items']:
        counts.setdefault(it['role'], set()).add(it['path'])
    print(f'\nYour sounds: {MINE}   (one folder per mood; any file name)')
    for m, (_, desc) in MOODS.items():
        n = len(counts.get(m, ()))
        print(f"   {m:<10} {n:>3} sound(s)   {desc}")
    for m in sorted(set(counts) - set(MOODS) - set(ROLES)):
        print(f"   {m:<10} {len(counts[m]):>3} sound(s)   (your own mood)")
    print('Built in (used on the zooms): ' + ', '.join(f"{r} {len(counts.get(r, ()))}" for r in ROLES))
    print('Add one:  python run.py sfx add "<path to the sound>" shock   (or tell Claude: "add this sound as shock: <path>")')


if __name__ == '__main__':
    main()
