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
import shutil
import subprocess
import sys
from pathlib import Path

from .common import load_json, probe, project_dir, save_json

KIT_VERSION = 1
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
            if head.isdigit():
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
        if not c.get('caption') and not text:
            notes.append(f"clip {c['id']}: no posting caption (PostKaro will start from the title)")
        elif text and set(PLATFORMS) - set(text):
            notes.append(f"clip {c['id']}: no text for {', '.join(sorted(set(PLATFORMS) - set(text)))} "
                         '(PostKaro will use the caption)')
        out.append({'id': c['id'], 'file': str(f.relative_to(pdir)), 'duration': dur,
                    'clip_score': c.get('clip_score', c.get('score')), 'title': c.get('title'),
                    'caption': c.get('caption'), 'note': honesty_note(c), 'deep': bool(c.get('deep')),
                    'text': {p: text[p] for p in PLATFORMS if p in text}})
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
    link, err = link_from_postkaro(app, pdir)
    if not link:
        print(f'PostKaro is installed but did not answer ({err}). Try:  cd "{app["path"]}" && python run.py open "{pdir}"')
        sys.exit(1)
    print(f'Post them: {link}')
    if a.open:
        open_link(link)


if __name__ == '__main__':
    main()
