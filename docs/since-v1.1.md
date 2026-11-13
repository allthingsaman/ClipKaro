# Since v1.1: every change, checked against v1.1

**v1.1 is the first stable version of ClipKaro**: the one that satisfied its owner. So every
change after it must be an **upgrade**. Nothing v1.1 could do may be lost or made harder. When a
change does something differently from v1.1, it must be because the owner wanted it, and if it is
a matter of taste, there must be a way to get v1.1's behaviour back.

This page lists every change since v1.1 and checks it against that rule. **Each new change gets
its line here, in the same commit.** Released so far: **v2.0** (2026-11-11, the lines marked v2.0)
and **v2.1** (2026-11-13, the lines dated 2026-11-12 and 2026-11-13).

**The marks**
- ⬆ **Upgrade**: v1.1 does this too, and now it's better; or it's new and changes nothing
  unless you use it.
- ↔ **Different on purpose**: it works differently from v1.1 because the owner asked for it or
  chose it in a blind test. The line says how to get v1.1's way back.
- ⚠ **Costs more**: more time or more Claude usage than v1.1.

Checked on 2026-11-13: no v1.1 command, option or setting has been removed or changed. Only new
ones were added.

---

## Writing down what is said

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
  No "…" in captions either. *(2026-11-13)*
  - Way back: none needed, because those captions were wrong words. The words themselves stay in
    the transcript, and `words-before-tidy.json` keeps the old marks.
- ⬆ **The video downloads while the audio is transcribed** (YouTube links), instead of at the cut
  step, so cutting starts right away. *(2026-11-12)*
  - Way back: `fetch --no-video` downloads it at the cut step, as in v1.1. The disk space is then
    used later.

## Choosing the moments

- ⬆ **Three modes: standard, deep, quick.** Standard is the default. Deep adds deep clips when you
  ask or say yes to the question. Quick, only when you ask ("quick clip this", "use fewer tokens"),
  picks like v1.1: Claude reads the video itself, with no helpers and no critic. All three keep every
  other upgrade on this page. *(2026-11-13)*
- ⬆ ⚠ **Long videos are read in parts**, so the middle and the end get the same attention as the
  start. Several AI readers work at once. *(v2.0)*
- ⬆ ⚠ **A second opinion (the critic).**
  - A blind AI editor scores every clip idea three times and ranks them.
  - It never throws a clip away; it only ranks them and gives notes for fixing them.
  - Since 2026-11-12 it judges only how a clip is made, never its topic.
  - Short videos get it too. *(v2.0)*
- ⬆ **More clips later, without reading the video again.** The good ideas that weren't cut stay
  saved; "3 more clips from that video" turns the next ones into clips in a few minutes. v1.1 had to
  read the whole video again for that. *(2026-11-13)*
- ⬆ **Repaired clips keep their place.** The repair round judges clips again, and scores wander
  between runs, so a trimmed clip could drop below its own original. Now a second look never costs
  a clip its place, and `cut --check` no longer warns about a repair it made on purpose. *(2026-11-13)*
- ⬆ **Sound hints**: laughs, applause and both people talking at once are pointed out. A calm
  video loses nothing. *(v2.0)*
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

## Cutting and editing

- ↔ **Fewer zooms when the camera cuts fast.** v1.1 changed the zoom at every camera cut. An anime
  clip with a cut every second got 48 zoom changes in 68 seconds; the owner asked for fewer. Now a
  cut soon after the last change keeps the zoom and only follows the new face: 28 changes on that
  clip. Joins between pieces and normal speech still change it as before. *(2026-11-13)*
  - Way back: no setting, because the zoom at every cut was the problem; `edit --no-zoom` still
    turns zooms off completely.
- ↔ **Captions clear of faces and the apps' buttons; a hook title.** v1.1 put captions on one line,
  up to 940 px wide, whatever was under them. Now they keep out of TikTok's button column and the
  apps' top and bottom bars (at most 800 px wide), and a shot whose caption line would cover a face
  moves them to the nearest free line. A 3-6 word title shows on a coloured box for the first 2-3
  seconds, never on a face. *(2026-11-13)*
  - Way back: `"safe_zones": false` and `"hook_title": false` in settings.json (or `--no-safe-zones`,
    `--no-hook-title`).
- ⬆ **Fix a caption word everywhere** with one command: `run.py fixword <project> "bow" "boat"`, or
  just tell Claude. Before, it was fixed by hand. *(2026-11-13)*
- ⬆ **Editing again no longer needs the original video** once the caption colours are saved, so
  clips of videos whose source was deleted can still be edited. *(2026-11-13)*

- ⬆ **Podcasts with painted faces on the wall** show the real person. **Dark studios**: camera cuts
  are found again. *(v2.0)*
- ⬆ **Captions always fit the frame.** Before, some ran off the sides. *(v2.0)*
- ⬆ **Clips joined from pieces** sound smooth. Where the video jumps more than 20 seconds, a short
  white flash and a soft whoosh show it. Clips of one piece sound exactly as in v1.1. *(v2.0)*

## Posting

- ⬆ **Text for each platform**: a YouTube title of up to 100 characters with fitting hashtags,
  Instagram and Facebook captions, and `post.json` for PostKaro. The finished clips in `edited/` are
  the same files as before. Without PostKaro nothing changes. *(v2.0, 2026-11-12)*

## Settings and commands

- ⬆ All six v1.1 settings work as before. There are three new ones: `jump_label`, `deep_clips` and
  `max_clips`. An old settings.json works unchanged.
- ⬆ Every v1.1 command works as before. The new ones are extra: `info`, `kind`, `parts`, `topics`,
  `sound`, `critic`, `deep`, `honesty`, `post`, `relisten`, `asr-bench`.

## Cost

- ⚠ **Claude usage** (standard and deep). Reading in parts, the critic and deep clips use more of your Claude plan than
  v1.1's single read. Estimates for a long podcast (not measured yet):
  - v1.1: about 0.1-0.2 million tokens;
  - now: about 1 million;
  - with deep clips: about 2 million.

  Choosing the clips also takes a few minutes longer. On Claude's Pro plan that can mean fewer
  videos per day than with v1.1.
  - **Way back: quick mode** *(2026-11-13)*. Say "quick clip this" or "use fewer tokens", and
    Claude picks like v1.1 (one read, no helpers, no critic), with every other upgrade kept. Its real
    usage is still to be measured with `/usage` (roadmap item 3b).

---

## How we keep it an upgrade

1. Before building, check: does this take away or limit anything v1.1 could do? If it changes
   something on purpose, add a way back (a setting, a word you can say, or a command option).
2. Test on old projects from the test bench. Old clips may come out different when the change fixes
   something; that's fine. Something that worked must not stop working.
3. Add the change to this page (with its mark) and to [CHANGELOG.md](../CHANGELOG.md), in the same
   commit.
