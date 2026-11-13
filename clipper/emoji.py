"""Emoji pictures for the edit: Google's Noto emoji (3D style, free to use: OFL / Apache 2.0).

Only the emojis a clip uses are downloaded, once, and kept in output/.cache/emoji/. Captions can't
draw colour emojis themselves (the subtitle renderer has no colour-emoji support), so the edit puts
the picture in the frame, above the caption line, when its word is said.
"""
import urllib.request

from .common import ROOT

CACHE = ROOT / 'output' / '.cache' / 'emoji'
SOURCES = ['https://raw.githubusercontent.com/googlefonts/noto-emoji/main/3D/png/512/emoji_u{code}.png',
           'https://raw.githubusercontent.com/googlefonts/noto-emoji/main/2D/png/512/emoji_u{code}.png']


def code(ch):
    """'💰' -> '1f4b0' (variation selectors left out, as the file names do)."""
    return '_'.join(f'{ord(c):x}' for c in ch.strip() if ord(c) not in (0xfe0e, 0xfe0f))


def png(ch):
    """The picture file of an emoji, downloaded the first time; None when it can't be had (offline)."""
    c = code(ch)
    if not c:
        return None
    path = CACHE / f'emoji_u{c}.png'
    if path.exists() and path.stat().st_size > 1000:
        return path
    CACHE.mkdir(parents=True, exist_ok=True)
    for url in SOURCES:
        try:
            with urllib.request.urlopen(url.format(code=c), timeout=20) as r:
                data = r.read()
            if data[:8] == b'\x89PNG\r\n\x1a\n':
                path.write_bytes(data)
                return path
        except Exception:
            continue
    return None
