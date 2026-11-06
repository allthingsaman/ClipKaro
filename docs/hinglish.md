# Hindi / Hinglish videos

ClipKaro is made for Hindi and Hinglish (Hindi mixed with English) videos as much as for English
ones. This page explains how they're handled. It's also the spelling guide Claude follows when it
writes the captions.

## How the transcript looks
`fetch` finds Hindi/Hinglish by itself (`language: hinglish` in project.json and at the top of
transcript.txt) and writes down the words with Whisper's big `large-v3-turbo` model. It's nudged to
write **Hindi in Hindi letters (Devanagari) and English words in English letters**, with `।` (the
Hindi full stop, "danda") at the end of sentences:

```
[12.40-17.85] तो आज मैं आपको बताऊँगा कि content creation में लोग सबसे बड़ी गलती क्या करते हैं।
```
Some English words still come out in Hindi letters (`वीडियो`, `बिज़नेस`). That's normal.

If the language is found wrongly, say which one it is: `--lang hinglish` (or `--lang en` for an
English video), with `--retranscribe` if the words were already written down. Or just tell Claude.

## Picking clips
- Read and judge the Hindi text the same way as English. The hook types and rules are the same.
- `hook`: copy the first line exactly as it appears in the transcript (Hindi letters are fine).
- `title` and `caption` (the text to post with the video): write them in **Roman Hinglish** (Hindi
  in English letters), the way the creator's audience types. Example: "Consistency > Perfection.
  Pehla video 3 hafte, sirf 12 views..."
- `emphasis`: give the English-letter spelling you'll use in romanize.json (`"consistency"`, `"12"`,
  `"galti"`). The Hindi-letter form works too.
- `run.py find` takes the phrase in the transcript's own letters: `find <project> "सबसे बड़ी गलती"`.

## Captions in English letters (`run.py romanize`)
Unless settings.json says `"hinglish_captions": "devanagari"`, captions are shown in English letters
(Roman Hinglish). After writing clips.json:

1. `python run.py romanize <project>`: adds every Hindi word in the picked clips to
   `output/<project>/romanize.json` with an empty value, and prints each clip's text for context.
2. Fill in **every** value (write the whole file back; keep the keys exactly as they are).
3. Run `python run.py romanize <project>` again. When it's complete, it prints each clip's caption
   text in English letters. Read it once as a viewer would, and fix anything that looks off.

`edit` uses this list automatically; the timing of each word doesn't change. Words left empty stay
in Hindi letters (drawn with the Poppins font, which has Hindi letters).

### Spelling style (how Indian creators type Hinglish)
- Plain English letters, no accents, lower case: `hai`, `hain`, `nahi`, `kya`, `kyunki`,
  `bahut`, `zyada`, `accha`, `theek`, `kaise`, `karenge`, `chahiye`, `log`, `aaj`, `abhi`.
- Common pairs: में `mein`, मैं `main`, है `hai`, हैं `hain`, और `aur`, तो `to`, भी `bhi`,
  ये `ye`, वो `wo`, क्या `kya`, क्यों `kyun`, यहाँ `yahan`, वहाँ `wahan`, ज़रूर `zaroor`.
- Long vowels only where people write them: `aap`, `baat`, `teen`, `poora`, `pehle`, `doston`.
- **English words in their English spelling**, even when Whisper wrote them in Hindi letters:
  `वीडियो` → `video`, `बिज़नेस` → `business`, `कंटेंट` → `content`, `सब्सक्राइब` → `subscribe`.
- Names and brands with a capital letter: `YouTube`, `Instagram`, `Delhi`, `iPhone`.
- Number words can become digits when that reads better in a caption: `बारह` → `12`.
- One key → usually one word. Two words are fine when Whisper joined them (`मेही` → `mein hi`).
- Fix an obvious Whisper misspelling when the context makes the intended word certain
  (`चाते` in "बनाना चाते हैं" → `chahte`). Never change the meaning or add words.
- A name Whisper wrote in English letters but spelled wrongly (for example "Raghav Jayal" for
  Raghav Juyal) isn't in romanize.json: fix it in `transcript/words.json` before cutting.

## Speed
Hindi/Hinglish always uses the big model. With an NVIDIA graphics card that takes a few minutes even
for a long video. Without one it's slow: 1 to 4 times the length of the video (not recommended).
