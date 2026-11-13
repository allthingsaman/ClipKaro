"""A quick look at a video before anything is downloaded (a few seconds).

    python run.py info "https://www.youtube.com/watch?v=..."
    python run.py info "C:/videos/my stream.mp4"

Prints the title, the length, whether it was a live stream or gameplay (as far as the page says), and
what to do about deep clips: for a video longer than 21 minutes (one part), settings.json
"deep_clips": "ask" means Claude asks the user once, right away, while `fetch` runs, unless the user's
message already said. The picture itself (facecam, break screens) is checked at the end of `fetch`.
"""
import argparse
import json
from pathlib import Path

from .common import die, fmt_ts, probe, settings
from .fetch import is_url, page_facts, ytdlp
from .kind import live_info
from .parts import DEEP_ASK_MIN, MIN_CLIPS, MINUTES_PER_CLIP, V11_MAX


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('source', help='YouTube URL or local video file')
    ap.add_argument('--cookies-from-browser', default=None)
    a = ap.parse_args()
    cfg = settings()

    if is_url(a.source):
        meta = json.loads(ytdlp(['--dump-single-json', '--skip-download', a.source], a.cookies_from_browser))
        facts = {'source': a.source, 'kind': 'youtube', 'title': meta.get('title'),
                 'channel': meta.get('channel') or meta.get('uploader'), 'duration': meta.get('duration'),
                 **page_facts(meta)}
    else:
        p = Path(a.source.strip().strip('"\'')).expanduser()
        if not p.exists():
            die(f'file not found: {p}')
        facts = {'source': str(p), 'kind': 'local', 'title': p.stem, 'channel': None,
                 'duration': probe(p).get('duration'), 'live_status': None, 'categories': []}

    minutes = (facts.get('duration') or 0) / 60
    live, why = live_info(facts)
    kind = []
    if live:
        kind.append(f'live stream ({why})')
    if 'Gaming' in facts.get('categories', []):
        kind.append("gameplay (YouTube's category is Gaming)")
    print(f"title:      {facts.get('title')}" + (f"  ·  {facts['channel']}" if facts.get('channel') else ''))
    print(f"length:     {fmt_ts(facts.get('duration') or 0).split('.')[0]}")
    print(f"kind:       {' + '.join(kind) if kind else 'nothing special on the page'}"
          '  (fetch also looks at the picture: facecam, break screens)')

    mode = str(cfg.get('deep_clips', 'ask')).lower()
    if mode == 'always':
        deep = 'yes (settings.json "deep_clips": "always")'
    elif mode == 'never':
        deep = 'no (settings.json "deep_clips": "never")'
    elif minutes > DEEP_ASK_MIN:
        deep = (f'ASK THE USER NOW (longer than {DEEP_ASK_MIN:.0f} minutes), unless their message already said. '
                f'Start fetch first, so it runs while they answer')
    else:
        deep = f'no: {DEEP_ASK_MIN:.0f} minutes or shorter (only when the user asks)'
    print(f'deep clips: {deep}')
    top = max(V11_MAX, min(int(cfg.get('max_clips', 20)), round(minutes / MINUTES_PER_CLIP)))
    print(f'clips:      {MIN_CLIPS} to {top} by default (every decent moment; up to {V11_MAX} as in v1.1, or one per '
          f"{MINUTES_PER_CLIP:.0f} min of real video for long ones). A number in the user's message wins: "
          'parts --at-least N / --at-most N / --clips N')
    print(f'next:       python run.py fetch "{a.source}"   (in the background)')


if __name__ == '__main__':
    main()
