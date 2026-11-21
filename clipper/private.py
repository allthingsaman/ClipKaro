"""Private details said out loud (v2.7): an email address spelled out, a phone number, a home address.

On a 4-hour GTA stream a viewer's email address was spelled out letter by letter ("email ID ... hai,
x x 1 2 1 1 ..."). Claude noticed it and kept it out of every clip by hand; now ClipKaro does:

- `spans(words)` finds them in the transcript: a cue ("email", "mail ID", "gmail", "at the rate",
  "number", "phone", "WhatsApp", "address", "pin code") followed within ~25 s by a run of spelled-out
  pieces said one right after another (single letters, digit groups, "dot", "underscore", "at the rate",
  letters with digits; at most 2 other words between two of them), or 9+ digits said in a row with
  nothing between them (a phone number). Number words ("one", "एक", "दो") only count right next to
  another spelled piece: on their own they are everyday words. Game words, prices, years, counting and
  talk *about* an email ("mail ID bhej do") have no such run and are left alone.
- Since the v2.7.1 review: everyday talk ("the number of people who quit at 25 ... one in two fail at
  30", "मेरा नंबर एक पे आया ... दो साल बाद 2019 में", "from 1999 2000 2001") is never taken for a detail,
  and it runs on gameplay and streams only ("private_details": "hide", the default), where viewers and
  friends read things out; "all" runs it on every video.
- `parts` leaves those lines out of what the reading helpers see (like a break screen), and `cut` takes
  those seconds out of any clip that touches them, so they can't end up in a clip even by hand. Both say
  where they were.

settings.json "private_details": "keep" switches it off; "all" also checks podcasts and talks.
"""
import re

from .common import norm_token

CUES = {'email', 'e-mail', 'emailid', 'gmail', 'gmail.com', 'yahoo', 'hotmail', 'outlook', 'rediffmail', 'icloud',
        'protonmail', '@', 'whatsapp', 'phone', 'mobile', 'number', 'contact', 'address', 'pincode', 'ईमेल', 'जीमेल',
        'नंबर', 'फोन', 'मोबाइल', 'एड्रेस'}          # not "पता": "मुझे नहीं पता" is everyday Hindi
PAIR_CUES = {('mail', 'id'), ('pin', 'code'), ('dot', 'com'), ('mail', 'address')}   # and "at the rate" (three words)
SPELL_WORDS = {'dot', 'underscore', 'com', 'gmail', 'hyphen', 'dash', 'डॉट', 'कॉम', 'अंडरस्कोर', '@'}  # + "at the rate"
NUMBER_WORDS = {'zero': 1, 'one': 1, 'two': 1, 'three': 1, 'four': 1, 'five': 1, 'six': 1, 'seven': 1, 'eight': 1,
                'nine': 1, 'double': 1, 'triple': 1, 'शून्य': 1, 'एक': 1, 'दो': 1, 'तीन': 1, 'चार': 1, 'पांच': 1, 'छह': 1,
                'सात': 1, 'आठ': 1, 'नौ': 1}
WINDOW_S = 25.0        # spelled pieces this long after a cue
MIN_SPELLED = 4        # this many spelled pieces make it a spelled-out detail
GAP_S = 5.0            # ... with no more than this between two of them (spelling aloud is slow: 3.1 s on a stream)
MAX_BETWEEN = 2        # ... and at most this many other words between two of them (spelling goes piece by piece)
FILLER_PAIRS = {'hm', 'mm', 'sh', 'ok'}
PHONE_DIGITS = 9       # a phone number: this many digits said close together
PHONE_GAP_S = 2.5
PAD_S = 0.5            # seconds kept clear around a found span


def _spelled(word):
    """A spelled-out piece: a single letter, digits, letters mixed with digits, "dot", "underscore", a number
    word, or two letters without a vowel ("DH": letters said one by one)."""
    n = norm_token(word)
    if not n or re.match(r'^\s*\.\d', word):           # ".5": a decimal, not a spelled piece
        return False
    if n in SPELL_WORDS or n in NUMBER_WORDS:
        return True
    if re.fullmatch(r'\d+', n):
        return True
    if re.fullmatch(r'[a-z]', n) and n not in ('a', 'i'):
        return True
    if re.fullmatch(r'[bcdfghjklmnpqrstvwxyz]{2}', n) and n not in FILLER_PAIRS:
        return True
    return bool(re.search(r'\d', n) and re.search(r'[a-z]', n))     # "x8", "abc123"


def _pieces(words, a, b):
    """Indexes of the spelled pieces among words[a:b]. "at the rate" (how "@" is said) is one piece; a number
    word counts only right next to another piece ("nine eight seven ..."), never alone ("one in two")."""
    out, i = [], a
    while i < b:
        if [norm_token(v['w']) for v in words[i:i + 3]] == ['at', 'the', 'rate']:
            out.append((i, False))
            i += 3
            continue
        if _spelled(words[i]['w']):
            out.append((i, norm_token(words[i]['w']) in NUMBER_WORDS))
        i += 1
    idx = {k for k, _ in out}
    return [k for k, weak in out if not weak or k - 1 in idx or k + 1 in idx or k - 3 in idx]


