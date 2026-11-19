"""Abusive and taboo words written with stars: "F******", "bh*******", "चू**".

The owner's choice (2026-11-19): nothing is cut, bleeped or muted, and the viewer hears every word. Only the
text shows stars: the captions on screen, the .srt and the posting texts, because the apps read text
first. The transcript, the critic and Claude always see the real words; stars are added when a clip is
edited or posted. Way back: settings.json "star_words": false shows every word in full.

Which words: a short built-in list of clear swear words and gaali (English, Roman Hinglish, Devanagari),
plus the words Claude marks for a clip in clips.json ("stars": ["word as said or as captioned", ...]):
slurs, sexual words and any other spelling the list doesn't know.
"""
import re
import unicodedata

from . import common
from .common import norm_token

# a word is starred when its plain form starts with one of these (fucking, chutiye, bhosdike ...)
ROOTS = [
    'fuck', 'motherfuck', 'mothafuck', 'shit', 'bullshit', 'bitch', 'asshole', 'arsehole', 'bastard', 'cunt',
    'dickhead', 'jackass', 'wanker',
    'chutiy', 'chutia', 'chootiy', 'bhenchod', 'bhencho', 'behenchod', 'behnchod', 'bhanchod', 'benchod',
    'madarchod', 'maderchod', 'madarchoo', 'bhosd', 'bhosad', 'bhosri', 'gaandu', 'gandu', 'gaand', 'lauda',
    'lawda', 'lavda', 'laude', 'lawde', 'lavde', 'lodu', 'haramkhor', 'haraamkhor', 'haramzad', 'haraamzad',
    'jhaant', 'jhantu', 'randiy',
    'चूतिय', 'चुतिय', 'भेनचोद', 'भैनचोद', 'बहनचोद', 'बेहेनचोद', 'बेंचोद', 'मादरचोद', 'भोसड', 'गांडू', 'गांड',
    'गाँड', 'लौड', 'लवड', 'हरामखोर', 'हरामजाद', 'झांट',
]
# ... or is exactly one of these (short words that are also the start of harmless ones)
EXACT = ['dick', 'dicks', 'pussy', 'pussies', 'cock', 'cocks', 'tits', 'twat', 'slut', 'sluts', 'whore', 'whores',
         'lund', 'randi', 'harami', 'bsdk', 'लंड', 'रंडी', 'हरामी']

_ROOTS = tuple(sorted({norm_token(r) for r in ROOTS} - {''}))
_EXACT = {norm_token(w) for w in EXACT} - {''}
_WORD = re.compile(r'\S+')


def on(cfg=None):
    """settings.json "star_words" (true by default)."""
    return (cfg if cfg is not None else common.settings()).get('star_words', True) is not False


def marks(words):
    """clips.json "stars" -> the plain forms to match."""
    return {norm_token(str(w)) for w in (words or [])} - {''}


def is_rude(word, marked=frozenset()):
    """True for a word on the built-in list or one Claude marked for this clip."""
    n = norm_token(word or '')
    return bool(n) and (n in marked or n in _EXACT or n.startswith(_ROOTS))


def star(word):
    """'FUCKING' -> 'F******', 'chutiye!' -> 'c******!', 'चूतिया' -> 'चू**': the first letter (with its vowel
    signs) stays, every later letter becomes one star; punctuation stays where it is."""
    out, state = [], 'before'              # before the first letter / inside it / after it
    for ch in word:
        cat = unicodedata.category(ch)[0]
        if cat == 'M':                     # a vowel sign or nukta belongs to the letter before it
            if state != 'rest':
                out.append(ch)
        elif cat in 'LN':
            if state == 'before':
                out.append(ch)
                state = 'first'
            else:
                out.append('*')
                state = 'rest'
        else:
            out.append(ch)
    return ''.join(out)


def star_text(text, marked=frozenset()):
    """Every rude word in a sentence starred (posting texts, the hook title); the rest exactly as it was."""
    if not text:
        return text
    return _WORD.sub(lambda m: star(m.group(0)) if is_rude(m.group(0), marked) else m.group(0), text)
