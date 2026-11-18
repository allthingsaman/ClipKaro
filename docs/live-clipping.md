# Live clipping: clips posted while you stream

Big game launches (like GTA 6) are a race: clippers post the best moments within hours. With live
clipping, ClipKaro clips **while your stream is still running** and posts the clips to YouTube Shorts,
Instagram Reels and your Facebook Page through PostKaro, about **15-30 minutes after the moment**.

It is **optional**: normal "clip this video" works exactly as before. Live clipping only runs when you
ask for it.

**On this page**
1. [How it works](#how-it-works)
2. [What you need](#what-you-need) and [what it costs](#what-it-costs)
3. [Set it up once](#set-it-up-once): ClipKaro and PostKaro, OBS, your folder and Twitch channel, the
   Twitch keys, a test stream
4. [Going live, step by step](#going-live-step-by-step) (every stream)
5. [When something doesn't work](#when-something-doesnt-work)

How to stream to YouTube, Twitch and Kick at the same time (the encoder settings, the stream keys,
checking that you're really live) is in its own guide: **[streaming-setup.md](streaming-setup.md)**.
Connecting your accounts for posting: **[postkaro.md](postkaro.md)**.

## How it works
1. **OBS records your stream** and starts a new file every 10 minutes (a setting in OBS).
2. **A watcher** (ClipKaro, running in the background) takes each finished 10-minute piece and writes
   down your words, the same way as for any video:
   - the Hinglish model;
   - game characters told apart from you;
   - hints from the sound and picture.

   It also adds what your **Twitch audience** did at that time: chat going wild ("[chat exploded ~15 s:
   KEKW]") and the clips viewers made ("[viewers clipped this]").
3. **Every 10 minutes Claude checks for new pieces.** A helper picks 0-2 clips from each one (nothing is
   forced from a quiet stretch). Then it checks the captions, cuts with your cam layout, edits (captions,
   your logo), runs the automatic quality check, and posts.
4. **PostKaro posts each clip at once on every connected platform**, to each platform's **default**
   account. You chose this for live streams: there is no review step. A clip that fails the quality
   check is never posted.

### The whole flow
```
 PS5 ──► capture card ──► OBS on your PC
                            │
            ┌───────────────┴──────────────────┐
            ▼                                  ▼
  streams to YouTube,               records the same picture to your disk
  Twitch and Kick                   (e.g. D:\OBS_Recording):
  (your viewers watch)              a new file every 10 minutes
            │                                  │
            ▼                                  ▼
  Twitch chat + viewer clips ──►   ClipKaro WATCHER  (starts when you say
  (hints only: WHERE people         "start live clipping gta6")
   reacted, never the video)        - waits until a piece is finished
                                    - writes down your words (Hinglish model)
                                    - adds the Twitch hints to the transcript
                                               │
                                               ▼
                                    CLAUDE, every 10 minutes (/loop)
                                    a helper takes the finished piece and
                                    picks 0-2 clips: captions → cut (cam
                                    layout) → edit (your logo) → quality check
                                               │
                                failed? ───────┤  never posted
                                               ▼  passed
                                    POSTKARO posts each clip at once to
                                    YouTube Shorts, Instagram Reels and your
                                    Facebook Page (your default accounts)
```

**How long it takes.** A moment you play at minute 3 of a piece is online about 15-30 minutes later:
- the piece ends at minute 10;
- writing down the words takes about 4-6 minutes on the graphics card;
- Claude checks every 10 minutes;
- a helper needs about 3-4 minutes per piece.

The first clips of a stream come about 20-30 minutes after you go live.

### Where the video comes from (and why Twitch)
- **The video is your own OBS recording**, never a download from Twitch or YouTube. It is the best
  picture there is (the full-quality original, before any platform compresses it), it has your cam in
  it, and there is nothing to wait for or download.
- **Clipping runs whenever OBS is recording**, whichever platforms you stream to. Not recording (only
  streaming)? Then there is nothing to clip. Streaming only to YouTube that day? Clipping works the
  same, just without the audience hints.
- **Twitch is used only for hints:** its chat can be read live without logging in, and with your free
  Twitch developer keys ClipKaro also sees the clips your viewers make. Both only tell Claude where
  people reacted; your words decide what becomes a clip. Without keys the chat hints still work; only
  the viewer-clip notes are off.
- **Claude never logs in to Twitch.** The watcher reads the chat and the viewer clips, and writes them
  into the transcript as notes. Claude reads those notes next to your words.

While a live session runs, ClipKaro's heavy steps run at **low priority** and edit on the **processor**,
so OBS keeps the graphics card's video encoder and your stream never drops frames because of ClipKaro.
The words are written down on the graphics card only when OBS leaves enough of its memory free;
otherwise on the processor (slower, but safe).

## What you need
| | |
|---|---|
| **ClipKaro and PostKaro** | installed on the computer that runs OBS, with PostKaro's accounts connected ([postkaro.md](postkaro.md)) |
| **OBS** | recording while it streams, in 10-minute pieces (set up below) |
| **Claude Code** | the Claude Code app (in VS Code, the desktop app or a terminal), opened **inside the ClipKaro folder**, and left open during the stream. The claude.ai website can't do this: it can't run programs on your computer |
| **Twitch** (optional) | your channel name, and free developer keys for the viewer-clip notes |
| **Internet** | enough upload for your streams; see [streaming-setup.md](streaming-setup.md#your-internet-and-your-laptop) |

## What it costs
| | |
|---|---|
| **Money** | Nothing extra: OBS, its multistream plugin, Twitch's developer access, ClipKaro and PostKaro are free. |
| **Claude usage** | The real cost: roughly 150-250k tokens per hour of stream (an estimate, not measured yet), so a 6-hour stream is about 1-1.5 million. Comfortable on Claude Max; on Pro you would hit the usage limit after a few hours. |
| **Your computer** | OBS plus ClipKaro. Tested so far on an RTX 3050 laptop (4 GB) with 16 GB of memory. |

## Set it up once

### 1. ClipKaro and PostKaro
- Both installed **on the computer that runs OBS**. In Claude Code (inside the ClipKaro folder):
  "install this repo", then "install PostKaro too".
- **PostKaro's accounts connected** on that same computer. Logins don't move between computers, or
  between Windows and Linux. How: [postkaro.md](postkaro.md).
- **Pick your default accounts.** With several Facebook Pages, Instagram accounts or YouTube channels
  connected, live clips go to the one marked **Default** on PostKaro's Accounts page (**Make default**
  changes it). Check with `python run.py status` in the PostKaro folder: the others say "(not in use)".
- **Your logo** in ClipKaro's `brand` folder (optional).

### 2. OBS: record while you stream, in 10-minute pieces
Open OBS → **Settings**. Set these once:

**Settings → Output** (at the top: **Output Mode: Advanced**) → **Recording** tab

| Setting | Set it to | Why |
|---|---|---|
| Type | Standard | |
| Recording Path | a folder **only for this**, for example `D:/OBS_Recording` (a drive with plenty of space) | ClipKaro takes every new video file in it |
| Recording Format | **Matroska Video (.mkv)** or Hybrid MP4 | a file stays readable even if OBS or the PC crashes |
| Video Encoder | **(Use stream encoder)** | recording costs no extra work. OBS then warns "Recordings cannot be paused": that's fine |
| Audio Track | tick **1** and **2** | 1 = everything; 2 = only your mic, so ClipKaro hears your voice alone |
| **Automatic File Splitting** | **on → Split by Time → 10 min** | the 10-minute pieces |

**Settings → General → Output** (in newer OBS this is here, not under Advanced)

| Setting | Set it to | Why |
|---|---|---|
| **Automatically record when streaming** | **on** | "Start Streaming" alone records nothing, and without a recording there is nothing to clip |
| Keep recording when stream stops | **off** | then "Stop Streaming" also stops the recording, and ClipKaro knows the last piece is finished |

**Settings → Advanced → Recording**

| Setting | Set it to | Why |
|---|---|---|
| Automatically remux to mp4 | **off** | when it's on, OBS makes an `.mp4` copy of every piece in the same folder, and the same moments would be clipped twice |

**Settings → Output → Streaming** tab

| Setting | Set it to | Why |
|---|---|---|
| Audio Track | **1** | track 1 has everything (game, mic, music). Track 2 is only your mic: if the stream used it, your viewers would hear no game sound |

**Edit → Advanced Audio Properties** (your mic on its own track)

| Source | Tracks |
|---|---|
| your **microphone** (only the one you really use; mute any other mic source) | **1 and 2** |
| **everything else**: game or capture-card sound, desktop audio, music, video files, the webcam's own sound | **1 only** |

ClipKaro writes down track 2 as "your voice", so game characters never get into your captions. Untick
track 2 for every source that isn't your mic.

**A vertical canvas plugin (Aitum Vertical, Vertical Canvas)?** Move its recordings out of the
folder: in its settings (the gear in its dock), set its **recording path** and its **backtrack
(instant replay) path** to a subfolder, for example `D:/OBS_Recording/Vertical`. ClipKaro ignores
subfolders. Why: a vertical recording or a backtrack clip saved mid-stream is a new file in the folder,
and ClipKaro would think the 10-minute piece OBS is still writing is finished, and clip it too early.

### 3. Your OBS folder and Twitch channel (in settings.json)
ClipKaro's `settings.json` comes with two **placeholders** for your own values:
```json
"live_folder": "<your OBS recording folder>",
"twitch_channel": "<your Twitch channel>",
```
You don't have to edit them. The first time you say "start live clipping", Claude asks for them
(the OBS Recording Path from step 2, and your Twitch channel name, or "none") and writes your answers
into `settings.json` itself. To change them later, edit the file, or tell Claude: "my OBS folder is
now E:/Streams".

Also in `settings.json`: `"live_post": "now"` posts at once; `"dry"` is for a test stream (step 5).

### 4. Twitch keys (optional: the viewer-clip notes)
1. Open [dev.twitch.tv/console](https://dev.twitch.tv/console) → **Register Your Application**:
   - name "ClipKaro";
   - OAuth Redirect URL `http://localhost` (click **Add**);
   - any category ("Application Integration" or "Broadcaster Suite");
   - client type "Confidential".

   Then **Create**.
2. Open the app (**Manage**), copy its **Client ID**, click **New Secret** and copy that too.
3. In the ClipKaro folder:
   ```
   python run.py live keys --client-id YOUR_ID --client-secret YOUR_SECRET
   ```
   (Or tell Claude "save my Twitch keys: <id> <secret>".) The keys are kept in your user folder, never in
   the ClipKaro folder.

Without keys, the chat is still read (it needs no login); only the viewer-clip notes are off.

### 5. A test stream (strongly recommended, once)
1. Tell Claude **"turn on test mode"** (it sets `"live_post": "dry"` in settings.json).
2. Stream for 20-30 minutes and say **"start live clipping test"**.
3. Clips are made, and PostKaro only shows what it *would* post. Nothing goes online.
4. Watch the clips. Then tell Claude **"turn off test mode"** (back to `"now"`) for the real stream.

## Going live, step by step
Do this every time you stream.

**Before you go live**
1. **Titles:** create your YouTube stream (or use your default key with Auto-start), and set the title
   and category on Twitch and Kick. Details: [streaming-setup.md](streaming-setup.md#every-stream).
2. **Plug in the charger**, and make sure the laptop doesn't go to sleep (Windows: Settings → System →
   Power → "When plugged in, put my device to sleep after": **Never**).

**Go live**

3. In OBS, click **Start Streaming**. Recording starts by itself: check the **red recording dot**
   (or the "Built-in record" timer in Aitum's Outputs dock).
4. Streaming to Twitch and Kick too? Start their outputs (Aitum: **Start All** in the Outputs dock),
   then check that each platform shows you **live**: [how to check](streaming-setup.md#check-that-youre-really-live).
   OBS showing green is not enough.

**Start live clipping**

5. Open Claude Code **inside the ClipKaro folder**, in a **new chat**:
   - **VS Code:** File → Open Folder → the ClipKaro folder, then open a new Claude Code chat.
   - **A terminal:** `cd` into the ClipKaro folder, then type `claude`.

   A new chat for each stream: a live session checks in every 10 minutes for hours, and a fresh chat has
   room for that.
6. Type **"start live clipping gta6"**. The name is up to you: one short word for this stream. The very
   first time, Claude asks for your OBS folder and Twitch channel (step 3 above). Saying it before you
   go live is fine too: the watcher waits for the first piece.
7. Claude starts the watcher and a 10-minute loop (`/loop 10m live clip gta6`). **Keep that Claude Code
   window open** (you can minimise it). Run only **one** live clipping session at a time.

**While you stream**
- The first clips go out about 20-30 minutes after you go live, then every 10 minutes or so.
- **To see how it goes:** ask Claude "how is live clipping going?", run `python run.py live status gta6`,
  or open PostKaro's **Queue** page (the links of posted clips are under **Posted**).
- **No review means trust.** Watch the first few clips on your phone, and delete one on the platform if
  you don't like it.

**When you end the stream**

8. Stop Twitch and Kick (Aitum's Outputs dock), then click **Stop Streaming**. The recording stops with it.
9. Tell Claude **"the stream is over"**. It finishes the last piece (OBS has stopped writing it about 2
   minutes later), stops the watcher, and reports what was posted.
10. The recording pieces stay in your OBS folder. Delete them whenever you like, once the clips are done.
    Or keep them: "clip this" on a recording still works later for long-form highlights.

## Your computer and the stream
- While a live session runs, ClipKaro gives way to OBS: low priority, editing on the processor, and the
  graphics card only when OBS leaves enough memory free (`"live_vram_mb"`, 2800 MB).
- **Graphics memory** (4 GB on an RTX 3050): OBS takes about 1-1.5 GB, the Hinglish speech model about
  2.3 GB. When there isn't room, ClipKaro writes the words down on the processor instead (slower).
  Turning off OBS's preview while streaming (right-click the preview) saves a little more.
- **In-game radio:** songs on GTA's car radio get copyright claims on YouTube and Instagram. Turn the
  radio off or down while streaming.
- The stream's own settings (encoders, bitrates, upload): [streaming-setup.md](streaming-setup.md).

## Good to know
- **A moment that runs across two pieces:** each piece knows the end of the previous one only as context.
  A moment that starts in one piece and ends in the next is clipped from the piece where most of it is.
- **The Twitch notes are approximate.** Viewers watch a few seconds behind you (`"twitch_delay"`, 10 s),
  so their reactions come late. The notes only show Claude where to look; your words decide.
- **Where the clips go:** each platform's default account in PostKaro. Change it on PostKaro's Accounts
  page (**Make default**) before the stream.

## When something doesn't work
| You see | Why | What to do |
|---|---|---|
| No clips at all; `live status` shows no pieces | OBS isn't recording, or records into another folder | Check the red recording dot. The OBS Recording Path must be the same folder as `"live_folder"` in settings.json |
| A piece is clipped before its 10 minutes are up, or the same moment twice | another video file landed in the folder: `.mp4` remux copies, vertical recordings, a saved backtrack clip | Remux off, vertical and backtrack paths in a subfolder ([step 2](#2-obs-record-while-you-stream-in-10-minute-pieces)) |
| Claude asks for your OBS folder or Twitch channel | `settings.json` still has the `<...>` placeholder | Answer once; Claude writes it in |
| Clips are made, but nothing is posted | test mode: `"live_post": "dry"` | Tell Claude "turn off test mode" |
| Clips go to the wrong Facebook Page or Instagram account | PostKaro's defaults | PostKaro → Accounts → **Make default** ([postkaro.md](postkaro.md#several-pages-or-channels-the-default-account)) |
| Game characters' lines in the captions | game sound is also on track 2 | Edit → Advanced Audio Properties: only your mic on track 2 |
| Your viewers hear only your voice | the stream uses audio track 2 | Settings → Output → Streaming → Audio Track **1** |
| The session never ends after "the stream is over" | OBS is still recording ("Keep recording when stream stops" is on) | Click **Stop Recording**; turn that option off |
| OBS shows green for Twitch or Kick, but they say offline | the stream connects and drops again | [streaming-setup.md](streaming-setup.md#when-something-doesnt-work) |

## Commands (normally Claude runs them)
```
python run.py live keys --client-id ID --client-secret SECRET
python run.py live start <name> --folder "<OBS folder>" --twitch <channel>    # keeps running
python run.py live next <name>        # the next piece to clip
python run.py live done <name> <project> --clips N
python run.py live status <name>
python run.py live stop <name>
python run.py post <project> --now [--dry]   # post a piece's clips everywhere at once (through PostKaro)
```
`--folder` and `--twitch` are only needed when settings.json doesn't have them.
