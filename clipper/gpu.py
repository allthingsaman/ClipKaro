"""Optional NVIDIA GPU support for transcription.

faster-whisper runs on CTranslate2, which needs NVIDIA's cuBLAS and cuDNN libraries to use a GPU.
`python install.py` installs them into the project's .venv as pip packages (when it finds an NVIDIA GPU), and this module
puts them on the library search path before a model loads. Nothing here is required: when the GPU
can't be used, `fetch` says why and carries on with the CPU.

    python run.py gpu                    # GPU self-test with the tiny model (install.py runs it)
    python run.py gpu large-v3-turbo     # ... with the real transcription model (needs ~2 GB of VRAM)
"""
import glob
import os
import re
import sys
import sysconfig
from pathlib import Path

_handles = []        # keep os.add_dll_directory() handles alive
_enabled = False


def cuda_device_count():
    try:
        import ctranslate2
        return ctranslate2.get_cuda_device_count()
    except Exception:
        return 0


def pick_device(requested='auto'):
    """'auto' -> 'cuda' when an NVIDIA GPU + driver are present, otherwise 'cpu'."""
    if requested in ('cpu', 'cuda'):
        return requested
    return 'cuda' if cuda_device_count() > 0 else 'cpu'


def cuda_major():
    """CUDA major version the installed CTranslate2 was built for (12 for current releases)."""
    try:
        import ctranslate2
        pkg = Path(ctranslate2.__file__).parent
        for f in [*pkg.glob('*.dll'), *pkg.glob('*.so*'), *pkg.parent.glob('ctranslate2.libs/*')]:
            m = re.search(rb'cublas64_(\d+)\.dll|libcublas\.so\.(\d+)', f.read_bytes())
            if m:
                return int(m.group(1) or m.group(2))
    except Exception:
        pass
    return 12


def pip_packages():
    """The NVIDIA pip packages that match this CTranslate2 build."""
    v = cuda_major()
    return [f'nvidia-cublas-cu{v}', f'nvidia-cudnn-cu{v}>=9,<10', f'nvidia-cuda-nvrtc-cu{v}']


def _lib_dirs():
    roots = {sysconfig.get_paths()['purelib'], sysconfig.get_paths()['platlib']}
    sub = 'bin' if os.name == 'nt' else 'lib'
    return [Path(d) for r in roots for d in glob.glob(os.path.join(r, 'nvidia', '*', sub)) if os.path.isdir(d)]


def enable_nvidia_libs():
    """Make pip-installed cuBLAS/cuDNN findable by CTranslate2 (no-op if they aren't installed)."""
    global _enabled
    if _enabled:
        return
    _enabled = True
    dirs = _lib_dirs()
    if not dirs:
        return
    import ctypes
    if os.name == 'nt':
        os.environ['PATH'] = os.pathsep.join([str(d) for d in dirs] + [os.environ.get('PATH', '')])
        for d in dirs:
            try:
                _handles.append(os.add_dll_directory(str(d)))
            except OSError:
                pass
        patterns, loader = ('cublasLt64_*.dll', 'cublas64_*.dll', 'cudnn64_*.dll'), ctypes.WinDLL
    else:
        patterns = ('libcublasLt.so.*', 'libcublas.so.*', 'libcudnn*.so.*', 'libnvrtc*.so.*')

        def loader(p):
            return ctypes.CDLL(p, mode=ctypes.RTLD_GLOBAL)
    # load them up front, so CTranslate2 finds them already in memory
    for pat in patterns:
        for d in dirs:
            for f in sorted(d.glob(pat)):
                try:
                    loader(str(f))
                except OSError:
                    pass


def describe_error(e):
    """One readable line + a hint for the usual GPU failures."""
    from .models import is_network_error
    msg = ' '.join(str(e).split())[:240] or type(e).__name__
    low = msg.lower()
    if is_network_error(e):
        hint = ('a download from huggingface.co was cut off: that is the internet connection, not the GPU. '
                'Run the same command again')
    elif any(k in low for k in ('cublas', 'cudnn', 'nvrtc', '.dll', '.so', 'cannot be loaded', 'not found')):
        hint = 'the NVIDIA libraries are missing. Run:  python install.py'
    elif 'out of memory' in low:
        hint = 'the GPU ran out of memory (try --model medium, or close other GPU apps)'
    elif 'driver' in low or 'insufficient' in low:
        hint = 'the NVIDIA driver looks too old. Update it (Windows: NVIDIA App or nvidia.com; Linux: your distribution driver, see docs/installation.md)'
    else:
        hint = 'see the message above'
    return msg, hint


def selftest(model_name='tiny'):
    """Run a Whisper model on the GPU for a few seconds. Returns (ok, message)."""
    import numpy as np
    n = cuda_device_count()
    if n == 0:
        return False, 'no NVIDIA GPU (or no NVIDIA driver) found'
    enable_nvidia_libs()
    try:
        from faster_whisper import WhisperModel
        from .models import model_path
        model = WhisperModel(model_path(model_name), device='cuda', compute_type='float16')
        noise = (np.random.default_rng(0).standard_normal(16000 * 5) * 0.01).astype(np.float32)
        segments, _ = model.transcribe(noise, language='hi', beam_size=5)
        list(segments)
        return True, f'{n} NVIDIA GPU(s) ready for transcription ("{model_name}" ran on the GPU)'
    except Exception as e:
        msg, hint = describe_error(e)
        return False, f'{msg}  ->  {hint}'


if __name__ == '__main__':
    ok, msg = selftest(sys.argv[1] if len(sys.argv) > 1 else 'tiny')
    print(('[ok] GPU: ' if ok else '[!] GPU not usable: ') + msg)
    sys.exit(0 if ok else 1)
