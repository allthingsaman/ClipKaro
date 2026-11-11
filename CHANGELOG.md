# What's new

## Unreleased: long videos are read in parts (deep clips, phase 1)

- **Long podcasts get read properly.** A video of more than about half an hour is split into parts
  of about 21 minutes (with 2 minutes of overlap, so no moment falls into a gap), and one AI reader
  per part works at the same time. Before, a 2-hour transcript was too big for the AI's file reader
  in one go, and long reads got skimmed. On the 2-hour Khan Sir podcast the candidates now spread
  evenly over the start, middle and end of the video.
- **A topic map** (`topics.txt`): every topic with its time, what it's about, its key lines and how
  they were said (own view, quote, joke, impression), YouTube's "most replayed" peaks and the lines
  the creator used in the cold open. It's the base for deep clips (stories spread across a video).
- **Exact times, real words.** The readers quote words; code finds them in the transcript and takes
  the exact times from there, so no time is guessed and no word is paraphrased.
- `fetch` keeps the video's description, the creator's chapters and the "most replayed" curve.
- **Very long videos no longer crash the computer.** Transcribing a 3-hour Hindi podcast used about
  7 GB of memory at once, and on a 16 GB laptop the system closed programs to survive. Audio longer
  than 30 minutes is now transcribed in pieces of about 20 minutes, cut in pauses, so memory use
  stays the same for any length. Shorter videos are transcribed exactly as before.
- **Podcasts with faces in the wall art show the right person.** In a podcast with painted faces on
  the wall behind the guest, ClipKaro measured a painted face instead of the guest and showed the
  listening host whenever the guest talked. It now looks only at the biggest face on each side.
  Clips cut before this fix are measured again automatically the next time you run `cut`.
- **Dark studios: camera cuts are found again.** In a podcast filmed against a black background
  (like the Sam Altman interview), the cut detector found no camera changes at all, so the crop
  stayed in one place for a whole clip, sometimes on the empty space between two people. Cuts are
  now found by comparing each frame with the frames around it. Bright videos get the same cuts as
  before.
- New commands: `run.py parts` and `run.py topics`. New rules in the picking guide: "Never change
  what someone meant" for clips joined from several pieces.

### Deep clips, phase 2: a second opinion before cutting
- **The critic.** Before anything is cut, a second AI editor checks every clip idea, three times,
  each time in a different order and without knowing who picked it or what score it got. Two
  checks are pass or fail: would a stranger understand the clip on its own, and does it end with
  its payoff (not just before it)? Then it scores the hook, the payoff, the feeling, how shareable
  it is and whether it has a line worth quoting. All ideas are ranked by their **clip score** out
  of 10, with reasons that quote the clip, and the best ones are used. A failed check becomes a
  note for the repair round, never a reason to throw a clip away: in the blind check, every clip
  the critic would have dropped was one the creator would post. The score compares the moments of
  one video and is not a prediction of views.
- **Short videos too:** Claude now writes a shortlist of about twice the clips you want, and the
  critic picks the best of them.
- **Every video gets sound hints**, not only popular ones: right after transcribing, ClipKaro
  listens for laughs, applause and two people talking at once (about 30 seconds for a 3-hour video).
  The readers get a short list of lively moments to check, and the critic sees marks such as
  "[laughter ~2 s]" in the text, so a joke that's funny because of how it's said isn't missed. A
  calm video loses nothing: the marks only ever help.
- **The creator's teaser and "most replayed":** when the creator's own cold-open teaser, or the
  YouTube "most replayed" graph (only popular videos have one), points at a moment nobody picked,
  that stretch is read again carefully. Those hints never rescue a weak clip; they only decide
  between two clips that are nearly equal.
- **A repair round:** like an editor after notes, Claude fixes the top clips that have a note (a
  teaser without its answer, an unnamed "he", a slow start) and lets the critic judge them once
  more. In testing, two pairs of pieces with such notes became a video's two best clips.
- **False starts:** `cut --check` now also warns when a clip may open with a restarted phrase
  ("1992 se leke, 1992 peak ho gaya"), so it can start at the second take.
- **Things to check before posting:** the critic flags claims that look wrong (`check-facts`) and
  misheard words that would look wrong in the captions ("farts" for "fads"), which Claude fixes
  before cutting. Neither changes a score.
- Every clip idea's scores are saved in `output/clip-log.csv`, so the critic can later be tuned to
  what you keep and post.
- New commands: `run.py sound` and `run.py critic`.

### Deep clips, phase 3: one story from moments far apart
- **Ask for it:** "deep clip this: <link>", "clip this, then go deeper" or "do a deep pass on
  <video>". The regular clips are made first, exactly as before; without these words nothing
  changes.
- **What it makes:** a short that joins 2-3 moments that are far apart but belong to one story: a
  question and its own answer 40 minutes later, the narrator's opening line and the story's
  payoff. The pieces always play in the order they were said.
- **Only when it's better:** every deep clip is scored by the blind critic next to the best
  single stretch around the same payoff. If one stretch tells the story as well, the deep clip is
  dropped. "No deep clip" is a normal answer.
