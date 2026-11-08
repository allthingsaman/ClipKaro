"""One-time setup: creates a private Python environment (.venv) and checks your tools.

    python install.py            # everything. An NVIDIA graphics card is found automatically: then the
                                 # GPU libraries (~1.5-2.5 GB) and the speech models (~1.7 GB) are set up too
    python install.py --cpu      # skip the NVIDIA GPU part
    python install.py --gpu      # the same as the default, but explain clearly when no GPU can be used
    python install.py --models   # also download the speech models ahead of time (without a GPU)
    python install.py --remotion # also install the optional Remotion edit engine (needs Node.js)

Safe to run again at any time.
"""
import os
import re
import shutil
import subprocess
import sys
import venv
from pathlib import Path

ROOT = Path(__file__).resolve().parent
VENV = ROOT / '.venv'
PY = VENV / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')

# install commands per system (docs/installation.md has the full guide)
INSTALL_HINTS = {
    'ffmpeg': {
        'nt': 'winget install -e --id Gyan.FFmpeg   (then open a NEW terminal)',
        'darwin': 'brew install ffmpeg',
        'debian': 'sudo apt install ffmpeg',
        'fedora': 'sudo dnf swap ffmpeg-free ffmpeg --allowerasing   (needs RPM Fusion enabled: '
                  "Fedora's own ffmpeg-free has no libx264. See docs/installation.md)",
        'arch': 'sudo pacman -S ffmpeg',
        'suse': "install ffmpeg from the Packman repository (openSUSE's own build has no libx264)",
        'linux': 'install the full ffmpeg (with libx264 and libass) from your package manager',
    },
    'node': {
        'nt': 'winget install -e --id OpenJS.NodeJS.LTS   (then open a NEW terminal)',
        'darwin': 'brew install node',
        'debian': 'sudo apt install nodejs   (if that gives a version older than 20, use the LTS from nodejs.org)',
        'fedora': 'sudo dnf install nodejs',
        'arch': 'sudo pacman -S nodejs npm',
        'suse': 'sudo zypper install nodejs',
        'linux': 'install Node.js 20+ (LTS) from nodejs.org',
    },
}


def system():
    """'nt', 'darwin', or the Linux family ('debian', 'fedora', 'arch', 'suse', 'linux')."""
    if os.name == 'nt':
        return 'nt'
    if sys.platform == 'darwin':
        return 'darwin'
    try:
        info = Path('/etc/os-release').read_text(encoding='utf-8', errors='replace').lower()
    except OSError:
        return 'linux'
    ids = ' '.join(re.findall(r'^(?:id|id_like)=["\']?([^"\'\n]+)', info, re.M))
    for family, keys in (('fedora', ('fedora', 'rhel', 'centos')), ('debian', ('debian', 'ubuntu')),
                         ('arch', ('arch',)), ('suse', ('suse',))):
        if any(k in ids for k in keys):
            return family
    return 'linux'


def hint(tool):
    return INSTALL_HINTS[tool][system()]


def ffmpeg_missing_features():
    """Parts of ffmpeg that cutting and captions need: the libx264 encoder and the libass filter."""
    def listing(what):
        r = subprocess.run(['ffmpeg', '-hide_banner', what], capture_output=True, text=True, errors='replace')
        return r.stdout
    missing = []
    if 'libx264' not in listing('-encoders'):
        missing.append('libx264 (video encoder)')
    if not re.search(r'^\s*\S{3}\s+ass\s', listing('-filters'), re.M):
        missing.append('libass (captions)')
    return missing


def example_path():
    return {'nt': r'C:\Users\you\Videos\my video.mp4', 'darwin': '/Users/you/Movies/my video.mp4'}.get(
        system(), '/home/you/Videos/my video.mp4')


