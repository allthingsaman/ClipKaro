# Live clipping: clips posted while you stream

Big game launches (like GTA 6) are a race: clippers post the best moments within hours. With live
clipping, ClipKaro clips **while your stream is still running** and posts the clips to YouTube Shorts,
Instagram Reels and your Facebook Page through PostKaro, about **15-30 minutes after the moment**.

It is **optional**: normal "clip this video" works exactly as before. Live clipping only runs when you
ask for it.

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
4. **PostKaro posts each clip at once on every connected platform.** You chose this for live streams: there
   is no review step. A clip that fails the quality check is never posted.

While a live session runs, ClipKaro's heavy steps run at **low priority** and edit on the **processor**,
so OBS keeps the graphics card's video encoder and your stream never drops frames because of ClipKaro.
The words are written down on the graphics card only when OBS leaves enough of its memory free;
otherwise on the processor (slower, but safe).

## What it costs
| | |
|---|---|
| **Money** | Nothing extra: OBS, its multistream plugin, Twitch's developer access, ClipKaro and PostKaro are free. |
| **Claude usage** | The real cost: roughly 150-250k tokens per hour of stream (an estimate, not measured yet), so a 6-hour stream is about 1-1.5 million. Comfortable on Claude Max; on Pro you would hit the usage limit after a few hours. |
| **Your computer** | OBS plus ClipKaro. Tested so far on an RTX 3050 laptop (4 GB) with 16 GB of memory: see "Your stream settings". |

## Before your first live stream (once)
1. **ClipKaro and PostKaro installed** on the computer that runs OBS, with **PostKaro's accounts
   connected** (PostKaro's `docs/connect-accounts.md`). Logins don't move between computers or between
   Windows and Linux: connect them on the streaming computer.
2. **Your logo** in ClipKaro's `brand` folder (optional).
3. **OBS recording** (Settings → Output, Output Mode: **Advanced** → **Recording** tab):
   - Recording Path: a folder only for this, for example `C:\Users\<you>\Videos\live`.
   - Recording Format: **Hybrid MP4** (or MKV).
   - Video Encoder: **(Use stream encoder)**. Recording then costs no extra encoding.
   - **Automatically split file: on, Split by time: 10 minutes.**
   - Audio Track: tick **1 and 2**.
4. **Your mic on its own track** (Edit → Advanced Audio Properties): microphone on tracks **1 and 2**,
   the capture card's game sound on track **1** only. ClipKaro then writes down your voice alone, so game
   characters never get into your captions.
5. **Twitch** (for the audience hints):
   - Open [dev.twitch.tv/console](https://dev.twitch.tv/console) → Register Your Application:
     - name "ClipKaro";
     - OAuth Redirect URL `http://localhost`;
     - category "Application Integration";
     - client type "Confidential".
   - Copy its Client ID, make a New Secret, and tell Claude: "save my Twitch keys: <id> <secret>". By
     hand: `python run.py live keys --client-id <id> --client-secret <secret>`.
   - The keys are kept in your user folder, never in the ClipKaro folder.
   - In `settings.json`, set `"twitch_channel"` to your channel name and `"live_folder"` to the OBS
     recording folder.
   - Without keys, the chat is still read (it needs no login); only the viewer-clip notes are off.
6. **A test stream:**
   - Set `"live_post": "dry"` in settings.json.
   - Stream for 20-30 minutes and say "start live clipping test".
   - Clips are made, and PostKaro only shows what it *would* post.
   - Set it back to `"now"` for the real stream.

## Your stream settings (PS5 → capture card → OBS → YouTube, Twitch and Kick)
- **Multistream** with the free OBS plugin **"Multiple RTMP Outputs"** (obs-multi-rtmp). Every platform
  has its own bitrate limit:

  | Where | Bitrate | How |
  |---|---|---|
  | YouTube | 12,000 kbps | OBS's own stream (the recording shares this encoder) |
  | Kick | 8,000 kbps (Kick's maximum) | a plugin target with its own NVENC encoder |
  | Twitch | 6,000 kbps (the limit unless you are a partner) | a plugin target with its own NVENC encoder |

- **The encoders:**
  - NVENC (H.264), rate control CBR, keyframe interval 2 s, preset **P5**. Use P4 if OBS shows
    "encoding lag".
  - That is 3 encodes; NVIDIA's laptop cards allow 5 at once.
  - Simplest fallback: one shared 6,000 kbps encode for all three.
- **Upload speed:** 12 + 8 + 6 is about 27 Mbps, all the time. You need **about 40 Mbps of real upload or
  more**, on an **Ethernet cable**. Test it before going live.
- **Graphics memory** (4 GB on an RTX 3050):
  - OBS takes about 1-1.5 GB, and the Hinglish speech model about 2.3 GB.
  - ClipKaro uses the card only when at least 2.8 GB is free (`"live_vram_mb"`), otherwise the processor.
  - Turn off OBS's preview while streaming (right-click the preview) to save a little more.
- **In-game radio:** songs on GTA's car radio get copyright claims on YouTube and Instagram. Turn the
  radio off or down while streaming.

## Going live
1. Start OBS, start streaming (it records too), then in Claude Code (inside the ClipKaro folder) say:
   **"start live clipping gta6"**.
2. Claude starts the watcher and a 10-minute loop (`/loop 10m live clip gta6`). Keep Claude Code open;
   you can minimise it.
3. **To see how it goes:** `python run.py live status gta6`, or PostKaro's Queue page.
4. **When you end the stream,** tell Claude **"the stream is over"**. It finishes the last piece (about 2
   minutes after OBS stops writing), stops the watcher, and reports what was posted.

## Good to know
- **A moment that runs across two pieces:** each piece knows the end of the previous one only as context.
  A moment that starts in one piece and ends in the next is clipped from the piece where most of it is.
- **The Twitch notes are approximate.** Viewers watch a few seconds behind you (`"twitch_delay"`, 10 s),
  so their reactions come late. The notes only show Claude where to look; your words decide.
- **No review means trust.** A clip that fails the quality check is never posted, but nobody watches a
  clip before it goes out. Watch the first few on your phone, and delete one on the platform if you
  don't like it.
- **After the stream,** the recording pieces stay in the OBS folder. "Clip this" on them later still works
  for long-form highlights.

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
