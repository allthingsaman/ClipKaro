# The simple edit: how it works and how to change it

The edit is deliberately simple: clean zooms, readable captions, and a few quiet sound effects.
No flashy transitions, emojis or motion graphics.

## Where things live
| What | File | Knobs |
|---|---|---|
| Zoom rhythm and levels | `clipper/plan.py` (`WIDE`, `PUNCH`, `DRIFT`, `OPEN_SCALE`, `beat_bounds`) | punch levels, beat length (2.8 s min) |
| Caption grouping | `clipper/plan.py` `caption_groups` | `max_words=3`, `max_chars=16`, `max_dur=1.6` |
| Caption look (python engine) | `clipper/edit.py` `write_ass` | font, outline, pop timing |
| Caption look (remotion engine) | `remotion/src/Clip.tsx` | same, in React |
| Sound effects | `clipper/plan.py` `sfx_cues`, files in `assets/sfx/` | gains in dB, which moments get one |
| Brand colour | `clipper/brand.py` / `brand.json` in the project | `python run.py brand <project> --accent "#hex"` |

## Common requests
- **"Captions higher/lower"**: `--caption-y` (centre line in px out of 1920; 1270 by default,
  about two-thirds down; around 1500 sits lower, around 1100 near mid-chest).
- **"Bigger/smaller captions"**: `--size` (96 by default).
- **"Not all caps"**: `--no-upper`.
- **"Show both of them here" / "show the other person" / "show the whole picture here"**: add
  `"framing": [[a, b, "split" | "left" | "right"]]` or `"show_full": [[a, b]]` to that clip in
  clips.json (source seconds), then `cut --clips N` and `edit --clips N` again. In the split screen
  the captions sit on the seam between the two people and there are no zooms.
- **"No sound effects" / "only one"**: `--sfx none` / `--sfx light`.
- **"Less zooming"**: `--no-zoom` for none, or raise the 2.8 s minimum in `beat_bounds`.
- **"Use my own sounds"**: drop files into `assets/sfx/` with `whoosh`, `hit` or `click`
  in the file name. They're scanned automatically (files that hold several sounds are split at
  the silences).
- **"Different font"**: put the .ttf in `assets/fonts/`, then pass its family name and file name
  through the `opts` in `edit.py` (`font`, `font_file`).

## Captions: every word kept, rude words with stars
Nothing is censored: no word is ever cut, bleeped or muted, and the viewer hears every word. Abusive
and taboo words are only **written** with stars, the first letter kept: "F******", "c******", "चू**"
(the owner's choice, 2026-11-19; the apps read text first).
- Where: the captions on screen, the `.srt`, the hook title (`edit`), and the posting texts
  (`run.py post`). The transcript, `words.json`, the critic and Claude always keep the real word.
- Which words: `clipper/stars.py` knows the common English swear words and Hindi gaali (Roman and
  Devanagari); clips.json `"stars"` adds slurs, sexual words and other spellings for that clip.
- Way back: settings.json `"star_words": false`, or `edit --no-stars` for one run ("no stars"):
  every word in full.
- Roman Hinglish: in `romanize.json`, spell gaali as it was said, like any other word. Never soften
  it: the stars come later, by themselves.
- If the speech-to-text wrote a starred word ("f***"), the caption check treats it like any mishearing
  and fixes it to the word that was said (`fixword --at`); the stars are then added the same way as
  for every other word.
- The posting texts follow `picking-moments.md` (`post`): gaali may go in titles (with stars), slurs
  never.

## Two engines, one plan
`plan.py` computes the camera for every frame, the caption timings and the sound cues.
- `--engine python` (default) draws it with OpenCV + ffmpeg/libass. It needs no extra installs
  and is fastest.
- `--engine remotion` draws the same plan with React/Remotion (`python install.py --remotion`).
  It has slightly smoother text rendering. It's free for individuals and small teams; companies
  should check Remotion's license.

The audio mix is the same in both engines.
