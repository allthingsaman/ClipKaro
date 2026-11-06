# Installation guide

ClipKaro works on **Windows, Mac and Linux**. Setting it up takes about 10-30 minutes, mostly
waiting for downloads. You only do it once.

Never used Claude Code or a terminal before? The **[user guide](user-guide.md)** walks you through
everything in very simple steps.

Before you start, check that your computer is suitable: [requirements.md](requirements.md). An
NVIDIA graphics card is strongly recommended; without one ClipKaro works, but slowly.

## The easiest way: let Claude Code do it
1. Get [Claude Code](https://claude.com/claude-code) (desktop app, terminal version, or the
   VS Code / JetBrains add-on) and sign in.
2. Open it in the folder where ClipKaro should go (for example your Documents folder) and type:

   > **install this repo: https://github.com/allthingsaman/ClipKaro**

3. Claude downloads ClipKaro into a new `ClipKaro` folder, checks your computer and installs what's
   missing. **It finds out by itself whether you have an NVIDIA graphics card** and sets it up if you
   do. Things that need your computer's password (like `sudo` on Linux), it gives you to run
   yourself: run them, then tell Claude you're done. On Windows, if it says a program isn't found
   right after installing it, restart Claude Code and say "continue the installation".
4. When it says setup is complete, **start Claude Code inside the new `ClipKaro` folder** (terminal:
   `cd ClipKaro`, then `claude`; desktop app or VS Code: open that folder) and type
   `clip this video: <link or file>`.

Already downloaded ClipKaro yourself? Open Claude Code inside the `ClipKaro` folder and type
**install this repo**. It does the same steps.

The rest of this page is the same setup done by hand.

---

