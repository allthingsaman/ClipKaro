# ClipKaro after v2.0: what's next, in order

ClipKaro v2.0 is out (November 2026). This page lists what is still to do, in the order we plan to
do it, with a rough time for each item. We close the items one by one. When one is done, its
status changes to **Done** with the date.

**Every item must be an upgrade to v1.1**, the first stable version: nothing v1.1 could do may be
lost or made harder. [since-v1.1.md](since-v1.1.md) checks every change against that.

The goal is **production ready**: someone else can install ClipKaro and PostKaro, use them on a
normal Claude plan, and post good clips without help. That is reached at the end of step 2.

**About the times**
- "Build" is focused working time with Claude: the code, the checks and the docs.
- "Your part" is your own time: testing, watching, choosing.
- Both are estimates. Items that need a blind test may take one more round.

---

## Step 1. Ship v2 (about 2 days)
Goal: the clips that are waiting get posted, and every new clip is checked by code before you see it.

| # | What | Why | Build | Your part | Status |
|---|---|---|---|---|---|
| 1 | **The critic judges craft, never the topic.** It looks at how a clip starts, whether it makes sense alone, how it ends and what could be cut. Politics, religion, rude jokes and controversial views are judged like any other clip. | You review every clip yourself, so no subject should hold a clip back. | 15 min | none | **Done** (2026-11-12) |
| 2 | **First real posts with PostKaro.** First an unlisted YouTube Short, then one Instagram Reel and one Facebook Reel, then the waiting clips. Anything that breaks gets fixed. | PostKaro has only been tested with fake platforms so far. | 0-3 h (only if something breaks) | 30-45 min | To do: **start here** |
| 3 | **More clips from long videos.** The fixed "3-8 clips" grows with the length of the video: still 3-8 for short videos, up to about one per 7 minutes of real video for long ones. A `max_clips` setting sets the limit. "At least N" / "at most N" always wins. Built together with: live streams and gameplay found by themselves (break screens left out), and one question about deep clips for videos over 21 minutes. Still open: good ideas that weren't cut stay listed, so you can ask for "clips 9-12 too". | Today a 2-hour podcast with 25 good moments still gives at most 8 clips. You post almost any decent clip, and more clips mean more chances. | 2-3 h | one test video, 20 min | **Done** (2026-11-12), except the "clips 9-12" list |
| 4 | **Automatic quality check after editing** (`run.py qa`). It checks every finished clip for Hindi letters left in Roman captions, captions too wide or under the app buttons, a cut inside a word, unsure words, black frames, sound too loud or too quiet, the length, and a flash of another shot at the very end. Claude fixes what fails before showing you. Roman spellings are checked again after every re-cut. | In the November cleanup, code found 3 clips with Hindi letters left and 51 clips with captions too close to the edge. Nobody should have to find those by eye. | about 1 day | 15 min with the first report | To do |

## Step 2. Production ready (about 4-6 days)
Goal: it installs on any computer, runs on a normal Claude plan, and posts to all three platforms.
At the end: **ClipKaro v2.1 and PostKaro 1.0**.

