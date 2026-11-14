# ClipKaro after v2.2: what's next, in order

ClipKaro v2.2 is out (2026-11-14). v2.1 came the day before it, and v2.0 on 2026-11-11. This page
lists what is still to do, in the order we plan to do it, with a rough time for each item. We close
the items one by one. When one is done, it moves to **Done** with the date.

**Every item must be an upgrade to v1.1**, the first stable version: nothing v1.1 could do may be
lost or made harder. [since-v1.1.md](since-v1.1.md) checks every change against that.

**About the times**
- "Build" is focused working time with Claude: the code, the checks and the docs.
- "Your part" is your own time: testing, watching, choosing.
- Both are estimates. Items that need a blind test may take one more round.

**How we got here.** On 2026-11-13 the owner put the small fixes, "more clips" and the usage modes
first, and the fresh install on Windows and macOS last. Posting to X is not planned for now.
- The small fixes (item 1) and the three modes (item 3) were done the same day.
- The professional look (items 4-8, 10 and 11) was built on 2026-11-13 as well.
- It was released as **v2.2** on 2026-11-14, after the owner watched all 106 test clips and chose
  what is on by default.

---

## Now

| # | What | Why | Build | Your part | Status |
|---|---|---|---|---|---|
| 3b | **Measure the three modes** with `/usage` (one long and one short video each), and try cheaper models (Sonnet or Haiku) for the helpers where a blind test shows no drop in quality. | Quick mode is built; its real saving isn't measured yet. Cheaper helpers would make standard lighter too. | 2-3 h | run `/usage` before and after each run, 30 min of blind pairs | To do: **start here** (needs you to run `/usage`) |

## Waiting for your choice

| # | What | Why | Build | Your part | Status |
|---|---|---|---|---|---|
| 4b | **Try sound effects by mood with real sounds.** The feature is built (item 4), but the `sounds` folders are still empty, so no clip has used it yet. You add 2-3 free sounds (a boom, a ding, a "fail" sound); Claude makes 2-3 example clips with them. | So you decide to keep the feature, or remove it, from clips you have watched. | 30 min | add the sounds, watch 3 clips, 20 min | Waiting for your sounds |
| 10b | **Background music**, from your own `music` folder (built in item 10). | It doesn't suit podcasts. It may suit gaming or motivation clips later. | none, it's built | decide when to try it again | **On hold** since 2026-11-14 (`"music": true` turns it on) |

## Next: cleaner still

| # | What | Why | Build | Your part | Status |
|---|---|---|---|---|---|
| 9 | **Cleaner transcripts: the rest.** Sometimes one long "word" hides several real words (a Khan Sir clip lost "ki ye America ki chaal hai"): find it and transcribe that bit again. Plus the speech-model test, scored against texts you corrected. | Missing or wrong words in captions look unprofessional. | 1 day | correct 5 short texts, 30-60 min | **Done on v2.3-dev** (2026-11-14): stretched words heard again (`fetch`, `relisten --stretched`); the speech-model test on two public test sets with checked texts (`asr-bench public`). Still yours: correcting the 4 draft texts of your own videos |
| 17 | **No flash of the next shot at a clip's end.** `run.py qa` finds it: 5 of the 106 test clips (Dr Vikas 1, Market 3 and 7, Khan Sir 13 and 16). `cut` should end such a clip a few frames earlier by itself. | A one-frame flash looks like a mistake. | 2-3 h | none | **Done on v2.3-dev** (2026-11-14): the wider qa check found 12; all 12 re-made |
| 18 | **One tiny sample video run from start to end** inside `run.py test`. This is the part of item 8 still to do. | It catches a break anywhere in the chain before you see it. | 2-3 h | none | **Done on v2.3-dev** (2026-11-14): `run.py test --full` |

## Then: smarter

