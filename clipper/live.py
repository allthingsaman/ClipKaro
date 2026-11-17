"""Live clipping (v2.6): clips posted while the stream is still running.

OBS records the stream and starts a new file every 10 minutes (Settings > Output > Recording >
"Automatically split file"). This watcher takes each finished piece, writes down its words as for any
video (the Hinglish model, game voices told apart, hints from sound and picture) and adds what the Twitch
audience did then (chat spikes, viewer clips). Claude, running every 10 minutes with /loop, picks 0-2 clips
from each ready piece, and they are cut, edited and posted at once through PostKaro.

    python run.py live keys --client-id ID --client-secret SECRET     # once (Twitch viewer clips)
    python run.py live start gta6 --folder "C:/Users/you/Videos/live" --twitch yourchannel   # keeps running
    python run.py live next gta6          # (Claude) the next piece to clip, with its context
    python run.py live done gta6 <project> [--clips 2]                # (Claude) a piece is finished
    python run.py live status gta6
    python run.py live stop gta6

While a live session runs, every heavy ClipKaro step runs at low priority and edits with the processor's
encoder, so OBS keeps the graphics card's encoder for the stream (run.py does this by itself). The words
are written down on the graphics card only when it has enough free memory next to OBS; otherwise on the
processor (slower, never a dropped stream frame).
"""
import argparse
import json
import os
import re
import subprocess
import sys
import threading
import time
from datetime import datetime
from pathlib import Path

from .common import OUTPUT, ROOT, die, load_json, probe, save_json, settings, slugify

VIDEO_EXT = ('.mkv', '.mp4', '.mov', '.flv', '.ts')
IDLE_S = 120          # the newest file counts as finished when it hasn't grown for this long (the stream ended)
POLL_S = 10
HEARTBEAT_S = 90      # run.py treats a session as running while its heartbeat is younger than this
CONTEXT_LINES = 6     # lines from the end of the previous piece, shown to Claude as context


def live_dir(name):
    return OUTPUT / '_live' / slugify(name, 40)


def state_file(name):
    return live_dir(name) / 'live.json'


def load_state(name):
    return load_json(state_file(name), {}) or {}


def running_sessions():
    """Names of live sessions with a fresh heartbeat (used by run.py to lower the priority of heavy steps)."""
    base = OUTPUT / '_live'
    out = []
    if base.is_dir():
        for d in base.iterdir():
            hb = d / 'heartbeat'
            try:
                if time.time() - float(hb.read_text()) < HEARTBEAT_S:
                    out.append(d.name)
            except (OSError, ValueError):
                pass
    return out


# ---------- pieces ----------

STAMP = re.compile(r'(\d{4})-(\d{2})-(\d{2})[ _T](\d{2})-(\d{2})-(\d{2})')


def piece_start(path, duration=None):
    """Unix time the piece started: from OBS's file name ("2026-11-19 00-10-03.mkv"), else its
    modification time minus its length."""
    m = STAMP.search(Path(path).stem)
    if m:
        return datetime(*map(int, m.groups())).timestamp()
    st = Path(path).stat()
    return st.st_mtime - (duration or 0)


def finished_pieces(folder, since, sizes, now=None):
    """The finished recording pieces in `folder`, oldest first: every file but the newest; the newest too
    once it hasn't grown for IDLE_S seconds. `sizes` ({path: (size, first seen at that size)}) is kept
    between calls."""
    now = now or time.time()
    files = sorted((p for p in Path(folder).iterdir() if p.suffix.lower() in VIDEO_EXT and p.is_file()
                    and p.stat().st_mtime >= since), key=lambda p: (p.stat().st_mtime, p.name))
    done = files[:-1]
    if files:
        last = files[-1]
        size = last.stat().st_size
        old = sizes.get(str(last))
        if old and old[0] == size:
            if now - old[1] >= IDLE_S:
                done.append(last)
        else:
            sizes[str(last)] = (size, now)
    return done


