# How to use ClipKaro: what to type

You use ClipKaro by **writing to Claude Code** (your AI helper) while it's open inside the
ClipKaro folder. There are no special commands to learn: you write a normal sentence, and Claude
does the right steps. This page shows what you can ask for.

Not set up yet? See [installation.md](installation.md), or the simple [user guide](user-guide.md).

## 1. The basic request

Open Claude Code **inside the ClipKaro folder** and type:

> **clip this video: https://youtu.be/VIDEO_ID**

or, for a video on your computer, its path in quotes:

> **clip this video: "C:\Users\you\Videos\my podcast.mp4"** (Windows)
> **clip this video: "/home/you/Videos/my podcast.mp4"** (Linux)
> **clip this video: "/Users/you/Movies/my podcast.mp4"** (Mac)

That's all. Claude then does every step by itself. It asks at most one question: for a video longer
than 21 minutes, "do you want deep clips too?" (see below). It asks right at the start, while the
video downloads, so nothing waits for you.

1. downloads the sound and the video, and writes down every word (using your NVIDIA graphics card if
   you have one),
2. looks at the picture: is it a **live stream**? **gameplay** with your webcam in a corner? It
   leaves out "Starting soon", "Be right back" and stream-ending screens by itself,
3. reads everything and picks every good moment: **3 to 8 clips**, and more for long videos (up to
   about one per 7 minutes), unless you ask for a number, and shows you a table of them,
4. for Hindi/Hinglish, writes the captions in English letters ("aaj hum business ki baat karenge"),
5. cuts each moment into a standing (9:16) video and keeps the speaker's face in the middle,
6. adds the edit: zooms, word-by-word captions, a couple of soft whooshes, phone-friendly volume,
7. shows you a table of the finished clips, with a caption to post for each one.

**Good to know**
- "clip this video" isn't a magic phrase. "make shorts from this", "cut this into reels",
  "best moments of this podcast" or "isko clip karo" all work.
- **Put file paths in quotes**, especially when they have spaces. You can usually drag the file into
  the window to paste its path. (Windows: Shift + right-click the file → "Copy as path".)
- Keep a video file where it is until the clips are done: ClipKaro reads it from there and doesn't
  make a copy.
- YouTube links work best. Many other video sites work too, but YouTube is what ClipKaro is tested with.
- One video at a time works best. Send the next one when the first is done.

## 2. Add your own wishes

Write your wishes **in the same message**, in normal words. You can combine as many as you like:

> clip this video: https://youtu.be/... only the 3 best, under 40 seconds, captions a bit lower,
> no sound effects

The tables below show what you can say. The right-hand column shows what ClipKaro does behind the
scenes; you don't need to type that part.

### Always in every clip
In every mode (quick, standard, deep), with nothing to say:
- **Pauses cut out**: pauses of half a second or more inside a clip are shortened to a natural 0.2 s,
  and "um" / "uh" are cut out. Never across a laugh; in gameplay only pauses up to 2 s.
- **No made-up words in the captions**: where Whisper invents words (laughter, game noise, music), the
  caption stays empty. The sound itself stays in the clip.
- **Captions out of the way**: off faces in close-ups, and clear of the apps' buttons.
- **Emojis** on up to 3 strong words, unless you say "no emojis".
- **No sound too loud**: the loudest moments stay under the apps' limit, so they don't crackle after
  upload.
- **Credit to the source**: a small "© Channel name" in the bottom-left corner of clips made from a
  YouTube link, "© twitch.tv/name" from a Twitch link (never your own video files). Say "no credit" to
  leave it out.
- **Your logo and outro**, when you have put them in the `brand` folder (below).
- **Nothing censored**: gaali, abuse, slurs, taboo talk (sex, cheating, adult jokes) and A-rated
  moments stay in the clips, and every word is heard: no bleep, no mute. If the full video is on
  YouTube, it already passed YouTube's checks, and these are the moments that go viral. Racial and
  caste slurs never go in a title, because that is where YouTube removes videos fastest. A clip with a
  slur, or with a sexual scene or nudity on screen, gets a "platform risk" note in Claude's report, and
  you decide.
- **Rude words with stars in the text**: the captions on screen and the posting texts write abusive and
  taboo words like "F******" or "c******" (the first letter, then stars), because the apps read text
  first. The sound keeps them. Say "no stars" for one video, or set `"star_words": false` (below).
- **Bold takes count extra**: an unpopular opinion, a roast, a rant, a blunt verdict, a dark joke, gaali
  said with real feeling or taboo talk, the things most people are afraid to say out loud, is a chance
  to go viral, so it ranks higher. A slur on its own adds nothing: the take does. Don't want that? Set
  `"bold_clips": "neutral"` (below).

### Extras you switch on by name
Put the name in your message, as many as you like:

> clip this video: https://youtu.be/... **hook title, box captions**

| Name | What it adds |
|---|---|
| **hook title** | 3-6 big words on a coloured box for the first 2-3 seconds ("PAKISTAN KA PM BANOGE?"), in the upper part of the picture, never on a face |
| **box captions**, **karaoke captions**, **minimal captions**, **bold captions**, **comic captions** | another caption look (below); normally the classic look |
| **deep clips** | moments far apart joined into one story (see "Deep clips" below) |
| **quick** | uses much less of your Claude plan: Claude picks the clips alone |

They also work later, on clips you already have: "add a hook title to clip 3", "make clip 2 with box
captions". To have one every time, add it to your preferences.

