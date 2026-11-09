<p align="center">
  <img src="https://res.cloudinary.com/amanupadhyay1211/image/upload/f_auto,q_auto,w_600/v1793979523/Cheerful_Bluebird_Filmstrip_Sticker_ugg1n5.png" alt="ClipKaro mascot: a cheerful bluebird in yellow sneakers snipping a film strip with yellow scissors, next to a phone with a play button" width="260">
</p>

# ClipKaro ✂️

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.10-3.14](https://img.shields.io/badge/python-3.10--3.14-blue.svg)](docs/requirements.md)
[![Platforms](https://img.shields.io/badge/platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey.svg)](docs/installation.md)

**Turn a long video into short videos, ready to post.** Give it a YouTube link or a video file.
ClipKaro finds the best moments and makes standing (9:16) videos for **YouTube Shorts, Instagram
Reels and TikTok**, with the speaker's face in the middle, captions that appear word by word, zoom
effects and sound effects. It's free, it runs on your own computer, and it works just as well for
**Hindi and Hinglish** videos as for English ones.

*"Clip karo" is Hinglish for "clip it".*

```
you:  clip this video: https://youtu.be/...
      → listens to the video → picks the 3-8 best moments → cuts them standing (9:16) → edits them
      → output/<video>/edited/01-why-hard-work-isnt-enough.mp4  (+ a caption to post with each one)
```

> **New to all this?** Start with the **[user guide](docs/user-guide.md)**: simple steps, no coding
> needed.

## What it does
- 🧠 **Picks the best moments for you.** It reads everything that is said and chooses parts that
  grab attention in the first seconds and make sense on their own (usually 25-60 seconds each).
- 📱 **Keeps the face in frame.** It turns wide videos into standing ones and keeps the speaker's
  face in the middle. Slides and other shots are shown whole over a blurred background.
- 🎙️ **Podcasts with two people.** It listens to who is talking and shows that person. When
  someone laughs or both talk at once, it shows both of them in a split screen. *(new in v1.1)*
- 🎮 **Gameplay with a webcam?** It notices the webcam by itself: the game on top, your face below,
  the captions in between.
- ✨ **A clean, lively edit.** Zoom-ins on the beat, captions that pop in word by word in a colour
  that fits the video, a couple of soft "whoosh" sounds, and volume set right for phones.
- 🇮🇳 **Hindi + English (Hinglish).** Found automatically. Captions in English letters
  ("aaj hum business ki baat karenge") or in Hindi letters.
- ⚡ **Fast with an NVIDIA graphics card.** A 7-minute Hinglish video is written down in about a
  minute. Without one it still works, but it's slow (not recommended).
- 🔒 **Free and private.** No extra accounts or keys for ClipKaro, no subscriptions, nothing
  uploaded. Works with YouTube links and your own video files.

## How it works
1. **Listen**: it downloads the sound and writes down every word with its exact time.
2. **Pick**: the AI (Claude Code) reads the words and chooses the best moments. A long podcast is
   read in parts of about 20 minutes, all at once, so nothing in the middle gets skimmed.
3. **Captions**: for Hindi/Hinglish, it writes every Hindi word in English letters.
4. **Cut**: each moment is cut to a standing video, framed on the speaker's face.
5. **Edit**: zooms, captions and sound effects are added, and the volume is evened out.

The computer does the mechanical work; the AI only makes the choices an editor would make.
How it works inside: [docs/architecture.md](docs/architecture.md).

## Quick start

### 1. Check your computer
Any 64-bit Windows, Mac or Linux computer with **8 GB of memory (RAM)** can run it. An **NVIDIA
graphics card (4 GB or more)** is **strongly recommended**: with it a video takes minutes, without it
a video can take a couple of hours. Details: [docs/requirements.md](docs/requirements.md).

### 2. Install (once)

**The easy way: let Claude Code install it.** Open [Claude Code](https://claude.com/claude-code) in
the folder where you want ClipKaro (for example your Documents folder) and type:

> **install this repo: https://github.com/allthingsaman/ClipKaro**

Claude downloads ClipKaro, checks your computer, installs what's missing and finds out by itself
whether you have an NVIDIA graphics card (and sets it up if you do). Anything that needs your
computer's password, it gives you to run yourself. When it's done, **open Claude Code inside the
new `ClipKaro` folder** (step 3). Every step explained simply: [docs/user-guide.md](docs/user-guide.md).

**Or install it yourself.** You need: [Claude Code](https://claude.com/claude-code),
**Python 3.10-3.14**, **ffmpeg** and **Node.js** (recommended).

**Windows** (in PowerShell; open a new window after the `winget` lines):
```powershell
winget install -e --id Python.Python.3.12
winget install -e --id Gyan.FFmpeg
winget install -e --id OpenJS.NodeJS.LTS
winget install -e --id Git.Git
git clone https://github.com/allthingsaman/ClipKaro.git
cd ClipKaro
python install.py
```

**Mac** (with [Homebrew](https://brew.sh)):
```bash
brew install python ffmpeg node git
git clone https://github.com/allthingsaman/ClipKaro.git
cd ClipKaro
python3 install.py
```

**Linux** (Ubuntu/Debian shown; Fedora needs the full ffmpeg from RPM Fusion, see the guide):
```bash
sudo apt install python3 python3-venv python3-pip ffmpeg nodejs git
git clone https://github.com/allthingsaman/ClipKaro.git
cd ClipKaro
python3 install.py
```

`install.py` checks your computer, tells you the exact command for anything that's missing, finds an
NVIDIA graphics card by itself and sets it up, and puts everything else in a private `.venv`
folder inside ClipKaro. You can run it again any time. Full guide for every system:
[docs/installation.md](docs/installation.md).

### 3. Make clips
Open Claude Code **inside the ClipKaro folder** (terminal: `cd ClipKaro`, then `claude`; desktop
app or VS Code: open the `ClipKaro` folder). Claude only knows how to make clips when it's started
there. Then type:

> **clip this video: https://youtu.be/...**

or, for a file on your computer (put the path in quotes):

> **clip this video: "C:\Users\you\Videos\my podcast.mp4"**

Claude does the rest by itself and shows you a table of finished clips, each with a caption you can
copy when you post.

Using a different AI helper (Codex, Cursor, Copilot, Gemini CLI, ...)? See [AGENTS.md](AGENTS.md).

### For AI agents installing ClipKaro
If a user asked you to install this repo, follow these steps (details per system in
[docs/installation.md](docs/installation.md)):
1. Clone it where the user is working (or where they ask):
   `git clone https://github.com/allthingsaman/ClipKaro.git`. No git? Download
   `https://github.com/allthingsaman/ClipKaro/archive/refs/heads/main.zip` and unpack it as `ClipKaro`.
2. Check the system: OS, `python --version` (3.10-3.14; use `python3` on macOS/Linux), ffmpeg with
   **libx264** and **libass** (`ffmpeg -hide_banner -encoders`, `-filters`), `node --version`
   (20+ recommended), and `nvidia-smi` (an NVIDIA GPU?).
3. Install what's missing, using the commands in [docs/installation.md](docs/installation.md) for
   that system. **Don't run commands that need admin rights (`sudo`) yourself:** give the user the
   exact commands in one block and wait until they say they're done. On Windows, `winget` may show a
   permission prompt; programs it installs only appear on the PATH of new terminals, so if `python`
   or `ffmpeg` still isn't found, ask the user to restart Claude Code (or call the program by its full
   path). Watch for the traps: Fedora's default `ffmpeg-free` has no libx264 (use RPM Fusion's
   `ffmpeg`), and Ubuntu/Debian need `python3-venv`. If the PC has an NVIDIA card but `nvidia-smi`
   fails, the driver is missing: help the user install it (docs/installation.md) before step 4.
4. From inside the ClipKaro folder run `python install.py`. It detects an NVIDIA GPU by itself and
   then installs the GPU libraries and the speech models too. Run it again until every line is
   `[ok]` (interrupted downloads resume). Without an NVIDIA GPU, tell the user that clipping works
   but is slow on the CPU.
5. NVIDIA only: `python run.py gpu large-v3-turbo` must print `[ok] GPU ...`.
6. Report what was installed, then tell the user to **start Claude Code inside the ClipKaro folder**
   and type `clip this video: <link or file>`. A session started in another folder doesn't load
   ClipKaro's clipping skill (`.claude/skills/clip-video/`).

## What you can ask for
Add your wishes to the same message, in normal words (English, Hindi or Hinglish):

- "clip this, but only the 3 best" · "clips under 30 seconds" · "only the parts about money"
- "show me the moments before you cut them" · "don't edit them, just cut"
- "no sound effects" · "no zooms" · "captions lower" · "bigger captions" · "not in capital letters"
- "use #00E5FF as the caption colour" · "Hindi captions in Hindi letters"
- "it's a gameplay video" · "keep it wide (16:9)" · "the video is in English"
- After you see the clips: "clip 2 starts too early" · "make clip 1 shorter" · "use yellow captions"
- Podcasts: "in clip 4, show both of them when he laughs" · "show the whole picture when he holds up the box"

The full list, and what each one changes: [docs/usage.md](docs/usage.md).

**Your own lasting wishes** ("always 5 clips", "my videos are in English", "my brand colour is
#00E5FF"): write them under "My preferences" at the bottom of [CLAUDE.md](CLAUDE.md), or just tell
Claude "add to my preferences: ...". See the [user guide](docs/user-guide.md#saving-your-own-preferences).

## What you get
```
output/<video>/
    edited/01-title.mp4     the finished short videos: upload these
    edited/01-title.srt     the captions as a separate subtitle file
    clips/01-title.mp4      the cut videos without the edit (also fine to post)
    clips.json              the chosen moments, with a caption to post for each one
    transcript/             everything that was said, with times
```

## Languages
| Language | How well |
|---|---|
| English | ✅ fully supported |
| Hindi and Hinglish (and spoken Urdu) | ✅ fully supported: captions in English letters or Hindi letters ([docs/hinglish.md](docs/hinglish.md)) |
| Spanish, French, German, Portuguese, Russian and others written in Latin or Cyrillic letters | 🟡 works, not fine-tuned yet |
| Other scripts (Bengali, Tamil, Arabic, Chinese, ...) | 🔧 the words are written down, but the captions need a font added |

Details: [docs/languages.md](docs/languages.md). Add a language: [docs/adding-a-language.md](docs/adding-a-language.md).

## NVIDIA graphics card
`install.py` finds an NVIDIA card by itself and sets it up: it puts NVIDIA's helper files inside
ClipKaro's own folder (you only need a recent NVIDIA driver, nothing else) and runs a quick test. You
can test it again any time with `python run.py gpu large-v3-turbo`. ClipKaro uses the card
automatically; if it ever fails, it tells you why and carries on without it (slower).
Without an NVIDIA card (including all Macs), everything runs on the processor (CPU): it works, but
it's slow and not recommended for long videos.

## Settings
Your defaults are in `settings.json`: the language (`auto`), the speech model (`auto`), whether to
use the graphics card (`auto`), how Hindi captions are written (`roman` = English letters, or
`devanagari` = Hindi letters) and the gameplay layout (`auto`). You can also just ask Claude to change
them. Details: [docs/usage.md](docs/usage.md#5-your-defaults-settingsjson).

## Running it by hand (optional)
Every step is a plain command you can run yourself:
```bash
python run.py fetch "<link or file>"          # sound + written words
# write output/<project>/clips.json (format in docs/architecture.md)
python run.py romanize <project>              # Hindi/Hinglish: English-letter spellings for the captions
python run.py cut <project>                   # standing videos
python run.py edit <project>                  # the edit
python run.py find <project> "exact phrase"   # exact time of a phrase
```
All commands and options: [docs/usage.md](docs/usage.md#command-reference).

## If something goes wrong
| Problem | Fix |
|---|---|
| `ffmpeg not found` | install ffmpeg ([docs/installation.md](docs/installation.md)), then open a **new** window |
| `your ffmpeg has no libx264` | install the full ffmpeg (Fedora: from RPM Fusion) |
| `Sign in to confirm you're not a bot` | `python run.py fetch <link> --cookies-from-browser chrome` (or firefox / edge) |
| Wrong language detected | `python run.py fetch <link> --lang en --retranscribe` (or `--lang hinglish`) |
| Very slow / graphics card not used | `python run.py gpu` tells you why; `python install.py` sets up the card |

Or simply paste the error into Claude Code and ask it to fix it. More help: [docs/troubleshooting.md](docs/troubleshooting.md).

## Documentation
| | |
|---|---|
| [User guide](docs/user-guide.md) | **start here if you're new**: simple steps, no coding |
| [Installation](docs/installation.md) | setup on Windows, Mac and Linux, NVIDIA graphics cards, updating |
| [Requirements](docs/requirements.md) | what computer you need, and how long things take |
| [Usage](docs/usage.md) | what to type, all the options, the files you get, settings |
| [Languages](docs/languages.md) | which languages work and how well |
| [Hindi / Hinglish](docs/hinglish.md) | how Hindi videos and English-letter captions work |
| [Troubleshooting](docs/troubleshooting.md) | common problems and questions |
| [Architecture](docs/architecture.md) | how it works inside, and how it picks moments (for developers) |
| [Adding a language](docs/adding-a-language.md) | step by step, for developers |
| [Roadmap (v2)](docs/roadmap-v2.md) | how ClipKaro compares with Opus Clip today, and what we'll build next |
| [Changelog](CHANGELOG.md) | what's new in each version |

## Folder layout
```
.claude/skills/clip-video/   the instructions Claude follows to make clips
clipper/                     the program's steps: fetch, parts, topics, romanize, cut, reframe, director, speakers, frames, facecam, brand, plan, edit, sfx, find, gpu
remotion/                    an optional second way to draw the edit
assets/                      fonts, the face-finding model, sound effects
docs/                        documentation
CLAUDE.md                    rules for Claude + your own preferences
settings.json                your defaults
run.py / install.py          starts each step / the setup
output/                      your projects (never uploaded)
```

## Please clip fairly
Only clip and post videos you own or have permission to use. Respect other creators and each
platform's rules. Watch your clips once before posting: automatic captions are good, not perfect.

## Contributing
Bug reports, fixes and new languages are welcome: [CONTRIBUTING.md](CONTRIBUTING.md).

## Credits
- Created and maintained by **Aman Upadhyay** ([@allthingsaman](https://github.com/allthingsaman)).
- Based on [Claude-Video-Clipper](https://github.com/Plextrang/Claude-Video-Clipper) (MIT).
- Fonts: [Montserrat](https://github.com/JulietaUla/Montserrat) and
  [Poppins](https://github.com/itfoundry/Poppins) (Hindi + English letters), SIL Open Font License 1.1.
- Face finding: [YuNet](https://github.com/opencv/opencv_zoo/tree/main/models/face_detection_yunet) (MIT).
- Who is talking, and laughter (podcasts): [sherpa-onnx](https://github.com/k2-fsa/sherpa-onnx) (Apache 2.0)
  running [pyannote segmentation 3.0](https://huggingface.co/pyannote/segmentation-3.0) (MIT),
  [3D-Speaker ERes2Net](https://github.com/modelscope/3D-Speaker) (Apache 2.0) and Google's
  [YAMNet](https://github.com/tensorflow/models/tree/master/research/audioset/yamnet) (Apache 2.0).
- Built on [yt-dlp](https://github.com/yt-dlp/yt-dlp), [faster-whisper](https://github.com/SYSTRAN/faster-whisper),
  OpenAI's [Whisper](https://github.com/openai/whisper) models, [OpenCV](https://opencv.org),
  [FFmpeg](https://ffmpeg.org) and, optionally, [Remotion](https://www.remotion.dev) (free for individuals and
  small companies; [larger companies need a Remotion license](https://www.remotion.dev/license)).
- Works with [Claude Code](https://claude.com/claude-code). ClipKaro is an independent project and
  isn't affiliated with Anthropic.

## License
[MIT](LICENSE) © 2026 Aman Upadhyay. Fonts, the face model and sound effects keep their own
licences; see [LICENSE](LICENSE).
