"""The review studio's helper (v2.10): one finished clip's facts, and the owner's changes to it, re-rendered.

PostKaro's Studio page calls it (the owner clicks, nothing is typed); it works from a terminal too:

    python run.py studio <project> --clip 3               JSON: start and end (and the words around them), the
                                                          captions, framing, emojis and sounds of clip 3
    python run.py studio <project> --clip 3 --apply F     apply the changes in F (a JSON file, or - for stdin), then
                                                          cut, edit and check that one clip again
    python run.py studio <project> --clip 3 --undo        put the clip back as it was before the last change, and
                                                          render it again

The changes (any of them):
    {"start": 123.4, "end": 170.2,                        the clip's first and last second in the video
     "words": [{"i": 1234, "text": "Pakistan"},           a caption word fixed (its index in words.json) ...
               {"i": 1240, "hide": true}, {"i": 7, "show": true}],     ... hidden, or shown again
     "framing": "auto" | "left" | "right" | "center" | "split" | "full",   the whole clip's framing
     "emoji_off": ["billion"],                            the emojis switched off (by their word), the rest on
     "moods_off": [3090.0],                               the sound effects switched off (by their second), the rest on
     "whooshes": false}                                   the automatic whooshes on or off

It writes the same clips.json fields Claude writes ("ranges", "framing", "emoji", "sfx"; a switched-off emoji or
sound waits in "emoji_off" / "sfx_off", so it can come back), fixes words like `fixword --at` (or marks them
unsure: no caption), then runs cut, edit and qa for that clip only (and the landscape copy, when it has one). No
Claude usage. Every --apply first saves the clip as it was (.studio/<clip>/), so --undo can bring it back.
Progress lines start with "STEP"; the last line is "RESULT {json}".
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

from .common import die, load_json, project_dir, save_json

FRAMINGS = ('auto', 'left', 'right', 'center', 'split', 'full')
EDGE_BEFORE, EDGE_AFTER = 15.0, 6.0       # seconds of words shown around the start (before, after) and the end


def find_clip(pdir, cid):
    picks = load_json(pdir / 'clips.json', {}) or {}
    for k, c in enumerate(picks.get('clips', []), 1):
        if int(c.get('id', k)) == cid:
            return picks, k - 1, c
    die(f'no clip {cid} in {pdir.name}/clips.json')


def meta_of(pdir, cid):
    for f in sorted((pdir / 'clips').glob(f'{cid:02d}-*.json')):
        m = load_json(f)
        if m and int(m.get('id', -1)) == cid:
            return m
    return None


def to_source(parts, t):
    """A second of the cut clip -> the same moment in the video."""
    at = 0.0
    for a, b in parts:
        if t < at + (b - a) + 1e-6:
            return a + max(0.0, t - at)
        at += b - a
    return parts[-1][1] if parts else t


def to_clip(parts, s):
    """A second of the video -> the cut clip's clock, or None when it was cut out."""
    at = 0.0
    for a, b in parts:
        if a - 1e-6 <= s <= b + 1e-6:
            return round(at + s - a, 2)
        at += b - a
    return None


def nearest_word(words, s, within=0.3):
    import bisect
    starts = [w['s'] for w in words]
    j = bisect.bisect_left(starts, s)
    best = min((k for k in (j - 1, j, j + 1) if 0 <= k < len(words)), key=lambda k: abs(words[k]['s'] - s), default=None)
    return best if best is not None and abs(words[best]['s'] - s) <= within else None


def framing_now(clip):
    fr, sf = clip.get('framing') or [], clip.get('show_full') or []
    a, b = clip['ranges'][0][0], clip['ranges'][-1][1]
    if not fr and not sf:
        return 'auto'
    if len(fr) == 1 and not sf and fr[0][0] <= a + 0.05 and fr[0][1] >= b - 0.05:
        return str(fr[0][2])
    if len(sf) == 1 and not fr and sf[0][0] <= a + 0.05 and sf[0][1] >= b - 0.05:
        return 'full'
    return 'custom'


