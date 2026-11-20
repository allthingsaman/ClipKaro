"""Your brand on every clip, and credit to the source (v2.4). Used by the edit step.

    brand/logo.png     your logo: the bottom-right corner, right in the corner, the whole clip
    brand/outro.mp4    your own outro (9:16, ideally 3-5 s), added after every clip
    (C) Channel name   the bottom-left corner, on clips made from a link (never your own files);
                       "© twitch.tv/name" for a Twitch or Kick video (v2.7)

Both sit right in the corners, with no gap, at 70 % opacity, on purpose (the owner's choice,
2026-11-17): a formality, not something to read. On phones the apps' own text, buttons and top bar
cover the corners, which is why captions, emojis and hook titles never go there, so nothing of the clip
collides with them. Neither shows during the outro. No intro: a clip must open on its hook.

settings.json: "source_credit", "logo" and "outro" (all true; the logo and outro are used only when
their files are in the brand folder), "logo_corner" (bottom-right) and "credit_corner" (bottom-left):
top-left, top-right, bottom-left or bottom-right. One run: edit --no-credit / --no-logo / --no-outro,
--logo-corner / --credit-corner. In the same corner, the credit sits next to the logo (above it at the
bottom, below it at the top).
The folder can be moved with the CLIPKARO_BRAND environment variable (tests, reviews with sample files).
"""
import os
import subprocess
from pathlib import Path

from .common import H, ROOT, W, ffmpeg, has_devanagari, imread, imwrite, probe, settings
from .plan import HINDI_FONT, LATIN_FONT

PAD = 0                           # px in from the frame's edges: none, right in the corner (the owner's choice)
CORNERS = ('top-left', 'top-right', 'bottom-left', 'bottom-right')
LOGO_CORNER, CREDIT_CORNER = 'bottom-right', 'bottom-left'
ALIGN = {'bottom-left': 1, 'bottom-right': 3, 'top-left': 7, 'top-right': 9}   # ASS \an: the text's anchor
LOGO_MAX_W, LOGO_MAX_H = 220, 120 # the logo fits this box: a square logo 120x120, a wide one up to 220 px
OPACITY = 0.7                     # the logo and the credit: 70 % visible, a formality (the owner, 2026-11-17)
CREDIT_SIZE = 34                  # CSS px: small
CREDIT_MAX = 40                   # characters of the channel's name before it is shortened with "..."
OUTRO_IDEAL = 5.0                 # longer than this: a warning (3-5 s is ideal)
OUTRO_MAX = 10.0                  # longer than this: left out, so an outro is never longer than the clip
IMAGE_EXT = ('.png', '.jpg', '.jpeg', '.webp')
VIDEO_EXT = ('.mp4', '.mov', '.m4v', '.mkv', '.webm')


def folder():
    return Path(os.environ.get('CLIPKARO_BRAND') or ROOT / 'brand')


def find(stem, exts, where=None):
    """brand/<stem>.<one of exts>, or None."""
    d = Path(where) if where else folder()
    if not d.is_dir():
        return None
    return next((p for p in sorted(d.iterdir())
                 if p.is_file() and p.stem.lower() == stem and p.suffix.lower() in exts), None)


STREAM_SITES = {'twitch.tv': 'twitch.tv', 'kick.com': 'kick.com'}   # credit names the site: "© twitch.tv/name"


def credit_text(project, on=True):
    """"(C) Channel name" for a video from a link (never your own files, no channel, or off), else None.

    A Twitch or Kick video gets "© twitch.tv/name" (v2.7): a streamer's name alone reads like a YouTube
    channel, which may be someone else's or the streamer's other channel. settings.json "credit_text"
    writes your own: "{channel}" in it becomes the channel's name ("clipped from {channel}")."""
    project = project or {}
    if not on or project.get('kind') != 'youtube':
        return None
    name = ' '.join(str(project.get('channel') or '').split())
    if not name:
        return None
    src = str(project.get('source') or '').lower()
    site = next((v for k, v in STREAM_SITES.items() if k in src), None)
    if site and not name.lower().startswith(site):
        name = f'{site}/{name}'
    own = str(settings().get('credit_text') or '').strip()
    text = own.replace('{channel}', name) if own else f'© {name}'
    if len(text) > CREDIT_MAX + 2:
        text = text[:CREDIT_MAX + 1].rstrip() + '…'
    return text


