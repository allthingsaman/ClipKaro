# What's new

## v2.12 (silent reactions in podcasts, November 2026)

- **A listener's silent laugh is seen.** ClipKaro only heard laughs; now it also reads faces. When the listener
  cracks up or looks shocked without a sound, it's a hint for picking the moment, and the clip shows both people
  then, as it does around a heard laugh. Only strong reactions count. `"silent_reactions": false` turns it off.

## v2.11 (learning from real views, November 2026)

- **How your clips really did** (with PostKaro 0.10): PostKaro reads every live post's numbers back (views, how
  much of it people watched, shares, likes) about 1, 3, 7 and 28 days after it went live, and shows them on
  Posted. Ask Claude **"how are my clips doing?"** for a plain report per channel: the best clips, which lengths
  and kinds do best, and how well ClipKaro's clip score matched reality.
- **The critic learns from your channels**: with 30+ posted clips that have a critic score and a result, the
  clip score's weights move towards what really did well (gameplay and talk videos apart, slowly). It only
  changes the ranking; no clip is ever dropped. `"learn_from_views": false` keeps the fixed weights.
- Each posted clip now carries its critic scores to PostKaro, so learning keeps working after you delete a
  project to free space.
- **One step each to unlock the full numbers:** switch on the YouTube Analytics API in your Google project and
  Reconnect YouTube; Reconnect Instagram and Facebook (read-only permissions). Until then: views, likes and
  comments.

## v2.10.1 (your own cuts in the Studio, November 2026)

- **Make your own cuts** in PostKaro 0.9.1's Studio: cut a part out of a clip's middle, add a moment from
  anywhere in the video (find its words, or look at the 2 minutes before or after the clip), and put your own
  emoji or sound on any word. Your emojis go first among the 3 a clip can show.

## v2.10 (the review studio, November 2026)

- **Fix a clip by clicking** (with PostKaro 0.9): press **Fix** on a clip in PostKaro, or open its new
  **Studio** tab. Move the start or end to another word, fix or hide a caption word, change the framing of a
  podcast clip, switch an emoji, a sound effect or the whooshes off; press **Make the clip again** and only that
  clip is cut and edited again (about a minute). **Undo last change** puts it back. No Claude usage, nothing to
  type.
- A landscape copy is cut again when its clip changes.

## v2.9 (boast, then fail; compilations, November 2026)

- **"Boast, then fail" clips** (gameplay, standard and deep mode): someone promises to do a mission "like a
  boss", and minutes later the game says FAILED. ClipKaro now reads the game's own game-over screens (WASTED,
  FAILED, BUSTED) from the picture (about a minute for a 4-hour stream) and shows them to Claude, who tells
  such a story in up to 6 sharp cuts, the FAILED screen shown whole. Only when it's funny: the fail must pay
  off something said before it, never just any death.
- **Compilations across videos** (advanced mode only): "a compilation of every glitch from my last 4 streams"
  makes one clip from moments of several videos. You name the topic or Claude suggests some; every moment is
  checked on its frames first (it takes a while); the moments are joined frame-exact with the loudness evened,
  and nothing is pause-cut, so silent glitches stay. Up to 1:30 a vertical Short; longer, also a landscape copy.
- A piece of a clip with nobody talking (a crash, a game-over screen) is now kept instead of left out, and a
  clip never runs past the end of its video.
- The text reader for English streamers' game subtitles is faster (it no longer enlarges every picture).

## v2.8 (quick wins, November 2026): only part of a video, smarter action pauses, a landscape copy, English streamers, DaVinci Resolve

The first step towards v3.0 ([the plan](docs/plan-v3.0.md)).

- **Only part of a video.** "Only the first hour" or "from 20:00 to 1:10:00": ClipKaro writes down and clips only
  that part (`fetch --from / --to`), handy when a stream kept recording after you stopped playing. Every time
  stays on the full video's clock.
- **Action pauses: only where something happened.** v2.7.1 kept every quiet second where the picture changes
  a lot, so plain camera swings stayed too. Now such a pause stays only when something shows it mattered: a game
  sound burst, or right after it a laugh, a shout, a reaction word ("ye kya", "bhaag"), an exclamation ("arre",
  "oye") or a voice much louder than the talk around it. On a 4-hour GTA stream 36 of the 124 kept pauses still
  stay, the police takedown before "ye kya ho gaya" among them (`"action_pauses": "keep"` is v2.7.1).
- **A landscape (16:9) copy, when you ask.** "Landscape copy" keeps the standing clips and adds a 1920x1080 copy
  of each, with the same captions, credit, logo, emojis and sound, for YouTube videos and long compilations.
- **No captions for game characters, also when you speak English.** ClipKaro now reads the game's own
  subtitles on screen (a small English text reader, about 10 MB): a line whose words are in the subtitle area
  while it is said is the game's and gets no caption. Turn the game's subtitles on when you stream. Hinglish
  videos keep their own rule.
- **Finish a clip in DaVinci Resolve (free), when you ask.** "Export to resolve" writes each clip as a Resolve
  timeline: the clip in its pieces, its sound, the sound effects on their own track, and the captions as a
  subtitle file. On Linux it makes copies the free Resolve can read.
- **"Word check done."** With `"unsure_words": "ask"`, your corrections in `word-check.json` are now applied:
  the right words written, "-" for no caption.
- **Frame sheets:** reaction words match whole words only ("aage" is no longer "aag" = fire) and are found in
  Hindi letters too.
- **A bigger webcam in gameplay clips.** The webcam under the game now grows until it is 50 px from the
  sides, 50 px below the captions and 30 px above the bottom (it was 60 / 90 / 30): a 16:9 webcam is 980
  wide instead of 958, a round one 690 instead of 650. `"facecam_margins"` in settings.json changes the
  space (`{"left": 60, "right": 60, "top": 90, "bottom": 30}` is the layout before).
