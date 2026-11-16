"""Who speaks each line of the transcript: one voice print per line, grouped into voices.

    python run.py voices <project>       (fetch runs it by itself for gameplay and live streams)

Why: in a gameplay stream the transcript mixes the streamer's own voice with the game's characters
(often English lines in a Hinglish stream). Clips should be built around the streamer's commentary
and reactions, and Claude can't always tell from the words alone who said a line. Each line gets a
voice; the voice that talks most over the whole video is the main voice (the streamer). In gameplay
videos, lines in another voice are marked "(other voice)" in the transcript Claude reads.

It also gives the sound hints a baseline per speaker (how loud and how high each voice usually is),
so a raised voice is measured against that person's own normal, not against everyone in the video.

How: the 3D-Speaker ERes2Net voice model (VoxCeleb, Apache 2.0; the same one the two-person framing
uses), run by sherpa-onnx, on each line's words (up to 6 s). Lines with less than MIN_SPEECH of words
get the voice of the line next to them when it is close, else none. The voice with the most lines is
found first (find_voices), then up to two more among the lines unlike it. About a minute of CPU per
hour of video. Research (Nov 2026) found that
separating the voice from the game's music before writing it down makes speech recognition worse, not
better (2025-26 studies), while voice prints tell voices apart well on lines of 2 s or more; so the
voices are told apart, and the sound Whisper hears is left as it is. A recording with the microphone
on its own audio track is better still: fetch transcribes that track (fetch.mic_track).

Writes transcript/voices.json:
  {"v": 1, "main": 0, "voices": {"0": {"seconds": .., "lines": ..}, ..},
   "lines": [[start, end, voice or null, likeness to the main voice], ...]}   (one per sentences.json line)
"""
import argparse
import os
import time

import numpy as np

from .common import die, load_json, project_dir, save_json
from . import speakers

VOICES_V = 1
SR = 16000
MIN_SPEECH = 1.0           # seconds of words a line needs for its own voice print
MAX_SPEECH = 6.0           # at most this much of a line goes into its voice print
NEIGHBOUR_GAP = 1.5        # a short line takes the voice of a line at most this far away
NEAR = 0.5                 # a line this like a voice (cosine of the voice prints) is that voice
MAX_VOICES = 3             # the main voice, and up to two more (a podcast guest, a game character)
MIN_SHARE = 0.08           # a voice needs at least this share of the lines with a print
OTHER_MAX_LIKE = 0.35      # "(other voice)" only when the line is this unlike the main voice ...
OTHER_MIN_S = 1.5          # ... and lasts at least this long
# Tuned on two gameplay streams (Nov 2026): lines marked "other voice" were 72-76 % English words (the
# game's characters; the rest mostly Whisper's nonsense over game sound), lines in the main voice 15-18 %
# (the streamer's Hinglish). Grouping all prints at once (sherpa-onnx clustering) split one stream into
# 144 "voices": prints of short lines over game sound vary too much, so voices are found one at a time.


def line_audio(audio, words, line, pad=0.05):
    """The line's words, joined (pauses left out), up to MAX_SPEECH seconds."""
    chunks, total = [], 0.0
    for w in words[line['i0']:line['i1'] + 1]:
        a, b = max(0.0, w['s'] - pad), w['e'] + pad
        if b - a <= 0:
            continue
        chunks.append(audio[int(a * SR):int(b * SR)])
        total += b - a
        if total >= MAX_SPEECH:
            break
    return (np.concatenate(chunks) if chunks else np.zeros(0, np.float32)), total


def prints_for(audio, words, lines):
    """[unit voice print or None] per line."""
    import sherpa_onnx
    path = speakers.model_file('voice')
    if not path:
        return None
    ext = sherpa_onnx.SpeakerEmbeddingExtractor(sherpa_onnx.SpeakerEmbeddingExtractorConfig(
        model=str(path), num_threads=max(1, min(4, (os.cpu_count() or 4) - 1))))
    out = []
    for ln in lines:
        if 'i0' not in ln:
            out.append(None)
            continue
        x, speech = line_audio(audio, words, ln)
        if speech < MIN_SPEECH or len(x) < SR // 2:
            out.append(None)
            continue
        st = ext.create_stream()
        st.accept_waveform(SR, x)
        st.input_finished()
        e = np.array(ext.compute(st), dtype=np.float32)
        out.append(e / (np.linalg.norm(e) or 1.0))
    return out


def dominant(X):
    """The voice print of the voice with the most lines: the line with the most lines like it is the
    core; their mean, refined three times on the lines like it, is the voice."""
    sim = X @ X.T
    core = int(np.argmax((sim >= NEAR).sum(1)))
    c = X[sim[core] >= NEAR].mean(0)
    for _ in range(3):
        c /= np.linalg.norm(c) or 1.0
        near = X @ c >= NEAR
        if not near.any():
            break
        c = X[near].mean(0)
    return c / (np.linalg.norm(c) or 1.0)


