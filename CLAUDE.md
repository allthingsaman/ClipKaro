# ClipKaro

This repo turns long videos into vertical short-form clips. When the user pastes a video link or
file, or asks for clips, shorts, reels or TikToks, **use the `clip-video` skill**
(`.claude/skills/clip-video/SKILL.md`) and follow it end to end without stopping for confirmation.

## Rules
- **Asked to install / set up this repo?** Follow "For AI agents installing ClipKaro" in README.md
  (details per system in docs/installation.md). Never run `sudo` yourself: give the user the exact
  commands in one block. Finish by telling the user to start Claude Code inside this folder.
- Setup is `python install.py` (`python3` on macOS/Linux). It finds an NVIDIA graphics card by itself
  and then sets up GPU transcription too (`--cpu` skips that). Safe to run again.
- Run everything through `python run.py <command>` from the repo root.
- **Asked to update ClipKaro?** `git pull`, then `python install.py`, and report what changed.
- Results go to `output/<project>/` (gitignored). Never commit or upload user videos.
- Long steps (transcription, rendering) should run in the background, with a progress update to the user.
- The user's defaults are in `settings.json`.
- **Hindi / Hinglish videos**: read `docs/hinglish.md`. Captions are Roman Hinglish unless
  settings.json says otherwise: after writing clips.json, run `python run.py romanize <project>`,
  fill every empty value in `output/<project>/romanize.json` with the Roman spelling, and run it
  again until it prints the finished caption text. Then cut and edit as usual.
- Local video files are passed straight to `fetch` as a quoted path, e.g.
  `python run.py fetch "C:\Users\you\Videos\my video.mp4"` or `python3 run.py fetch "/home/you/Videos/my video.mp4"`.
- Gameplay videos with a webcam overlay get the facecam layout automatically at `cut` (gameplay on
  top, cam below, captions between); `cut` prints it. Use `--layout crop` to turn it off, and set
  `"facecam"` in settings.json if the cam is found in the wrong place. In gameplay videos the
  transcript also holds the game's own dialogue: build clips around the creator's commentary and
  reactions, not the game characters' lines.
- Podcasts and interviews with two people on screen are framed automatically at `cut` (speaker
  crop, split screen around laughs and cross-talk). After cutting, check those clips with
  `python run.py frames <project> --clips N` and fix only what's wrong with `"framing"` or
  `"show_full"` in clips.json (see the skill). Add `"split"` where the listener visibly laughs or
  reacts while the other talks: the sound alone can't catch a silent reaction.
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
