# ClipKaro v2: how good is it today, and how to make it industry grade

This page compares ClipKaro's **output** with the best-known AI clippers (mainly Opus Clip), and lays
out a plan to close the gaps. It only looks at the clipping pipeline: *give it a video → get clips
that can go viral*. Payments, accounts and app design are out of scope.

It's a plan, not a promise. Items marked **Status (v1.1)** are already built; the rest is still to
do. Contributions are welcome (see [CONTRIBUTING.md](../CONTRIBUTING.md)).

> **New in v1.1 (November 2026):** ClipKaro now knows *who is speaking* (speaker diarization) and
> frames podcasts like an editor: the person talking is shown, and both people are shown in a split
> screen around laughs and cross-talk. On 9 hand-checked podcast clips it chose the ideal framing
> 83% of the time and showed the wrong person only 1% of the time. This closes the biggest visible
> gap with Opus Clip for two-person podcasts. See items 8-10 and [CHANGELOG.md](../CHANGELOG.md).

---

## 1. The short answer

**ClipKaro is close to Opus Clip on the basics, and since v1.1 also on two-person podcasts; ahead
on Hindi/Hinglish; behind on "polish" (caption styles, B-roll, music) and on videos where people
move around or there are three or more.**

| | Verdict |
|---|---|
| Picking good moments | **About as good, maybe better** on talking-head and podcast videos: Claude reads the *whole* transcript like an editor, and every cut is checked against sentence ends. Not proven yet: we need a blind test (section 6). |
| Hindi / Hinglish | **Clearly ahead.** Opus Clip's own help page says it doesn't support Hindi. ClipKaro writes Hinglish captions in English letters, which few tools do. |
| Framing (keeping the right person in frame) | **Closer since v1.1.** In podcasts with two people on screen, ClipKaro now shows the person who is *talking* and switches to a split screen for laughs and cross-talk. Still behind on smooth tracking of people who move around, and on three or more people. |
| The edit (captions, zooms, sounds) | **Behind on variety.** Our zooms and word-by-word captions are good, but competitors also offer caption templates, emojis, B-roll, background music and silence removal. |
| Reliability | **Behind.** Whisper sometimes writes nonsense during laughter or cross-talk, and today a person (or Claude) has to spot it. Competitors hide more of this. |
| Speed | **Fine with an NVIDIA card, slow without** (a long video can take about 2 hours on a CPU). Competitors run in the cloud, so they're always fast. |
| Cost, privacy, control | **Ahead.** Free, no watermark, no credits, nothing uploaded, every step can be changed. |

**So: not yet "industry grade" for every creator, but the gap is mostly engineering that we know how
to do.** The five most important upgrades are in section 5.

---

## 2. How we compared

- **What we looked at:** the published features of Opus Clip, Vizard, Klap, Submagic and similar
  tools, user reviews (G2, Trustpilot, review blogs), and our own test runs (a 7-minute Hinglish
  review and a 2-hour Hinglish podcast).
- **What we didn't do yet:** run the same videos through Opus Clip and ClipKaro side by side.
  That's the first task of v2 (section 6). Until then, the comparison is based on features and
  reviews, not a measured test.
- Sources are listed at the end.

---

## 3. Side by side: what each tool produces

