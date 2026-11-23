# Testing guide for v3.0

Everything built after **v2.7.1** (the last stable version, the one you have on GitHub) is tested here, by you,
before it becomes **v3.0**. That is ClipKaro **v2.8 to v2.15** and PostKaro **0.9.0 to 0.10.1**.

How it goes (decided 2026-11-23):
1. You test with your own videos, using this guide.
2. You tick a box when it works. When it doesn't, write a note under the box (see "Writing down a problem" at the
   end).
3. Your notes become the **finishing touches**: Claude fixes each gap, and you check the fixes.
4. When you're happy with everything, the whole set is bundled and released as **v3.0**.

**The marks** (Claude's own testing while building, 2026-11-23, all on the Fedora laptop):
- ✅ **Claude tested it, you can skip it.** The box is already ticked, with a note on how it was tested.
- 👀 **Quick look.** Tested, but on one video only, or only from still frames: a short check from you.
- 🧪 **You must test it.** Claude couldn't (Windows, DaVinci Resolve, a real English stream, your accounts, a
  real clipping chat) or only automatic tests cover it.
- ❓ **Needs your answer.**

Of the 59 checks: **21 ticked** (✅), **15 quick looks** (👀), **22 to test** (🧪) and **1 answer** (❓).

The automatic tests (`python run.py test --full`: 186 tests, including a tiny made-up video from start to end) all
pass. They prove the code works, not that the clips look right.

---

## 1. Before you start

**Where to test.** The new versions are only on the Fedora laptop for now (nothing is pushed yet). To test on
Windows too, push first, then update there:
```
# on the Fedora laptop, in the ClipKaro folder
git push git@github.com-personal:allthingsaman/ClipKaro.git main v2.8 v2.9 v2.10 v2.10.1 v2.11 v2.12 v2.13 v2.14 v2.15
# in the PostKaro folder
git push git@github.com-personal:allthingsaman/PostKaro.git main v0.9.0 v0.9.1 v0.10.0 v0.10.1
# then on Windows, in each of the two folders:
git pull
python install.py
```

**Once, on every computer you test on:**
- [ ] Run `python install.py` in the ClipKaro folder (`python3` on Fedora). It adds the small text reader for
  game subtitles. You should see `[ok] rapidocr (game subtitles for English streamers)`, and nothing about a
  second OpenCV.
- [ ] Restart PostKaro so it runs the new version. In the PostKaro folder, when nothing is uploading:
  `python run.py service off`, then `python run.py service on`. Then `python run.py status` starts with
  "PostKaro 0.10.1 · running".
- Some parts download a small model the first time they are used (nothing to do, just a short wait): the text
  reader (about 10 MB), the face-expression model (16 MB) and the body finder (3.6 MB).

**Once, for the numbers in PostKaro (v2.11):**
1. In Google Cloud (your PostKaro project): **YouTube Analytics API** → **Enable**. PostKaro's Posted page has
   the direct link. In Google Auth platform → Data Access, also tick `.../auth/yt-analytics.readonly`.
2. In PostKaro → Accounts: **Reconnect** YouTube, then **Reconnect** Facebook and Instagram (allow everything).

**Videos to have ready.** A few videos cover almost everything:

| Video | Tests |
|---|---|
| A long **Hinglish GTA stream** of yours with deaths, failed missions and a boast ("like a boss") | action pauses, game-over screens, boast-then-fail, only part of a video, bigger webcam, word check |
| Your **last 3-4 streams**, already clipped | compilation |
| An **English gameplay stream** with the game's subtitles on (yours, or a public one) | captions only for the streamer |
| A **two-person podcast** (Khan Sir / Raj Shamani style) | silent laughs, Studio framing, nothing changed for podcasts |
| A **panel or podcast with three people** in one wide shot | three people |
| A talk or podcast that **names films, places or famous people** | b-roll |
| Someone **walking around in front of a still camera** (a class at the board, a stage talk, a vlog) | following people who move |

---

## 2. At a glance: on by itself, or do you ask for it?

**"By itself"** means you clip as usual ("clip this: link") and it just happens. **"Ask"** means you put the
words in your message.

