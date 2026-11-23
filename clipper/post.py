"""Hand the finished clips to PostKaro, the posting app (a separate, optional install).

    python run.py post <project>          write output/<project>/post.json; if PostKaro is installed,
                                          add the clips to it and print the link that opens them
    python run.py post <project> --open   ... and open that link in the browser

post.json holds, for each clip: the video file, its length, clip score, honesty note, and the text
for each platform (clips.json "post": YouTube title + description, Instagram caption, Facebook
caption). Format: PostKaro's docs/post-kit.md. ClipKaro works the same without PostKaro.
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

from . import stars as starlib
from .common import load_json, probe, project_dir, save_json, settings

KIT_VERSION = 1
# how a joined clip (deep clips) used to be marked in its posting texts: for us, not for viewers (2026-11-21)
JOINED_LINE = re.compile(r'^[ \t]*From \d+ moments of the full video:[^\n]*(\n|$)', re.I | re.M)
JOINED_TITLE = re.compile(r'[ \t]*\(\d+ moments joined\)', re.I)


def without_joined_note(text):
    """A posting text without "From 2 moments of the full video: 0:08 · 22:53" and "(2 moments joined)"."""
    if not isinstance(text, str):
        return text
    return JOINED_TITLE.sub('', JOINED_LINE.sub('', text)).strip()
PLATFORMS = ('youtube', 'instagram', 'facebook')


def postkaro_app():
    """PostKaro's app.json (where it is installed, its port), or None when it isn't installed."""
    if os.environ.get('POSTKARO_HOME'):
        f = Path(os.environ['POSTKARO_HOME']) / 'app.json'
    elif os.name == 'nt':
        f = Path(os.environ.get('LOCALAPPDATA') or Path.home() / 'AppData' / 'Local') / 'postkaro' / 'app.json'
    elif sys.platform == 'darwin':
        f = Path.home() / 'Library' / 'Application Support' / 'postkaro' / 'app.json'
    else:
        f = Path(os.environ.get('XDG_CONFIG_HOME') or Path.home() / '.config') / 'postkaro' / 'app.json'
    info = load_json(f)
    if not info or not (Path(info.get('path', '')) / 'run.py').exists():
        return None
    return info


def clip_files(pdir):
    files = {}
    for sub in ('clips', 'edited'):                 # edited wins
        d = pdir / sub
        for f in sorted(d.glob('*.mp4')) if d.is_dir() else ():
            head = f.name.split('-')[0]
            if head.isdigit() and not f.stem.endswith('-landscape'):   # the 16:9 copy is not a short (v2.8)
                files[int(head)] = f
    return files


def honesty_note(c):
    """A deep clip's honesty note: the deep pass keeps it inside "deep", older clips.json files at the top."""
    deep = c.get('deep') if isinstance(c.get('deep'), dict) else {}
    note = c.get('honesty_note') or deep.get('honesty_note')
    if isinstance(note, dict):              # {"role": ..., "reason": ...} from the judges
        note = note.get('reason') or note.get('note') or json.dumps(note, ensure_ascii=False)
    return note or None


def build(pdir):
    """-> (kit, notes): the post kit and a list of things worth telling the user."""
    clips = load_json(pdir / 'clips.json', {}).get('clips', [])
    proj = load_json(pdir / 'project.json', {})
    files = clip_files(pdir)
    out, notes = [], []
    facts_cache = {}
    stars_on = starlib.on()
    joined_on = settings().get('joined_note', False) is True
    for c in clips:
        f = files.get(c.get('id'))
        if not f:
            notes.append(f"clip {c.get('id')}: no video file yet (cut and edit it first)")
            continue
        try:
            dur = round(probe(str(f))['duration'], 2)
        except SystemExit:
            dur = round(sum(e - s for s, e in c.get('ranges', [])), 2)
        text = c.get('post') or {}
        caption, title = c.get('caption'), c.get('title')
        if not joined_on:              # where a joined clip's moments are in the video: never in what viewers read
            text = {p: ({k: without_joined_note(v) for k, v in t.items()} if isinstance(t, dict) else t)
                    for p, t in text.items()}
            caption = without_joined_note(caption)
        if stars_on:                   # abusive and taboo words with stars, as in the captions ("F******")
            marked = starlib.marks(c.get('stars'))
            title = starlib.star_text(title, marked)
            text = {p: ({k: starlib.star_text(v, marked) if isinstance(v, str) else v for k, v in t.items()}
                        if isinstance(t, dict) else t) for p, t in text.items()}
            caption = starlib.star_text(caption, marked)
        if not c.get('caption') and not text:
            notes.append(f"clip {c['id']}: no posting caption (PostKaro will start from the title)")
        elif text and set(PLATFORMS) - set(text):
            notes.append(f"clip {c['id']}: no text for {', '.join(sorted(set(PLATFORMS) - set(text)))} "
                         '(PostKaro will use the caption)')
        from .learn import clip_facts                # v2.11: what the clip is, kept by PostKaro for learning
        facts = clip_facts(pdir, c['id'], facts_cache)  # (the project folder may be deleted later)
        out.append({'id': c['id'], 'file': str(f.relative_to(pdir)), 'duration': dur,
                    'clip_score': c.get('clip_score', c.get('score')), 'title': title,
                    'caption': caption, 'note': honesty_note(c), 'deep': bool(c.get('deep')),
                    'text': {p: text[p] for p in PLATFORMS if p in text},
                    **({'facts': facts} if facts else {})})
    kit = {'postkit': KIT_VERSION, 'made_by': 'ClipKaro', 'project': pdir.name, 'title': proj.get('title'),
           'source': {'channel': proj.get('channel'), 'channel_url': proj.get('channel_url'),
                      'url': proj.get('source') if proj.get('kind') == 'youtube' else None},
           'clips': out}
    return kit, notes