def free_vram_mb():
    """Free graphics memory in MB (the first NVIDIA card), or None."""
    try:
        r = subprocess.run(['nvidia-smi', '--query-gpu=memory.free', '--format=csv,noheader,nounits'],
                           capture_output=True, text=True, timeout=10)
        return int(r.stdout.split()[0]) if r.returncode == 0 and r.stdout.strip() else None
    except (OSError, ValueError, IndexError, subprocess.SubprocessError):
        return None


def pick_device(cfg):
    """'cuda' when the graphics card has room for the speech model next to OBS, else 'cpu'."""
    need = int(cfg.get('live_vram_mb', 2800))
    free = free_vram_mb()
    return ('cuda' if free is not None and free >= need else 'cpu'), free


def low_priority():
    """Process options so a child process gets less of the processor than OBS."""
    if os.name == 'nt':
        return {'creationflags': 0x00004000}               # BELOW_NORMAL_PRIORITY_CLASS (children inherit it)
    return {'preexec_fn': lambda: os.nice(10)}


def run_step(args, log):
    """python run.py <args> at low priority, its output appended to the session log. -> exit code."""
    with open(log, 'a', encoding='utf-8') as f:
        f.write(f'\n$ run.py {" ".join(args)}\n')
        f.flush()
        r = subprocess.run([sys.executable, str(ROOT / 'run.py'), *args], cwd=ROOT, stdout=f, stderr=subprocess.STDOUT,
                           **low_priority())
    return r.returncode


def add_twitch_notes(name, piece):
    """Save the piece's Twitch notes (transcript/twitch.json) and write its transcript again with them."""
    cfg = settings()
    pdir = OUTPUT / piece['project']
    notes = []
    try:
        from .twitch import piece_notes
        notes = piece_notes(live_dir(name), piece['start'], piece['start'] + piece['duration'],
                            float(cfg.get('twitch_delay', 10)))
    except Exception as e:                 # never fatal: the clips come from the words alone then
        print(f'   (Twitch notes skipped: {type(e).__name__}: {e})', flush=True)
    save_json(pdir / 'transcript' / 'twitch.json', [list(n) for n in notes])
    try:
        from .fetch import render_transcript
        render_transcript(pdir, load_json(pdir / 'project.json', {}) or {},
                          load_json(pdir / 'transcript' / 'sentences.json') or [])
    except Exception as e:
        print(f'   (transcript not written again: {type(e).__name__}: {e})', flush=True)
    return notes


# ---------- the watcher ----------

