# ClipKaro after v2.8: what's next, in order

ClipKaro v2.8 (quick wins) is the newest version (2026-11-23), the first step towards v3.0; v2.9 ("boast, then
fail" clips and compilations) is next. **The plan for v3.0, approved by the owner on 2026-11-23, is
[plan-v3.0.md](plan-v3.0.md)**: three phases, released step by step (v2.8, v2.9 …) and then bundled as v3.0. This page lists what is
still to do, in the order we plan to do it, with a rough time for each item. We close the items one
by one. When one is done, it moves to **Done** with the date.

**Every item must be an upgrade to v1.1**, the first stable version: nothing v1.1 could do may be
lost or made harder. [since-v1.1.md](since-v1.1.md) checks every change against that.

**About the times**
- "Build" is focused working time with Claude: the code, the checks and the docs.
- "Your part" is your own time: testing, watching, choosing.
- Both are estimates. Items that need a blind test may take one more round.

**How we got here.**
- v2.2 (2026-11-14): the professional look (items 4-8, 10 and 11).
- v2.3 (2026-11-16): cleaner captions and smarter picking: a Hinglish speech model, skipped words heard
  again, hints from the sound and picture, game characters told apart from the streamer (and no
  captions for them), Claude's caption check, no flash at a clip's end, and a README that shows it all.
  The owner reviewed every part on the test videos before it went in.
- v2.4 (2026-11-17): your brand on every clip (your logo, your outro, "© Channel" credit to the source,
  any corner), action without talking noted in gameplay, a caption check that spells names and numbers
  right, and a README that says which AI helper you need and how ClipKaro compares with Opus Clip inside
  Claude.
- v2.5 (2026-11-17): ClipKaro and PostKaro checked for Windows and Mac (item 16). Everything planned
  before the major update (v3.0) is done.
- v2.6 (2026-11-17): live clipping for the GTA 6 launch.
- v2.7 (2026-11-20): gameplay with friends done by itself: frame sheets, careful listening, friends'
  captions, starter sound effects on time, private details kept out, "no limit"; never censored, with stars
  in written words. Planned with the owner in [plan-v2.7-just-paste-a-link.md](plan-v2.7-just-paste-a-link.md).
- v2.7.1 (2026-11-21): the action stays in (pauses with something happening on screen), real usage numbers, and
  the fixes of the release review.
- v2.8 (2026-11-23, quick wins): only part of a video, smarter action pauses, a landscape copy, game subtitles
  for English streamers, a DaVinci Resolve timeline, "word check done", whole reaction words.

---

## Waiting on you

| # | What | Why | Build | Your part | Status |
|---|---|---|---|---|---|
| 3b | **On hold (the owner, 2026-11-23): Try cheaper models** (Sonnet or Haiku) for the helpers where a blind test shows no drop in quality. Real usage per mode is now measured from Claude Code's own records (v2.7.1, [requirements.md](requirements.md#how-much-claude-usage)): quick about half of standard; the helpers are most of a long video's usage (critic, part readers, word check). | Cheaper helpers would make standard and gameplay lighter for everyone. | 2-3 h | 30 min of blind pairs; `/usage` before and after shows the share of your own plan | Waiting for your blind pairs |
| 13b | ~~**Your microphone on its own track.**~~ **Closed (2026-11-23):** it works only for your own OBS recordings; Twitch and YouTube mix every track into one, so their downloads can't separate the mic (checked by the owner on Windows). | Record a stream in OBS with the mic on its own audio track (Settings > Output > Recording: tracks 1 and 2; Edit > Advanced Audio Properties: mic on 1 and 2, desktop audio on 1), then clip that file. | The cleanest way to keep game voices out of the words: ClipKaro then writes down your voice alone. | none, it's built | one stream recorded that way | When you can (not every stream has to be) |
| 22 | ~~**A first real install on a Windows PC or a Mac.**~~ **Done (2026-11-21):** the owner installed both apps on Windows for his video guide. | v2.5 checked both by reading the code and the steps and by tests on this laptop; nobody has run it on one yet. | The AI helper sorts out most surprises, but a real run finds what reading can't. | none | 1 h on a Windows or Mac computer (yours or a friend's): "install this repo", then one short video | When one is at hand |
| 19 | ~~**The first full "clip this video" run with everything new**~~ **Done (2026-11-21/22):** two fresh GTA 6 streams clipped with v2.7. | (the Hinglish model, hints, game captions, caption check, the deep-clip question, live stream detection). | The pieces were tested one by one; a fresh stream is the full test. | none | your next stream | Waiting for your next stream |