def _runs(words, pieces):
    """The pieces grouped into runs said one after another: at most MAX_BETWEEN other words and GAP_S
    seconds between two pieces."""
    runs = []
    for k in pieces:
        if runs and k - runs[-1][-1] - 1 <= MAX_BETWEEN + (2 if norm_token(words[runs[-1][-1]]['w']) == 'at' else 0) \
                and words[k]['s'] - words[runs[-1][-1]]['e'] <= GAP_S:
            runs[-1].append(k)
        else:
            runs.append([k])
    return runs


def _digits(word):
    n = norm_token(word)
    if re.fullmatch(r'\d+', n or ''):
        return len(n)
    return NUMBER_WORDS.get(n, 0)


def _is_cue(words, i):
    n = norm_token(words[i]['w'])
    if n in CUES or '@' in words[i]['w']:
        return True
    nxt = [norm_token(v['w']) for v in words[i + 1:i + 3]]
    return (n, nxt[0] if nxt else '') in PAIR_CUES or [n] + nxt == ['at', 'the', 'rate']


def _counting(run):
    """Numbers counted up or down ("1, 2, 3, 4, 10, 11 ...", "1999 2000 2001"): counting or years, not a phone
    number."""
    vals = [int(norm_token(v['w'])) for v in run if re.fullmatch(r'\d+', norm_token(v['w']) or '')]
    steps = [b - a for a, b in zip(vals, vals[1:])]
    return len(vals) >= 3 and max(steps.count(1), steps.count(-1)) >= 0.6 * len(steps)


def spans(words):
    """[(start, end, what)] of private details said out loud, merged and padded, in video seconds."""
    found = []
    for i, w in enumerate(words):
        if not _is_cue(words, i):
            continue
        j = i + 1
        while j < len(words) and words[j]['s'] - w['s'] <= WINDOW_S:
            j += 1
        good = [r for r in _runs(words, _pieces(words, i + 1, j))
                if len(r) >= MIN_SPELLED and len({norm_token(words[k]['w']) for k in r}) >= 3   # a loop isn't spelling
                and not _counting([words[k] for k in r])]
        if good:
            what = 'a phone number' if norm_token(w['w']) in {'phone', 'mobile', 'whatsapp', 'number', 'नंबर', 'फोन',
                                                               'मोबाइल'} else 'an email address or contact detail'
            found.append((w['s'], words[good[-1][-1]]['e'], what))
    k = 0
    while k < len(words):                       # phone numbers said without a cue word
        if not _digits(words[k]['w']):
            k += 1
            continue
        j, total = k, 0
        while j < len(words) and _digits(words[j]['w']) and (j == k or words[j]['s'] - words[j - 1]['e'] <= PHONE_GAP_S):
            total += _digits(words[j]['w'])
            j += 1
        if total >= PHONE_DIGITS and j - k >= 2 and not _counting(words[k:j]) \
                and len({norm_token(v['w']) for v in words[k:j]}) >= 3:
            found.append((words[k]['s'], words[j - 1]['e'], 'a phone number'))
        k = max(j, k + 1)
    found.sort()
    out = []
    for s, e, what in found:
        s, e = max(0.0, s - PAD_S), e + PAD_S
        if out and s <= out[-1][1]:
            out[-1] = (out[-1][0], max(out[-1][1], e), out[-1][2])
        else:
            out.append((round(s, 2), round(e, 2), what))
    return out


def subtract(ranges, private):
    """The clip's ranges with the private spans taken out (pieces under 0.5 s dropped)."""
    out = []
    for a, b in ranges:
        pieces = [[a, b]]
        for s, e, _ in private:
            nxt = []
            for x, y in pieces:
                if e <= x or s >= y:
                    nxt.append([x, y])
                    continue
                if s > x:
                    nxt.append([x, s])
                if e < y:
                    nxt.append([e, y])
            pieces = nxt
        out += [p for p in pieces if p[1] - p[0] >= 0.5]
    return out


def hide_lines(lines, private):
    """The transcript lines with every line touching a private span replaced by one marker line (the same
    shape as a break screen's), so the reading helpers never see or pick it."""
    if not private:
        return list(lines)
    from .common import fmt_ts
    out, open_span = [], None
    for ln in lines:
        hit = next((sp for sp in private if 's' in ln and 'marker' not in ln
                    and ln['s'] < sp[1] and sp[0] < ln['e']), None)
        if hit is None:
            out.append(ln)
            open_span = None
            continue
        if open_span is hit:
            out[-1]['n'] += 1
            out[-1]['e'] = max(out[-1]['e'], ln['e'])
        else:
            out.append({'s': ln['s'], 'e': ln['e'], 'n': 1, 'span': hit})
            open_span = hit
    for ln in out:
        if 'span' in ln:
            s, e, what = ln.pop('span')
            ln['marker'] = (f"# ===== PRIVATE DETAILS {fmt_ts(s).split('.')[0]}-{fmt_ts(e).split('.')[0]}: {what} said "
                            f"out loud; its {ln.pop('n')} line(s) are left out. Never in a clip =====")
    return out


def enabled(cfg):
    return str((cfg or {}).get('private_details', 'hide')).lower() != 'keep'


def wanted(project, cfg=None):
    """True when this video is checked: gameplay and streams ("hide", the default: viewers and friends read
    things out there), every video with "all", none with "keep"."""
    from .common import settings
    from .kind import is_irregular, stream_hint
    mode = str((settings() if cfg is None else cfg).get('private_details', 'hide')).lower()
    if mode == 'keep':
        return False
    return mode == 'all' or bool(is_irregular(project) or stream_hint(project))
