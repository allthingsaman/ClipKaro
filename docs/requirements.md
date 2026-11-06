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
| **Python** | 3.10 | 3.12 or 3.13 (3.14 works too) |
| **ffmpeg** (video tool) | a version with libx264 and libass | ffmpeg 6 or 7 |
| **Node.js** | not needed | version 20 or newer (helps YouTube downloads) |
| **Internet** | for the first setup (2-4 GB, once) and for YouTube links | |

**Doesn't work on:** 32-bit computers, and Windows laptops with an ARM processor (like Snapdragon),
because the speech engine has no version for them. Linux on ARM and Apple Silicon Macs (M1-M4) do
work.

**Python versions:** 3.10 and 3.11 work, but get older versions of some parts; 3.12 to 3.14 get the
newest.

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

**With an NVIDIA graphics card** (measured on a laptop with an RTX 3050, 4 GB):

| Video | Writing down the words | Cutting 4 clips | Editing 4 clips (2.5 minutes of shorts) |
|---|---|---|---|
| 7.7-minute Hinglish review | 72 seconds | about 2 minutes (incl. downloading the video) | about 2 minutes |

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
| `large-v3-turbo` | 1.6 GB | Hindi/Hinglish always, and every language with an NVIDIA card | 3 GB, or 2.3 GB on the card |
| `large-v3` | 3.1 GB | optional: the most accurate and the slowest (`--model large-v3`) | 5 GB, or 4.5 GB on the card |

## Disk space

| What | Size |
|---|---|
| ClipKaro's own parts (the `.venv` folder) | about 1 GB, or about 3 GB with an NVIDIA card |
| Speech models | 0.6 GB (English only, no graphics card) up to about 1.9 GB |
| Each video you clip | the downloaded video (roughly 0.5-1 GB per hour at 1080p) + the clips (20-40 MB each) |

When you're done with a video, delete its folder in `output/` to get the space back.

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
