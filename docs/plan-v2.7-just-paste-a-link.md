# Plan for v2.7: "just paste the link"

**Status: built and released in v2.7 (2026-11-20).** The owner approved every item. Item 1 was discussed in three rounds and built as described below.

## Why this plan

On 2026-11-19 and 2026-11-20 we clipped a 4-hour GTA 6 Twitch stream: three friends on voice chat, in Hinglish.
To get good clips, the owner had to explain a lot by hand:
- make lots of clips, and allow overlaps;
- never censor;
- listen to every word carefully;
- keep unclear words out of the captions;
- choose the sound effects;
- use a Twitch credit;
- keep a spoken email address out of the clips;
- start a clip where the game moment happens, not where the talking about it starts.

The goal of v2.7 is that nobody has to say any of this again.
A user pastes the link, says "clip this", and ClipKaro does the rest by itself.
When everything below is approved and built, it goes into the main branch as **v2.7**.
The changes already on the v2.6-dev branch (never censor, bold takes count extra, stars in written words) go in with it.

Each item below says:
- what goes wrong today, with the example from this stream;
- what ClipKaro would do by itself;
- the way back (every change must be an upgrade to v1.1, so there is always a way to get the old behaviour);
- a rough build time.

## The owner's answers so far

- **Item 1 (watching the gameplay): yes, as a new feature.**
  - The AI helpers get pictures of the gameplay together with the transcript.
  - It is only for gaming videos: gameplay, walkthroughs and game streams. ClipKaro finds out by itself whether a video is one, from the title and from frames of the video.
  - It works in all three modes (quick, standard and deep) whenever the video is a gaming video.
- **"Plan first, don't render yet": no.** It was only for building ClipKaro. Claude can still do it by hand on request.
- **Overlapping clips:** explained below; your choice is still open.

## What you need to do

Read the items. Answer yes or no for each ("yes to all", or "yes to 1-9").
Three items still need a choice from you; they are marked **Your choice**.
After your yes, Claude builds them one at a time. Each item gets:
- a test;
- a line in [since-v1.1.md](since-v1.1.md);
- updated docs;
- a local commit.

At the end, Claude merges everything into main, tags v2.7 and gives you the push commands.

---

## 1. ClipKaro watches the gameplay, not just the words (frame sheets), as built

This item is only for gameplay and live streams. Podcasts and talks never get it.

1. **Overview (`fetch`):** one frame every 10 seconds of the whole video, 21 frames per sheet (7 across, 3 down), each with its time.
   - The webcam is shown enlarged in the bottom-left corner.
   - A red border marks the loudest 15 % of the video; at a fixed level, half of a loud stream's frames were red.
   - The reaction words ("BHAAG", "YAH KYA") are written on the frames.
   - It takes about a minute for 4 hours.
2. **The readers** get the sheets of their part with the transcript. They name spots worth a closer look, at most one per 4 minutes, only where something visible happens.
3. **Close-ups (`run.py zoom`):** 21 frames, one per second, mostly before the spot, with the webcam inset. The `clipkaro-eventfinder` helpers decide: clip or not, when it starts, and when the reaction ends.
4. **Events into the clips (`run.py events`):**
   - a clip that starts on the reaction starts 1.5 s before its event, with no pause cuts in its first 10 s;
   - an event no clip shows becomes a new clip;
   - nothing moves when a clip already starts there;
   - an exact-frame sheet (4 frames a second) puts the start and the sound on the right frame.
5. **Sounds start on their moment, never before it.** This applies to every video; the way back is `"sound_onset": "peak"`.

**Tested on the 4-hour GTA stream:**
- The helpers saw only the pictures, no words, and named 6 of the 7 events Claude had found by hand. The shark was missed; its words would have helped.
- The eventfinder confirmed all 6, with start times within 0-4 s, found one new event, and said "no" to 9 of 10 random spots.

**Cost, measured:**
- about 90,000 tokens per helper that looked at 19 sheets;
- about 64,000 for 16 close-ups.

**Way back:** `"watch_gameplay": false`, `"event_lead_in": false`.

## 2. Careful listening, and no captions on unsure words

**Today.**
With three voices and game sound, the first transcript was badly garbled.
Claude did several things by hand:
- had a second speech model hear the whole stream;
- had two more models hear every clip again;
- fixed 583 words where the models agreed;
- put 176 unsure words in a file for you to check by ear.

Then you chose a simpler rule: an unsure word gets no caption.

**Change.**
For a gaming video, or any video with three or more voices, ClipKaro does all of this by itself:
1. A second hearing of the whole video, which the reading helpers use.
2. Two more hearings of every picked clip.
3. Fixes where the hearings agree.
4. Every word they can't settle gets **no caption**, while the sound plays as normal. The list is kept, so a line can be brought back later.
5. A fix that would flip the meaning (an added or dropped "nahin"), or kill a pun, is never applied. That word is hidden instead.

**Way back.**
- settings.json `"careful_listening": false` turns it off.
- `"unsure_words": "ask"` gives you a file to check by ear instead.

