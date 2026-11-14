# ClipKaro after v2.1: what's next, in order

ClipKaro v2.1 is out (November 2026; v2.0 came two days before it). This page lists what is still to do, in the order we plan to
do it, with a rough time for each item. We close the items one by one. When one is done, it moves to
**Done** with the date.

**Every item must be an upgrade to v1.1**, the first stable version: nothing v1.1 could do may be
lost or made harder. [since-v1.1.md](since-v1.1.md) checks every change against that.

**About the times**
- "Build" is focused working time with Claude: the code, the checks and the docs.
- "Your part" is your own time: testing, watching, choosing.
- Both are estimates. Items that need a blind test may take one more round.

Re-ordered on 2026-11-13 by the owner: the small fixes, "more clips" and the usage modes first; the
fresh install on Windows and macOS last; posting to X not planned for now. The small fixes (1) and
the three modes (3) were done the same day.

---

## Now

| # | What | Why | Build | Your part | Status |
|---|---|---|---|---|---|
| 3b | **Measure the three modes** with `/usage` (one long and one short video each), and try cheaper models (Sonnet or Haiku) for the helpers where a blind test shows no drop in quality. | Quick mode is built; its real saving isn't measured yet. Cheaper helpers would make standard lighter too. | 2-3 h | run `/usage` before and after each run, 30 min of blind pairs | To do: **start here** (needs you to run `/usage`) |

## Next: look more professional
Each item is blind-tested against the version before it, and it only stays if it wins.