### How many clips, and how long
| You write | What happens |
|---|---|
| (nothing) | ClipKaro decides: every good moment, from 3 up to 8 (as in v1.1), and for long videos up to about one per 7 minutes (at most 20, `max_clips` in settings.json). Break screens don't count |
| "at least 10 clips" / "kam se kam 10" | 10 or more, never fewer (if the video is thin, Claude says which ones are weaker) |
| "no limit" / "as many as possible" / "jitne ho sake" / "100+" | every decent moment, however many: a 4-hour stream can give 100 or more |
| "at most 5 clips" / "only the 3 best" | no more than that |
| "give me 8 clips" | exactly 8 |
| "only the first hour" / "from 20:00 to 1:10:00" / "pehle ek ghante ka hi" | only that part of the video is written down and clipped (`fetch --to 1:00:00`, `--from 20:00 --to 1:10:00`): faster, and handy when a stream kept recording after you stopped playing |
| "clips under 30 seconds" / "around 45-60 seconds" | that length (normally 25-60 seconds, never under 15 or over 90) |
| "one clip only, the strongest" | a single clip |

### Which moments
| You write | What happens |
|---|---|
| "only clips about money" / "focus on the funny parts" | only moments about that topic or with that mood |
| "include the part where she talks about her first business" | that moment becomes one of the clips |
| "skip the first 10 minutes" / "only from 20:00 to 45:00" | moments only from that part |
| "show me the moments first" / "let me approve the clips" | Claude stops after picking and waits for your OK |
| "it's a gameplay video" | clips are built around what the player says, not the game's own voices (ClipKaro usually finds this out by itself, see "Live streams and gameplay" below) |