def find_winget_ffmpeg():
    """winget puts ffmpeg on the PATH of NEW terminals only. Find it for this one too."""
    if os.name != 'nt' or shutil.which('ffmpeg'):
        return
    import glob
    local = os.environ.get('LOCALAPPDATA', '')
    places = [os.path.join(local, 'Microsoft', 'WinGet', 'Links'),
              os.path.join(os.environ.get('ProgramFiles', ''), 'WinGet', 'Links')]
    places += glob.glob(os.path.join(local, 'Microsoft', 'WinGet', 'Packages', 'Gyan.FFmpeg*', '*', 'bin'))
    for d in places:
        if os.path.isfile(os.path.join(d, 'ffmpeg.exe')):
            os.environ['PATH'] = d + os.pathsep + os.environ.get('PATH', '')
            return


def main():
    ok = True
    print('== ClipKaro setup ==')

    if sys.version_info < (3, 10):
        print(f'[X] Python 3.10+ needed (you have {sys.version.split()[0]}).')
        sys.exit(1)
    print(f'[ok] Python {sys.version.split()[0]}')

    find_winget_ffmpeg()
    for tool in ('ffmpeg', 'ffprobe'):
        if shutil.which(tool):
            print(f'[ok] {tool}')
        else:
            ok = False
            print(f'[X] {tool} not found. Install it:  {hint("ffmpeg")}')
    if shutil.which('ffmpeg'):
        missing = ffmpeg_missing_features()
        if missing:
            ok = False
            print(f'[X] your ffmpeg has no {" and no ".join(missing)}, which cutting and captions need. '
                  f'Install the full ffmpeg:  {hint("ffmpeg")}')
        else:
            print('[ok] ffmpeg has libx264 and libass')

    node = shutil.which('node')
    if node:
        v = subprocess.run([node, '--version'], capture_output=True, text=True).stdout.strip()
        m = re.match(r'v?(\d+)', v)
        if m and int(m.group(1)) < 20:
            print(f'[!] node {v} is old. YouTube downloads work best with Node.js 20 or newer:  {hint("node")}')
        else:
            print(f'[ok] node {v} (helps YouTube downloads; needed only for the optional Remotion engine)')
    else:
        print(f'[!] node not found (recommended for reliable YouTube downloads):  {hint("node")}')

    if not PY.exists():
        print('-> creating .venv ...')
        venv.create(VENV, with_pip=True)
    print('-> installing Python packages (first time takes a few minutes) ...')
    subprocess.run([str(PY), '-m', 'pip', 'install', '--upgrade', 'pip', '-q'], check=False)
    r = subprocess.run([str(PY), '-m', 'pip', 'install', '-q', '-r', str(ROOT / 'requirements.txt')])
    if r.returncode != 0:
        ok = False
        print('[X] pip install failed (see the error above).')
    else:
        # YouTube changes often; keeping yt-dlp current fixes most download errors
        subprocess.run([str(PY), '-m', 'pip', 'install', '-q', '-U', 'yt-dlp[default]'], check=False)
        print('[ok] Python packages (yt-dlp up to date)')
        # optional: hears who is talking and when people laugh, for podcasts with two people on
        # screen. Without it everything still works; those shots just keep the classic framing.
        r2 = subprocess.run([str(PY), '-m', 'pip', 'install', '-q', 'sherpa-onnx>=1.10'], check=False)
        if r2.returncode == 0:
            print('[ok] sherpa-onnx (two-person framing for podcasts)')
        else:
            print('[!] sherpa-onnx could not be installed: podcasts with two people keep the classic framing')

    # NVIDIA GPU: set up automatically when a card with a working driver is found (--cpu skips it)
    gpu_found = False
    if PY.exists() and '--cpu' not in sys.argv:
        gpu_found = setup_gpu(asked='--gpu' in sys.argv)
    if (gpu_found or '--models' in sys.argv) and PY.exists():
        print('-> downloading the speech models ahead of time: large-v3-turbo (~1.6 GB) and base (~150 MB).')
        print('   First time only; if the connection drops it retries and resumes.')
        r = subprocess.run([str(PY), '-m', 'clipper.models', 'base', 'large-v3-turbo'], cwd=ROOT, env=hf_env())
        if r.returncode != 0:
            print('[!] model download incomplete. Run  python install.py --models  again later '
                  '(or just start clipping: it downloads what is missing).')

    if '--remotion' in sys.argv:
        npm = shutil.which('npm')
        if not npm:
            ok = False
            print(f'[X] npm not found, the Remotion engine needs Node.js:  {hint("node")}')
        else:
            print('-> installing the Remotion engine (npm) ...')
            r = subprocess.run([npm, 'install', '--no-audit', '--no-fund'], cwd=ROOT / 'remotion',
                               shell=(os.name == 'nt'))
            ok = ok and r.returncode == 0
            print('[ok] Remotion engine' if r.returncode == 0 else '[X] npm install failed')

    print()
    if ok:
        print('Setup complete. Open this folder in Claude Code (or another AI coding agent, see AGENTS.md) and say:')
        print('    clip this video: https://youtu.be/...')
        print(f'    clip this video: "{example_path()}"')
    else:
        print('Setup finished with problems, fix the [X] items above and run again.')
    sys.exit(0 if ok else 1)


