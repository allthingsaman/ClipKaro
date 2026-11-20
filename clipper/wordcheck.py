"""Careful listening, step 3 (v2.7): apply the word-check helpers' answers (wordcheck/batch-NN.json).

    python run.py wordcheck <project>          fixes, no captions on the doubts, players' lines shown again
    python run.py wordcheck <project> --dry    only show what would change (wordcheck/applied.txt)

A fix is written only where the hearings agree; one that would add or drop a "nahin" is never written
(those words get no caption instead). settings.json "unsure_words": "ask" puts the doubts in word-check.json
for you to correct by ear, instead of hiding them. Then romanize, the caption check, cut and edit as usual.
"""
import argparse

from .common import die, project_dir


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('project')
    ap.add_argument('--dry', action='store_true', help='only show what would change')
    a = ap.parse_args()
    from . import hearing
    pdir = project_dir(a.project)
    if not list((pdir / 'wordcheck').glob('batch-*.json')):
        die(f'no answers yet: start the clipkaro-wordcheck helpers on {pdir.name}/wordcheck/batch-NN.txt first')
    n = hearing.apply(pdir, dry=a.dry)
    print(f"-> word check{' (dry run)' if a.dry else ''}: {n['fixed']} word(s) fixed, {n['hidden']} unsure spot(s) "
          f"without captions, {n['meaning']} fix(es) that would flip the meaning hidden instead, "
          f"{n['shown_lines']} player line(s) shown again, {n['hidden_lines']} game line(s) hidden, "
          f"{n['not_found']} not found (wordcheck/applied.txt)")
    if n.get('asked'):
        print(f"-> {n['asked']} doubt(s) in word-check.json for the owner to check by ear")


if __name__ == '__main__':
    main()