### Language and listening
| You write | What happens |
|---|---|
| "the video is in Hinglish" / "it's in English" / "it's in Spanish" | uses that language (normally it's found automatically) |
| "the language came out wrong, do it again in English" | writes down the words again in English |
| "use the most accurate model" | uses the biggest speech model (slower) |
| "use the processor, not the graphics card" / "use the graphics card" | chooses where the listening runs |

### The look of the edit
| You write | What happens |
|---|---|
| "don't edit them, just cut" / "raw clips only" | stops after cutting (clips are in the `clips` folder) |
| "no sound effects" | no whooshes |
| "only one whoosh" / "fewer sound effects" | just one whoosh, at the start |
| "no zooms" | no zoom effects |
| "no captions" | no captions |
| (nothing) | **Captions stay clear** of faces and of the apps' own buttons (TikTok's right column and bottom text, the top bars of Shorts and Reels), and **pauses are cut out** (half a second or more, shortened to 0.2 s; "um" / "uh" removed; never across a laugh). No title on screen |
| "hook title" / "change clip 3's title to ..." | **a hook title**: 3-6 big words on a coloured box for the first 2-3 seconds ("PAKISTAN KA PM BANOGE?"), in the upper part of the picture, never on a face (`edit --hook-title`). Off unless you ask |
| "captions lower" / "captions higher" | moves the captions down or up (on that exact line: they don't move off faces then) |
| "box captions" / "karaoke captions" / "minimal captions" / "bold captions" / "comic captions" | another **caption look**: on a dark box; each word filling with colour as it's said; smaller in normal case; big Anton letters; tilted comic letters (`--look box`, or `"caption_look"` in settings.json to keep it). Normally the classic look |
| (nothing) | **emojis** on up to 3 strong words ("paisa" 💰, "shocking" 😱): they pop in above or beside the caption when the word is said, never on a face. Claude picks them; "no emojis" turns them off for that clip or that video |
| "no stars" | rude words in full in the captions (normally "F******": the first letter, then stars). The sound is the same either way: nothing is ever bleeped |
| "bigger captions" / "smaller captions" | changes the caption size |
| "captions not in capital letters" | normal upper and lower case |
| "use #00E5FF as the caption colour" / "yellow captions" | the highlight colour of the captions |
| "use the creator's brand colour" | Claude uses it if it knows it for sure; otherwise it picks a colour from the video |
| "Hindi captions in Hindi letters" | captions in Devanagari instead of English letters |
| "show how much time was skipped" / "add a time label at the jumps" | a small "27 MIN LATER" label for 1.6 s where a joined clip jumps in time (`--jump-label`) |
| "render with Remotion" | uses the optional second editor (slower; needs `python install.py --remotion`; free for individuals and small companies, [larger companies need a license](https://www.remotion.dev/license)) |

### Framing
| You write | What happens |
|---|---|
| "keep it wide" / "16:9" | keeps the original wide shape (instead of the standing clips) |
| "landscape copy" / "16:9 copy too" / "YouTube video version bhi" | the finished clips stay standing, and a wide 1920x1080 copy is made next to each (`edited/NN-title-landscape.mp4`): the same moment, captions, credit, logo, emojis and sound, placed for a wide frame; no zooms, no outro. Compilations longer than 1:30 always get one |
| "use the facecam layout" / "don't use the facecam layout" | gameplay on top and your webcam below, or not |
| "the webcam is in the bottom-left corner" | Claude saves the webcam's position in `settings.json` |
| (nothing: it's automatic) | in podcasts with two people on screen, the person talking is shown; around laughs and when they talk over each other, both are shown stacked (split screen) |
| "show both of them when Raj laughs at 2:10" / "show Khan Sir there, not Raj" | Claude changes the framing of that moment only |
| "show the whole picture when he holds up the box" | that moment shows the full landscape frame over a blurred background |

### Your logo and outro (your brand)
Put two files in the `brand` folder inside ClipKaro (it has a short note on what to put there):
- **`logo.png`**: your logo, right in the bottom-right corner of every clip (no gap),
  small and 70 % visible (like the credit: a formality, not something to read). A PNG with a see-through background looks best; JPG works too.
  A logo on a plain square (black, white or one colour) gets that background removed by itself.
- **`outro.mp4`**: your own outro, added after every clip. Make it **standing (9:16)** and **3-5
  seconds** long. Longer than 5 s: ClipKaro warns you; longer than 10 s: it is left out, so an outro is
  never longer than the clip. Its sound is evened out to the clip's volume.

There is no intro on purpose: a clip must open on its hook. Neither the logo nor the credit shows during
the outro. For one video, say "no logo" or "no outro"; for good, take the file out of the folder. The
plain cuts in `clips/` stay without them. Another corner: `"logo_corner"` and `"credit_corner"` in
settings.json (below), each `top-left`, `top-right`, `bottom-left` or `bottom-right`. In the same corner,
the credit sits right next to the logo.

### Sound effects by mood
ClipKaro plays two soft whooshes on its own, and a boom on a shocking line, a "boing" on a punchline
and so on from the **`sounds` folder** inside the ClipKaro folder, one folder per mood. `install.py`
fills it with a free starter set (33 sounds from Mixkit: free for videos, no credit needed; the list is
in `sounds/SOURCES.txt`). Delete any you don't like and add your own:

| Folder | For | Example sounds |
|---|---|---|
| `sounds/attention/` | a new point, "listen to this" | a riser, a ding, a notification |
| `sounds/shock/` | a shocking line or reveal | a deep boom, a bass drop, "dun dun" |
| `sounds/fear/` | something scary or tense | a suspense sting, a horror hit |
| `sounds/funny/` | a punchline, an awkward moment | a boing, a record scratch, "bruh" |
| `sounds/sad/` | a sad or emotional moment | a soft piano or violin sting |
| `sounds/hype/` | a big win | an air horn, a crowd cheer |
| `sounds/reveal/` | an answer, a result | a ta-da, a sparkle |
| `sounds/fail/` | a mistake | a wrong buzzer, a sad trombone |
| `sounds/money/` | money talk | a cash register, coins |

- **Any file name works** inside a mood folder (`.mp3`, `.wav`, `.m4a`, `.ogg`, `.flac`); a short
  sound (under 2.5 s) works best. A new folder (`sounds/romantic/`) becomes a new mood.
- **Without opening folders:** `python run.py sfx add "C:\Downloads\boom.mp3" shock`, or tell Claude
  "add this sound as shock: C:\Downloads\boom.mp3". A folder of sounds works too.
  `python run.py sfx` shows every mood and how many sounds it has; `python run.py sfx starter` downloads
  the starter set again into the folders that are empty (your own sounds are never touched).
- `run.py cut <project> --check` lists which moods the clips ask for and says when one has no sound.
- Claude then marks 0-2 moments per clip that call for one, only for moods that have sounds. Say
  "no sound effects" for none, or "a boom when he says the number" for a specific one.
- Use only sounds you may use in videos: Pixabay, Mixkit and the YouTube Audio Library give
  permission; a sound from someone else's video usually doesn't.

### Background music (on hold)
Background music from your own tracks is built, but **on hold**: it doesn't suit podcasts, so clips
get no music for now. It may come back later (`"music": true` in settings.json switches it on; the
`music` folder holds the tracks).

### Changes after you've seen the clips
| You write | What happens |
|---|---|
| "clip 2 starts too early, start at 'the real reason'" | Claude finds the exact moment and redoes only clip 2 |
| "make clip 1 shorter" / "end clip 3 on the punchline" | the same: only that clip is redone |
| "fix the spelling of 'Juyal' in clip 3's captions" / "'bow' should be 'boat'" | the word is corrected everywhere it was heard (`run.py fixword`) and the clips that have it are edited again |
| "make the captions bigger in all clips" | the edit is done again; the cuts stay |
| "change the posting caption of clip 4" | Claude rewrites it |
| "add one more clip about X" | adds one clip, and cuts and edits only that one |

### More clips later (without reading the video again)
While choosing, the critic scores **every** clip idea of a video (often 15-30), and only the best
become clips. The others stay saved with their scores and exact times. At the end Claude tells you,
for example, "6 more good ideas are saved". Any time later, even days after:

| You write | What happens |
|---|---|
| "more clips from the Khan Sir video" | the next 3 ideas become clips (Claude says how many are left) |
| "3 more clips from <video>" | the next 3, best first |
| "clips 9-12 too" | enough of them for 12 clips in all |
| "show me the ideas you didn't cut" | the list, best first, with scores (`more.txt`) |
| "add idea 2 and 5" | exactly those from the list |

Only the new clips are written, cut and edited; it takes a few minutes and little of your Claude
plan, because nothing is read again. The new clips are added to post.json for PostKaro. When no
ideas are left, "find more clips in this video" reads it again.

### Downloading
| You write | What happens |
|---|---|
| "YouTube says sign in to confirm you're not a bot" / "try again" | uses the cookies file in the ClipKaro folder (your YouTube login, saved once with a browser extension: [how](troubleshooting.md#youtube-asks-you-to-sign-in)) |
| "use my Firefox cookies" | downloads using your browser's YouTube login (Firefox anywhere; Chrome or Edge on Mac and Linux) |

### Long videos (podcasts of an hour or more)
| You write | What happens |
|---|---|
| (nothing: it's automatic) | a long video is read in parts of about 20 minutes, all at the same time, so no part is skimmed; then all the moments found are judged together |
| (nothing: it's automatic) | if the creator's own teaser at the start, or YouTube's "most replayed" graph, points at a moment nobody picked, that stretch is read again carefully |
| "show me the topic map" | Claude shows `topics.txt`: every topic with its time, what it's about, and the key lines |

### Quick (basic), standard or deep (advanced)
The README has a side-by-side chart of the three modes and when each one fits best.

| You write | What happens |
|---|---|
| (nothing) | **standard**: the best quality. Long videos are read by several AI readers at once, a second AI editor (the critic) checks every idea, the clips with notes are repaired, and Claude checks every clip's captions for misheard words |
| "deep clip this", "use deep clipping", "advanced mode", or **yes** to the question for videos over 21 minutes | **deep**: standard, plus clips that join moments far apart (see "Deep clips" below) |
| "quick clip this", "quick mode", "basic mode", "use fewer tokens", "save my Claude limit", "jaldi clip karo" | **quick**: Claude reads the video itself and picks the clips, without the readers, the critic and the caption check. It uses much less of your Claude plan (about what v1.1 used) and is faster; the picks get no second opinion, and misheard words stay as the speech model wrote them. No deep-clip question is asked |

Everything after picking is the same in all three (except the caption check, which quick mode
skips): captions, Hinglish spelling, game voices, break screens, cutting, the edit and the posting texts. Write "always use quick mode" under "My
preferences" in CLAUDE.md to make quick your default.

### The second opinion (standard and deep)
| You write | What happens |
|---|---|
| (nothing: it's automatic) | before anything is cut, a second AI editor, the **critic**, checks every clip idea three times, without knowing who picked it. Every idea gets a **clip score** out of 10, with reasons, and the best ones are used. A clip that needs earlier context, or whose punchline comes after the cut, gets a note, and Claude repairs it |
| "show me all the clip ideas" | Claude shows `critic.txt`: every idea with its score, the reasons and any notes |
| "give me all the good clips" | more clips than usual, taken from the top of the critic's list |
| "give me only clips with 7 or more" | only clips with a clip score of 7/10 or more are used |

A clip score judges how well-made a clip looks from its words and sound (hook, payoff, feeling,
how shareable it is), compared with the other moments of the same video. It is **not** a
prediction of views: views also depend on your channel, the timing and luck.

### Live streams and gameplay (nothing to say)
ClipKaro finds out by itself when a video is a **live stream** (YouTube says it was live, or a "Be
right back" screen sits in the middle) or **gameplay** (YouTube's Gaming category, or your webcam in
a corner of the picture). Then:
- **"Starting soon", "Be right back" and stream-ending screens are left out.** It looks for a
  picture that stands still for 30 seconds or more with nobody in the webcam. A pause menu or a map
  while you talk in the webcam is real video and stays in. Claude can show you a picture of each
  break it found ("show me the break screens").
- **Clips are built around what you say**, not the game's own characters and music.
- **Quiet stretches are expected.** You play without talking for a while; that's normal. A clip
  doesn't keep a long silence unless the gameplay itself is the point (a chase, a crash).
- **Stream housekeeping is left out**: hello chat, "is the audio OK", viewer counts, "I'm back".
- **Game characters are told apart from you.** Lines in another voice than yours are marked
  "(other voice)" in what Claude reads, so clips are built around your words, not the cutscenes.
- **No captions for game characters.** The game already shows its own subtitles, so ClipKaro's
  captions show only you and your friends (their sound stays, and a great game scene can still be in a
  clip). This works when you speak Hindi or Hinglish and the game speaks English: a line counts as the
  game's only when it is real English words, so your friends' Hinglish ("Kisko khaoon?", "Main kama
  loon") keeps its captions. A friend speaking English sounds like the game to ClipKaro, so Claude's
  caption check brings those lines back by hand. `"game_voice_captions": true` captions everything.
- **You speak English too?** Then the language can't tell you apart from the game, so ClipKaro looks at the
  game's own subtitles instead: a line whose words are on screen in the subtitle area while it is said is the
  game talking, and gets no caption. Turn the game's subtitles on when you stream. If the game shows none,
  every line keeps its captions, as before. (A small text reader, about 10 MB, downloads the first time.)
- **Your microphone on its own track?** If you record with OBS and keep the microphone on its own audio
  track, give ClipKaro that file: it writes down your words from the microphone alone (no game sound,
  no game characters) and keeps the full sound in the clips.

If ClipKaro ever takes real video for a break screen, say "break 2 is real video" and it comes back.

### Deep clips: one story from moments far apart
For a video **longer than 21 minutes**, Claude asks once at the start: "do you want deep clips too?"
You can answer in the first message instead, and then it doesn't ask. To never be asked, set
`"deep_clips"` in settings.json to `"always"` or `"never"`.

| You write | What happens |
|---|---|
| "deep clip this: <link>", "clip this, use deep clipping" or "clip this, then go deeper" | the regular clips first, then Claude looks for stories spread across the video (a question and its answer much later, an opening line and the story's payoff) and joins 2-3 of those moments into one short |
| "do a deep pass on <video>" | the same, for a video you've already clipped |
| "show me the deep clip report" | Claude shows `deep/report.txt`: every deep clip tried, its clip score next to the best single stretch, and why it was kept or not |

A deep clip is kept only when it scores at least as well as the best single stretch, **and** at
least two of three separate honesty judges agree it keeps what the person meant. If one judge has
a doubt, the clip is kept and Claude tells you that judge's reason, so you can check it before
posting. A clip the judges reject for something a few seconds would fix (a "but..." cut off right
after a piece, or an answer without its question) gets one repair: Claude keeps those seconds, and
the clip is scored and judged again from scratch. Often no deep clip passes: that's
normal, and Claude says so. A kept clip shows a short white flash where it jumps in time. Where its
moments are in the full video ("From 2 moments of the full video: 35:30 · 1:03:01") is in Claude's
report for you, not in the posting texts; the caption ends with the full video link.
(`"joined_note": true` in settings.json puts that line back at the top of the posting texts.) A deep pass takes extra time: about 10-15 more minutes (measured: 10 minutes for
a 68-minute interview, 13 for a 2-hour podcast).

### Can I write anything else?
Yes. Claude is an AI, so you can ask in your own words, in English, Hindi or Hinglish. If you ask
for something ClipKaro **can't do yet**, Claude tells you instead of pretending. Examples: extra
footage, stickers or translated subtitles (background music is built but on hold).
If you want, you can ask Claude to **change ClipKaro's code** to add such a feature: it's your
copy, and [architecture.md](architecture.md) shows where everything is.

## 3. Your lasting wishes: "My preferences"

If you always want the same things, you don't have to repeat them every time. Write them once at the
bottom of the file **`CLAUDE.md`** (in the ClipKaro folder), under **"My preferences"**, one per line:

```
- My videos are in English.
- Always give me 5 clips, 30-45 seconds long.
- My brand colour is #00E5FF.
- No sound effects.
```

Or ask Claude: **"add to my preferences: always give me 5 clips"**. Claude reads this file every time
it starts in the ClipKaro folder, and follows your preferences unless you ask for something else in
a message.

## 4. What you get

Everything goes into `output/<project>/`. `<project>` is a folder named after the video, for example
`output/my-podcast-episode-12-dQw4w9WgXcQ/`:

| Folder / file | What it is |
|---|---|
| `edited/01-title.mp4` | **the finished short videos** (1080x1920, ready for phones): upload these |
| `edited/01-title.srt` | the captions as a separate subtitle file, for apps that accept one |
| `clips/01-title.mp4` | the cut videos without zooms, captions or sounds (also fine to post) |
| `clips.json` | the chosen moments: titles, times, clip scores, highlighted words and **the text to post** on YouTube, Instagram and Facebook |
| `post.json` | the finished clips with their posting text, for PostKaro (see below) |
| `critic.txt` | every clip idea, ranked by its clip score, with the critic's reasons and notes |
| `transcript/transcript.txt` | everything that was said, with times |

Claude's last message lists each clip with its length, file and a caption to post.

### Posting your clips (PostKaro)
PostKaro is ClipKaro's partner app: it posts the clips to YouTube Shorts, Instagram Reels and your
Facebook Page from your own laptop, each at its own time. It is a separate install (its own folder
and README), on Windows, Mac and Linux: tell Claude "install PostKaro too", or see
[installation.md](installation.md#postkaro-the-posting-app-optional). When it is installed, Claude's last message ends with **"Post them: <link>"**. Click it:
every clip is there with its title and caption for each platform, ready to check and schedule.
Without PostKaro, upload the files in `edited/` yourself; the text for each platform is in
`clips.json` under `post`.

## 5. Your defaults: `settings.json`

The file `settings.json` in the ClipKaro folder holds your default settings. You can also just ask
Claude to change them.

```json
{
  "language": "auto",
  "model": "auto",
  "device": "auto",
  "hinglish_captions": "roman",
  "layout": "auto",
  "facecam": null,
  "facecam_margins": {"left": 50, "right": 50, "top": 50, "bottom": 30},
  "jump_label": false,
  "deep_clips": "ask",
  "max_clips": 20,
  "bold_clips": "boost",
  "star_words": true,
  "joined_note": false,
  "hook_title": false,
  "safe_zones": true,
  "jump_cuts": true,
  "action_pauses": "smart",
  "caption_look": "classic",
  "emoji": true,
  "music": false,
  "hinglish_model": "auto",
  "game_voice_captions": false,
  "game_subtitles": true,
  "hints": true,
  "source_credit": true,
  "logo": true,
  "outro": true,
  "logo_corner": "bottom-right",
  "credit_corner": "bottom-left",
  "logo_background": "remove",
  "live_folder": "<your OBS recording folder>",
  "twitch_channel": "<your Twitch channel>",
  "twitch_delay": 10,
  "live_post": "now",
  "live_vram_mb": 2800,
  "encoder": "auto",
  "render_workers": "auto",
  "cookies_file": null
}
```

| Setting | Normally | Choices |
|---|---|---|
| `language` | `auto` (found automatically) | `auto`, `hinglish`, `en`, `hi`, or any [Whisper language code](https://github.com/openai/whisper/blob/main/whisper/tokenizer.py) (`es` Spanish, `fr` French, `de` German, ...) |
| `model` | `auto` | `auto` (the big `large-v3-turbo` with an NVIDIA card or for Hindi/Hinglish, otherwise the smaller `small.en`/`small`), `large-v3`, `medium`, `small`, `base`, ... |
| `device` | `auto` | `auto` (the NVIDIA card if it works, otherwise the processor), `cuda` (the NVIDIA card), `cpu` (the processor) |
| `hinglish_captions` | `roman` | `roman` (English letters: "aaj hum baat karenge"), `devanagari` (Hindi letters: "आज हम बात करेंगे") |
| `layout` | `auto` | `auto` (facecam layout when a webcam is found in a gameplay video), `facecam`, `crop` |
| `deep_clips` | `ask` | `ask` (for a video longer than 21 minutes, Claude asks once whether you want deep clips too), `always`, `never` |
| `max_clips` | `20` | the most clips a long video gets when you don't ask for a number (a number you ask for, or "no limit", always wins) |
| `careful_listening` | `true` | Hindi/Hinglish gameplay and live streams on an NVIDIA card: a second speech model hears the whole video for Claude's readers, two more hear every picked clip, and helpers check every caption word (about 6 minutes of graphics card per hour of video, plus some Claude usage). It waits while live clipping runs, and stays off with `"device": "cpu"`; `false`: off |
| `unsure_words` | `hide` | careful listening: a word the hearings can't settle gets no caption (the sound stays); `ask`: listed in `word-check.json` for you to correct by ear: write what was really said in "correct" ("-" for no caption), then tell Claude "word check done" and the clips are fixed |
| `watch_gameplay` | `true` | gameplay and live streams: Claude's readers also see the video (a frame every 10 s, with the loud moments marked), close-ups where they point, and clips that start where something happens on screen (about 15-20 % more Claude usage on such videos; never on podcasts or talks, and not during live clipping); `false`: off |
| `event_lead_in` | `true` | with frame sheets: a clip that starts on a reaction starts at its event instead; `false`: events only become new clips |
| `action_pauses` | `smart` | gameplay and streams: a pause where the picture changes a lot stays in only when something shows that it mattered: a game sound burst in it, or right after it a laugh, a shout, a reaction word ("arre", "ye kya", "bhai") or a voice clearly louder than before. A camera swing with no reaction is cut as usual. `keep`: every pause with a lot of picture change stays (v2.7.1); `cut`: pauses are cut by the sound alone (v2.7) |
| `sound_onset` | `moment` | a sound effect starts on its moment, never more than 0.1 s before it; `peak`: its loudest point on the moment, as before v2.7 (a slow sound then starts early) |
| `private_details` | `hide` | gameplay and streams: an email address or phone number said out loud (letters and digits said one after another, or 9+ digits) is left out of what Claude reads and cut out of every clip; `all`: checked on every video, podcasts too; `keep`: treated like any other words |
| `overlap_clips` | `streams` | in gameplay and streams, two clips may share some seconds when they clearly differ (a short and a long cut of one moment, a joined clip), so you choose which to post; never near-copies, at most 3 clips per moment. Other videos keep one clip per moment. `allow`: overlaps everywhere; `avoid`: nowhere, as before v2.7 |
| `bold_clips` | `boost` | `boost`: bold, honest takes (an unpopular opinion, a roast, a rant, a dark joke, gaali said with feeling, taboo talk, an A-rated moment) rank higher when Claude picks and when the second editor judges; `neutral`: they rank like any other moment, as before. Either way nothing is cut, bleeped or scored down because of the words |
| `joined_note` | `false` | a clip joined from moments far apart (deep clips): its titles and captions say nothing about it; where the moments are stays in clips.json and Claude's report. `true`: "From 2 moments of the full video: ..." first and "(2 moments joined)" in the YouTube title, as before |
| `star_words` | `true` | abusive and taboo words written with stars in the captions and the posting texts ("F******"); the sound keeps every word. `false`: every word in full ("no stars" does it for one video) |
| `hook_title` | `false` | `true`: a 3-6 word title on screen for the first seconds of every clip ("hook title") |
| `caption_look` | `classic` | `classic`, `box`, `karaoke`, `minimal`, `bold`, `comic` |
| `emoji` | `true` | `false`: no emojis on the words |
| `music` | `false` | on hold: `true` plays background music from your own `music` folder |
| `hinglish_model` | `auto` | the speech model for Hindi and Hinglish videos: `auto` (the Hinglish model with an NVIDIA card and English-letter captions; `large-v3-turbo` otherwise), `large-v3-turbo` (as before v2.3), or another model name |
| `game_subtitles` | `true` | gameplay with an English streamer: a line the game's own subtitles show on screen gets no caption (a text reader reads the subtitle area); `false`: not read, every line captioned as before |
| `game_voice_captions` | `false` | gameplay with a Hindi/Hinglish streamer: game characters' lines get no captions, because the game shows its own subtitles (their sound stays); `true`: captioned too, as before v2.3 |
| `hints` | `true` | notes next to the words Claude reads (`[voice raised]`, `[explosion]`, `(other voice)` ...); `false`: the plain transcript, as in v1.1 |
| `source_credit` | `true` | "© Channel name" in the bottom-left corner of clips made from a YouTube link ("© twitch.tv/name" from Twitch, "© kick.com/name" from Kick; never your own files); `false`: no credit, as before v2.4 |
| `credit_text` | `null` | your own words for the credit; `{channel}` becomes the channel's name, e.g. `"clipped from {channel}"` |
| `logo` | `true` | your logo from `brand/` in the bottom-right corner, when the file is there; `false`: never |
| `outro` | `true` | your outro from `brand/` after every clip, when the file is there; `false`: never |
| `logo_corner` | `bottom-right` | where your logo goes, right in the corner: `top-left`, `top-right`, `bottom-left`, `bottom-right` |
| `credit_corner` | `bottom-left` | where the "© Channel name" credit goes: the same four corners |
| `logo_background` | `remove` | a plain background around your logo (a black or white square) is made see-through, so only the logo shows; `keep`: the logo exactly as it is |
| `encoder` | `auto` | `auto` (the NVIDIA card's video encoder when it works: 3x faster, same picture, files about 1.3x bigger), `nvenc`, `x264` (the processor, as before) |
| `render_workers` | `auto` | clips edited at the same time: `auto` (2 with 4+ processor cores and 4+ GB of free memory, else 1), or a number |
| `cookies_file` | `null` | a cookies file with your YouTube login, for when YouTube asks "confirm you're not a bot" (used only then). Without it, `cookies.txt` (or the extension's `www.youtube.com_cookies.txt`) in the ClipKaro folder is found by itself. How to make one: [troubleshooting.md](troubleshooting.md#youtube-asks-you-to-sign-in) |
| `live_folder` | `"<your OBS recording folder>"` | live clipping: the folder OBS records into, e.g. `"D:/OBS_Recording"`. A `"<...>"` placeholder counts as not set: the first time you start live clipping, Claude asks and writes your answer here ([live-clipping.md](live-clipping.md#3-your-obs-folder-and-twitch-channel-in-settingsjson)) |
| `twitch_channel` | `"<your Twitch channel>"` | live clipping: your Twitch channel name, for the chat and viewer-clip hints. A placeholder too: Claude asks the first time (answer "none" if you don't stream on Twitch) |
| `twitch_delay` | `10` | live clipping: seconds your Twitch viewers are behind you (their reactions are moved this much earlier) |
| `live_post` | `now` | live clipping: `now` posts every clip at once; `dry` is for a test stream: PostKaro only shows what it would post ("turn on test mode" / "turn off test mode") |
| `live_vram_mb` | `2800` | live clipping: the words are written down on the graphics card only when OBS leaves at least this much of its memory free (MB); otherwise on the processor |
| `jump_cuts` | `true` | `false`: every pause kept, as in v1.1 (only as a way back; pause cutting is part of every clip) |
| `safe_zones` | `true` | `false`: captions on one fixed line and up to 940 px wide, as in v1.1 (only as a way back: they may cover a chin or sit under TikTok's buttons) |
| `jump_label` | `false` | `true`: a small "27 MIN LATER" label where a deep clip jumps in time (the white flash and a soft whoosh are always there) |
| `facecam` | `null` | only if the webcam is found in the wrong place (it is found by itself, also with two or three people in it): the webcam's fixed position, as parts of the picture: `{"x": 0.80, "y": 0.35, "w": 0.19, "h": 0.34, "shape": "circle"}` (`x` left, `y` top, `w` width, `h` height; `shape` is `circle` or `rect`) |
| `facecam_margins` | `{"left": 50, "right": 50, "top": 50, "bottom": 30}` | gameplay with a webcam: the free space (in pixels of the 1080x1920 clip) kept around the webcam below the game. The webcam grows until one side reaches it: a 16:9 webcam fills the width, a round one the height. The top space keeps the captions off the webcam. `{"left": 60, "right": 60, "top": 90, "bottom": 30}` is the smaller webcam of before |

## 6. Doing the steps by hand (optional)

You don't need Claude for the mechanical steps. Each one is a command you type in the ClipKaro
folder (`python3` instead of `python` on Mac/Linux):

```bash
python run.py fetch "<link or file>"            # 1. download the sound, write down the words; shows the <project> name
# 2. write output/<project>/clips.json yourself (format: docs/architecture.md, part 4)
python run.py critic <project>                  # 2a. optional: packets for a blind second opinion (see the skill)
python run.py romanize <project>                # 2b. Hindi/Hinglish: lists the words for romanize.json
python run.py cut <project> --check             # 3a. check where the clips start and end (cuts nothing)
python run.py cut <project>                     # 3b. standing clips → output/<project>/clips/
python run.py brand <project> --accent "#FFD60A"  # 4. optional: the caption colour
python run.py edit <project>                    # 5. the edit → output/<project>/edited/
```

### All commands and options
| Command | Options |
|---|---|
| `run.py fetch <link or file>` | `--lang auto\|hinglish\|en\|hi\|<code>`, `--model auto\|large-v3-turbo\|large-v3\|medium\|small\|small.en`, `--device auto\|cuda\|cpu`, `--beam N`, `--cookies-from-browser chrome\|firefox\|edge`, `--cookies <file>`, `--retranscribe` |
| `run.py romanize <project>` | `--clips 1,3` |
| `run.py cut <project>` | `--check`, `--clips 1,3`, `--horizontal`, `--layout auto\|facecam\|crop` |
| `run.py brand <project>` | `--accent "#RRGGBB"`, `--text "#RRGGBB"`, `--outline "#RRGGBB"`, `--note "why"`, `--reset` |
| `run.py edit <project>` | `--clips 2`, `--jump-label` / `--no-jump-label`, `--engine python\|remotion`, `--sfx auto\|light\|none`, `--no-zoom`, `--no-captions`, `--no-upper`, `--caption-y 1270` (bigger number = lower), `--size 96`, `--out <folder>`, `--no-credit`, `--no-logo`, `--no-outro`, `--logo-corner`, `--credit-corner` |
| `run.py more <project>` | `--add 3` (the next 3 ideas become clips), `--upto 12` (enough for 12 clips), `--pick 2,5` (those from the list) |
| `run.py qa <project>` | checks every finished clip and writes `qa.txt`: FAIL (fix first) for Hindi letters in Roman captions, captions outside the safe zone, a cut inside a word, loudness far off -14 LUFS, black frames, a stale edit; CHECK for captions over a face, a frozen picture, a flash at the end, a short clip, many words without captions. `--clips 2,5` |
| `run.py test` | ClipKaro's own tests (a second; no video needed): run after changing the code. `--full` also runs a tiny made-up video through cut, edit and qa (about 30 seconds) |
| `run.py music` | lists your music moods; `add "<file or folder>" <mood>` adds tracks, `remove <file name>` takes one out |
| `run.py sfx` | lists your sound moods; `add "<file or folder>" <mood>` adds sounds, `remove <file name>` takes one out |
| `run.py tidy <project>` | no captions for words made up during laughter, noise ("झाल") or loops, for videos transcribed before (`fetch` does it by itself); `--dry` |
| `run.py fixword <project> "wrong" "right"` | `--at 2107.5` (only the place nearest that second), `--dry` (show what would change) |
| `run.py find <project> "exact phrase"` | `--near 470` (only matches within 60 seconds of that time) |
| `run.py parts <project>` | `--minutes 21` (each part's own stretch), `--margin 120` (context seconds on each side); tests: `--no-chapters`, `--shift 0.5`, `--dir` |
| `run.py topics <project>` | `--check` (check topics.json again after editing it), `--rebuild`, `--dir` |
| `run.py sound <project>` | measures laughs, applause, both talking at once, game sound bursts and lively spots (`fetch` does this by itself) |
| `run.py voices <project>` | who speaks each line: the main voice and up to two more (`hints` runs it) |
| `run.py captions <project>` | every picked clip's captions as viewers will read them, with times, for Claude's caption check (fix a misheard word with `fixword "<word>" "<right>" --at <seconds>`); `--clips 2,5` |
| `run.py hints <project>` | the notes next to the words: a raised voice, shouting, game sounds, big action on screen, other voices in gameplay; for videos fetched before v2.3 (`fetch` does it by itself) |
| `run.py critic <project>` | `--fresh` (start over), `--from clips\|candidates\|deep` (what to judge), `--runs 3` |
| `run.py deep <project>` | run again after each helper step, it does the next stage itself; `--fresh` (start over; earlier files go to `deep/old/`) |
| `run.py honesty <project>` | first run: one packet per deep clip for the three honesty judges; second run: merges their verdicts; `--fresh` (start over) |
| `run.py asr-bench make` / `run [model]` / `report` | a small speech-to-text test on your own videos (Hindi, Hinglish, English): `make` cuts four ~3-minute snippets and draft texts into `output/_asrbench/`; correct the texts by ear once; `run` scores a model (the share of words wrong, compared by sound so Devanagari and Roman Hinglish count the same); `report` lists every model tried, best first, per test set. `public` also downloads two public test sets with checked texts (Hinglish conversation, everyday Hindi). A model can be one folder of a repo: `owner/repo:int8`. Switch models only when one clearly wins |
| `run.py relisten <project>` | listens again to unclear speech (game voices, film clips) in videos transcribed before Nov 2026: clear English replaces nonsense, the rest gets no captions; then re-cut the clips it names. `--stretched`: hears again the words Whisper skipped (one "word" stretched over several), for videos transcribed before v2.3. `--current`: starts from the words as they are now (caption fixes stay, hidden words stay hidden) |
| `run.py frames <project>` | `--clips 1,3`, `--every 1.5`: picture sheets showing what the crop keeps, before or after cutting |
| `run.py live start\|next\|done\|status\|stop <name>` | live clipping while you stream ([live-clipping.md](live-clipping.md)): `start <name> --folder "<OBS folder>" --twitch <channel>` (keeps running), `keys --client-id ID --client-secret SECRET` (Twitch viewer clips) |
| `run.py post <project>` | `--open` (open the PostKaro link in the browser), `--now` (live clipping: post every clip everywhere at once through PostKaro; `--dry` or `"live_post": "dry"` only shows it). Writes `post.json`; prints the PostKaro link when PostKaro is installed |
| `run.py gpu [model]` | tests the NVIDIA graphics card (default model `tiny`; try `large-v3-turbo`) |

Add `-h` to any command to see its help, for example `python run.py cut -h`.

### Command reference
The same, as a quick list: `fetch` (listen) → `romanize` (Hindi captions) → `cut` (standing clips)
→ `brand` (colour, optional) → `edit` (the finished look). Helpers: `find` (exact times),
`frames` (what the crop keeps), `gpu` (graphics-card test). Long videos: `parts` (split the
transcript for careful reading) and `topics` (join the readers' answers into a topic map and one
list of clip candidates).

## 7. Make it your own
- **Your own sound effects**: put `.mp3` or `.wav` files into `assets/sfx/`, with `whoosh`, `hit` or
  `click` in the file name. They're found automatically. Only use sounds you're allowed to use.
- **A different caption font**: see "Where to change things" in [architecture.md](architecture.md#8-where-to-change-things).
- **Another language**: see [languages.md](languages.md) and [adding-a-language.md](adding-a-language.md).

## 8. Good to know
- **Watch your clips once before posting.** The automatic captions are very good, but not perfect,
  especially for fast or noisy Hindi. Claude fixes obvious mistakes while writing the captions.
- **Only clip videos you own or have permission to use**, and follow each app's rules.
- Nothing is uploaded anywhere. Your videos and clips stay in the `output` folder on your computer.
- Using another AI helper instead of Claude Code? See [AGENTS.md](../AGENTS.md).