def start(name, folder, twitch=None, from_start=False):
    cfg = settings()
    folder = Path(folder).expanduser()
    if not folder.is_dir():
        die(f'no such folder: {folder}  (the folder OBS records into: Settings > Output > Recording Path)')
    d = live_dir(name)
    d.mkdir(parents=True, exist_ok=True)
    st = load_state(name)
    since = 0 if from_start else st.get('since') or time.time() - 60
    st.update({'name': name, 'folder': str(folder), 'twitch': twitch, 'since': since,
               'started': st.get('started') or time.time()})
    st.setdefault('pieces', [])
    save_json(state_file(name), st)
    (d / 'stop').unlink(missing_ok=True)
    log = d / 'live.log'
    stop = threading.Event()
    threads = []
    if twitch:
        from . import twitch as tw
        threads.append(tw.ChatLogger(twitch, d / 'chat.jsonl', stop))
        keys = tw.load_keys()
        if keys:
            threads.append(tw.ClipPoller(twitch, keys, d / 'clips.jsonl', stop, since or time.time()))
        else:
            print('-> Twitch viewer clips: off (no keys yet: python run.py live keys --client-id ... '
                  '--client-secret ...). Chat is read anyway.', flush=True)
        for t in threads:
            t.start()
    print(f'-> live clipping "{name}": watching {folder}' + (f', Twitch chat of {twitch}' if twitch else ''),
          flush=True)
    print(f'   log: {log}\n   Claude: /loop 10m live clip {name}', flush=True)
    sizes = {}

    def beat():                    # "a live session runs": every 20 s, also while a piece is written down
        while not stop.is_set():
            (d / 'heartbeat').write_text(str(time.time()))
            stop.wait(20)
    threading.Thread(target=beat, daemon=True, name='live-heartbeat').start()
    try:
        while not (d / 'stop').exists():
            st = load_state(name)
            known = {p['file'] for p in st['pieces']}
            for f in finished_pieces(folder, since, sizes):
                if str(f) in known:
                    continue
                n = len(st['pieces']) + 1
                info = probe(f)
                piece = {'n': n, 'file': str(f), 'project': f'live-{slugify(name, 30)}-p{n:02d}',
                         'start': piece_start(f, info.get('duration')), 'duration': info.get('duration') or 0,
                         'status': 'writing down the words', 'found': time.time()}
                st['pieces'].append(piece)
                save_json(state_file(name), st)
                device, free = pick_device(cfg)
                print(f'-> piece {n}: {f.name} ({piece["duration"] / 60:.1f} min) -> {piece["project"]}, '
                      f'words on the {"graphics card" if device == "cuda" else "processor"}'
                      + (f' ({free} MB free)' if free is not None else ''), flush=True)
                code = run_step(['fetch', str(f), '--name', piece['project'], '--device', device], log)
                if code != 0 and device == 'cuda':          # the card ran out of memory after all: processor
                    print(f'   piece {n}: the graphics card failed, again on the processor', flush=True)
                    code = run_step(['fetch', str(f), '--name', piece['project'], '--device', 'cpu', '--retranscribe'],
                                    log)
                if code == 0:
                    notes = add_twitch_notes(name, piece) if twitch else []
                    piece['status'], piece['ready'] = 'ready', time.time()
                    piece['twitch_notes'] = len(notes)
                    print(f'   piece {n} ready for Claude' + (f' ({len(notes)} Twitch notes)' if twitch else ''),
                          flush=True)
                else:
                    piece['status'] = 'failed (see live.log)'
                    print(f'   piece {n} failed: see {log}', flush=True)
                st = load_state(name)
                st['pieces'] = [piece if p['n'] == n else p for p in st['pieces']]
                save_json(state_file(name), st)
                known.add(str(f))
            time.sleep(POLL_S)
    except KeyboardInterrupt:
        pass
    finally:
        stop.set()
        (d / 'heartbeat').unlink(missing_ok=True)
        print(f'-> live clipping "{name}" stopped', flush=True)


# ---------- what Claude asks ----------

def context_lines(project, n=CONTEXT_LINES):
    """The last n spoken lines of a piece's transcript."""
    tx = OUTPUT / project / 'transcript' / 'transcript.txt'
    try:
        lines = [ln for ln in tx.read_text(encoding='utf-8').splitlines() if ln.startswith('[')]
    except OSError:
        return []
    return lines[-n:]


def next_piece(name):
    st = load_state(name)
    if not st:
        die(f'no live session "{name}" (python run.py live start {name} --folder ...)')
    ready = [p for p in st.get('pieces', []) if p['status'] == 'ready']
    waiting = [p for p in st.get('pieces', []) if p['status'] == 'writing down the words']
    if not ready:
        print(f'NONE READY ({len(waiting)} being written down, {len(st.get("pieces", []))} pieces so far)')
        return None
    p = ready[0]
    prev = next((q for q in st['pieces'] if q['n'] == p['n'] - 1), None)
    print(f"NEXT: piece {p['n']}  project {p['project']}  ({p['duration'] / 60:.1f} min, recorded "
          f"{datetime.fromtimestamp(p['start']).strftime('%H:%M')})")
    print(f"transcript: output/{p['project']}/transcript/transcript.txt")
    if p.get('twitch_notes'):
        print(f"Twitch notes in it: {p['twitch_notes']} ([chat exploded ...] / [viewers clipped this])")
    if prev:
        print('just before this piece (context only, from the previous piece; not in this one):')
        for ln in context_lines(prev['project']):
            print('   ' + ln)
    clipped = [c for q in st['pieces'] for c in q.get('titles', [])]
    if clipped:
        print('already clipped this stream (don\'t repeat): ' + ' | '.join(clipped[-12:]))
    print(f"after posting:  python run.py live done {name} {p['project']} --clips N")
    return p


