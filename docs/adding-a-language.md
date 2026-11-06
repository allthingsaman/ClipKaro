# Adding a language

**In simple words:** most languages already work in ClipKaro (see [languages.md](languages.md)).
Making a new language work *really well* means up to three things: making sure the speech model
hears it well, giving the captions a font that has its letters, and (if creators mix it with
English, like Hinglish) writing its words in English letters for the captions. This page shows how,
step by step. It involves changing a few lines of code, so it's meant for developers. If you're not
one, you can ask Claude Code to follow this page for you, for example: "follow
docs/adding-a-language.md and add Tamil".

This guide is for developers who want ClipKaro to handle a new language well. Read
[languages.md](languages.md) first: many languages already work at a basic level without any
change.

There are three levels. Do only as much as your language needs:

| Level | When you need it | Work |
|---|---|---|
| **1. Use it as is** | Latin or Cyrillic script, and Whisper already transcribes it well | none: `--lang <code>` |
| **2. Proper captions** | the language uses another script (Bengali, Tamil, Arabic, ...) or other punctuation | add a font + a few lines of code |
| **3. A mixed mode** like Hinglish | creators mix it with English (Tanglish, Banglish, Spanglish, ...) and you want Roman captions | detection, decoding, romanization, a style guide |

The worked example at the end adds **Tamil + Tanglish**.

Background: [architecture.md](architecture.md) explains the pipeline these steps plug into.

---

## Level 1: use the language as is

1. Find its Whisper code in
   [whisper/tokenizer.py](https://github.com/openai/whisper/blob/main/whisper/tokenizer.py)
   (`LANGUAGES`): for example `es`, `bn`, `ta`, `ar`.
2. Run a test video:
   ```bash
   python run.py fetch "<video>" --lang <code>
   ```
   Auto-detection usually gets it right too; `--lang` just removes the guesswork.
3. Read `output/<project>/transcript/transcript.txt`. If the words are right, you're done: picking,
   cutting and editing work for any language.
4. **Accuracy not good enough?**
   - Use the big model: `--model large-v3-turbo`, or `--model large-v3` (most accurate, slowest).
     An NVIDIA GPU uses `large-v3-turbo` automatically.
   - Use a **fine-tuned model** for your language. `--model` also accepts a Hugging Face repo id
     (`someone/whisper-tamil-ct2`) or a local folder, as long as it's in CTranslate2 format (the
     folder has `model.bin`, `config.json`, `tokenizer.json`, `preprocessor_config.json`,
     `vocabulary.*`). Convert a regular Whisper model from Hugging Face with:
     ```bash
     pip install ctranslate2 transformers[torch]
     ct2-transformers-converter --model <hf-whisper-model> --output_dir whisper-xx-ct2 \
         --copy_files tokenizer.json preprocessor_config.json --quantization float16
     ```
     Then `python run.py fetch "<video>" --model ./whisper-xx-ct2`. You can also set it as the
     default with `"model"` in `settings.json`.

---

## Level 2: proper captions for a new script

### Step 1: add a font
Captions are drawn with the fonts in `assets/fonts/`. Montserrat covers Latin and Cyrillic, and
Poppins covers Latin and Devanagari. For any other script, add a bold font that has **both your
script and Latin letters**, so mixed captions stay in one style.