def find_voices(prints):
    """-> (voice prints, label per line or None). Voices are found one after another, each among the
    lines unlike the voices found so far."""
    idx = [i for i, p in enumerate(prints) if p is not None]
    labels = [None] * len(prints)
    if not idx:
        return [], labels
    X = np.stack([prints[i] for i in idx])
    found, avail = [], np.arange(len(idx))
    while len(found) < MAX_VOICES and len(avail) >= 10:
        c = dominant(X[avail])
        if (X[avail] @ c >= NEAR).sum() < max(5, MIN_SHARE * len(idx)):
            break
        found.append(c)
        avail = avail[(X[avail] @ np.stack(found).T).max(1) < OTHER_MAX_LIKE]
    if not found:
        return [], labels
    sims = X @ np.stack(found).T
    for k, i in enumerate(idx):
        j = int(np.argmax(sims[k]))
        labels[i] = j if sims[k, j] >= NEAR else None
    return found, labels


def fill_short(lines, labels):
    """A line too short for its own print takes the voice of the nearest line within NEIGHBOUR_GAP."""
    out = list(labels)
    for i, lab in enumerate(labels):
        if lab is not None or 's' not in lines[i]:
            continue
        best = None
        for j in (i - 1, i + 1):
            if 0 <= j < len(lines) and labels[j] is not None and 's' in lines[j]:
                gap = lines[i]['s'] - lines[j]['e'] if j < i else lines[j]['s'] - lines[i]['e']
                if gap <= NEIGHBOUR_GAP and (best is None or gap < best[0]):
                    best = (gap, labels[j])
        if best:
            out[i] = best[1]
    return out


def analyse(audio, words, lines):
    """-> voices dict (see the module text), or None without the voice model."""
    prints = prints_for(audio, words, lines)
    if prints is None:
        return None
    found, labels = find_voices(prints)
    if not found:
        return None
    labels = fill_short(lines, labels)
    secs = {}
    for ln, lab in zip(lines, labels):
        if lab is not None and 's' in ln:
            secs.setdefault(lab, [0.0, 0])
            secs[lab][0] += ln['e'] - ln['s']
            secs[lab][1] += 1
    if not secs:
        return None
    main = max(secs, key=lambda k: secs[k][0])
    rows = []
    for ln, lab, p in zip(lines, labels, prints):
        if 's' not in ln:
            rows.append(None)
            continue
        like = round(float(p @ found[main]), 3) if p is not None else None
        rows.append([round(ln['s'], 2), round(ln['e'], 2), lab, like])
    return {'v': VOICES_V, 'main': main,
            'voices': {str(k): {'seconds': round(v[0], 1), 'lines': v[1]} for k, v in sorted(secs.items())},
            'lines': rows}


def is_other(row, main):
    """A line in another voice than the main one, confidently: unlike the main voice, long enough to judge."""
    if not row:
        return False
    s, e, lab, like = row
    return lab != main and like is not None and like < OTHER_MAX_LIKE and e - s >= OTHER_MIN_S


def rows_for(v, lines):
    """The voices row of each sentence line, matched by start time (the transcript can be rewritten
    after the voices were measured: a repaired word, a caption fix); None where none matches."""
    by_start = {round(r[0], 2): r for r in (v or {}).get('lines') or [] if r}
    return [by_start.get(round(ln['s'], 2)) if 's' in ln else None for ln in lines]


def other_lines(v, lines=None):
    """Indexes of the sentence lines spoken in another voice than the main one."""
    if not v:
        return set()
    rows = rows_for(v, lines) if lines is not None else v['lines']
    return {i for i, row in enumerate(rows) if is_other(row, v['main'])}


# ---------- game characters' lines: no captions (v2.3) ----------
# In a gameplay video the game shows its own subtitles, so ClipKaro's captions show only the streamer
# (the owner's wish, Nov 2026: a captioned game line appeared twice on screen). With a Hindi / Hinglish
# streamer the game's characters speak English, so a game line is one that is (a) unlike the streamer's
# voice (or too short for a voice print and right next to a game line) and (b) mostly English; inside it,
# the streamer's Hindi words keep their captions. The sound stays, and the line stays in the transcript,
# so Claude can still pick a great game scene. `"game_voice_captions": true` shows them again.
GAME_MAX_LIKE = 0.35       # unlike the streamer's voice
GAME_ENGLISH = 0.6         # at least this share of the line's words is English
GAME_NEAR_S = 2.0          # a short line within this gap of a game line counts with it
# words only Hindi / Hinglish uses, in English letters (the Hinglish model writes Hindi this way)
HINDI_COMMON = set("""hai hain ho hoga hogi honge tha thi the thhe ka ki ke ko se mein me mai main mujhe mera meri mere
tera teri tere tu tum tumhe aap aapka aapki apna apni apne hum ham humne hamne hamara hamari ye yeh yah wo woh vo vah
kya kyun kyon kyunki kyonki kaise kahan kab kaun kitna kitne nahi nahin na mat bhi aur ya to toh par pe bas abhi
ab phir fir sab kuch kuchh koi ek do teen bahut bohot zyada thoda accha achha achchha theek thik haan han bhai
yaar yar arre are oye chal chalo dekho dekh suno bolo bol kar karo karna karte karta karti kiya kiye karenge raha
rahi rahe gaya gayi gaye diya diye liya liye de do le lo jao jaa ja jaana aaya aayi aaye aa lag laga lagta lagti
wala wali wale wahan vahan yahan idhar udhar matlab lekin magar jab tab agar waise aise kaisa jaisa bilkul
sahi galat pehle baad saath upar neeche andar bahar ghar paisa paise log logon""".split()) - {
    'the', 'to', 'do', 'me', 'main', 'are', 'log', 'lag', 'ya', 'par', 'mat'}   # also everyday English words