**Cost.** ⚠ It costs more: about 25 minutes of graphics-card time for a 4-hour stream, plus the helpers' usage.

**Build:** about 2-3 hours.

## 3. Your friends' lines keep their captions

**Today.**
In gameplay, ClipKaro hides the captions of game characters, because the game shows its own subtitles.
The rule also hid some Hinglish lines from your friends, in about 25 of the 149 clips. Examples:
- "Kisko khaoon?" (the meow song);
- "Main kama loon";
- "Mumbai map?".

**Change.**
- A line with Hindi words in it is never treated as a game character.
- clips.json also gets a way to force captions on a stretch.

**Way back.** Not needed: it only brings back captions that were wrongly hidden.

**Build:** about 1 hour.

## 4. Streams with friends: the friends count fully

**Today.**
The helpers are told to build clips around the streamer.
A friend's line could be mistaken for a game character.

**Change.**
- All helpers are told that a stream can have friends on voice chat.
- A friend's banter counts exactly like the streamer's.

**Way back.** Not needed: it only adds clips.

**Build:** about 30 minutes.

## 5. Lots of clips, and overlapping clips

**What "overlapping clips" means.**
Two clips overlap when they share some of the same seconds of the video. On this stream, several clips use the same 25 seconds of the chair breaking:
- clip 20 is the short version: the chair breaks, "kaise tooti?";
- clip 37 is the long version: the same, plus the "sasti chair" roast;
- clip 17 joins it with a taunt from 20 minutes later.

**Today.**
ClipKaro avoids this. When two good ideas share seconds, it keeps only the better one, and a joined clip is rejected when more than half of it is already a normal clip.
For this stream you asked for overlaps, so you got all three versions.

The good side of allowing it: more clips, and you choose which version to post. The risk: a follower may see the same joke twice.

**Change.**
- "No limit", "as many as possible" or "100+" in your message lets the helpers bring up to 20 ideas per part, with no cap on the number of clips.
- A new setting `"overlap_clips"` decides about shared seconds:
  - `"avoid"`: today's way, one clip per moment.
  - `"allow"`: up to 3 clips per moment, only when they clearly differ (a short and a long version, or a joined one). Two clips that are almost the same are never made.

**Your choice.** Which should be the default?
Claude suggests `"allow"`, because you post almost every decent clip and like having both a short and a long version.

**Way back.** Whichever you don't pick stays one setting away.

**Build:** about 1 hour.

## 6. Sound effects that work out of the box

**Today.**
The `sounds` folders start empty, so no clip gets a mood sound until someone adds files.
On 2026-11-20 Claude downloaded 33 free sounds from Mixkit, and you liked them.

**Change.**
- `python install.py` downloads the same starter set. The Mixkit license allows free use in videos, with no credit needed. The list is kept in `sounds/SOURCES.txt`.
- Your own files are always used too.
- `cut --check` lists which moods a video needs.

**Way back.** `python install.py --no-sounds`, or delete the files.

**Build:** about 1 hour.

## 7. The Twitch credit, and finding a webcam with two people in it

**Today.**
- **Credit:** a clip from a Twitch link got "© allthingsaman". That reads like your YouTube channel, which is a different, non-gaming channel.
- **Webcam:** the finder looks for one face, so it missed a webcam with two people in it. Claude fixed both by hand.

**Change.**
- A clip from a Twitch link gets "© twitch.tv/<channel>" by itself.
- The webcam finder also looks for a fixed box on screen whose edges never move, so a cam with 2-3 people in it is found too.

**Way back.**
- settings.json `"credit_text"`, to write any credit you like;
- `"facecam"`, to set the box by hand.

**Build:** about 1-2 hours.

## 8. Private details said on stream stay out of clips

**Today.**
At 3:29:36 an email address was spelled out loud. Claude noticed it and kept it out of every clip by hand.

**Change.**
- ClipKaro looks in the transcript for an email address, phone number or home address that is spelled out.
- It keeps those seconds out of every clip and tells you where they were.
- Names of games, places in the game and public people are not affected.

**Way back.** settings.json `"private_details": "keep"`.

**Build:** about 1 hour.

## 9. A small fix: a too-loud first syllable

**Today.**
Clip 149 began with a loud syllable in its first 15 milliseconds. The loudness limiter didn't react in time, so the quality check failed it. Claude fixed that one file by hand.

**Change.**
The edit adds a moment of silence before the sound goes through the limiter, then trims it off again.

**Way back.** Not needed: nothing you can hear changes.

**Build:** about 30 minutes.

## 10. All of this in the clipping steps Claude follows, and the release

**Change.**
- The clip-video skill and the helpers' instructions get everything above. "Clip this: <link>" then does the whole job.
- The docs get it too, in simple words: the user guide, the hinglish page, live clipping and the README's "what's new".
- When all items are done:
  - `python run.py test` passes;
  - one fresh gaming video is clipped from start to end as the final check;
  - Claude merges into main and tags v2.7;
  - you push.

**Build:** about 2 hours, plus the final test run.

---

**Total:** about 16-21 hours of building, one item at a time.
Item 1 is half of it.
