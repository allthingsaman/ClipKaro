"""Single entry point. Always runs inside the project's .venv (created by install.py).

    python run.py info <youtube-url | local-file>        a quick look first: length, live stream?, deep clips?
    python run.py fetch <youtube-url | local-file>       download audio + transcribe (and the video, for YouTube)
    python run.py kind <project>                         live stream? gameplay? break screens to leave out (fetch runs it)
    python run.py romanize <project>                     Roman Hinglish captions for Hindi/Hinglish videos
    python run.py cut <project>                          cut the picked clips to 9:16
    python run.py edit <project> [--engine python|remotion] [--clips 1,3]
    python run.py parts <project>                        split a long transcript into parts for careful reading
    python run.py topics <project>                       join the parts' answers: topic map + clip candidates
    python run.py sound <project>                        sound cues: laughter, applause, lively spots (fetch runs it)
    python run.py critic <project>                       a blind second opinion on every clip idea (clip score)
    python run.py deep <project>                         deep clips: stories spread across the video (when asked)
    python run.py honesty <project>                      deep clips: three judges check nothing changes what was meant
    python run.py find <project> "exact phrase"          word-accurate time of a phrase
    python run.py fixword <project> "wrong" "right"     fix a misheard caption word everywhere (--at T: one place)
    python run.py more <project> [--add N]               the good ideas not cut yet; add them as more clips later
    python run.py frames <project>                       preview what the vertical crop keeps (spot show_full moments)
    python run.py gpu [model]                            check that transcription runs on the NVIDIA GPU
    python run.py post <project> [--open]                hand the clips to PostKaro (the posting app), if installed
    python run.py relisten <project>                     listen again to unclear speech (game voices): fix or drop its captions
    python run.py hear <project>                         careful listening: a second hearing of a noisy stream (fetch runs it)
    python run.py rehear <project>                       careful listening: every picked clip heard again + word-check packets
    python run.py wordcheck <project>                    careful listening: apply the word-check helpers' answers
    python run.py watch <project>                        frame sheets: the overview of a gameplay video (fetch runs it)
    python run.py zoom <project>                         frame sheets: close-ups of the spots the readers named
    python run.py events <project>                       frame sheets: the events seen, into the clips
    python run.py tidy <project>                         no captions for words made up during laughter, noise or loops
    python run.py sfx [add <file> <mood>]                your sound effects by mood (shock, funny, fear ...)
    python run.py music [add <file> <mood>]              your background music by mood (chill, hype ...)
    python run.py qa <project>                           check every finished clip (captions, cuts, loudness, black frames ...)
    python run.py test                                   ClipKaro's own tests (fast; protect v1.1's behaviour)
    python run.py asr-bench make|run [model]|report      test speech-to-text models on your own videos
    python run.py live start|next|done|status|stop <name> live clipping: clips posted while you stream (docs/live-clipping.md)

Run `python run.py <command> -h` for the options of each step. Defaults live in settings.json.
"""
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PY = ROOT / '.venv' / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')

COMMANDS = {
    'info': 'clipper.info',
    'fetch': 'clipper.fetch',
    'kind': 'clipper.kind',
    'romanize': 'clipper.romanize',
    'cut': 'clipper.cut',
    'brand': 'clipper.brand',
    'edit': 'clipper.edit',
    'find': 'clipper.find',
    'fixword': 'clipper.fixword',
    'more': 'clipper.more',
    'tidy': 'clipper.tidy',
    'sfx': 'clipper.sfx',
    'music': 'clipper.music',
    'qa': 'clipper.qa',
    'test': 'clipper.selftest',
    'parts': 'clipper.parts',
    'topics': 'clipper.topics',
    'sound': 'clipper.sound',
    'voices': 'clipper.voices',
    'hints': 'clipper.hints',
    'captions': 'clipper.captions',
    'critic': 'clipper.critic',
    'deep': 'clipper.deep',
    'honesty': 'clipper.honesty',
    'frames': 'clipper.frames',
    'post': 'clipper.post',
    'relisten': 'clipper.relisten',
    'hear': 'clipper.hear',
    'rehear': 'clipper.rehear',
    'wordcheck': 'clipper.wordcheck',
    'watch': 'clipper.watchcmd',
    'zoom': 'clipper.zoom',
    'events': 'clipper.events',
    'asr-bench': 'clipper.asrbench',
    'gpu': 'clipper.gpu',
    'live': 'clipper.live',
}