| Area | Opus Clip (and the best of the others) | ClipKaro today | Gap |
|---|---|---|---|
| **Finding moments** | "ClipAnything" uses picture, sound and emotion cues. You can describe the moment you want. Gives each clip a "virality score". Reviewers say selection is uneven ("10 clips but only 3 good") and starts/ends can be awkward. | Claude reads the full transcript with clear editor rules (hook → story → payoff, 15-90 s, no warm-ups). You can ask in plain words ("only the parts about money"). Text only: it can't hear laughter or see a big reaction. | Add sound and picture signals; add a scoring step. |
| **Clip start and end** | Reviewers mention cut-off context and awkward starts/ends. | Every cut is snapped to whole words, with automatic warnings for cuts in the middle of a sentence. | We're ahead; keep it. |
| **Long videos (1-3 h)** | Handled automatically. | Works, but for our 2-hour test the moment-picking was split into four parts **by hand** to read everything carefully. | Build that splitting into ClipKaro. |
| **Transcription** | Claims about 97% caption accuracy. Hindi not supported (per its help page). | Whisper large-v3-turbo with re-transcription of skipped speech. Very good on clear speech; makes nonsense words during laughter and cross-talk, and splits some words ("P .O .K."). | Clean-up filters and confidence flags. |
| **Who is speaking** | Active speaker detection (Opus Clip, Vizard); Klap labels speakers in captions. | **Since v1.1:** speaker diarization (who speaks when) and laughter detection, matched to each person's seat across the whole video. Used for framing; not yet shown in captions or the transcript. | Show speakers in the transcript Claude reads; speaker labels in captions. |
| **Framing** | Follows the speaker and moving people/objects ("ReframeAnything"). | One still crop per camera shot, on the face. **Since v1.1:** in two-person shots, a crop on the person *talking*, switching between words. Slides and things being shown get the whole frame over a blurred background (`show_full`). Gameplay with a webcam gets a stacked layout. | Smooth tracking of people who move; following objects. |
| **Two or more people** | Split-screen for interviews, 3-4 panels for panels, picture-in-picture for remote guests (Klap, Vizard). | **Since v1.1:** two-person split screen for laughs, cross-talk, quick back-and-forth and wide shots (main talker on top, captions on the seam). | 3-4 panels; picture-in-picture for remote guests. |
| **Captions** | Many animated templates, emojis, GIFs (Submagic), 50+ languages. | One clean style: word-by-word pop-in, highlighted key words, colour from the video; Roman Hinglish or Devanagari. | Templates, emojis, face-aware placement. |
| **Edit polish** | Auto zooms synced to words, B-roll, background music, sound effects on transitions, one-click silence removal (Submagic); AI B-roll (Opus Clip). | Zoom punch-ins on the beat, 1-2 soft whooshes, loudness set for phones. | Silence/filler trimming, hook title, music, B-roll. |
| **Gaming / sports** | Reviewers say Opus Clip is weaker here. | Facecam layout; picks moments from the creator's commentary. Weak on silent action moments (text-only). | Sound/picture signals help here too. |
| **Languages** | Opus Clip: about 20-30 languages, no Hindi (per help page), no right-to-left. | English and Hindi/Hinglish fully; most others at a basic level. | We lead for Indian creators; extend to more Indian languages. |
| **Cost and privacy** | Paid credits per minute; reviews complain about billing. Videos are uploaded. | Free, local, unlimited. | Our advantage. |

---

## 4. What ClipKaro already does better (keep these)

1. **An editor that reads everything.** Claude reads the full transcript, explains *why* each clip
   works, and follows written editorial rules that anyone can improve.
2. **Clean cuts.** Word-snapped starts and ends, and warnings for mid-sentence cuts.
3. **Hindi and Hinglish**, with captions in English letters. This is our strongest difference
   for the Indian creator market.
4. **Free, private and unlimited**: no credits, no watermark, no uploads.
5. **Fully adjustable.** Every decision is in a readable file (`clips.json`, `romanize.json`), and
   every step can be redone for one clip. Since v1.1 any moment's framing can be changed too
   (`framing`, `show_full`).
6. **Careful two-person framing (v1.1).** It never guesses a face: when unsure it shows both people.
   The AI editor checks picture sheets and adds what sound can't catch (a silent laugh).

---

## 5. The plan

Each item says **what**, **why it matters for going viral**, **how** (the engineering), the
**size** (S = a few days, M = 1-2 weeks, L = 3-6 weeks, for one developer working with Claude Code),
and **how we'll measure** it.

