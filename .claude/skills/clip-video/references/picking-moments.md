# How to pick the best moments

You are the editor. The scripts do the mechanical work; **this judgment is the product**.
Read the whole transcript once before choosing anything.

## What a good short is
A good short is **one self-contained idea** that a stranger can understand with zero context.
It **opens on a hook**, every line after it continues that story, and it **ends on a payoff**.

- **Length:** 25–60 s of speech is the sweet spot (hard limits 15–90 s). Shorter is better than padded.
- **The hook lands in the first 1–3 seconds**, so start on the hook line itself, never on a warm-up
  ("So, um, yeah, the thing is…").
- **One idea per short.** If a moment needs two ideas, it's two shorts or neither.

## Hook types (the first line must be one of these)
1. **Contrarian or negative claim**: "Most advice about X is wrong." / "Stop doing X."
2. **A question the viewer already asks themselves**: "Why do some people get rich and others don't?"
3. **A surprising fact or number**: a concrete figure, an unexpected result.
4. **A story opener**: "When I was 23, I had $1,000 to my name…"
5. **Desire + obstacle**: "If you want X, the thing stopping you is Y."
6. **Relatable situation + reframe**: something everyone does, seen in a new way.

A hook does two jobs: it **opens a curiosity gap** ("I need to hear the answer"), and it **signals
relevance** ("this is for me"). When several hooks compete, pick the one with the widest curiosity
gap whose **payoff exists inside the same clip**. A hook you can't resolve within the clip is the wrong hook.

## Story shape (flexible)
hook → contrast or stakes ("but…") → explanation, proof or story → escalation → **payoff**
(the lesson, the answer or the outcome). The last line must feel like an ending: a conclusion, a
punchline, a rule or a call to action. Never end mid-thought, on "and…", or on a setup.

**Ending traps** (both happened in testing):
- **A line break is not a sentence end.** Transcript lines can break inside a long sentence, so
  check that your last word really finishes the sentence (`run.py find` shows what follows).
- **Don't end on a filler restatement.** If the strongest line is followed by a weaker "so it's
  really that…" line that leads into the next thought, end on the strong line. The last thing the
  viewer hears should be the punchline, not a bridge.

## What to leave out
- Warm-ups, "as I said earlier", references to things outside the clip ("like the guy I mentioned").
- Ads, sponsor reads, "like and subscribe", housekeeping, inside jokes, cross-talk.
- Tangents, even good ones. Jump to the line that sums up the lesson.
- Retakes and false starts. With repeated takes, use the best (usually the last) complete one.

## Continuous first, splice only when it clearly wins
- **Default: one continuous range.** It always sounds natural.
- You may join **2–3 ranges** from the same video only when it clearly makes a better short. The
  usual case is a strong hook line from later in the video placed first, followed by the
  explanation. Each joined piece must be whole sentences, and together they must read naturally.
  Never build a sentence the speaker didn't say.
- Ranges of different clips must not overlap.

## Never change what someone meant (joins and cold opens)
A clip made of pieces must stay true to the full video. Check every join:
1. **The full-video test.** Would the speaker be surprised by the clip? Would a viewer who then
   watched the full video feel misled? If maybe, use one continuous range.
2. **Original order.** Pieces play in the order they were said. The one exception is a cold open:
   one line of at most about 5 s that works without setup, raises a question instead of giving
   away the answer, and means the same when heard first. Never a reaction, and never an answer
   whose question isn't shown.
3. **Answers and reactions stay with their own question.** An answer only follows its own
   question; "haan", "bilkul", "exactly" or a laugh only follows the line it reacted to.
4. **Keep how it was said.** Never cut a quote, a hypothetical, sarcasm, an impression or a game
   character so that it sounds like the speaker's own view.
5. **Keep the softener.** Never drop a "just kidding", "मज़ाक था", "not really" or a correction
   that comes right after a piece.
6. **Nothing points at cut-out words.** No piece opens with "he", "that", "wo", "isliye" or
   "lekin" unless its setup is in the clip.
7. **Never build a sentence the speaker didn't say**, and never add silence after a question
   for effect.
