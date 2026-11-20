# What computer you need

ClipKaro listens to your video and writes down every word **on your own computer**. That is heavy
work, so how fast it goes depends a lot on your computer.

**In short:**
- ✅ **Recommended: a computer with an NVIDIA graphics card (4 GB or more).** A video is ready in
  minutes.
- ⚠️ **Without an NVIDIA graphics card: it works, but it's slow (not recommended).** Writing down
  the words then runs on the processor (CPU), and one video can take **a couple of hours** (users
  have reported about 2 hours for one video). Hindi/Hinglish is the slowest, because it uses a
  bigger, more accurate model.
- Cutting and editing run on the processor on every computer, and are fine either way.

## Minimum and recommended

| | Minimum (works, but slow) | Recommended |
|---|---|---|
| **System** | Windows 10 (64-bit), macOS 13, or 64-bit Linux with Python 3.10+ (Ubuntu 22.04+, Debian 12+, Fedora 38+) | Windows 11, macOS 14 or newer, a current Linux |
| **Graphics card** | none (everything runs on the processor: slow) | **NVIDIA with 4 GB+ of video memory** (GTX 16-series, RTX 20-series or newer), with an up-to-date driver |
| **Processor (CPU)** | 64-bit, 4 cores | 8 cores or more |
| **Memory (RAM)** | 8 GB | 16 GB |
| **Free disk space** | 8 GB | 20 GB or more (videos take space) |
| **Python** | 3.10 | 3.12 or 3.13 (3.14 works too, except on Intel Macs; 3.15 is too new for the speech engine) |
| **ffmpeg** (video tool) | a version with libx264 and libass | ffmpeg 6 or 7 |
| **Node.js** | not needed | version 20 or newer (helps YouTube downloads) |
| **Internet** | for the first setup (2-4 GB, once) and for YouTube links | |

**Doesn't work on:** 32-bit computers, and Windows laptops with an ARM processor (like Snapdragon),
because the speech engine has no version for them. Linux on ARM and Apple Silicon Macs (M1-M4) do
work.

**Python versions:** 3.10 and 3.11 work, but get older versions of some parts; 3.12 to 3.14 get the
newest. 3.15 doesn't work yet: the speech engine's onnxruntime part has no version for it (November
2026). `install.py` says so before it starts.

**Macs:** Apple Silicon (M1 or newer). Intel Macs can work, with Python 3.12 or 3.13, but Homebrew has no
ready-made full ffmpeg for them (it builds it, which takes a long time).

## Graphics cards

| Your graphics card | What happens |
|---|---|
| **NVIDIA, 4 GB or more** | ✅ Fast. `install.py` finds it and sets it up by itself. The big speech model used about **2.3 GB** of the card's memory in our tests. |
| **NVIDIA, 2-3 GB** | Might work: if the card runs out of memory, ClipKaro tries a lighter setting, and then falls back to the processor (slow). |
| **NVIDIA, older than GTX 10-series** | Too old: the processor is used (slow). |
| **AMD or Intel graphics** | Not used for this: the processor is used (slow). |
| **Mac (any)** | The processor is used (slow). Apple Silicon is quicker than older Macs, but still much slower than an NVIDIA card. |

You need an NVIDIA **driver** recent enough for CUDA 12 (version 525 or newer on Linux, 528 or
newer on Windows): simply install the latest one. You don't need to install anything else from
NVIDIA: `install.py` puts the extra NVIDIA files inside ClipKaro's own folder.

## How long it takes

**With an NVIDIA graphics card** (measured on a laptop with an RTX 3050, 4 GB, November 2026):

| Video | Writing down the words | Choosing the clips | Cutting | Editing | Start to finish |
|---|---|---|---|---|---|
| 7.7-minute Hinglish review | 72 seconds | | about 2 minutes for 4 clips (incl. downloading the video) | about 2 minutes | |
| 37-minute Hindi gameplay stream, deep clips, 8 clips | about 14 minutes, download included | about 20 minutes (deep clips are 8 of them) | about 4 minutes | about 2 minutes | **42 minutes** |
| 4-hour Hinglish GTA stream with 3 friends, 160 clips | about 40 minutes (6 times faster than the video plays), plus 22 minutes for the second hearing | | about 35 seconds a clip (32-second clips, webcam layout and the picture check included) | about 14 seconds a clip | |

