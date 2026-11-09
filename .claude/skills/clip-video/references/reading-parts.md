# Reading one part of a long video

Long transcripts are read in parts (`python run.py parts <project>`), one reader per part, all at
the same time. You are one of those readers. Your answer is joined with the others by code
(`python run.py topics <project>`), so follow the format exactly.

## Your job
1. **Read your whole part file** (`output/<project>/parts/part-NN.txt`). If the reader tool shows a
   PARTIAL view, keep reading with offset/limit until the TASK lines at the end.
2. **Only your stretch counts.** The lines between `===== YOUR STRETCH STARTS =====` and
   `===== YOUR STRETCH ENDS =====` are yours. The lines before and after are context, so you
   understand what is going on; another reader owns them.
3. Write `output/<project>/parts/part-NN.json` (the path is in the TASK lines), then reply in at most
   5 lines: how many topics and candidates, and anything that went wrong.

Work in this order, in one reading: first the topics, then the best moment of every 5-minute
block, then the clip candidates. Understand the part before you choose.

## Copy, never invent
- **Times:** copy the start number of a line exactly as it is printed: `[2412.36-2419.80] ...` → `2412.36`.
  Never work out a time yourself. Code turns your quotes into exact word times.
- **Words:** quote the transcript's own words exactly, in its own script and spelling, mistakes
  included (`दूपते जाद का कफ्तान`, not the correct Hindi and not English letters). Quotes are
  checked against the transcript; a quote that isn't found is an error. Dots under letters
  (nukta: ख़ / ख), punctuation and capital letters don't matter for the check, so quote any line.
- **Quote length:** where 5 or more words are asked for, a line with fewer words is quoted whole
  (`"आप KBC कैसे हैं?"`). Never stop a clip early just to get a longer quote: end it where the
  sentence ends, even on a short line.
- Titles, summaries and reasons are in **English**. Candidate titles are in **Roman Hinglish** for a
  Hindi/Hinglish video (like clip titles: "Pakistan Ka PM Banoge?"), else in the video's language.

## 1. Topics
A topic is one stretch about one thing, usually **1-5 minutes** (at least 30 s, at most 8 minutes;
about 4-10 per part). List every topic that **starts inside your stretch**, in time order, and only
those. Topics follow each other with no gaps: a topic ends where the next one starts.

- `start`: the start time of the topic's **opening line** (copied). Usually the host's question or
  a clear cue ("अब बात करते हैं...", "let's talk about...").
- `cue`: the first words of that opening line, exactly (5-12 words, or the whole line if it's
  shorter); `null` if the topic starts without a clear cue (then the start stays exactly on the
  line you named, so name the right one). With a cue, code finds it and moves the start onto the
  cue's line if you named the line just before or after.
- `title`: specific, English, at most 8 words, without giving away the punchline
  ("Why China outgrew India", not "Discussion" or "Story 1").
- `summary`: 1-2 plain sentences, at most 40 words. Say **who** claims what ("Khan Sir argues...").
- `role` (one): `story`, `explanation`, `argument`, `advice`, `debate`, `banter`, `reaction`,
  `digression`; structural: `teaser` (a cold open of lines from later), `sponsor`, `intro`, `outro`,
  `housekeeping`; or `other`.
- `key_lines` (1-4): the lines that carry the topic, each `{"words": exact quote of 4-20 words,
  "line": start time of the line it is in, "role": ..., "voice": ..., "softened_by": null or exact
  quote}`.
  - `role`: `hook`, `question`, `claim`, `example`, `setup`, `turn`, `punchline`, `conclusion`,
    `callback`, `reaction`.
  - `voice`: `own` (the speaker's own view), `quoting` (someone else's words), `hypothetical`,
    `sarcasm`, `impression` (mimicking someone), `game` (a game character).
  - `softened_by`: a nearby line that softens, takes back or jokes away this line ("मज़ाक था",
    "just kidding", a correction), quoted exactly; else `null`.
- `terms` (up to 8): names and key words in **both** forms: the transcript's own spelling and the
  English or correct form, e.g. `["कफ्तान", "captain", "पाकिस्तान", "Pakistan"]`.
- `energy`: `low`, `medium` or `high`, judged from the words; `energy_tags` (any of `humour`,
  `conflict`, `strong-claim`, `surprise`, `emotion`, `story-peak`).
- `sensitive` (any of `politics`, `religion`, `caste-communal`, `accusation`, `crime`, `health`,
  `money`, `legal`), else `[]`.