def hf_env():
    env = dict(os.environ, PYTHONUTF8='1', PYTHONIOENCODING='utf-8', HF_HUB_DISABLE_XET='1',
               HF_HUB_DISABLE_SYMLINKS_WARNING='1', HF_HUB_VERBOSITY='error')
    if sys.platform.startswith('linux'):     # CUDA libraries installed into .venv by setup_gpu()
        import glob
        dirs = sorted(glob.glob(str(VENV / 'lib' / 'python3*' / 'site-packages' / 'nvidia' / '*' / 'lib')))
        if dirs:
            env['LD_LIBRARY_PATH'] = os.pathsep.join(dirs + ([env['LD_LIBRARY_PATH']] if env.get('LD_LIBRARY_PATH') else []))
    return env


def setup_gpu(asked=False):
    """NVIDIA libraries for GPU transcription, installed into .venv, then a quick GPU self-test.
    Runs on every install: it does nothing without an NVIDIA card (asked=True: --gpu was given).
    Optional: if anything here fails, transcription simply runs on the CPU.
    Returns True when an NVIDIA GPU was found and its libraries are installed."""
    slow = 'Videos will be transcribed on the CPU: that works, but it is slow (not recommended).'
    if sys.platform == 'darwin':
        if asked:
            print('[!] --gpu is for NVIDIA graphics cards (Windows / Linux). Macs transcribe on the CPU.')
        return False
    env = hf_env()
    q = subprocess.run([str(PY), '-c', 'from clipper import gpu; print(gpu.cuda_device_count()); '
                        'print(" ".join(gpu.pip_packages()))'], cwd=ROOT, capture_output=True, text=True, env=env)
    lines = q.stdout.split('\n')
    if q.returncode != 0 or not lines[0].strip().isdigit():
        print('[!] could not check for an NVIDIA GPU (is the Python install above ok?)')
        return False
    if int(lines[0]) == 0:
        print(f'[!] no NVIDIA graphics card found (or its driver is not installed). {slow}\n'
              '    Have an NVIDIA card? Install or update its driver (see docs/installation.md), check that  '
              'nvidia-smi  shows it, then run  python install.py  again.')
        return False
    print(f'[ok] NVIDIA GPU found ({lines[0].strip()}): setting up GPU transcription')
    print('-> installing NVIDIA GPU libraries for transcription (about 1.5-2.5 GB, first time only) ...')
    r = subprocess.run([str(PY), '-m', 'pip', 'install', '-q', '-U', *lines[1].split()])
    if r.returncode != 0:
        print(f'[!] could not install the NVIDIA libraries (see above). {slow} Run  python install.py  again.')
        return False
    print('-> testing the GPU (downloads a tiny 75 MB test model once) ...')
    env = hf_env()       # again: the libraries just installed must be on the Linux library path
    t = subprocess.run([str(PY), '-m', 'clipper.gpu'], cwd=ROOT, env=env)
    if t.returncode != 0:
        print('   Transcription will use the CPU until this is fixed (everything else works the same).')
    return True


if __name__ == '__main__':
    main()