8. **Quotation marks only for words actually said**, in titles and captions.
9. **Never use ads, sponsor reads, cold-open teasers, intros or outros** as pieces.

## Live streams and gameplay
`fetch` says when a video is a live stream or gameplay (`-> video: live stream + gameplay with a
facecam`). Then these rules apply too:
- **Break screens are never clip material.** "Starting soon", "Be right back" and stream-ending
  screens are already left out (a `# ===== ... SCREEN =====` marker line shows where). Don't take a
  clip that runs into one; `cut --check` warns if one does.
- **Build clips around the streamer's own talk and reactions.** The transcript also holds the game's
  characters, cut-scenes and music; they are context, not the clip's voice. A game line may stay in
  when the streamer's reaction needs it.
- **Quiet stretches are normal.** The streamer plays without talking for a while; that is not a dead
  video. Inside a clip, though, a silence of more than ~8 s loses viewers unless the gameplay itself
  is the point (a chase, a crash, a boss fight): end before it, or join the pieces around it
  (`cut --check` points these out). Good moments separated by long quiet stretches are what deep
  clips are for.
- **Leave out stream housekeeping**: hello chat, "is the audio OK", viewer counts, subscribe
  requests, "I'm back", reading donations, setting up the scene.

## How many
`parts` prints the number to make (`-> clips: aim for N`):
- **The user asked for a number** ("at least 10", "at most 5", "give me 8"): follow it exactly.
  "At least 10" means 10 or more, never fewer: if the video is thin, take the 10 best anyway and
  say which ones are weaker.
