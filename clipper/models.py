"""Whisper model downloads (from huggingface.co, cached under ~/.cache/huggingface).

A dropped connection while downloading is retried a few times; huggingface_hub resumes partial
files, so a retry only fetches what is still missing.

    python -m clipper.models base large-v3-turbo     # download ahead of time (install.py does this when it finds an NVIDIA GPU)
"""
import os
import sys
import time

_NET = ('connecterror', 'connectionerror', 'connection aborted', 'connection reset', 'forcibly closed',
        'remoteprotocolerror', 'readerror', 'readtimeout', 'connecttimeout', 'timed out', 'timeout',
        'winerror 10054', 'winerror 10060', 'winerror 10061', 'getaddrinfo', 'name resolution',
        'temporary failure', 'max retries', 'ssl', 'proxyerror', 'incompleteread', 'chunkedencodingerror',
        'offlinemodeisenabled', 'localentrynotfounderror', 'cannot find the requested files')

ALLOW = ['config.json', 'preprocessor_config.json', 'model.bin', 'tokenizer.json', 'vocabulary.*']


def is_network_error(e):
    text = f'{type(e).__name__}: {e}'.lower()
    return any(k in text for k in _NET)


def network_help(name, e):
    msg = ' '.join(str(e).split())[:200]
    return (f'could not download the Whisper model "{name}" from huggingface.co ({msg}).\n'
            'This is the internet connection, not your GPU or this tool. Run the same command again:\n'
            'the download continues where it stopped. If it keeps failing, try another network\n'
            '(e.g. a phone hotspot) or a VPN for this one download; afterwards the model is cached.')


def repo_id(name):
    from faster_whisper.utils import _MODELS
    return name if '/' in name else _MODELS.get(name, name)


def model_path(name, progress=False, attempts=4):
    """Local folder of a Whisper model, downloading it first when needed. Raises on failure."""
    if os.path.isdir(name):
        return name
    import huggingface_hub
    if ':' in name:                        # "owner/repo:int8": only that folder of the repo (a smaller build)
        rid, sub = name.split(':', 1)
        pats = [f'{sub}/{p}' for p in ALLOW]
        try:
            return os.path.join(huggingface_hub.snapshot_download(rid, allow_patterns=pats, local_files_only=True), sub)
        except Exception:
            return os.path.join(huggingface_hub.snapshot_download(rid, allow_patterns=pats), sub)
    rid = repo_id(name)
    try:                                   # already downloaded? no network needed
        return huggingface_hub.snapshot_download(rid, allow_patterns=ALLOW, local_files_only=True)
    except Exception:
        pass
    kw = {} if progress else {'tqdm_class': _silent_tqdm()}
    for attempt in range(1, attempts + 1):
        try:
            return huggingface_hub.snapshot_download(rid, allow_patterns=ALLOW, **kw)
        except Exception as e:
            if not is_network_error(e) or attempt == attempts:
                raise
            wait = 5 * attempt
            print(f'   ! download of "{name}" interrupted ({type(e).__name__}); retrying in {wait}s '
                  f'({attempt}/{attempts - 1}) ...', flush=True)
            time.sleep(wait)


def _silent_tqdm():
    from faster_whisper.utils import disabled_tqdm
    return disabled_tqdm


def main(names):
    ok = True
    for n in names:
        print(f'-> model "{n}" ({repo_id(n)}) ...', flush=True)
        try:
            print(f'   ok: {model_path(n, progress=True)}')
        except Exception as e:
            ok = False
            print('   [!] ' + (network_help(n, e) if is_network_error(e) else f'{type(e).__name__}: {e}'))
    return ok


if __name__ == '__main__':
    sys.exit(0 if main(sys.argv[1:] or ['base', 'large-v3-turbo']) else 1)