- `self_contained`: `true` if a stranger understands it alone; else `false` and `needs`: in words,
  what a viewer must know first.
- `refers_back`: exact quotes of back-references ("जैसा मैंने बताया", "as I said earlier"), else `[]`.
- `open`: things started here but not finished in your stretch: `{"kind": "setup" | "question" |
  "story", "words": exact quote, "line": start time}` (a question answered later, a joke set up
  but not paid off, "I'll tell you later"). These become threads across the video.

`lead_in`: if your stretch does **not** start with a new topic, describe how the topic from before
continues: `{"summary": "...", "key_lines": [...]}`; else `{"summary": null, "key_lines": []}`.

## 2. The best moment in every 5-minute block
The header lists your blocks (`# 5-MINUTE BLOCKS (start seconds): ...`). For **each** block give
one entry: `{"from": the block's start number as printed, "best": {"line": start time, "words":
exact quote, "why": one line} }`, or `"best": null` with `"why"` saying why nothing there works
(sponsor read, slow logistics...). This makes sure no part of the video is skimmed.

## 3. Clip candidates (up to 5, or none)
Read `references/picking-moments.md` once for what makes a good short. A candidate is a
self-contained moment of 15-90 s (25-60 s ideal): hook first, payoff last.

- Its **middle must lie inside your stretch** (it may run into the context lines).
- One continuous range by default. A splice (2-3 pieces) only when it clearly wins, all pieces from
  this part, in the order they were said, except one cold-open line of at most ~5 s that raises a
  question and means the same when heard first.
- Never from a structural topic (teaser, sponsor, intro, outro, housekeeping).
- Each piece: `{"first": the first 5+ words exactly, "first_line": start time of the line they're
  in, "last": the last 5+ words exactly, "last_line": start time of the line they're in}`. Start on
  the hook's first word and end on the payoff's last word, at sentence ends.
- `title` (Roman Hinglish or the video's language), `hook_type` (`contrarian`, `question`, `fact`,
  `story`, `desire`, `reframe`), `score` 1-10, `why` (one line, quoting what makes it work),
  `needs_context`: `null`, or what a viewer would miss.
- **Score** on one shared scale, the same for every reader:
  - **9-10**: a hook that stops the scroll in 2 seconds, a clear payoff, strong energy, quotable.
    *Example (made up): "Most people save money and still stay poor. Here's the one thing they
    skip..." then a concrete method and a punchy last line.*
  - **7-8**: a good hook and payoff, but slower, or it needs a few seconds of setup.
    *Example: "When I started my first shop, nobody came for three months..." a real story with a
    lesson, but the lesson arrives late.*
  - **5-6**: interesting but flat, or the payoff is weak. **1-4**: needs outside context, no payoff,
    or a list of facts without a story.
  - Score the moment, not the topic: a great topic with a weak start scores low.

## Safety: never change what someone meant
- Keep each person's words with their own meaning: say in `voice` when a line is a quote, a
  hypothetical, sarcasm or an impression; note softeners in `softened_by`.
- A candidate must not make someone seem to say something they didn't: no answer after a
  different question, no reaction after a different line, nothing that points at cut-out words
  ("he", "that", "wo", "isliye") unless its setup is in the clip.

## The file to write
UTF-8 JSON, no comments, exactly these keys:
```json
{"part": 3,
 "lead_in": {"summary": null, "key_lines": []},
 "topics": [{"start": 2412.36, "cue": "<exact first words of that line>", "title": "<English title>",
   "summary": "<1-2 sentences>", "role": "argument",
   "key_lines": [{"words": "<exact words>", "line": 2420.10, "role": "claim", "voice": "own", "softened_by": null}],
   "terms": ["पाकिस्तान", "Pakistan"], "energy": "high", "energy_tags": ["humour"], "sensitive": ["politics"],
   "self_contained": true, "needs": null, "refers_back": [], "open": []}],
 "blocks": [{"from": 2341.86, "best": {"line": 2501.20, "words": "<exact>", "why": "<reason>"}},
            {"from": 2641.86, "best": null, "why": "<why none>"}],
 "candidates": [{"id": "c1", "pieces": [{"first": "<5+ exact words>", "first_line": 2501.20,
     "last": "<5+ exact words>", "last_line": 2541.60}], "title": "<title>",
   "hook_type": "question", "score": 8, "why": "<reason>", "needs_context": null}],
 "note": "<3-4 sentences on what this part covers>"}
```
