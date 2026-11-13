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

### How many clips, and how long
| You write | What happens |
|---|---|
| (nothing) | ClipKaro decides: every good moment, from 3 up to 8 (as in v1.1), and for long videos up to about one per 7 minutes (at most 20, `max_clips` in settings.json). Break screens don't count |
| "at least 10 clips" / "kam se kam 10" | 10 or more, never fewer (if the video is thin, Claude says which ones are weaker) |
| "at most 5 clips" / "only the 3 best" | no more than that |
| "give me 8 clips" | exactly 8 |
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
| (nothing) | **a hook title**: 3-6 big words on a coloured box for the first 2-3 seconds ("PAKISTAN KA PM BANOGE?"), in the upper part of the picture, never on a face. **Captions stay clear** of faces and of the apps' own buttons (TikTok's right column and bottom text, the top bars of Shorts and Reels) |
| (nothing) | **jump cuts**: pauses of half a second or more inside a clip are shortened to a natural 0.2 s, and filler sounds ("um", "uh", "hmm") are cut out, so the clip feels tight. Never across a laugh; in gameplay and live streams only pauses up to 2 s (a longer quiet stretch may be the action) |
| "keep the pauses" / "no jump cuts" | the clip plays without cuts inside a piece, as before (`cut --no-jump-cuts`) |
| "no hook title" / "change clip 3's title to ..." | no title on screen (`--no-hook-title`), or a different one |
| "captions exactly where they were" | captions on one fixed line again, the full width (`--no-safe-zones`) |
| "captions lower" / "captions higher" | moves the captions down or up (on that exact line: they don't move off faces then) |
| "box captions" / "karaoke captions" / "minimal captions" / "bold captions" / "comic captions" | another **caption look**: on a dark box; each word filling with colour as it's said; smaller in normal case; big Anton letters; tilted comic letters (`--look box`, or `"caption_look"` in settings.json to keep it). Normally the classic look |
| (nothing) | **emojis** on up to 3 strong words ("paisa" 💰, "shocking" 😱): they pop in above or beside the caption when the word is said, never on a face. Claude picks them; "no emojis" turns them off |
| "add background music" / "no music" | music from **your own** music folder (see below), or none |
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
| "keep it wide" / "16:9" | keeps the original wide shape |
| "use the facecam layout" / "don't use the facecam layout" | gameplay on top and your webcam below, or not |
| "the webcam is in the bottom-left corner" | Claude saves the webcam's position in `settings.json` |
| (nothing: it's automatic) | in podcasts with two people on screen, the person talking is shown; around laughs and when they talk over each other, both are shown stacked (split screen) |
| "show both of them when Raj laughs at 2:10" / "show Khan Sir there, not Raj" | Claude changes the framing of that moment only |
| "show the whole picture when he holds up the box" | that moment shows the full landscape frame over a blurred background |

### Sound effects by mood (your own sounds)
ClipKaro plays two soft whooshes on its own. For more (a boom on a shocking line, a "boing" on a
punchline), add your own sounds, sorted by mood, in the **`sounds` folder** inside the ClipKaro folder:

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
  `python run.py sfx` shows every mood and how many sounds it has.
- Claude then marks 0-2 moments per clip that call for one, only for moods that have sounds. Say
  "no sound effects" for none, or "a boom when he says the number" for a specific one.
- Use only sounds you may use in videos: Pixabay, Mixkit and the YouTube Audio Library give
  permission; a sound from someone else's video usually doesn't.

### Background music (your own tracks)
ClipKaro ships no music: songs are copyrighted, and YouTube, Instagram and Facebook mute or block
clips with music you may not use. Put tracks you may use in the **`music` folder** inside the
ClipKaro folder, one folder per mood:

| Folder | For |
|---|---|
| `music/chill/` | calm talk, explanations, a relaxed story (lo-fi, soft beats) |
| `music/upbeat/` | light, positive, quick |
| `music/hype/` | gaming wins, sport, big energy |
| `music/suspense/` | mystery, tension, true crime |
| `music/emotional/` | sad or touching stories (piano, strings) |
| `music/funny/` | comedy, awkward moments |
| `music/inspiring/` | motivation, success stories |

- Any file name; a new folder is a new mood. Or `python run.py music add "C:\Downloads\lofi.mp3" chill`,
  or tell Claude "add this music as chill: <file>". `python run.py music` shows what you have.
- Claude picks a mood for each clip that suits one; the music plays from its start, about 10 dB under
  the voice, quieter still while someone talks, and fades in and out.
- Free sources: the YouTube Audio Library (check each track's licence before posting outside
  YouTube) and Pixabay Music.

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
| "YouTube says sign in to confirm you're not a bot" / "use my Firefox cookies" | downloads using your browser's YouTube login (Chrome, Firefox or Edge) |

### Long videos (podcasts of an hour or more)
| You write | What happens |
|---|---|
| (nothing: it's automatic) | a long video is read in parts of about 20 minutes, all at the same time, so no part is skimmed; then all the moments found are judged together |
| (nothing: it's automatic) | if the creator's own teaser at the start, or YouTube's "most replayed" graph, points at a moment nobody picked, that stretch is read again carefully |
| "show me the topic map" | Claude shows `topics.txt`: every topic with its time, what it's about, and the key lines |

### Quick, standard or deep
| You write | What happens |
|---|---|
| (nothing) | **standard**: the best quality. Long videos are read by several AI readers at once, a second AI editor (the critic) checks every idea, and the clips with notes are repaired |
| "deep clip this", "use deep clipping", or **yes** to the question for videos over 21 minutes | **deep**: standard, plus clips that join moments far apart (see "Deep clips" below) |
| "quick clip this", "quick mode", "use fewer tokens", "save my Claude limit", "jaldi clip karo" | **quick**: Claude reads the video itself and picks the clips, without the readers and the critic. It uses much less of your Claude plan (about what v1.1 used) and is faster; the picks get no second opinion. No deep-clip question is asked |

Everything after picking is the same in all three: captions, Hinglish spelling, game voices, break
screens, cutting, the edit and the posting texts. Write "always use quick mode" under "My
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
normal, and Claude says so. A kept clip shows a short white flash where it jumps in time, and its
posting caption starts with a line like "From 2 moments of the full video: 35:30 · 1:03:01" and the
full video link. A deep pass takes extra time: about 10-15 more minutes (measured: 10 minutes for
a 68-minute interview, 13 for a 2-hour podcast).

### Can I write anything else?
Yes. Claude is an AI, so you can ask in your own words, in English, Hindi or Hinglish. If you ask
for something ClipKaro **can't do yet**, Claude tells you instead of pretending. Examples: background
music, extra footage, emojis and stickers, translated subtitles, or posting to the apps for you.
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
and README). When it is installed, Claude's last message ends with **"Post them: <link>"**. Click it:
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
  "jump_label": false,
  "deep_clips": "ask",
  "max_clips": 20,
  "hook_title": true,
  "safe_zones": true,
  "jump_cuts": true,
  "caption_look": "classic",
  "emoji": true,
  "music": true,
  "encoder": "auto",
  "render_workers": "auto"
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
| `max_clips` | `20` | the most clips a long video gets when you don't ask for a number (a number you ask for always wins) |
| `hook_title` | `true` | `false`: no 3-6 word title on screen for the first seconds |
| `caption_look` | `classic` | `classic`, `box`, `karaoke`, `minimal`, `bold`, `comic` |
| `emoji` | `true` | `false`: no emojis on the words |
| `music` | `true` | `false`: no background music, even when you have tracks |
| `encoder` | `auto` | `auto` (the NVIDIA card's video encoder when it works: 3x faster, same picture, files about 1.3x bigger), `nvenc`, `x264` (the processor, as before) |
| `render_workers` | `auto` | clips edited at the same time: `auto` (2 with 4+ processor cores and 4+ GB of free memory, else 1), or a number |
| `jump_cuts` | `true` | `false`: no pauses or filler sounds cut out of the clips |
| `safe_zones` | `true` | `false`: captions on one fixed line and up to 940 px wide, as in v1.1 (they may cover a chin in a close-up or sit under TikTok's buttons) |
| `jump_label` | `false` | `true`: a small "27 MIN LATER" label where a deep clip jumps in time (the white flash and a soft whoosh are always there) |
| `facecam` | `null` | the webcam's fixed position, as parts of the picture: `{"x": 0.80, "y": 0.35, "w": 0.19, "h": 0.34, "shape": "circle"}` (`x` left, `y` top, `w` width, `h` height; `shape` is `circle` or `rect`) |

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
| `run.py fetch <link or file>` | `--lang auto\|hinglish\|en\|hi\|<code>`, `--model auto\|large-v3-turbo\|large-v3\|medium\|small\|small.en`, `--device auto\|cuda\|cpu`, `--beam N`, `--cookies-from-browser chrome\|firefox\|edge`, `--retranscribe` |
| `run.py romanize <project>` | `--clips 1,3` |
| `run.py cut <project>` | `--check`, `--clips 1,3`, `--horizontal`, `--layout auto\|facecam\|crop` |
| `run.py brand <project>` | `--accent "#RRGGBB"`, `--text "#RRGGBB"`, `--outline "#RRGGBB"`, `--note "why"`, `--reset` |
| `run.py edit <project>` | `--clips 2`, `--jump-label` / `--no-jump-label`, `--engine python\|remotion`, `--sfx auto\|light\|none`, `--no-zoom`, `--no-captions`, `--no-upper`, `--caption-y 1270` (bigger number = lower), `--size 96`, `--out <folder>` |
| `run.py more <project>` | `--add 3` (the next 3 ideas become clips), `--upto 12` (enough for 12 clips), `--pick 2,5` (those from the list) |
| `run.py qa <project>` | checks every finished clip and writes `qa.txt`: FAIL (fix first) for Hindi letters in Roman captions, captions outside the safe zone, a cut inside a word, loudness far off -14 LUFS, black frames, a stale edit; CHECK for captions over a face, a frozen picture, a flash at the end, a short clip, many words without captions. `--clips 2,5` |
| `run.py test` | ClipKaro's own tests (a second; no video needed): run after changing the code |
| `run.py music` | lists your music moods; `add "<file or folder>" <mood>` adds tracks, `remove <file name>` takes one out |
| `run.py sfx` | lists your sound moods; `add "<file or folder>" <mood>` adds sounds, `remove <file name>` takes one out |
| `run.py tidy <project>` | no captions for words made up during laughter, noise ("झाल") or loops, for videos transcribed before (`fetch` does it by itself); `--dry` |
| `run.py fixword <project> "wrong" "right"` | `--at 2107.5` (only the place nearest that second), `--dry` (show what would change) |
| `run.py find <project> "exact phrase"` | `--near 470` (only matches within 60 seconds of that time) |
| `run.py parts <project>` | `--minutes 21` (each part's own stretch), `--margin 120` (context seconds on each side); tests: `--no-chapters`, `--shift 0.5`, `--dir` |
| `run.py topics <project>` | `--check` (check topics.json again after editing it), `--rebuild`, `--dir` |
| `run.py sound <project>` | measures laughs, applause, both talking at once, and lively spots (`fetch` does this by itself) |
| `run.py critic <project>` | `--fresh` (start over), `--from clips\|candidates\|deep` (what to judge), `--runs 3` |
| `run.py deep <project>` | run again after each helper step, it does the next stage itself; `--fresh` (start over; earlier files go to `deep/old/`) |
| `run.py honesty <project>` | first run: one packet per deep clip for the three honesty judges; second run: merges their verdicts; `--fresh` (start over) |
| `run.py asr-bench make` / `run [model]` / `report` | a small speech-to-text test on your own videos (Hindi, Hinglish, English): `make` cuts four ~3-minute snippets and draft texts into `output/_asrbench/`; correct the texts by ear once; `run` scores a model (the share of words wrong, compared by sound so Devanagari and Roman Hinglish count the same); `report` lists every model tried, best first. Switch models only when one clearly wins |
| `run.py relisten <project>` | listens again to unclear speech (game voices, film clips) in videos transcribed before Nov 2026: clear English replaces nonsense, the rest gets no captions; then re-cut the clips it names |
| `run.py frames <project>` | `--clips 1,3`, `--every 1.5`: picture sheets showing what the crop keeps, before or after cutting |
| `run.py post <project>` | `--open` (open the PostKaro link in the browser). Writes `post.json`; prints the PostKaro link when PostKaro is installed |
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