## Ideas
| # | What | Status |
|---|---|---|
| P2 | **Action without talking gets its own line** ("(no talking) [big action on screen ~6 s] [explosion]"), so silent gameplay moments aren't missed. | **Done** (v2.4, 2026-11-17) |
| P3 | **More caption-check rules**: names spelled right, numbers as digits where they are amounts, years or scores. | **Done** (v2.4, 2026-11-17) |
| P4 | **YouTube's own captions as a second opinion.** | **On hold, for the owner to decide** (research, 2026-11-17): a study of 8,740 hours of Indian speakers found YouTube's captions worse than even a small Whisper model, with errors in the same places (so it would mostly repeat our mistakes), no published test exists for Hinglish (guides say it garbles fast Hindi-English switching), and a wrong second opinion could lead the caption check astray. |

## Next phase
The major update, v3.0, planned in detail in [plan-v3.0.md](plan-v3.0.md). Phase 1: v2.8 quick wins are out
(2026-11-23); v2.9 ("boast, then fail" clips and compilations) is next. Item J's other two clues (voices in
bursts, studio vs mic sound) wait for an English test stream.

## Major update (v3.0), later
Big new features for a later major version, once everything essential for clipping is done.

| # | What | Why | Rough size |
|---|---|---|---|
| 15 | **Review studio.** A page where you move a clip's start or end, fix a caption word and re-render one clip, without typing commands (maybe inside PostKaro). | The last bit of quality is a human touch, and it should be easy. | 3-5 days |
| 14 | **Learn from real views.** PostKaro reads back views and watch time, compares them with the clip scores, and tunes the critic for your channels. | The scores should learn what works for *your* viewers. Needs about 50 posted clips with 2+ weeks of views. | 2-3 days |
| | **B-roll**: short stock clips or pictures over the speaker where the words name something | Opus Clip has AI B-roll | 2-3 days |
| | **Following people who move**, and objects | Opus Clip's ReframeAnything | 1-2 weeks |
| | **Three or more people**: panels, picture-in-picture for remote guests | Klap and Vizard have layouts | 1 week |

## Later, if we need it
Smaller items. We review them when the next phase is done and decide which are worth building.

