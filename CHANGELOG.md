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
