# What's new

## Not released yet

- **No made-up words in the captions during laughter, noise or loops.** Whisper invents words where
  nobody speaks clearly. Those now get no captions:
  - shaky words during a laugh, and "ha ha" / "हा हा" written out;
  - "झाल", a word Whisper writes for game sounds and music;
  - made-up loops like "कर दो कर दो कर दो";
  - the long tail of a phrase repeated 8 or more times.

  Real repetition ("let's go, let's go, let's go") keeps its captions. English videos are not
  affected; gameplay videos lose captions on about 1% of words, the ones that were wrong.
  `fetch` does it by itself; `run.py tidy <project>` applies it to older videos.
- **Jump cuts.** Pauses of half a second or more inside a clip are shortened to a natural 0.2 s,
  and "um" / "uh" are cut out, so clips feel tight (about 6 % shorter on average, up to 13 seconds in
  a slow interview clip). Laughs are never cut; in gameplay only pauses up to 2 s. Every word stays.
  `"jump_cuts": false` keeps the pauses.
- **A hook title on screen.** Every clip opens with a big 3-6 word title on a box in the video's
  accent colour for the first 2-3 seconds ("PAKISTAN KA PM BANOGE?"), so it stops the scroll with the
  sound off. It goes in the upper part of the picture, never on a face. Claude writes it with the
  posting text; older clips use their title. `"hook_title": false` turns it off.
- **Captions clear of faces and app buttons.** Captions keep out of TikTok's like and share column
  and the apps' top and bottom bars, and move to a free line in a close-up where they would cover a
  chin. `"safe_zones": false` puts them back on one fixed line.
- **No "…" in captions.** Trailing-off marks ("like...", "हाग…") are no longer shown.

## v2.1 (November 2026): just say "clip this"

v2.1 needs fewer words from you and gives more back. Say "clip this video". ClipKaro then works out
the rest by itself: what kind of video it is (a live stream? gameplay?), how many clips to make, and
for long videos whether you want deep clips (it asks you once). If you want to save your Claude
plan, add the word "quick". Clips that weren't cut are kept, so you can ask for more later. Game
voices get the right captions more often.

Every change is checked against v1.1, the first stable version: nothing v1.1 could do was lost, and
each change is listed in [docs/since-v1.1.md](docs/since-v1.1.md). The pieces were tested on the
owner's own videos: two GTA live streams, the Khan Sir podcast, an anime video and the rest of the
test bench. Not measured yet: how much of the Claude plan quick mode really saves (roadmap item 3b).

### Just say "clip this"
- **Three modes: standard, deep and quick.**
  - *Standard* is the default.
  - *Deep* adds deep clips: ask for them, or say yes to the one question for long videos.
  - *Quick* runs only when you ask ("quick clip this", "use fewer tokens"). Claude then picks the
    clips alone, like v1.1, and uses much less of your Claude plan.
  - Every other upgrade works in all three modes.
- **One question for long videos.** For a video longer than 21 minutes, Claude asks once at the start
  whether you want deep clips too, while the video downloads. `"deep_clips": "always"` or `"never"`
  in settings.json stops the question.
- **The number of clips follows the video's length.**
  - Every good moment becomes a clip: 3 to 8, as before.
  - Long videos get more: up to about one per 7 minutes of real video, at most 20 (`max_clips`).
    A 2-hour stream no longer stops at 8.
  - "At least 10", "at most 5" or "give me 8" in your message always wins.
- **Live streams and gameplay are recognised by themselves.**
  - It knows a live stream when YouTube says so, or when a "Be right back" screen sits in the
    middle. It knows gameplay from the Gaming category, or a webcam in a corner.
  - "Starting soon", "Be right back" and stream-ending screens are left out: a still picture for 30
    seconds or more with nobody on the webcam. Pause menus where you talk on cam stay in.
  - Streams get their own rules: clips are built around what you say, quiet stretches are normal,
    and "hello chat" or "is the audio OK" stay out of clips.
  - On a 1:40 GTA stream it found all three break screens in 28 seconds.
- **The video downloads while the audio is transcribed**, so cutting starts right away. `fetch
  --no-video` keeps the old way.
- New commands: `run.py info` (a quick look before downloading) and `run.py kind` (live stream?
  gameplay? break screens?).

### More clips, ranked fairly
- **More clips later.** The critic scores every clip idea in a video (often 15 to 30), and only the
  best are made. The rest are now kept. Days later, say "3 more clips from the Khan Sir video" (or
  "clips 9-12 too"), and the next ones become clips in a few minutes, without reading the video
  again. The Khan Sir podcast had 18 such ideas, the best scoring 7.1/10. `run.py more`; `post`
  tells you how many are waiting.