- Pick an open-licence font (SIL Open Font License), e.g. from [Google Fonts](https://fonts.google.com).
  Good matches for the bold short-form look: an **ExtraBold** or **Black** weight.
- Copy the `.ttf` into `assets/fonts/`, and its licence next to it (`OFL-<Font>.txt`).
- Find the font's family name, which the caption renderer needs:
  ```bash
  fc-query -f '%{family}\n' assets/fonts/YourFont-ExtraBold.ttf     # Linux/macOS with fontconfig
  ```
  It prints something like `Mukta Malar,Mukta Malar ExtraBold`: use the last name.
- Add the font to the third-party list in `LICENSE` and to the credits in `README.md`.

### Step 2: teach ClipKaro to recognise the script
`clipper/common.py` has `has_devanagari()`. Add a general helper next to it:

```python
SCRIPTS = {                        # Unicode blocks of the scripts ClipKaro handles specially
    'devanagari': ('ऀ', 'ॿ'),
    'tamil': ('஀', '௿'),       # add yours: https://en.wikipedia.org/wiki/Unicode_block
}


def has_script(text, script):
    lo, hi = SCRIPTS[script]
    return any(lo <= c <= hi for c in text or '')
```

### Step 3: choose the font, case and spacing
In `clipper/plan.py`, `build()` picks the caption font. Add yours the same way Devanagari is
handled:

```python
TAMIL_FONT = ('Mukta Malar ExtraBold', 'MuktaMalar-ExtraBold.ttf')   # (family name, file in assets/fonts)

def build(meta, brand, opts):
    ...
    hindi = any(has_devanagari(w['w']) for w in meta['words'])
    tamil = any(has_script(w['w'], 'tamil') for w in meta['words'])
    native = hindi or tamil
    # scripts without capital letters stay in normal case (only the Latin words would shout)
    upper = opts.get('uppercase', True) and not native
    caps = caption_groups(meta, upper=upper) if opts.get('captions', True) else []
    font, font_file = (opts['font'], opts['font_file']) if opts.get('font') else \
        (HINDI_FONT if hindi else TAMIL_FONT if tamil else LATIN_FONT)
    ...
            # letter spacing breaks the shaping of complex scripts: keep it at 0 for them
            'spacing': 0 if native else 1,
```

- **Case**: keep UPPERCASE only for scripts that have capitals (Latin, Cyrillic, Greek, Armenian).
- **Spacing**: any script whose letters join or combine (Indic scripts, Arabic, Thai, ...) needs
  spacing 0.
- **Right-to-left scripts** (Arabic, Persian, Urdu, Hebrew): libass handles the text direction;
  check a rendered frame to make sure word order looks right.
- The Remotion engine needs nothing extra: `edit.py` copies the chosen font file into
  `remotion/public/fonts/` automatically.

### Step 4: sentence-ending punctuation
ClipKaro uses sentence ends to split transcript lines, to warn about cuts in mid-sentence and to
time zooms. They're defined in `clipper/common.py`:

```python
SENT_END = '.?!।॥'                 # add yours, e.g. '。！？' (Chinese/Japanese), '؟' (Arabic), '۔' (Urdu)
```

Also add them to `STRIP` in `clipper/plan.py`, the punctuation removed from the end of caption
words:

```python
STRIP = re.compile(r'[.,;:।॥]+$')  # e.g. r'[.,;:।॥。，、؟،۔]+$'
```

### Step 5: decoding glitches (optional)
`clean_words()` in `clipper/fetch.py` removes a vowel sign looping inside a Devanagari word
("हूँँँँँ"). If your script shows the same glitch, include it in that check
(`if has_devanagari(t) or has_script(t, 'tamil'):`).

### Step 6: test
```bash
python run.py fetch "<test video>" --lang <code>
# write a small clips.json (or let the agent pick), then:
python run.py cut <project>
python run.py edit <project> --clips 1
ffmpeg -ss 5 -i output/<project>/edited/01-*.mp4 -frames:v 1 frame.png    # look at the captions
```
Check that there are no empty boxes, the letters are shaped correctly, and the words appear in
the right order. Then run an English video and a Hinglish video once more, to make sure nothing
else changed.

---

## Level 3: a mixed mode like Hinglish

Creators often mix their language with English ("Hinglish", "Tanglish", "Banglish", "Spanglish").
Viewers usually read such captions in **Roman letters**. Hinglish in ClipKaro shows the full
pattern; copy it.

### Step 1: name the mode and its aliases
In `clipper/fetch.py`:
```python
TANGLISH = 'tanglish'
LANG_ALIASES = {..., 'tanglish': TANGLISH, 'tamil-english': TANGLISH, 'tamil': 'ta'}
```

### Step 2: detection
`resolve_language()` averages Whisper's guesses over four windows. Hinglish wins when Hindi/Urdu
is on top, or when English is on top but Hindi + Urdu reach 25 %. Add a rule for your mode:
```python
    if top == 'ta' or (top == 'en' and probs.get('ta', 0.0) >= 0.25):
        return TANGLISH, ranked
```
Tune the 25 % on a few real videos: print `ranked` to see the numbers.

### Step 3: model and decoding
Add a helper like `is_hindi()` and use it in the same places:
```python
def is_tamil(lang):
    return lang in (TANGLISH, 'ta')
```
- `pick_model()`: use `large-v3-turbo` for it (smaller models are weak on most non-English
  languages).
- `_transcribe_once()`: pass Whisper the real language code (`language = 'ta'` for Tanglish), and
  use the **sequential** decoding branch the Hindi path uses. Non-Latin scripts need several times
  more tokens than English, and sequential decoding resumes where a 30-second window ran out
  instead of dropping words.
- **The primer sentence** (`hotwords`): Whisper copies the style of the text it's primed with.
  Write one natural sentence in your mode, with your language in its own script and English words
  in Roman, like `HINGLISH_PROMPT`:
  ```python
  TANGLISH_PROMPT = 'நான் இந்த video-வை last week record பண்ணேன், இதுல நிறைய important points இருக்கு.'
  ```
  Have a native speaker check it: it sets the style of the whole transcript.
- `write_transcript()`: add a header note like the Hinglish one, so the AI editor knows how the
  transcript is written.

### Step 4: Roman captions
`clipper/romanize.py` lists the native-script words of the picked clips in `romanize.json`, the AI
editor fills in Roman spellings, and `edit` uses them in the captions (timings never change).

- Add your mode to `ROMAN_FOR = ('hinglish', 'hi', 'ur', 'tanglish', 'ta')`.
- Where it checks `has_devanagari(core)`, check your script too (or use a small
  `native(text)` helper that checks every script in `SCRIPTS`).
- Give users a switch like `hinglish_captions`: add e.g. `'tanglish_captions': 'roman'` to
  `DEFAULT_SETTINGS` in `common.py` and read it in `wants_roman()`.
- If your script has its own full stop, map it in `_PUNCT` (`'।': '.'` is the Hindi one).

### Step 5: a style guide for the AI editor
Write `docs/<mode>.md` like [hinglish.md](hinglish.md): how the transcript looks, and **how people
in that community type the language in Roman letters** (common words, vowel length, how English
words are kept, names). The quality of the Roman captions comes from this guide.

### Step 6: tell the AI editor about it
- `.claude/skills/clip-video/SKILL.md`, section "2b": mention your mode and link its style guide.
- `CLAUDE.md` (and `AGENTS.md` if you changed agent instructions): one line saying that videos in
  your mode get Roman captions, and where the guide is.

### Step 7: test end to end
1. Auto-detection on 2-3 real videos: does `fetch` print `detected language: tanglish`?
2. The transcript: native script for the language, Roman for the English words, nothing skipped.
3. `romanize` lists the words; fill them; `romanize` again prints clean Roman captions.
4. `cut --check`, `cut`, `edit`; look at a few frames.
5. Run an English and a Hinglish video again (nothing else should change).
6. Update the table in [languages.md](languages.md).

---

## Worked example: Tamil and Tanglish (summary)

| File | Change |
|---|---|
| `assets/fonts/` | add `MuktaMalar-ExtraBold.ttf` + `OFL-MuktaMalar.txt` (Tamil + Latin, SIL OFL) |
| `clipper/common.py` | `SCRIPTS` + `has_script()`; `'tanglish_captions': 'roman'` in `DEFAULT_SETTINGS` |
| `clipper/plan.py` | `TAMIL_FONT`; font, case and spacing choice in `build()` |
| `clipper/fetch.py` | `TANGLISH`, aliases, the detection rule, `is_tamil()`, the model choice, sequential decoding with `language='ta'` and `TANGLISH_PROMPT`, the transcript header note |
| `clipper/romanize.py` | `ROMAN_FOR` + the Tamil script check + `wants_roman()` reads `tanglish_captions` |
| `docs/tanglish.md` | the Roman Tamil spelling guide |
| `.claude/skills/clip-video/SKILL.md`, `CLAUDE.md` | point the AI editor to the guide |
| `docs/languages.md`, `LICENSE`, `README.md` | the support table, the font's licence and credit |

If you add support for a language, please share it with a pull request:
[CONTRIBUTING.md](../CONTRIBUTING.md).