### v1.x: quick wins (small changes, big effect)

#### 1. Trim silences and filler words ("jump cuts") (S)
- **Why:** Short-form viewers leave during pauses. Tight clips feel faster and keep people watching.
  Submagic and others do this in one click.
- **How:** We already have the exact time of every word. Inside each clip, cut pauses longer than
  about 0.35 s (keep a natural 0.1-0.15 s breath), and optionally filler words ("um", "uh"; for
  Hindi only clear fillers, chosen carefully). Each cut gets a small zoom change, which our camera
  planner already does for splices, so the jump is hidden. A setting turns it off.
- **Measure:** clip length drops 10-20% with no lost words; viewers in the blind test (section 6)
  prefer the trimmed version.

#### 2. Hook title on screen (S)
- **Why:** Most viral shorts show a big 3-6 word hook in the first 2-3 seconds ("Pakistan ka PM
  banoge?"). It stops the scroll even with the sound off.
- **How:** Claude already writes a title for each clip. Add a `hook_text` field to `clips.json` and
  draw it at the top for the first 2-3 s (same font and brand colour, pop-in animation).
- **Measure:** blind test: "would you stop scrolling?"

#### 3. Built-in handling of long videos (M)
- **Why:** Podcasts are long. Reading a 2-hour transcript in one go makes the AI skim. For our
  Khan Sir test we split it into four parts by hand, which gave much better picks.
- **How:** a `run.py segments <project>` step that splits the transcript into ~25-minute windows
  with a small overlap. The skill tells the agent to find the 5 best candidates per window (in
  parallel, if the agent supports helpers), then rank **all** candidates together, remove repeats
  of the same topic, and keep the best N.
- **Measure:** the same picks whether a video is 20 minutes or 3 hours; no part of the video skipped.

#### 4. A second opinion before cutting (S)
- **Why:** The most common complaint about AI clippers: "10 clips, only 3 good".
- **How:** Pick about twice as many candidates as needed, then a separate "critic" pass scores each
  one on a fixed sheet: hook (0-10), makes sense alone (0-10), payoff (0-10), emotion/energy
  (0-10), quotable (0-10). Clips under a threshold are dropped, even if that means fewer clips. The
  scores are saved in `clips.json` and shown to the user as a simple "viral score" with reasons.
- **Measure:** share of clips rated "I'd post this" in the blind test.

#### 5. Cleaner transcripts (M)
- **Why:** Wrong words in captions look unprofessional. In our tests: nonsense words during laughter
  ("झाल"), the Hinglish primer sentence leaking into silent parts, and split words ("P .O .K.",
  "एर बस" for Airbus).
- **How:**
  - Drop words whose timing falls on detected laughter or applause, have very low confidence, and
    repeat nonsense syllables.
  - Detect and drop words copied from the primer sentence when there's no speech energy.
  - Join split tokens automatically (letters split by dots, numbers split from letters).
  - Mark every word Whisper is unsure about (confidence below ~0.4), so the AI checks those first
    when it writes the captions.
  - **Stretched words** (found in v1.1 testing): sometimes Whisper writes one long "word" over a
    stretch where several words were said, so those words are missing from the captions (a Khan
    Sir clip lost "ki ye America ki chaal hai"). Find words longer than about 1 s over continuous
    speech, transcribe just that bit again, and replace them. In v1.1 two cases were fixed by hand.
- **Measure:** caption word error rate on a hand-corrected 10-minute sample of each test video.

#### 6. Automatic quality check after editing (S)
- **Why:** Today Claude or the user has to look at frames to catch problems. An editor always
  reviews before publishing.
- **How:** `run.py qa <project>` writes a report and one contact-sheet image per clip: cut points
  inside words, unsure caption words, leftover Hindi letters, percentage of time a face is in
  frame, black or blurred frames, loudness, length, and a camera cut in the last half second of a
  clip (a short flash of another shot at the very end, seen once in v1.1 testing). The skill tells
  the agent to read the report and fix what fails.
- **Measure:** problems caught before the user sees them.

#### 7. Caption placement that avoids faces and app buttons (S)
- **Status (v1.1): partly done.** In the split screen the captions sit on the seam between the two
  people and never cover a face, even at a switch. Still open: in very tight close-ups the caption
  line can sit on the chin or beard (seen in a Khan Sir clip).
- **Why:** Captions over a mouth or under TikTok's buttons hurt watch time.
- **How:** We know where the face is in every shot. Move the caption line up or down when it would
  cover the face, and keep it inside the "safe zone" of TikTok, Reels and Shorts.

### v2.0: the big upgrades

#### 8. Know who is speaking ("speaker diarization") (M)
- **Status (v1.1): done for framing.** sherpa-onnx with pyannote segmentation 3.0 and 3D-Speaker
  ERes2Net finds who speaks when; a speaker register matches voices across all clips of a video.
  Not yet shown in the transcript Claude reads.
- **Why:** In interviews it matters *who* says the line: the guest's answers are usually the clips.
  It's also the base for items 9 and 10.
- **How:** run a diarization model after transcription (options: pyannote.audio, NVIDIA NeMo, or
  WhisperX, which combines Whisper with diarization). Each word gets a speaker label (S1, S2, ...);
  the transcript shows who speaks; Claude can name them from context ("Raj", "Khan Sir").
- **Watch out:** some models need a free Hugging Face token and accepting their terms. Check each
  model's licence before shipping it.
- **Measure:** speaker labels right on a hand-checked sample.

#### 9. Frame the person who is talking (active speaker framing) (L)
- **Status (v1.1): done for two people sitting still** (podcasts, interviews): `clipper/director.py`.
  On hand-checked clips the right framing was chosen 83% of the time (91% acceptable) and the wrong
  person only 1%. Still to do: smooth tracking of people who move, more than two people.
- **Why:** This is the biggest visible gap with Opus Clip, Vizard and Klap. In a two-shot, or when
  the camera stays on both people, the crop must follow the one who is talking.
- **How:**
  1. Track faces through each shot (we already find faces with YuNet; add a simple tracker that
     links faces from frame to frame).
  2. Decide which face is speaking: match the speaker labels from item 8 with **mouth movement**
     (face landmarks), or use a dedicated active-speaker model (research models such as TalkNet or
     Light-ASD; check the licence).
  3. Move a "virtual camera" like a human operator would: stay still while the speaker is still,
     follow smoothly with a dead zone, and switch at sentence ends when the speaker changes.
     Reaction shots stay allowed during laughter.
- **Measure:** percentage of time the active speaker is in frame (target above 95%), checked on the
  test set.

#### 10. Automatic layouts for two or more people (M)
- **Status (v1.1): two-person split screen done** (laughs, cross-talk, quick back-and-forth, wide
  shots). Picture-in-picture and 3-4 panels are still to do.
- **Why:** In fast back-and-forth, switching every two seconds feels jumpy. Split-screen keeps both
  faces visible (Klap and Vizard do this).
- **How:** if the speaker changes more than about every 4 seconds for a while, or both people react,
  use a stacked split-screen (one face per half), like our existing facecam layout. Picture-in-
  picture for remote guests; 3-4 panels for panels.

#### 11. Use sound and picture, not just words (M)
- **Status (v1.1): laughter is heard** (YAMNet) and used for framing. Not yet shown to Claude as
  hints for picking moments.
- **Why:** Some of the best moments are laughter, a reaction, a raised voice, or an action in a game,
  and the transcript alone can't see them. This is what "multimodal" clippers like ClipAnything use.
- **How:** code computes simple signals and marks them in the transcript Claude reads, for example
  `[laughter]`, `[applause]`, `[voice rises]`, `[fast back-and-forth]`, `[big movement]`:
  - **sound:** a sound-event model for laughter and applause (for example YAMNet; check licence),
    plus loudness and pitch changes;
  - **picture:** how much the picture changes, gestures, and (later) facial expressions.
  Claude stays the editor; the signals are hints, not rules.
- **Measure:** blind test, especially on funny moments and gaming videos.

#### 12. More editing styles (M)
- **Why:** Different niches look different (podcasts, education, gaming, motivation).
- **How:**
  - **Caption templates:** 5-8 presets (word pop, karaoke box, highlighted word on a coloured box,
    two-line, minimal).
  - **Emojis:** Claude suggests one emoji on a strong word every few seconds. Draw them as images
    (Twemoji, CC-BY 4.0, or Noto Emoji, SIL OFL): the caption renderer (libass) can't draw colour
    emojis, but our python engine composes every frame and can.
  - **Sound:** a "pop" on an emoji, a "hit" on the punchline, a riser before the payoff, using the
    roles our sound library already has (`hit`, `click`).
  - **Background music:** optional, with automatic "ducking" (music gets quieter under the voice,
    with ffmpeg's `sidechaincompress`). Ship no music; users add their own licensed tracks.
  - **B-roll (optional, later):** Claude picks keywords; stock clips (for example from Pexels'
    free licence, with credit) are shown briefly when nobody is on screen.

#### 13. Faster rendering (M)
- **Why:** Editing currently takes about as long as the clips themselves, on the processor.
- **How:** apply the zooms with ffmpeg (crop and scale per segment) instead of drawing every frame
  in Python; use NVIDIA's hardware encoder (NVENC) when available; render several clips in
  parallel.
- **Measure:** edit time under 30% of the clip length on a GPU machine.

### v3: learning and reach

#### 14. Learn from what actually goes viral
- **How:** optionally read each posted clip's views and watch time (YouTube Analytics API, with the
  user's permission), compare with the scores ClipKaro gave, and adjust the scoring sheet. Over time
  ClipKaro learns what works for each creator. Nothing leaves the user's computer.

#### 15. A local "review studio"
- **Why:** The last mile of quality is human: drag a start point, fix a caption word, try another
  colour, all without typing commands.
- **How:** a small web page served on the user's own computer (`run.py studio`) that shows the clips,
  their scores and captions, and re-renders one clip at a time.

#### 16. More Indian languages
- Tamil/Tanglish, Bengali/Banglish, Marathi, Telugu and others, following
  [adding-a-language.md](adding-a-language.md). This widens our lead in India.

---

## 6. How we'll know we're as good as Opus Clip

**Measure first, then improve.** Before building v2, create a small test set and a blind test:

1. **Test set (12 videos):** 4 English (talk, podcast, interview), 4 Hindi/Hinglish (podcast, talk),
   2 gaming with a webcam, 2 multi-camera interviews. Use videos we have permission to use.
2. **Run ClipKaro and Opus Clip** on the English and gaming ones (Opus Clip doesn't support Hindi;
   compare Hinglish videos with a tool that does, such as Captions.ai or Vizard).
3. **Blind rating:** 3-5 people watch the clips without knowing which tool made them, and score:
   hook, makes sense alone, ending, framing, caption accuracy, and "would you post it?"
4. **Automatic numbers:** caption word error rate, percentage of time the active speaker is in
   frame, percentage of clean starts and ends, processing time.
5. **Targets for v2:** ClipKaro wins or ties in at least 60% of English comparisons; caption error
   rate under 5% on clear speech; the active speaker in frame more than 95% of the time.

Keep the test set and run it after every big change, so improvements are real and nothing breaks.

**Progress (v1.1):** a first labelled set exists for framing: 9 two-person podcast clips (224 s)
labelled moment by moment (who speaks, who laughs, ideal framing). Result: ideal framing 83%,
acceptable 91%, wrong person 1%. The side-by-side test against Opus Clip is still to do.

---

## 7. Should ClipKaro become an app?

**Not yet. Improve the output first.** Our edge is that the AI editor (Claude Code) does the
thinking for free on the user's own plan, and everything runs locally. A full app would need:
- a decision on how the AI is paid for (the user's own API key, or our own server, which costs money
  per video),
- bundling Python, ffmpeg and the models into an installer for each system,
- support and updates for non-technical users.

**Suggested path:**
1. **Now:** keep ClipKaro as a Claude Code skill and command-line tool, and build v1.x and v2.
2. **Then:** the local review studio (item 15). It makes the output better, and it's the core of any
   future app.
3. **Later, if many non-technical creators want it:** wrap the engine and the studio in a desktop app
   (for example with Tauri or Electron), using the Claude API with the user's own key.

Marketplaces like Agensi can help people discover ClipKaro in the meantime, without building an app.

---

## 8. The first five things to build

| Order | What | Size | Why first |
|---|---|---|---|
| 1 | Test set + blind test (section 6) | S | Tells us where we really stand, and proves each improvement |
| 2 | Silence/filler trimming + hook title (items 1, 2) | S | The quickest visible jump in "viral feel" |
| 3 | Long videos + second opinion (items 3, 4) | M | Better picks on podcasts, fewer weak clips |
| 4 | Cleaner transcripts + automatic quality check (items 5, 6) | M | Professional captions without manual fixing |
| 5 | Speaker diarization + active speaker framing + split-screen (items 8, 9, 10) | L | Closes the biggest visible gap with Opus Clip. **Done in v1.1 for two-person podcasts.** |

After these five, ClipKaro should match or beat Opus Clip on talking-head and podcast videos, and
stay clearly ahead for Hindi/Hinglish creators. With item 5 done first (v1.1), the next ones are
the test set and blind test, then silence trimming and the hook title.

---

## Sources

- OpusClip features and reviews: [opus.pro](https://opus.pro/home-site),
  [Castmagic review](https://www.castmagic.io/software-reviews/opus-clip),
  [Shotkit review](https://shotkit.com/opus-clip-review-ai-viral-shorts/),
  [MakerStack review](https://makerstack.co/reviews/opus-clip-review/),
  [TheCMO review](https://thecmo.com/tools/opusclip-review/)
- OpusClip and Hindi: [OpusClip help: Hindi support](https://help.opus.pro/docs/article/does-opusclip-support-hindi),
  [OpusClip blog: multilingual captions](https://www.opus.pro/blog/multilingual-captions)
- User complaints: [eesel.ai: OpusClip reviews](https://www.eesel.ai/blog/opusclip-reviews),
  [G2: OpusClip reviews](https://www.g2.com/products/opusclip),
  [Trustpilot: opus.pro](https://www.trustpilot.com/review/opus.pro?page=2)
- Alternatives and comparisons: [Castmagic: OpusClip alternatives](https://www.castmagic.io/blog/opus-clip-alternatives),
  [Choppity: best OpusClip alternatives](https://www.choppity.com/blog/best-opus-clip-alternatives/),
  [Omid Saffari: alternatives compared](https://omidsaffari.com/blog/opus-clip-alternatives)
- Submagic: [auto zooms](https://submagic.co/features/auto-zooms),
  [auto video editor](https://www.submagic.co/features/auto-video-editor),
  [UC Strategies review](https://ucstrategies.com/news/submagic-review-2026-pricing-features-is-it-worth-it-for-creators/)
- Vizard and Klap: [Vizard: active speaker centring](https://vizard.ai/blog/vizard-now-automatically-centers-the-active-speaker),
  [Vizard: speaker identification](https://vizard.ai/blog/vizards-speaker-identification-just-got-smarter),
  [Klap: podcast clip maker](https://klap.app/tools/podcast-clip-maker)
- Hinglish captions elsewhere: [Captions.ai: add captions](https://help.captions.ai/docs/captions/add-captions)