- **The critic judges craft, never the topic.** It looks at how a clip starts, whether it makes sense
  alone, how it ends and what could be cut. A clip about politics, religion or anything controversial
  gets the same scores as any other. What to post is always your choice.
- **Repaired clips keep their place.** The repair round's second look can no longer push a trimmed
  clip below its own original (scores wander between runs). `cut --check` no longer warns about
  those repairs.

### Captions
- **Game characters' English is caught more often.**
  - The old check missed a whole English game line, written as Hindi-letter nonsense, when your own
    clear words came right after it. It now finds the unclear core first, and it still catches
    everything the old check caught.
  - Before turning a line into English, ClipKaro makes sure it isn't your Hinglish being
    *translated* ("usko ghar jaana hai" must not become "I have to go to his house").
  - A line that can't be heard well in either language gets no captions.
  - Listening again is faster: Whisper gets only those few seconds, not the whole video each time.
- **Fix a caption word everywhere**: `run.py fixword <project> "bow" "boat"`, or just tell Claude.
  It changes the word wherever it was heard, keeps the timing, and names the clips to make again.

### Editing
- **Fewer zooms when the camera cuts fast.** A camera cut that comes soon after the last zoom change
  now only follows the new face. One anime clip went from 48 zoom changes in 68 seconds to 28.
- **Editing again works without the original video** once the caption colours are saved, so clips
  of videos whose source was deleted can still be edited.

### Posting
- **Fuller YouTube titles.** Each one uses up to 100 characters: the hook, then the game, show or
  person it's about, then 2-3 matching hashtags ending in #Shorts. For example: "Final Boss Yahin La
  Diya, Mar Gaya | Black Myth Wukong Hindi Gameplay #BlackMythWukong #Shorts". Instagram and Facebook
  texts stay as they were.
- **Deep clips' YouTube titles** end with "(2 moments joined)". The description and the captions
  still start with "From 2 moments of the full video: ...".
- **PostKaro gets the honesty note.** When one of the three honesty judges objected to a deep clip,
  post.json passes that judge's reason on to PostKaro.

### v1.1 stays the baseline
- [docs/since-v1.1.md](docs/since-v1.1.md) lists every change since v1.1 as an upgrade, as different
  on purpose (with the way back), or as costing more. From now on every change must be an upgrade to
  v1.1.
- The Opus Clip comparison is updated for v2.1: [docs/roadmap-v2.md](docs/roadmap-v2.md). What's
  next, in order: [docs/roadmap-v3.md](docs/roadmap-v3.md).

## v2.0 (November 2026): deep clips, a second opinion, tighter cuts

The biggest update so far. In the owner's blind comparison with v1.1 on five fresh videos (21 pairs),
v2 found more postable moments (v2 3, v1.1 1, "post both" 6), every deep clip was postable and none was
misleading, and after the tight-cut fix the two cut the same moments equally well (1-1, 6 ties).
Transcribing takes the same time and GPU; choosing clips takes a few minutes longer and uses more Claude
(a long podcast with deep clips: about 30 minutes of picking and roughly 10x v1.1's Claude usage).
Deep clips are only made when you ask for them.

### Long videos are read in parts (deep clips, phase 1)

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

### Tighter cuts, and game voices captioned right
- **Tighter cuts.** In the owner's blind comparison, where both versions cut the same moment, the
  tighter cut won 8 of 8: the new version had made 7 of them longer. Now the second-opinion critic
  also marks dead weight (a slow lead-in, after-thoughts at the end, a detour inside a long answer),
  and the repair round starts on the hook, ends on the payoff and cuts detours out. Every second kept
  must carry something.
- **Game voices.** In a gameplay video transcribed as Hindi, a game character speaking English came out
  as Hindi-letter nonsense in the captions. Unclear stretches are now heard again: clear English
  replaces the nonsense ("…he may yet rise again"), and anything still unclear gets no captions
  instead of wrong ones. `run.py relisten <project>` fixes videos transcribed before.
- Fixed: caption fixes made before the deep pass broke its quotes; the deep pass offered a repair for a
  story that already had a kept clip.

### A [noun] for "this movie"
- When a clip says "इस movie" or "he" and never names it, Claude adds the noun in brackets to the captions
  right after the first mention: IS MOVIE [RAMAYANA] KA (clips.json `clarify`; brackets mark an editor's
  addition). It can be added after cutting: edit the clip again.

### Captions always fit the frame
- **No more captions cut off at the sides.** Some captions ran out of the frame: a whole line stuck in
  one caption (a misheard phrase fixed as one entry, or a Hindi word whose Roman spelling is several
  words), or a group of long words. Caption lines are now measured with the real font and kept at
  most 940 px wide; one very long word (like MISUNDERSTANDING) is shrunk just enough to fit. Out of
  6,698 captions in 30 test videos, none is wider than the frame any more.

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
