# Since v1.1: every change, checked against v1.1

**v1.1 is the first stable version of ClipKaro**: the one that satisfied its owner. So every
change after it must be an **upgrade**. Nothing v1.1 could do may be lost or made harder. When a
change does something differently from v1.1, it must be because the owner wanted it, and if it is
a matter of taste, there must be a way to get v1.1's behaviour back.

This page lists every change since v1.1 and checks it against that rule. **Each new change gets
its line here, in the same commit.** Released so far:
- **v2.0** (2026-11-11): the lines marked v2.0;
- **v2.1** (2026-11-13): the lines dated 2026-11-12 and 2026-11-13 without a v2.2 mark;
- **v2.2** (2026-11-14): the lines marked v2.2;
- **v2.3** (2026-11-16): the lines marked v2.3;
- **v2.4** (2026-11-17): the lines marked v2.4;
- **v2.5** (2026-11-17): the lines marked v2.5;
- **v2.6** (2026-11-17): the lines marked v2.6;
- **v2.7.1** (2026-11-21, published together with v2.7): the lines marked v2.7 and v2.7.1.

**The marks**
- ⬆ **Upgrade**: v1.1 does this too, and now it's better; or it's new and changes nothing
  unless you use it.
- ↔ **Different on purpose**: it works differently from v1.1 because the owner asked for it or
  chose it in a blind test. The line says how to get v1.1's way back.
- ⚠ **Costs more**: more time or more Claude usage than v1.1.

