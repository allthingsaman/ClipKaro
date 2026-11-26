# Be a smart user: ClipKaro

How to get the best clips **and** use as little of your Claude plan as possible. What to type for each kind of
video, which mode to pick, and the habits that save time, usage and disk space.

ClipKaro's own programs (writing down the words, cutting, editing) run on your computer and use none of your
Claude plan. **Claude's reading and judging is what costs usage.** So the smart moves are: let Claude read only
what it needs, and judge only as carefully as the video deserves.

---

## 1. Pick the right mode

| Mode | How you ask | What you get | Usage for a 30-min video |
|---|---|---|---|
| ⚡ **Quick** (basic) | "quick clip this: (link)" or "basic mode" | Claude picks alone, once. No second opinion, no caption check. | about 0.3 million tokens |
| ⭐ **Standard** (default) | "clip this: (link)" | Plus a blind critic scores every idea 3 times, weak starts and ends are repaired, captions are checked for misheard words. | about 0.6 million |
| 🧵 **Deep** (advanced) | "deep clip this: (link)" or "advanced mode" | Plus clips that join moments far apart (a question at minute 3 and its answer at minute 41), checked by 3 honesty judges. | about 1.1 million |

(Measured on real runs; see [docs/requirements.md](docs/requirements.md#how-much-claude-usage).)

### Which mode for which video

| Your video | Best mode | Why |
|---|---|---|
| **Under 10 minutes** (a talk, a reel, one topic) | Quick, or Standard if it's important | Few moments to choose from: a second opinion adds little. **Never deep**: there's nothing far apart to join. |
| **10-21 minutes** | Standard | The critic finds the strongest 3-5. Deep isn't offered: too short for a story spread across it. |
| **21-40 minutes** | Standard | ClipKaro asks once about deep clips: say **no** unless you know a story comes back later in the video. |
| **A podcast or interview, 40 minutes or more** | Standard, or **Deep** when a question and its answer are far apart | This is what deep clips are made for. Often none is good enough, and Claude says so honestly. |
| **Gameplay or a live stream** | Standard | The jokes and reactions are local (a fail and the laugh right after it). Deep only for long streams with callbacks ("like a boss" ... then the fail 20 minutes later). |
| **Many videos in one day / you're near your plan's limit** | Quick | About half of Standard. Read the captions yourself before posting: Quick doesn't check them. |
| **A test, or "is this video even worth it?"** | Quick + "show me the moments before you cut them" | You see the ideas first and stop if nothing is good. |
| **Someone else's video** (you clip a channel you like) | Standard | Fine, but PostKaro will warn about copyright: your choice. |

**Make a mode your default:** "add to my preferences: always use quick mode" (or standard / deep). To never be
asked about deep clips: settings.json `"deep_clips": "never"` (or `"always"`).

---

## 2. What to write: combinations that work

Put everything in **one message**: it saves a round trip (and usage). Any language: English, Hindi, Hinglish.

| You want | Write | Benefit |
|---|---|---|
| The best few only | "clip this: (link), only the 3 best" / "at most 5 clips" | Fewer clips to cut, edit and write posting texts for: faster, lighter. |
| Many clips (a long stream) | "at least 10 clips" / "no limit" | Every good moment. "No limit" on a 4-hour stream gave 160 clips: about the work of 8-10 normal videos. |
| Only one topic | "clip this, only the parts about money" | Claude ignores the rest. |
| Only part of the video | "only the first hour" | Less to read: less usage. |
| Short clips | "clips under 30 seconds" | Tighter clips (shorter usually wins, unless the extra seconds are funny or needed). |
| To see the picks before cutting | "show me the moments before you cut them" | You drop the weak ones before any rendering. |
| Raw cuts only | "don't edit them, just cut" | No captions or zooms: fastest. |
| No extras | "no sound effects" · "no zooms" · "no emojis" · "no captions" | As you like it. |
| A caption look | "box captions" · "karaoke captions" · "minimal captions" · "bold captions" · "comic captions" | Your channel's style (classic otherwise). |
| Caption size or place | "bigger captions" · "captions lower" · "not in capital letters" | |
| Your colour | "use #00E5FF as the caption colour" | Your brand on every clip. |
| A title on screen | "hook title" | A big 3-6 word title for the first seconds. Only when you ask. |
| Pictures of what's named | "add b-roll" | A film's trailer piece or a picture covers the speaker for 2-3 s. Costs a little more; a trailer piece may get a copyright claim. |
| More later | "3 more clips from the Khan Sir video" | **Cheap**: the saved ideas are used; the video is not read again. |
| No credit / no logo / no outro | "no credit" · "no logo" · "no outro" | |
| Hindi letters in captions | "Hindi captions in Hindi letters" | Devanagari instead of Roman Hinglish. |
| A fix after you watched | "clip 2 starts too early" · "in clip 4, 'bow' should be 'boat'" | Only that clip is made again. |

**Examples of one good message:**
- *"clip this: (link), at most 5, under 45 seconds, box captions, no emojis"*
- *"quick clip this: (path to my video), only the parts about the trailer"*
- *"deep clip this: (link to a 1-hour podcast), at least 8 clips, hook title"*
- *"clip this stream: (path), no limit, show me the moments before you cut them"*

**Things you never need to say:** that it's gameplay, a stream, a podcast with two people, or Hinglish.
ClipKaro sees that by itself (webcam layout, break screens left out, split screens, Roman Hinglish captions,
careful listening on noisy Hindi streams with an NVIDIA card).

---

## 3. Save your Claude plan: the habits

1. **Pick the lightest mode that fits** (section 1). Quick for short or many videos.
2. **One message with all your wishes** instead of several follow-ups.
3. **Say a number** ("at most 5") when you only want a few: fewer posting texts and edits.
4. **"Show me the moments first"** on videos you're unsure about: no wasted cutting.
5. **"3 more clips from ..." later** instead of clipping the same video again.
6. **A new chat for each video.** A long chat carries everything said before; a fresh one starts light.
7. **Put your standing wishes in "My preferences"** (end of CLAUDE.md): "add to my preferences: clips 30-45
   seconds long". Then you never type them again, and Claude never asks.
8. **Small fixes in PostKaro's Studio, not in Claude:** a start word, a caption word, framing, an emoji: the Studio
   makes the clip again with no Claude usage at all.
9. **On a small plan:** Google Antigravity's free plan is usually enough for about one video per session.

**Gameplay and streams cost a little extra in every mode** (about 0.15 million tokens per 30 minutes: the word check
of every clip and the frame sheets). That's what keeps captions right on noisy Hindi streams: worth it.

---

## 4. Live clipping (while you stream)

| Say | What happens |
|---|---|
| "start live clipping gta6" | A watcher on OBS's 10-minute recording pieces; every 10 minutes Claude clips the finished piece and PostKaro posts the clips everywhere at once. |
| "the stream is over" | The last piece is clipped and it stops. |

Smart: test first with settings.json `"live_post": "dry"` (it only shows what it would post). Live clipping uses
your plan all stream long: on a small plan, clip the recording afterwards in Quick mode instead.

---

## 5. Your computer: time, memory, disk

- **One video at a time.** Two at once can run the laptop out of memory (it happened). Close heavy apps (many Chrome
  tabs, games) while it works.
- **An NVIDIA card** makes writing down the words a few minutes instead of hours.
- **Disk:** each project keeps its files in `output/<project>/`. Once a video's posts are live, the downloaded video
  and `clips/` can go (a later "3 more clips" or a Studio fix downloads a linked video again). Keep `edited/` until
  every post is live: PostKaro uploads from there. A video file of your own is never copied: leave it where it was.

---

## 6. With the other two apps

- **PostKaro** posts your clips (YouTube Shorts, Instagram Reels, Facebook Reels): click the **"Post them"** link
  ClipKaro gives at the end. Its own guide: `BE-SMART-USER.md` in the PostKaro folder.
- **EditKaro** edits your own long videos. After you post one, ClipKaro makes its **Instagram teaser** from the
  finished video (EditKaro asks Claude to do it), and you can clip the finished video into Shorts too:
  "clip this: (path to the finished video)".

More: every phrase in [docs/usage.md](docs/usage.md), step by step in [docs/user-guide.md](docs/user-guide.md).
