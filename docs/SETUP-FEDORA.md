# Setup prompt for Claude Code on Fedora Linux

Let Claude Code set up ClipKaro on Fedora for you, including transcription on an NVIDIA GPU.
Open the ClipKaro folder in Claude Code and paste everything inside the box below. It checks
before it changes anything, never runs `sudo` itself (it gives you those commands to run), and is
safe to paste again after a reboot.

Other systems: follow [installation.md](installation.md), or use the short prompt in its section
"Let your AI agent do the setup".

```
Set up this repo on my Fedora Linux PC end to end, with transcription on my NVIDIA GPU.
I don't want CPU transcription on this machine.

About the repo: ClipKaro (long video -> vertical 9:16 shorts) with Hindi/Hinglish support
(auto-detected, Whisper large-v3-turbo, Roman Hinglish captions via `python3 run.py romanize`,
Poppins font for Devanagari), NVIDIA GPU transcription with CPU fallback (clipper/gpu.py,
`install.py --gpu`), a facecam layout for gameplay videos (clipper/facecam.py) and defaults in
settings.json. Read README.md, CLAUDE.md and docs/installation.md first.

Rules
- Anything that needs sudo: don't run it. Give me the exact commands in one block; I'll run them
  in a terminal and tell you when they're done.
- Don't change the repo's code unless a step fails and that's the only fix; then tell me what and why.
- Run long downloads in the background and keep me posted.
- If a reboot is needed, say so. After it I'll paste this prompt again, so make every step safe
  to repeat: check first, skip what's already done.

Step 0 - right version of the repo
These must exist: clipper/facecam.py, clipper/romanize.py, clipper/gpu.py, clipper/models.py,
docs/hinglish.md, settings.json, assets/fonts/Poppins-ExtraBold.ttf. If any is missing, stop and
tell me: this copy of ClipKaro is incomplete or outdated.
If this folder was copied from a Windows PC and a .venv folder came along (it has .venv/Scripts
and no .venv/bin/python), delete .venv: it only works on Windows, and step 4 makes a new one.

Step 1 - check the machine, show me a short table
- Fedora release (cat /etc/fedora-release), kernel, free disk space (needs about 8 GB)
- python3 --version, and whether python3.12 / python3.13 are installed
- GPU: lspci | grep -iE 'vga|3d|nvidia' ; nvidia-smi ; mokutil --sb-state
- Existing NVIDIA packages and where they come from: rpm -qa | grep -i nvidia
- ffmpeg -version (first line); does it have libx264 and libass:
  ffmpeg -hide_banner -encoders | grep libx264 ; ffmpeg -hide_banner -filters | grep -w ass
- node --version

Step 2 - NVIDIA driver (skip if nvidia-smi already shows the GPU with driver 525 or newer)
- If a driver from another source is installed (NVIDIA .run installer, negativo17, NVIDIA's CUDA
  repo), tell me before changing anything. Don't mix driver sources.
- Otherwise use RPM Fusion:
    sudo dnf install https://mirrors.rpmfusion.org/free/fedora/rpmfusion-free-release-$(rpm -E %fedora).noarch.rpm https://mirrors.rpmfusion.org/nonfree/fedora/rpmfusion-nonfree-release-$(rpm -E %fedora).noarch.rpm
    sudo dnf upgrade --refresh
    sudo dnf install akmod-nvidia xorg-x11-drv-nvidia-cuda
  Then wait until `modinfo -F version nvidia` prints a version (the kernel module builds in the
  background for 5-10 minutes) before rebooting.
- If Secure Boot is enabled, the module must be signed or it won't load. Explain both options and
  let me choose: enroll the akmods key
    sudo dnf install kmodtool akmods mokutil openssl
    sudo kmodgenca -a
    sudo mokutil --import /etc/pki/akmods/certs/public_key.der
  (set a one-time password, then on reboot pick "Enroll MOK" on the blue screen), or turn off
  Secure Boot in the BIOS.
- After the reboot, nvidia-smi must show the GPU.
- Don't install the CUDA toolkit: the CUDA libraries come as pip packages in step 4.

Step 3 - system packages
- Full ffmpeg from RPM Fusion (Fedora's default ffmpeg-free has no libx264 encoder, which the
  cutter needs). Enable RPM Fusion as in step 2 if it isn't already, then:
    sudo dnf swap ffmpeg-free ffmpeg --allowerasing
  (If dnf says "No packages to remove for argument: ffmpeg-free", that's fine: it still installs
  the full ffmpeg. Check the transaction first with a dry run: dnf swap --assumeno ...)
- sudo dnf install nodejs git python3-pip     (Node.js helps yt-dlp with YouTube)
  Skip what's already installed.
- Python 3.10-3.14 works. If step 4 can't find prebuilt packages (wheels) for ctranslate2,
  onnxruntime, av or opencv-python on a newer Python, run `sudo dnf install python3.13` and use
  python3.13 instead of python3 from then on (delete .venv first if a broken one was created).

Step 4 - install the tool with GPU support
    python3 install.py --gpu
Everything goes into .venv inside the repo and the Hugging Face cache (~/.cache/huggingface/hub):
- Python packages from requirements.txt: yt-dlp, faster-whisper (CTranslate2), soundfile, numpy,
  opencv-python
- NVIDIA libraries for CTranslate2 (matched to its CUDA version, CUDA 12 today):
  nvidia-cublas-cu12, nvidia-cudnn-cu12 (cuDNN 9), nvidia-cuda-nvrtc-cu12 (about 1.5-2.5 GB)
- Whisper speech models (CTranslate2 format, from huggingface.co):
  tiny  = Systran/faster-whisper-tiny (~75 MB, GPU self-test)
  base  = Systran/faster-whisper-base (~150 MB, language detection)
  large-v3-turbo = mobiuslabsgmbh/faster-whisper-large-v3-turbo (~1.6 GB, the transcription model
  on the GPU and for Hindi/Hinglish)
- Already in the repo, nothing to download: YuNet face detector (assets/models), fonts
  (Montserrat, Poppins), sound effects. Silero VAD ships inside faster-whisper.
Expected: every line [ok], including "[ok] ffmpeg has libx264 and libass" and
"[ok] GPU: 1 NVIDIA GPU(s) ready for transcription".
If a download is cut off (ConnectError, connection reset), run it again: downloads resume.
If opencv fails with "libGL.so.1", run: sudo dnf install mesa-libGL

Step 5 - prove the real model runs on the GPU
    python3 run.py gpu large-v3-turbo
It must print "[ok] GPU ... ran on the GPU". Run nvidia-smi while it runs: python should be using
VRAM (about 2.3 GB). Keep fixing until this passes:
- libcublas / libcudnn / libnvrtc not found: check .venv/lib/python3*/site-packages/nvidia/*/lib
  exists (install.py --gpu installs it; run.py puts it on LD_LIBRARY_PATH)
- "CUDA driver version is insufficient" or similar: the driver is too old, go back to step 2
- out of memory: close other GPU apps and try again (4 GB is enough for large-v3-turbo)

Step 6 - leave settings.json as it is ("device": "auto" uses the GPU when it works). Don't commit,
push or upload anything.

Step 7 - report
A short summary: Fedora, Python, ffmpeg, node, NVIDIA driver and CUDA version (from nvidia-smi),
the GPU test result, where the models are, and what I type to clip a video:
    clip this video: https://youtu.be/...
    clip this video: "/home/<me>/Videos/my video.mp4"
```
