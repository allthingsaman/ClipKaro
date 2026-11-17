"""Your Twitch audience as hints for live clipping (v2.6): the chat's big moments and the clips your
viewers make, next to the words Claude reads ("[chat exploded ~15 s: KEKW]", "[viewers clipped this x2]").

    python run.py live keys --client-id ID --client-secret SECRET   # once: your free Twitch developer app

- Chat is read without logging in (Twitch's anonymous read-only chat), so it needs no keys.
- Viewer clips need a free developer app (dev.twitch.tv/console): its Client ID and Client Secret are kept
  in your user folder (never in the ClipKaro folder, never committed), and only public data is read.

Times: the stream that viewers watch runs some seconds behind what you do (encoding and Twitch's own
delay), so their reactions come later than the moment. Chat and clip times are moved earlier by
"twitch_delay" (settings.json, 10 s) and every note says "~": they show where to look, never where to cut.
Nothing here is ever needed: without Twitch (or with a quiet chat) the clips come from the words alone.
"""
import json
import os
import random
import re
import socket
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

BIN = 5.0                 # chat messages are counted in 5-second bins
SPIKE_MIN = 4             # a spike needs at least this many messages in a bin
SPIKE_X = 3.0             # ... and this many times the usual rate (the median bin of the stream so far)
REACTIONS = ['KEKW', 'LUL', 'OMEGALUL', 'LMAO', 'LOL', 'XD', '😂', '🤣', '💀', 'POG', 'POGGERS', 'POGCHAMP',
             'W', 'L', 'GG', 'F', '?', '🔥', 'HAHAHA', 'HAHA', 'WTF', 'OMG', 'BRO', 'BHAI', 'NOOO']
CLIP_POLL = 60            # seconds between checks for new viewer clips


# ---------- keys (the developer app) ----------

def keys_file():
    base = Path(os.environ.get('APPDATA') or Path.home() / 'AppData' / 'Roaming') if os.name == 'nt' else \
        Path(os.environ.get('XDG_CONFIG_HOME') or Path.home() / '.config')
    return base / 'clipkaro' / 'twitch.json'


def save_keys(client_id, client_secret):
    f = keys_file()
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(json.dumps({'client_id': client_id.strip(), 'client_secret': client_secret.strip()}), encoding='utf-8')
    try:
        os.chmod(f, 0o600)
    except OSError:
        pass
    return f


def load_keys():
    try:
        k = json.loads(keys_file().read_text(encoding='utf-8'))
        return k if k.get('client_id') and k.get('client_secret') else None
    except (OSError, ValueError):
        return None


# ---------- chat (anonymous, read-only) ----------

class ChatLogger(threading.Thread):
    """Reads the channel's chat and appends {"t": unix time, "u": user, "m": message} lines to a file.
    Reconnects by itself; stops when `stop` is set."""

    def __init__(self, channel, out, stop):
        super().__init__(daemon=True, name='twitch-chat')
        self.channel, self.out, self.stop = channel.lower().lstrip('#'), Path(out), stop
        self.count = 0

    def run(self):
        wait = 2
        while not self.stop.is_set():
            try:
                self._session()
                wait = 2
            except OSError:
                pass
            self.stop.wait(wait)
            wait = min(60, wait * 2)

    def _session(self):
        s = socket.create_connection(('irc.chat.twitch.tv', 6667), timeout=30)
        try:
            s.sendall(f'NICK justinfan{random.randint(10000, 99999)}\r\nJOIN #{self.channel}\r\n'.encode())
            buf = b''
            with open(self.out, 'a', encoding='utf-8') as f:
                while not self.stop.is_set():
                    try:
                        data = s.recv(4096)
                    except socket.timeout:
                        s.sendall(b'PING :tmi.twitch.tv\r\n')
                        continue
                    if not data:
                        return
                    buf += data
                    *lines, buf = buf.split(b'\r\n')
                    for raw in lines:
                        line = raw.decode('utf-8', 'replace')
                        if line.startswith('PING'):
                            s.sendall(('PONG' + line[4:] + '\r\n').encode())
                            continue
                        m = parse_privmsg(line)
                        if m:
                            f.write(json.dumps({'t': round(time.time(), 2), 'u': m[0], 'm': m[1]},
                                               ensure_ascii=False) + '\n')
                            f.flush()
                            self.count += 1
        finally:
            s.close()


def parse_privmsg(line):
    """(user, message) of a chat line, else None. ':name!name@name.tmi.twitch.tv PRIVMSG #ch :hello'"""
    m = re.match(r'^(?:@\S+ )?:(\w+)!\S+ PRIVMSG #\w+ :(.*)$', line)
    return (m.group(1), m.group(2)) if m else None


# ---------- viewer clips (Helix API, an app token) ----------

def _get(url, headers):
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read().decode('utf-8'))


def app_token(keys):
    body = urllib.parse.urlencode({'client_id': keys['client_id'], 'client_secret': keys['client_secret'],
                                   'grant_type': 'client_credentials'}).encode()
    req = urllib.request.Request('https://id.twitch.tv/oauth2/token', data=body, method='POST')
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read().decode('utf-8'))['access_token']