- **The webcam box is the webcam, not a strip of the game too.** When your faces sit low in the webcam,
  ClipKaro could take a line of the game below it for the webcam's border: on a GTA 6 stream the 16:9 webcam
  came out square, half of it game, and your faces shrank to fit. Now a box taller than a webcam picture is
  cut at the webcam's own border (where a 16:9 or 4:3 picture ends, below every face). If a box still looks
  too tall, `cut` warns and saves a picture of it (`frames/facecam-box.jpg`) so Claude checks it.

## v2.7.1 (November 2026): the action stays in, and real usage numbers

- **No pause cut where something happens on screen** (gameplay and streams). Pause cutting goes by the
  sound, so a quiet second with action in it (a takedown, a crash) could be cut out, leaving the shout
  without its cause. Now a pause where the picture changes a lot, for at least half a second, stays in.
  On a 4-hour GTA stream that brought back 107 seconds in 76 of 160 clips (1.4 s a clip on average);
  calm stretches and talk are cut as before, and podcasts are not affected (`"action_pauses": "cut"`
  turns it off).
- **Never a cut inside a word still being said.** A pause is now measured from the end of every word
  before it, so a long, stretched word that runs past a short one is never cut off (clip 21 of the GTA
  stream; normal transcripts are cut exactly as before).