Checked again for v2.13 on 2026-11-23: nothing removed; three-person shots gain their own framing, two-person
shots are unchanged (their clips measure their signals again once, on the next cut).
Checked again for v2.12 on 2026-11-23: nothing removed; one change on purpose (two-person clips show both people
during a listener's silent laugh; `"silent_reactions": false` is the way back).
Checked again for v2.11 on 2026-11-23: nothing removed. One change is different on purpose: the critic's weights
can be learned from real views (`"learn_from_views": false` is the way back); until `run.py learn` has 30+ clips
with results, nothing changes at all.
Checked again for v2.10.1 on 2026-11-23: nothing removed; only the Studio's own marks behave differently (an
emoji with a second, which only the Studio writes).
Checked again for v2.10 on 2026-11-23: nothing removed or changed on purpose; the Studio only adds (it writes
the same clips.json fields Claude writes), and a clip's `"whooshes": false` only exists when the owner sets it.
Checked again for v2.9 on 2026-11-23: nothing removed. One change is different on purpose: a game-over
screen inside a clip is always shown whole (`"game_over_screens": false` is the way back). The rest only adds
(story clips, compilations) or fixes (a piece without words kept, no clip past the video's end).
Checked again for v2.8 on 2026-11-23: nothing removed. Two changes are different on purpose, each with a way back:
action pauses (only where something happened; `"action_pauses": "keep"`) and English streamers' game lines
(no captions when the game's subtitles show them; `"game_subtitles": false`). The rest only adds (part of a
video, landscape copy, Resolve, word check done) or only asks for it.
Checked again for v2.7.1 on 2026-11-20: nothing removed; the one change to clips (action pauses stay)
only touches gameplay and streams, and `"action_pauses": "cut"` brings v2.7's cutting back.
Checked again after the release review on 2026-11-21: the private-details check, which ran on every video,
now runs on gameplay and streams only, like the rest of v2.7, so podcasts and talks are cut exactly as in
v2.6 again; nothing else reaches a normal video.

Checked again for v2.7 on 2026-11-20: no v1.1 command, option or setting has been removed. Everything new for
gameplay and streams (frame sheets, careful listening, overlapping clips, the two-person webcam finder) stays
off for a normal video, and a test (`NormalVideosUntouched`) keeps it that way.

Checked again for v2.5 on 2026-11-17: no v1.1 command, option or setting has been removed or
changed. Only new ones were added.

---

## Writing down what is said

- ⬆ **Only part of a video.** "Only the first hour" or "from 20:00 to 1:10:00" writes down and clips only
  that part (`fetch --from / --to`), with every time on the full video's clock. Asked for after a stream
  kept recording an hour after the owner stopped playing. Without it, the whole video, as before.
  *(v2.8, 2026-11-23)*
- ⬆ **Long videos no longer crash the computer.** Audio over 30 minutes is transcribed in pieces of
  about 20 minutes. Shorter videos are transcribed exactly as in v1.1. *(v2.0)*
- ↔ **Game voices.** Where a game character speaks English in a Hindi video, v1.1 showed wrong
  captions: Hindi-letter nonsense. Now that stretch is heard again. Clear English replaces the
  nonsense. If it's still unclear, it gets no captions instead of wrong ones. *(v2.0)*
  - Since 2026-11-12 it catches more of these.
  - It also checks that the English isn't a *translation* of your own Hinglish.
  - Way back: none needed, because v1.1's captions there were wrong words.
- ⬆ **No made-up words during laughter, noise or loops.** v1.1 captioned them ("कर दो कर दो कर
  दो", "झाल"). Now they get no captions; clear words said while laughing, and real repetition, stay.
  No "…" in captions either. *(v2.2, 2026-11-13)*
  - Way back: none needed, because those captions were wrong words. The words themselves stay in
    the transcript, and `words-before-tidy.json` keeps the old marks.
- ⬆ **The video downloads while the audio is transcribed** (YouTube links), instead of at the cut
  step, so cutting starts right away. *(2026-11-12)*
  - Way back: `fetch --no-video` downloads it at the cut step, as in v1.1. The disk space is then
    used later.
- ⬆ **Skipped words heard again.** Whisper sometimes skips a few words and stretches the word next to
  them over their time, so those words were missing from v1.1's captions. Each stretched word with
  speech inside it is heard again with two words of context; the new words are kept only when they add
  real words and keep the old ones (on the test podcast: 42 lines repaired). *(v2.3, 2026-11-14)*
  - Way back: none needed, the old words stay unless the new ones add to them. For older videos it is
    `run.py relisten <project> --stretched`, which keeps `words-before-stretched.json`.
- ↔ **A Hinglish speech model for Hindi and Hinglish videos** (with an NVIDIA card). v1.1 used
  `large-v3-turbo` for every language. On public test sets with checked texts, the Hinglish model
  (Whisper-Hindi2Hinglish-Prime) got 21 % of Hinglish conversation wrong against turbo's 50 %, and 19 % of
  everyday Hindi against 34 %. It writes Hindi in English letters, so Claude reads about 40 % fewer tokens
  and spells far fewer words. It takes about 1.3x as long to write a video down. English videos, the
  processor, and Hindi-letter captions keep `large-v3-turbo`. The owner chose it (2026-11-15). *(v2.3)*
  - Way back: `"hinglish_model": "large-v3-turbo"` in settings.json.
- ⬆ **Your microphone on its own track.** A recording with the microphone on a separate audio track
  (OBS can do that) is written down from the microphone alone, without the game's sound and
  characters. The clips keep the full sound. A file with one track works exactly as before. *(v2.3)*
- ⬆ ⚠ **Careful listening on noisy Hindi / Hinglish streams.** With three friends talking over game sound,
  the transcript of a 4-hour GTA stream was badly garbled, and Claude fixed it by hand: a second speech model
  for the readers, two more hearings of every clip, word-check helpers, 583 words fixed and 176 unsure spots
  left without captions. Now it happens by itself for Hindi / Hinglish gameplay and live streams on an NVIDIA
  card: `fetch` adds the second hearing, `parts` hands it to the readers, `run.py rehear` hears every picked
  clip again, the `clipkaro-wordcheck` helpers compare, and `run.py wordcheck` applies the fixes (never one
  that flips a "nahin") and hides the rest. Costs about 6 minutes of graphics card per hour of video, a few
  seconds per clip, and the helpers' Claude usage. *(v2.7, 2026-11-20)*
  - Way back: `"careful_listening": false` in settings.json; `"unsure_words": "ask"` lists the doubts in
    word-check.json for the owner instead of hiding them.

## Choosing the moments

- ⬆ **Three modes: standard, deep, quick.** Standard is the default. Deep adds deep clips when you
  ask or say yes to the question. Quick, only when you ask ("quick clip this", "use fewer tokens"),
  picks like v1.1: Claude reads the video itself, with no helpers and no critic. All three keep every
  other upgrade on this page. *(2026-11-13)* Since v2.3 they can also be called by the README's names,
  "basic mode" (quick) and "advanced mode" (deep), and quick mode also skips the caption check. *(v2.3)*
- ⬆ ⚠ **Long videos are read in parts**, so the middle and the end get the same attention as the
  start. Several AI readers work at once. *(v2.0)*
- ⬆ ⚠ **A second opinion (the critic).**
  - A blind AI editor scores every clip idea three times and ranks them.
  - It never throws a clip away; it only ranks them and gives notes for fixing them.
  - Since 2026-11-12 it judges only how a clip is made, never its topic.
  - Short videos get it too. *(v2.0)*
- ↔ **Nothing censored, and bold takes count extra.** The owner asked for this on 2026-11-19.
  - Gaali, abuse, dark jokes, offensive opinions, taboo talk (sex, cheating) and A-rated moments are
    never cut, bleeped or scored down: not when picking, not by the critic. Gaali may go in posting
    titles too.
  - A bold, honest take (an unpopular opinion, a roast, a rant, a blunt verdict, a dark joke, gaali said
    with real feeling, taboo talk, an A-rated moment) now ranks higher: the critic gives it credit in hook, share and quote, and the
    readers, the live helper and Claude treat it as a strong hook. Before, the critic was neutral both
    ways.
  - A racial or caste slur on its own stays neutral (no points either way), never goes in a title, and
    gets a "platform risk" line in the report. It never stops a clip, live streams included.
  - Way back: `"bold_clips": "neutral"` in settings.json: bold takes are judged like any other moment,
    as before. *(2026-11-19)*
- ↔ **Rude words with stars in the text.** The owner asked for this on 2026-11-19: abusive and taboo
  words are written like "F******" in the captions, the `.srt`, the hook title and the posting texts.
  The sound keeps every word (never bleeped or muted), and Claude and the critic read the real words.
  v1.1 wrote every word in full.
  - Way back: `"star_words": false` in settings.json, or say "no stars" (`edit --no-stars`).
    *(2026-11-19)*
- ⬆ **More clips later, without reading the video again.** The good ideas that weren't cut stay
  saved; "3 more clips from that video" turns the next ones into clips in a few minutes. v1.1 had to
  read the whole video again for that. *(2026-11-13)*
- ⬆ **Repaired clips keep their place.** The repair round judges clips again, and scores wander
  between runs, so a trimmed clip could drop below its own original. Now a second look never costs
  a clip its place, and `cut --check` no longer warns about a repair it made on purpose. *(2026-11-13)*
- ⬆ **Sound hints**: laughs, applause and both people talking at once are pointed out. A calm
  video loses nothing. *(v2.0)*
- ⬆ ⚠ **More hints next to the words** Claude reads: `[voice raised]`, `[shouting]` (higher and
  louder than that speaker's own normal), game sound bursts (`[explosion]`, `[gunfire]`, `[crash]`),
  `[big action on screen]` and, in gameplay, `(other voice)` on lines a game character says. They show
  where to look; the words decide, and no hint never lowers a clip. Kept rare (the clearest few per
  10 minutes). Costs about 2-3 minutes of processor time per hour of video at `fetch`, plus about 4 for
  gameplay (the picture's motion). *(v2.3, 2026-11-14)*
  - Way back: `"hints": false` in settings.json gives Claude v1.1's plain transcript lines.
- ↔ **Tighter cuts.** In the owner's blind test, the tighter cut won 8 times out of 8 where both
  versions cut the same moment. So clips start on the hook and end on the payoff, with dead weight
  cut out. *(v2.0)*
  - Way back: ask for it ("keep the whole answer", "make clip 3 longer"); v1.1's lengths are still
    allowed.
- ⬆ **How many clips.** v1.1 made 3 to 8.
  - Short videos still get 3 to 8.
  - Long videos can get more: up to about one per 7 minutes, at most 20.
  - "At least 10", "at most 5" or "give me 8" are followed exactly. *(2026-11-12; fixed on 2026-11-13
    so a short video is never offered fewer than v1.1's 8)*
- ⬆ **Live streams and gameplay are recognised by themselves.** "Starting soon", "Be right back" and
  stream-ending screens are left out. The stream rules apply: clips built around your talk, quiet
  stretches expected, no stream housekeeping. *(2026-11-12)*
  - Way back: if real video is ever taken for a break, say "break 2 is real video"
    (`run.py kind <project> --keep 2`).
- ⬆ **Deep clips**: one short from moments far apart in the video. They are only made when you
  want them. Without them, the regular clips are made exactly as before. *(v2.0)*
- ↔ **One question for long videos.** For a video longer than 21 minutes, Claude asks once whether
  you want deep clips too. It asks at the start, while the video downloads. v1.1 never asked.
  The owner asked for this on 2026-11-12.
  - If you're away, the run waits for your answer.
  - Way back: `"deep_clips": "never"` (or `"always"`) in settings.json, and no question is asked.
- ⬆ **A [noun] in the captions** when a clip says "this movie" or "he" without naming it:
  IS MOVIE [RAMAYANA] KA. *(v2.0)*
- ⬆ **More checks before cutting**: false starts, a piece that starts on "he" or "वो", claims to
  check, misheard words, break screens, long silences in streams. These are warnings only; they
  never block a clip. *(v2.0, 2026-11-12)*
- ⬆ **Friends on voice chat count like the streamer.** The reading helpers, the critic and Claude were
  told to build gameplay clips around the streamer and to treat "(other voice)" lines as the game. On a
  stream where friends play along, their banter, roasts and stories were worth as much, and Claude had to
  say so by hand. Now every helper is told: a friend's line counts exactly like the streamer's; only the
  game's scripted English is context. *(v2.7, 2026-11-20)*
  - Way back: none needed (it only adds clips; game characters are still never the clip's voice).
- ⬆ **"No limit" really means no limit.** Asked for "as many as possible" or "100+", Claude had to tell
  the reading helpers by hand to bring more ideas (each was capped at 10). Now `parts --no-limit` (said as
  "no limit", "as many as possible", "jitne ho sake", "100+") drops the cap and lets each helper bring up
  to 20; "at least 30" or more does that too. *(v2.7, 2026-11-20)*
  - Way back: none needed; without those words the count is as before.
- ↔ **In gameplay and streams, clips may share a moment.** v1.1 never let two clips share seconds: the
  better one was kept. On a stream with friends a funny moment earns a short, a long and a joined version,
  so there two clips may now share seconds when they clearly differ. Never near-copies (most of the longer
  clip the same) and at most 3 clips per moment; `cut --check` names those. Podcasts and every other video
  keep one clip per moment, exactly as before. *(v2.7, 2026-11-20)*
  - Way back: `"overlap_clips": "avoid"` in settings.json (`"allow"` puts overlaps on every video).
- ⬆ **Private details said out loud stay out of clips** (gameplay and streams). On a GTA stream a viewer's
  email address was spelled out letter by letter, and Claude kept it out of every clip by hand. Now ClipKaro
  finds an email address, contact detail or phone number said out loud (a cue like "email ID" or "number"
  followed by letters and digits said one right after another, or 9+ digits in a row; counting, years,
  prices and game buttons are left alone), leaves it out of what the reading helpers see, and `cut` takes
  those seconds out of any clip that touches them. *(v2.7, 2026-11-20)*
  - The release review found everyday talk taken for a detail ("the number of people who quit at 25 ...
    one in two", "मेरा नंबर एक पे आया ... दो साल बाद 2019 में", "मुझे नहीं पता"), which cut seconds out of podcast
    clips. Now only pieces said one right after another count, a number word ("one", "एक") only next to
    another piece, and it runs on gameplay and streams only, where viewers and friends read things out.
    The stream's real email address and in-game number are still found. *(v2.7.1, 2026-11-21)*
  - Way back: `"private_details": "keep"` turns it off; `"all"` also checks podcasts and talks.
- ↔ **Joined clips don't say so in their posting texts.** Deep clips (v2.0) started every caption and
  description with "From 2 moments of the full video: 0:08 · 22:53" and ended the YouTube title with
  "(2 moments joined)". The owner, 2026-11-21: that is information for us, not for viewers. Now it stays
  in clips.json and in Claude's report, and `run.py post` takes it out of older clips.json files too. The
  short white flash at each jump in the video is unchanged. v1.1 had no deep clips. *(v2.7.1, 2026-11-21)*
  - Way back: `"joined_note": true` in settings.json.
- ⬆ **Reaction words on the frame sheets, right in both scripts.** The yellow word on a frame (where
  someone shouts "bhaag", "kya ho gaya") now matches whole words only ("aage" no longer reads as "aag", fire),
  and finds the Hindi-letter spellings too, so a transcript in Devanagari gets its reaction words as well.
  *(v2.8, 2026-11-23)*
- ⬆ **"Word check done" applies your answers.** With `"unsure_words": "ask"`, careful listening lists the
  words it couldn't settle in `word-check.json` instead of hiding them; now you write what was really said
  (or "-" for no caption), say "word check done", and the corrections go into the captions of the clips
  they're in (`wordcheck --answers`). Before, nothing read your answers back. *(v2.8, 2026-11-23)*
- ⬆ **Checked before release** (the v2.7.1 review, 2026-11-21). Found by reading the code and fixed:
  - Careful listening crashed on every clip longer than about 25 s (the speech engine hears at most 30 s at
    once without its speech detector): longer clips are now heard in windows of under 30 s, split in a
    pause. Checked on three 34-58 s clips of the GTA stream. A model's loop (one sentence ten times) is kept
    once.
  - Careful listening and frame sheets wait while live clipping runs (the graphics card is OBS's, and live
    clips must go out fast), and careful listening stays off the graphics card when the processor was chosen.
  - "Never flip a nahin" knows every spelling ("don't", "nahiii", "नहीं", "nahin-aaunga"); a respelling
    (nahi -> nahin) is applied instead of hidden, and a hidden flip can't be shown again by a later fix.
  - A game line marks its own line, never the friend's line just before it.
  - Frame sheets work on Windows with Hindi letters in the video's title (the safe picture helpers of v2.5);
    a frame sheet that fails never stops `fetch` or `parts`, and they never download the video again; a game
    or console named in a podcast's or a review's title no longer turns frame sheets on.
  - Event starts: a clip starting just after its event gets its lead-in, an event another clip already
    shows is never repeated, no clip grows past 90 s, and with `"event_lead_in": false` no near-copy is
    added next to the reaction clip. *(v2.7.1, 2026-11-21)*
- ⬆ ⚠ **ClipKaro watches gameplay, not just the words** (gameplay and live streams only). The best game
  moment is often seen first and talked about after, so clips started when the talking started, after the
  bike fire or the chair breaking. Now `fetch` makes a frame overview (one frame every 10 s, about a minute
  per 4 hours, the webcam enlarged in each frame, a red border where the sound jumps, the reaction words
  written on): the readers see their stretch of it and name spots to look at closer; `run.py zoom` makes
  close-ups (one frame a second) for the new `clipkaro-eventfinder` helpers; `run.py events` makes the clip
  start 1.5 s before its event (no pause cuts inside the event) or adds the event as a new clip, with an
  exact-frame sheet to put the start and the sound on the right frame. Costs about 15-20 % more Claude
  usage on a gameplay video (about 1,550 tokens per sheet). Podcasts and talks never get it. *(v2.7, 2026-11-20)*
  - Way back: `"watch_gameplay": false`; `"event_lead_in": false` keeps clips starting at the first word.

## Cutting and editing

- ↔ **Fewer zooms when the camera cuts fast.** v1.1 changed the zoom at every camera cut. An anime
  clip with a cut every second got 48 zoom changes in 68 seconds; the owner asked for fewer. Now a
  cut soon after the last change keeps the zoom and only follows the new face: 28 changes on that
  clip. Joins between pieces and normal speech still change it as before. *(2026-11-13)*
  - Way back: no setting, because the zoom at every cut was the problem; `edit --no-zoom` still
    turns zooms off completely.
- ↔ **Pauses cut out, in every clip.** v1.1 played every pause inside a clip. Now pauses of half a
  second or more are shortened to a natural 0.2 s and "um" / "uh" are cut out, never across a laugh,
  and in gameplay only pauses up to 2 s. About 6 % of a clip on average. *(v2.2, 2026-11-13; the owner
  watched it on all 106 test clips and chose it for every clip, 2026-11-14)*
  - Way back: `"jump_cuts": false` in settings.json (or `cut --no-jump-cuts`).
- ⬆ **The action stays in: no pause cut where the picture moves a lot** (gameplay and streams). Pause
  cutting goes by the sound, so a quiet second where something happens on screen could be cut, leaving
  the shout without its cause: clip 143 of a GTA stream lost the takedown of a police officer right
  before "ye kya ho gaya". Now ClipKaro measures how much the picture changes in each pause (4 times a
  second, the webcam left out); a pause where it changes at least 1.5 times as much as usual in that clip,
  for at least half a second, stays in. A fast camera swing counts too (the pixels can't tell it from a
  takedown, and a jump in the middle of a swing looks like a glitch anyway). On that stream: 117 of 575
  pauses stay, 76 of 160 clips got 1.4 s longer on average; calm stretches and talk are cut as before.
  Podcasts and talks are not affected. *(v2.7.1, 2026-11-20)*
  - Way back: `"action_pauses": "cut"` in settings.json.
- ⬆ **No pause cut inside a word still being said.** A pause was measured from the end of the word just
  before it; when a stretched word ran past a shorter one (clip 21 of the GTA stream: "kaun," held 1.5 s
  around a short mark), the cut fell inside it, and the quality check failed the clip. Now a pause starts
  only after every word before it has ended. Transcripts without overlapping words are cut exactly as
  before (on that stream only clip 21 changed). *(v2.7.1, 2026-11-21)*
  - Way back: none needed (a cut inside a word was a fault).
- ↔ **Captions clear of faces and the apps' buttons.** v1.1 put captions on one line, up to 940 px
  wide, whatever was under them. Now they keep out of TikTok's button column and the apps' top and
  bottom bars (at most 800 px wide), and a shot whose caption line would cover a face moves them to
  the nearest free line. *(v2.2, 2026-11-13)*
  - Way back: `"safe_zones": false` in settings.json (or `--no-safe-zones`).
- ⬆ **A hook title, only when asked.** Saying "hook title" (or `"hook_title": true`, `edit
  --hook-title`) shows a 3-6 word title on a coloured box for the first 2-3 seconds, never on a face.
  Without it, no title, as in v1.1. *(v2.2, 2026-11-13; on for every clip for a day, then off after the
  owner's test)*
- ⬆ **Caption looks, emojis and background music.** Five more caption looks besides v1.1's (which
  stays the default); emojis on up to 3 strong words, never on a face; background music from your own
  `music` folder, quietly under the voice. *(v2.2, 2026-11-13; music on hold since 2026-11-14,
  `"music": false`, because it doesn't suit podcasts)*
  - Way back: the classic look is the default; "no emojis" or `"emoji": false`.
- ⬆ **Sound effects by mood, from your own folder** (`sounds/shock`, `sounds/funny` ...). Claude
  marks the moments that call for one. Until you add sounds, clips sound exactly as before (the two
  whooshes). *(v2.2, 2026-11-13)*
- ⬆ **Editing is about twice as fast**: the NVIDIA card encodes the clips (3x faster than the
  processor, the same picture) and two clips are edited at once when the computer has room. Files are
  about 1.3x bigger. *(v2.2, 2026-11-13)*
  - Way back: `"encoder": "x264"` and `"render_workers": 1` in settings.json.
- ⬆ **Every clip is checked by code before you see it** (`run.py qa`), and ClipKaro has its own tests
  (`run.py test`) that keep v1.1's behaviour from breaking unnoticed. *(v2.2, 2026-11-13)*
- ⬆ **Fix a caption word everywhere** with one command: `run.py fixword <project> "bow" "boat"`, or
  just tell Claude. Before, it was fixed by hand. *(2026-11-13)*
- ⬆ **Editing again no longer needs the original video** once the caption colours are saved, so
  clips of videos whose source was deleted can still be edited. *(2026-11-13)*
- ⬆ **No sound peaks over the limit.** v1.1's loudness step could overshoot on a sharp sound, and the
  AAC encoder adds peaks to harsh phone-mic sound: three test clips peaked at -0.6 to +0.3 dB. Now a
  limiter holds the mix at -2 dB, and the encoded sound is measured and limited again when it's still
  over -1.2 dB. The loudness and everything below the peaks sound exactly as before. *(v2.2, 2026-11-13)*
- ⬆ **Cutting again after a clean-up keeps the podcast framing.** When only the video was kept, `cut`
  makes the voice track again from it, so the speaker crop and split screen work as before instead
  of falling back to the plain framing. *(v2.2, 2026-11-13)*

- ⬆ **Podcasts with painted faces on the wall** show the real person. **Dark studios**: camera cuts
  are found again. *(v2.0)*
- ⬆ **Captions always fit the frame.** Before, some ran off the sides. *(v2.0)*
- ⬆ **Clips joined from pieces** sound smooth. Where the video jumps more than 20 seconds, a short
  white flash and a soft whoosh show it. Clips of one piece sound exactly as in v1.1. *(v2.0)*
- ⬆ **Action without talking gets its own line** in what Claude reads (gameplay): "(no talking) [big
  action on screen ~6 s] [explosion]", where before the note was lost because no line was spoken then.
  A note goes on the spoken line that covers most of it. *(v2.4)*
  - Way back: `"hints": false` (no notes at all, as in v1.1).
- ⬆ **The caption check also spells names right and writes numbers as digits** where they are amounts,
  years or scores (standard and deep mode; quick mode skips the check, as before). *(v2.4)*
- ⬆ **Your logo and outro.** Put `logo.png` and `outro.mp4` (9:16, ideally 3-5 s) in the `brand`
  folder: the logo goes in the bottom-right corner of every edited clip (`logo_corner`), the outro after it. Nothing
  changes until a file is there. An outro over 10 s is left out (never longer than the clip). *(v2.4)*
  - Way back: take the file out, `"logo": false` / `"outro": false`, or "no logo" / "no outro".
  - A logo on a plain square (black, white, one colour) gets the square removed by itself; the logo's own
    dark or light parts stay. `"logo_background": "keep"` uses the file exactly as it is.
- ↔ **"© Channel name" in the bottom-left corner** of clips made from a YouTube link (never your own
  video files): a small credit to the source, right in the corner at 70 % opacity on purpose (a
  formality, not something to read; `credit_corner` picks another corner). v1.1 had none. The owner asked for it (2026-11-17). *(v2.4)*
  - Way back: `"source_credit": false` in settings.json, or "no credit" for one video.
- ↔ **"© twitch.tv/name" on clips from Twitch** (and "© kick.com/name" from Kick). Before, they got
  "© name", which reads like a YouTube channel (for the owner, a different, non-gaming channel). *(v2.7,
  2026-11-20)*
  - Way back: `"credit_text": "© {channel}"` in settings.json writes the bare name again; any other words
    work too.
- ⬆ **A webcam with two or three people in it is found.** The finder looked for one face in the same spot,
  so a cam where two friends sit side by side, lean and look down was missed and the clips lost the
  gameplay-on-top layout. Now the faces near one side are counted together and the webcam's fixed border
  gives the exact box (on a GTA 6 stream: 454x260 found, the hand-set box was 462x260). It only runs for a
  video already known as gameplay or a stream (live, YouTube's Gaming category, a Twitch or Kick link, a game
  in the title), so a podcast recorded in boxes is never taken for one. *(v2.7, 2026-11-20)*
  - Way back: `"facecam"` in settings.json sets the box by hand; `--layout crop` turns the layout off.
- ⬆ **The webcam box stops at the webcam's own border.** The border search looked for the bottom edge
  below the faces, so when the friends sat low in the webcam it took a fixed line of the game 200 px lower:
  on a GTA 6 stream the 454x260 webcam came out 454x459, half of it game, and the layout shrank the faces to
  fit. Now a box taller than 4:3 is cut where a 16:9 or 4:3 webcam picture ends, at a fixed border below
  every face (so a shelf in the room is never taken for it). A box that still looks too tall makes `cut`
  warn and save `frames/facecam-box.jpg` to check by eye. Boxes already the right shape, round webcams and
  hand-set boxes are unchanged (the other GTA stream: 454x260, as before). *(2026-11-21)*
  - Way back: none needed (the box holding game picture was a fault); `"facecam"` set by hand still wins.
- ↔ **A bigger webcam under the game.** The webcam grew until it was 60 px from the sides, 90 px below the
  seam and 30 px from the bottom. The owner chose 50 / 50 / 50 / 30 after comparing frames of two GTA
  streams (2026-11-21): a 16:9 webcam is now 980x550 (was 958x540), a round one 690 across (was 650). The
  50 px on top still keeps the captions off the webcam.
  - Way back: `"facecam_margins": {"left": 60, "right": 60, "top": 90, "bottom": 30}` in settings.json.
- ↔ **No captions for game characters** in gameplay with a Hindi or Hinglish streamer. v1.1 captioned
  every line it heard clearly, so a game character's line appeared twice: in the game's own subtitles
  and in ClipKaro's. Now only the streamer is captioned; the game lines keep their sound and stay in
  the transcript (Claude can still pick a game scene). The owner asked for it (2026-11-16). *(v2.3)*
  - Way back: `"game_voice_captions": true` in settings.json.
- ⬆ **Your friends' Hinglish keeps its captions.** The game-voice rule knew only common Hindi words, so a
  friend's line with less common ones ("Kisko khaoon?", "Main kama loon", "Vaah, vaah") looked English and
  lost its captions (about 30 lines on a 3-friends GTA stream). Now a word counts as English only when the
  speech model's own vocabulary holds it whole; Roman Hindi breaks into pieces there. On that stream: 841
  words captioned again, no line newly hidden, every game line still hidden. A friend speaking English still
  sounds like the game, so the caption check can bring a line back (`"show_captions"` in clips.json) or drop a
  game line the rule let through (`"hide_captions"`); it now lists the hidden lines for that. *(v2.7,
  2026-11-20)*
  - Way back: none needed (it only brings back captions that were wrongly hidden); `"game_voice_captions": true`
    still captions everything.
- ↔ **No captions for game characters, also when you speak English.** With an English streamer the rule
  above had nothing to go by (both speak English), so every game line was captioned and appeared twice. Now
  ClipKaro reads the game's own subtitles on screen (a small text reader, English only, about 10 MB): a line
  whose words are in the subtitle area while it is said is the game's and gets no caption; its sound stays.
  It reads only the lines of the picked clips, about a second a frame, and first checks whether the video
  shows subtitles at all (if not, nothing more is read and every line keeps its captions). Hinglish videos
  keep their own rule, at no extra cost. *(v2.8, 2026-11-23)*
  - Way back: `"game_subtitles": false` (not read) or `"game_voice_captions": true` (everything captioned).
- ⬆ ⚠ **Claude checks the captions** before cutting (standard and deep mode): it reads every clip's
  captions like a viewer and fixes clear mishearings ("sorry" heard as सारी, a wrong name) with
  `fixword`. A little more Claude usage per video; quick mode skips it, as before. *(v2.3)*
- ⬆ **No flash of the next shot at a clip's end.** A camera cut in a clip's last frames showed a few
  frames of another shot (12 of the 106 test clips). Now the clip ends just before such a cut, or, when
  the last word is still being said, the picture holds the last frame for a moment while the word ends;
  a split screen never switches for less than 0.6 s at an edge. No word is cut. *(v2.3, 2026-11-14)*
  - Way back: none needed (a flash was a fault); clips without such a cut are cut exactly as before.
- ⬆ **No sound spike at a clip's very first moment.** A loud sound in a clip's first milliseconds made
  the sound encoder overshoot, whatever the limiter did, so the quality check failed the clip (clip 149
  of a GTA stream: -0.7 dB at 12 ms, the limit is -1). Now the sound fades in over 30 ms at the very
  start, too short to hear. Nothing else moves: same length, same timing. *(v2.7, 2026-11-20)*
  - Way back: none needed (the spike was a fault).
- ⬆ **Sound effects from the first clip.** The mood folders (`sounds/shock`, `funny` ...) started empty,
  so no clip got a mood sound until someone found and added files. `install.py` now downloads a free
  starter set (33 sounds from Mixkit: free for videos, commercial use too, no credit needed; the owner
  approved them on a GTA stream), only into folders that are still empty. `cut --check` names the moods
  the clips ask for and any without a sound. *(v2.7, 2026-11-20)*
  - Way back: `python install.py --no-sounds`, or delete the files (an empty mood plays nothing, as before).
- ⬆ **Sound effects start on their moment, never before it.** A mood sound's loudest point was lined up
  with the moment, so a slow sound started early: on a GTA stream a trombone began a second before the crash
  it was for, and a crowd cheer can start almost 3 seconds early. Now every mood sound starts at most 0.1 s
  before its moment; a sound that hits at once (a boom, a boing, a buzzer) lands exactly as before.
  *(v2.7, 2026-11-20)*
  - Way back: `"sound_onset": "peak"` in settings.json.

- ↔ **Action pauses: only the ones where something happened stay** (gameplay and streams). v2.7.1 kept every
  pause where the picture changes a lot, so the takedown before "ye kya ho gaya" stayed, but so did plain camera
  swings (76 of 160 GTA clips got about 1.4 s longer). Now such a pause stays only when there is also a sign that
  something happened: a game sound burst in it, or right after it a laugh, a shout, a reaction word ("ye kya",
  "bhaag") or an exclamation ("arre", "oye"), or a voice much louder than the talk around it. On that stream about
  36 of the 124 kept pauses still stay, the takedown among them; swings with no reaction are cut again.
  *(v2.8, 2026-11-23)*
  - Way back: `"action_pauses": "keep"` in settings.json (v2.7.1); `"cut"` is v2.7.

- ⬆ **A landscape (16:9) copy, when you ask.** "Landscape copy" keeps the standing clips and adds a wide
  1920x1080 copy of each (`run.py landscape`): the same pieces and pause cuts, the captions, credit, logo, emojis
  and sound placed for a wide frame; no zooms, no outro. For YouTube videos and long compilations. Before, it
  was made by hand (22 November). Without asking, nothing changes. *(v2.8, 2026-11-23)*

- ⬆ **Finish a clip in DaVinci Resolve, when you ask.** "Export to resolve" writes each clip as a timeline the
  free DaVinci Resolve opens (`run.py resolve`): the clip in its pieces (each pause cut a visible cut), its sound,
  the sound effects on their own track, and the captions as a subtitle file. On Linux it makes edit copies the
  free Resolve can read. Before, a clip could only be edited further from the finished MP4. *(v2.8, 2026-11-23)*

- ⬆ **"Boast, then fail" story clips** (gameplay, standard and deep mode). A promise or boast and, minutes
  later, the fail that pays it off, told in up to 6 sharp cuts within 10 minutes (further apart: a deep
  clip). The game's game-over screens (WASTED, FAILED, BUSTED) are read from the picture (about a minute for
  4 hours, a small English text reader) and shown to Claude as lines of their own, so a piece can be the
  FAILED screen itself. Only when it's funny: the fail must pay off something said before. *(v2.9, 2026-11-23)*
- ⬆ **A piece without words is kept, not skipped.** A range in clips.json with nobody talking (a crash, a
  game-over screen) was left out of the clip without a word; now it is shown exactly as given, and
  `cut --check` says so. New `"keep_whole"` stretches are shown whole (no trimming to words, no pause cut).
  *(v2.9, 2026-11-23)*
- ↔ **A game-over screen in a clip is always shown whole** (gameplay): no pause cut inside it, and a clip
  edge inside it isn't trimmed to the words. *(v2.9, 2026-11-23)*
  - Way back: `"game_over_screens": false` (the screens are not read).
- ⬆ **A clip never runs past the video's end.** The small sound handle after the last word could reach
  beyond the end of the video; the clip's timing then didn't match the picture at its very end. *(v2.9)*
- ⬆ **Compilations across videos** (advanced mode only): "a compilation of every glitch from my last 4
  streams" makes one clip from moments of several clipped videos: you name the topic or Claude suggests
  some, every moment is checked on its frames, the pieces are joined frame-exact with the loudness evened,
  and nothing is pause-cut (silent glitches stay). Over 1:30 it also gets a landscape copy. Before, this was
  done by hand (22 November). *(v2.9, 2026-11-23)*

- ↔ **A listener's silent laugh is seen** (podcasts and talk videos). ClipKaro only heard laughs, so a guest who
  cracked up without a sound was missed. Now faces are read: a strong laugh without a sound becomes a hint for
  picking (`[a silent laugh on screen ~2 s]`, the strongest few), and in a two-person shot both people are shown
  while the listener laughs or looks shocked, as around a heard laugh. Only strong ones (the owner's rule). About 4
  minutes per hour of video at fetch. *(v2.12, 2026-11-23)*
  - Way back: `"silent_reactions": false` in settings.json.

- ⬆ **Three people in one shot** (panels, three on a sofa). The wide shot used to be framed as if only the two
  most visible people were there; the third was never shown, even when talking. Now the one talking alone gets
  the crop (left, middle or right), and laughs and talking over each other show all three stacked, with the
  captions on the lower seam. Two-person shots are framed exactly as before. *(v2.13, 2026-11-23)*

## Posting

- ⬆ **How your clips really did** (with PostKaro 0.10). PostKaro reads every live post's numbers back (views,
  watched %, shares, likes) at about 1, 3, 7 and 28 days and shows them on Posted; "how are my clips doing?" gives
  a plain report per channel (`run.py learn`). *(v2.11, 2026-11-23)*
- ↔ **The critic learns from your channels.** With 30+ posted clips that have a critic score and a result, the
  clip score's five weights move towards what really did well on your channels (gameplay and talk videos apart,
  at most half up or down, slowly). It only changes the ranking; no clip is dropped. *(v2.11, 2026-11-23)*
  - Way back: `"learn_from_views": false` in settings.json (the fixed weights).
- ⬆ **Fix a clip by clicking: PostKaro's Studio** (with PostKaro 0.9). Press **Fix** on a clip: move its start
  or end to another word, fix or hide a caption word, change the framing, switch an emoji, a sound effect or
  the whooshes off; only that clip is made again (about a minute), and **Undo last change** puts it back. No
  Claude usage. Before, every change meant asking Claude or typing commands. *(v2.10, 2026-11-23)*
- ⬆ **Make your own cuts in the Studio** (PostKaro 0.9.1). Cut a part out of a clip's middle, add a moment from
  anywhere in the video, put your own emoji or sound on a word; your emojis go first among the 3 a clip shows.
  Claude's emojis without a second are placed exactly as before. *(v2.10.1, 2026-11-23)*
- ⬆ **A landscape copy follows its clip.** When a clip with a landscape copy is cut again, the wide copy is
  cut again too (it used to keep its old cut and its own sound). *(v2.10)*
- ⬆ **Text for each platform**: a YouTube title of up to 100 characters with fitting hashtags,
  Instagram and Facebook captions, and `post.json` for PostKaro. The finished clips in `edited/` are
  the same files as before. Without PostKaro nothing changes. *(v2.0, 2026-11-12)*

## Settings and commands

- ⬆ All six v1.1 settings work as before. There are three new ones: `jump_label`, `deep_clips` and
  `max_clips`. An old settings.json works unchanged.
- ⬆ Every v1.1 command works as before. The new ones are extra: `info`, `kind`, `parts`, `topics`,
  `sound`, `critic`, `deep`, `honesty`, `post`, `relisten`, `asr-bench`, `voices`, `hints`, `captions`.
- ⬆ `run.py test --full` also runs a tiny made-up video from start to end (cut, edit, qa), and
  `asr-bench public` scores speech models on public Hindi and Hinglish test sets. *(v2.3)*
- ⬆ **Windows and Mac** *(v2.5)*: on Windows, pictures in folders with Hindi letters are read and written
  through a way that understands them (OpenCV's own can't), videos open through FFmpeg, and caption files
  of clips with Hindi names get English-letter names; on a Mac, Homebrew's `ffmpeg-full` (the one that can
  draw captions) is found by itself. On Linux, and for plain English names, nothing changes.
- ⬆ `install.py` stops at once, with the fix, on a Python the speech engine can't use (3.15, or 3.14 on an
  Intel Mac), instead of failing half-way; a `.venv` made with one is made again. *(v2.5)*
- ⬆ **Live clipping** *(v2.6)*: `run.py live` (a watcher on OBS's 10-minute recording pieces, Twitch chat and
  viewer clips as hints), `post --now` (everything posted at once through PostKaro's new `post-now`), and
  the settings `live_folder`, `twitch_channel`, `twitch_delay`, `live_post`, `live_vram_mb`. Nothing changes
  unless a live session is started; while one runs, heavy steps run at low priority and edit with the
  processor's encoder (the stream comes first). Auto-posting without review is the owner's choice for live
  streams only; normal clipping still ends with PostKaro's review page.
- ⬆ New settings `source_credit`, `logo` and `outro`, and `edit --no-credit`, `--no-logo`, `--no-outro`.
  No Claude usage; an outro adds about a second of rendering per clip. *(v2.4)*
- ⬆ **YouTube's sign-in check on Windows** *(2026-11-17)*: on Windows, `--cookies-from-browser` can't read
  Chrome, Edge or Brave (they lock their logins: "Failed to decrypt with DPAPI"), so a video YouTube asked
  about couldn't be downloaded. Now a cookies file in the ClipKaro folder (`cookies.txt`, or the
  extension's `www.youtube.com_cookies.txt`; another place: setting `cookies_file` or `fetch --cookies <file>`)
  is tried by itself, **only when YouTube asks**, and the rest of that video's downloads use it too. The
  error messages now say what to do in plain words. Without such a file every download is exactly as
  before, and `--cookies-from-browser` works as before. Git ignores any `*cookies*.txt`.
- ⬆ **Live settings as placeholders** *(2026-11-18)*: settings.json now ships `live_folder` and
  `twitch_channel` as `"<your OBS recording folder>"` / `"<your Twitch channel>"` instead of `null`, so it
  shows what goes there. Any `"<...>"` value counts as not set, exactly like `null` before (never used as a
  path), and Claude asks for the two the first time live clipping starts and writes the answers in. A
  settings.json with `null` or with real values works unchanged; `live_post` stays `now`. No Claude usage
  beyond one question, once. Test: LiveSettings (2).
- ⬆ **Docs** *(2026-11-18)*: the live clipping guide is now `docs/live-clipping.md` (was `docs/live.md`), with
  the whole setup and going live step by step, and the right place of OBS's "Automatically record when
  streaming" (Settings → General → Output in newer OBS). New: `docs/streaming-setup.md` (multistream on
  OBS: YouTube, Twitch and Kick at once, the encoder settings, checking you're live) and `docs/postkaro.md`
  (posting with PostKaro). The README highlights the YouTube cookies file Windows needs.
- ⬆ **Docs** *(2026-11-21)*: the README opens with the owner's 16-minute video guide (installing ClipKaro and
  PostKaro on Windows and using them), linked under the short description.

## Cost

- ⚠ **Claude usage** (standard and deep). Reading in parts, the critic and deep clips use more of your Claude plan than
  v1.1's single read. **Measured on real runs** *(2026-11-20, from Claude Code's record of every request;
  tokens without the cheap re-reads, and what the same work costs on the pay-per-use API, Opus 5.5)*:
  - v1.1's single read, a 7-minute talk: 0.2 million tokens (about $3);
  - standard, a 37-minute Hindi gameplay stream: about 0.6 million (about $7-8);
  - the same with deep clips: 1.1 million (about $13);
  - a 4-hour stream with 160 clips, deep clips and careful listening: 8.2 million for the helpers alone
    ($79).

  Worked out from these for a 1-hour video: quick about 0.4-0.55 million, standard about 0.9-1.1
  million, deep about 1.5-1.8 million; gameplay and streams add about 0.25 million. The earlier
  guesses (about 1 million standard, 2 million deep for a long podcast) were close.
  All numbers: [requirements.md](requirements.md#how-much-claude-usage).

  Choosing the clips also takes a few minutes longer. On Claude's Pro plan that can mean fewer
  videos per day than with v1.1.
  - **Way back: quick mode** *(2026-11-13)*. Say "quick clip this" or "use fewer tokens", and
    Claude picks like v1.1 (one read, no helpers, no critic), with every other upgrade kept. It uses
    about half of standard.

---

## How we keep it an upgrade

1. Before building, check: does this take away or limit anything v1.1 could do? If it changes
   something on purpose, add a way back (a setting, a word you can say, or a command option).
2. Test on old projects from the test bench. Old clips may come out different when the change fixes
   something; that's fine. Something that worked must not stop working.
3. Add the change to this page (with its mark) and to [CHANGELOG.md](../CHANGELOG.md), in the same
   commit.
