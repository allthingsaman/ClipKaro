# ClipKaro v3.0: the plan (draft for discussion)

*Planned with the owner on 23 November 2026 and **approved** the same day. Phase 1 starts on the branch
`v2.8-quick-wins`.*

v3.0 is the big release: the major-update items from [roadmap-v3.md](roadmap-v3.md), the ideas that came
up while clipping the GTA 6 streams, and the small fixes found in the v2.7.1 review. Every item follows the
house rules:
- an upgrade to v1.1, with a way back where it changes how things work;
- a line in [since-v1.1.md](since-v1.1.md);
- a test;
- `python run.py test` passing;
- the docs kept in step.

## 0. Updates since the roadmap (23 November 2026)

| Item | Now |
|---|---|
| Live clipping on a real stream | **Tested** by the owner on Windows, in test mode ("dry"), on a GTA stream: clips were made |
| A fresh gaming video, start to finish (v2.7's final check) | **Done** by the owner (Twitch 2934733365 and 2934840802, 21–22 November) |
| A real install on a Windows PC (item 22) | **Done:** the owner installed both apps for his video guide |
| Cheaper helper models (item 3b) | **On hold:** the owner does the blind pairs later |
| Your mic on its own track (item 13b) | **Works only for your own OBS recordings.** Twitch and YouTube mix every sound track into one before they show the stream, so their downloads can't separate the mic (the owner checked on Windows). Close it, and say so in the docs |
| TikTok and LinkedIn in PostKaro | **Removed** from the plan (the owner's choice) |
| On hold, unchanged | Opus Clip side-by-side test, background music, posting to X, YouTube's captions as a second opinion |
| PostKaro | 0.8.0 (pick when "Spread over" starts) is built; the owner pushes it. The "Reject" feature is designed, waiting for his look |
| How v3.0 is released (owner, 23 Nov) | **Step by step:** v2.8, v2.9, v2.10 … each with a few items, then everything bundled as v3.0 |

## 1. The items at a glance

| # | Item | For | Size (estimate) |
|---|---|---|---|
| A | Review studio: fix a clip without commands | every video | 3–5 days |
| B | Learn from real views | every channel | 2–3 days |
| C | B-roll over the speaker | podcasts, talks | 3–5 days |
| D | Following people who move | vlogs, IRL, stage | 1–2 weeks |
| E | Three or more people | podcasts, panels | about 1 week |
| F | "Boast, then fail" clips | gameplay | about 1 day |
| G | Compilations across videos (advanced mode only) | gameplay first | 2–3 days |
| H | A landscape (16:9) copy of a clip | every video | about 1 day |
| I | Silent reactions in podcasts | podcasts | 1–2 days |
| J | Captions for the streamer, never for game characters, also when both speak English | gameplay | 2–3 days |
| K | Open a clip in DaVinci Resolve (free) | every video | about 1 day |
| L | The three limits from the review | gameplay | about 1.5 days |
| M | Clip only part of a video ("only the first hour") | every video | half a day |
| N | Housekeeping: refresh the roadmap, close the finished items | – | an hour |

**Total: roughly 5–7 weeks of focused sessions,** plus the owner's tests. A proposed order is in section 3.

## 2. Each item

### A. Review studio
- **What:** a page where the owner changes a finished clip without typing commands, and re-renders only that clip:
  - move its start or end;
  - fix a caption word;
  - switch the framing (the speaker, both people, the whole picture);
  - turn an emoji or a sound effect on or off.
- **Goal:** a clip the owner wants changed is fixed in under a minute, by clicking.
- **How:** a local page like PostKaro's (127.0.0.1). It writes the same clips.json fields Claude writes today (`ranges`, `framing`, `show_full`, captions through `fixword`), then runs cut, edit and qa for that one clip. No Claude usage.
- **Decided (owner):** **inside PostKaro, as its own page** (a "Review studio" tab next to Post / Queue /
  Posted). PostKaro only handles posting, so it is the natural home: one app for checking, fixing and posting,
  nothing scattered. PostKaro calls ClipKaro's commands to re-render a clip.
- **Still to settle when building:** which edits come first (start/end and caption words are the obvious two).

### B. Learn from real views
- **What:** PostKaro reads back each posted clip's views and watch time, and ClipKaro learns which kinds of clips do well on *your* channels.
- **Goal:** a short report ("on Gaming Things, boast-and-fail clips average 2x the views; clips over 45 s lose people at 20 s"), and a critic whose ranking matches your real views better than today.
- **How:**
  - **YouTube:** the Analytics API gives views, average view percentage and a retention curve per video ([metrics](https://developers.google.com/youtube/analytics/metrics.md)). It needs one more read-only permission, so you'd press Reconnect once.
  - **Instagram and Facebook:** insights through Meta's API (which numbers exist for Reels is checked when building).
  - **Learning:** the clip scores are compared with the results. The critic's weights (hook, payoff, emotion, share, quote) are tuned per channel. It only ever **ranks**, and never drops a clip.
- **To know:** YouTube's retention is one curve for the whole period, and on Shorts it can go above 100% because people loop the video.
- **Needs:** about 50 posted clips with 2+ weeks of views. You're past that now.
- **Success (Claude's proposal; the owner left it to research):** three numbers, read 7 days after posting,
  compared only with the same channel's other clips:
  1. **Reach:** engaged views ([YouTube Analytics](https://developers.google.com/youtube/analytics/metrics.md)
     has `engagedViews`; Shorts views are counted differently since March 2025, so engaged views keep old and
     new clips comparable);
  2. **Did people stay:** average view percentage (over 100% means people watched it again);
  3. **Did people care:** shares per 1,000 views (the critic's "who would send this" score).
  A clip's result is its rank on its own channel (top, middle, bottom third). Studio's "viewed vs swiped away"
  would be ideal, but the API doesn't offer it. Instagram's Reels numbers are checked when building.
- **Decided:** the owner leaves the measure to Claude; this proposal is it.
- **What it changes:** the critic's weights per channel, slowly, and only the ranking, never dropping a clip.
  It also writes a plain report ("on Gaming Things, clips under 30 s are watched 20% further").

### C. B-roll over the speaker
- **What:** when the words name something (a film, a person, a place, a product), a 2–3 second clip or picture covers the speaker, then cuts back.
- **Goal:** a viewer sees what's being talked about, without the clip feeling busy.
- **How:**
  - **The plan:** Claude marks the moments while writing clips.json (a `broll` field).
  - **Sources:**
    - official trailers on YouTube for films;
    - Wikimedia Commons for pictures of people and places;
    - free stock clips from [Pexels](https://help.pexels.com/hc/en-us/articles/900005852323) or [Pixabay](https://pixabay.com/api/docs/). Both need free keys; Pixabay asks for 24-hour caching. Pexels' help page said new keys were paused, so check before relying on it.
  - **Matching:** frames are scored against the description (SigLIP). Claude picks from a contact sheet.
  - **Not found:** **no guessing;** a note for you instead.
  - **Copyright:** **warn, never block,** and keep snippets short.
- **Shared with EditKaro:** this is the same job as EditKaro's Phase 3, so it's built once and used by both.
- **What changes in a podcast clip, an example:** the guest says "jab main Kedarnath gaya, poori valley baraf
  se dhaki thi…". For 2–3 seconds the picture switches from his face to a clip of the snowy Kedarnath valley,
  the captions carry on, then it's back to his face. One to three cutaways a minute, only on clear, concrete
  things (a place, a famous person, a product, a film), never on vague words.
- **Why the trailer question:** when someone names a film ("Animal ka climax"), the best picture is a shot
  from that film's official trailer on YouTube. That footage belongs to the studio, so YouTube's Content ID may
  claim the clip (the ad money goes to the studio, or it's blocked in some countries). Free stock clips
  (Pexels, Pixabay) carry no claims but can't show a particular film. So: trailer shots (better, some claim
  risk) or stock and free pictures only (safe)?
- **Decided (owner): trailers are allowed,** for the better picture, with these rules:
  - **no trailer piece longer than 5 seconds.** Covering more means several short pieces (about 4 s each)
    from different parts of the trailer, never one long stretch;
  - **credit the channel** the footage came from;
  - a claim usually means a review request, not a strike; the owner handles those, and the review studio
    (item A) lets anyone remove a piece.
- **Default:** only when named ("b-roll") at first; a default is chosen after a few tests.

### D. Following people who move
- **What:** a speaker who walks, turns or moves around the stage stays in the frame smoothly. Objects (a car, a ball) are later.
- **Goal:** the subject never leaves the 9:16 frame, and the camera doesn't jitter.
- **How:**
  - **Tracking:** a person detector plus a tracker. [Roboflow Trackers](https://cdn.jsdelivr.net/gh/roboflow/trackers@develop/README.md) (Apache 2.0) has ByteTrack and BoT-SORT, which corrects for a moving camera.
  - **The detector:** one with a free licence (not the AGPL Ultralytics YOLO). The licence is checked when building.
  - **The camera:** smoothed, the same way ClipKaro already smooths its face camera.
- **To settle:** which of your videos have people moving: IRL streams, vlogs, events? We need one to test with.

### E. Three or more people
- **What:** podcasts or panels with 3+ people, and remote guests in a grid.
- **Goal:** the person talking is on screen most of the time. Laughs and cross-talk show 2–3 people stacked.
- **How:**
  - **Who's talking:** decided from both the lips and the voice with active-speaker detection. [Light-ASD](https://arxiv.org/pdf/2303.04439v1.pdf) is about 1M parameters, so it runs fine on the processor; its licence is checked when building.
  - **Layouts:** the speaker crop, 2 or 3 stacked panels, or picture-in-picture for a remote guest.
- **To settle:** a 3-person video of yours (or one you like) to test with.

### F. "Boast, then fail" clips (gameplay)
- **What:** a friend promises "we'll do this mission like a boss", and minutes later the game says FAILED.
  ClipKaro finds such stories and tells them in a few sharp cuts.
- **The owner's rule:** **only when it's funny.** Not every death, WASTED or FAILED is a clip. A fail counts when it pays off something said before: a boast, a promise, a confident claim, a joke. Claude judges that, and the critic scores it like any other clip.
- **How:**
  - **Game-over screens:** WASTED, FAILED and BUSTED become hint lines in the transcript, like "[explosion]" today. This runs locally, uses no Claude usage, and takes about a minute per 4 hours of video.
  - **A "boast → fail" thread** in the deep pass links the claim to the fail, even when the fail is only on screen.
  - **Story clips:** in gameplay, up to about 6 pieces from one stretch of up to 10 minutes. Every piece must carry something (your "shorter wins" rule).
  - **Pieces without words** are allowed: a crash or the FAILED screen with only game sound.
- **Decided (owner):** **standard mode too.** A boast and its fail almost always happen within one part
  (about 21 minutes), so the part readers can find them without the deep pass; the game-over hints are free.
  Only a boast and fail further apart than one part needs deep mode.

### G. Compilations across videos (advanced mode only)
- **What:** one clip made from moments in several videos on one topic, like the "2 billion dollar glitches" compilation made by hand on 22 November.
- **Why advanced mode only:** finding the topic and every matching moment across whole videos is Claude's job, and it costs usage.
- **How:**
  1. **The topic:** you name it ("every glitch", "every time Jason dies"), or Claude suggests topics from the projects' topic maps.
  2. **The search:** Claude reads the topic maps, transcripts and frame sheets of the chosen projects.
  3. **The moments:** each is checked on its frames.
  4. **The join:** frame-exact, with the loudness evened.
  5. **The finish:** the normal captions, edit, qa and post.
- **The lesson of 22 November:** pause cutting removed silent glitches (a tree vanishing), so compilation pieces aren't pause-cut. You also asked why it took long; the answer is the frame check of every moment, and the report says so up front.
- **Decided (owner):** topics he names, and Claude's suggestions too.
- **Format:** up to 1:30, vertical only (a Short); over 1:30, vertical **and** landscape (item H), so it can
  also go on YouTube as a normal video.
- **Longest length:** no fixed limit for now; a Short can be up to 3 minutes on YouTube, and a longer
  compilation simply becomes a landscape video as well.

### H. A landscape (16:9) copy of a clip
- **What:** a 1920x1080 version for YouTube long-form or compilations, with captions, logo, credit and emojis placed for a wide picture. On 22 November it was made by hand.
- **How:** `edit --landscape`, a new layout for the existing edit: the same captions and sound, a different frame.
- **Decided (owner):** only when asked, and always for compilations longer than 1:30.

### I. Silent reactions in podcasts
- **What:** the listener laughs or looks shocked **without making a sound**. Today ClipKaro can't hear it, so it misses the moment and keeps the camera on the speaker.
- **Your rule:** only **strong** reactions.
- **How:**
  - **Detection:** two-person podcasts get a face-expression check on frames 2–4 times a second ([HSEmotion](https://github.com/HSE-asavchenko/hsemotion-onnx), Apache 2.0; its labels for happiness and surprise are checked when building).
  - **A strong laugh or shock becomes:**
    - a hint for picking moments: "[the guest laughs silently ~2 s]";
    - a split screen at that moment, so viewers see both people.
- **To settle:** nothing big; the strength threshold is tuned on one of your podcasts.

### J. Captions for the streamer, never for game characters, also when both speak English
- **The owner's rule:** the streamer's (and friends') words always get captions; game characters never do.
  It is a base feature, so it must also work when the game and the streamer both speak English.
- **Why it fails today:** every line already has a **voice print** (`clipper/voices.py`), and the streamer is
  the voice that talks most. A line is a game line when its voice is unlike the streamer's **and** it is mostly
  English. With a Hinglish streamer the language separates the game from friends (who also sound unlike the
  streamer); with an English streamer that second clue is gone, so the rule is switched off.
- **The solution: three more clues, all local and free, used together:**
  1. **The game's own subtitles on screen** (the strongest). Most games, GTA 6 included, can show subtitles. A
     text reader (PP-OCRv5, the same one the dub project uses) reads the subtitle area; a transcript line whose
     words match the subtitle on screen at that moment is a game line. Found once per video in seconds.
  2. **Voices that come and go in bursts.** The streamer and friends talk all through the stream; game characters
     speak in short bursts (a cutscene, a phone call), many different voices. A voice heard only in such bursts is
     the game; a voice heard across the whole stream is a person.
  3. **Studio sound vs microphone sound,** learned per video. Game lines are recorded in a studio and mixed into
     the game; the streamer's mic and voice chat sound different (room, compression). Lines found by clues 1 and 2
     teach a small per-video model which sound is which, and it decides the unclear lines. (To test: the least
     proven of the three.)

  Plus what exists: the mic on its own track (perfect, when the recording has it) and Claude's caption check.
- **Goal:** on an English gameplay stream, at least 9 of 10 game lines lose their captions and no streamer line
  does (a wrong hidden caption is worse than a missed one).
- **Decided (owner):** go ahead; try it, then improve where needed.
- **Needs:** an English-speaking stream with game dialogue to test on (the owner's, or a public one).

### K. Open a clip in DaVinci Resolve (instead of Premiere Pro)
- **What:** every clip can also come out as an editable timeline that DaVinci Resolve (free) opens. Kdenlive (free) opens it too.
- **Why not CapCut:** it can't import a timeline from another program, and has no Linux version (EditKaro's research).
- **How:** reuse EditKaro's export: OpenTimelineIO plus Final Cut Pro 7 XML, with captions as a subtitle track and markers.
- **Decided:** on request only ("export to resolve"). Built last in v2.8; the owner can still skip it.

### L. The three limits from the review
1. **Reaction words on frame sheets.** (Not an AI model: a fixed word list in the code.)
   - **What they are:** gameplay frame sheets write a yellow word on frames where someone reacts ("BHAAG", "KYA"), so the helpers know where to look.
   - **Problem 1:** the list holds Roman Hindi spellings ("bhaag", "kya", "arre"), so Roman transcripts work; a transcript in Hindi letters (Devanagari, on computers without an NVIDIA card) gets no yellow words.
   - **Problem 2:** it matches only the start of a word, so "aage" shows as "AAG" (fire).
   - **Fix:** whole words, in both scripts.
2. **`"unsure_words": "ask"` has no follow-up.** (The idea exists and writes the list; the answer step was never built. The normal setting, "hide", asks nothing.)
   - **What it is:** careful listening normally **hides** words the three hearings can't agree on. With `"ask"`, it lists them in word-check.json so you can correct them by ear.
   - **Problem:** nothing reads your corrections back.
   - **Fix:** a step that applies them ("word check done" → `wordcheck --answers`).
3. **Kept pauses include fast camera swings.**
   - **What it is:** in gameplay, a quiet pause where the picture changes a lot stays in, so the takedown before "ye kya ho gaya" isn't cut out.
   - **Problem:** a fast camera turn also changes the picture a lot, so some boring camera swings stay too. On the GTA stream 76 of 160 clips got about 1.4 s longer.
   - **Decided (owner): the smarter check.** Today a pause stays when the picture changes a lot. Smarter: it stays
     only when the picture changes a lot **and** there's a sign that something happened:
     - a game sound event in or just after the pause (an explosion, crash, gunshot, hit; ClipKaro's sound hints
       already find these);
     - a reaction right after it (a raised voice, a shout, a laugh, "ye kya hua", "bhai!");
     - a game-over screen (WASTED, FAILED), from item F.

     A camera swing alone, with no sound event and no reaction, is cut like any pause. It uses hints ClipKaro
     already has, so it costs no Claude usage. Measured on the GTA stream: how many of the 117 kept pauses still
     stay, and the takedown before "ye kya ho gaya" must still be one of them.

### M. Clip only part of a video
- **What:** "only the first hour" or "from 20:00 to 1:10:00": only that part is downloaded, written down and clipped.
- **Why:** on 22 November a stream kept recording an hour after you stopped playing.
- **How:** `fetch --from / --to`, plus the words to say it ("only the first hour").

### N. Housekeeping
- Refresh roadmap-v3.md: v2.7.1 is the newest, and items 19, 22 and 13b are done or closed.
- Close the items above.

## 3. Phases and releases (the owner's order, 23 November)

Built on a `v3.0-dev` branch; each step is released as it's done (v2.8, v2.9 …), and when every phase is
finished the whole set is bundled and released as **v3.0**.

| Phase | Release | Items |
|---|---|---|
| **1** | v2.8 | Quick wins: M (part of a video), L (the three limits, with the smarter camera check), H (landscape copy), K (Resolve), J (English streamers), N (housekeeping) |
| | v2.9 | F (boast, then fail; standard and deep) and G (compilations; advanced mode only) |
| **2** | v2.10 | A (review studio, a page inside PostKaro) |
| | v2.11 | B (learn from real views) |
| **3** | v2.12 + | I (silent reactions), E (three or more people), C (B-roll, shared with EditKaro), D (following people who move), then the finishing touches |
| | **v3.0** | everything above, bundled, with a release page |

**Test videos:** the owner sends a video with 3+ people moving around when Phase 3 starts (E, D, C), and an
English-speaking gameplay stream is found for J.

## 4. Decisions (all settled on 23 November 2026)

| # | Question | Decision |
|---|---|---|
| 1 | Order and releases | phases 1–3, v2.8 onward, bundled as v3.0 |
| 2 | A: where the review studio lives | a page inside PostKaro |
| 3 | B: what success means | left to Claude: reach (engaged views), staying (average view %), sharing (per 1,000 views), at day 7, ranked per channel |
| 4 | C: trailers | allowed; no piece over 5 s, longer coverage cut into ~4 s pieces from different parts; channel credited; B-roll only when named at first |
| 5 | D, E: test videos | the owner sends one when Phase 3 starts |
| 6 | F: modes | standard and deep |
| 7 | G: compilations | the owner's topics and Claude's suggestions; up to 1:30 vertical, over 1:30 vertical and landscape |
| 8 | H, K | landscape only when asked (always for compilations over 1:30); Resolve only when asked |
| 9 | J: English streamers | the three-clue solution, tried first, improved after |
| 10 | L3: camera swings | the smarter check |

## Sources

- [YouTube Analytics metrics](https://developers.google.com/youtube/analytics/metrics.md)
- [Roboflow Trackers (Apache 2.0)](https://cdn.jsdelivr.net/gh/roboflow/trackers@develop/README.md), [BoT-SORT paper](https://arxiv.org/pdf/2206.14651)
- [Light-ASD comparison (paper)](https://arxiv.org/pdf/2303.04439v1.pdf), [LoCoNet](https://arxiv.org/html/2301.08237v2), [TalkNet](https://github.com/TaoRuijie/TalkNet_ASD)
- [HSEmotion ONNX (Apache 2.0)](https://github.com/HSE-asavchenko/hsemotion-onnx), [LibreFace](https://github.com/ihp-lab/libreface)
- [Pexels API help](https://help.pexels.com/hc/en-us/articles/900005852323), [Pixabay API docs](https://pixabay.com/api/docs/)
- EditKaro's Resolve research: `~/Desktop/EditKaro/docs/research.md` and `decisions.md`