- **Only when it's honest:** three separate AI judges (a rules checker, one who speaks for the
  person in the clip, and a viewer who then watches the full video) read each piece inside its
  original minutes, and everything cut between the pieces. If two or three of them say "fail" or
  "not sure", the clip is dropped, whatever its score. If only one does, the clip is kept and
  Claude shows you that judge's reason, so you can look before posting. Tested on 56 clips the
  judges had never seen, about half of them made to mislead: all 29 misleading clips were caught,
  2 of the 27 honest ones were dropped, and 1 was kept with a note.
- **Joins are visible:** where a clip skips more than 20 seconds, a short white flash shows the
  jump, and the posting caption starts with "From 2 moments of the full video: 35:30 · 1:03:01"
  plus the full video link.
- New commands: `run.py deep` and `run.py honesty`.

### Deep clips, phase 4: smoother joins and a repair round
- **Joins sound smooth.** Where a clip is joined from pieces, the sound now fades out and in only
  in the quiet between words, a little longer where the video jumps in time (the background sound
  changes there), so a join never clicks and never clips a word. Clips of one piece sound exactly
  as before.
- **A jump is heard, too:** a soft whoosh plays with the white flash where a clip skips more than
  20 seconds.
- **Optional time label:** ask for it ("show how much time was skipped") or set
  `"jump_label": true`, and a small "27 MIN LATER" appears for a moment at each jump. Off by
  default.
- **A second chance for deep clips:** when the honesty judges reject a deep clip for something a
  few seconds would fix (a "but..." cut off, an answer without its question), Claude repairs it once
  and it is scored and judged again from scratch. Tested on the Khan Sir podcast: a rejected clip came back, passed, and is now that video's one deep clip (with a note from one judge).
- **One more check for joined clips:** `cut --check` warns when a later piece starts on "he",
  "that", "वो" or "haan", which may point at (or answer) words that were cut out.
- Fixed: the deep pass now prints its warnings (it only counted them).

### Posting: ready for PostKaro
- **Text for each platform.** Every clip now gets its own posting text for YouTube (a title of up to
  100 characters plus a short description), Instagram (a caption with at most 5 hashtags, Instagram's
  limit) and Facebook, instead of one caption for all.
- **Fixed: long videos lost their captions.** On long podcasts most clips had no posting caption
  (for example 1 of 7). Every clip now gets one, deep clips included (they start with their "From 2
  moments of the full video" line).
- **`run.py post <project>`** writes `post.json`: the finished clips with each platform's text. If PostKaro
  (the separate posting app) is installed, it prints a **"Post them"**
  link that opens PostKaro with every clip filled in. Without PostKaro nothing changes.

## v1.1 (November 2026): better framing

### Podcasts with two people on screen
- **The person talking is shown.** When two people sit too far apart for one standing crop (a
  side-by-side picture or a wide shot of the room), ClipKaro now listens to who is talking and
  shows that person. Before, it showed the bigger face, which was often the listener.
- **Laughs show both people.** From about 2 seconds before a laugh (the punchline) to 2 seconds
  after, and when both talk at once or go quickly back and forth, both people are shown one above
  the other (a split screen). The person who talks most sits on top, with the captions in between.
- **Wide shots of the room** show both people, unless one person talks alone for a long time.
- **It never guesses a face.** When it can't tell who is talking, it shows both.
- **The AI editor checks it.** A silent laugh or an "impressed" face can't be heard, so the AI
  editor looks at picture sheets (`run.py frames`) and adds a split screen there.
- Tested on 9 hand-checked podcast clips: the ideal framing 83% of the time, an acceptable one 91%,
  the wrong single face 1%.

### Show what matters
- **`show_full`**: when someone holds up a product or points at a screen outside the crop, that
  stretch shows the whole landscape picture over a blurred background, without zooming in.
- **`framing`**: the AI editor (or you) can choose what any stretch shows: the face on the left or
  right, the centre, both people (`split`) or the whole picture (`full`).
- **`run.py frames`**: picture sheets of what the crop keeps, with hints where something moves
  outside it or the words point at something ("ye dekho").
- **Inserts inside a shot** (a photo or clip the cut detection missed) now get their own framing,
  so their text isn't cut off.

### Smaller fixes
- One person who leans or laughs is no longer mistaken for two people.
- Captions never cover a face when the picture switches to or from the split screen.
- No more one-frame caption blink, no blended double frames at camera cuts, and zoom changes land
  on the exact frame of a cut.
- Subtitle (`.srt`) files no longer start with a broken negative time.

### Setup
- `python install.py` adds `sherpa-onnx` (it hears who is talking). If it can't be installed, all
  else still works and podcasts keep the simpler framing. Three small models (about 50 MB) are
  downloaded the first time a podcast needs them.
- Everything that worked before works the same: shots with one person, slides, gameplay with a
  webcam and the `--horizontal` option are framed as in v1.0 (apart from the inserts above).

## v1.0 (November 2026): first public release
Clips from YouTube links and video files: transcription with word timings (NVIDIA GPU or CPU),
moment picking by the AI editor, Hinglish captions in English letters, face-centred 9:16 cuts,
the gameplay webcam layout, zooms, word-by-word captions and sound effects.
