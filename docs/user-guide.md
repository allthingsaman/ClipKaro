# ClipKaro user guide

**For everyone. No coding needed.** This guide explains, step by step and in simple words, how to
set up ClipKaro and make your first short videos.

---

## What ClipKaro does

You give it a **long video**: a YouTube link, or a video file on your computer.

ClipKaro then:
1. listens to the whole video and writes down every word,
2. finds the **best short moments** (the parts that grab attention and make sense on their own),
3. turns each moment into a **standing (vertical) video** for YouTube Shorts, Instagram Reels and
   TikTok, keeping the speaker's face in the middle,
4. adds **captions** (the words appear on screen as they are spoken), **zoom effects** and a few
   **sound effects**,
5. writes a **ready-to-post caption** (text and hashtags) for each video.

It works with English, Hindi and Hinglish (Hindi mixed with English), and more.

Everything happens **on your own computer**. Your videos are not uploaded anywhere.

---

## What you need

| | |
|---|---|
| **A computer** | Windows, Mac or Linux, with at least 8 GB of memory (RAM) and about 20 GB of free space |
| **An NVIDIA graphics card** | **Strongly recommended.** With one, a video is ready in minutes. Without one, ClipKaro still works, but it is **very slow**: one video can take a couple of hours. Macs don't have NVIDIA cards, so on a Mac it's always the slow way. |
| **Claude Code** | the AI helper that does all the work for you (it needs a Claude account with a plan that includes Claude Code: see [claude.com/claude-code](https://claude.com/claude-code)) |
| **Internet** | for the first setup (it downloads a few GB once) and for YouTube links |

**Do I have an NVIDIA graphics card?**
- **Windows**: press `Ctrl + Shift + Esc` to open Task Manager → click **Performance** → look at the
  **GPU** entries. If one says **NVIDIA**, you have one.
- **Linux**: open a terminal and type `nvidia-smi`. If it shows a table with your card's name, you
  have one and it's ready.

---

## A few words you will see

| Word | What it means |
|---|---|
| **Claude Code** | An AI helper. You type what you want in normal words, and it does the steps on your computer. |
| **Folder** | A place on your computer that holds files (like "Documents" or "Videos"). |
| **Terminal** | A window where you type commands. Claude uses it for you. Sometimes it asks you to type one command yourself (see Step 2). |
| **Repo** | Short for "repository": the ClipKaro files on the GitHub website. |
| **Path** | The full address of a file on your computer, like `C:\Users\you\Videos\talk.mp4`. |
| **GPU** | The graphics card. An NVIDIA one makes ClipKaro much faster. |

---

## Step 1: Get Claude Code

1. Go to **[claude.com/claude-code](https://claude.com/claude-code)**.
2. Download it for your computer and sign in with your Claude account. On **Windows** and **Mac**,
   the **desktop app** is the easiest. On **Linux**, follow the instructions there for the terminal
   version.

---

## Step 2: Ask Claude to install ClipKaro

1. Open Claude Code in the folder where you want ClipKaro to live, for example your
   **Documents** folder.
2. Type this and press Enter:

   > **install this repo: https://github.com/allthingsaman/ClipKaro**

3. Claude now:
   - downloads ClipKaro into a new folder called **ClipKaro**,
   - checks your computer and installs what's missing,
   - **finds out by itself whether you have an NVIDIA graphics card** and sets it up if you do,
   - tests that everything works.

**While it works:**
- **Claude asks before it does things on your computer.** Read the short message and allow it.
- **Sometimes Claude asks you to run a command yourself.** That happens for things that need your
  computer's password. Do this:
  1. Open a terminal:
     - **Windows**: press the Start button, type `Terminal`, press Enter.
     - **Mac**: press `Cmd + Space`, type `Terminal`, press Enter.
     - **Linux**: press `Ctrl + Alt + T`.
  2. Copy the command from Claude and paste it into the terminal (Windows: `Ctrl + V`;
     Mac: `Cmd + V`; Linux: `Ctrl + Shift + V`), then press Enter.
  3. If it asks for your password, type it and press Enter. **The letters don't show while you type.
     That's normal.**
  4. When it's finished, go back to Claude and type **done**.
- **Windows only:** if Claude says a program "isn't found" right after installing it, close Claude
  Code, open it again in the same folder, and type **continue the installation**.
- **It takes a while**: about 10-30 minutes, depending on your internet speed. Most of it is
  downloading.

When Claude says the setup is complete, go on to Step 3.

---

## Step 3: Open the ClipKaro folder in Claude Code

**This step matters.** Claude only knows how to make clips when it is opened **inside the
ClipKaro folder**.

- **Desktop app**: open the **ClipKaro** folder (for example `Documents/ClipKaro`) as the folder
  to work in.
- **Terminal version**: type `cd ClipKaro`, press Enter, then type `claude` and press Enter.

Do this every time you want to make clips.

---

## Step 4: Make your clips

In Claude Code (inside the ClipKaro folder), type:

> **clip this video: https://youtu.be/...**

(paste your YouTube link after the colon)

**For a video on your computer**, paste its path inside quotes:

> **clip this video: "C:\Users\you\Videos\my podcast.mp4"**

How to copy a file's path:
- **Windows**: hold **Shift**, right-click the video file, choose **Copy as path**.
- **Mac**: right-click the file, hold the **Option** key, choose **Copy "…" as Pathname**.
- **Linux**: right-click the file and choose **Copy**, then paste it, or drag the file into the
  Claude Code window.

Keep the video file where it is until the clips are finished.

**Now wait.** Claude tells you what it's doing. Before anything is cut, a second AI editor checks
every clip idea, like a fair friend who didn't pick them, ranks them, and points out what to
fix (for example a clip that needs earlier context); Claude then fixes those. It judges only how
the clip is made (its start, its end, whether it makes sense alone), never the topic: a clip about
politics or religion is judged like any other, and what to post is always your choice. Then Claude shows a table of the moments it picked, each with a **clip score**
out of 10 (for example "8/10 Strong") and the reasons. The score says how well-made the clip looks,
not how many views it will get. At the end it shows your finished clips, each with a caption you
can copy when you post.

---

## Step 5: Find your clips

Your finished videos are in:

**ClipKaro folder → `output` → (a folder named after your video) → `edited`**

Or just ask Claude: **"open the folder with my clips"**.

The `edited` videos are ready to upload to YouTube Shorts, Instagram Reels and TikTok.

**Want ClipKaro's partner to post them for you?** PostKaro is a separate app that posts your clips to
YouTube Shorts, Instagram Reels and your Facebook Page, each at the time you choose. Once it is
installed, Claude ends with a **"Post them"** link: click it, check the titles and captions, and press
Schedule.

---

## Asking for something different

Write your wishes in the same message, in normal words. English, Hindi or Hinglish all work.
Some examples:

- "clip this video: (link), but only the 3 best" · "at least 10 clips" · "at most 5 clips"
- "clips under 30 seconds"
- "only the parts about money"
- "show me the moments before you cut them"
- "no sound effects" · "no zooms" · "no captions"
- "captions a bit lower" · "bigger captions" · "captions not in capital letters"
- "use yellow captions" · "use #00E5FF as the caption colour"
- "Hindi captions in Hindi letters" (instead of English letters)
- "it's a gameplay video" (usually not needed: see below)

**Long videos** need no special words either. A video of an hour or more is read in parts of
about 20 minutes, all at the same time (Claude says, for example, "Reading the video in 6 parts at
once"), so the middle of a long podcast gets the same attention as the start. It takes a few
minutes more. Afterwards you can ask "show me the topic map" to see every topic with its time.

**How many clips?** If you don't say, ClipKaro makes every good moment into a clip: 3 to 8, like
before, and more for long videos (up to about one for every 7 minutes: a 2-hour stream can give 17).
Say "at least 10" or "at most 5" and it follows that.

**Live streams and gameplay** need no special words. ClipKaro sees by itself when a video was a
live stream or is gameplay with your webcam in a corner. It then leaves out the "Starting soon",
"Be right back" and stream-ending screens, builds clips around what *you* say (not the game's
characters), and doesn't mind the quiet stretches where you just play.

**Quick, standard or deep.** Normally ClipKaro uses *standard*: a second AI editor checks every
clip idea before anything is cut. If you want to save your Claude plan, say "quick clip this" or
"use fewer tokens": Claude then picks the clips alone, like the first versions did. It's faster and
much lighter, but the picks get no second opinion.

**Want more clips later?** ClipKaro judges every possible clip in a video, often 15 to 30, and
makes only the best ones. The rest are saved. Days later you can say "3 more clips from the Khan
Sir video" and get them in a few minutes, without the video being read again.

**A wrong word in the captions?** Say "in clip 4, 'bow' should be 'boat'". It is fixed everywhere
the word was heard, and the clips that have it are made again.

**Deep clips**: for a video longer than 21 minutes, Claude asks you once at the start whether you
want them. You can also say so in your first message: "deep clip this: (link)" or "clip this,
use deep clipping". After the normal clips, Claude looks for a story that is spread across the video, like a
question at minute 3 and its answer at minute 41, and joins those moments into one short, always in
the order they were said. Three separate checks make sure the joined clip doesn't change what
anyone meant (if only one of them has a doubt, Claude keeps the clip and tells you why, so you can
decide), and a short white flash with a soft whoosh shows where it jumps in time (ask "show how
much time was skipped" to also see a small "27 MIN LATER"). Often no deep clip is good
enough, and Claude tells you so. It takes about 10-15 minutes more.

**Podcasts and interviews with two people** need no special words. ClipKaro shows the person who
is talking. When someone laughs, or both talk at once, it shows both of them, one above the other
(a "split screen"), with the captions in between.

After you see the clips, you can ask for changes:
- "clip 2 starts too early"
- "make clip 1 shorter"
- "the spelling of 'Juyal' in clip 3 is wrong"
- "make the captions bigger in all clips"
- "in clip 4, show both of them when he laughs" · "show the other person there"

You can ask for anything in your own words. If ClipKaro can't do something yet (for example adding
background music), Claude will tell you.

More examples: [usage.md](usage.md).

---

## Saving your own preferences

If you always want the same things (for example "always 5 clips" or "my videos are in English"),
save them once, and Claude will follow them every time.

**The easiest way:** ask Claude, for example:

> **add to my preferences: my videos are in English, and I always want 5 clips of 30-45 seconds**

**Or do it yourself:** in the ClipKaro folder, open the file **`CLAUDE.md`** with a text editor
(Notepad on Windows, TextEdit on Mac). At the bottom there's a part called **"My preferences"**.
Write each wish on its own line, starting with `- `, for example:

```
- My videos are in English.
- Always give me 5 clips, 30-45 seconds long.
- My brand colour is #00E5FF.
- No sound effects.
```

Save the file. The next time you start Claude Code in the ClipKaro folder, it follows them.

---

## How long it takes

| | With an NVIDIA graphics card | Without one (not recommended) |
|---|---|---|
| Writing down the words of a 10-minute video | 1-2 minutes | English: a few minutes. Hindi/Hinglish: 10-40 minutes |
| A whole video, from link to finished clips | usually 15-30 minutes (the second opinion on every clip idea adds 5-15 of them) | can take **a couple of hours** |

The very first time also includes downloading (once).

---

## If something goes wrong

1. **Ask Claude.** Copy the error message, paste it into Claude Code and add "please fix this".
   Claude can usually solve it.
2. Some common ones:
   - **YouTube says "Sign in to confirm you're not a bot"**: tell Claude
     "use my Chrome cookies" (or Firefox, or Edge: the browser where you're logged in to YouTube).
   - **The wrong language was detected**: tell Claude "the video is in English" (or Hinglish).
   - **A word in the captions is misspelled**: tell Claude which word and which clip.
   - **It's very slow**: you probably don't have an NVIDIA graphics card, or its driver isn't
     installed. Ask Claude "is my NVIDIA graphics card being used?"
3. More help: [troubleshooting.md](troubleshooting.md).

**Always watch your clips once before you post them.** The automatic captions are very good, but
not perfect.

---

## Updating ClipKaro

Open Claude Code in the ClipKaro folder and type: **update ClipKaro**. Claude downloads the newest
version and runs the setup again.

---

## Please be fair

Only clip and post videos that **you own** or that you have **permission** to use. Respect other
creators and each platform's rules.