# heavy steps: while a live clipping session runs they get a low priority and the processor's video encoder,
# so OBS keeps the graphics card's encoder and the stream never drops frames
HEAVY = {'fetch', 'cut', 'edit', 'qa', 'frames', 'sound', 'hints', 'voices', 'relisten', 'kind', 'hear', 'rehear',
         'watch', 'zoom', 'events'}


def live_running():
    """True while a live clipping session has a fresh heartbeat (clipper/live.py writes it)."""
    import glob
    import time
    for hb in glob.glob(str(ROOT / 'output' / '_live' / '*' / 'heartbeat')):
        try:
            if time.time() - float(open(hb).read()) < 90:
                return True
        except (OSError, ValueError):
            pass
    return False


def with_nvidia_libs(env):
    """Linux: the CUDA libraries from `install.py` live inside .venv; the loader only reads
    LD_LIBRARY_PATH when a process starts, so set it for the child process."""
    if sys.platform.startswith('linux'):
        import glob
        dirs = sorted(glob.glob(str(ROOT / '.venv' / 'lib' / 'python3*' / 'site-packages' / 'nvidia' / '*' / 'lib')))
        if dirs:
            env['LD_LIBRARY_PATH'] = os.pathsep.join(dirs + ([env['LD_LIBRARY_PATH']] if env.get('LD_LIBRARY_PATH') else []))
    return env


def find_ffmpeg():
    """Windows: winget puts ffmpeg on the PATH of NEW terminals only, so find it for this one too.
    macOS: Homebrew's plain "ffmpeg" has no libass (captions), so ClipKaro uses "ffmpeg-full", which
    Homebrew keeps off the PATH: put it first. A background app on a Mac may not see Homebrew's folder
    at all: add it when ffmpeg isn't found otherwise."""
    import glob
    import shutil
    if sys.platform == 'darwin':
        for d in ('/opt/homebrew/opt/ffmpeg-full/bin', '/usr/local/opt/ffmpeg-full/bin'):
            if os.path.isfile(os.path.join(d, 'ffmpeg')):
                os.environ['PATH'] = d + os.pathsep + os.environ.get('PATH', '')
                return
        if not shutil.which('ffmpeg'):
            for d in ('/opt/homebrew/bin', '/usr/local/bin'):
                if os.path.isfile(os.path.join(d, 'ffmpeg')):
                    os.environ['PATH'] = os.environ.get('PATH', '') + os.pathsep + d
                    return
        return
    if os.name != 'nt' or shutil.which('ffmpeg'):
        return
    local = os.environ.get('LOCALAPPDATA', '')
    places = [os.path.join(local, 'Microsoft', 'WinGet', 'Links'),
              os.path.join(os.environ.get('ProgramFiles', ''), 'WinGet', 'Links')]
    places += glob.glob(os.path.join(local, 'Microsoft', 'WinGet', 'Packages', 'Gyan.FFmpeg*', '*', 'bin'))
    for d in places:
        if os.path.isfile(os.path.join(d, 'ffmpeg.exe')):
            os.environ['PATH'] = d + os.pathsep + os.environ.get('PATH', '')
            return


def main():
    if len(sys.argv) < 2 or sys.argv[1] not in COMMANDS:
        print(__doc__)
        sys.exit(1)
    if not PY.exists():
        print('First run setup:  python install.py')
        sys.exit(1)
    find_ffmpeg()
    env = dict(os.environ, PYTHONIOENCODING='utf-8', PYTHONUTF8='1', PYTHONUNBUFFERED='1', HF_HUB_DISABLE_XET='1',
               HF_HUB_DISABLE_SYMLINKS_WARNING='1', HF_HUB_VERBOSITY='error')
    cmd = [str(PY), '-m', COMMANDS[sys.argv[1]], *sys.argv[2:]]
    kw = {}
    if sys.argv[1] in HEAVY and live_running():
        env.setdefault('CLIPKARO_ENCODER', 'x264')
        env['CLIPKARO_LIVE'] = '1'      # careful listening and frame sheets wait: the card is OBS's (v2.7.1)
        kw = {'creationflags': 0x00004000} if os.name == 'nt' else {'preexec_fn': lambda: os.nice(10)}
    sys.exit(subprocess.run(cmd, cwd=ROOT, env=with_nvidia_libs(env), **kw).returncode)


if __name__ == '__main__':
    main()
