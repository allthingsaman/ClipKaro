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
    python run.py frames <project>                       preview what the vertical crop keeps (spot show_full moments)
    python run.py gpu [model]                            check that transcription runs on the NVIDIA GPU
    python run.py post <project> [--open]                hand the clips to PostKaro (the posting app), if installed
    python run.py relisten <project>                     listen again to unclear speech (game voices): fix or drop its captions
    python run.py asr-bench make|run [model]|report      test speech-to-text models on your own videos

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
    'parts': 'clipper.parts',
    'topics': 'clipper.topics',
    'sound': 'clipper.sound',
    'critic': 'clipper.critic',
    'deep': 'clipper.deep',
    'honesty': 'clipper.honesty',
    'frames': 'clipper.frames',
    'post': 'clipper.post',
    'relisten': 'clipper.relisten',
    'asr-bench': 'clipper.asrbench',
    'gpu': 'clipper.gpu',
}


def with_nvidia_libs(env):
    """Linux: the CUDA libraries from `install.py` live inside .venv; the loader only reads
    LD_LIBRARY_PATH when a process starts, so set it for the child process."""
    if sys.platform.startswith('linux'):
        import glob
        dirs = sorted(glob.glob(str(ROOT / '.venv' / 'lib' / 'python3*' / 'site-packages' / 'nvidia' / '*' / 'lib')))
        if dirs:
            env['LD_LIBRARY_PATH'] = os.pathsep.join(dirs + ([env['LD_LIBRARY_PATH']] if env.get('LD_LIBRARY_PATH') else []))
    return env


def find_winget_ffmpeg():
    """winget puts ffmpeg on the PATH of NEW terminals only. Find it for this one too."""
    import glob
    import shutil
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
    find_winget_ffmpeg()
    env = dict(os.environ, PYTHONIOENCODING='utf-8', PYTHONUTF8='1', PYTHONUNBUFFERED='1', HF_HUB_DISABLE_XET='1',
               HF_HUB_DISABLE_SYMLINKS_WARNING='1', HF_HUB_VERBOSITY='error')
    cmd = [str(PY), '-m', COMMANDS[sys.argv[1]], *sys.argv[2:]]
    sys.exit(subprocess.run(cmd, cwd=ROOT, env=with_nvidia_libs(env)).returncode)


if __name__ == '__main__':
    main()