def info(pdir, cid):
    picks, _, clip = find_clip(pdir, cid)
    meta = meta_of(pdir, cid)
    words = load_json(pdir / 'transcript' / 'words.json') or []
    if not meta:
        die(f'clip {cid} is not cut yet: python run.py cut {pdir.name} --clips {cid}')
    parts = meta['parts']
    name = meta['name']
    plan = load_json(pdir / '.work' / f'{name}.plan.json') or {}
    start, end = clip['ranges'][0][0], clip['ranges'][-1][1]
    edge = lambda a, b: [{'i': k, 'w': w['w'], 's': w['s'], 'e': w['e'], 'hidden': bool(w.get('unsure'))}  # noqa: E731
                         for k, w in enumerate(words) if a <= w['s'] <= b]
    groups = []
    for g in plan.get('captions') or []:
        row = []
        for w in g.get('words') or []:
            i = nearest_word(words, to_source(parts, w['s']))
            row.append({'text': w.get('text', ''), 'i': i, 'heard': words[i]['w'] if i is not None else None,
                        't': round(w['s'], 2)})
        groups.append({'t': round(g.get('start', row[0]['t'] if row else 0), 2), 'words': row})
    hidden = [{'i': k, 'w': w['w'], 't': to_clip(parts, w['s'])} for k, w in enumerate(words)
              if w.get('unsure') and any(a <= w['s'] < b for a, b in parts)]
    edited = next((f for f in sorted((pdir / 'edited').glob(f'{name}.mp4'))), None) if (pdir / 'edited').is_dir() else None
    layout = meta.get('layout') or ('horizontal' if any(s.get('mode') == 'horizontal' for s in meta.get('shots', []))
                                    else 'crop')
    return {
        'project': pdir.name, 'clip': cid, 'name': name, 'title': clip.get('title'), 'duration': meta['duration'],
        'layout': layout, 'ranges': clip['ranges'], 'start': start, 'end': end, 'pieces': len(parts),
        'video_duration': (load_json(pdir / 'project.json', {}) or {}).get('duration'),
        'edges': {'start': edge(start - EDGE_BEFORE, start + EDGE_AFTER), 'end': edge(end - EDGE_AFTER, end + EDGE_BEFORE)},
        'captions': groups, 'hidden': hidden,
        'framing': framing_now(clip), 'framings': [] if layout in ('facecam', 'horizontal') else list(FRAMINGS),
        'emoji': [{'word': e[0], 'char': e[1], 'on': True} for e in clip.get('emoji') or []]
                 + [{'word': e[0], 'char': e[1], 'on': False} for e in clip.get('emoji_off') or []],
        'moods': [{'t': m[0], 'mood': m[1], 'clip_t': to_clip(parts, m[0]), 'on': True} for m in clip.get('sfx') or []]
                 + [{'t': m[0], 'mood': m[1], 'clip_t': to_clip(parts, m[0]), 'on': False} for m in clip.get('sfx_off') or []],
        'whooshes': clip.get('whooshes', True) is not False,
        'edited': str(edited) if edited else None, 'cut': str(pdir / 'clips' / meta['file']),
        'updated': os.path.getmtime(edited) if edited else None,
        'can_undo': (pdir / '.studio' / str(cid) / 'clip.json').exists(),
        'busy': lock_owner(pdir) is not None,
    }


# ---------------------------------------------------------------- changes