| What | Why | Rough size |
|---|---|---|
| **No game-character captions for English-speaking streamers**: the game's subtitles are read since v2.8 (item J); voices in bursts and studio vs mic sound wait for an English test stream | v2.3 tells game lines apart by language; an English streamer needs other clues (the game's subtitles, voices in bursts, studio vs mic sound) | 2-3 days |
| **A facial-reaction hint** (a listener's silent laugh or shock): now in the v3.0 plan (item I) | the one moment sound can't catch | 1-2 days |
| **More pairs for the hints test** (on a podcast and a second stream) | the first test was 2 pairs, both won by the hints | your time, 20 min a video |
| ~~Export to Premiere Pro~~ → **a DaVinci Resolve timeline instead** (free): done in v2.8 ("export to resolve") | Premiere is paid; Resolve and Kdenlive are free | 1 day |

The [comparison with Opus Clip](roadmap-v2.md) explains where it is still ahead.

## On hold
- **TikTok and LinkedIn in PostKaro**: removed from the plan by the owner (2026-11-23).
- **The side-by-side test against Opus Clip**: the same English and gaming videos through both, rated
  blind. It needs an Opus Clip subscription, which the owner doesn't have right now.
- **Background music** from your own `music` folder: built, but it doesn't suit podcasts
  (`"music": true` turns it on).
- **Posting to X (Twitter)**: left out by the owner for now.
- **YouTube's own captions as a second opinion** (idea P4, above).

## Not planned for now
- **More Indian languages** (Tamil, Bengali, Marathi, Telugu…). ClipKaro supports Hindi, Hinglish
  and English only, on purpose. [adding-a-language.md](adding-a-language.md) explains how, for later.

## Small extras (any time, only if you want them)
- **2 more clips from the MCU video** (the critic's next ideas): "3 more clips from that video".
- **Delete the test folders** `output/_feature-examples/` and `output/_hints_ab/` once you don't need them.

## Done
| What | Done |
|---|---|
| **Gameplay with friends, done by itself** (v2.7): frame sheets (the readers see a frame every 10 s, close-ups where they point, clips that start at the event), careful listening for noisy Hindi / Hinglish streams, friends' captions and friends counted like the streamer, overlapping clips and "no limit" for streams, starter sound effects that start on their moment (item 4b), private details kept out, the Twitch credit and two-person webcams. Tested on a 4-hour GTA 6 stream with three friends. | 2026-11-20 (v2.7) |
| **Live clipping** (v2.6, for the GTA 6 launch): clips posted while you stream, from OBS's 10-minute pieces, with Twitch chat and viewer clips as hints and auto-posting through PostKaro. First real use: the GTA 6 launch stream. | 2026-11-17 (v2.6) |
| **Install check for Windows and macOS** (item 16), for ClipKaro and PostKaro: the Mac steps fixed (Homebrew's Python 3.15 and its caption-less ffmpeg), Hindi folder names on Windows, a Python check in setup, PostKaro's setup for every system. Checked by reading and tests; a real run is item 22. | 2026-11-17 (v2.5) |
| **v2.4**: your brand on every clip (items 20 and 21): your logo and a 3-5 s outro from the `brand` folder, and "© Channel name" on clips from a YouTube link, right in the corners at 70 % opacity, any corner by setting; action without talking gets its own line (P2); the caption check spells names and numbers right (P3). | 2026-11-17 |
| **v2.3**: no captions for game characters (gameplay, Hindi/Hinglish streamer) and Claude's caption check (standard and deep), on top of everything below. | 2026-11-16 |
| **The hints' first blind test** (item 12): on a GTA stream, picks with and without hints matched 6 of 8; of the 2 that differed, the owner preferred the hints version both times. | 2026-11-16 |
| **A Hinglish speech model** (item 9b): Whisper-Hindi2Hinglish-Prime for Hindi and Hinglish videos with an NVIDIA card. On public test sets 21 % of Hinglish conversation wrong against turbo's 50 %, 19 % of everyday Hindi against 34 %; about 40 % fewer tokens for Claude; about 1.3x the transcription time. English stays on turbo. | 2026-11-15 |
| **Skipped words heard again** (item 9) on new videos and, with `relisten --stretched`, on all 13 test videos (10 clips re-made; hidden and hand-fixed words never touched). Plus the speech-model test on public test sets (`asr-bench public`). | 2026-11-15 |
| **Hints from the sound and picture** (item 12): `[voice raised]`, `[shouting]`, game sound bursts, `[big action on screen]` next to the words Claude reads. | 2026-11-14 |
| **Game characters told apart from the streamer** (item 13): `(other voice)` in what Claude reads; a recording with the mic on its own track is written down from the mic alone. Research showed that separating a voice from the mix makes speech recognition worse, so it isn't done. | 2026-11-14 |
| **No flash of the next shot at a clip's end** (item 17): 12 test clips re-made. | 2026-11-14 |
| **Tests from start to end** (item 18): `run.py test --full`. | 2026-11-14 |
| **A README that shows it**: the real video next to the clip ClipKaro made (deep clip, two people, gameplay, caption placement). | 2026-11-14 |
| **Instagram and Facebook texts for the 64 older test clips.** | 2026-11-14 |
| **v2.2 released**, after the owner watched all 106 re-edited test clips and chose the defaults: pauses cut, captions off faces and the apps' buttons, no captions on made-up words, emojis and the sound-peak limit in every clip; the hook title and caption looks only when named; music on hold. | 2026-11-14 |
| **Sound effects by mood, from your own folder** (item 4). | 2026-11-13 (not yet tried with real sounds: item 4b) |
| **Pauses cut out** (item 5), **hook title on screen** only when asked (item 6), **captions clear of faces and app buttons** (item 7), **automatic quality check** (item 8), **six caption looks and emojis** (item 10), **faster rendering** (item 11). | 2026-11-13 |
| **The critic judges craft, never the topic.** | 2026-11-12 |
| **More clips from long videos**, live streams and gameplay found by themselves, one deep-clip question for long videos. | 2026-11-12 |
| **First real posts with PostKaro**, and **PostKaro 1.0: the new look**. | 2026-11-12 / 13 |
| **Game characters' English caught more often**, never a translation of the streamer's Hinglish. | 2026-11-12 |
| **Every change since v1.1 checked** ([since-v1.1.md](since-v1.1.md)). | 2026-11-13 |
| **Small fixes** (item 1), **more clips later** (item 2), **three modes** (item 3). | 2026-11-13 |

---

**Waiting on you: item 4b (and 3b, on hold). Next: v3.0, step by step ([plan-v3.0.md](plan-v3.0.md)).**

The comparison with Opus Clip and others, and the reasons behind many of these items, are in
[roadmap-v2.md](roadmap-v2.md).