def link_from_postkaro(app, pdir):
    """Ask PostKaro to add the project and give its link (it starts its helper if needed)."""
    root = Path(app['path'])
    py = root / '.venv' / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')
    exe = [str(py)] if py.exists() else [sys.executable]
    try:
        r = subprocess.run([*exe, str(root / 'run.py'), 'link', str(pdir)], capture_output=True, text=True,
                           timeout=120, encoding='utf-8', errors='replace')
    except (OSError, subprocess.SubprocessError) as e:
        return None, str(e)
    for line in reversed(r.stdout.strip().splitlines()):
        try:
            j = json.loads(line)
            return j.get('link'), None if j.get('ok') else 'PostKaro did not start'
        except ValueError:
            continue
    return None, (r.stderr or r.stdout).strip()[-400:]


def post_now_via_postkaro(app, pdir, dry=False):
    """Live clipping: PostKaro adds the clips and posts each on every connected platform at once.
    -> (result dict or None, problem)."""
    root = Path(app['path'])
    py = root / '.venv' / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')
    exe = [str(py)] if py.exists() else [sys.executable]
    try:
        r = subprocess.run([*exe, str(root / 'run.py'), 'post-now', str(pdir), *(['--dry'] if dry else [])],
                           capture_output=True, text=True, timeout=300, encoding='utf-8', errors='replace')
    except (OSError, subprocess.SubprocessError) as e:
        return None, str(e)
    for line in reversed(r.stdout.strip().splitlines()):
        try:
            return json.loads(line), None
        except ValueError:
            continue
    return None, (r.stderr or r.stdout).strip()[-400:] or 'PostKaro has no "post-now" yet: update PostKaro'


def open_link(url):
    if sys.platform.startswith('linux') and shutil.which('xdg-open'):
        subprocess.Popen(['xdg-open', url], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                         start_new_session=True)
    elif sys.platform == 'darwin':
        subprocess.Popen(['open', url])
    else:
        import webbrowser
        webbrowser.open(url)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('project')
    ap.add_argument('--open', action='store_true', help='open the PostKaro link in the browser')
    ap.add_argument('--now', action='store_true',
                    help='live clipping: post every clip on every connected platform at once (no review)')
    ap.add_argument('--dry', action='store_true', help='with --now: only show what would be posted')
    a = ap.parse_args()
    pdir = project_dir(a.project)
    kit, notes = build(pdir)
    if not kit['clips']:
        print('No finished clips to post yet: run cut (and edit) first.')
        sys.exit(1)
    save_json(pdir / 'post.json', kit)
    print(f"post.json: {len(kit['clips'])} clip(s) ready to post -> {pdir / 'post.json'}")
    for n in notes:
        print('  ?', n)
    from .more import summary_line
    more = summary_line(pdir)
    if more:
        print(more)
    app = postkaro_app()
    if not app:
        print('PostKaro (the posting app) is not installed, so post the files in edited/ by hand. '
              'PostKaro posts them to YouTube, Instagram and Facebook for you: see docs/usage.md, "Posting".')
        return
    if a.now:
        # a test stream: settings.json "live_post": "dry" shows what would be posted, and posts nothing
        a.dry = a.dry or str(settings().get('live_post', 'now')).lower() == 'dry'
        res, err = post_now_via_postkaro(app, pdir, a.dry)
        if not res:
            print(f'PostKaro did not post ({err})')
            sys.exit(1)
        if a.dry:
            print('(test: nothing posted) Would post now: ' + ', '.join(f"clip {x['clip']} on {x['platform']}" for x in res.get('would_post', []))
                  or 'nothing (no connected platform?)')
            return
        print(f"Posting now: {res.get('scheduled', 0)} post(s) on their way (PostKaro uploads within a minute)")
        for s in res.get('skipped', []):
            print(f"  ! clip {s['clip']} on {s['platform']} not posted: {' '.join(s['why'])}")
        if res.get('link'):
            print(f"Follow them: {res['link']}")
        return
    link, err = link_from_postkaro(app, pdir)
    if not link:
        print(f'PostKaro is installed but did not answer ({err}). Try:  cd "{app["path"]}" && python run.py open "{pdir}"')
        sys.exit(1)
    print(f'Post them: {link}')
    if a.open:
        open_link(link)


if __name__ == '__main__':
    main()