| What | Version | How it's switched on | Way back (if you don't like it) |
|---|---|---|---|
| Only part of a video | v2.8 | **Ask:** "only the first hour", "from 20:00 to 1:10:00", "pehle ek ghante ka hi" | (just don't ask) |
| Smarter action pauses (gameplay) | v2.8 | **By itself** | `"action_pauses": "keep"` (v2.7.1's way) |
| Bigger webcam in gameplay clips | v2.8 | **By itself** | `"facecam_margins"` in settings.json |
| No captions for game characters, English streamers | v2.8 | **By itself** (English gameplay; turn the game's subtitles on when you stream) | `"game_subtitles": false` |
| Landscape (16:9) copy | v2.8 | **Ask:** "landscape copy", "16:9 copy too", "YouTube video version bhi" | (just don't ask) |
| Export to DaVinci Resolve | v2.8 | **Ask:** "export to resolve", "open clip 3 in Resolve" | (just don't ask) |
| Word check done | v2.8 | **Setting** `"unsure_words": "ask"`, then **ask:** "word check done" | `"unsure_words": "hide"` (the normal setting) |
| Game-over screens read (WASTED, FAILED, BUSTED) | v2.9 | **By itself** (gameplay) | `"game_over_screens": false` |
| "Boast, then fail" clips | v2.9 | **By itself** (gameplay, standard and deep mode, only when it's funny). You can also **ask:** "make a boast-then-fail clip of the Phoenix mission" | (comes with the game-over screens) |
| Compilation across videos | v2.9 | **Ask, in advanced mode:** "advanced mode: a compilation of every glitch from my last 4 streams" | (just don't ask) |
| Review Studio in PostKaro | v2.10 | **By itself:** a **Fix** button on every clip, and a **Studio** tab | (just don't use it) |
| Your own cuts, moments, emojis, sounds in the Studio | v2.10.1 | **By itself**, in the Studio | (Undo) |
| Numbers of your posts in PostKaro | v2.11 | **By itself** (read in the background), after the one-time steps above | — |
| "How are my clips doing?" report, and the critic learning | v2.11 | **Ask:** "how are my clips doing?" or "learn from my views". The critic uses what was learned from then on, by itself | `"learn_from_views": false` |
| Silent laughs in podcasts | v2.12 | **By itself** (talk videos, not gameplay) | `"silent_reactions": false` |
| Three people in one shot | v2.13 | **By itself** | a `framing` in clips.json |
| B-roll | v2.14 | **Ask:** "add b-roll", "b-roll on clip 3" | (just don't ask); the Studio switches a piece off |
| Following people who move | v2.15 | **By itself** | `"follow_moving": false` |

Everything else you already know (captions, emojis, credit, logo, outro, careful listening, live clipping) works as
in v2.7.1.

---

## 3. Gameplay and streams

### Smarter action pauses (v2.8, by itself)
**What it is.** ClipKaro cuts quiet pauses out of clips. In v2.7.1, a pause where the picture changed a lot was
always kept (so a takedown before "ye kya ho gaya" stayed), but plain camera swings stayed too. Now such a pause
stays only when something shows it mattered: a game sound (explosion, crash, gunshot), or right after it a laugh, a
shout, a reaction word ("ye kya", "bhaag"), "arre", "oye", or a much louder voice.
- [ ] 👀 *Claude's test: measured on one GTA stream (124 kept pauses down to 36, the police takedown kept); which ones stay is your call.* In a few gameplay clips, watch the quiet moments. A takedown, crash or explosion before a reaction stays in;
  a plain camera turn with nobody reacting is cut. If too much action is cut, write it down.

### Bigger webcam (v2.8, by itself)
**What it is.** In the gameplay-on-top, webcam-below layout, the webcam is a little bigger (50 px from the sides,
50 px below the captions, 30 px above the bottom). And when your faces sit low in the webcam, ClipKaro no longer
takes a strip of the game for part of the webcam.
- [ ] 👀 *Claude's test: checked on one GTA 6 stream when it was built.* The webcam fills the space below the captions; the webcam box holds only the webcam, no line of the game.
- [ ] 👀 If `cut` says "the webcam box is taller than a webcam picture", look at `frames/facecam-box.jpg`.

### Captions only for the streamer, also in English (v2.8, by itself)
**What it is.** In gameplay, game characters' lines get no captions (the game shows its own subtitles). Hinglish
streams already had this. Now English streams have it too: ClipKaro reads the game's subtitles on screen, and a
line shown there is the game's.
**Needs:** an English stream with the game's subtitles switched on.
- [ ] 🧪 *Claude's test: only tested on a made-up clip with drawn subtitles, never on a real English stream.* Game characters' lines have no ClipKaro captions; every line of yours and your friends' has captions. Goal:
  at least 9 of 10 game lines without captions, none of yours missing.

### Game-over screens and "boast, then fail" (v2.9, by itself)
**What it is.** ClipKaro reads WASTED / FAILED / BUSTED from the picture (about a minute for a 4-hour stream) and
shows them to Claude as lines of their own. When someone boasts ("mission like a boss karenge") and the game then
says FAILED, Claude can tell it as one clip in a few sharp cuts: the boast, the fail screen shown whole, the
reaction. Only when it's funny: never a clip for every random death.
- [x] ✅ *Claude's test: tested on your 4-hour GTA stream: 6 real screens (WASTED, FAILED, BUSTED) in about 1.5 minutes, none false.* `fetch` prints `-> game-over screens in ...s: N (WASTED, FAILED)`, and `transcript.txt` has lines like
  `[5437.03-5441.53] [on screen: FAILED - THE PHOENIX WAS DESTROYED.]`. No false ones (a sign or a menu read as a
  game over)?
- [ ] 🧪 *Claude's test: the story clip was made directly; Claude never found one by itself in a normal clipping run.* On a stream with a boast and a fail a few minutes apart, Claude finds the story by itself: up to 6 cuts, the
  boast first, the FAILED screen whole, the reaction last.
- [ ] 🧪 Asking works too: "make a boast-then-fail clip of the Phoenix mission".
- [ ] 🧪 Deep mode: a boast and its fail more than about 20 minutes apart are found as one deep clip.
- [x] ✅ *Claude's test: checked on the "like a boss ... FAILED" story clip, and by unit tests.* In any clip showing WASTED or FAILED, the screen plays whole (no pause cut inside it).

### Only part of a video (v2.8, ask)
**What it is.** For a stream that kept recording after you stopped playing: only the part you name is written down
and clipped (faster). All times stay on the full video's clock.
- [x] ✅ *Claude's test: used twice (a GTA stream, and a Khan Sir class: only 2:00 to 6:00 written down, clip times on the full clock).* Say "clip this: link, only the first hour". The transcript's first lines say which part was written down,
  and every clip comes from that part.

### Word check done (v2.8, setting + ask)
**What it is.** On noisy Hinglish streams, careful listening normally hides words it can't be sure of (no caption).
With `"unsure_words": "ask"` in settings.json, it lists them in `word-check.json` instead, so you can correct them
by ear.
- [ ] 🧪 *Claude's test: unit tests only; no real run with your answers.* Clip a noisy stream with that setting. Fill a few answers in `word-check.json` (the right word, or "-" for no
  caption) and say "word check done". The right words show in the captions, "-" words have none, and only those
  clips are made again.

### Reaction words on frame sheets (v2.8, by itself)
- [ ] 🧪 *Claude's test: unit tests only. Low priority: needs a computer without an NVIDIA card.* On a computer without an NVIDIA card (Hindi letters in the transcript), look at a gameplay frame sheet
  (`frames/`): yellow reaction words show where someone reacts, and "aage" is never shown as "AAG".

---

## 4. Podcasts and talks

### Silent laughs (v2.12, by itself)
**What it is.** ClipKaro hears laughs, but missed a listener who cracks up without a sound. Now it also reads faces.
A strong silent laugh becomes a hint for picking moments, and in a two-person clip both people are shown while the
listener laughs. Only strong reactions count. It adds about 4 minutes per hour of video to `fetch`.
- [ ] 👀 *Claude's test: tuned on 6 minutes of one Khan Sir podcast; check on another podcast.* After fetch, `transcript.txt` has a few lines with `[a silent laugh on screen ~2 s]`. Are they real?
- [ ] 👀 In a clip where the listener laughs silently while the other talks, the split screen shows both, then goes
  back to the speaker.
- [ ] 👀 People simply talking or smiling a little never trigger it.

### Three people in one shot (v2.13, by itself)
**What it is.** Before, a wide shot of three people was framed as if only two were there, so the third was never
shown, even when talking. Now the one talking gets the crop (left, middle or right), and laughs or talking over each
other show all three stacked.
- [ ] 👀 *Claude's test: tested on one 3-minute panel (MensXP) only.* When one person talks for a while, the clip shows them, also the one in the middle.
- [ ] 👀 Laughs and cross-talk show all three stacked; captions sit between the 2nd and 3rd person, never on a face.
- [ ] 👀 "In clip 2, show the middle person at 0:14" works.

### Following people who move (v2.15, by itself)
**What it is.** Each camera shot used to get one fixed standing crop, so a teacher walking along the board walked
out of the clip. Now, only when the person would leave the crop, it follows them like a camera operator. It holds
still for small moves and pans smoothly when they move away, also when they turn their back to the camera (a body
finder fills in for the face). People who sit or stand still are framed exactly as before.
- [ ] 👀 *Claude's test: tested on one Khan Sir class, from still frames every 0.5 s. Watch `output/zz-follow/clips/03-the-ias-officers-dog.mp4` playing.* The person stays in the clip while they walk, also with their back to the camera.
- [ ] 👀 *Claude's test: only still frames were seen; only your eyes can judge jitter.* Smooth, not shaky: no jitter, no sudden jumps.
- [x] ✅ *Claude's test: on the Khan Sir podcast and the panel, no shot started following.* A seated podcast looks exactly as before.
- [x] ✅ *Claude's test: covered by a unit test: a framing you set always holds still.* "In clip 2, keep the left side from 0:14 to 0:20" holds the crop still there.
- [x] ✅ *Claude's test: seen on the Khan Sir sheets.* On frame sheets (`run.py frames`), shots that follow say **FOLLOWS** and the green box moves.

### B-roll (v2.14, ask)
**What it is.** Say "add b-roll". When the words name a film, a place, a famous person or a product, a picture of it
(from Wikimedia Commons, free with credit) or a short piece of the film's official trailer covers the speaker for
2-3 seconds; the captions carry on. A small credit shows at the top ("Trailer: T-Series", "Photo: author, licence,
Wikimedia Commons") and goes into the posting texts. Your rules: trailer pieces at most 5 seconds, and nothing
right found = no b-roll there (never a wrong picture). A trailer piece can get a YouTube copyright claim (usually
the ad money goes to the studio); you can switch any piece off in PostKaro's Studio.
- [ ] 👀 *Claude's test: one test clip, the two b-roll spots placed by hand, not chosen in a real "add b-roll" run.* Each cutaway shows the thing named (the right film, place or person), 2-3 seconds, captions on top.
- [ ] 🧪 *Claude's test: needs a real "add b-roll" run.* Where nothing right was found, Claude's report says so and the speaker stays on screen.
- [ ] 🧪 *Claude's test: the credit at the top was checked; the "B-roll:" line in the posting texts needs a real run.* Credits at the top; the posting texts end with a "B-roll: ..." line.
- [x] ✅ *Claude's test: checked on the Animal trailer (letterbox bands cut off, the title card shown whole).* No trailer piece over 5 seconds; no black bands; a film's title card shows whole.
- [ ] 🧪 *Claude's test: needs a real clipping run.* A normal "clip this" (no "b-roll" in it) makes no b-roll.
- [ ] 🧪 *Claude's test: optional; never tested (no key).* Optional: stock video needs your own free key (`"pexels_key"` or `"pixabay_key"` in settings.json).

---

## 5. Extras you ask for

### Landscape copy (v2.8, ask)
**What it is.** The clips stay standing, and a wide 1920x1080 copy is made next to each, for normal YouTube
videos. Compilations longer than 1:30 always get one.
- [x] ✅ *Claude's test: frames of the wide copy checked.* Say "landscape copy" for a clip: `edited/NN-title-landscape.mp4` has the same moment and sound, captions low
  in the middle, credit and logo in their corners. PostKaro still posts the standing clip.

### Export to DaVinci Resolve (v2.8, ask)
**What it is.** To finish a clip by hand in the free DaVinci Resolve: a timeline with the clip in its pieces, its
sound, the sound effects on their own track, and the captions as a subtitle file.
- [ ] 🧪 *Claude's test: the timeline file was only checked with a reader program, never opened in Resolve itself.* Say "export clip 2 to resolve". In Resolve: File > Import > Timeline (the `.xml` in `resolve/NN-title/`) and
  File > Import > Subtitle (`captions.srt`). The clip shows in its pieces, the sound on A1, the sound effects on
  A2 at the right moments, the captions as a subtitle track, no "media offline".
- [ ] 🧪 Try on Fedora (it makes edit copies first) and on Windows (no copies needed).

### Compilation across videos (v2.9, ask in advanced mode)
**What it is.** One clip made of moments from several clipped videos on one topic (you name it, or Claude suggests
some). Every moment is checked on its frames first, so it takes a while and uses more of your Claude plan.
- [ ] 👀 *Claude's test: a 2-video test only (`output/zz-comptest`).* Say "advanced mode: a compilation of every glitch from my last 4 GTA streams". Claude says up front that it
  takes a while and shows the frame sheets it checked (`compile/moment-NN.jpg`). The clip has no silent glitch cut
  out, no jump in loudness between moments, and captions and credit as usual. Over 1:30 there is also a
  landscape copy.
- [ ] 🧪 In quick or standard mode, Claude says compilations are advanced mode only.
- [ ] 🧪 Streams with the webcam in different places: Claude warns that the layout follows the first video.
- [ ] ❓ **Your answer, please:** compilations of 1:30 or less come out standing only. Is that what you meant? (You
  wrote "keep it on landscape" for the short ones.)

---

## 6. PostKaro

### The Studio: fix a clip by clicking (v2.10, PostKaro 0.9.0)
**What it is.** Every clip of a ClipKaro video has a **Fix** button, and there is a **Studio** tab. You change a
clip by clicking, then **Make the clip again**: only that clip is cut and edited again (about a minute), with no
Claude usage. **Undo last change** puts it back.
- [x] ✅ *Claude's test: clicked through in a test copy of PostKaro (on Fedora).* **Start and end:** click an earlier (grey) word under Start and a later one under End. The new clip plays
  from the word you picked to the word you picked.
- [x] ✅ **A caption word:** click a wrong one, type the right one; fixed, the sound the same. Also try "No caption
  for this word".
- [x] ✅ **Framing (podcast):** **Both people**, then **Left person**: the whole clip shows that.
- [x] ✅ **Emojis, sounds, whooshes:** switch one of each off: gone; back on: back.
- [x] ✅ **Undo last change** puts the clip back exactly as before.
- [ ] 🧪 *Claude's test: never done (Claude doesn't post publicly).* **Posting after a fix:** the fixed version is the one that goes out. A clip already uploaded but not live yet
  says to cancel that post first.
- [x] ✅ *Claude's test: 52 s for a 43-second clip on the Fedora laptop.* **Speed:** is "about a minute" true on your laptop? Note the time it shows.

### Your own cuts (v2.10.1, PostKaro 0.9.1)
- [x] ✅ *Claude's test: clicked through in a test copy of PostKaro (on Fedora).* **Cut a part out:** under **Words**, click a word → "Cut out from here…" → click a later word → make the clip
  again. That part is gone (a short flash at the join).
- [x] ✅ **Add a moment:** **Find** words said anywhere in the video (or "The 2 minutes after the clip"), click the
  first and last word, **Add**. The moment plays in its place in time, with captions.
- [x] ✅ **Your own emoji:** click a word, pick 🔥 (or type any emoji). It shows on that word, even when the clip
  already had 3 of Claude's.
- [x] ✅ **Your own sound:** click a word, pick a mood (funny, shock …). The sound plays on that word.
- [x] ✅ **Undo** after these puts the clip back.

### B-roll switches (PostKaro 0.10.1)
- [x] ✅ *Claude's test: clicked through in a test copy of PostKaro: the trailer piece went, the photo stayed.* On a clip with b-roll, the Studio has a **B-roll** section. Switch one piece off and make the clip again: the
  speaker is back there, the other pieces stay.

### How your posts did (v2.11, PostKaro 0.10.0)
**What it is.** PostKaro reads every live post's numbers in the background, about 1, 3, 7 and 28 days after it went
live (views, how much people watched, shares, likes), and shows them on Posted. Asking Claude "how are my clips
doing?" gives a plain report per channel. With 30+ posted clips that have results, the critic's ranking slowly
leans towards what really did well on your channels. It only changes the order; no clip is ever dropped.
- [ ] 🧪 *Claude's test: views, likes and comments were read for your 394 live posts; the rest needs your one-time steps first.* Posted shows numbers under each live post. After the one-time steps, the "no … yet" notices are gone.
- [ ] 🧪 The numbers match YouTube Studio / Instagram Insights for two or three posts.
- [ ] 👀 *Claude's test: the report ran on 79 of your YouTube clips; whether it sounds right is for you to say.* "How are my clips doing?" gives the best clips, which lengths and kinds do best, and how well the clip score
  matched. Does it sound right to you?
- [ ] 🧪 *Claude's test: not enough clips with a critic score yet for the learning to start.* After the report says "Weights now used", the next video's `critic.txt` says "Weights: learned from N posted
  clips".

---

## 7. Nothing you liked should have changed

v1.1 and v2.7.1 are the baseline: everything new must be an upgrade.
- [ ] 👀 A normal two-person podcast clip looks like before (framing, captions, emojis, sounds).
- [ ] 🧪 Quick mode still makes clips with little Claude usage.
- [ ] 🧪 *Claude's test: everything ran on Fedora only.* **On Windows:** install, one clipping run, and the Studio (Fix a clip, make it again) all work.
- [ ] 🧪 Live clipping on a stream works as in v2.7.1 (no frame sheets, auto-posting through PostKaro).
- [ ] 🧪 Clips without "b-roll", "landscape copy" or "export to resolve" in the message have none of those.
- [x] ✅ *Claude's test: every test run on the Fedora laptop used your own settings.json (it has none of the new settings).* Your settings.json from before works unchanged (every new setting starts with a sensible default).

---

## 8. Claude's own test runs, if you want to look first

Claude tested each part on public YouTube videos while building it. You can look at the results (they are scratch
projects; delete them whenever you like):

| Folder in `output/` | Shows | Look at |
|---|---|---|
| `zz-follow` | following people who move (a Khan Sir map class: he walks across the screen and points at the board) | `clips/` (cut, not edited): clip 3 from 0:15 to 0:27, clip 2 from 0:00 to 0:20; `frames/` |
| `zz-panel` | three people (a MensXP panel) and b-roll (the Taj Mahal photo at 0:20; the Animal trailer piece at 0:05 is switched off from the Studio test) | `edited/01-panel-test.mp4` |
| `zz-landtest` | landscape copy, and the "like a boss ... FAILED" story clip | `edited/159-...-landscape.mp4`, `clips/161-...` |
| `zz-comptest` | a compilation from 2 videos | `edited/01-test-glitches.mp4` |
| `zz-subtest` | game subtitles read on an English test clip | `clips/01-subtitle-test.mp4` |
| `zz-parttest` | only part of a video | its `transcript/` |

---

## 9. Writing down a problem

Under the box that failed, write:
- **the video** (link or file) and the **clip number**;
- **the time** in the clip (e.g. 0:14);
- **what you saw**, and **what you expected**.

For example: "Following, clip 3 of the class video, 0:21: he walks off the right side for a second, the camera
catches up late." These notes are the finishing touches. Claude fixes them one by one, you check the fixes, and
then everything is released as v3.0.