## What gets installed
| | What | Why |
|---|---|---|
| 1 | **[Claude Code](https://claude.com/claude-code)** (or another AI helper, see [AGENTS.md](../AGENTS.md)) | the "editor" that reads what's said in the video and picks the best moments |
| 2 | **Python 3.10-3.14** (3.12 or 3.13 is the safest choice) | the language ClipKaro is written in |
| 3 | **ffmpeg**, a version with **libx264** and **libass** | the tool that cuts the video and draws the captions |
| 4 | **Node.js 20+** (recommended) | helps download from YouTube without problems |
| 5 | **Git** (optional) | downloads and updates ClipKaro; you can also download it as a ZIP file |
| 6 | **NVIDIA driver** (only if you have an NVIDIA graphics card) | lets ClipKaro use the card, which makes it much faster |
| 7 | **ClipKaro itself**: `python install.py` | sets up everything else inside ClipKaro's own folder |

`install.py` changes nothing outside the ClipKaro folder, except the speech models, which are kept in
a shared place (`~/.cache/huggingface/hub`).

Jump to your system: [Windows](#windows-10-and-11) · [Mac](#mac) ·
[Linux: Ubuntu / Debian](#ubuntu-debian-linux-mint-pop_os) · [Fedora](#fedora) ·
[Arch](#arch-linux-manjaro-endeavouros) · [other Linux](#other-linux)

---

## Windows 10 and 11

Open **PowerShell** or **Terminal** (Start button → type "Terminal") and run these lines one by one.
`winget` comes with Windows 10 and 11.

```powershell
winget install -e --id Python.Python.3.12
winget install -e --id Gyan.FFmpeg
winget install -e --id OpenJS.NodeJS.LTS
winget install -e --id Git.Git
```

**Close the window and open a new one** (new programs only show up in new windows), then check:

```powershell
python --version      # Python 3.12.x
ffmpeg -version       # ffmpeg version ...
node --version        # v20 or newer
```

If `python` opens the Microsoft Store instead: Settings → Apps → Advanced app settings → App
execution aliases → switch off the two "python" entries. If you install Python from
[python.org](https://www.python.org/downloads/) instead, tick **"Add python.exe to PATH"** during
the install.

Download ClipKaro and set it up:

```powershell
git clone https://github.com/allthingsaman/ClipKaro.git
cd ClipKaro
python install.py
```

**NVIDIA graphics card?** Install or update its driver first, with the
[NVIDIA App](https://www.nvidia.com/en-us/software/nvidia-app/) (or from nvidia.com). `install.py`
then finds the card and sets it up by itself.

---

## Mac

Install [Homebrew](https://brew.sh) if you don't have it yet (paste this into the Terminal app):

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

Then:

```bash
brew install python ffmpeg node git
git clone https://github.com/allthingsaman/ClipKaro.git
cd ClipKaro
python3 install.py
```

Macs don't have NVIDIA graphics cards, so ClipKaro writes down the words on the processor. It works,
but it's slow, especially for Hindi/Hinglish (1-4 times the video's length). Apple Silicon (M1 or
newer) is the quickest Mac for this. On a Mac, type `python3` wherever these docs say `python`.

---

## Linux

On Linux, type `python3` wherever these docs say `python`.

### Ubuntu, Debian, Linux Mint, Pop!_OS

```bash
sudo apt update
sudo apt install python3 python3-venv python3-pip ffmpeg nodejs git
node --version     # if this is older than v20, install the LTS version from https://nodejs.org instead
```

Don't skip `python3-venv`: without it, ClipKaro can't create its private `.venv` folder.

**NVIDIA graphics card?** Run `sudo ubuntu-drivers install`, restart the computer, and check that
`nvidia-smi` shows your card. (Debian: install `nvidia-driver` from the non-free repository.)

### Fedora

Fedora's own ffmpeg (`ffmpeg-free`) can't make the kind of video files ClipKaro needs (it has no
libx264). Use the full ffmpeg from [RPM Fusion](https://rpmfusion.org):

```bash
# 1. turn on RPM Fusion (skip if it's already on)
sudo dnf install https://mirrors.rpmfusion.org/free/fedora/rpmfusion-free-release-$(rpm -E %fedora).noarch.rpm https://mirrors.rpmfusion.org/nonfree/fedora/rpmfusion-nonfree-release-$(rpm -E %fedora).noarch.rpm

# 2. the full ffmpeg (it's fine if dnf says "No packages to remove for argument: ffmpeg-free")
sudo dnf swap ffmpeg-free ffmpeg --allowerasing

# 3. the rest
sudo dnf install nodejs git python3-pip
```

**NVIDIA graphics card?** If `nvidia-smi` doesn't show your card yet:

```bash
sudo dnf install akmod-nvidia xorg-x11-drv-nvidia-cuda
```

Wait 5-10 minutes until `modinfo -F version nvidia` prints a version number (the driver is being
built in the background), then restart the computer. If **Secure Boot** is on, the driver must be
signed or it won't start: either sign it (`sudo kmodgenca -a`, then
`sudo mokutil --import /etc/pki/akmods/certs/public_key.der`, choose a one-time password, and pick
"Enroll MOK" on the blue screen when the computer restarts), or switch Secure Boot off in the BIOS.
Use only one source for the NVIDIA driver (RPM Fusion, negativo17, NVIDIA's own repo or its `.run`
installer): don't mix them.

There's also a ready-made message you can paste into Claude Code to have it do the whole Fedora
setup step by step: [SETUP-FEDORA.md](SETUP-FEDORA.md).

### Arch Linux, Manjaro, EndeavourOS

```bash
sudo pacman -S python ffmpeg nodejs npm git
```

**NVIDIA graphics card?** Follow the [Arch Wiki NVIDIA page](https://wiki.archlinux.org/title/NVIDIA)
(for current cards usually `nvidia-open` + `nvidia-utils`), restart, and check `nvidia-smi`.

### Other Linux
Install Python 3.10+ (with its `venv` part), an ffmpeg that includes **libx264** and **libass** (on
openSUSE, from the Packman repository), Node.js 20+ and git. The NVIDIA driver comes from your
distribution.

### Download ClipKaro and set it up (all Linux)

```bash
git clone https://github.com/allthingsaman/ClipKaro.git
cd ClipKaro
python3 install.py
```

---

## What `install.py` does

```
python install.py             # everything (an NVIDIA graphics card is found and set up automatically)
python install.py --cpu       # skip the NVIDIA part
python install.py --models    # also download the speech models now (useful without an NVIDIA card)
python install.py --remotion  # also install the optional Remotion editor (needs Node.js)
```

1. **Checks your tools**: Python, ffmpeg (and that it has libx264 and libass) and Node.js. If
   something is missing, it prints an `[X]` line with the exact command to install it on **your**
   system.
2. **Sets up ClipKaro's private parts** in a `.venv` folder inside ClipKaro: the downloader
   (yt-dlp), the speech engine (faster-whisper) and a few helpers. It also updates the downloader,
   because YouTube changes often.
3. **Looks for an NVIDIA graphics card.** If it finds one (with a working driver), it installs
   NVIDIA's helper files into `.venv` (about 1.5-2.5 GB), runs a quick test, and downloads the speech
   models (about 1.7 GB). If it finds none, it says so: ClipKaro then works on the processor, slowly.
4. Without an NVIDIA card, the first video you clip downloads the speech model it needs (about
   490 MB for English, 1.6 GB for Hindi/Hinglish).

**You can run it again any time.** Work that's already done is skipped. If a download is
interrupted ("ConnectError", "connection reset"), just run it again: it continues where it stopped.

A good run with an NVIDIA card looks like this:

```
== ClipKaro setup ==
[ok] Python 3.12.7
[ok] ffmpeg
[ok] ffprobe
[ok] ffmpeg has libx264 and libass
[ok] node v22.11.0 (helps YouTube downloads; needed only for the optional Remotion engine)
[ok] Python packages (yt-dlp up to date)
[ok] NVIDIA GPU found (1): setting up GPU transcription
[ok] GPU: 1 NVIDIA GPU(s) ready for transcription ("tiny" ran on the GPU)
Setup complete. Open this folder in Claude Code (or another AI coding agent, see AGENTS.md) and say:
    clip this video: https://youtu.be/...
```

Without an NVIDIA card, instead of the two GPU lines you see:

```
[!] no NVIDIA graphics card found (or its driver is not installed). Videos will be transcribed on the CPU: that works, but it is slow (not recommended).
```

## Check that it works

With an NVIDIA card, this tests the real speech model on it (about 10 seconds):
```bash
python run.py gpu large-v3-turbo
```
It should print `[ok] GPU: 1 NVIDIA GPU(s) ready for transcription ("large-v3-turbo" ran on the GPU)`.

Then open Claude Code inside the ClipKaro folder and try a short video:

> clip this video: https://youtu.be/...

## Where things are kept
| What | Where | Size |
|---|---|---|
| ClipKaro's private parts | the `.venv` folder inside ClipKaro | about 1 GB, about 3 GB with an NVIDIA card |
| Speech models | `~/.cache/huggingface/hub/` (Windows: `C:\Users\<you>\.cache\huggingface\hub`) | 0.6-1.9 GB |
| Your clips and projects | the `output` folder inside ClipKaro | about 0.1-1 GB per video |

To keep the speech models somewhere else, set the `HF_HOME` environment variable to another folder.

## Updating
Ask Claude Code (inside the ClipKaro folder): **update ClipKaro**. Or by hand:
```bash
git pull
python install.py
```

## Removing ClipKaro
Delete the ClipKaro folder. To also remove the speech models, delete the
`models--Systran--faster-whisper-*` and `models--mobiuslabsgmbh--faster-whisper-large-v3-turbo`
folders in the place shown in the table above. Python, ffmpeg and Node.js are separate programs:
keep or remove them as you like.

## Problems?
See [troubleshooting.md](troubleshooting.md), or paste the error into Claude Code and ask it to fix it.