**Gameplay and streams take a little longer** than a podcast of the same length, because ClipKaro also
listens a second time (about 11 times faster than the video plays, with an NVIDIA card), checks the
picked clips' words with helpers, and looks at the picture (one frame every 10 seconds: under a minute
for 4 hours of video). About 10-15 minutes more for a 30-minute stream.

**Rough times for a whole video** (with an NVIDIA card, standard mode, after the download):

| Video length | Podcast or talk | Gameplay or live stream |
|---|---|---|
| 20 minutes | about 20 minutes | about 30 minutes |
| 30 minutes | about 25 minutes | about 35-40 minutes |
| 1 hour | about 35-45 minutes | about 50-60 minutes |

Deep clips add about 8-15 minutes. Quick mode saves about 5-10 minutes (no critic, no helpers).

**Without one, on the processor (not recommended)** (English measured on a mid-range Windows laptop):

| Video | Writing down the words | Cutting | Editing |
|---|---|---|---|
| 10-minute English talk | about 1.5 minutes | about 2.5 minutes | about as long as the clips |
| 88-minute English podcast | about 14 minutes | about 5 minutes | about as long as the clips |
| Hindi/Hinglish | **1 to 4 times the length of the video** (a 35-second clip took 2 minutes 11 seconds; a 30-minute video can take about 2 hours) | a few minutes | about as long as the clips |

Rules of thumb:
- **English without a graphics card**: writing down the words takes about a quarter of the video's
  length.
- **Hindi/Hinglish without a graphics card**: 1-4 times the video's length. Use an NVIDIA card for
  these videos if you can.
- **Editing** takes about as long as the clips themselves (a 40-second clip: about 30-40 seconds).
- **The very first time** also includes the downloads (once).

## The speech models

The speech models are the "ears" of ClipKaro. They download once and are kept in
`~/.cache/huggingface/hub` (Windows: `C:\Users\<you>\.cache\huggingface\hub`).

| Model | Download size | Used for | Memory while it runs (about) |
|---|---|---|---|
| `tiny` | 78 MB | only the quick graphics-card test | very little |
| `base` | 148 MB | finding out the language (a few seconds) | 0.5 GB |
| `small.en` | 486 MB | English without a graphics card | 1.5 GB |
| `small` | 486 MB | other languages without a graphics card | 1.5 GB |
| `medium` | 1.5 GB | optional (`--model medium`) | 2.5 GB, or 2 GB on the card |
| `large-v3-turbo` | 1.6 GB | Hindi/Hinglish without an NVIDIA card, and every other language with one | 3 GB, or 2.3 GB on the card |
| `large-v3` | 3.1 GB | optional: the most accurate and the slowest (`--model large-v3`) | 5 GB, or 4.5 GB on the card |
| Hinglish model (`Hub84/faster-whisper-hinglish-prime`) | 1.5 GB | Hindi/Hinglish with an NVIDIA card (writes Hinglish in English letters) | about 2 GB on the card |
| Second hearing (`nikh360pro/capsbro-hinglish-ct2`) | 1.5 GB | careful listening: Hindi/Hinglish gameplay and streams, NVIDIA only | about 2 GB on the card |
| Third hearing (`MSpider3/whisper-hindi2hinglish-swift-ct2`) | 78 MB | careful listening: each picked clip once more | very little |

The last two download the first time a Hindi/Hinglish gameplay video or stream is clipped on a computer
with an NVIDIA card. Podcasts, English videos and computers without one never download them.

For **podcasts with two people on screen**, three small models are downloaded the first time they're
needed (about 50 MB in total, kept in `~/.cache/clipkaro/models`): one finds who is talking, one
tells the two voices apart, and one hears laughter. They run on the processor in a few seconds per
clip. Video work uses a lot of memory: with 8 GB of RAM, close other big programs while cutting.

## Disk space

| What | Size |
|---|---|
| ClipKaro's own parts (the `.venv` folder) | about 1 GB, or about 3 GB with an NVIDIA card |
| Speech models | 0.6 GB (English only, no graphics card) up to about 1.9 GB; about 5 GB with the Hinglish model and careful listening (Hindi/Hinglish gameplay on an NVIDIA card) |
| Starter sound effects | about 3 MB |
| Voice and laughter models (podcasts) | about 50 MB |
| Each video you clip | the downloaded video (roughly 0.5-1 GB per hour at 1080p) + the clips (20-40 MB each) |

