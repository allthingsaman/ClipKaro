"""Listen again to the stretches of a transcript the recogniser was unsure of.

    python run.py relisten <project>              unsure stretches (game voices in another language)
    python run.py relisten <project> --stretched  stretched words: one "word" over several that were skipped

`fetch` does both by itself (unsure stretches since Nov 2026, stretched words since v2.3). This command
is for videos transcribed before that.
- Unsure stretches: in a gameplay video transcribed as Hindi, a game character speaking English used to
  come out as Devanagari nonsense, which became wrong captions. Each unsure stretch is heard again in
  the language Whisper hears there: clear speech in another language replaces the nonsense, anything
  still unclear gets no captions. words.json is backed up once to words-before-relisten.json.
- Stretched words: Whisper sometimes skips a few words and stretches the word next to them over their
  time, so those words are missing from the captions. Each such word is heard again with two words of
  context either side; new words replace the old ones only when they add words and keep most of the old
  ones. It works on the current words.json, so caption fixes and tidy marks stay. words.json is backed
  up once to words-before-stretched.json.
`--current` hears the unsure stretches of the words as they are now, so caption fixes stay (then run
`python run.py tidy <project>` again, which marks made-up words anew).
Then re-cut the clips it names.
"""
import argparse
import os
import shutil

from . import gpu
from .common import fmt_ts, load_json, project_dir
from .fetch import (HINGLISH, HINGLISH_PROMPT, is_hindi, relisten, relisten_report, repair_stretched, to_wav16k,
                    write_transcript)
from .models import model_path


def changed_clips(pdir, before, new):
    """Report the changed words and the picked clips that touch them (they need cutting again)."""
    old_keys = {(round(w['s'], 2), w['w'], bool(w.get('unsure'))) for w in before}
    changed = [w for w in new if (round(w['s'], 2), w['w'], bool(w.get('unsure'))) not in old_keys]
    clips = (load_json(pdir / 'clips.json', {}) or {}).get('clips', [])
    hit = sorted({c['id'] for c in clips for r0, r1 in c['ranges'] for w in changed if r0 <= w['s'] < r1})
    if changed:
        print(f'   changed: {len(changed)} word(s), from {fmt_ts(changed[0]["s"])} to {fmt_ts(changed[-1]["e"])}')
    if hit:
        print(f'next: python run.py cut {pdir.name} --clips {",".join(map(str, hit))}   then edit them again')


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('project')
    ap.add_argument('--device', default='auto', help='auto (default), cuda, cpu')
    ap.add_argument('--stretched', action='store_true',
                    help='hear stretched words again (one word over several that were skipped)')
    ap.add_argument('--current', action='store_true',
                    help='start from the words as they are now (keeps caption fixes; run tidy after), '
                         'not from the first transcription')
    a = ap.parse_args()
    pdir = project_dir(a.project)
    project = load_json(pdir / 'project.json', {})
    tdir = pdir / 'transcript'
    if a.stretched or a.current:
        words = load_json(tdir / 'words.json')
    else:
        # always from the words as first transcribed (running it again gives the same result)
        words = load_json(tdir / 'words-before-relisten.json') or load_json(tdir / 'words.json')
    wav = pdir / 'source' / 'audio16k.wav'
    if not wav.exists():
        src = next((f for f in (pdir / 'source').glob('audio.*')), None)
        if not src:
            raise SystemExit(f'no audio in {pdir / "source"}: run fetch again')
        to_wav16k(src, wav)
    import soundfile as sf
    from faster_whisper import WhisperModel
    audio, _ = sf.read(str(wav), dtype='float32')
    device = gpu.pick_device(a.device)
    if device == 'cuda':
        gpu.enable_nvidia_libs()
    name = project.get('asr_model') or 'large-v3-turbo'
    print(f'-> listening again with whisper "{name}" on {device.upper()} ...', flush=True)
    model = WhisperModel(model_path(name), device=device, compute_type='float16' if device == 'cuda' else 'int8',
                         cpu_threads=max(1, (os.cpu_count() or 4) - 1))
    lang = project.get('language') or 'en'
    before = [dict(w) for w in words]

    if a.stretched:
        new, changes = repair_stretched(model, audio, [dict(w) for w in words], 'hi' if is_hindi(lang) else lang, 5,
                                        HINGLISH_PROMPT if lang == HINGLISH else None)
        if not changes:
            print('no stretched word hid any skipped words')
            return
        for old, got in changes:
            print(f'   "{old}"  ->  "{got}"')
        if not (tdir / 'words-before-stretched.json').exists():
            shutil.copy2(tdir / 'words.json', tdir / 'words-before-stretched.json')
        write_transcript(pdir, new, project)
        changed_clips(pdir, before, new)
        return

    new, info = relisten(model, audio, [{k: v for k, v in w.items() if k != 'unsure'} for w in words],
                         'hi' if is_hindi(lang) else lang, 5)
    if not info:
        print('nothing unclear: every stretch of speech was heard with confidence')
        return
    relisten_report(info)
    backup = tdir / ('words-before-relisten-current.json' if a.current else 'words-before-relisten.json')
    if not backup.exists():
        shutil.copy2(tdir / 'words.json', backup)
    write_transcript(pdir, new, project)
    changed_clips(pdir, before, new)
    if a.current:
        print(f'next: python run.py tidy {pdir.name}   (marks made-up words again)')


if __name__ == '__main__':
    main()
