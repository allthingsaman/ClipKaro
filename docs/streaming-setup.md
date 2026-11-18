# Streaming setup: multistream on OBS (YouTube, Twitch and Kick at once)

This guide sets up OBS to stream to **YouTube (horizontal), YouTube (vertical), Twitch and Kick at the
same time**, and to record the stream for [live clipping](live-clipping.md). It's the setup ClipKaro's
owner uses, written down after getting it working:
- **OBS 33**;
- the free **Aitum Stream Suite** plugin, for the extra outputs and the vertical canvas;
- **stream keys** everywhere.

Other multistream plugins work the same way; only the buttons differ.

**On this page**
1. [What you get](#what-you-get)
2. [Stream keys, not account logins](#stream-keys-not-account-logins)
3. [Set up the outputs (once)](#set-up-the-outputs-once)
4. [Encoder settings](#encoder-settings), [audio](#audio) and [recording](#recording)
5. [Your internet and your laptop](#your-internet-and-your-laptop)
6. [Every stream](#every-stream), and how to [check that you're really live](#check-that-youre-really-live)
7. [When something doesn't work](#when-something-doesnt-work)

## What you get
```
OBS
 ├─ Settings → Stream (YouTube stream key)   → YouTube, horizontal   starts with "Start Streaming"
 ├─ Aitum: YouTube Output (vertical canvas)  → YouTube, vertical     its own button (or Start All)
 ├─ Aitum: Twitch Output (Twitch key)        → Twitch                its own button (or Start All)
 ├─ Aitum: Kick Output (Kick key)            → Kick                  its own button (or Start All)
 └─ Recording → D:/OBS_Recording, 10-minute pieces → ClipKaro live clipping
```

Aitum's **Outputs** dock shows all of them, one row each:

| Row | What it is | How it starts |
|---|---|---|
| Built-in stream | YouTube, horizontal (OBS's own stream) | OBS's **Start Streaming** |
| Built-in record | the recording | by itself with Start Streaming ("Automatically record when streaming") |
| Kick Output | Kick | its own button, or **Start All** |
| Twitch Output | Twitch | its own button, or **Start All** |
| YouTube Output (Aitum Vertical) | YouTube, vertical | its own button, or **Start All** |

A row's button turns green with a running timer while it sends. **Green doesn't prove the platform
accepted it**: see [check that you're really live](#check-that-youre-really-live).

## Stream keys, not account logins
OBS can stream two ways: **log in** with your account (OBS's "Connect account"), or paste a **stream
key**. Use **stream keys** everywhere: the login way sends to one platform only, while keys let every
output go to its own place.

A stream key is like a password for your channel's stream: anyone who has it can stream to your
channel. Never show it on stream or share it. If one leaks, make a new one on the platform.

| Platform | Where to find the stream key |
|---|---|
| YouTube | YouTube Studio → **Create → Go live** → **Stream** tab → Stream key (copy) |
| Twitch | Creator Dashboard → **Settings → Stream** → **Primary Stream Key** (copy) |
| Kick | Creator Dashboard → **Stream URL & Key** (copy the key) |

**Twitch and Kick have nothing to "create".** Unlike YouTube, there is no "create stream" button: your
channel goes live by itself a few seconds after OBS starts sending to your key. You only set the title
and category beforehand ([every stream](#every-stream)).

## Set up the outputs (once)

### 1. YouTube, horizontal: OBS's own stream
**Settings → Stream:**
- **Service:** YouTube - RTMPS.
- Don't "Connect account". Choose **Use Stream Key** and paste your YouTube key.

### 2. Twitch and Kick: Aitum Stream Suite outputs
1. Install **Aitum Stream Suite** (free, from Aitum: aitum.tv), then restart OBS. It adds the **Outputs**
   dock. Can't see it? Turn it on in OBS's top menu → **Docks**.
2. Click the **gear (⚙)** at the bottom left of the Outputs dock → **Output** → **+** (add output):
   - **Twitch:** pick Twitch, paste your Twitch stream key, **Save Output**. The server
     (`rtmp://live.twitch.tv/app`) is filled in.
   - **Kick:** pick Kick, paste your Kick stream key, **Save Output**. The Kick server is filled in and
     can't be changed: that's fine, leave it.
3. Give each its own encoder: [encoder settings](#encoder-settings) below.

### 3. YouTube, vertical (optional)
Aitum's vertical canvas streams a 9:16 picture to YouTube with its own output ("YouTube Output", canvas
"Aitum Vertical"). It has its own stream key: on YouTube, a **second** stream (one horizontal, one
vertical). It starts with **Start All** in the Outputs dock, or with its own button.

For live clipping: in the vertical canvas settings (the gear in its dock), set its **recording path**
and **backtrack path** to a subfolder (for example `D:/OBS_Recording/Vertical`), not the main recording
folder. [Why](live-clipping.md#2-obs-record-while-you-stream-in-10-minute-pieces).

## Encoder settings
**Use H.264 for every stream.** YouTube also accepts HEVC (H.265), but **Twitch and Kick don't**: with
HEVC they accept the connection and drop it again a second later, over and over, while OBS still shows
green. Every output also needs a bitrate within its platform's limit.

| | Built-in stream (YouTube horizontal) | Twitch Output | Kick Output | YouTube Output (vertical) |
|---|---|---|---|---|
| **Where** | Settings → Output → **Streaming** tab | Aitum ⚙ → Output → Twitch: its own encoder settings | Aitum ⚙ → Output → Kick: its own encoder settings | Aitum ⚙ → Output → YouTube (vertical): its own encoder settings |
| Encoder | NVIDIA NVENC **H.264** | NVIDIA NVENC **H.264** | NVIDIA NVENC **H.264** | NVIDIA NVENC **H.264** |
| Rate control | CBR | CBR | CBR | CBR |
| **Bitrate** | **10000 kbps** | **6000 kbps** (the usual Twitch limit) | **8000 kbps** (Kick's maximum) | **6000 kbps** |
| **Keyframe interval** | **2 s** | 2 s | 2 s | 2 s |
| Preset | P5 | P5 | P5 | P5 |
| Profile | high | high | high | high |
| Resolution / FPS | 1920×1080, 60 | 1920×1080, 60 | 1920×1080, 60 | 1080×1920 |
| Audio | AAC 160, **track 1** | AAC 160, track 1 | AAC 160, track 1 | AAC 160, track 1 |

More for the Built-in stream (Streaming tab): Tuning **High Quality**, Multipass **Two Passes (Quarter
Resolution)**, Look-ahead **off** (saves the graphics card with four streams), B-frames **2**.

- **No graphics card from NVIDIA?** Use the matching hardware encoder (AMD: AMF H.264, Intel: QuickSync
  H.264) with the same numbers.
- **Without its own encoder, an Aitum output borrows the main one**, at the main bitrate. At 10000 kbps
  that's too much for Twitch and Kick, which is why each needs its own.
- **The keyframe interval matters:** YouTube warns above 4 seconds, and all three platforms want 2.

## Audio
| Track | What's on it | Used by |
|---|---|---|
| **1** | everything: game or capture card, desktop audio, music, video files, mic | **every stream**, the recording |
| **2** | **only your mic** | the recording, for ClipKaro (your voice alone, so game characters stay out of the captions) |

- **Settings → Output → Streaming → Audio Track: 1.** If the stream used track 2, your viewers would
  hear only your voice.
- **Edit → Advanced Audio Properties:** your mic on tracks 1 and 2, every other source on track 1 only.
  Have several mic sources (built-in mic, USB mic)? Keep only the one you use unmuted, or your voice
  plays twice.

## Recording
The recording shares the main stream's encoder: Settings → Output → **Recording** tab → Video Encoder
**(Use stream encoder)**, so it records at the main stream's 10000 kbps at no extra cost. The rest of
the recording setup (folder, MKV, tracks 1 and 2, 10-minute pieces, "Automatically record when
streaming" under **Settings → General → Output**) is in
[live-clipping.md](live-clipping.md#2-obs-record-while-you-stream-in-10-minute-pieces).

## Your internet and your laptop
**Upload speed.** Every stream is sent separately, all the time:

| | kbps |
|---|---|
| YouTube horizontal | 10000 |
| Twitch | 6000 |
| Kick | 8000 |
| YouTube vertical | 6000 |
| audio (4 × ~160) | ~640 |
| **Total** | **about 31 Mbps of upload, nonstop** |

- Run a speed test first, and look at **upload**, not download. Plan for **about 40 Mbps of real
  upload** or more, so the streams have room.
- **Use an Ethernet cable** if you can. Wi-Fi drops for a moment now and then, and the platforms show
  that as "unstable".
- **Not enough upload?** Lower the YouTube horizontal stream to 8000, or stream to one platform fewer.

**The graphics card.** Four H.264 encodes run on the NVIDIA encoder chip (NVENC). A laptop RTX card can
do that, but if OBS says **"Encoding overloaded"** or stutters:
1. Preset **P4** on all four;
2. Multipass **Single Pass**;
3. Look-ahead **off**;
4. still too much: stream to one platform fewer.

## Every stream
**Before you go live**
1. **YouTube:** create the stream in YouTube Studio (**Create → Go live → Stream**): title, thumbnail,
   category. Using the same stream key every time? Switch on **Auto-start** (and Auto-stop) in the
   stream's settings: then starting OBS takes you live without clicking "Go live" on YouTube.
2. **Twitch:** Creator Dashboard → **Stream Manager** → **Edit Stream Info**: title, category, **Save**.
3. **Kick:** Creator Dashboard → **Stream Info** (the pencil): title, category, save.

**Go live**

4. In OBS, click **Start Streaming**. YouTube (horizontal) and the recording start.
5. In the Outputs dock, click **Start All**: Twitch, Kick and the vertical YouTube start (or click
   their buttons one by one).
6. [Check that you're really live](#check-that-youre-really-live) on every platform.
7. Live clipping? Now say "start live clipping <name>" in Claude Code
   ([going live, step by step](live-clipping.md#going-live-step-by-step)).

**When you end**

8. Stop Aitum's outputs (Twitch, Kick, vertical YouTube) in the Outputs dock (the ■ next to Start All),
   then **Stop Streaming**.

## Check that you're really live
OBS's green timer only means OBS is *trying*. Check on the platforms themselves, about 30 seconds
after starting:

| Platform | Look here | Good | Not good |
|---|---|---|---|
| YouTube | YouTube Studio's live control room | "Live", stream health "Excellent" or "Good" | "No data", or a warning |
| Twitch | twitch.tv/your-channel, or Creator Dashboard → Stream Manager | **Live**, your picture plays | **OFFLINE**, or a red **UNSTABLE** label |
| Kick | kick.com/your-channel, or Creator Dashboard → **Session Info** | **LIVE**, your picture in Stream Preview | **OFFLINE**, or **MISCONFIGURED** |

**OBS's log tells you too:** Help → **Log Files → View Current Log**. An output that keeps writing
"Connection to … successful" followed by "Disconnected from …" every few seconds is being refused by
that platform. Or ask Claude Code (in the ClipKaro folder): "read my OBS log: are Twitch and Kick
connected?"

## When something doesn't work
| You see | Why | What to do |
|---|---|---|
| OBS shows green for Twitch or Kick, but the platform says **offline** | the platform drops the stream every few seconds, almost always because the video is **HEVC (H.265)** | Use **NVIDIA NVENC H.264** ([encoder settings](#encoder-settings)) |
| Kick: **MISCONFIGURED** "Your input bitrate is set too high" | above Kick's 8000 kbps | Kick Output: its own encoder at **8000** or less |
| Twitch: **UNSTABLE**, or "The video download was cancelled" | the bitrate is above about 6000, or the connection drops (Wi-Fi) | Twitch Output: its own encoder at **6000**; use an Ethernet cable |
| **Start Streaming** doesn't start Twitch or Kick | Aitum's outputs have their own buttons | **Start All** in the Outputs dock |
| No "create stream" on Twitch or Kick | there isn't one | Just start the output: the channel goes live by itself |
| The Kick server can't be changed | Aitum fills it in for Kick | Leave it. A log line "No application or playpath in URL!" is harmless |
| "Automatically record when streaming" isn't under Advanced | newer OBS moved it | **Settings → General → Output** |
| Your viewers hear only your voice | the stream uses audio track 2 | Settings → Output → Streaming → Audio Track **1** |
| OBS says "Encoding overloaded" | four encodes are a lot for a laptop | Preset P4, Single Pass, Look-ahead off ([above](#your-internet-and-your-laptop)) |
| Dropped frames (OBS's bottom bar, "Dropped Frames") | not enough upload, or Wi-Fi | Lower the bitrates; use an Ethernet cable |
