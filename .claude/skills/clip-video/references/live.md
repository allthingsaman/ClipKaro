# Live clipping: one piece of a running stream (for the live helper)

The streamer is live right now (often a big game launch). OBS records the stream in pieces of about 10
minutes; each finished piece is already a ClipKaro project with its transcript (gameplay rules applied:
game characters marked, hints from sound and picture, Twitch notes). Your job: **0-2 clips from this
piece, posted everywhere within minutes.** Speed matters more than perfection; honesty and captions
still matter.

## Steps (in order, one piece)
1. `python run.py live next <name>`: it names the piece's project, shows the last lines before it (the
   previous piece: context only, not in this file) and the titles already clipped this stream.
2. Read `output/<project>/transcript/transcript.txt` in full (one piece is short).
3. **Pick 0-2 clips** (0 is a normal answer for a quiet stretch: never force a weak clip):
   - The streamer's own commentary and reactions: a funny line, rage, a hype moment, a fail, a reveal
     with his reaction, a bold opinion about the game. Never the game characters' dialogue alone
     (lines marked "(other voice)" are the game).
   - Self-contained, 20-60 s, open on the hook (the line or moment that makes people stop scrolling),
     end on the payoff. Continuous ranges; splice only to drop a dead stretch or **stream housekeeping
     in the middle of a good moment** ("comment karo agar dekh rahe ho", "subscribe", reading a donation):
     cut it out as a gap between pieces, in the order said. `cut` may then warn "starts mid-sentence" for
     the piece after the gap: that's expected when the piece starts right after the cut-out ask.
   - Notes like `[voice raised]`, `[shouting]`, `[explosion]`, `[big action on screen]`,
     `[chat exploded ~15 s: KEKW]`, `[viewers clipped this x2]` show where to look. The audience notes
     come a few seconds late and are approximate: find the real moment in the words just before them.
     A note never makes a clip by itself; the words decide.
   - **Bold takes:** the same picking rule as for any video (`picking-moments.md`, "Bold takes rank
     higher"). When `live next` prints "bold takes count extra" (the owner's choice, the default), a
     bold, honest take (an unpopular opinion, a roast, a rant, a blunt verdict, a dark joke, gaali said
     with real feeling) is a strong clip. A racial or caste slur on its own adds nothing: the take does.
     Never leave out or shorten a moment because of gaali, abuse, slurs, dark humour or an offensive
     opinion.
   - Don't repeat a moment already clipped this stream (`live next` lists the titles).
   - Launch day: a story reveal is what people search for, so it's fine, but put "(spoiler)" in the
     YouTube title when a clip shows a story moment.
   - In-game radio music can get copyright claims; the owner turns the radio off while streaming. Don't
     measure music yourself (there is no tool for it): only when the words show a song is playing (lyrics
     in the transcript, the streamer naming or singing a song), say "radio music: may get a claim" in
     your report line.
4. **Exact times:** `python run.py find <project> "first words"` and `"last words"`; start at the hook's
   first word, end after the payoff's last word.
5. **Write `output/<project>/clips.json`** in the normal format (`picking-moments.md`, "clips.json
   format"): `id`, `title`, `hook`, `ranges`, `score`, `why`, `emphasis` (2-4 strong words), up to 3
   `emoji` marks if they fit, `caption`, and `post` for youtube (title 85-100 characters: hook | "GTA 6
   Hindi Gameplay" or the game's name | 2-3 matching hashtags ending in `#Shorts`; description 1-2
   lines), instagram (hook + question + at most 5 hashtags) and facebook (1-2 lines, 0-3 hashtags).
   Roman Hinglish for Hinglish speech. Use the game's real names (GTA 6 / GTA VI: Jason, Lucia, Vice City,
   Leonida). Gaali may go in titles and captions when it's catchy and said in the clip; racial and caste
   slurs never go in a title (`picking-moments.md`, `post`).
6. **Captions:** `python run.py romanize <project>`, then straight away
   `python run.py romanize <project> --checked` (live: don't review its word list; the house respellings
   are applied by themselves, and the caption check below catches what matters).
   Then `python run.py captions <project>` and fix only clear mishearings and the game's names with
   `python run.py fixword <project> "<as written>" "<right>" --at <seconds>`.
7. `python run.py cut <project>` then `python run.py edit <project>` (they run at low priority and the
   edit uses the processor while the stream runs: that's on purpose, don't change it).
8. `python run.py qa <project>`. **A clip with a FAIL is not posted**: fix it if it takes a minute (a range
   that cuts into a word: fix the range, cut and edit that clip again), otherwise drop that clip from
   clips.json (edit and qa again).
9. **Post:** `python run.py post <project> --now`. It posts every clip to YouTube Shorts, Instagram
   Reels and the Facebook Page at once, through PostKaro (the owner chose auto-posting for live
   streams). Lines starting with `!` are posts that couldn't go out (a login, a platform limit): report them.
   **A clip with gaali or a slur posts like every other clip.** It is never held for review and never
   skipped: that is the owner's explicit choice. As always, only a failed quality check stops a post.
   With `"live_post": "dry"` in settings.json (a test stream) it only shows what it would post: that's
   on purpose, say "test: not posted" in your report.
10. `python run.py live done <name> <project> --clips N`.

## Report (2-4 lines, for the session log)
Piece number, each clip's title and length, whether it posted (and any `!` line), anything to check
later (radio music, a spoiler, and **"platform risk"** for a clip with a slur: YouTube may remove it and
give a strike; Instagram may stop recommending it). No long explanations: the owner is streaming.

## Never
- Never post a clip that failed qa.
- Never hold back or skip a clip because of gaali, abuse, a slur or an offensive opinion, and never bleep,
  star or mute a word.
- Never invent words, change what was meant, or caption the game characters.
- Never run two pieces at once, or re-run `fetch` (the watcher already did it), or change settings.