def mark_done(name, project, clips=0, titles=()):
    st = load_state(name)
    for p in st.get('pieces', []):
        if p['project'] == project:
            p['status'], p['clips'], p['done'] = 'done', clips, time.time()
            if not titles:
                picked = (load_json(OUTPUT / project / 'clips.json', {}) or {}).get('clips', [])
                titles = [c.get('title', '') for c in picked]
            p['titles'] = [t for t in titles if t]
            save_json(state_file(name), st)
            print(f"piece {p['n']} done: {clips} clip(s)")
            return
    die(f'{project} is not a piece of "{name}"')


def status(name):
    st = load_state(name)
    if not st:
        die(f'no live session "{name}"')
    on = name in running_sessions() or slugify(name, 40) in running_sessions()
    print(f"live \"{name}\": {'running' if on else 'not running'}, watching {st.get('folder')}"
          + (f", Twitch {st['twitch']}" if st.get('twitch') else ''))
    d = live_dir(name)
    if st.get('twitch'):
        from .twitch import read_jsonl
        print(f"   chat messages: {len(read_jsonl(d / 'chat.jsonl'))}, viewer clips: {len(read_jsonl(d / 'clips.jsonl'))}")
    for p in st.get('pieces', []):
        lag = ''
        if p.get('done') and p.get('found'):
            lag = f"  ({(p['done'] - p['found']) / 60:.0f} min from piece to posted)"
        print(f"   piece {p['n']:>2}  {p['status']:<24} {p.get('clips', '-')!s:>2} clip(s)  {p['project']}{lag}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest='cmd', required=True)
    s = sub.add_parser('start')
    s.add_argument('name')
    s.add_argument('--folder', default=None, help='the folder OBS records into (default: settings.json "live_folder")')
    s.add_argument('--twitch', default=None, help='your Twitch channel (default: settings.json "twitch_channel")')
    s.add_argument('--from-start', action='store_true', help='also take pieces already in the folder (tests)')
    for c in ('next', 'status', 'stop'):
        sub.add_parser(c).add_argument('name')
    d = sub.add_parser('done')
    d.add_argument('name')
    d.add_argument('project')
    d.add_argument('--clips', type=int, default=0)
    k = sub.add_parser('keys')
    k.add_argument('--client-id', required=True)
    k.add_argument('--client-secret', required=True)
    a = ap.parse_args()
    cfg = settings()
    if a.cmd == 'start':
        folder = a.folder or cfg.get('live_folder')
        if not folder:
            die('which folder does OBS record into? --folder "<path>" (or "live_folder" in settings.json)')
        start(a.name, folder, a.twitch or cfg.get('twitch_channel') or None, a.from_start)
    elif a.cmd == 'next':
        next_piece(a.name)
    elif a.cmd == 'done':
        mark_done(a.name, a.project, a.clips)
    elif a.cmd == 'status':
        status(a.name)
    elif a.cmd == 'stop':
        live_dir(a.name).mkdir(parents=True, exist_ok=True)
        (live_dir(a.name) / 'stop').write_text('stop')
        print(f'-> asked "{a.name}" to stop (within {POLL_S} s)')
    elif a.cmd == 'keys':
        from .twitch import save_keys
        f = save_keys(a.client_id, a.client_secret)
        print(f'-> Twitch keys saved in {f} (outside the ClipKaro folder; never committed)')


if __name__ == '__main__':
    main()