| # | What | Why | Build | Your part | Status |
|---|---|---|---|---|---|
| 5 | **Claude usage modes.** Three modes: *quick* (one read, no critic, like v1.1), *standard* (v2, the default) and *deep* (deep clips). The helpers use a cheaper model (Sonnet or Haiku) wherever a blind test shows no drop in quality. Each mode is measured with `/usage` on one long and one short video. | v2 with deep clips uses about 10x the Claude usage of v1.1 on a long podcast. That is too much for creators on the Pro plan. | 1-1.5 days | 30 min of blind pairs | To do |
| 6 | **Tests and a fresh install.** Automatic tests for captions, Roman Hinglish, cut points and post.json, and one tiny sample video run from start to end. Then an install from zero on Windows and on macOS. | So far ClipKaro has only run on this Fedora laptop. A change can break something without anyone noticing. | 1.5-2 days | a Windows or Mac computer (yours or a friend's), 1 h | To do |
| 7 | **Small fixes.** One command fixes a caption word everywhere (words, sentences, transcript). Fewer zooms in fast-talking clips: one anime clip had 48 zooms in 68 seconds. Repaired clips stop losing their rank. | Small things that look unprofessional or cost good clips. | 4-6 h | none | To do |
| 8 | **PostKaro 1.0.** Choose the account for each video, finish the new look (already in progress), and have a new user check the first-run and connect-accounts guides. | So other creators can use it, not only us. | 1-1.5 days | review the design, 30 min | To do (new look in progress) |

## Step 3. Look more professional (about 7-9 days)
Goal: clips that look like a paid editor made them. Each item is blind-tested against the version
before it, and it only stays if it wins.

| # | What | Why | Build | Your part | Status |
|---|---|---|---|---|---|
| 9 | **Trim silences and filler words** (jump cuts). Pauses inside a clip get cut, and a small zoom change hides each cut. A setting turns it off. | Viewers leave during pauses. Tight clips keep people watching. | 1 day | blind test, 20 min | To do |
| 10 | **Hook title on screen.** A big 3-6 word line ("Pakistan ka PM banoge?") for the first 2-3 seconds. | It stops the scroll even with the sound off. | 4-6 h | blind test, 15 min | To do |
| 11 | **Captions clear of faces and app buttons.** Captions stay inside each app's safe zone, and in tight close-ups they move off the chin. | Captions under the like button or over a mouth hurt watch time. | 1 day | look at 5 clips | To do |
| 12 | **Cleaner transcripts.** Fixes for phrases repeated in a loop, one long "word" hiding several real words, and nonsense words during laughter. Plus the speech-model test, scored against texts you corrected. | Wrong words in captions look unprofessional. | 1.5-2 days | correct 5 short texts, 30-60 min | To do |
| 13 | **More editing styles.** 5-8 caption looks, emojis on strong words, punch sounds, and optional background music that gets quieter under the voice (you add your own licensed music). | Gaming, podcasts and education each look different. | 2-3 days | pick your favourites | To do |
| 14 | **Faster rendering.** The NVIDIA video encoder, zooms done by ffmpeg, and two clips at once when there is enough memory. | Today about 30 seconds per clip. That is fine for now, so this one comes last. | 1-1.5 days | none | To do |

## Step 4. Smarter (when step 3 is done, or once real views exist)

| # | What | Why | Build | Your part | Status |
|---|---|---|---|---|---|
| 15 | **Sound and picture cues for Claude.** Laughter, applause, a raised voice, and big movement in games are given to Claude as hints when it picks moments. | Some of the best moments live in a laugh or a reaction, not in the words. | 1.5-2 days | blind test | To do |
| 16 | **Gameplay: your voice apart from the game.** Separate the player's voice from the game's sound before transcribing. We research the best voice-separation model first. | Game characters' lines still mix into the transcript. | 1-2 days | one gameplay video | To do |
| 17 | **Learn from real views.** PostKaro reads back views and watch time, compares them with the clip scores, and tunes the critic for your channels. | The scores should learn what works for *your* viewers. | 2-3 days | needs about 50 posted clips with 2+ weeks of views | Waiting for posted clips |
| 18 | **Review studio.** A page where you move a clip's start or end, fix a caption word and re-render one clip, without typing commands (maybe inside PostKaro). | The last bit of quality is a human touch, and it should be easy. | 3-5 days | try it | To do |
| 19 | **X (Twitter) in PostKaro.** We check X's API price and limits first. | One more place to post. | about 1 day, if the free tier allows posting | connect your account | To do |

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

## Not planned for now
- **More Indian languages** (Tamil, Bengali, Marathi, Telugu…). ClipKaro supports Hindi, Hinglish
  and English only, on purpose. [adding-a-language.md](adding-a-language.md) explains how, for later.

---

**Total to production ready (steps 1 and 2): about 6-8 days of building.**
**Steps 3 and 4: about 3-4 more weeks.**

The comparison with Opus Clip and others, and the reasons behind many of these items, are in
[roadmap-v2.md](roadmap-v2.md).
