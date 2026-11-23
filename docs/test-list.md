# Test list: everything to try before v3.0

The owner tests all new parts together at the end, once every version of the v3.0 plan
([plan-v3.0.md](plan-v3.0.md)) is built (decided 2026-11-23). This list grows with each version: what to
try, how, and what you should see. Tick a box when it works; write a note under it when it doesn't.

Tip: one English gameplay stream with game dialogue and one long Hinglish stream cover most of it.

## v2.8 (quick wins)

- [ ] **Only part of a video.** Paste a long stream and say "only the first hour" (or "from 20:00 to 1:10:00").
  You should see: `fetch` writes down only that part (the transcript's first line says which), and every clip
  comes from it, with times on the full video's clock.
- [ ] **Smarter action pauses.** In a few gameplay clips, watch the quiet moments. You should see: a takedown,
  crash or explosion before a reaction stays in; a plain camera turn with nobody reacting is cut. If too much
  action is cut, say so (`"action_pauses": "keep"` is the v2.7.1 way).
- [ ] **Landscape copy.** Ask "landscape copy" for a clip. You should see: `edited/NN-title-landscape.mp4`,
  1920x1080, the same moment and sound as the standing clip, captions low in the middle, credit and logo in
  their corners. PostKaro still posts the standing clip.
- [ ] **No captions for game characters when the streamer speaks English** (needs an English stream with the
  game's subtitles on). You should see: game characters' lines without ClipKaro captions, every line of the
  streamer and friends with captions. Goal: at least 9 of 10 game lines hidden, no streamer line hidden. The
  first run downloads the text reader (about 10 MB).
- [ ] **Export to Resolve.** Say "export clip 2 to resolve", then in DaVinci Resolve: File > Import > Timeline
  (the `.xml` in `resolve/NN-title/`) and File > Import > Subtitle (`captions.srt`). You should see: the clip
  on V1 in its pieces, its sound on A1, the sound effects on A2 at the right moments, the captions as a
  subtitle track, no "media offline". Try on Fedora (edit copies) and on Windows (no copies).
- [ ] **Word check done.** With `"unsure_words": "ask"` in settings.json, clip a noisy Hinglish stream, fill
  a few answers in `word-check.json` (a right word, a "-"), and say "word check done". You should see: the
  right words in the captions, no caption where you wrote "-", and Claude cuts and edits only those clips again.
- [ ] **Reaction words on frame sheets.** On a computer without an NVIDIA card (Hindi letters in the
  transcript), look at a gameplay frame sheet (`frames/`). You should see: yellow reaction words (in English
  letters) where someone reacts, and "aage" never shown as "AAG".
- [ ] **Setup on Windows and Mac.** Run `python install.py` again. You should see:
  `[ok] rapidocr (game subtitles for English streamers)`, and nothing about a second OpenCV.
- [ ] **Answer:** compilations of 1:30 or less come out vertical only. Is that what you meant? (You wrote
  "keep it on landscape" for the short ones.)

## v2.9 (boast, then fail; compilations)

- [ ] **Game-over screens in the transcript.** Clip a gameplay stream where you die or fail a mission. You
  should see: `fetch` prints `-> game-over screens in ...s: N (WASTED, FAILED)` (about a minute for 4 hours),
  and `transcript.txt` has lines like `[5437.03-5441.53] [on screen: FAILED - THE PHOENIX WAS DESTROYED.]`.
  No false ones (a sign or a menu read as a game over)?
- [ ] **"Boast, then fail" clips (standard mode).** On a stream with a boast and a fail within a few minutes
  ("like a boss" ... FAILED), see whether Claude finds it by itself. You should see: one clip told in a few
  sharp cuts (up to 6), the boast first, the FAILED screen shown whole, the reaction last; and NOT a clip for
  every random death. Also try asking for one: "make a boast-then-fail clip of the Phoenix mission".
- [ ] **Boast and fail far apart (deep mode).** If a boast and its fail are more than about 20 minutes apart,
  the deep pass should find it as a "boast-fail" thread.
- [ ] **A game-over screen is never cut short.** In any gameplay clip that shows WASTED or FAILED, the screen
  plays whole (no pause cut inside it).
- [ ] **Compilation (advanced mode).** Say "advanced mode: a compilation of every glitch from my last 4 GTA
  streams" (or another topic, or ask Claude for topic ideas). You should see: Claude says up front that it
  takes a while, shows the frame sheets it checked (`compile/moment-NN.jpg`), and makes one clip: no silent
  glitch cut out, no jump in loudness between moments, captions and the channel credit as usual. Over 1:30
  there is also `edited/01-...-landscape.mp4`. In quick or standard mode Claude should say compilations are
  advanced mode only.
- [ ] **Compilation from streams with different webcam spots.** Claude should warn that the webcam layout
  follows the first video.

## v2.10 (the review studio in PostKaro 0.9)

Update PostKaro first (`git pull` in its folder, then restart it: `python run.py open` there).
- [ ] **Fix button and Studio tab.** In PostKaro, every clip of a ClipKaro video has a **Fix** button, and the
  **Studio** tab lists your videos and clips.
- [ ] **Start and end.** Open a clip, click an earlier (grey) word under Start, and a later word under End,
  then **Make the clip again**. You should see: the steps tick (cut, edit, quality check), about a minute, and
  the new clip plays from the word you picked to the word you picked.
- [ ] **A caption word.** Click a wrong caption word, type the right one, make the clip again: the caption is
  fixed, the sound is the same. Try "No caption for this word" too.
- [ ] **Framing (a podcast).** On a two-person clip, pick **Both people**, then **Left person**: the whole clip
  shows that.
- [ ] **Emojis, sounds, whooshes.** Switch one emoji, one sound effect and the whooshes off: gone in the new
  clip; switch them back on: back.
- [ ] **Undo last change.** Puts the clip back exactly as before.
- [ ] **Posting after a fix.** Schedule a fixed clip: the fixed version is the one that goes out. A clip
  already uploaded (scheduled on YouTube, not live yet) says to cancel that post first.
- [ ] **Speed.** Is "about a minute" true on your laptop? Note the time it shows.

## v2.10.1 (your own cuts in the Studio, PostKaro 0.9.1)

- [ ] **Cut a part out.** Under **Words**, click a word, "Cut out from here", click a later word, **Make the clip
  again**: that part is gone, the rest plays on (a short flash at the join, as with Claude's joins).
- [ ] **Add a moment.** Use **Find** (words said anywhere in the video) and "The 2 minutes after the clip"; click the
  first and last word, **Add**, make the clip again: the moment plays in its place in time, with captions.
- [ ] **Your own emoji.** Click a word, pick 🔥 (or type any emoji): it shows on that word, even when the clip
  already had 3 of Claude's. Pick one on a word said twice: it shows on the one you clicked.
- [ ] **Your own sound.** Click a word, pick a mood (funny, shock …): the sound plays on that word.
- [ ] **Undo** after all of these puts the clip back.