def change_clip(clip, ch, words):
    """The clip entry with the changes (a new dict) and the words (a new list); raises ValueError on a bad change."""
    from .fixword import replace_at
    c = json.loads(json.dumps(clip))
    rs = c['ranges']
    if 'start' in ch:
        s = float(ch['start'])
        if not 0 <= s < rs[0][1] - 1.0:
            raise ValueError('the new start must be at least 1 s before the end of the first piece')
        rs[0][0] = round(s, 2)
    if 'end' in ch:
        e = float(ch['end'])
        if not e > rs[-1][0] + 1.0:
            raise ValueError('the new end must be at least 1 s after the start of the last piece')
        rs[-1][1] = round(e, 2)
    total = sum(b - a for a, b in rs)
    if not 3.0 <= total <= 600.0:
        raise ValueError(f'the clip would be {total:.0f} s long')
    if 'framing' in ch:
        f = ch['framing']
        if f not in FRAMINGS:
            raise ValueError(f'framing must be one of {", ".join(FRAMINGS)}')
        c.pop('framing', None)
        c.pop('show_full', None)
        if f != 'auto':
            c['framing'] = [[rs[0][0], rs[-1][1], f]]
    if 'emoji_off' in ch:
        off = set(ch['emoji_off'] or [])
        every = (c.get('emoji') or []) + (c.get('emoji_off') or [])
        c['emoji'] = [e for e in every if e[0] not in off]
        c['emoji_off'] = [e for e in every if e[0] in off]
        if not c['emoji_off']:
            c.pop('emoji_off')
    if 'moods_off' in ch:
        off = {round(float(t), 2) for t in ch['moods_off'] or []}
        every = (c.get('sfx') or []) + (c.get('sfx_off') or [])
        c['sfx'] = [m for m in every if round(float(m[0]), 2) not in off]
        c['sfx_off'] = [m for m in every if round(float(m[0]), 2) in off]
        if not c['sfx_off']:
            c.pop('sfx_off')
    if 'whooshes' in ch:
        if ch['whooshes']:
            c.pop('whooshes', None)
        else:
            c['whooshes'] = False
    w = list(words)
    for fix in sorted(ch.get('words') or [], key=lambda x: -int(x['i'])):   # from the end: indexes stay right
        i = int(fix['i'])
        if not 0 <= i < len(w):
            raise ValueError(f'no word {i}')
        if fix.get('hide'):
            w[i] = dict(w[i], unsure=True)
        elif fix.get('show'):
            w[i] = {k: v for k, v in w[i].items() if k != 'unsure'}
        elif str(fix.get('text') or '').strip():
            w, _ = replace_at(w, i, 1, str(fix['text']).strip())
        else:
            raise ValueError(f'word {i}: give the right word, or hide it')
    return c, w


# ---------------------------------------------------------------- one render at a time

LOCK_STALE_S = 1800        # a lock this old is left over from a render that died


def lock_owner(pdir):
    """The process id rendering a clip of this video, or None. On Windows os.kill(pid, 0) would send Ctrl+C,
    so there only the lock's age counts."""
    f = pdir / '.studio' / 'lock'
    try:
        pid, since = (float(x) for x in f.read_text().split())
    except (OSError, ValueError):
        return None
    if time.time() - since > LOCK_STALE_S:
        return None
    if os.name != 'nt':
        try:
            os.kill(int(pid), 0)
        except (OSError, ProcessLookupError):
            return None
    return int(pid)


def lock(pdir):
    if lock_owner(pdir):
        die('another clip of this video is being rendered; try again when it is done')
    (pdir / '.studio').mkdir(exist_ok=True)
    (pdir / '.studio' / 'lock').write_text(f'{os.getpid()} {time.time():.0f}')


def unlock(pdir):
    try:
        (pdir / '.studio' / 'lock').unlink()
    except OSError:
        pass


def render(pdir, cid):
    """cut, edit and qa for one clip (and its landscape copy, when there is one). True when it went through."""
    meta = meta_of(pdir, cid)
    land = meta and (pdir / 'edited' / f"{meta['name']}-landscape.mp4").exists()
    steps = [('cut', 'clipper.cut'), ('edit', 'clipper.edit'), ('check', 'clipper.qa')] + \
        ([('landscape copy', 'clipper.landscape')] if land else [])
    for label, mod in steps:
        print(f'STEP {label}', flush=True)
        r = subprocess.run([sys.executable, '-m', mod, pdir.name, '--clips', str(cid)], capture_output=True,
                           text=True, encoding='utf-8', errors='replace')
        tail = [ln for ln in (r.stdout + r.stderr).splitlines() if ln.strip()][-6:]
        for ln in tail:
            print(f'   {ln}', flush=True)
        if r.returncode != 0:
            print(f'FAILED {label}', flush=True)
            return False
    return True