When you're done with a video, delete its folder in `output/` to get the space back.

## How much Claude usage

ClipKaro's own programs (writing down the words, cutting, editing) run on your computer and use none of
your Claude plan. Claude is the editor: it reads the video's words and picks the clips, and its helpers
read long videos in parts, judge every idea and check the words. That part uses your plan.

Claude plans don't charge per video; they have usage limits that reset every few hours and every week.
To compare videos fairly, the tables show the **tokens** (the pieces of text Claude reads and writes,
its thinking included; text it reads again from its short-term memory is left out, because it counts
very little) and **what the same work would cost on Claude's pay-per-use API** (Claude Opus 5.5,
November 2026 prices). You don't pay that on a plan: it only shows how big the job is.

**Measured on real runs** (added up from Claude Code's own record of every request):

| Video | Mode | Tokens | Same work on the API |
|---|---|---|---|
| 7-minute talk, picked in one read (like quick mode today) | quick | 0.2 million | about $3 |
| 37-minute Hindi gameplay stream, 8 clips | standard | about 0.6 million | about $7-8 |
| the same video, with deep clips | deep | 1.1 million | about $13 |
| 4-hour Hinglish GTA stream, 160 clips ("no limit"), deep clips, careful listening | deep | 8.2 million for the helpers, plus the main editor | $79 for the helpers, plus about $10-20 |

**Worked out from those measurements, per video length** (Hindi/Hinglish or English; the usual number
of clips, about one per 7 minutes):

| Video length | Quick | Standard (the default) | Deep (standard + deep clips) |
|---|---|---|---|
| 20 minutes | about 0.25-0.3 million ($3-4) | about 0.45-0.6 million ($5-8) | (asked only for videos over 21 minutes) |
| 30 minutes | about 0.3-0.35 million ($4-5) | about 0.5-0.7 million ($6-8) | about 1-1.2 million ($11-14) |
| 1 hour | about 0.4-0.55 million ($5-7) | about 0.9-1.1 million ($11-13) | about 1.5-1.8 million ($18-22) |

**Gameplay and live streams** (Hindi/Hinglish with an NVIDIA card) add the word check of every picked
clip (about $0.19 a clip), the frame sheets (about 1,550 tokens a sheet, one sheet per 3.5 minutes) and
the close-ups (about $0.70 for a packet of up to 24 spots), in every mode:

| Video length | Extra for gameplay or a stream |
|---|---|
| 20 minutes | about 0.12 million ($1.50) |
| 30 minutes | about 0.15 million ($2) |
| 1 hour | about 0.25 million ($3) |

**More clips cost more.** Every extra clip idea is judged three times by the critic (about $0.08 an
idea), every picked clip gets its posting texts, and in gameplay its word check. "No limit" on a
4-hour stream (160 clips) is about the work of 8-10 standard videos.

**Is it affordable for a small creator?**
- **The computer part is free**, and an NVIDIA card makes it fast. Gameplay needs no extra hardware
  (careful listening simply switches off without an NVIDIA card).
- **Claude Code needs a paid Claude plan** (Pro or higher). **Quick mode** is the everyday choice on
  Pro: it uses about half of standard. Use standard for the videos that matter, and deep for long
  podcasts with stories spread across them.
- **Find out what your plan holds:** type `/usage` in Claude Code before and after your first
  video. The difference tells you how many videos fit in your limits.
- **Big jobs** (a 4-hour stream, "no limit", 100+ clips) are better on a larger plan, or split over
  a few days.

## Check your computer

The simplest way: run `python install.py` (`python3` on Mac/Linux). It checks everything and tells
you what's missing, including whether an NVIDIA card was found.

Or check by hand:
```bash
python --version                  # should be 3.10 or newer
ffmpeg -hide_banner -encoders | grep libx264      # Windows PowerShell: | findstr libx264
ffmpeg -hide_banner -filters  | grep -w ass       # Windows PowerShell: | findstr " ass "
nvidia-smi                        # NVIDIA only: shows your card, its driver and its memory
```
