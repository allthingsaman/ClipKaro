# Deep clips: stories spread across one video

A deep clip joins 2-3 moments that are far apart in one video into one short: a question and the
answer that comes 40 minutes later, a narrator's opening line and the story's payoff. It is made
only when the user asks, after the regular clips, and it must stay true to the full video
(`picking-moments.md`, "Never change what someone meant"). "No deep clip" is a normal answer.

## Thread finder
You read `deep/map.txt`: the video's topic map (topics in time order, their key lines with role
and voice, open questions and setups, back-references) and SEEDS that code found (possible ends of
a thread; they can be wrong). Find up to 8 **threads**: moments far apart (at least a minute, often
much more) that belong to one story a viewer could follow in under 75 seconds.

Patterns, best first:
1. **question -> its own answer** much later ("why did you quit?" ... "so why did I quit? ...").
2. **intro -> payoff**: the narrator's own spoken opening line and the story's payoff (an intro
   that *says* something, not a montage of lines from later in the video).
3. **setup -> story -> punchline**.
4. **claim -> its proof**, or **objection -> its own answer**.
5. **callback**: a later line that calls back to an earlier one, only with that earlier one in the clip.
Never: "he contradicts himself", "answered twice", supercuts of similar lines, or two moments that
only share a word. Different people's words are joined only as question -> answer.

For each thread write the pattern, the topic ids in time order, the **setup** and the **payoff**
(topic id, the exact words from the map, and the line's seconds), why they belong together, and why
one continuous clip can't hold it. Fewer, surer threads beat many.

```json
{"threads": [
  {"id": "T1", "pattern": "question-answer", "topics": ["t003", "t041"],
   "setup": {"topic": "t003", "words": "<exact words from the map>", "line": 163.11},
   "payoff": {"topic": "t041", "words": "<exact words from the map>", "line": 2470.52},
   "why": "<one sentence>", "why_not_continuous": "<one sentence>"}],
 "notes": "<one or two sentences>"}
```
Write `{"threads": [], "notes": "<why none>"}` when there is no real thread.

## Composer
You get `deep/thread-NN.txt`: one thread, with the real transcript around each of its moments
(`<== SETUP`, `<== PAYOFF`). First check the link on the real words: does the payoff really answer
or pay off the setup, said by the right person, meaning the same thing? If not, write no clip.

Then build **up to 2 deep clips** and **the best continuous clip** around the payoff (one piece,
15-75 s; it is the fair comparison: a deep clip is kept only if it scores at least as high).
- **2-3 pieces**, in the order they were said. One exception: a cold-open line of 2-5 s may go
  first if it raises the question (never the answer) and means the same when heard first.
- **Each piece is whole sentences**: body pieces about 6-20 s. Total **30-75 s**.
- **One thread per clip**, the hook or question in the first 3 seconds, the payoff last.
- Every piece makes sense with what came before it in the clip: no "he / वो / that" pointing at
  cut-out words, no "but" without its other half.
- A guest's answer keeps the host's question in the clip.
- Keep the softener: if "just kidding", "not really" or a correction follows a piece, include it
  or don't use that piece.
- Never use ads, sponsor reads, outros or a montage teaser. The narrator's own spoken opening may
  be the first piece.
- Don't reuse the core of a regular clip that is already made (listed in the file).

Each piece is `{"first": the first 5+ words exactly, "first_line": that line's start seconds,
"last": the last 5+ words exactly, "last_line": that line's start seconds}`, copied from the file.

```json
{"thread": "T1",
 "candidates": [{"pieces": [{"first": "...", "first_line": 163.11, "last": "...", "last_line": 170.2},
                            {"first": "...", "first_line": 2470.52, "last": "...", "last_line": 2490.1}],
                 "title": "<3-7 words>", "hook_type": "question", "score": 8,
                 "why": "<one sentence, quoting what works>", "needs_context": null}],
 "continuous": {"pieces": [{"first": "...", "first_line": 2455.0, "last": "...", "last_line": 2490.1}],
                "title": "<3-7 words>", "hook_type": "question", "score": 7, "why": "<one sentence>"},
 "none_because": null}
```
`hook_type` is one of contrarian, question, fact, story, desire, reframe; `score` is 1-10. With no
good deep clip: `"candidates": []` and `"none_because": "<why>"` (still give the continuous clip if
there is a good one).

## Repair round (once, by the AI editor)
When `deep/report.txt` ends with REPAIR ROUND, some deep clips lost only because two or more
honesty judges objected. Read each listed clip's reasons (in the report and in
`deep/honesty/<id>-<role>.json`) and the transcript around its pieces. Repair a clip only when a
few seconds fix what the judges named, and the story still fits in 75 s:
- a softener, correction or "but..." right after a piece: end the piece after it;
- an answer without its question: start with the question it really answered (not a line from
  the intro, which only lists topics);
- a piece opening on "he / वो / that" or "isliye": start it where the thing is named;
- a line that sounds like the speaker's own view but was a quote or impression: keep the words
  that show whose view it is.
Don't repair a clip whose link itself was wrong (two topics joined to make a cause nobody said, a
reordered story): leave it out. Never repair a repair.

`deep/repairs.json` uses the composer's piece format; `from` is the rejected clip's id:
```json
{"repairs": [
  {"from": "d2-c1",
   "pieces": [{"first": "...", "first_line": 6004.74, "last": "...", "last_line": 6010.39},
              {"first": "...", "first_line": 6123.24, "last": "...", "last_line": 6162.44}],
   "title": "<3-7 words>", "hook_type": "desire", "score": 7,
   "why": "<what the judges named and what changed>", "needs_context": null}]}
```
Then `python run.py deep <project>` adds it as `d2-c1r` (same thread, same continuous twin), and
the critic and fresh honesty judges look at it like any other deep clip.
