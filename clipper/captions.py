"""The captions of the picked clips, as viewers will read them: for Claude's caption check.

    python run.py captions <project>              every clip in clips.json
    python run.py captions <project> --clips 2,5

Speech models mishear: an English word heard as a Hindi look-alike ("sorry" as सारी), a name, a word
bent by an accent. Claude reads each clip's captions like a viewer, knowing what the video is about,
and fixes the clear mishearings before cutting (standard and deep mode; quick mode skips it to save
Claude usage):

    python run.py fixword <project> "सारी" "sorry" --at 898.6

Each line shows its start time in the video (for --at) and the captions as they will show (in English
letters for Roman Hinglish, without the words that get no caption: made-up words, game characters).
When the transcript writes a word differently, its own words follow in brackets: fixword needs those.
"""
import argparse

from .common import die, load_json, project_dir, settings


def clip_lines(pdir, project, clip, words, lines, table, game, roman):
    """[(start, shown text, transcript text)] for one clip, one row per transcript line."""
    from .romanize import apply
    out = []
    for ln in lines:
        if 's' not in ln or 'i0' not in ln:
            continue
        idx = [k for k in range(ln['i0'], ln['i1'] + 1)
               if any(a <= words[k]['s'] < b for a, b in clip['ranges'])
               and not words[k].get('unsure') and k not in game]
        if not idx:
            continue
        raw = [dict(words[k]) for k in idx]
        shown = apply(raw, table)[0] if roman else raw
        out.append((words[idx[0]]['s'], ' '.join(w['w'] for w in shown), ' '.join(w['w'] for w in raw)))
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('project')
    ap.add_argument('--clips', default=None, help='comma list of clip ids, e.g. 1,3')
    a = ap.parse_args()
    pdir = project_dir(a.project)
    project = load_json(pdir / 'project.json', {}) or {}
    picks = load_json(pdir / 'clips.json')
    words = load_json(pdir / 'transcript' / 'words.json')
    lines = load_json(pdir / 'transcript' / 'sentences.json') or []
    if not picks or not words:
        die(f'no clips.json or transcript in {pdir}')
    from .romanize import load_table, wants_roman
    roman = wants_roman(project)
    table = load_table(pdir) if roman else {}
    game = set()
    if not settings().get('game_voice_captions', False):
        from . import voices
        game = voices.game_words(pdir, project, words, lines)
    want = {int(x) for x in a.clips.split(',')} if a.clips else None
    print(f'# Captions as they will show. Read them like a viewer of "{project.get("title") or pdir.name}" and fix only '
          f'clear mishearings (an English word heard as a Hindi look-alike, a name, an accent slip), never what was '
          f'really said: python run.py fixword {pdir.name} "<word as in the transcript>" "<right word>" --at <seconds>\n')
    for i, clip in enumerate(picks['clips'], 1):
        cid = int(clip.get('id', i))
        if want and cid not in want:
            continue
        rows = clip_lines(pdir, project, clip, words, lines, table, game, roman)
        print(f'== clip {cid}: "{clip.get("title")}"')
        for t, shown, raw in rows:
            print(f'[{t:.2f}] {shown}' + (f'   ({raw})' if raw != shown else ''))
        print()


if __name__ == '__main__':
    main()