def corner(value, default):
    """(one of CORNERS, message or None): "bottom-right", "bottom right", "bot_right", "BR" ... all work."""
    v = str(value or '').strip().lower().replace('_', '-').replace(' ', '-')
    v = {'bl': 'bottom-left', 'br': 'bottom-right', 'tl': 'top-left', 'tr': 'top-right'}.get(v, v)
    v = v.replace('bot-', 'bottom-').replace('btm-', 'bottom-')
    if v in CORNERS:
        return v, None
    return default, (f'! "{value}" is not a corner (top-left, top-right, bottom-left or bottom-right): '
                     f'{default} instead')


def credit(project, on=True, where=CREDIT_CORNER):
    text = credit_text(project, on)
    if not text:
        return None
    font, font_file = HINDI_FONT if has_devanagari(text) else LATIN_FONT
    # anchored at the corner itself: x and y are the corner's point, \an says which corner of the text
    x = PAD if where.endswith('left') else W - PAD
    y = PAD if where.startswith('top') else H - PAD
    return {'text': text, 'x': x, 'y': y, 'an': ALIGN[where], 'corner': where, 'size': CREDIT_SIZE,
            'font': font, 'font_file': font_file}


def logo_box(w, h, where=LOGO_CORNER):
    """(width, height, x, y) of a w x h logo in that corner, PAD in from the edges."""
    k = min(LOGO_MAX_W / w, LOGO_MAX_H / h)
    lw, lh = max(2, int(round(w * k / 2)) * 2), max(2, int(round(h * k / 2)) * 2)
    x = PAD if where.endswith('left') else W - PAD - lw
    y = PAD if where.startswith('top') else H - PAD - lh
    return lw, lh, x, y


BG_EDGE = 0.03       # the outer 3 % of the logo is its border
BG_SHARE = 0.9       # a plain background: 90 % of the border within BG_NEAR of one colour
BG_NEAR = 24         # colour distance (0-255, the largest of B, G, R) counted as "the same colour"
BG_LO, BG_HI = 12, 72  # near the background: see-through below BG_LO, solid from BG_HI, a soft ramp between
BG_FRINGE = 0.015    # the soft ramp reaches this far (share of the logo's size) past the background: a glow's edge


def plain_background(img):
    """The logo's background colour (B, G, R) when its border is one plain colour and it has nothing
    see-through yet, else None."""
    import numpy as np
    if img.ndim == 3 and img.shape[2] == 4 and img[:, :, 3].min() < 250:
        return None                                   # already see-through somewhere: leave it alone
    bgr = img[:, :, :3] if img.ndim == 3 else np.dstack([img] * 3)
    h, w = bgr.shape[:2]
    e = max(1, int(round(min(h, w) * BG_EDGE)))
    ring = np.concatenate([bgr[:e].reshape(-1, 3), bgr[-e:].reshape(-1, 3),
                           bgr[:, :e].reshape(-1, 3), bgr[:, -e:].reshape(-1, 3)]).astype(np.int16)
    colour = np.median(ring, axis=0)
    near = np.abs(ring - colour).max(axis=1) <= BG_NEAR
    return tuple(int(c) for c in colour) if near.mean() >= BG_SHARE else None


def see_through(img, colour):
    """The logo with its plain background removed (BGRA): only the background that touches the edge (the
    same colour inside the logo stays: a dark shield, the hole of a letter), plus a thin soft fringe around
    it so a glow fades out instead of ending in a hard line, with the background colour taken out of the
    half see-through pixels."""
    import cv2
    import numpy as np
    bgr = (img[:, :, :3] if img.ndim == 3 else np.dstack([img] * 3)).astype(np.float32)
    dist = np.abs(bgr - np.array(colour, np.float32)).max(axis=2)
    _, labels = cv2.connectedComponents((dist <= BG_NEAR).astype(np.uint8), connectivity=4)
    edge = set(np.unique(np.concatenate([labels[0], labels[-1], labels[:, 0], labels[:, -1]]))) - {0}
    bg = np.isin(labels, list(edge)) & (dist <= BG_NEAR)
    r = max(1, int(round(min(dist.shape) * BG_FRINGE)))
    near = cv2.dilate(bg.astype(np.uint8), cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * r + 1, 2 * r + 1))) > 0
    outside = (bg | near) & (dist < BG_HI)
    a = np.ones(dist.shape, np.float32)
    a[outside] = np.clip((dist[outside] - BG_LO) / (BG_HI - BG_LO), 0, 1)
    k = np.maximum(a, 1e-3)[:, :, None]
    fg = np.clip((bgr - np.array(colour, np.float32) * (1 - k)) / k, 0, 255)
    return np.dstack([fg, a * 255]).astype(np.uint8)