def is_hindi_word(word):
    """A Hindi word: in Hindi letters, or one of the common Hindi words in English letters."""
    from .common import has_devanagari, norm_token
    return has_devanagari(word) or norm_token(word) in HINDI_COMMON


def game_words(pdir, project, words, lines=None, v=None):
    """Indexes (in words.json) of the words a game character says in a gameplay video with a Hindi /
    Hinglish streamer: their captions are left out. Empty for every other video, or without voices."""
    from .common import norm_token
    from .fetch import is_hindi
    from .kind import is_irregular
    if not (is_irregular(project) and is_hindi(project.get('language') or '')):
        return set()
    v = v or load(pdir)
    lines = lines if lines is not None else load_json(pdir / 'transcript' / 'sentences.json') or []
    if not v or not lines:
        return set()
    rows = rows_for(v, lines)

    def english(ln):
        ws = [w for w in words[ln['i0']:ln['i1'] + 1] if norm_token(w['w']) and not w.get('unsure')]   # shown words
        return bool(ws) and sum(not is_hindi_word(w['w']) for w in ws) >= GAME_ENGLISH * len(ws)

    real = [i for i, ln in enumerate(lines) if 'i0' in ln]
    game = {i for i in real if rows[i] and rows[i][3] is not None and rows[i][3] < GAME_MAX_LIKE and english(lines[i])}
    def near_game(i):
        ln = lines[i]
        return [j for j in (i - 1, i + 1) if 0 <= j < len(lines) and j in game and 's' in lines[j]
                and min(abs(lines[j]['s'] - ln['e']), abs(ln['s'] - lines[j]['e'])) <= GAME_NEAR_S]

    grown = True
    while grown:
        grown = False
        for i in real:
            if i in game or not english(lines[i]):
                continue
            like = rows[i][3] if rows[i] else None
            # a short line (no voice print, or rewritten since) next to a game line joins it; a line only
            # somewhat like the streamer joins when game lines sit on both sides of it
            if (like is None and near_game(i)) or (like is not None and like < NEAR and len(near_game(i)) == 2):
                game.add(i)
                grown = True
    return {k for i in game for k in range(lines[i]['i0'], lines[i]['i1'] + 1) if not is_hindi_word(words[k]['w'])}


def load(pdir):
    v = load_json(pdir / 'transcript' / 'voices.json')
    return v if v and v.get('v') == VOICES_V else None


def scan(pdir, quiet=False):
    wav = pdir / 'source' / 'audio16k.wav'
    words = load_json(pdir / 'transcript' / 'words.json')
    lines = load_json(pdir / 'transcript' / 'sentences.json')
    if not wav.exists() or not words or not lines:
        return None
    import soundfile as sf
    t = time.time()
    audio, _ = sf.read(str(wav), dtype='float32')
    try:
        v = analyse(audio, words, lines)
    except ImportError:
        v = None
    if v is None:
        if not quiet:
            print('   (voices skipped: the voice model or sherpa-onnx is not available)')
        return None
    v['seconds_taken'] = round(time.time() - t, 1)
    save_json(pdir / 'transcript' / 'voices.json', v)
    if not quiet:
        main = v['voices'][str(v['main'])]
        n_other = len(other_lines(v))
        print(f"-> voices in {v['seconds_taken']:.0f}s: {len(v['voices'])} voice(s); the main one speaks "
              f"{main['seconds'] / 60:.0f} min in {main['lines']} lines; {n_other} line(s) clearly in another voice")
    return v


def ensure(pdir, quiet=False):
    return load(pdir) or scan(pdir, quiet=quiet)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('project')
    a = ap.parse_args()
    pdir = project_dir(a.project)
    if scan(pdir) is None:
        die(f'no audio or transcript in {pdir}: run `python run.py fetch` first')


if __name__ == '__main__':
    main()