- **No number**: about one clip per 7 minutes of real video (break screens don't count), at least 3,
  at most `"max_clips"` from settings.json (20). Make fewer only when there aren't that many decent
  moments; never pad with weak ones. The owner posts almost any decent clip, so don't hold good
  ones back either. If nothing is clip-worthy, say so.
- Deep clips count towards the number.

## Ranking (score 1–10)
Rank by: hook strength (curiosity + relevance) > a clear payoff > emotional energy (conviction,
humour, surprise) > quotability (a line someone would screenshot) > visual clarity (the speaker
on camera, not a slide). Put the best clip first.

## Timestamps
- Use the `[start-end]` seconds from `transcript.txt`. Start at the **start** of the hook line and
  end at the **end** of the payoff line.
- Times don't need to be perfect: the cutter snaps them to whole words and adds natural handles.
  Never cut inside a sentence, though.

## Tight cuts (the owner's taste)
From the owner's blind comparison of two versions on the same videos (Nov 2026), where the tighter cut
won every time the two cut the same moment:
- **Open on the hook.** Drop the warm-up: the clip starts on the first line worth hearing.
- **End on the payoff.** Stop after the line that lands the point; cut after-thoughts and restating.
- **Cut detours inside long answers.** A long continuous answer whose hook gets lost midway is worse
  than the same answer with the side story or repeat cut out (pieces in the order said, smooth).
- **Keep extra seconds only when they carry something**: a funny line, the fight the talk is about,
  the setup the payoff needs.
- **Never cut the hook line** out of the middle, and **never end before the speaker finishes the point.**

## clips.json format
Write `output/<project>/clips.json`:

```json
{
  "clips": [
    {
      "id": 1,
      "title": "Why Hard Work Isn't Enough",
      "hook": "Exact first line of the clip",
      "ranges": [[123.4, 171.9]],
      "score": 9,
      "hook_type": "contrarian",
      "why": "One sentence: why this works as a standalone short",
      "emphasis": ["broke", "ten", "million"],
      "caption": "Ready-to-post caption for TikTok/Reels/Shorts, 1-2 lines + 3-5 hashtags",
      "clarify": [["इस movie", "Ramayana"]],
      "post": {
        "youtube": {"title": "Why Hard Work Isn't Enough (He Learned It at 40)",
                    "description": "One or two lines on what the clip shows. #hardwork #success #podcast"},
        "instagram": {"caption": "A hook line + a question to comment on 👇 #hardwork #success #mindset"},
        "facebook": {"caption": "A hook line that makes people want to watch. #hardwork"}
      }
    }
  ]
}
```

- `clarify` (optional): the clip points at something it never names ("इस movie", "ये film", "वो",
  "उनका", "he", "this company") and a viewer couldn't know what. Add `[spoken words exactly as in the
  transcript, the noun]`; the captions then show the noun in brackets after the first mention: "IS
  MOVIE [RAMAYANA] KA". Brackets are the usual mark of an editor's addition, so nothing is put in the
  speaker's mouth. Only what the video itself makes clear (its title, an earlier line), 1–3 words, never
  an opinion. If the line that names it is short and close by, adding that line is better.
- `caption` and `post` are needed for **every** clip, on every route (short videos, long videos read
  in parts, deep clips). They are what the user posts, by hand or with PostKaro (`run.py post`).
- `post`: the text for each platform, in the same language and script as the captions (Roman
  Hinglish for Hindi/Hinglish videos unless settings.json says otherwise). Write each one for its
  platform, not one copy-paste:
  - `youtube.title`: use the 100 characters well (aim for 85–100, never over), so a stranger knows
    what it is: the hook (often the `title`, a little fuller), then `|` and who or what it's about
    (the game, show, person or podcast: "Black Myth Wukong Hindi Gameplay", "Khan Sir on Raj
    Shamani"), then 2–3 hashtags that match the clip, the last one `#Shorts`, e.g. "Final Boss
    Yahin La Diya, Mar Gaya | Black Myth Wukong Hindi Gameplay #BlackMythWukong #Shorts". No
    unrelated tags like #viral or #trending: YouTube's rules allow only hashtags about the video.
    `youtube.description`: 1–2 lines + up to 3 hashtags. Don't
    add the full-video link: ClipKaro/PostKaro add "Full video: <link>" themselves.
  - `instagram.caption`: a hook line, then a question or call to comment, then **at most 5
    hashtags** (Instagram allows no more). No `#shorts`.
  - `facebook.caption`: 1–2 lines, 0–3 hashtags, no `#shorts`.
  - Deep clips: start every platform's text with the clip's `source_line` ("From 2 moments of the
    full video: 0:08 · 22:53"), so viewers know it is joined. The one exception is the YouTube
    title: end it with "(2 moments joined)" instead, so the title stays a title.
  - Never put `<` or `>` in YouTube text (YouTube refuses them).

- `title`: 3–7 words, a curiosity-driven name (used for the file name and as a posting title).
- `emphasis`: 2–6 single words that carry the meaning (numbers, money, strong verbs, the key
  noun). They stay highlighted in the brand colour in the captions. Use the exact word as spoken.
- `ranges`: one `[start, end]` pair, or 2–3 pairs for a splice (they play in the listed order).
- `from`: the id the critic gave the clip idea: a candidate id for long videos (`"p3-c1"`, copy its
  `ranges` from `candidates.txt`; `cut --check` warns when they differ), or `"s3"` for the third
  clip of a short video's shortlist.
- `clip_score` (from `critic.txt`): the clip score out of 10, e.g. `7.8`. `score` stays your own
  first impression from picking.
- `show_full` (optional): `[[a, b]]` source-time stretches shown as the whole landscape frame over
  a blurred background, when what matters lies outside a 9:16 crop (a product held up, a screen,
  a slide, a gesture across the room). Use sentence edges.
- `framing` (optional): `[[a, b, "left" | "right" | "center" | "split" | "full" | 0-1]]` chooses
  what a stretch shows: the face on the left or right, the centre, both people stacked (`split`),
  the whole frame (`full`), or an exact spot (0 = left edge, 1 = right edge). Usually written after
  looking at the `run.py frames` sheets, to fix the automatic choice or to show a reaction the
  sound can't catch (a silent laugh: `split`). It always wins over the automatic framing.

## Quality checklist (run it before you write the file)
- [ ] Would a stranger understand it with zero context?
- [ ] Is the first line a real hook, with no warm-up?
- [ ] Does it end on a payoff, not mid-thought?
- [ ] Is it 15–90 s (ideally 25–60 s)?
- [ ] One idea only, with nothing that refers outside the clip?
- [ ] No ads, housekeeping or retakes?
- [ ] No overlap with another clip?