class ClipPoller(threading.Thread):
    """Every minute, the clips viewers made of this channel since `since` (unix time), appended to a file as
    {"id", "created": unix time, "duration", "views", "title"}."""

    def __init__(self, channel, keys, out, stop, since):
        super().__init__(daemon=True, name='twitch-clips')
        self.channel, self.keys, self.out, self.stop, self.since = channel.lower().lstrip('#'), keys, Path(out), stop, since
        self.seen, self.problem = set(), None

    def run(self):
        token = uid = None
        while not self.stop.is_set():
            try:
                if not token:
                    token = app_token(self.keys)
                h = {'Client-Id': self.keys['client_id'], 'Authorization': f'Bearer {token}'}
                if not uid:
                    data = _get(f'https://api.twitch.tv/helix/users?login={self.channel}', h).get('data') or []
                    if not data:
                        self.problem = f'no Twitch channel called "{self.channel}"'
                        return
                    uid = data[0]['id']
                started = datetime.fromtimestamp(self.since - 120, timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
                data = _get(f'https://api.twitch.tv/helix/clips?broadcaster_id={uid}&started_at={started}&first=100',
                            h).get('data') or []
                new = [c for c in data if c['id'] not in self.seen]
                if new:
                    with open(self.out, 'a', encoding='utf-8') as f:
                        for c in new:
                            self.seen.add(c['id'])
                            created = datetime.strptime(c['created_at'], '%Y-%m-%dT%H:%M:%SZ').replace(
                                tzinfo=timezone.utc).timestamp()
                            f.write(json.dumps({'id': c['id'], 'created': created, 'duration': c.get('duration') or 30,
                                                'views': c.get('view_count', 0), 'title': c.get('title', '')},
                                               ensure_ascii=False) + '\n')
                self.problem = None
            except urllib.error.HTTPError as e:
                if e.code == 401:
                    token = None
                self.problem = f'Twitch answered {e.code}'
            except (OSError, ValueError, KeyError) as e:
                self.problem = f'{type(e).__name__}: {e}'
            self.stop.wait(CLIP_POLL)


# ---------- notes for one piece of the recording ----------

def read_jsonl(path):
    out = []
    try:
        with open(path, encoding='utf-8') as f:
            for line in f:
                try:
                    out.append(json.loads(line))
                except ValueError:
                    pass
    except OSError:
        pass
    return out


def reaction(messages):
    """The most used reaction word or emoji in these messages, or ''."""
    counts = {}
    for m in messages:
        toks = set(re.findall(r'\w+|[^\w\s]', m.upper()))
        for r in REACTIONS:
            if r in toks:
                counts[r] = counts.get(r, 0) + 1
    if not counts:
        return ''
    best = max(counts, key=counts.get)
    return best if counts[best] >= 2 else ''


def chat_spikes(chat, start, end, delay=10.0):
    """[(start, end, note)] in seconds of the piece [start, end) (unix times): stretches where the chat
    went much faster than usual. The usual rate is the median 5-second bin of the whole chat so far."""
    import statistics
    if not chat:
        return []
    t0 = min(c['t'] for c in chat)
    bins = {}
    for c in chat:
        bins.setdefault(int((c['t'] - t0) // BIN), []).append(c)
    span = int((max(c['t'] for c in chat) - t0) // BIN) + 1
    usual = statistics.median([len(bins.get(i, [])) for i in range(span)]) if span else 0
    need = max(SPIKE_MIN, SPIKE_X * max(usual, 0.5))
    hot = sorted(i for i, msgs in bins.items() if len(msgs) >= need)
    runs = []
    for i in hot:
        if runs and i - runs[-1][-1] <= 1:
            runs[-1].append(i)
        else:
            runs.append([i])
    out = []
    for r in runs:
        a = t0 + r[0] * BIN - delay - start
        b = t0 + (r[-1] + 1) * BIN - delay - start
        if b <= 0 or a >= end - start:
            continue
        msgs = [c['m'] for i in r for c in bins[i]]
        what = reaction(msgs)
        n = round(b - a)
        out.append((max(0.0, round(a, 2)), round(min(b, end - start), 2),
                    f'[chat exploded ~{n} s' + (f': {what}]' if what else ']')))
    return out


def clip_marks(clips, start, end, delay=10.0):
    """[(start, end, note)] in seconds of the piece: what viewers clipped. A Twitch clip holds the seconds
    before the viewer pressed the button, as they saw them (behind by `delay`)."""
    spans = []
    for c in clips:
        b = c['created'] - delay - start
        a = b - float(c.get('duration') or 30)
        if b > 0 and a < end - start:
            spans.append([max(0.0, a), min(end - start, b), 1])
    spans.sort()
    merged = []
    for s in spans:
        if merged and s[0] <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], s[1])
            merged[-1][2] += 1
        else:
            merged.append(s)
    return [(round(a, 2), round(b, 2), '[viewers clipped this' + (f' x{n}]' if n > 1 else ']'))
            for a, b, n in merged]


def piece_notes(live_dir, start, end, delay=10.0):
    """All Twitch notes for the piece recorded from `start` to `end` (unix times)."""
    live_dir = Path(live_dir)
    chat = read_jsonl(live_dir / 'chat.jsonl')
    clips = read_jsonl(live_dir / 'clips.jsonl')
    return chat_spikes(chat, start, end, delay) + clip_marks(clips, start, end, delay)


if __name__ == '__main__':                      # a quick look: python -m clipper.twitch <channel> (Ctrl+C stops)
    stop = threading.Event()
    log = ChatLogger(sys.argv[1], 'chat-test.jsonl', stop)
    log.start()
    try:
        while True:
            time.sleep(10)
            print(f'{log.count} chat messages so far')
    except KeyboardInterrupt:
        stop.set()