- **Real numbers for time and Claude usage.** [What computer you need](docs/requirements.md) now shows
  times and Claude usage measured on real runs (from Claude Code's own record of every request) and
  worked out per video length for podcasts and gameplay, with advice for small creators. Quick mode
  uses about half of standard; a 30-minute podcast in standard is about 0.6 million tokens.
- The speech model and disk tables list the Hinglish model and the two careful-listening models.
- **Joined clips don't announce it.** A clip made from moments far apart (deep clips) no longer starts its
  caption with "From 3 moments of the full video: ..." or ends its YouTube title with "(3 moments joined)":
  that is for you, not your viewers, so it stays in Claude's report (`"joined_note": true` brings it back).
- **Checked before release.** A review of everything since v2.6 found these, all fixed (none was ever
  published):
  - **Private details:** everyday talk ("the number of people who quit at 25 ... one in two", "मुझे नहीं
    पता") was taken for a phone number and cut out of podcast clips. Now only letters and numbers said one
    right after another count, and it runs on gameplay and streams only (`"private_details": "all"` for
    every video). The real email address and in-game number on the GTA stream are still found.
  - **Careful listening** crashed on clips longer than about 25 seconds; they are now heard in windows of
    under 30 seconds (checked on three 34-58 s clips of the GTA stream).
  - **Live clipping keeps the graphics card for OBS:** careful listening and frame sheets wait while it runs.
  - **"Never flip a nahin"** knows every spelling ("don't", "nahiii", "नहीं"), and a plain respelling
    (nahi -> nahin) is no longer hidden.
  - **Frame sheets on Windows** work when the video's title has Hindi letters, and a failing frame sheet
    never stops `fetch` or `parts`. A game named in a podcast's title no longer turns them on.
  - **Event starts:** no clip grows past 90 seconds, and an event is never shown by two clips.

## v2.7 (November 2026): gameplay with friends, watched and heard carefully

v2.7 brings everything a long gameplay stream with friends on voice chat needed by hand on a 4-hour GTA 6
stream, so "clip this: <link>" now does it by itself. All of the heavier work happens only for gameplay
and live streams; podcasts and talks get the fixes and nothing else (a test checks that).

- **Never censored, bold takes count extra.** Gaali, abuse, dark jokes and offensive opinions are never cut,
  bleeped or scored down; bold, honest takes (an unpopular opinion, a roast, taboo or A-rated talk) earn extra
  with the critic and the readers (`"bold_clips": "neutral"` is the way back). Slurs stay neutral and out of
  titles, with a note when a platform might restrict a clip.
- **Abusive and taboo words written with stars** ("F******") in captions, the .srt and posting texts, while the
  sound keeps every word (`"star_words": false`, or "no stars", writes them in full).

- **ClipKaro watches your gameplay.** In gameplay and live streams Claude's helpers now see the video too: a
  frame every 10 seconds with the loud moments marked, and a closer look where something happens. A clip of
  a crash, a fire or a friend falling off a chair starts at the moment itself, not when the talking about it
  starts. Podcasts and talks are not affected (`"watch_gameplay": false` turns it off).
- **Sound effects start on time.** A slow sound (a trombone, a crowd cheer) used to start up to a few
  seconds before the moment it was for. Now every sound effect starts on its moment, never before it.
- **Careful listening for noisy streams.** Hindi / Hinglish streams and gameplay where several people talk
  over game sound get two more speech models (with an NVIDIA card): Claude's helpers compare all three for
  every clip, fix the words they agree on, and leave words nobody can make out without captions.
- **Private details stay out of clips.** An email address spelled out or a phone number said on stream is
  found and left out of every clip by itself (`"private_details": "keep"` turns it off).
- **Sound effects included.** Setup now downloads a free starter set of 33 sound effects (Mixkit, no credit
  needed) into the mood folders, so clips get a boom, a boing or a buzzer from the very first video. Your
  own sounds are never replaced; `python install.py --no-sounds` skips it.
- **"No limit", and clips that share a moment.** Say "no limit" or "as many as possible" and every good
  moment becomes a clip, however many. In gameplay and streams a funny moment can now come as a short and
  a longer version (or inside a joined clip), so you choose which to post; two clips are never almost the
  same. Podcasts keep one clip per moment. `"overlap_clips"` in settings.json changes that.
- **Streams with friends.** Friends playing along on voice chat now count exactly like you when the
  helpers look for clips: their banter, roasts and stories become clips too.
- **Your friends' Hinglish keeps its captions in gameplay.** Lines like "Kisko khaoon?" or "Main kama loon"
  were taken for a game character and lost their captions. Now only real English counts as the game's, so
  you and your friends on voice chat are captioned and the game characters still aren't. Claude's caption
  check also lists the hidden lines, so a friend's English line can be brought back.
- **Twitch credit and webcams with friends in them.** Clips from a Twitch video now say "© twitch.tv/name"
  (Kick: "© kick.com/name"), so nobody takes it for a YouTube channel; `credit_text` in settings.json
  writes your own words. In gameplay and streams, a webcam with two or three people in it is now found
  by itself, so those streams get the gameplay-on-top, webcam-below layout too (podcasts are left alone).
- **No sound spike at a clip's first moment.** A clip that opened on a loud sound could fail the quality
  check (the sound encoder overshot in the first milliseconds). The sound now fades in over 30 ms at the
  very start; you can't hear it.
- **YouTube's "confirm you're not a bot" on Windows.** Chrome, Edge and Brave on Windows lock their
  saved logins, so "use my Chrome cookies" failed there ("Failed to decrypt with DPAPI"). Now you save your
  YouTube login once as a cookies file with a browser extension and put it in the ClipKaro folder
  ([how](docs/troubleshooting.md#youtube-asks-you-to-sign-in)). ClipKaro uses it by itself, only when
  YouTube asks; most videos still download without it. The error messages now say what to do.
  The README now shows this as an **important note for Windows** right under the install steps.
- **Live clipping: Claude asks for your OBS folder and Twitch channel.** settings.json now ships them as
  placeholders (`"<your OBS recording folder>"`, `"<your Twitch channel>"`). The first time you say
  "start live clipping", Claude asks for both and writes your answers in. A placeholder is never used as a
  real folder.
- **New and renamed guides:**
  - [docs/live-clipping.md](docs/live-clipping.md) (was `docs/live.md`): the whole setup and going live, step
    by step. Now in newer OBS's real places ("Automatically record when streaming" is under Settings →
    General → Output), with the settings that keep pieces clean (no remux copies, the vertical canvas and
    backtrack in a subfolder, the stream on audio track 1) and a table of fixes.
  - [docs/streaming-setup.md](docs/streaming-setup.md), new: streaming to YouTube (horizontal and
    vertical), Twitch and Kick at once from OBS with stream keys. The encoder settings for each (H.264:
    Twitch and Kick refuse HEVC), upload speed, and how to check you're really live.
  - [docs/postkaro.md](docs/postkaro.md), new: PostKaro for ClipKaro users. Install, opening it with its
    link, connecting your accounts, default accounts with several Pages or channels, posting every day,
    live clipping, fixes.

## v2.6 (November 2026): live clipping

v2.6 clips your stream while it is still running, for game launches like GTA 6. Normal clipping is
unchanged. Checked in a rehearsal: a recorded stream was fed in as OBS-style 10-minute pieces, and
a piece went from finished to posted (a dry run: nothing went online) in about 9 minutes. The first
real stream is the owner's GTA 6 launch stream.

- **Live clipping: clips posted while you stream** (for game launches like GTA 6). OBS records in pieces
  of 10 minutes; ClipKaro writes down each finished piece, adds what your Twitch audience did (chat going
  wild, the clips viewers made) as hints, and every 10 minutes a helper picks 0-2 clips per piece, cuts,
  edits and posts them at once to YouTube Shorts, Instagram Reels and your Facebook Page through
  PostKaro (no review step: your choice for live streams; a clip that fails the quality check is never
  posted). While it runs, ClipKaro's heavy steps give way to OBS. `"live_post": "dry"` makes a test
  stream post nothing. How to set it up: [docs/live-clipping.md](docs/live-clipping.md). Normal clipping is unchanged.
- **The live clipping guide** ([docs/live-clipping.md](docs/live-clipping.md)) has the whole flow as a chart and explains
  where the video comes from: your own OBS recording, never a download (Twitch only adds hints).
  The OBS setup now includes "Automatically record when streaming" (streaming alone records nothing).
- **README:** live clipping is explained at the top, with a link to the guide.
- **PostKaro 0.6.0:** `post-now` posts every clip of a piece on every connected platform at once (what
  live clipping uses); `--dry` only lists what it would post.

## v2.5 (November 2026): Windows and Mac, checked

v2.5 closes everything planned before the major update (v3.0): ClipKaro and PostKaro now install and
run the same way on Windows, Mac and Linux. Checked by reading the code and the steps, and by tests on
Linux; the first real run on a Windows PC or a Mac is still to come (roadmap item 22).

- **Windows and Mac, checked.** The install steps and the code were checked for both, together with
  PostKaro (0.5.0):
  - **Mac:** Homebrew's `python` is now 3.15, too new for the speech engine, and its plain `ffmpeg` can't
    draw captions. The steps now say `brew install python@3.13 ffmpeg-full`, and ClipKaro and PostKaro
    find `ffmpeg-full` by themselves (Homebrew keeps it off the PATH).
  - **Windows:** project folders named after a Hindi title work: pictures are read and written in a
    way that understands Hindi letters, videos are opened through FFmpeg, and caption files get
    English-letter names. Keep ClipKaro out of OneDrive-synced folders (the docs say why).
  - **Setup** stops at once, with the command to fix it, on a Python the speech engine can't use (3.15,
    or 3.14 on an Intel Mac), and makes `.venv` again if it was made with one.
  - **PostKaro** on all three systems: setup steps for each in both READMEs, "install PostKaro too" for
    the AI helper, UTF-8 output for Hindi titles, and ffmpeg found for thumbnails (also for the Mac
    login item).

## v2.4 (November 2026): your brand on every clip

v2.4 puts your logo, your outro and a credit to the source on every clip, notes gameplay action
even when nobody is talking, and makes the caption check spell names and numbers right. The README
now says which AI helper you need and how ClipKaro compares with Opus Clip inside Claude. The owner
reviewed the brand kit on a real gameplay clip before release.

- **Action without talking isn't missed anymore.** A game explosion or big action on screen was noted
  only on a line someone was speaking; in a stretch of pure gameplay the note was lost (37 of 58 in
  three test streams). Now it gets a line of its own in what Claude reads, "(no talking) [big action on
  screen ~6 s] [explosion]", so a clip can keep your setup, the action and your reaction together. A
  note now goes on the line that covers most of it, so action you talk over stays on your line.
- **Your brand on every clip.** Put your logo and a 3-5 s outro (9:16) in the new `brand` folder: the
  logo goes in the bottom-right corner of every clip, the outro after it. No intro, so a clip still
  opens on its hook. An outro longer than 10 s is left out, so it is never longer than the clip.
- **Credit to the source.** Clips made from a YouTube link get a small "© Channel name" in the
  bottom-left corner (never your own video files). `"source_credit": false` in settings.json turns it off.
  A logo on a plain black or white square gets the square removed by itself.
  Both sit right in their corners at 70 % opacity; `"logo_corner"` and `"credit_corner"` choose another
  corner (top-left, top-right, bottom-left, bottom-right).
- **The caption check knows more** (standard and deep mode): names of games, characters, people and
  brands spelled right, and numbers said in words written as digits where they are amounts, years or
  scores ("do hazaar tera" -> 2013, "paanch lakh" -> 5 lakh), never where they aren't ("ek din" stays).
- **Which AI helper you need**, in the README: Claude Code (Pro or higher), Google Antigravity (it has
  a free plan), or another agent that can work on your computer; Claude's free chat can't run it.
- **ClipKaro or Opus Clip inside Claude?**, in the README: with Opus Clip's Claude connector, Opus Clip
  makes the clips (a paid Opus Clip plan and credits, no Hindi); with ClipKaro, your AI helper is the editor.

## v2.3 (November 2026): cleaner captions, smarter picks

v2.3 makes the captions more correct and the picks smarter, and you still don't have to ask for anything:
- Hindi and Hinglish videos are written down by a speech model trained on Hinglish: on public tests it
  got half as many words wrong;
- skipped words are heard again;
- Claude checks every clip's captions for misheard words (standard and deep mode);
- game characters' lines get no captions in gameplay (the game shows its own subtitles);
- Claude reads hints from the sound and picture (a raised voice, an explosion, big action, game
  characters);
- no clip ends on a flash of another shot.

The README now shows the real video next to the clip ClipKaro made, and explains the three modes:
Quick (basic), Standard and Deep (advanced). The owner reviewed every part on the test videos before
release.

- **It hears what the words can't show.** Claude now reads short notes next to the words:
  - `[voice raised]` and `[shouting]`: the line is higher and louder than that speaker's own normal
    (a podcast rarely gets one, which is right: a hint has to be sure);
  - `[explosion]`, `[gunfire]`, `[crash]`: game sound bursts;
  - `[big action on screen ~4 s]` in gameplay: where the game picture moves most;
  - `(other voice)` in gameplay: a line a game character says, not the streamer. On two test streams,
    those lines were 75 % English words (the game's characters), the streamer's 15-20 %.

  They show where to look; the words decide, and no note never counts against a moment. `"hints":
  false` in settings.json gives the plain transcript. `run.py hints <project>` adds them to older videos.
- **A Hinglish speech model for Hindi and Hinglish videos.** With an NVIDIA card, Hindi and Hinglish
  videos are now written down by a Whisper model trained on Hinglish (Whisper-Hindi2Hinglish-Prime): on
  public test sets it got 21 % of Hinglish conversation wrong where the old model got 50 %, and 19 % of
  everyday Hindi against 34 %. It writes straight in English letters (ClipKaro turns its textbook
  spellings like "nahin" into "nahi"), so Claude reads about 40 % fewer tokens and spells far fewer
  words; transcribing takes about 1.3x as long. It hears speech in short pieces (in long windows it could
  loop). English videos keep large-v3-turbo. `"hinglish_model": "large-v3-turbo"` goes back.
- **No captions for game characters.** In gameplay with a Hindi or Hinglish streamer, the game's own
  subtitles already show its characters' lines, so ClipKaro's captions now show only the streamer (the
  game lines keep their sound, and a great game scene can still be in a clip). `"game_voice_captions":
  true` captions them too.
- **Claude checks the captions** (standard and deep mode). Before cutting, Claude reads every clip's
  captions like a viewer (`run.py captions`) and fixes clear mishearings: "sorry" written as "saari", a
  wrong name, a word bent by an accent. Quick mode skips it to save your Claude plan.
- **The hints passed their first blind test.** On a GTA stream, clips picked with and without hints
  matched 6 times out of 8; of the 2 that differed, the owner preferred the hints version both times.
- **Your microphone on its own track.** OBS can record the microphone and the game on separate audio
  tracks. ClipKaro now notices that and writes down your words from the microphone alone; the clips keep
  the full sound. (Research for this release found that separating a voice from a mix afterwards makes
  speech recognition worse, so a mixed recording is left as it is and the voices are told apart instead.)
- **Skipped words heard again.** Whisper sometimes skips a few words and stretches one word over their
  time ("बिटे पावर में" where Khan Sir said "पावर तीन-तीन के पास है, ब्रिटेन के पास है, फ्रांस के पास
  है, अमेरिका के पास है, पावर में"). Those stretches are heard again; the new words are kept only when
  they add real words and keep the old ones. `run.py relisten <project> --stretched` for older videos.
- **No flash of the next shot at a clip's end.** 12 of the 106 test clips showed a few frames of
  another camera as they ended. The clip now ends just before that cut, or holds its last frame while the
  last word ends; a split screen never switches for a split second at an edge. All 12 were re-made.
- **A speech-model test with checked texts.** `run.py asr-bench public` downloads two public test sets
  (Hinglish conversation and everyday Hindi, with every right spelling listed) to compare speech models
  fairly. Models can be one folder of a repo (`owner/repo:int8`); `--compute int8_float16` for a big one.
  First result: a Hinglish fine-tune of Whisper (Hinglish-Prime) got 21 % of Hinglish conversation wrong
  where today's model gets 50 %, and 19 % of everyday Hindi against 34 %. Not switched yet: the owner
  checks it by ear first (roadmap 9b).
- **`relisten --current`** hears unclear stretches of the transcript as it is now, keeping caption fixes
  and every hidden word hidden.
- **Tests from start to end.** `run.py test --full` runs a tiny made-up video through cut, edit and qa.
- **Instagram and Facebook texts for the 64 older test clips**, so every clip has its own text per
  platform.
- **A README that shows it**: the real video next to the clip ClipKaro made, for deep clips, two
  people, gameplay and caption placement (`docs/media/`).

## v2.2 (November 2026): a cleaner, tighter edit

v2.2 makes every clip look and sound more finished, without you asking for anything:
- pauses and "um"s are cut out;
- made-up words get no captions;
- captions stay off faces and clear of the apps' buttons;
- a few strong words get an emoji;
- no sound peak goes over the limit;
- code checks every clip before you see it.

Editing is also about twice as fast on an NVIDIA card. Six caption looks and a hook title are there
when you name them.

The owner watched all 106 clips of the 13 test videos with these features before choosing what is on
by default (2026-11-14):
- **In every clip:** pause cutting, no captions on made-up words, captions off faces and the apps'
  buttons, and the sound-peak limit.
- **Emojis** too, unless you say "no emojis".
- **Only when you name them:** the hook title and the other caption looks.
- **On hold:** background music.

Nothing v1.1 could do was lost: [docs/since-v1.1.md](docs/since-v1.1.md) lists every change.

- **No made-up words in the captions during laughter, noise or loops.** Whisper invents words where
  nobody speaks clearly. Those now get no captions:
  - shaky words during a laugh, and "ha ha" / "हा हा" written out;
  - "झाल", a word Whisper writes for game sounds and music;
  - made-up loops like "कर दो कर दो कर दो";
  - the long tail of a phrase repeated 8 or more times.

  Real repetition ("let's go, let's go, let's go") keeps its captions. English videos are not
  affected; gameplay videos lose captions on about 1% of words, the ones that were wrong.
  `fetch` does it by itself; `run.py tidy <project>` applies it to older videos.
- **Editing is about twice as fast.** The NVIDIA card's video encoder does the encoding (3x faster
  than the processor at the same picture quality), and two clips are edited at once when the computer
  has the memory for it. Four clips: 160 s before, 85 s now. Files are about 1.3x bigger. Computers
  without an NVIDIA card encode as before. `"encoder"` and `"render_workers"` in settings.json.
- **Every clip checked before you see it.** `run.py qa` checks each finished clip: Hindi letters left in
  Roman captions, captions outside the safe zone, a word cut in half, the loudness, black frames, a
  stale edit (fix first), and a caption over a face, a frozen picture or a flash at the end (look at
  it). Claude fixes what fails before showing you. Tried on all 106 clips of the 13 test videos
  (2026-11-13): it found 3 clips with sound peaks too high and a caption on a head in a split screen
  (both fixed); now 0 to fix. A face is checked every half second, a hand or a mic is not a
  face, and a text card on black that is in the video itself is only for a look.
- **Tests that protect v1.1.** `run.py test` runs ClipKaro's own checks in under a second: v1.1's
  captions, zooms and cuts with the upgrades off, and every upgrade since.
- **Caption looks.** Besides the classic look: `box` (on a dark box), `karaoke` (each word fills with
  colour as it's said), `minimal` (smaller, normal case), `bold` (big Anton letters) and `comic`
  (tilted comic letters). Say "box captions", or set `"caption_look"` in settings.json.
- **Emojis on strong words.** Claude adds up to 3 per clip (💰 on "paisa", 😱 on a shock). They pop in
  above or beside the caption when the word is said (in gameplay beside it first, because the game's own
  subtitles sit just above), and are left out rather than put on a face.
  `"emoji": false` turns them off.
- **Background music, your own: built, but on hold.** It doesn't suit podcasts, so clips get no music
  for now (`"music": true` in settings.json switches it on). Tracks go in the `music` folder, one
  folder per mood; they play about 10 dB under the voice. ClipKaro ships no music.
- **Sound effects by mood, your own.** Put sounds in the `sounds` folder, one folder per mood
  (attention, shock, fear, funny, sad, hype, reveal, fail, money, or your own), or say "add this sound
  as shock: <file>" (`run.py sfx add`). Claude marks the moments that call for one, a boom on a shocking
  line, a boing on a punchline, and the sound's loudest point lands right there, under the voice.
  Without your sounds, nothing changes.
- **Pauses cut out, in every clip.** Pauses of half a second or more inside a clip are shortened to a
  natural 0.2 s and "um" / "uh" are cut out (about 6 % shorter on average). Laughs are never cut; in
  gameplay only pauses up to 2 s. Every word stays.
- **A hook title, only when you ask.** Say "hook title": every clip opens with a big 3-6 word title on
  a box in the video's accent colour for the first 2-3 seconds ("PAKISTAN KA PM BANOGE?"), in the
  upper part of the picture, never on a face. `"hook_title": true` turns it on for every clip.
- **Captions clear of faces and app buttons.** Captions keep out of TikTok's like and share column
  and the apps' top and bottom bars, and move to a free line in a close-up where they would cover a
  chin. `"safe_zones": false` puts them back on one fixed line.
- **No "…" in captions.** Trailing-off marks ("like...", "हाग…") are no longer shown.
- **No more sound peaks over the limit.** Three clips of the test videos peaked at -0.6 to +0.3 dB, where
  the apps' own processing can crackle: the loudness step overshoots on sharp sounds, and the AAC encoder
  adds 2-3 dB of peak to harsh phone-mic sound. Now a limiter holds the mix at -2 dB, the encoded sound
  is measured, and if it's still over -1.2 dB the limiter goes lower and it's encoded again. The
  loudness stays the same.
- **Podcasts keep their speaker framing when cut again after a clean-up.** A project that kept only
  its video (the audio files deleted to save space) lost the speaker crop and split screen when cut
  again. `cut` now makes the voice track again from the video, in a few seconds.

## v2.1 (November 2026): just say "clip this"

v2.1 needs fewer words from you and gives more back. Say "clip this video". ClipKaro then works out
the rest by itself: what kind of video it is (a live stream? gameplay?), how many clips to make, and
for long videos whether you want deep clips (it asks you once). If you want to save your Claude
plan, add the word "quick". Clips that weren't cut are kept, so you can ask for more later. Game
voices get the right captions more often.

Every change is checked against v1.1, the first stable version: nothing v1.1 could do was lost, and
each change is listed in [docs/since-v1.1.md](docs/since-v1.1.md). The pieces were tested on the
owner's own videos: two GTA live streams, the Khan Sir podcast, an anime video and the rest of the
test bench. Not measured yet: how much of the Claude plan quick mode really saves (roadmap item 3b).

### Just say "clip this"
- **Three modes: standard, deep and quick.**
  - *Standard* is the default.
  - *Deep* adds deep clips: ask for them, or say yes to the one question for long videos.
  - *Quick* runs only when you ask ("quick clip this", "use fewer tokens"). Claude then picks the
    clips alone, like v1.1, and uses much less of your Claude plan.
  - Every other upgrade works in all three modes.
- **One question for long videos.** For a video longer than 21 minutes, Claude asks once at the start
  whether you want deep clips too, while the video downloads. `"deep_clips": "always"` or `"never"`
  in settings.json stops the question.
- **The number of clips follows the video's length.**
  - Every good moment becomes a clip: 3 to 8, as before.
  - Long videos get more: up to about one per 7 minutes of real video, at most 20 (`max_clips`).
    A 2-hour stream no longer stops at 8.
  - "At least 10", "at most 5" or "give me 8" in your message always wins.
- **Live streams and gameplay are recognised by themselves.**
  - It knows a live stream when YouTube says so, or when a "Be right back" screen sits in the
    middle. It knows gameplay from the Gaming category, or a webcam in a corner.
  - "Starting soon", "Be right back" and stream-ending screens are left out: a still picture for 30
    seconds or more with nobody on the webcam. Pause menus where you talk on cam stay in.
  - Streams get their own rules: clips are built around what you say, quiet stretches are normal,
    and "hello chat" or "is the audio OK" stay out of clips.
  - On a 1:40 GTA stream it found all three break screens in 28 seconds.
- **The video downloads while the audio is transcribed**, so cutting starts right away. `fetch
  --no-video` keeps the old way.
- New commands: `run.py info` (a quick look before downloading) and `run.py kind` (live stream?
  gameplay? break screens?).

### More clips, ranked fairly
- **More clips later.** The critic scores every clip idea in a video (often 15 to 30), and only the
  best are made. The rest are now kept. Days later, say "3 more clips from the Khan Sir video" (or
  "clips 9-12 too"), and the next ones become clips in a few minutes, without reading the video
  again. The Khan Sir podcast had 18 such ideas, the best scoring 7.1/10. `run.py more`; `post`
  tells you how many are waiting.
- **The critic judges craft, never the topic.** It looks at how a clip starts, whether it makes sense
  alone, how it ends and what could be cut. A clip about politics, religion or anything controversial
  gets the same scores as any other. What to post is always your choice.
- **Repaired clips keep their place.** The repair round's second look can no longer push a trimmed
  clip below its own original (scores wander between runs). `cut --check` no longer warns about
  those repairs.

### Captions
- **Game characters' English is caught more often.**
  - The old check missed a whole English game line, written as Hindi-letter nonsense, when your own
    clear words came right after it. It now finds the unclear core first, and it still catches
    everything the old check caught.
  - Before turning a line into English, ClipKaro makes sure it isn't your Hinglish being
    *translated* ("usko ghar jaana hai" must not become "I have to go to his house").
  - A line that can't be heard well in either language gets no captions.
  - Listening again is faster: Whisper gets only those few seconds, not the whole video each time.
- **Fix a caption word everywhere**: `run.py fixword <project> "bow" "boat"`, or just tell Claude.
  It changes the word wherever it was heard, keeps the timing, and names the clips to make again.

### Editing
- **Fewer zooms when the camera cuts fast.** A camera cut that comes soon after the last zoom change
  now only follows the new face. One anime clip went from 48 zoom changes in 68 seconds to 28.
- **Editing again works without the original video** once the caption colours are saved, so clips
  of videos whose source was deleted can still be edited.

### Posting
- **Fuller YouTube titles.** Each one uses up to 100 characters: the hook, then the game, show or
  person it's about, then 2-3 matching hashtags ending in #Shorts. For example: "Final Boss Yahin La
  Diya, Mar Gaya | Black Myth Wukong Hindi Gameplay #BlackMythWukong #Shorts". Instagram and Facebook
  texts stay as they were.
- **Deep clips' YouTube titles** end with "(2 moments joined)". The description and the captions
  still start with "From 2 moments of the full video: ...".
- **PostKaro gets the honesty note.** When one of the three honesty judges objected to a deep clip,
  post.json passes that judge's reason on to PostKaro.

### v1.1 stays the baseline
- [docs/since-v1.1.md](docs/since-v1.1.md) lists every change since v1.1 as an upgrade, as different
  on purpose (with the way back), or as costing more. From now on every change must be an upgrade to
  v1.1.
- The Opus Clip comparison is updated for v2.1: [docs/roadmap-v2.md](docs/roadmap-v2.md). What's
  next, in order: [docs/roadmap-v3.md](docs/roadmap-v3.md).

## v2.0 (November 2026): deep clips, a second opinion, tighter cuts

The biggest update so far. In the owner's blind comparison with v1.1 on five fresh videos (21 pairs),
v2 found more postable moments (v2 3, v1.1 1, "post both" 6), every deep clip was postable and none was
misleading, and after the tight-cut fix the two cut the same moments equally well (1-1, 6 ties).
Transcribing takes the same time and GPU; choosing clips takes a few minutes longer and uses more Claude
(a long podcast with deep clips: about 30 minutes of picking and roughly 10x v1.1's Claude usage).
Deep clips are only made when you ask for them.

### Long videos are read in parts (deep clips, phase 1)

- **Long podcasts get read properly.** A video of more than about half an hour is split into parts
  of about 21 minutes (with 2 minutes of overlap, so no moment falls into a gap), and one AI reader
  per part works at the same time. Before, a 2-hour transcript was too big for the AI's file reader
  in one go, and long reads got skimmed. On the 2-hour Khan Sir podcast the candidates now spread
  evenly over the start, middle and end of the video.
- **A topic map** (`topics.txt`): every topic with its time, what it's about, its key lines and how
  they were said (own view, quote, joke, impression), YouTube's "most replayed" peaks and the lines
  the creator used in the cold open. It's the base for deep clips (stories spread across a video).
- **Exact times, real words.** The readers quote words; code finds them in the transcript and takes
  the exact times from there, so no time is guessed and no word is paraphrased.
- `fetch` keeps the video's description, the creator's chapters and the "most replayed" curve.
- **Very long videos no longer crash the computer.** Transcribing a 3-hour Hindi podcast used about
  7 GB of memory at once, and on a 16 GB laptop the system closed programs to survive. Audio longer
  than 30 minutes is now transcribed in pieces of about 20 minutes, cut in pauses, so memory use
  stays the same for any length. Shorter videos are transcribed exactly as before.
- **Podcasts with faces in the wall art show the right person.** In a podcast with painted faces on
  the wall behind the guest, ClipKaro measured a painted face instead of the guest and showed the
  listening host whenever the guest talked. It now looks only at the biggest face on each side.
  Clips cut before this fix are measured again automatically the next time you run `cut`.
- **Dark studios: camera cuts are found again.** In a podcast filmed against a black background
  (like the Sam Altman interview), the cut detector found no camera changes at all, so the crop
  stayed in one place for a whole clip, sometimes on the empty space between two people. Cuts are
  now found by comparing each frame with the frames around it. Bright videos get the same cuts as
  before.
- New commands: `run.py parts` and `run.py topics`. New rules in the picking guide: "Never change
  what someone meant" for clips joined from several pieces.

### Deep clips, phase 2: a second opinion before cutting
- **The critic.** Before anything is cut, a second AI editor checks every clip idea, three times,
  each time in a different order and without knowing who picked it or what score it got. Two
  checks are pass or fail: would a stranger understand the clip on its own, and does it end with
  its payoff (not just before it)? Then it scores the hook, the payoff, the feeling, how shareable
  it is and whether it has a line worth quoting. All ideas are ranked by their **clip score** out
  of 10, with reasons that quote the clip, and the best ones are used. A failed check becomes a
  note for the repair round, never a reason to throw a clip away: in the blind check, every clip
  the critic would have dropped was one the creator would post. The score compares the moments of
  one video and is not a prediction of views.
- **Short videos too:** Claude now writes a shortlist of about twice the clips you want, and the
  critic picks the best of them.
- **Every video gets sound hints**, not only popular ones: right after transcribing, ClipKaro
  listens for laughs, applause and two people talking at once (about 30 seconds for a 3-hour video).
  The readers get a short list of lively moments to check, and the critic sees marks such as
  "[laughter ~2 s]" in the text, so a joke that's funny because of how it's said isn't missed. A
  calm video loses nothing: the marks only ever help.
- **The creator's teaser and "most replayed":** when the creator's own cold-open teaser, or the
  YouTube "most replayed" graph (only popular videos have one), points at a moment nobody picked,
  that stretch is read again carefully. Those hints never rescue a weak clip; they only decide
  between two clips that are nearly equal.
- **A repair round:** like an editor after notes, Claude fixes the top clips that have a note (a
  teaser without its answer, an unnamed "he", a slow start) and lets the critic judge them once
  more. In testing, two pairs of pieces with such notes became a video's two best clips.
- **False starts:** `cut --check` now also warns when a clip may open with a restarted phrase
  ("1992 se leke, 1992 peak ho gaya"), so it can start at the second take.
- **Things to check before posting:** the critic flags claims that look wrong (`check-facts`) and
  misheard words that would look wrong in the captions ("farts" for "fads"), which Claude fixes
  before cutting. Neither changes a score.
- Every clip idea's scores are saved in `output/clip-log.csv`, so the critic can later be tuned to
  what you keep and post.
- New commands: `run.py sound` and `run.py critic`.

### Deep clips, phase 3: one story from moments far apart
- **Ask for it:** "deep clip this: <link>", "clip this, then go deeper" or "do a deep pass on
  <video>". The regular clips are made first, exactly as before; without these words nothing
  changes.
- **What it makes:** a short that joins 2-3 moments that are far apart but belong to one story: a
  question and its own answer 40 minutes later, the narrator's opening line and the story's
  payoff. The pieces always play in the order they were said.
- **Only when it's better:** every deep clip is scored by the blind critic next to the best
  single stretch around the same payoff. If one stretch tells the story as well, the deep clip is
  dropped. "No deep clip" is a normal answer.
- **Only when it's honest:** three separate AI judges (a rules checker, one who speaks for the
  person in the clip, and a viewer who then watches the full video) read each piece inside its
  original minutes, and everything cut between the pieces. If two or three of them say "fail" or
  "not sure", the clip is dropped, whatever its score. If only one does, the clip is kept and
  Claude shows you that judge's reason, so you can look before posting. Tested on 56 clips the
  judges had never seen, about half of them made to mislead: all 29 misleading clips were caught,
  2 of the 27 honest ones were dropped, and 1 was kept with a note.
- **Joins are visible:** where a clip skips more than 20 seconds, a short white flash shows the
  jump, and the posting caption starts with "From 2 moments of the full video: 35:30 · 1:03:01"
  plus the full video link.
- New commands: `run.py deep` and `run.py honesty`.

### Deep clips, phase 4: smoother joins and a repair round
- **Joins sound smooth.** Where a clip is joined from pieces, the sound now fades out and in only
  in the quiet between words, a little longer where the video jumps in time (the background sound
  changes there), so a join never clicks and never clips a word. Clips of one piece sound exactly
  as before.
- **A jump is heard, too:** a soft whoosh plays with the white flash where a clip skips more than
  20 seconds.
- **Optional time label:** ask for it ("show how much time was skipped") or set
  `"jump_label": true`, and a small "27 MIN LATER" appears for a moment at each jump. Off by
  default.
- **A second chance for deep clips:** when the honesty judges reject a deep clip for something a
  few seconds would fix (a "but..." cut off, an answer without its question), Claude repairs it once
  and it is scored and judged again from scratch. Tested on the Khan Sir podcast: a rejected clip came back, passed, and is now that video's one deep clip (with a note from one judge).
- **One more check for joined clips:** `cut --check` warns when a later piece starts on "he",
  "that", "वो" or "haan", which may point at (or answer) words that were cut out.
- Fixed: the deep pass now prints its warnings (it only counted them).

### Tighter cuts, and game voices captioned right
- **Tighter cuts.** In the owner's blind comparison, where both versions cut the same moment, the
  tighter cut won 8 of 8: the new version had made 7 of them longer. Now the second-opinion critic
  also marks dead weight (a slow lead-in, after-thoughts at the end, a detour inside a long answer),
  and the repair round starts on the hook, ends on the payoff and cuts detours out. Every second kept
  must carry something.
- **Game voices.** In a gameplay video transcribed as Hindi, a game character speaking English came out
  as Hindi-letter nonsense in the captions. Unclear stretches are now heard again: clear English
  replaces the nonsense ("…he may yet rise again"), and anything still unclear gets no captions
  instead of wrong ones. `run.py relisten <project>` fixes videos transcribed before.
- Fixed: caption fixes made before the deep pass broke its quotes; the deep pass offered a repair for a
  story that already had a kept clip.

### A [noun] for "this movie"
- When a clip says "इस movie" or "he" and never names it, Claude adds the noun in brackets to the captions
  right after the first mention: IS MOVIE [RAMAYANA] KA (clips.json `clarify`; brackets mark an editor's
  addition). It can be added after cutting: edit the clip again.

### Captions always fit the frame
- **No more captions cut off at the sides.** Some captions ran out of the frame: a whole line stuck in
  one caption (a misheard phrase fixed as one entry, or a Hindi word whose Roman spelling is several
  words), or a group of long words. Caption lines are now measured with the real font and kept at
  most 940 px wide; one very long word (like MISUNDERSTANDING) is shrunk just enough to fit. Out of
  6,698 captions in 30 test videos, none is wider than the frame any more.

### Posting: ready for PostKaro
- **Text for each platform.** Every clip now gets its own posting text for YouTube (a title of up to
  100 characters plus a short description), Instagram (a caption with at most 5 hashtags, Instagram's
  limit) and Facebook, instead of one caption for all.
- **Fixed: long videos lost their captions.** On long podcasts most clips had no posting caption
  (for example 1 of 7). Every clip now gets one, deep clips included (they start with their "From 2
  moments of the full video" line).
- **`run.py post <project>`** writes `post.json`: the finished clips with each platform's text. If PostKaro
  (the separate posting app) is installed, it prints a **"Post them"**
  link that opens PostKaro with every clip filled in. Without PostKaro nothing changes.

## v1.1 (November 2026): better framing

### Podcasts with two people on screen
- **The person talking is shown.** When two people sit too far apart for one standing crop (a
  side-by-side picture or a wide shot of the room), ClipKaro now listens to who is talking and
  shows that person. Before, it showed the bigger face, which was often the listener.
- **Laughs show both people.** From about 2 seconds before a laugh (the punchline) to 2 seconds
  after, and when both talk at once or go quickly back and forth, both people are shown one above
  the other (a split screen). The person who talks most sits on top, with the captions in between.
- **Wide shots of the room** show both people, unless one person talks alone for a long time.
- **It never guesses a face.** When it can't tell who is talking, it shows both.
- **The AI editor checks it.** A silent laugh or an "impressed" face can't be heard, so the AI
  editor looks at picture sheets (`run.py frames`) and adds a split screen there.
- Tested on 9 hand-checked podcast clips: the ideal framing 83% of the time, an acceptable one 91%,
  the wrong single face 1%.

### Show what matters
- **`show_full`**: when someone holds up a product or points at a screen outside the crop, that
  stretch shows the whole landscape picture over a blurred background, without zooming in.
- **`framing`**: the AI editor (or you) can choose what any stretch shows: the face on the left or
  right, the centre, both people (`split`) or the whole picture (`full`).
- **`run.py frames`**: picture sheets of what the crop keeps, with hints where something moves
  outside it or the words point at something ("ye dekho").
- **Inserts inside a shot** (a photo or clip the cut detection missed) now get their own framing,
  so their text isn't cut off.

### Smaller fixes
- One person who leans or laughs is no longer mistaken for two people.
- Captions never cover a face when the picture switches to or from the split screen.
- No more one-frame caption blink, no blended double frames at camera cuts, and zoom changes land
  on the exact frame of a cut.
- Subtitle (`.srt`) files no longer start with a broken negative time.

### Setup
- `python install.py` adds `sherpa-onnx` (it hears who is talking). If it can't be installed, all
  else still works and podcasts keep the simpler framing. Three small models (about 50 MB) are
  downloaded the first time a podcast needs them.
- Everything that worked before works the same: shots with one person, slides, gameplay with a
  webcam and the `--horizontal` option are framed as in v1.0 (apart from the inserts above).

## v1.0 (November 2026): first public release
Clips from YouTube links and video files: transcription with word timings (NVIDIA GPU or CPU),
moment picking by the AI editor, Hinglish captions in English letters, face-centred 9:16 cuts,
the gameplay webcam layout, zooms, word-by-word captions and sound effects.
