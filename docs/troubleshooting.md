# Problems and questions

**The quickest fix:** copy the error message, paste it into Claude Code (inside the ClipKaro folder)
and add "please fix this". Most errors also print the fix themselves: read the last lines first.

On Mac and Linux, type `python3` wherever this page says `python`.

## Setting up

| Problem | What to do |
|---|---|
| `python` isn't found, or it opens the Microsoft Store (Windows) | Install Python (see [installation.md](installation.md)) and open a **new** window. In Windows Settings → Apps → Advanced app settings → App execution aliases, switch off the two "python" entries. |
| `ffmpeg not found` | Install ffmpeg (see [installation.md](installation.md)) and open a **new** window. |
| `[X] your ffmpeg has no libx264` or `no libass` | Your ffmpeg is a cut-down version. Mac: `brew install ffmpeg-full` (Homebrew's plain `ffmpeg` has no libass; ClipKaro finds ffmpeg-full by itself). Fedora: `sudo dnf swap ffmpeg-free ffmpeg --allowerasing` (from RPM Fusion). openSUSE: ffmpeg from Packman. Others: install your system's full `ffmpeg`. |
| `[X] Python 3.15 is too new` (or `On an Intel Mac ... stops at Python 3.13`) | Install Python 3.12 or 3.13 and run the setup with it. Windows: `winget install -e --id Python.Python.3.12`, then `py -3.12 install.py`. Mac: `brew install python@3.13`, then `python3.13 install.py`. A `.venv` made with the wrong Python is made again by itself. |
| Windows: everything is slow, or OneDrive fills up | ClipKaro is in a folder OneDrive backs up (often Documents or Desktop). Move the ClipKaro folder to your home folder (`C:\Users\<you>\ClipKaro`), delete the `.venv` folder inside it, and run `python install.py` again. |
| `No module named venv` / `ensurepip is not available` (Ubuntu/Debian) | `sudo apt install python3-venv`, delete the `.venv` folder, and run `python3 install.py` again. |
| `First run setup: python install.py` | ClipKaro isn't set up yet in this folder: run `python install.py`. |
| You copied the ClipKaro folder from another computer | Delete the `.venv` folder inside it and run `python install.py` again. That folder only works on the computer that made it. |
| `pip install failed` | Read the message above it. Usually it's the internet connection, or a very new Python: Python 3.12 or 3.13 is the safest. |
| `ImportError: libGL.so.1` (Linux) | `sudo apt install libgl1` (Ubuntu/Debian) or `sudo dnf install mesa-libGL` (Fedora). |
| `ConnectError`, `connection reset` or `WinError 10054` while downloading a model | The connection to the download site dropped. Run the same command again: it continues where it stopped. Still failing? Try another network (or a VPN) for this one download. |

## NVIDIA graphics card

Test it any time: `python run.py gpu large-v3-turbo`.

| Problem | What to do |
|---|---|
| `no NVIDIA graphics card found (or its driver is not installed)` | If you do have an NVIDIA card: `nvidia-smi` must show it. If it doesn't, install or update the driver (see [installation.md](installation.md)) and restart the computer. Then run `python install.py` again: it finds the card by itself. |
| `cublas` / `cudnn` / `nvrtc` ... `not found` / `cannot be loaded` | NVIDIA's helper files are missing: run `python install.py` again. On Linux, always start ClipKaro's steps through `run.py`. |
| `CUDA driver version is insufficient` | The NVIDIA driver is too old: update it (version 525+ on Linux, 528+ on Windows). |
| `out of memory` | Close other programs that use the graphics card (games, video editors, other AI tools). ClipKaro tries a lighter setting first, then the processor. Asking Claude to "use the medium model" also needs less memory. |
| Linux: `nvidia-smi` stops working after a system update | The driver is being rebuilt for the new system: wait a few minutes and restart. With Secure Boot on, the driver must be signed (see [installation.md](installation.md#fedora)). |
| It says `on CPU` although you have an NVIDIA card | Run `python run.py gpu`: it says why the card can't be used. Check that `"device"` in `settings.json` isn't `"cpu"`. Note: finding out the language always takes a few seconds on the processor; only the "transcribing" line matters. |
| It's very slow | Without a working NVIDIA card, ClipKaro listens on the processor, which is slow (a couple of hours for a long video is normal then). See [requirements.md](requirements.md). |
| Mac | Macs always use the processor. That's expected (and slow). |

## Downloading videos

| Problem | What to do |
|---|---|
| `Sign in to confirm you're not a bot` | YouTube wants your login. Put a **cookies file** in the ClipKaro folder (see [below](#youtube-asks-you-to-sign-in)) and run the same command again. On Mac and Linux, "use my Chrome cookies" (or Firefox / Edge) also works: `--cookies-from-browser chrome`. |
| Windows: `Failed to decrypt with DPAPI` | Chrome, Edge and Brave on Windows lock their saved logins, so no other program can read them, even with the browser closed. Use a cookies file instead (see [below](#youtube-asks-you-to-sign-in)), or Firefox: `--cookies-from-browser firefox`. |
| `Could not copy Chrome cookie database` | The browser is still running, perhaps in the background (its icon next to the clock). Close it completely. On Windows, a cookies file is the easier way (see [below](#youtube-asks-you-to-sign-in)). |
| `YouTube did not accept the login in cookies.txt` | The cookies are old: YouTube changes them now and then, and logging out ends them. Export them again and replace the file. |
| `yt-dlp failed` after YouTube changed something | Run `python install.py`: it updates the downloader. Installing Node.js 20+ also helps. |
| `file not found` for a video on your computer | Put the path in quotes and check it (drag the file into the window to paste its exact path). |
| `has no video track` | ClipKaro needs a video, not a sound-only file. |
| `the original video file is gone` | The video was moved or deleted after the first step. Put it back, or start again with its new path. |

### YouTube asks you to sign in

Sometimes YouTube asks a download to prove it isn't a robot ("Sign in to confirm you're not a bot").
It depends on the video and the moment: one video downloads fine, the next one asks. ClipKaro then
needs your YouTube login, as a **cookies file**. You make it once (about 2 minutes):

1. In the browser where you're logged in to YouTube (Chrome, Brave, Edge ...), add the extension
   **"Get cookies.txt LOCALLY"** from the browser's extension store.
2. Open youtube.com, click the extension and press **Export**. It saves `www.youtube.com_cookies.txt`
   to your Downloads folder.
3. Move that file into the ClipKaro folder (next to `run.py`). Keep its name or call it
   `cookies.txt`: both are found by themselves.
4. Run the same command again (or tell Claude "try again").

- ClipKaro uses the file **only when YouTube asks**. Most videos download without your login, as before.
- The file is never uploaded or committed (git ignores it). Treat it like a password: anyone who has it
  is logged in to your YouTube account.
- It stops working after a while (YouTube changes the login now and then, and logging out ends it).
  Then export it again and replace the file. It lasts longer if you export it from a private window
  (allow the extension there first): log in to YouTube in the private window, export, then close it.
- The file can live somewhere else too: `"cookies_file": "C:/Users/you/yt-cookies.txt"` in
  `settings.json`, or `python run.py fetch <link> --cookies <file>` for one video.
- Why not the browser itself (`--cookies-from-browser`)? On Windows, Chrome, Edge and Brave lock their
  saved logins, so no other program can read them. On Mac and Linux, and with Firefox anywhere, that
  still works.
- YouTube can block an account that downloads a lot. ClipKaro asks only a few times per video, but if
  you clip many videos a day, a second YouTube account for this is safer.

## The written words and the language

| Problem | What to do |
|---|---|
| Wrong language found | Tell Claude "the video is in English" (or Hinglish, Spanish, ...). By hand: `python run.py fetch <link> --lang en --retranscribe`. |
| `transcript already exists` | The words were already written down. To do it again, add `--retranscribe` (or ask Claude to "redo the transcript"). |
| Hindi words are misspelled | Whisper isn't perfect with fast or noisy Hindi. Claude fixes obvious mistakes when it writes the captions; tell it about any others ("in clip 2, X should be Y"). |
| Hindi is very slow | Hindi uses the big model. Without an NVIDIA card it takes 1-4 times the video's length. |
| `run.py find` says `no exact match` | Use fewer words: Whisper may have spelled one differently. For Hindi, type the words in Hindi letters, as they appear in the transcript. |

## Cutting and editing

| Problem | What to do |
|---|---|
| `cut --check` warns `starts/ends mid-sentence` | Claude fixes these. By hand: find the exact time with `run.py find` and change the clip, unless you cut there on purpose. |
| The speaker's face isn't in the frame | ClipKaro didn't find a face in that shot, so it showed the whole picture over a blurred background. For gameplay with a webcam, see the next line. |
| Gameplay: the webcam is in the wrong place, or not found | Tell Claude where the webcam is ("the webcam is in the bottom-left corner"). By hand, in `settings.json`: `"facecam": {"x": 0.80, "y": 0.35, "w": 0.19, "h": 0.34, "shape": "circle"}` (parts of the picture: left, top, width, height). `--layout crop` switches this layout off. |
| Gameplay: the webcam looks small, with blurred game around or under it | The webcam's box holds part of the game too. `cut` then warns "the webcam box is taller than a camera picture" and saves `frames/facecam-box.jpg` with the box in red. Tell Claude: it writes the webcam's real box in the project's `project.json` (`"facecam"`, in pixels) and cuts again. To make every webcam bigger or smaller, change `"facecam_margins"` in `settings.json`. |
| A podcast clip shows the wrong person, or misses someone laughing | Tell Claude the moment: "in clip 4 at 0:23, show both of them" or "show Khan Sir there". By hand, in clips.json: `"framing": [[a, b, "split"]]` (or `"left"` / `"right"`), in source seconds, then `cut --clips 4` and `edit --clips 4`. `python run.py frames <project> --clips 4` shows what each moment keeps. |
| `speaker models not available; classic framing for two-person shots` | sherpa-onnx isn't installed, or the voice models couldn't be downloaded (no internet the first time). Run `python install.py` again with internet, then cut again. Everything else works without them. |
| Captions in the wrong place | Tell Claude "captions higher" or "captions lower". By hand: `--caption-y 1100` (higher) or `--caption-y 1500` (lower). |
| Hinglish captions show Hindi letters | Some words don't have an English-letter spelling yet: `python run.py romanize <project>`, fill in `romanize.json`, and run `edit` again (or ask Claude). |
| The caption colour looks dull | Tell Claude "use yellow captions". By hand: `python run.py brand <project> --accent "#FFD60A"`, then `edit` again. |
| `remotion render failed` / `Remotion is not installed yet` | Run `python install.py --remotion` (needs Node.js), or just use the normal editor. |

## Questions

**Is it free? Do I need any keys or accounts?**
ClipKaro is free and open source (MIT licence) and needs no keys of its own. The AI helper (for
example Claude Code) uses your own Claude account and plan.

**Does it upload my videos?**
No. Listening, cutting and editing all happen on your computer. It only uses the internet to download
a video from a link and, once, the speech models.

**Can I use it without Claude Code?**
Yes. Other AI helpers that can run commands and edit files work too: see [AGENTS.md](../AGENTS.md).
You can even do it without any AI, by choosing the moments yourself in `clips.json`: see
[usage.md](usage.md#6-doing-the-steps-by-hand-optional).

**Does it work without internet?**
After setup, yes, for video files on your computer. Links need the internet to download.

**Do I need an NVIDIA graphics card?**
It's strongly recommended. Without one, everything still works, but writing down the words is slow:
a long video can take a couple of hours. See [requirements.md](requirements.md).

**Which languages work?**
English and Hindi/Hinglish fully, and most other languages at a basic level. See
[languages.md](languages.md).

**How do I make Claude remember what I like?**
Write it under "My preferences" at the bottom of `CLAUDE.md`, or ask Claude "add to my preferences:
...". See the [user guide](user-guide.md#saving-your-own-preferences).

**Where are my clips?**
In the ClipKaro folder: `output` → your video's folder → `edited` (finished) and `clips` (cut only).

**How do I free up disk space?**
Delete the folders in `output` that you don't need anymore. The speech models are listed in
[installation.md](installation.md#where-things-are-kept).

**Can I post clips of other people's videos?**
Only if you own them or have permission. Respect other creators and each app's rules.

**Still stuck?** Open an issue on GitHub with what you did, the full error message, your system
(Windows, Mac or Linux), and what `python install.py` prints.