def clean_logo(p, work, keep=False):
    """(the file to use, message or None, (width, height)): the logo without a plain background and
    without empty see-through margins, so the logo itself sits right in the corner (made once, in the
    project's .work folder); or the file itself ("logo_background": "keep", or nothing to do)."""
    import cv2
    import numpy as np
    img = imread(p, cv2.IMREAD_UNCHANGED)
    size = (img.shape[1], img.shape[0])
    if keep or work is None:
        return p, None, size
    colour = plain_background(img)
    note = None
    if colour is not None:
        rgba = see_through(img, colour)
        name = {(0, 0, 0): 'black', (255, 255, 255): 'white'}.get(
            tuple(round(c / 255) * 255 for c in colour), 'plain')
        note = f'-> your logo has a {name} background: made see-through (settings.json "logo_background": "keep" leaves it)'
    elif img.ndim == 3 and img.shape[2] == 4:
        rgba = img
    else:
        return p, None, size
    ys, xs = np.nonzero(rgba[:, :, 3] > 8)
    if not len(xs):
        return p, None, size
    x0, x1, y0, y1 = xs.min(), xs.max() + 1, ys.min(), ys.max() + 1
    if colour is None and (x1 - x0, y1 - y0) == size:
        return p, None, size                       # see-through already, no empty margin: as it is
    st = p.stat()
    out = Path(work) / f'logo-ready-{int(st.st_mtime)}-{st.st_size}.png'
    if not out.exists():
        tmp = out.with_name(out.stem + f'.{os.getpid()}.part.png')
        imwrite(tmp, rgba[y0:y1, x0:x1])
        os.replace(tmp, out)
    return out, note, (int(x1 - x0), int(y1 - y0))


def logo(on=True, where=None, place=LOGO_CORNER, work=None, keep_background=False):
    """({file, w, h, x, y, alpha, corner} or None, messages)."""
    p = find('logo', IMAGE_EXT, where)
    if not on or not p:
        return None, []
    import cv2
    if imread(p, cv2.IMREAD_UNCHANGED) is None:
        return None, [f'! {p.name}: not a picture ClipKaro can read (use PNG or JPG): left out']
    use, note, (w, h) = clean_logo(p, work, keep_background)
    lw, lh, x, y = logo_box(w, h, place)
    return ({'file': str(Path(use).resolve()), 'name': p.name, 'w': lw, 'h': lh, 'x': x, 'y': y, 'alpha': OPACITY,
             'corner': place},
            [note] if note else [])


def share_corner(cr, lg):
    """The credit and the logo in the same corner: the credit moves next to the logo, above it at the
    bottom, below it at the top, so neither covers the other."""
    if cr and lg and cr['corner'] == lg['corner']:
        cr['y'] = lg['y'] if cr['corner'].startswith('bottom') else lg['y'] + lg['h']
    return cr


def outro_check(duration, width, height):
    """(use it?, messages) for an outro of this length and shape."""
    msgs = []
    if duration > OUTRO_MAX:
        return False, [f'! the outro is {duration:.1f} s long: left out (the most is {OUTRO_MAX:.0f} s, 3-5 s is '
                       f'ideal), so it is never longer than the clip. Make a shorter one.']
    if duration > OUTRO_IDEAL:
        msgs.append(f'! the outro is {duration:.1f} s long: 3-5 s is ideal (viewers swipe away during a long one)')
    if width and height and abs(width / height - W / H) > 0.02:
        msgs.append(f'! the outro is {width}x{height}, not standing (9:16): fitted over a blurred copy of itself')
    return True, msgs


def outro(work, on=True, where=None):
    """({file, duration, audio (a wav, -14 LUFS)} or None, messages)."""
    p = find('outro', VIDEO_EXT, where)
    if not on or not p:
        return None, []
    try:
        info = probe(str(p))
    except Exception:
        info = {}
    if not info.get('width'):
        return None, [f'! {p.name}: no picture in it (or not a video ClipKaro can read): left out']
    d = float(info.get('duration') or 0)
    ok, msgs = outro_check(d, info['width'], info['height'])
    if not ok:
        return None, msgs
    return {'file': str(p.resolve()), 'duration': round(d, 3), 'audio': str(outro_audio(p, d, work))}, msgs


def has_audio(path):
    r = subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'a', '-show_entries', 'stream=index',
                        '-of', 'csv=p=0', str(path)], capture_output=True, text=True)
    return bool(r.stdout.strip())