| # | What | Why | Build | Your part | Status |
|---|---|---|---|---|---|
| 12 | **Sound and picture cues for Claude.** Laughter, applause, a raised voice, and big movement in games are given to Claude as hints when it picks moments. | Some of the best moments live in a laugh or a reaction, not in the words. | 1.5-2 days | blind test | **Built on v2.3-dev** (2026-11-14): `[voice raised]`, `[shouting]`, game sound bursts, `[big action on screen]` next to the words (`run.py hints`). Still to do: the blind test |
| 13 | **Gameplay: your voice apart from the game.** Separate the player's voice from the game's sound before transcribing. We research the best voice-separation model first. | Game characters' lines still mix into the transcript. | 1-2 days | one gameplay video | **Built on v2.3-dev** (2026-11-14): research found that separating a voice from the mix makes speech recognition worse, so the voices are told apart instead: `(other voice)` on game characters' lines; a recording with the microphone on its own track is written down from the microphone alone. Still yours: a stream recorded that way, to try it |
| 14 | **Learn from real views.** PostKaro reads back views and watch time, compares them with the clip scores, and tunes the critic for your channels. | The scores should learn what works for *your* viewers. | 2-3 days | needs about 50 posted clips with 2+ weeks of views | Waiting for posted clips (posting started 2026-11-12) |
| 15 | **Review studio.** A page where you move a clip's start or end, fix a caption word and re-render one clip, without typing commands (maybe inside PostKaro). | The last bit of quality is a human touch, and it should be easy. | 3-5 days | try it | To do |

## Last

| # | What | Why | Build | Your part | Status |
|---|---|---|---|---|---|
| 16 | **A fresh install on Windows and macOS**, checked from zero. | So far ClipKaro has only run on this Fedora laptop. | about 1 day | a Windows or Mac computer (yours or a friend's), 1 h | To do (not a priority now) |

## To match Opus Clip (not scheduled yet)
The [comparison with Opus Clip](roadmap-v2.md) (updated for v2.2) shows where it is still ahead.
v2.2 closed most of the polish gap: pauses cut, a hook title when asked, captions clear of the apps'
buttons, six caption looks and emojis. Item 12 adds picture cues, 14 is a score that learns from
real views, and 15 is our answer to its editor. Not on the list yet:

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
- **Re-cut the MCU and gamer videos with v2.** Checked 2026-11-14: their clips already are v2 picks
  (MCU 3 of 4, the gamer video 7 of 8 match the critic's ranking). Left: "2 more clips from the MCU
  video" (the critic's next ideas), only if you want them.
- ~~**Per-platform texts for the older clips.**~~ Done 2026-11-14: all 64 have Instagram and
  Facebook texts.
- **Hear the older gameplay videos again** (GTA episode 2, Black Myth Wukong, the gamer video) with
  the improved check for game voices (2026-11-12), and re-render the clips it changes. About 5
  minutes per video, plus the re-render.
- **The first full "clip this video" run with the new defaults** (the deep-clip question, live
  stream detection, the clip range, v2.2's edit). The pieces were tested one by one; your next
  stream is the full test.

## Done
| What | Done |
|---|---|
| **v2.2 released**, after the owner watched all 106 re-edited test clips and chose the defaults: pauses cut, captions off faces and the apps' buttons, no captions on made-up words, emojis and the sound-peak limit in every clip; the hook title and caption looks only when named; music on hold. | 2026-11-14 |
| **Sound effects by mood, from your own folder** (item 4). Claude marks the moments that call for one, and the sound's loudest point lands on the word, under the voice. | 2026-11-13 (not yet tried with real sounds: item 4b) |
| **Pauses cut out** (item 5). Pauses of half a second or more are shortened to 0.2 s and "um" / "uh" are cut, never across a laugh. | 2026-11-13 (on in every clip since 2026-11-14) |
| **Hook title on screen** (item 6), only when you say "hook title". | 2026-11-13 (off unless asked since 2026-11-14) |
| **Captions clear of faces and app buttons** (item 7). | 2026-11-13 |
| **Automatic quality check** (item 8): `run.py qa` checks every finished clip, and `run.py test` runs 23 tests. | 2026-11-13 (the sample video run is item 18) |
| **No made-up words in the captions** (part of item 9): laughter, the noise word "झाल", loops and "…". | 2026-11-13 |
| **More editing styles** (item 10): six caption looks and emojis on strong words. Background music is built but on hold (item 10b). | 2026-11-13 |
| **Faster rendering** (item 11): the NVIDIA encoder and two clips at once, 1.9x faster. | 2026-11-13 |
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

**Now (item 3b): a few hours, with your `/usage` runs. Next and then (items 9, 12-15, 17 and 18):
about 2-3 weeks.**

The comparison with Opus Clip and others, and the reasons behind many of these items, are in
[roadmap-v2.md](roadmap-v2.md).
