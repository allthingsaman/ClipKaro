---
name: clip-video
description: Turn any long video (YouTube link or local file) into ready-to-post vertical short-form clips for YouTube Shorts, Instagram Reels and TikTok. It downloads and transcribes the video, picks the best self-contained moments, cuts and face-reframes them to 9:16, and optionally adds a simple clean edit (smooth zooms, word-by-word captions in the creator's brand colours, 1-2 subtle whooshes). Use whenever the user pastes a YouTube/video link or video file and wants clips, shorts, reels, TikToks, highlights or "the best moments", even if they only say "clip this", "cut this up" or "make shorts from this".
---

# Clip Video

Turns one long video into several vertical shorts. **You (Claude) are the editor who picks the
moments**; the scripts in this repo do the download, transcription, cutting and rendering.
Everything runs locally and free: no API keys and no uploads.

All commands run from the repo root with `python run.py ...` (it uses the repo's own `.venv`).
On Windows use `python`; on macOS/Linux use `python3` if `python` isn't found.

## 0. Setup (first time only)
If `.venv/` doesn't exist, run `python install.py` (it finds an NVIDIA graphics
card by itself and sets it up). If it reports a missing ffmpeg/Node, show the user the exact install command it printed,
and ask them to run it and restart the terminal.
Install Remotion (`python install.py --remotion`) only if the user asks for the Remotion engine.
`settings.json` holds the user's defaults (language, model, device, Hinglish caption script).

## 1. Get the transcript
```
python run.py fetch "<youtube url or path to a video file>"
```
- A **local file** works the same as a link: pass its full path in quotes, e.g.
  `python run.py fetch "C:\Users\me\Videos\my talk.mp4"`. Nothing is uploaded or copied; `cut`
  reads the file in place, so it must stay where it is until the clips are done.
- This downloads the **audio only** (fast) and transcribes it with word timestamps (Whisper). On an
  NVIDIA GPU it takes a few minutes even for a long video; on the CPU, roughly 1/4 to 1/2 of the
  video's length for English and 1-4x the video's length for Hindi/Hinglish (bigger
  model). Run it in the background for long videos and tell the user roughly how long it will take.
- It prints the project name, the detected language and the transcript path:
  `output/<project>/transcript/transcript.txt`.
- If YouTube blocks the download ("confirm you're not a bot"), retry with
  `--cookies-from-browser chrome` (or firefox / edge). Ask the user which browser they use.
- The language is detected automatically. **Hindi/Hinglish** gets `language: hinglish`: Hindi in
  Devanagari, English words in Roman. Read `docs/hinglish.md` for those videos. If the user
  says what language the video is in, pass it: `--lang hinglish` or `--lang en`.

## 2. Pick the moments (your job)
Read `references/picking-moments.md` first (plus `docs/hinglish.md` for a Hindi/Hinglish
video). Then plan how to read the transcript:
```
python run.py parts <project>
```
**One part** (up to about 28 minutes of Hinglish, longer for English): read `transcript.txt` in
full. Look at the words around the **lively spots** `parts` printed (laughs, both talking at once;
the detector can be wrong, so judge them only by the words). Write a **shortlist of about twice
the clips wanted** (for 4 clips, 8 ideas; at most 16) to clips.json, in the normal format, then
let the critic judge them (section 2a).

**Several parts** (long videos): don't read the whole transcript at once. The file reader stops at
256 KB, and long reads get skimmed; never use `allow_large` for it. Instead:
1. Tell the user, e.g. "Reading the video in 6 parts at once; this takes a few minutes."
2. Start one **`clipkaro-part-reader`** helper per part, **all in one message** (Agent tool,
   subagent type `clipkaro-part-reader`, prompt e.g. "Part 3 of 6:
   output/<project>/parts/part-03.txt"). Don't run them while `fetch`, `cut` or `edit` is running
   (memory). Without helpers, read the parts one at a time as `references/reading-parts.md` says,
   writing each `part-NN.json` before reading the next.
3. `python run.py topics <project>` joins the answers and checks every quote. If it names a part
   to redo, run only that part's helper again and pass it the problem lines. If it lists **focus
   files** (a line from the creator's teaser, or a "most replayed" peak, that no candidate covers),
   start one `clipkaro-part-reader` per focus file, all at once, then run `topics` again. Videos
   without a teaser or a replay curve simply have none.
4. Read `topics.txt` (the topic map; look at its CHECK FIRST list). Then let the critic judge
   **all** candidates (section 2a) and pick from its list.

Good clip ideas are self-contained (hook → story → payoff, 25–60 s ideal), in the clips.json
format of `references/picking-moments.md`. Prefer continuous ranges; splice only when it clearly
makes a better short.

## 2a. The critic: a blind second opinion (every video)
```
python run.py critic <project>
```
It writes 3 packets in `output/<project>/critic/`: every clip idea (all candidates of a long
video, or the shortlist in clips.json) in a different random order each time, with neutral
labels, sound markers like `[laughter ~2 s]` and the words right after each clip. The critic never
sees your scores, titles, the replay curve or anything about the channel.
1. Tell the user, e.g. "A second editor is checking all 20 ideas, three times; a few minutes."
2. Start **3 `clipkaro-critic` helpers at once, in one message** (Agent tool; prompt e.g.
   "Run 2 of 3: output/<project>/critic/run-2.txt"). If that helper type isn't available, start
   general helpers with: "You are the ClipKaro critic. Read .claude/agents/clipkaro-critic.md;
   everything after its front matter is your instructions. Run 2 of 3: <file>". Don't run them
   while `fetch`, `cut` or `edit` is running (memory). Without helpers, judge the runs yourself
   one at a time, writing each `run-N.json` before reading the next packet.
3. Run `python run.py critic <project>` again. If it names a run with problems, run only that
   helper again and pass it the problem lines. It writes `critic.txt`: every idea **ranked by clip
   score, best first**, with the critic's reasons, and notes: `fix?` (needs earlier context, or the
   payoff comes after the cut) and `check` (the runs disagreed). Notes are for the repair round;
   the critic never throws a clip away (in the user's blind check, clips it would have dropped were
   ones they'd post). The score ranks clips **within this video**; calm, informative clips are fine.
4. Pick the final 3–8 clips from the top. Of clips that overlap at all, keep the better one; at
   most one per topic unless the ideas clearly differ; if a third of a long video has no pick but
   holds one ranked in the top quarter, swap it in for the weakest pick. A confident voice is not
   content: read close calls yourself.
5. **Repair round (once, when it helps).** Like an editor after notes, fix the clips you'd pick (or
   good ones just below) that have a `fix?` or `trim?` note, a false start, or a weak hook:
   - "never says who / what" or a teaser with no answer: add the short line that names it or
     gives the answer, as a second piece in the order it was said (or a ~5 s cold open); when that
     line is far away, add a `clarify` note instead ("इस movie" -> [Ramayana] in the captions);
   - opens on "जो / वो / so my point was", a false start or a slow line: start where the subject
     is named, at the second take, or at the suggested stronger start;
   - the payoff comes after the cut, or the sentence goes on: end at the end of **that** thought,
     its last sentence, not later; if that is more than ~10 s away, end the first piece earlier and
     add only the payoff line as a second piece;
   - two halves of one story: join them (2–3 pieces, in the order said);
   - **tighten** (`trim?` notes, and your own read of every clip you pick): start on the hook (cut a
     warm-up lead-in), end on the payoff (cut after-thoughts and restating), and cut detours out of
     a long answer as pieces in the order said, so it still plays like one take. Never cut the hook
     line, a line the payoff needs, a funny line or a reaction; never end before the speaker
     finishes the point.

   **Every second you keep or add must carry something.** Of two cuts that say the same thing, keep
   the shorter. (The owner's blind test, Nov 2026: where both versions cut the same moment, the
   tighter cut won 8 of 8; the longer one only wins when its extra seconds are funny or needed.)
   Follow "Never change what someone meant" in `references/picking-moments.md`. When you changed
   any clip, write a shortlist to clips.json (your picks, with the repaired versions; at most 16),
   run `python run.py critic <project> --fresh --from clips`, start the 3 helpers again and pick
   from the new `critic.txt`. Skip the round when the top clips have no notes.
6. Write the final clips.json: each clip with `"from": "<id>"` (e.g. `"p3-c1"`, or `"s3"` for the
   third clip of a shortlist), its `ranges` exactly as listed, `"clip_score"`, and its posting text:
   `"caption"` and `"post"` (YouTube title + description, Instagram caption, Facebook caption;
   `references/picking-moments.md`). Every clip needs them, long videos included: the part
   readers' candidates have none, so write them here. A clip that says "इस movie" / "he" / "वो" and
   never names it gets a `clarify` note (`references/picking-moments.md`). The critic's caption fixes
   come last (2e).

## 2d. Deep clips (only when asked)
"deep clip this: <link>", "clip this, then go deeper", "do a deep pass on <video>": first make the
regular clips as usual, then join moments that are far apart into one story (a question and its
own answer 40 minutes later, a narrator's opening line and the story's payoff). Rules and formats:
`references/deep-clips.md`. A short video needs a topic map first: start one `clipkaro-part-reader`
for `parts/part-01.txt`, then `python run.py topics <project>`.
1. `python run.py deep <project>` writes `deep/map.txt`. Start one **`clipkaro-thread-finder`**
   helper on it (prompt: the map's path). It writes `deep/threads.json`.
2. `python run.py deep <project>` again: it checks the threads and writes one `deep/thread-NN.txt`
   per thread. Start one **`clipkaro-composer`** per thread file, all at once.
3. `python run.py deep <project>` again: it checks the joined clips (quotes, order, no ads or
   montage teasers, not a regular clip's core) and writes `deep/candidates.json`, each deep clip
   with its own best continuous version ("twin").
4. `python run.py critic <project> --from deep` and 3 `clipkaro-critic` helpers, as in 2a. A deep
   clip goes on only if it scores at least as high as its twin.
5. `python run.py honesty <project>`: for each packet, start 3 **`clipkaro-honesty`** helpers at
   once, one per role (prompt e.g. "Role: viewer. Packet: output/<project>/deep/honesty/d1-c1.txt").
   Run it again to merge: two or more fail / unsure reject the clip (never override that); one
   keeps it with a `check` note quoting that judge.
6. `python run.py deep <project>` again: `deep/report.txt` lists the kept deep clips. If it
   ends with **REPAIR ROUND**, do it once: for each listed clip whose judges name something a few
   seconds fix (a cut "but..." or "just kidding", the question it answers, a piece starting on
   "he / वो"), write `deep/repairs.json` (`references/deep-clips.md`, "Repair round"), run `deep`
   again, then `critic --from deep --fresh` with 3 critics, `honesty` (judges for the new packets
   only) and `deep` once more. Never repair a repair; skip clips the judges call twisted at heart.
7. Add the kept deep clips to
   clips.json as extra clips, each with `"deep": {"moments": [...]}`, a real `caption` that starts
   with its `source_line` ("From 2 moments of the full video: 0:08 · 22:53") and ends with "Full
   video: <link>", and a `post` block whose texts also start with the source line. `cut` shows each jump across time with a short flash. When a kept clip has an
   `honesty_note` (one judge objected), tell the user that judge's reason in your final message.
New helper types appear after Claude Code restarts; until then start general helpers and tell
them to read `.claude/agents/<name>.md` (everything after its front matter is their instructions).
"No deep clip" is a normal, honest answer: say so plainly.

**Get exact times.** A transcript line can hold several sentences. When your hook or payoff
starts or ends **inside** a line, look up the exact word time instead of using the line's time:
```
python run.py find <project> "the thing that separates"     -> start 457.35 ...
python run.py find <project> "never give it to you"         -> ... end 474.95
```
Use the `start` of the hook's first words and the `end` of the payoff's last words. Otherwise a
clip can open with leftover words from the previous sentence.

Before moving on, show the user a short table: #, title, length, hook line, clip score (e.g.
"8/10 Strong"). Below it, one line on what the repair round fixed (e.g. "2 clips repaired: one
now names who he is, one ends on the answer"), and this line: "Clip scores judge how well-made
each clip looks from its words and sound; they are not a prediction of views."
List clips the critic tagged `check-facts` with the claim to check (the user decides before
posting). Don't wait for approval unless they asked to review picks first. Keep going.

## 2e. Caption fixes (last, after the deep pass if there is one)
Copy `transcript/words.json` to `transcript/words-before-fixes.json` once, then apply the critic's
**caption fixes** (misheard words, e.g. "farts" -> "fads") for the picked clips in `words.json`, one
word entry at a time, keeping the times. The deep pass and the topic map match quotes against the
words as first heard (`words-before-fixes.json`), so fixes never break them.

## 2b. Roman Hinglish captions (Hindi/Hinglish projects only)
Skip this for other languages, or if settings.json has `"hinglish_captions": "devanagari"`.
```
python run.py romanize <project>
```
It adds every Hindi word of the picked clips to `output/<project>/romanize.json` with an empty
value and prints the clips' text. Fill in every value following the spelling style in
`docs/hinglish.md` (write the whole file back, keys unchanged), then run it again until it
prints the finished Roman caption text. If you change clips.json later, run it again.

## 3. Cut to vertical
First check the boundaries (it takes a second and cuts nothing):
```
python run.py cut <project> --check
```
It warns when a clip starts or ends mid-sentence, falls outside 15–90 s, or (for a clip joined
from pieces) a later piece opens on "he / वो / that" or "haan / exactly", which may point at or
answer words that were cut. For every warning, look at the quoted words. Fix the range with `run.py find` unless the cut is clearly intentional
(e.g. a splice point, or a start right after "but"). Then cut:
```
python run.py cut <project>
```
This downloads the video (max 1080p) the first time, snaps every range to whole words, reframes
each camera shot around the speaker's face (9:16, 1080x1920), and writes `clips/NN-title.mp4`.
Shots with no detectable face (slides, b-roll) get a blurred-background "fit" layout.
**Gameplay with a webcam overlay** is detected automatically and stacked instead: gameplay on top,
the cam enlarged below, captions on the seam (`-> layout: facecam` in the output). `--layout crop`
turns it off; a wrong cam position is fixed with `"facecam"` in settings.json (see README). In gameplay
videos, pick moments from the creator's commentary and reactions, not the game characters' dialogue.
Use `--horizontal` to keep 16:9, and `--clips 2,4` to redo only some.

**Two people on screen (podcasts, interviews)** are framed automatically when they sit too far
apart for one 9:16 crop (a side-by-side picture or a wide shot of the room). `cut` listens to who
is talking and frames each moment like an editor:
- one person talks, the other listens: a crop on the speaker;
- around a laugh (from 2 s before it, when the punchline lands, to 2 s after), both laughing,
  talking over each other, a quick back-and-forth, or when it can't tell who is talking: both
  people stacked in a split screen, the one who talks most on top, the captions on the seam;
- a wide shot of the room: split screen, unless one person talks alone for 6 s or more.
It never guesses a face. `cut` prints one line per clip (`clip 4: right 31s`, `clip 1: split 26s`).
The first time it downloads small voice and laughter models (~50 MB).

**Check what the crop keeps** (for podcasts, product videos, anything where something is shown):
```
python run.py frames <project> --clips 1,3
```
It writes `output/<project>/frames/NN-title.jpg`: frames with the crop box, SPEAKER / BOTH (split)
labels, a FULL border for whole-frame stretches, red borders where something moves outside the
crop, and orange dots where words point at something ("ye dekho", "look at this"). Look at the
sheets of every clip with a two-person shot or a red border. Fix only what is wrong, in clips.json
(source seconds, at word gaps), then `cut --clips N` again:
- `"framing": [[a, b, "split"]]`: show both people, e.g. the listener visibly laughs or reacts
  while the other talks (a silent laugh, an "impressed" face). Sound can't catch these; you can.
- `"framing": [[a, b, "left" | "right" | "center" | 0-1]]`: show that person (or point); e.g. a big
  reaction shot of the one laughing while the speaker pauses, or the wrong face in any crop.
- `"show_full": [[a, b]]` (or `"framing": [[a, b, "full"]]`): the whole landscape frame over a
  blurred background, when what is shown or talked about lies outside the crop (a product held up,
  a screen, a gesture across the room).
Hand-picked framing always wins over the automatic choice.

**These raw cuts are already postable.** If the user only wanted clips, stop here and report.

## 4. Brand colours for captions (quick, don't overthink)
The captions use white text, a black outline, and **one accent colour** for the spoken word and
the emphasis words. Choose the accent like this:
1. **If you know the creator's signature caption or brand colour** (from your knowledge, or a
   quick web search if you have that tool), set it:
   `python run.py brand <project> --accent "#RRGGBB" --note "creator brand colour"`.
   Only do this when you're confident; don't guess.
2. Otherwise do nothing: the edit step picks the strongest non-skin colour from the video itself
   (graphics, set lighting, clothing) and brightens it for readability, or falls back to a
   classic short-form yellow.
3. Sanity-check the printed colour. It must read clearly over the footage and not clash. If it
   looks off (e.g. muddy brown or near-grey), override it with a clean colour from the printed
   palette or with `#FFD60A`.

## 5. Simple edit (optional, recommended)
```
python run.py edit <project>
```
For each clip this adds:
- **Zooms**: it opens on a quick zoom-out, then alternates wide and punched-in framing about
  every 3–5 s on sentence ends, with one or two smooth emphasis zooms and a slow push in between.
  It always scales around the face. Camera cuts and splices get a framing change, which hides
  the jump.
- **Captions**: 1–3 words at a time, bold, popping in word by word. The spoken word lights up in
  the accent colour, and the `emphasis` words from clips.json stay highlighted. An `.srt` is also
  written. Hinglish projects use the Roman spellings from romanize.json; any word still in
  Devanagari switches that clip to the Poppins font (it has Hindi letters) in normal case.
- **Sound**: at most 2 subtle whooshes: one on the opening zoom and one on an emphasis zoom (in a
  joined clip that jumps in time, a softer one on the jump instead, with the flash). The voice is lightly compressed, and the
  whole mix is normalised to -14 LUFS.

Options: `--sfx light|none`, `--no-zoom`, `--no-captions`, `--no-upper` (sentence case),
`--caption-y 1270` (higher number = lower on screen), `--size 96`, `--engine remotion`,
`--jump-label` (a small "27 MIN LATER" where a joined clip jumps in time; only if the user asks,
or `"jump_label": true` in settings.json).
Read `references/editing.md` if the user wants a different look.

## 6. Deliver
Run `python run.py post <project>`. It writes `post.json` (the clips with each platform's text)
and, when PostKaro (the posting app) is installed, prints **`Post them: <link>`**. Lines starting
with `?` name clips without posting text: add their `caption` / `post` in clips.json and run it
again.

Report the results as a short table: clip, length, clip score, file path. Under each clip, give
two or three of the critic's reasons that quote the clip (from `critic.txt`). Point to
`output/<project>/edited/` (or `clips/` if not edited) and include each clip's posting caption
from clips.json. Repeat the line that clip scores are not a prediction of views. If `post` printed
a link, end with it: "Post them: <link>" (it opens PostKaro with every clip filled in; it only works
on this computer). Otherwise mention that the files are ready to upload to Shorts, Reels and TikTok.

## Rules
- Never invent words. Clips only contain what the speaker actually said.
- Never commit anything in `output/` (it's gitignored). Don't upload anything anywhere yourself:
  posting only happens in PostKaro, when the user presses Schedule there.
- Remind users to clip only videos they own or have permission to use.
- If a step fails, read the error. The scripts print the fix (missing tool, cookies, etc.).