def outro_audio(p, duration, work):
    """The outro's sound as a 48 kHz stereo wav of exactly its length, at -14 LUFS like the clips (silence
    when it has none), with a 20 ms fade-in so the join never clicks. Made once per outro file (kept in
    the project's .work folder)."""
    st = p.stat()
    out = Path(work) / f'outro-v1-{int(st.st_mtime)}-{st.st_size}.wav'
    if out.exists():
        return out
    tmp = out.with_name(out.stem + f'.{os.getpid()}.part.wav')
    if has_audio(p):
        ffmpeg('-i', str(p), '-vn', '-af',
               'aresample=48000,aformat=channel_layouts=stereo,loudnorm=I=-14:TP=-2:LRA=11,aresample=48000,'
               f'afade=t=in:d=0.02,apad,atrim=0:{duration:.3f}', '-c:a', 'pcm_s16le', str(tmp))
    else:
        ffmpeg('-f', 'lavfi', '-i', 'anullsrc=r=48000:cl=stereo', '-t', f'{duration:.3f}', '-c:a', 'pcm_s16le',
               str(tmp))
    os.replace(tmp, out)
    return out


def resolve(project, work, credit_on=True, logo_on=True, outro_on=True, where=None,
            logo_corner=LOGO_CORNER, credit_corner=CREDIT_CORNER, logo_background='remove'):
    """Everything the edit adds, once per run: ({credit, logo, outro}, messages). The corners come from
    settings.json ("logo_corner", "credit_corner"); a wrong one falls back to the default, with a note."""
    lc, n1 = corner(logo_corner, LOGO_CORNER)
    cc, n2 = corner(credit_corner, CREDIT_CORNER)
    lg, m1 = logo(logo_on, where, lc, work, str(logo_background).lower() == 'keep')
    ou, m2 = outro(work, outro_on, where)
    cr = share_corner(credit(project, credit_on, cc), lg)
    return {'credit': cr, 'logo': lg, 'outro': ou}, [m for m in (n1, n2) if m] + m1 + m2


def summary(kit):
    """One line for the edit's output, or ''."""
    parts = []
    if kit.get('logo'):
        parts.append(f"logo {kit['logo'].get('name') or Path(kit['logo']['file']).name} "
                     f"({kit['logo']['corner'].replace('-', ' ')})")
    if kit.get('outro'):
        parts.append(f"outro {Path(kit['outro']['file']).name} ({kit['outro']['duration']:.1f} s, after every clip)")
    if kit.get('credit'):
        parts.append(f"credit \"{kit['credit']['text']}\" ({kit['credit']['corner'].replace('-', ' ')})")
    return ('-> your brand: ' + ', '.join(parts)) if parts else ''


def video_graph(base_vf, fps, logo=None, outro=None, logo_in=2, outro_in=3):
    """The -filter_complex for the finished picture: input 0's video through base_vf (the captions and
    the credit, or 'null'), the logo on top, then the outro after it. Output label [v]."""
    chains = [f'[0:v]{base_vf},setsar=1,format=yuv420p[main]']
    cur = 'main'
    if logo:
        chains.append(f"[{logo_in}:v]scale={logo['w']}:{logo['h']},format=rgba,"
                      f"colorchannelmixer=aa={logo['alpha']}[lg]")
        chains.append(f"[{cur}][lg]overlay={logo['x']}:{logo['y']}:format=auto,format=yuv420p[ml]")
        cur = 'ml'
    if outro:
        # standing outros fill the frame; any other shape sits over a blurred copy of itself
        chains.append(f"[{outro_in}:v]split[oa][ob];"
                      f"[oa]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},boxblur=24:2[obg];"
                      f"[ob]scale={W}:{H}:force_original_aspect_ratio=decrease[ofg];"
                      f"[obg][ofg]overlay=(W-w)/2:(H-h)/2,fps={fps},setsar=1,format=yuv420p[ov]")
        chains.append(f'[{cur}][ov]concat=n=2:v=1:a=0[v]')
    else:
        chains.append(f'[{cur}]null[v]')
    return ';'.join(chains)


def inputs(kit):
    """(extra ffmpeg inputs after the picture (0) and the sound (1), logo input index, outro input index)."""
    args, k, li, oi = [], 2, None, None
    if kit.get('logo'):
        args += ['-i', kit['logo']['file']]
        li, k = k, k + 1
    if kit.get('outro'):
        args += ['-i', kit['outro']['file']]
        oi = k
    return args, li, oi
