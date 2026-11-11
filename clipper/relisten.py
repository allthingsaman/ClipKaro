"""Listen again to the stretches of a transcript the recogniser was unsure of.

    python run.py relisten <project>

`fetch` does this by itself since Nov 2026. This command is for videos transcribed before that. In a
gameplay video transcribed as Hindi, a game character speaking English used to come out as Devanagari
nonsense, which became wrong captions. Each unsure stretch is heard again in the language Whisper hears
there: clear speech in another language replaces the nonsense, anything still unclear gets no captions.
words.json is backed up once to words-before-relisten.json. Then re-cut the clips it names.
"""
import argparse
import os
import shutil

from . import gpu
from .common import fmt_ts, load_json, project_dir
from .fetch import is_hindi, relisten, relisten_report, to_wav16k, write_transcript
from .models import model_path


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('project')
    ap.add_argument('--device', default='auto', help='auto (default), cuda, cpu')
    a = ap.parse_args()
    pdir = project_dir(a.project)
    project = load_json(pdir / 'project.json', {})
    tdir = pdir / 'transcript'
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
    new, info = relisten(model, audio, [{k: v for k, v in w.items() if k != 'unsure'} for w in words],
                         'hi' if is_hindi(lang) else lang, 5)
    if not info:
        print('nothing unclear: every stretch of speech was heard with confidence')
        return
    relisten_report(info)
    if not (tdir / 'words-before-relisten.json').exists():
        shutil.copy2(tdir / 'words.json', tdir / 'words-before-relisten.json')
    write_transcript(pdir, new, project)
    # which picked clips touch a changed stretch (they need cutting again to get the new captions)
    old_keys = {(round(w['s'], 2), w['w'], bool(w.get('unsure'))) for w in before}
    changed = [w for w in new if (round(w['s'], 2), w['w'], bool(w.get('unsure'))) not in old_keys]
    clips = (load_json(pdir / 'clips.json', {}) or {}).get('clips', [])
    hit = sorted({c['id'] for c in clips for r0, r1 in c['ranges'] for w in changed if r0 <= w['s'] < r1})
    if changed:
        print(f'   changed: {len(changed)} word(s), from {fmt_ts(changed[0]["s"])} to {fmt_ts(changed[-1]["e"])}')
    if hit:
        print(f'next: python run.py cut {pdir.name} --clips {",".join(map(str, hit))}   then edit them again')


if __name__ == '__main__':
    main()