def result(pdir, cid, ok, extra=None):
    meta = meta_of(pdir, cid)
    edited = pdir / 'edited' / meta['file'] if meta else None
    out = {'ok': ok, 'clip': cid, 'file': str(edited) if edited and edited.exists() else None,
           'duration': meta['duration'] if meta else None, **(extra or {})}
    print('RESULT ' + json.dumps(out, ensure_ascii=False), flush=True)


def apply(pdir, cid, ch):
    from .fetch import write_transcript
    picks, k, clip = find_clip(pdir, cid)
    words = load_json(pdir / 'transcript' / 'words.json') or []
    try:
        new_clip, new_words = change_clip(clip, ch, words)
    except (ValueError, KeyError, TypeError) as e:
        die(f'not changed: {e}')
    lock(pdir)
    try:
        back = pdir / '.studio' / str(cid)
        back.mkdir(parents=True, exist_ok=True)
        save_json(back / 'clip.json', clip)                       # one step of undo
        if ch.get('words'):
            shutil.copy2(pdir / 'transcript' / 'words.json', back / 'words.json')
        elif (back / 'words.json').exists():
            (back / 'words.json').unlink()
        picks['clips'][k] = new_clip
        save_json(pdir / 'clips.json', picks)
        if ch.get('words'):
            tdir = pdir / 'transcript'
            if not (tdir / 'words-before-fixes.json').exists():
                shutil.copy2(tdir / 'words.json', tdir / 'words-before-fixes.json')
            write_transcript(pdir, new_words, load_json(pdir / 'project.json', {}) or {})
        print(f'STEP saved ({", ".join(sorted(ch))})', flush=True)
        ok = render(pdir, cid)
    finally:
        unlock(pdir)
    result(pdir, cid, ok)
    if not ok:
        sys.exit(1)


def undo(pdir, cid):
    from .fetch import write_transcript
    back = pdir / '.studio' / str(cid)
    old = load_json(back / 'clip.json')
    if not old:
        die('nothing to undo for this clip')
    picks, k, _ = find_clip(pdir, cid)
    lock(pdir)
    try:
        picks['clips'][k] = old
        save_json(pdir / 'clips.json', picks)
        if (back / 'words.json').exists():
            write_transcript(pdir, load_json(back / 'words.json'), load_json(pdir / 'project.json', {}) or {})
        shutil.rmtree(back)
        print('STEP put back', flush=True)
        ok = render(pdir, cid)
    finally:
        unlock(pdir)
    result(pdir, cid, ok)
    if not ok:
        sys.exit(1)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('project')
    ap.add_argument('--clip', type=int, required=True)
    g = ap.add_mutually_exclusive_group()
    g.add_argument('--apply', metavar='FILE', help='a JSON file with the changes, or - to read them from stdin')
    g.add_argument('--undo', action='store_true', help='put the clip back as it was before the last change')
    a = ap.parse_args()
    pdir = project_dir(a.project)
    if a.apply:
        text = sys.stdin.read() if a.apply == '-' else Path(a.apply).read_text(encoding='utf-8')
        try:
            ch = json.loads(text)
        except json.JSONDecodeError as e:
            die(f'the changes are not JSON: {e}')
        apply(pdir, a.clip, ch if isinstance(ch, dict) else {})
    elif a.undo:
        undo(pdir, a.clip)
    else:
        print(json.dumps(info(pdir, a.clip), ensure_ascii=False))


if __name__ == '__main__':
    main()
