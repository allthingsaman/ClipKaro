# Contributing to ClipKaro

Thanks for helping! Bug reports, fixes, new languages, better docs and new sound effects are all
welcome.

## Reporting a bug
Open an issue with:
- what you ran (the command, or what you asked the agent),
- the full error message,
- your operating system, Python version, and whether you use an NVIDIA GPU,
- the output of `python install.py`.

Please don't attach videos you don't have the rights to share.

## Making a change
1. Fork the repository and create a branch.
2. Set up as in [docs/installation.md](docs/installation.md).
3. Read [docs/architecture.md](docs/architecture.md): it shows where everything lives and the
   design rules (judgment in the AI, mechanics in code; files are the interface; one plan, two
   renderers; never invent words).
4. Test your change on real videos: at least one English and one Hindi/Hinglish video, through
   `fetch`, `cut` and `edit`. Look at the result.
5. Update the docs if behaviour or options change (`docs/`, `README.md`, and the skill in
   `.claude/skills/clip-video/` if the AI editor should know).
6. Open a pull request that explains what changed and why.

## Code style
- Plain Python 3.10+, standard library first; new dependencies only when really needed.
- Keep error messages actionable: say what went wrong and the exact fix.
- Keep it cross-platform (Windows, macOS, Linux): use `pathlib`, quote paths, no shell-only tricks.

## What to work on
The plan for the next version, with the most useful improvements in order, is in
[docs/roadmap-v2.md](docs/roadmap-v2.md).

## Adding a language
See [docs/adding-a-language.md](docs/adding-a-language.md).

## Sound effects and fonts
Only add files with a licence that allows redistribution (e.g. CC0, SIL Open Font License), and
note the source and licence in `assets/sfx/README.md` or next to the font.

By contributing, you agree that your contributions are licensed under the [MIT License](LICENSE).
