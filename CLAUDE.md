# ClipKaro

This repo turns long videos into vertical short-form clips. When the user pastes a video link or
file, or asks for clips, shorts, reels or TikToks, **use the `clip-video` skill**
(`.claude/skills/clip-video/SKILL.md`) and follow it end to end without stopping for confirmation.
The mode is **standard** unless the user asks otherwise: **quick** only when they ask for it ("quick",
"basic mode", "use fewer tokens"), **deep** when they ask for deep clips ("deep clip", "advanced mode")
or say yes to the one question the skill
may ask: for a video longer than 21 minutes, whether they want deep clips too (only when settings.json
`"deep_clips"` is `"ask"`, they didn't ask for quick, and their message didn't already say). Ask it
right at the start, while `fetch` runs. A number of clips in the message ("at least 10", "at most 5")
goes to `parts`; without one, ClipKaro decides by the video's length.
**Always on, in every mode** (not options to offer): pause cutting, no captions on made-up words,
captions off faces and clear of the apps' buttons, the sound-peak limit, no captions for game
characters in gameplay (the game shows its own); emojis too, unless the user says "no emojis";
the "© Channel" credit on clips from a link ("© twitch.tv/name" for Twitch; `edit --no-credit` for "no credit"), the
user's logo and outro when they are in `brand/` (`--no-logo` / `--no-outro` when asked), and no
censoring: gaali, abuse, slurs, taboo talk (sex, cheating) and A-rated moments stay in the clips, heard
in full, and bold, honest takes count extra (way back: settings.json `"bold_clips": "neutral"`);
abusive and taboo words are written with stars in captions and posting texts, "F******" (way back:
`"star_words": false`, or `edit --no-stars` for "no stars"); racial and caste slurs never in a title.
**Standard and deep only** (quick mode skips it to save usage): the caption check (`run.py captions`,
fix clear mishearings with `fixword --at`; skill step 2c). **Only when the user names it**: "hook title" (write `hook_text` per clip, `edit
--hook-title`) and a caption look ("box captions" ...). Background music is on hold: no `music` mood.

## Rules
- **Asked to install / set up this repo?** Follow "For AI agents installing ClipKaro" in README.md
  (details per system in docs/installation.md). Never run `sudo` yourself: give the user the exact
  commands in one block. Finish by telling the user to start Claude Code inside this folder.
- Setup is `python install.py` (`python3` on macOS/Linux; on a Mac `python3.13 install.py`, because
  Homebrew's default Python 3.15 is too new for the speech engine). It finds an NVIDIA graphics card by
  itself and then sets up GPU transcription too (`--cpu` skips that). Safe to run again.
- **Asked to install PostKaro too** (the posting app)? Step 7 of "For AI agents installing ClipKaro" in
  README.md: clone it next to this folder and run its `install.py` with the same Python.
- Run everything through `python run.py <command>` from the repo root.
- **Asked to update ClipKaro?** `git pull`, then `python install.py`, and report what changed.
- **Live clipping** ("live clip my stream", "start live clipping"): skill section 8 and
  `docs/live-clipping.md` (OBS multistream settings: `docs/streaming-setup.md`): a watcher on OBS's
  10-minute recording pieces, `/loop 10m live clip <name>`, one `clipkaro-live` helper per piece, clips
  auto-posted everywhere through PostKaro (the owner's choice for live streams). settings.json ships
  `"live_folder"` and `"twitch_channel"` as `"<...>"` placeholders: when one is still a placeholder,
  ask the user for it first and write the answer into settings.json yourself.
- Results go to `output/<project>/` (gitignored). Never commit or upload user videos.
- Long steps (transcription, rendering) should run in the background, with a progress update to the user.
- The user's defaults are in `settings.json`.
- **Hindi / Hinglish videos**: read `docs/hinglish.md`. Captions are Roman Hinglish unless
  settings.json says otherwise: after writing clips.json, run `python run.py romanize <project>`,
  fill every empty value in `output/<project>/romanize.json` with the Roman spelling, and run it
  again until it prints the finished caption text. Then cut and edit as usual. (Written down by the
  Hinglish model, the default with an NVIDIA card: it lists English-letter words to check instead;
  add any respellings, then `romanize <project> --checked`.)
- Local video files are passed straight to `fetch` as a quoted path, e.g.
  `python run.py fetch "C:\Users\you\Videos\my video.mp4"` or `python3 run.py fetch "/home/you/Videos/my video.mp4"`.
- Gameplay videos with a webcam overlay get the facecam layout automatically at `cut` (gameplay on
  top, cam below, captions between); `cut` prints it. Use `--layout crop` to turn it off, and set
  `"facecam"` in settings.json if the cam is found in the wrong place. In gameplay videos the
  transcript also holds the game's own dialogue: build clips around the creator's commentary and
  reactions, not the game characters' lines.
- Live streams and gameplay are recognised automatically at the end of `fetch` (`run.py kind`):
  "Starting soon", "Be right back" and stream-ending screens are left out of the transcript, and the
  stream rules apply (quiet stretches are normal, no stream housekeeping in clips). The user never
  has to explain that a video is a stream.
- Podcasts and interviews with two people on screen are framed automatically at `cut` (speaker
  crop, split screen around laughs and cross-talk). After cutting, check those clips with
  `python run.py frames <project> --clips N` and fix only what's wrong with `"framing"` or
  `"show_full"` in clips.json (see the skill). Add `"split"` where the listener visibly laughs or
  reacts while the other talks: the sound alone can't catch a silent reaction.
- **v1.1 is the baseline.** It is the first stable version, and every change after it must be an
  upgrade: nothing v1.1 could do may be lost or made harder. If a change does something differently
  on purpose, give a way back (a setting, a phrase, an option). Record each change in
  `docs/since-v1.1.md` (marked ⬆ upgrade, ↔ different on purpose, or ⚠ costs more) in the same commit.
  After changing the code, run `python run.py test` (fast) and add a test for what you changed.
- User documentation is in `docs/` (start at `docs/README.md`; for people new to all this:
  `docs/user-guide.md`; how the code works: `docs/architecture.md`). Keep it in sync when behaviour
  or options change, and write it in simple, everyday words.
- When the user asks to add something to their preferences, add it as a new line under
  "My preferences" below, in their own words.

## My preferences
The personal wishes of whoever uses this copy of ClipKaro. Follow them every time, unless a
message says otherwise. Change them freely, or ask Claude: "add to my preferences: ...".
Examples of what you can write: "always give me 5 clips", "clips 30-45 seconds long",
"my brand colour is #00E5FF", "no sound effects", "my videos are in English".

- My videos are often in Hinglish (Hindi + English).
