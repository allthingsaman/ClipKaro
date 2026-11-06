# Languages

ClipKaro writes down what's said using **Whisper**, a free speech model that knows about 99
languages. On top of that, ClipKaro has **extra care for English and for Hindi/Hinglish**: better
models, settings tuned for them, and captions designed for them. Most other languages work too,
just without that extra care. And developers can [add proper support for a new language](adding-a-language.md).

## Which languages work, and how well

| Language | How well | Found automatically? | Captions |
|---|---|---|---|
| **English** | ✅ fully supported | yes | bold capital letters |
| **Hinglish** (Hindi mixed with English) | ✅ fully supported | yes | **English letters** ("aaj hum business ki baat karenge") or Hindi letters |
| **Hindi** | ✅ fully supported (handled like Hinglish) | yes | English letters or Hindi letters |
| **Urdu (spoken)** | ⚠️ works, but written like Hindi | yes (treated as Hinglish) | English letters (they read like Roman Urdu) |
| Languages written in **Latin letters**: Spanish, Portuguese, French, German, Italian, Dutch, Polish, Turkish, Indonesian, Malay, Filipino, Vietnamese, Swahili, ... | 🟡 works, not fine-tuned yet | yes | bold capital letters |
| Languages written in **Cyrillic letters**: Russian, Ukrainian, Bulgarian, Serbian, Kazakh, ... | 🟡 works, not fine-tuned yet | yes | bold capital letters |
| **Other languages in Hindi letters**: Marathi, Nepali | 🟡 works, not fine-tuned yet | yes (if it says "Hinglish", tell Claude the right language) | Hindi letters, not changed to English letters |
| **Other scripts**: Bengali, Tamil, Telugu, Gujarati, Punjabi, Kannada, Malayalam, Arabic, Persian, Hebrew, Greek, Thai, Chinese, Japanese, Korean, ... | 🔧 the words are written down correctly, but the captions need a font added | yes | ClipKaro's fonts don't have these letters yet (you may see empty boxes): see [adding-a-language.md](adding-a-language.md) |

## English
- Without an NVIDIA graphics card, ClipKaro uses a smaller English-only model (`small.en`) that is
  quick and accurate. With an NVIDIA card it uses the big `large-v3-turbo` model.
- Captions are bold capital letters, 1-3 words at a time.

## Hindi and Hinglish
The language ClipKaro takes the most care of. The full story is in [hinglish.md](hinglish.md). In short:
- **Finding it**: the video is treated as Hinglish when Hindi (or Urdu) is the main language, or when
  English is the main language but at least a quarter sounds like Hindi. ClipKaro checks four
  different points of the video for this.
- **Listening**: always with the big `large-v3-turbo` model, which is far better at Hindi than the
  small ones. It listens in 30-second pieces, one at a time, so fast speech isn't cut off, and it's
  nudged to keep English words in English letters. If it skipped some speech, ClipKaro finds that
  part and listens to it again.
- **Written down as**: Hindi in Hindi letters, English in English letters: "आज हम business की बात करेंगे।"
- **Captions**: Claude writes every Hindi word of the chosen clips in English letters, so captions read
  "aaj hum business ki baat karenge". Prefer Hindi letters? Ask Claude, or set
  `"hinglish_captions": "devanagari"` in `settings.json`.
- **Speed**: without an NVIDIA graphics card, this big model is slow: 1 to 4 times the length of the
  video. An NVIDIA card is strongly recommended for Hindi/Hinglish videos.

## Other languages
- **Found automatically**, but you can always say it: tell Claude "the video is in Spanish". (By hand:
  `python run.py fetch <link> --lang es`. The codes are Whisper's, see
  [the full list](https://github.com/openai/whisper/blob/main/whisper/tokenizer.py): `es` Spanish,
  `fr` French, `de` German, `pt` Portuguese, `bn` Bengali, `ta` Tamil, `ar` Arabic, ...)
- **Accuracy**: without an NVIDIA card, other languages use the smaller multilingual model (`small`).
  For better results, ask Claude to "use the big model" (`--model large-v3-turbo`, slower), or use an
  NVIDIA card (which uses the big model automatically). Whisper is excellent for widely spoken
  languages and weaker for rare ones.
- **Choosing the moments**: Claude reads what's said in that language. It understands most languages
  well. Titles and captions to post are written in the video's language, unless you ask otherwise.
- **Where sentences end**: ClipKaro knows the full stop `.`, `?`, `!` and the Hindi `।`. Languages that
  end sentences with other marks (Chinese and Japanese `。`, Arabic `؟`, Urdu `۔`, ...) still work, but
  ClipKaro is a little less precise about where sentences end.
- **Caption letters**: captions use the video's own alphabet. ClipKaro's fonts have English/European
  letters, Cyrillic, and Hindi letters. Other alphabets need a font added: see
  [adding-a-language.md](adding-a-language.md).
- **Chinese, Japanese, Thai** (no spaces between words): everything works, but looking up an exact
  phrase may need single words.

## Choosing the language yourself
| How | Example |
|---|---|
| Tell Claude | "clip this video, it's in Hinglish: https://youtu.be/..." |
| Fix a wrong guess | "the language is wrong, it's English: please do it again" |
| Always the same language | ask Claude "add to my preferences: my videos are in English", or set `"language": "en"` in `settings.json` |
| By hand | `python run.py fetch <link> --lang hinglish` (add `--retranscribe` to redo one) |

## Want better support for your language?
See [adding-a-language.md](adding-a-language.md) (for developers). It explains three levels: using a
language as it is, giving it proper captions (font, punctuation, capital letters), and building a full
mixed mode like Hinglish (Tanglish, Banglish, Spanglish, ...).