| # | What | Why | Build | Your part | Status |
|---|---|---|---|---|---|
| 4 | **Sound effects by mood, from your own folder.** Folders (or file names) for each mood: attention, shock, fear/suspense, funny, hit, whoosh. Claude marks the moments in a clip that call for one (a reveal, a scare, a punchline), and the edit places the sound there, quietly under the voice. To add a sound: download it, put the mood word in its name (or drop it in that mood's folder), and it is used from then on. Today `assets/sfx/` already picks up whoosh, hit and click files by name, but the edit only plays 1-2 whooshes. | Sound grabs attention and sets the mood; you choose the sounds that fit your channel. | about 1 day | collect a few sounds you like, 20 min | **Done** (2026-11-13) |
| 5 | **Trim silences and filler words** (jump cuts). Pauses inside a clip get cut, and a small zoom change hides each cut. On in every clip. | Viewers leave during pauses. Tight clips keep people watching. | 1 day | blind test, 20 min | **Done** (2026-11-13); the owner approved it for every clip (2026-11-14) |
| 6 | **Hook title on screen.** A big 3-6 word line ("Pakistan ka PM banoge?") for the first 2-3 seconds. | It stops the scroll even with the sound off. | 4-6 h | blind test, 15 min | **Done** (2026-11-13), **off unless asked**: the owner didn't like it on every clip |
| 7 | **Captions clear of faces and app buttons.** Captions stay inside each app's safe zone, and in tight close-ups they move off the chin. | Captions under the like button or over a mouth hurt watch time. | 1 day | look at 5 clips | **Done** (2026-11-13) |
| 8 | **Automatic quality check after editing** (`run.py qa`). It checks every finished clip for Hindi letters left in Roman captions, captions too wide or under the app buttons, a cut inside a word, unsure words, black frames, sound too loud or too quiet, the length, and a flash of another shot at the very end. Claude fixes what fails before showing you. Plus automatic tests for captions, Roman Hinglish, cut points and post.json, with one tiny sample video run from start to end. | In the November cleanup, code found 3 clips with Hindi letters left and 51 clips with captions too close to the edge. The tests keep the v1.1 baseline safe. | 1.5-2 days | 15 min with the first report | **Done** (2026-11-13): `run.py qa`, `run.py test` (17 tests; the tiny sample video run is still to do) |
| 9 | **Cleaner transcripts.** Fixes for phrases repeated in a loop, one long "word" hiding several real words, and nonsense words during laughter. Plus the speech-model test, scored against texts you corrected. | Wrong words in captions look unprofessional. | 1.5-2 days | correct 5 short texts, 30-60 min | **Partly done** (2026-11-13): laughter, the noise word, loops and "…" (`run.py tidy`). Still to do: one long "word" hiding several, the speech-model test |
| 10 | **More editing styles.** 5-8 caption looks, emojis on strong words, and optional background music that gets quieter under the voice (you add your own licensed music). | Gaming, podcasts and education each look different. | 2-3 days | pick your favourites | **Done** (2026-11-13): 6 caption looks, emojis, music from your own folder (music on hold since 2026-11-14: it doesn't suit podcasts) |
| 11 | **Faster rendering.** The NVIDIA video encoder, zooms done by ffmpeg, and two clips at once when there is enough memory. | Today about 30 seconds per clip. | 1-1.5 days | none | **Done** (2026-11-13): NVIDIA encoder + 2 clips at once, 1.9x faster |

## Then: smarter

| # | What | Why | Build | Your part | Status |
|---|---|---|---|---|---|
| 12 | **Sound and picture cues for Claude.** Laughter, applause, a raised voice, and big movement in games are given to Claude as hints when it picks moments. | Some of the best moments live in a laugh or a reaction, not in the words. | 1.5-2 days | blind test | To do |
| 13 | **Gameplay: your voice apart from the game.** Separate the player's voice from the game's sound before transcribing. We research the best voice-separation model first. | Game characters' lines still mix into the transcript. | 1-2 days | one gameplay video | To do |
| 14 | **Learn from real views.** PostKaro reads back views and watch time, compares them with the clip scores, and tunes the critic for your channels. | The scores should learn what works for *your* viewers. | 2-3 days | needs about 50 posted clips with 2+ weeks of views | Waiting for posted clips (posting started 2026-11-12) |
| 15 | **Review studio.** A page where you move a clip's start or end, fix a caption word and re-render one clip, without typing commands (maybe inside PostKaro). | The last bit of quality is a human touch, and it should be easy. | 3-5 days | try it | To do |

## Last

| # | What | Why | Build | Your part | Status |
|---|---|---|---|---|---|
| 16 | **A fresh install on Windows and macOS**, checked from zero. | So far ClipKaro has only run on this Fedora laptop. | about 1 day | a Windows or Mac computer (yours or a friend's), 1 h | To do (not a priority now) |

## To match Opus Clip (not scheduled yet)
The [comparison with Opus Clip](roadmap-v2.md) (updated for v2.1) shows where it is still ahead. Items
5, 6, 7 and 10 above close most of the polish gap (silence trimming, a hook title, safe zones, caption
looks and music), 12 adds picture cues, 14 is a score that learns from real views, and 15 is our
answer to its editor. Not on the list yet:

| What | Opus Clip has | Rough size |
|---|---|---|
| **The side-by-side test**: the same English and gaming videos through Opus Clip and ClipKaro, rated blind | the reason to trust any of this | 1 day, plus a few people to rate |
| **B-roll**: short stock clips or pictures over the speaker where the words name something | AI B-roll (stock and generated) | 2-3 days |
| **Brand templates**: your logo, an intro and an outro on every clip | brand templates | 1 day |
| **Following people who move**, and objects | ReframeAnything | 1-2 weeks |
| **Three or more people**: panels, picture-in-picture for remote guests | layouts in Klap and Vizard | 1 week |
| **TikTok and LinkedIn in PostKaro** | a scheduler for six platforms | 1-2 days each, depending on their APIs |
| **Export to Premiere Pro** (XML), for creators who finish by hand | XML export | 1 day |

## Small extras (any time)
- **Re-cut the MCU and gamer videos with v2.** Their finished clips are v1.1 picks with v2 captions,
  and a fresh download is needed. About 1 hour each.
- **Per-platform texts for the 56 older clips.** These clips have one caption each; this adds a
  YouTube title and separate Instagram and Facebook texts. About 30 minutes.
- **Hear the older gameplay videos again** (GTA episode 2, Black Myth Wukong, the gamer video) with
  the improved check for game voices (2026-11-12), and re-render the clips it changes. About 5
  minutes per video, plus the re-render.
- **The first full "clip this video" run with the new defaults** (the deep-clip question, live
  stream detection, the clip range). The pieces were tested one by one; your next stream is the
  full test.

## Done
| What | Done |
|---|---|
| **The critic judges craft, never the topic.** Politics, religion, rude jokes and controversial views are judged like any other clip. | 2026-11-12 |
| **More clips from long videos.** 3-8 for short videos as in v1.1, up to about one per 7 minutes for long ones, at most `max_clips`; "at least / at most N" always wins. Built together with live streams and gameplay found by themselves (break screens left out) and one deep-clip question for long videos. | 2026-11-12 (the range fixed on 2026-11-13) |
| **First real posts with PostKaro**, on Instagram and YouTube, scheduled. Some Instagram posts got a 400 error and worked on retry; that is being fixed in a PostKaro session. | 2026-11-12 |
| **PostKaro 1.0: the new look** (made with Hallmark), approved by the owner. | 2026-11-13 |
| **Game characters' English caught more often**, never a translation of the streamer's Hinglish; listening again works on only the few seconds it needs. | 2026-11-12 |
| **Every change since v1.1 checked** ([since-v1.1.md](since-v1.1.md)). | 2026-11-13 |
| **Small fixes** (item 1): `run.py fixword` fixes a caption word everywhere; a fast camera cut only follows the new face instead of zooming (anime: 48 zoom changes in 68 s, now 28); repaired clips keep their place and their id; editing again works without the original video. | 2026-11-13 |
| **More clips later** (item 2, "clips 9-12 too"): the good ideas that weren't cut stay saved (`more.txt`), and "3 more clips from that video" makes them without reading again (`run.py more`). | 2026-11-13 |
| **Three modes** (item 3): standard by default, deep when asked or on yes to the question for long videos, quick only when asked (one read by Claude, no helpers, no critic). | 2026-11-13 (measuring with `/usage` is item 3b) |

## Not planned for now
- **Posting to X (Twitter).** Left out by the owner for now.
- **More Indian languages** (Tamil, Bengali, Marathi, Telugu…). ClipKaro supports Hindi, Hinglish
  and English only, on purpose. [adding-a-language.md](adding-a-language.md) explains how, for later.

---

**Now (item 3b): a few hours, with your `/usage` runs. Next and then (items 4-15): about 3-4 weeks.**

The comparison with Opus Clip and others, and the reasons behind many of these items, are in
[roadmap-v2.md](roadmap-v2.md).
