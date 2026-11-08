# Instructions for AI coding agents

This file is for AI coding agents other than Claude Code (Codex, Cursor, GitHub Copilot, Gemini
CLI and others that read `AGENTS.md`). Claude Code reads `CLAUDE.md` and the skill directly.

ClipKaro turns long videos into vertical short-form clips. **You are the editor who picks the
moments**; the Python scripts do the download, transcription, cutting and rendering.

**Asked to install this repo?** Follow "For AI agents installing ClipKaro" in
[`README.md`](README.md).

When the user pastes a video link or file, or asks for clips, shorts, reels or TikToks:

1. Read and follow [`CLAUDE.md`](CLAUDE.md): the project rules.
2. Read and follow [`.claude/skills/clip-video/SKILL.md`](.claude/skills/clip-video/SKILL.md): the
   full workflow, end to end, without stopping for confirmation. It refers to
   `references/picking-moments.md` (how to choose moments; read it before picking) and
   `references/editing.md` (the edit's options).
3. For Hindi/Hinglish videos, also read [`docs/hinglish.md`](docs/hinglish.md).

Key points (details in the files above):
- Run everything from the repo root with `python run.py <command>` (`python3` on macOS/Linux).
  First-time setup: `python install.py` (it finds an NVIDIA graphics card by itself and sets it up).
- Transcription and rendering take minutes: run them so they can finish (in the background if
  your tool supports it) and keep the user posted.
- Results go to `output/<project>/`. Never commit or upload user videos or anything in `output/`.
- Never invent words: clips contain only what the speaker said.
- After `cut`, check clips with two people on screen (podcasts) or things being shown with
  `python run.py frames <project> --clips N`, and fix only what's wrong with `"framing"` /
  `"show_full"` in clips.json (details in the skill).
- Don't run commands that need administrator rights (`sudo`, installers); give the user the
  exact commands instead.
- User documentation is in [`docs/`](docs/README.md); how the code works is in
  [`docs/architecture.md`](docs/architecture.md).
