"""ClipKaro's own checks: python run.py test

Fast (no video, no model, no internet). They protect v1.1's behaviour (the classic captions, the
zoom rhythm, cut points on whole words, Roman Hinglish, post.json) and the upgrades since, so a
change can't break them without anyone noticing.
"""
import json
import tempfile
import unittest
from pathlib import Path

from clipper import cut, fixword, kind, layout, more, plan, tidy
from clipper.fetch import unsure_stretches


def W(text, s, e, p=0.95, **kw):
    return dict(w=text, s=s, e=e, p=p, **kw)


def sentence(text, start, gap=0.08, dur=0.3, p=0.95):
    out, t = [], start
    for word in text.split():
        out.append(W(word, round(t, 3), round(t + dur, 3), p))
        t += dur + gap
    return out


def meta_for(words, duration=None, shots=None):
    duration = duration or round(words[-1]['e'] + 0.4, 3)
    return {'words': words, 'duration': duration, 'fps': 30,
            'shots': shots or [{'t0': 0.0, 't1': duration, 'mode': 'crop', 'focus': [540, 700]}],
            'splices': [], 'jumps': [], 'parts': [[0.0, duration]]}


V11 = {'look': 'classic', 'safe': False, 'hook': False, 'captions': True, 'zoom': True, 'sfx': 'none',
       'caption_y': 1270}


class V11Baseline(unittest.TestCase):
    """With the upgrades switched off, the edit is v1.1's."""

    def setUp(self):
        self.meta = meta_for(sentence('this is how the market really works for most people today. '
                                      'and nobody tells you the real reason behind it.', 0.0))

    def test_classic_captions(self):
        p = plan.build(self.meta, {'accent': '#FFD60A', 'text': '#FFFFFF', 'outline': '#000000'}, V11)
        st = p['caption_style']
        self.assertEqual((st['font'], st['size'], st['outline'], st['y']), ('Montserrat ExtraBold', 96, 8, 1270))
        self.assertTrue(st['uppercase'] and st['pop'])
        self.assertIsNone(p['hook'])
        for g in p['captions']:
            self.assertLessEqual(len(g['words']), 3)
            self.assertNotIn('y', g)                      # one fixed line, as in v1.1
            line = ' '.join(w['text'] for w in g['words'])
            self.assertLessEqual(plan.caption_width(line, st) * g.get('scale', 1), plan.MAX_CAPTION_W + 1)
            self.assertEqual(line, line.upper())

    def test_owner_defaults(self):
        # the owner's choice (2026-11-14): pauses cut, captions off faces and app buttons, emojis on;
        # no title on screen unless the message says "hook title"; background music on hold
        from clipper.common import DEFAULT_SETTINGS
        self.assertTrue(DEFAULT_SETTINGS['jump_cuts'] and DEFAULT_SETTINGS['safe_zones'] and DEFAULT_SETTINGS['emoji'])
        self.assertFalse(DEFAULT_SETTINGS['hook_title'])
        self.assertFalse(DEFAULT_SETTINGS['music'])
        self.assertEqual(DEFAULT_SETTINGS['caption_look'], 'classic')
        brand = {'accent': '#FFD60A', 'text': '#FFFFFF', 'outline': '#000000'}
        p = plan.build(self.meta, brand, {k: v for k, v in V11.items() if k != 'hook'})
        self.assertIsNone(p['hook'])
        p = plan.build(self.meta, brand, dict(V11, hook=True, hook_text='Nobody tells you this'))
        self.assertIsNotNone(p['hook'])

    def test_plain_transcript_way_back(self):
        # "hints": false gives Claude v1.1's transcript lines, without any notes
        from clipper import common, hints
        saved = common.settings
        common.settings = lambda: dict(common.DEFAULT_SETTINGS, hints=False)
        try:
            self.assertEqual(hints.notes(Path(tempfile.gettempdir()) / 'no-such-project'), {})
        finally:
            common.settings = saved
        self.assertEqual(hints.line_text({'s': 3.5, 'e': 6.25, 'text': 'hello there'}, {}), '[3.50-6.25] hello there')

    def test_zoom_rhythm(self):
        keys, cam, transitions, beats = plan.build_camera(self.meta)
        self.assertEqual(transitions[0]['kind'], 'open')
        self.assertAlmostEqual(cam[0][0], plan.OPEN_SCALE, places=2)
        starts = [t['t'] for t in transitions]
        self.assertTrue(all(b - a >= 0.5 for a, b in zip(starts, starts[1:])))

    def test_cut_snaps_to_whole_words(self):
        words = self.meta['words']
        s, e, i0, i1 = cut.snap_range(words[2]['s'] + 0.1, words[8]['e'] - 0.1, words)
        self.assertLessEqual(s, words[i0]['s'])
        self.assertGreaterEqual(e, words[i1]['e'])
        self.assertGreater(s, words[i0 - 1]['e'])


class Captions(unittest.TestCase):
    def test_no_ellipsis_shown(self):
        self.assertEqual(plan.display('like...', True), 'LIKE')
        self.assertEqual(plan.display('हाग…', False), 'हाग')
        self.assertEqual(plan.display('...so', True), 'SO')
        self.assertEqual(plan.display('…', True), '')

    def test_safe_width(self):
        words = sentence('MISUNDERSTANDINGS ABOUT INTERNATIONALISATION OVERWHELMINGLY', 0.0, dur=0.6)
        st = {'font': plan.LATIN_FONT[0], 'font_file': plan.LATIN_FONT[1], 'size': 96, 'outline': 8, 'spacing': 1}
        for g in plan.caption_groups(meta_for(words), style=st, max_w=layout.SAFE_W):
            line = ' '.join(w['text'] for w in g['words'])
            self.assertLessEqual(plan.caption_width(line, st) * g.get('scale', 1), layout.SAFE_W + 1)

    def test_hook_lines_fit(self):
        st = {'font': plan.LATIN_FONT[0], 'font_file': plan.LATIN_FONT[1], 'size': 76, 'spacing': 1, 'outline': 18}
        for text in ['PAKISTAN KA PM BANOGE?', "WHY HE KEPT A BRICK FROM BIN LADEN'S HOUSE", 'MISUNDERSTANDINGS']:
            lines, size = plan.hook_lines(text, st)
            self.assertLessEqual(len(lines), 3)
            for line in lines:
                self.assertLessEqual(plan.caption_width(line, dict(st, size=size)), layout.SAFE_W)

    def test_emoji_spot(self):
        st = {'font': plan.LATIN_FONT[0], 'font_file': plan.LATIN_FONT[1], 'size': 96, 'outline': 8, 'spacing': 1}
        words = sentence('the police are here now run', 0.0)
        caps = [{'start': 0.0, 'end': 0.7, 'words': [{'text': 'RUN'}]},
                {'start': 0.76, 'end': 2.2, 'words': [{'text': 'POLICE'}]}]
        for mode, where in (('crop', 'above'), ('facecam', 'beside')):
            shots = [{'t0': 0.0, 't1': 3.0, 'mode': mode}]
            got, missing = plan.emoji_marks([['police', '🚨']], words, caps, shots, {}, 1160, 3.0, st)
            self.assertEqual(len(got), 1, missing)
            e = got[0]
            self.assertEqual('above' if e['y'] < 1160 - 100 else 'beside', where)
            if where == 'beside':     # clear of the wider line that follows while it shows
                wide = plan.caption_width('POLICE', st)
                self.assertGreaterEqual(abs(e['x'] - 540) - plan.EMOJI_SIZE / 2, wide / 2)

    def test_caption_part_at_a_split_keeps_the_seam(self):
        # Khan Sir clip 10: the split starts on frame 374 (14.96 s at 25 fps) but its t0 says 14.98; the part
        # of a caption from that frame on belongs on the seam, not on the lower person's head
        shots = [{'t0': 0.0, 't1': 14.98, 'f0': 0, 'mode': 'crop'},
                 {'t0': 14.98, 't1': 20.0, 'f0': 374, 'mode': 'split'}]
        faces = {0: [(300, 300, 780, 900)], 1: [(300, 300, 780, 700), (300, 1200, 780, 1500)]}
        caps = [{'start': 14.55, 'end': 14.96, 'words': []},
                {'start': 14.96, 'end': 15.37, 'cont': True, 'y': 960, 'words': []}]
        plan.safe_caption_y(caps, shots, faces, 1270, False, None, 25)
        self.assertEqual(caps[1]['y'], 960)
        self.assertNotEqual(caps[0].get('y', 1270), 960)

    def test_hand_is_not_a_face(self):
        face, hand = (240, 139, 919, 1082), (154, 799, 727, 1510)       # a fist under the chin (PS5 clip 1)
        self.assertEqual(layout.real_faces([hand, face]), [face])
        top, bottom = (200, 100, 800, 700), (200, 1000, 800, 1600)      # two people in a split screen
        self.assertEqual(sorted(layout.real_faces([top, bottom])), [top, bottom])

    def test_text_avoids_faces(self):
        face = [(300, 400, 780, 1000)]
        y = layout.place(400, 135, face, layout.TITLE_LINES)
        self.assertGreater(abs(y - 700), 135 / 2 + 300)    # not over the face
        self.assertEqual(layout.zoomed(face, None, 30, 0, 1), face)
        grown = layout.zoomed(face, [[1.2, 540, 700]] * 40, 30, 0, 1)[0]
        self.assertLess(grown[1], 400)
        self.assertGreater(grown[3], 1000)


class Transcripts(unittest.TestCase):
    def test_tidy(self):
        real = sentence("let's go let's go let's go", 0.0, p=0.8)
        junk = sentence('कर दो कर दो कर दो', 5.0, p=0.6)
        noise = [W('झाल', 9.0, 9.2, 0.7)]
        new, why = tidy.tidy_words(real + junk + noise)
        self.assertFalse(any(w.get('unsure') for w in new[:len(real)]))
        self.assertTrue(all(w.get('unsure') for w in new[len(real):]))
        laugh, why = tidy.tidy_words(sentence('ha ha', 20.0) + sentence('that was funny', 21.0))
        self.assertTrue(laugh[0].get('unsure') and laugh[1].get('unsure'))
        self.assertFalse(laugh[2].get('unsure'))

    def test_unsure_stretch_not_hidden_by_clear_words(self):
        # a shaky game line right before clear words (the case the first version missed)
        shaky = [W(f'x{k}', 10 + 0.4 * k, 10.3 + 0.4 * k, p) for k, p in
                 enumerate([0.47, 0.24, 0.41, 0.23, 0.74, 0.29, 0.87, 0.41, 0.9, 0.66, 0.2, 0.15, 0.45, 0.46])]
        clear = sentence('naam se bula raha hai bhai ye to', shaky[-1]['e'] + 0.1, p=0.9)
        found = unsure_stretches(shaky + clear)
        self.assertTrue(found)
        i0, i1 = found[0]
        self.assertLessEqual(i0, 1)
        self.assertGreaterEqual(i1, len(shaky) - 3)
        self.assertLess(i1, len(shaky) + 2)

    def test_fixword(self):
        words = sentence('driving like a cycle path michael', 0.0)
        words[-1]['w'] = 'michael?'
        hits, n = fixword.find_all(words, 'cycle path')
        self.assertEqual((hits, n), ([3], 2))
        new, k = fixword.replace_at(words, 3, 2, 'psychopath')
        self.assertEqual([w['w'] for w in new], ['driving', 'like', 'a', 'psychopath', 'michael?'])
        self.assertEqual((new[3]['s'], new[3]['e']), (words[3]['s'], words[4]['e']))
        new, _ = fixword.replace_at(words, 5, 1, 'Michael')
        self.assertEqual(new[-1]['w'], 'Michael?')         # the punctuation stays


class StretchedWords(unittest.TestCase):
    """One word stretched over several that were skipped is heard again (roadmap item 9)."""
    def setUp(self):
        from clipper import fetch
        self.fetch = fetch
        # "ki ye America ki chaal hai" was skipped: "बात" lasts 2.6 s
        self.words = [W('ये', 0.0, 0.2), W('तो', 0.25, 0.4), W('सबको', 0.45, 0.8), W('पता', 0.85, 1.1),
                      W('बात', 1.15, 3.75), W('है', 3.8, 4.0), W('कि', 4.05, 4.2), W('अब', 4.25, 4.5)]
        self.saved = (fetch.stretched_words, fetch._decode)
        fetch.stretched_words = lambda audio, words: [i for i, w in enumerate(words) if w['e'] - w['s'] > 2]

    def tearDown(self):
        self.fetch.stretched_words, self.fetch._decode = self.saved

    def heard(self, text):
        ws = text.split()
        step = (3.75 - 0.0) / len(ws)
        self.fetch._decode = lambda *a, **k: ([W(w, round(i * step, 2), round((i + 1) * step - 0.05, 2))
                                              for i, w in enumerate(ws)], 0.8)

    def test_skipped_words_come_back(self):
        self.heard('तो सबको पता है कि ये America की चाल है बात')
        new, changes = self.fetch.repair_stretched(None, None, [dict(w) for w in self.words], 'hi', 5)
        self.assertEqual(len(changes), 1)
        self.assertIn('America', [w['w'] for w in new])
        self.assertLess(max(w['e'] - w['s'] for w in new), 2.0)

    def test_a_guess_never_replaces_real_words(self):
        self.heard('कुछ और ही बातें यहां सुनाई दे रहीं')             # none of the well-heard words again
        new, changes = self.fetch.repair_stretched(None, None, [dict(w) for w in self.words], 'hi', 5)
        self.assertEqual(changes, [])
        self.assertEqual([w['w'] for w in new], [w['w'] for w in self.words])

    def test_hidden_or_fixed_words_are_never_touched(self):
        self.heard('तो सबको पता है कि ये America की चाल है बात')
        _, changes = self.fetch.repair_stretched(None, None, [dict(w) for w in self.words], 'hi', 5, protect={3})
        self.assertEqual(changes, [])

    def test_fillers_alone_are_not_a_repair(self):
        self.heard('तो सबको um um पता पता बात')
        _, changes = self.fetch.repair_stretched(None, None, [dict(w) for w in self.words], 'hi', 5)
        self.assertEqual(changes, [])


class Hints(unittest.TestCase):
    """Sound and picture hints next to the words (roadmap items 12 and 13)."""
    def test_main_voice_and_other_voices(self):
        import numpy as np
        from clipper import voices
        rng = np.random.default_rng(0)
        streamer, game = rng.normal(size=192), rng.normal(size=192)
        prints, lines = [], []
        for i in range(60):
            base = streamer if i % 3 else game                  # 40 streamer lines, 20 game lines
            p = base + 0.3 * rng.normal(size=192)
            prints.append(p / np.linalg.norm(p))
            lines.append({'s': i * 3.0, 'e': i * 3.0 + 2.5, 'i0': 0, 'i1': 0, 'text': 'x'})
        found, labels = voices.find_voices(prints)
        self.assertGreaterEqual(len(found), 2)
        main = max(set(labels), key=labels.count)
        self.assertEqual({i for i in range(60) if labels[i] == main}, {i for i in range(60) if i % 3})
        saved = voices.prints_for
        voices.prints_for = lambda a, w, l: prints
        try:
            v = voices.analyse(None, [], lines)
        finally:
            voices.prints_for = saved
        self.assertEqual(voices.other_lines(v), {i for i in range(60) if i % 3 == 0})

    def test_raised_voice_needs_higher_and_louder(self):
        from clipper import hints
        lines = [{'s': i * 4.0, 'e': i * 4.0 + 3.0} for i in range(20)]
        levels = [(0.0, -20.0)] * 20
        levels[5] = (5.0, -12.0)            # +5 semitones, +8 dB: raised
        levels[9] = (9.0, -9.0)             # +9, +11: shouting
        levels[12] = (6.0, -20.0)           # only higher (a question): nothing
        levels[15] = (25.0, -10.0)          # +25 semitones: a pitch-tracker slip, nothing
        got = hints.raised_lines(levels, lines, None, lambda a, b: False)
        self.assertEqual([(r[0], r[2]) for r in got], [(20.0, 'voice raised'), (36.0, 'shouting')])

    def test_big_action_is_rare_and_long_enough(self):
        import numpy as np
        from clipper import motion
        track = np.ones(4 * 600, np.float32)
        track[400:420] = 10.0               # 5 s of big motion
        track[1000:1003] = 10.0             # under a second: not a moment
        got = motion.action_spans(track)
        self.assertEqual(len(got), 1)
        self.assertAlmostEqual(got[0][0], 100.0, delta=1.0)

    def test_action_without_talking_gets_its_own_line(self):
        from clipper import hints
        spans = [(10.0, 14.0), (20.0, 24.0)]
        self.assertEqual(hints.host_line((11.0, 13.0, 'x'), spans), 0)          # said over it
        self.assertEqual(hints.host_line((9.8, 12.3, 'x'), spans), 0)           # starts just before: most is on the line
        self.assertIsNone(hints.host_line((15.0, 19.0, 'x'), spans))            # nobody talks then
        with tempfile.TemporaryDirectory() as d:
            pdir = Path(d)
            (pdir / 'transcript').mkdir()
            lines = [{'s': 10.0, 'e': 14.0, 'i0': 0, 'i1': 0, 'text': 'bhai dekho'},
                     {'s': 20.0, 'e': 24.0, 'i0': 1, 'i1': 1, 'text': 'arre arre'}]
            (pdir / 'transcript' / 'motion.json').write_text(json.dumps({'v': 1, 'action': [[15.0, 18.0, 1.4]]}))
            (pdir / 'transcript' / 'cues.json').write_text(json.dumps({'v': 1, 'bursts': [[16.5, 17.5, 'explosion', 0.8]]}))
            silent = hints.silent_notes(pdir, {}, lines)
            self.assertEqual(silent, [{'s': 15.0, 'e': 18.0, 'note': '(no talking) [big action on screen ~3 s] [explosion]'}])
            shown = [hints.line_text(ln) for ln in hints.with_silent(lines, silent)]
            self.assertEqual(shown[1], '[15.00-18.00] (no talking) [big action on screen ~3 s] [explosion]')
            self.assertEqual(hints.strip_hints(shown[1].split('] ', 1)[1]).split(), [])   # nothing to quote

    def test_notes_in_a_line_and_never_in_a_quote(self):
        from clipper import hints
        ln = {'s': 12.4, 'e': 15.1, 'text': 'You call it whatever you want'}
        nt = {12.4: ('(other voice)', ['[voice raised]', '[explosion]'])}
        text = hints.line_text(ln, nt)
        self.assertEqual(text, '[12.40-15.10] (other voice) You call it whatever you want [voice raised] [explosion]')
        self.assertEqual(hints.strip_hints(text.split('] ', 1)[1]).split(), 'You call it whatever you want'.split())
        self.assertEqual(hints.line_text({'s': 1.0, 'e': 2.0, 'text': 'plain'}), '[1.00-2.00] plain')

    def test_microphone_track_chosen_only_when_clearly_alone(self):
        from clipper import fetch
        saved = (fetch.audio_tracks, fetch._track_sample, fetch.track_quiet_gap)
        try:
            fetch.audio_tracks = lambda p: [(0, ''), (1, '')]
            fetch._track_sample = lambda p, k, d: k
            fetch.track_quiet_gap = lambda k: {0: (0.7, 7.6), 1: (0.7, 26.5)}[k]
            self.assertEqual(fetch.mic_track('x', 100), 1)
            fetch.track_quiet_gap = lambda k: {0: (0.7, 7.6), 1: (0.7, 9.0)}[k]     # not clearly quieter
            self.assertIsNone(fetch.mic_track('x', 100))
            fetch.audio_tracks = lambda p: [(0, '')]
            self.assertIsNone(fetch.mic_track('x', 100))
        finally:
            fetch.audio_tracks, fetch._track_sample, fetch.track_quiet_gap = saved


class Relisten(unittest.TestCase):
    def test_hidden_words_stay_hidden(self):
        from clipper.relisten import keep_hidden
        before = [W('ye', 1.0, 1.2), dict(W('आंट्टी', 1.3, 1.6), unsure=True), W('chalo', 1.7, 2.0)]
        new = [W('ye', 1.0, 1.2), W('आंट्टी', 1.3, 1.6), W('You', 2.1, 2.3), W('chalo', 1.7, 2.0)]
        out = keep_hidden(before, new)
        self.assertEqual([w['w'] for w in out if not w.get('unsure')], ['ye', 'You', 'chalo'])


class GameVoiceCaptions(unittest.TestCase):
    """Gameplay: no captions for game characters, the streamer's words keep theirs (owner, Nov 2026)."""
    def project(self, d, kind=True, lang='hinglish'):
        pdir = Path(d)
        (pdir / 'transcript').mkdir()
        words = [W('आप', 0.0, 0.3), W('माइकल', 0.4, 0.8), W('को', 0.9, 1.0), W('बचा', 1.1, 1.4), W('लाएं।', 1.5, 2.0),
                 W('That', 3.0, 3.3), W("doesn't", 3.4, 3.7), W('sound', 3.8, 4.1), W('good.', 4.2, 4.6),
                 W('Stay', 5.0, 5.3), W('with', 5.4, 5.6), W('me.', 5.7, 5.9),
                 W('यार', 7.0, 7.3), W('but', 7.4, 7.6), W('he', 7.7, 7.8), W('broke', 7.9, 8.2), W('it.', 8.3, 8.6)]
        lines = [{'s': 0.0, 'e': 2.0, 'i0': 0, 'i1': 4, 'text': ''}, {'s': 3.0, 'e': 4.6, 'i0': 5, 'i1': 8, 'text': ''},
                 {'s': 5.0, 'e': 5.9, 'i0': 9, 'i1': 11, 'text': ''}, {'s': 7.0, 'e': 8.6, 'i0': 12, 'i1': 16, 'text': ''}]
        voices_ = {'v': 1, 'main': 0, 'voices': {}, 'lines': [[0.0, 2.0, 0, 0.8], [3.0, 4.6, None, 0.1],
                                                              [5.0, 5.9, None, None], [7.0, 8.6, None, 0.2]]}
        for name, data in (('words.json', words), ('sentences.json', lines), ('voices.json', voices_)):
            (pdir / 'transcript' / name).write_text(json.dumps(data, ensure_ascii=False), encoding='utf-8')
        project = {'language': lang, 'video_kind': {'gaming': kind, 'facecam': kind}}
        return pdir, project, words

    def test_game_lines_lose_captions_streamer_keeps_his(self):
        from clipper import voices
        with tempfile.TemporaryDirectory() as d:
            pdir, project, words = self.project(d)
            game = voices.game_words(pdir, project, words)
            self.assertEqual({words[k]['w'] for k in game},
                             {'That', "doesn't", 'sound', 'good.', 'Stay', 'with', 'me.', 'but', 'he', 'broke', 'it.'})
            self.assertNotIn(12, game)                                    # "यार": the streamer, in a mixed line
            self.assertFalse(any(k in game for k in range(5)))            # the streamer's own line

    def test_only_gameplay_with_a_hindi_streamer(self):
        from clipper import voices
        with tempfile.TemporaryDirectory() as d:
            pdir, project, words = self.project(d, kind=False)
            self.assertEqual(voices.game_words(pdir, project, words), set())
        with tempfile.TemporaryDirectory() as d:
            pdir, project, words = self.project(d, lang='en')
            self.assertEqual(voices.game_words(pdir, project, words), set())

    class FakeVocab:
        """A speech model's word pieces: these English words are one piece each, anything else three."""
        ENGLISH = set('hands up this is a stick i think that called stream rate map stay with me you know him so '
                      'good sound broke it he but'.split())

        def encode(self, text, add_special_tokens=False):
            from types import SimpleNamespace
            return SimpleNamespace(ids=[1] if text.strip() in self.ENGLISH else [1, 2, 3])

    def test_friends_hinglish_lines_are_not_english(self):
        # v2.7: on a 3-friends GTA stream these lost their captions (less common Hindi words looked English)
        from clipper import voices
        tok = self.FakeVocab()
        for line in ('Kisko khaoon?', 'Main kama loon', 'Vaah, vaah.', 'Stream par stream par rate bata',
                     'Mumbai map?', 'chale gae vaapas.'):
            self.assertFalse(voices.mostly_english(line.split(), tok), line)
        for line in ('Hands up, this is a stick up', "I think that's called stalking Mandy.", 'Stay with me.',
                     'You know him so.'):
            self.assertTrue(voices.mostly_english(line.split(), tok), line)     # game lines stay hidden

    def test_friend_unlike_the_streamer_keeps_captions(self):
        from unittest import mock
        from clipper import voices
        with tempfile.TemporaryDirectory() as d:
            pdir, project, words = self.project(d)
            words[5:9] = [W('Kisko', 3.0, 3.3), W('khaoon', 3.4, 3.7), W('bata', 3.8, 4.1), W('yaar.', 4.2, 4.6)]
            (pdir / 'transcript' / 'words.json').write_text(json.dumps(words, ensure_ascii=False), encoding='utf-8')
            with mock.patch.object(voices, 'english_tokenizer', return_value=self.FakeVocab()):
                game = voices.game_words(pdir, project, words)
            self.assertFalse(any(k in game for k in range(5, 9)))               # the friend's line keeps its captions
            self.assertTrue({9, 10, 11} <= game)                                # "Stay with me." is the game's

    def test_captions_skip_game_words(self):
        groups = plan.caption_groups(meta_for([W('Franklin', 0.0, 0.4), dict(W('Stay', 0.5, 0.8), game=True),
                                               W('sorry', 0.9, 1.2)]))
        shown = ' '.join(w['text'] for g in groups for w in g['words']).upper().split()
        self.assertEqual(shown, ['FRANKLIN', 'SORRY'])


class CaptionCheck(unittest.TestCase):
    def test_lines_as_viewers_read_them(self):
        from clipper import captions
        words = [W('फ्रैंक्लिन', 10.0, 10.4), W('को', 10.5, 10.6), W('सारी।', 10.7, 11.0),
                 dict(W('झाल', 11.2, 11.5), unsure=True), W('Stay', 12.0, 12.3), W('भाई', 13.0, 13.3)]
        lines = [{'s': 10.0, 'e': 11.5, 'i0': 0, 'i1': 3}, {'s': 12.0, 'e': 12.3, 'i0': 4, 'i1': 4},
                 {'s': 13.0, 'e': 13.3, 'i0': 5, 'i1': 5}]
        table = {'फ्रैंक्लिन': 'Franklin', 'को': 'ko', 'सारी': 'saari', 'भाई': 'bhai'}
        rows = captions.clip_lines(None, {}, {'ranges': [[9.0, 12.9]]}, words, lines, table, {4}, True)
        self.assertEqual(rows, [(10.0, 'Franklin ko saari.', 'फ्रैंक्लिन को सारी।'),   # no made-up word
                                (12.0, captions.GAME_MARK + 'Stay', 'Stay')])          # v2.7: hidden, but listed
        # v2.7: a friend speaking English, brought back by hand
        rows = captions.clip_lines(None, {}, {'ranges': [[9.0, 12.9]], 'show_captions': [[11.9, 12.5]]},
                                   words, lines, table, {4}, True)
        self.assertEqual(rows[1], (12.0, 'Stay', 'Stay'))
        rows = captions.clip_lines(None, {}, {'ranges': [[9.0, 13.5]], 'hide_captions': [[12.9, 13.4]]},
                                   words, lines, table, set(), True)
        self.assertEqual(rows[-1], (13.0, captions.GAME_MARK + 'भाई', 'भाई'))      # a game line the rule let through


class CaptionCheckRules(unittest.TestCase):
    def test_the_check_names_its_rules(self):
        from clipper import captions
        for must in ('sorry', 'names', 'digits', '2013', 'एक दिन', 'not sure'):
            self.assertIn(must, captions.RULES)


class HinglishModel(unittest.TestCase):
    """The Hinglish speech model for Hindi / Hinglish videos on an NVIDIA card (roadmap 9b)."""
    def pick(self, lang, device, **cfg):
        from clipper import common, fetch
        saved = fetch.settings
        fetch.settings = lambda: dict(common.DEFAULT_SETTINGS, **cfg)
        try:
            return fetch.pick_model('auto', lang, device)
        finally:
            fetch.settings = saved

    def test_which_model(self):
        from clipper.fetch import HINGLISH_MODEL
        self.assertEqual(self.pick('hinglish', 'cuda'), HINGLISH_MODEL)
        self.assertEqual(self.pick('hi', 'cuda'), HINGLISH_MODEL)
        self.assertEqual(self.pick('hinglish', 'cpu'), 'large-v3-turbo')         # the big model is slow there
        self.assertEqual(self.pick('en', 'cuda'), 'large-v3-turbo')              # English stays as it was
        self.assertEqual(self.pick('en', 'cpu'), 'small.en')
        self.assertEqual(self.pick('hinglish', 'cuda', hinglish_captions='devanagari'), 'large-v3-turbo')
        self.assertEqual(self.pick('hinglish', 'cuda', hinglish_model='large-v3-turbo'), 'large-v3-turbo')  # way back

    def test_silence_word_and_spelling(self):
        from clipper import fetch, romanize
        self.assertTrue(fetch.is_nan('nan') and fetch.is_nan(' Nan.') and not fetch.is_nan('naan'))
        self.assertTrue(fetch.writes_roman(fetch.HINGLISH_MODEL) and not fetch.writes_roman('large-v3-turbo'))
        table = {k: v for k, v in romanize.ROMAN_RESPELL.items() if v != k}
        out, missing = romanize.apply([W('Nahin', 0, 0.3), W('vahaan', 0.4, 0.7), W('the', 0.8, 1.0),
                                       W('VFX', 1.1, 1.4)], table)
        self.assertEqual([w['w'] for w in out], ['Nahi', 'wahan', 'the', 'VFX'])
        self.assertEqual(missing, [])


class SpeechTest(unittest.TestCase):
    def test_every_right_spelling_counts(self):
        from clipper import asrbench
        ref = asrbench.lattice_keys([['इम्प्रूव', 'improve'], ['होता', 'hota'], ['है', 'hai']])
        self.assertEqual(asrbench.lattice_wer(ref, asrbench.keys('improve hota hai')), 0.0)
        self.assertEqual(asrbench.lattice_wer(ref, asrbench.keys('इम्प्रूव होता है')), 0.0)
        self.assertAlmostEqual(asrbench.lattice_wer(ref, asrbench.keys('improve hai')), 1 / 3)


class JumpCuts(unittest.TestCase):
    def setUp(self):
        self.words = sentence('so this is the first point', 0.0) + sentence('and here is the second one', 4.0) \
            + [W('um', 7.0, 7.2)] + sentence('and the third', 7.6)

    def test_pauses_and_fillers_cut(self):
        pieces = cut.jump_pieces(0.0, self.words[-1]['e'], self.words, lambda a, b: True)
        self.assertEqual(len(pieces), 3)
        kept = [w['w'] for w in self.words for a, b in pieces if a <= w['s'] and w['e'] <= b]
        self.assertNotIn('um', kept)
        self.assertEqual(len(kept), len(self.words) - 1)

    def test_never_across_a_laugh(self):
        pieces = cut.jump_pieces(0.0, self.words[-1]['e'], self.words, lambda a, b: not (a < 3.5 and b > 2.5))
        self.assertEqual(len(pieces), 2)

    def test_voice_track_made_again_from_the_video(self):
        # a project tidied after posting keeps only video.mp4: the director must still hear who talks
        import shutil
        import subprocess
        if not shutil.which('ffmpeg'):
            self.skipTest('no ffmpeg')
        with tempfile.TemporaryDirectory() as d:
            pdir = Path(d)
            (pdir / 'source').mkdir()
            video = pdir / 'source' / 'video.mp4'
            subprocess.run(['ffmpeg', '-v', 'error', '-f', 'lavfi', '-i', 'color=black:s=64x36:d=1', '-f', 'lavfi',
                            '-i', 'sine=f=440:d=1:sample_rate=44100', '-shortest', '-ac', '2', str(video)], check=True)
            wav = cut.audio16k(pdir, video)
            self.assertTrue(wav.exists())
            import soundfile as sf
            info = sf.info(str(wav))
            self.assertEqual((info.samplerate, info.channels), (16000, 1))

    def test_loud_clipped_sound_stays_under_the_peak_limit(self):
        # harsh, clipped sound (a phone mic): the AAC encoder adds peaks; the edit measures and limits again
        import shutil
        import subprocess
        if not shutil.which('ffmpeg'):
            self.skipTest('no ffmpeg')
        from clipper import edit
        with tempfile.TemporaryDirectory() as d:
            src, out = Path(d) / 'clip.wav', Path(d) / 'mix.m4a'
            subprocess.run(['ffmpeg', '-v', 'error', '-f', 'lavfi', '-i',
                            'aevalsrc=clip(4*sin(2*PI*180*t)*(0.6+0.4*sin(2*PI*3*t))\\,-1\\,1):s=48000:d=4',
                            str(src)], check=True)
            edit.encode_audio(src, [], out, 4.0)
            self.assertLessEqual(edit.true_peak(out), edit.MAX_PEAK_DB + 0.05)
            self.assertFalse(out.with_suffix('.wav').exists())

    def test_loud_first_syllable_fades_in_and_timing_kept(self):
        # v2.7: a loud sound in a clip's first milliseconds made the AAC encoder overshoot whatever the limiter
        # did (clip 149 of a GTA stream: -0.7 dB at 12 ms, with the limit tried down to -4 dB); the mix now fades
        # in over START_FADE (30 ms, not heard). Nothing else moves: same length, no shift in time, with or
        # without sound effects mixed in, and the encoded peak stays under the apps' limit
        import shutil
        import subprocess
        import numpy as np
        if not shutil.which('ffmpeg'):
            self.skipTest('no ffmpeg')
        from clipper import edit
        with tempfile.TemporaryDirectory() as d:
            src, cue, out = Path(d) / 'clip.wav', Path(d) / 'cue.wav', Path(d) / 'mix.wav'
            # loud from the very first sample; a short click at exactly 2.0 s to measure the timing by
            subprocess.run(['ffmpeg', '-v', 'error', '-f', 'lavfi', '-i',
                            "aevalsrc='0.9*sin(2*PI*300*t)*lt(t\\,0.3)+0.02*sin(2*PI*200*t)+0.9*between(t\\,2\\,2.002)'"
                            ':s=48000:d=3', '-ac', '2', str(src)], check=True)
            subprocess.run(['ffmpeg', '-v', 'error', '-f', 'lavfi', '-i', 'sine=f=900:d=0.5:sample_rate=44100',
                            str(cue)], check=True)
            cues = [{'file': 'cue.wav', 'path': str(cue), 'offset': 0.0, 'length': 0.5, 'at': 0.0, 'gain_db': -6,
                     'norm_db': 0}]
            for cc in ([], cues):
                edit.mix_audio(src, cc, out, 3.0)
                r = subprocess.run(['ffmpeg', '-v', 'error', '-i', str(out), '-f', 'f32le', '-'], capture_output=True)
                x = np.abs(np.frombuffer(r.stdout, dtype=np.float32)).reshape(-1, 2).max(axis=1)   # both channels
                self.assertAlmostEqual(len(x) / 48000, 3.0, delta=0.002)                 # nothing lost or added
                first_ms, later = x[:48].max(), x[int(0.04 * 48000):int(0.1 * 48000)].max()
                self.assertLess(first_ms, later / 10)                                    # faded in at the start
                self.assertGreater(later, 10 ** (-6 / 20))                               # then at full level
                click = 1.95 * 48000 + int(np.argmax(x[int(1.95 * 48000):int(2.05 * 48000)]))
                self.assertAlmostEqual(click / 48000, 2.0, delta=0.001)                  # no shift in time
            m4a = Path(d) / 'mix.m4a'
            edit.encode_audio(src, cues, m4a, 3.0)
            self.assertLessEqual(edit.true_peak(m4a), edit.MAX_PEAK_DB + 0.05)

    def test_gameplay_keeps_long_quiet(self):
        words = sentence('so this is the first point', 0.0) + sentence('and here is the second one', 5.0)
        quiet = words[6]['s'] - words[5]['e']                                  # 2.8 s of gameplay
        self.assertGreater(quiet, cut.GAME_PAUSE)
        self.assertEqual(len(cut.jump_pieces(0.0, words[-1]['e'], words, lambda a, b: True, cut.GAME_PAUSE)), 1)
        self.assertEqual(len(cut.jump_pieces(0.0, words[-1]['e'], words, lambda a, b: True)), 2)

    def test_never_inside_a_word_still_being_said(self):
        # clip 21 of the GTA stream: a short mark lay inside a stretched word ("kaun," held 1.5 s); the pause
        # was measured from the mark's end and the cut fell inside "kaun". Now it counts from the word's end.
        words = [W('Through', 0.0, 0.4), W('kaun,', 0.4, 2.0), W('…', 1.0, 1.2), W('chaahe', 2.4, 2.8),
                 W('kaun', 2.8, 3.0), W('kaun', 3.1, 3.6)]
        pieces = cut.jump_pieces(0.0, 3.8, words, lambda a, b: True, cut.GAME_PAUSE)
        self.assertEqual(len(pieces), 1)                      # 0.4 s after "kaun," ends: no pause to cut
        words[1]['e'] = 1.1                                   # the same with a normal "kaun,": cut as before
        self.assertEqual(len(cut.jump_pieces(0.0, 3.8, words, lambda a, b: True, cut.GAME_PAUSE)), 2)

    def test_gameplay_keeps_a_pause_with_action_on_screen(self):
        # v2.7.1, clip 143 of the GTA stream: a takedown happened in a quiet second and pause cutting took it
        # out. A pause where the picture changes a lot stays; the same pause on a still picture is cut, and
        # motion only inside the webcam box doesn't count.
        import shutil
        import subprocess
        from clipper.common import DEFAULT_SETTINGS
        if not shutil.which('ffmpeg'):
            self.skipTest('no ffmpeg')
        words = sentence('so this is the first', 0.0) + sentence('abey yaar ye kya ho gaya', 3.1)
        self.assertTrue(cut.JUMP_PAUSE < words[5]['s'] - words[4]['e'] < cut.GAME_PAUSE)    # a 1.3 s pause
        clip = {'ranges': [[0.0, words[-1]['e'] + 0.2]]}
        with tempfile.TemporaryDirectory() as d:
            still, action, cam_only = (Path(d) / f'{n}.mp4' for n in ('still', 'action', 'cam'))
            gray = 'color=gray:s=320x180:r=30:d=6'
            subprocess.run(['ffmpeg', '-v', 'error', '-f', 'lavfi', '-i', gray, '-pix_fmt', 'yuv420p', str(still)], check=True)
            # a white box swinging back and forth from 2 s to 3 s: in the game area, or only inside the cam box
            for out, x, y in ((action, '120+100*sin(t*20)', 50), (cam_only, '200+40*sin(t*20)', 100)):
                subprocess.run(['ffmpeg', '-v', 'error', '-f', 'lavfi', '-i', gray, '-f', 'lavfi', '-i',
                                'color=white:s=70x70:r=30:d=6', '-filter_complex',
                                f"[0][1]overlay=x='{x}':y={y}:enable='between(t,2,3)'", '-pix_fmt', 'yuv420p',
                                str(out)], check=True)
            cam = {'x': 160, 'y': 90, 'w': 160, 'h': 90}
            n = lambda video, box=None: len(cut.with_jump_cuts(clip, words, {}, True,
                                                               cut.action_check(clip, video, box, (320, 180)))['ranges'])
            self.assertEqual(n(still), 2)                       # nothing happens: the pause is cut as before
            self.assertEqual(n(action), 1)                      # something happens: the pause stays
            self.assertEqual(n(cam_only, cam), 2)               # only the webcam moved: cut as before
            self.assertEqual(n(cam_only), 1)                    # (the same picture without the cam box left out)
            out = cut.with_jump_cuts(clip, words, {}, True, cut.action_check(clip, action, None, (320, 180)))
            self.assertEqual(out.get('action_kept'), 1)
        self.assertEqual(len(cut.with_jump_cuts(clip, words, {}, True)['ranges']), 2)       # no check: as before
        self.assertEqual(DEFAULT_SETTINGS['action_pauses'], 'keep')
        from unittest import mock                                # one flicker (a quarter second) is not action
        calm = [(i / 4, (i + 1) / 4, 10.0) for i in range(24)]
        for spikes, expect in (({9}, False), ({9, 10}, True)):
            rows = [(a, b, 40.0 if i in spikes else c) for i, (a, b, c) in enumerate(calm)]
            with mock.patch.object(cut, 'picture_change', return_value=rows):
                self.assertEqual(cut.action_check({'ranges': [[0, 6]]}, 'v.mp4')(2.1, 3.0), expect)


class EdgeFlash(unittest.TestCase):
    """A camera cut in a piece's last frames must not show a flash of the next shot (roadmap item 17)."""
    def setUp(self):
        self.words = sentence('so this is the first point', 10.0)
        self.clip = {'ranges': [[10.0, self.words[-1]['e']]]}
        self.end = cut.snap_range(10.0, self.words[-1]['e'], self.words)[1]

    def trims(self, cut_at):
        return cut.edge_trims(self.clip, self.words, 25.0,
                              lambda t0, dur: [(t0 + i * 0.04, 0.9 if abs(t0 + i * 0.04 - cut_at) < 0.02 else 0.01)
                                               for i in range(int(dur / 0.04) + 1)])

    def test_cut_after_the_last_word_ends_the_piece_before_it(self):
        last_e = self.words[-1]['e']
        tr = list(self.trims(last_e + 0.12).values())
        self.assertEqual(len(tr), 1)
        self.assertLess(tr[0]['e'], last_e + 0.12)
        self.assertGreater(tr[0]['e'], last_e)                 # no word lost
        self.assertEqual(tr[0]['hold_out'], 0.0)

    def test_cut_during_the_last_word_holds_the_old_shot(self):
        last = self.words[-1]
        tr = list(self.trims(last['e'] - 0.1).values())[0]
        self.assertAlmostEqual(tr['e'], round(self.end, 3))   # the sound plays to the end of the word
        self.assertGreater(tr['hold_out'], 0.1)
        self.assertLessEqual(tr["hold_out"], cut.EDGE_HOLD + 0.5 / 25.0 + 1e-6)   # up to half a frame more
        f = cut.edge_hold_filter('0:v', tr, 3.0, '0h')
        self.assertIn('tpad=', f)
        self.assertIn('stop_mode=clone', f)

    def test_framing_switch_never_leaves_a_sliver_at_an_edge(self):
        # Khan Sir 14: the split screen switched to a speaker crop 0.3 s before the end
        shots = [{'a': 0.0, 'b': 5.0, 'mode': 'crop'}, {'a': 5.0, 'b': 9.7, 'mode': 'split'},
                 {'a': 9.7, 'b': 10.0, 'mode': 'crop'}]
        out = cut.merge_edge_slivers(shots)
        self.assertEqual([(x['a'], x['b'], x['mode']) for x in out], [(0.0, 5.0, 'crop'), (5.0, 10.0, 'split')])
        out = cut.merge_edge_slivers([{'a': 0.0, 'b': 0.2, 'mode': 'split'}, {'a': 0.2, 'b': 4.0, 'mode': 'crop'}])
        self.assertEqual([(x['a'], x['b'], x['mode']) for x in out], [(0.0, 4.0, 'crop')])
        self.assertEqual(cut.merge_edge_slivers(shots[:2]), shots[:2])     # nothing short: unchanged

    def test_no_cut_no_change(self):
        self.assertEqual(self.trims(-100), {})
        clip = cut.with_edge_trims(self.clip, None, self.words, 25.0) if False else self.clip
        self.assertEqual(cut.snap_piece(clip, *self.clip['ranges'][0], self.words)[1], self.end)


class Streams(unittest.TestCase):
    def test_break_markers(self):
        lines = [{'s': 0.0, 'e': 5.0, 'text': 'starting soon song'}, {'s': 200.0, 'e': 205.0, 'text': 'hello chat'}]
        out = kind.hide_breaks(lines, [{'n': 1, 'start': 0.0, 'end': 160.0, 'where': 'start'}])
        self.assertIn('marker', out[0])
        self.assertEqual(out[1]['text'], 'hello chat')

    def test_still_runs(self):
        import numpy as np
        frames = np.concatenate([np.zeros((10, 36, 64), np.float32),               # a still screen
                                 np.random.default_rng(1).uniform(0, 255, (10, 36, 64)).astype(np.float32)])
        times = np.arange(20) * 6.0
        runs = kind.still_runs(times, frames)
        self.assertEqual(runs, [(0, 9)])

    def test_friends_on_voice_chat_count_like_the_streamer(self):
        # v2.7: the helpers were told to build only on the streamer; a 3-friends stream needed it said by hand
        self.assertIn('friends', kind.RULES)
        self.assertIn('count the same', kind.RULES)
        root = Path(__file__).resolve().parent.parent / '.claude' / 'agents'
        for name in ('clipkaro-part-reader.md', 'clipkaro-critic.md'):
            self.assertIn('friend', (root / name).read_text(encoding='utf-8'), name)


class MoreClips(unittest.TestCase):
    def test_unused_ideas(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)
            (p / 'critic').mkdir()
            ideas = [{'id': 'p1-c1', 'ranges': [[10, 40]], 'title': 'A', 'clip_score': 7.0, 'rank_score': 7.0},
                     {'id': 'p1-c2', 'ranges': [[100, 130]], 'title': 'B', 'clip_score': 6.0, 'rank_score': 6.0},
                     {'id': 'p1-c3', 'ranges': [[120, 150]], 'title': 'C', 'clip_score': 5.0, 'rank_score': 5.0},
                     {'id': 'p2-c1', 'ranges': [[300, 330]], 'title': 'D', 'clip_score': 4.0, 'rank_score': 4.0}]
            (p / 'critic' / 'critic.json').write_text(json.dumps({'clips': ideas}))
            (p / 'clips.json').write_text(json.dumps({'clips': [{'id': 1, 'from': 'p1-c1', 'ranges': [[10, 40]]}]}))
            from unittest import mock
            with mock.patch.object(more, 'overlap_mode', return_value='avoid'):
                left = [x['id'] for x in more.unused(p)]
            self.assertEqual(left, ['p1-c2', 'p2-c1'])     # "avoid": C overlaps the better B
            self.assertEqual([x['id'] for x in more.unused(p)], ['p1-c2', 'p2-c1'])   # a normal video: as before
            (p / 'project.json').write_text(json.dumps({'video_kind': {'live': True}}))  # a stream (v2.7 default)
            left = [x['id'] for x in more.unused(p)]       # C shares only 10 of its 30 s with B: allowed
            self.assertEqual(left, ['p1-c2', 'p1-c3', 'p2-c1'])
            ideas.append({'id': 'p2-c2', 'ranges': [[303, 333]], 'title': 'E', 'clip_score': 3.0, 'rank_score': 3.0})
            (p / 'critic' / 'critic.json').write_text(json.dumps({'clips': ideas}))
            self.assertNotIn('p2-c2', [x['id'] for x in more.unused(p)])       # a near-copy of D: never

    def test_overlaps_only_on_gameplay_and_streams(self):
        from unittest import mock
        from clipper import common
        podcast, stream = {'title': 'Figuring Out', 'video_kind': {}}, {'video_kind': {'live': True}}
        with mock.patch.object(common, 'settings', return_value={}):                  # the default: "streams"
            self.assertEqual((common.overlap_mode(podcast), common.overlap_mode(stream)), ('avoid', 'allow'))
        with mock.patch.object(common, 'settings', return_value={'overlap_clips': 'allow'}):
            self.assertEqual(common.overlap_mode(podcast), 'allow')
        with mock.patch.object(common, 'settings', return_value={'overlap_clips': 'avoid'}):
            self.assertEqual(common.overlap_mode(stream), 'avoid')

    def test_overlap_rule(self):
        # v2.7, overlap_clips "allow": a short and a long cut of one moment, a joined clip: fine; near-copies and
        # a fourth clip of the same seconds: not
        from clipper.common import overlap_problem
        short, long_ = [[100, 125]], [[100, 170]]
        self.assertIsNone(overlap_problem(long_, [('clip 1', short)]))
        self.assertIn('almost the same', overlap_problem([[101, 126]], [('clip 1', short)]))
        three = [('clip 1', short), ('clip 2', long_), ('clip 3', [[90, 130], [400, 420]])]
        self.assertIn('already in 3 clips', overlap_problem([[110, 200]], three))
        self.assertIn('overlaps clip 1', overlap_problem(long_, [('clip 1', short)], 'avoid'))


class ManyClips(unittest.TestCase):
    """v2.7: "no limit" / "as many as possible" / "100+": no cap, and each reader brings up to 20 ideas."""

    def test_no_limit(self):
        from types import SimpleNamespace
        from clipper import parts
        project = {'duration': 14650, 'breaks': [], 'video_kind': {}}
        t = parts.clip_target(project, 0, 14650, {}, 20)
        self.assertEqual((t['lo'], t['hi']), (3, 20))                         # the default, as before
        self.assertEqual(parts.ideas_per_part(t, 12), 5)
        t = parts.clip_target(project, 0, 14650, {'no_limit': True}, 20)
        self.assertEqual(t['hi'], parts.NO_LIMIT)                              # no cap
        self.assertGreaterEqual(t['lo'], 20)                                   # at least the usual number
        self.assertEqual(parts.ideas_per_part(t, 12), 20)
        t = parts.clip_target(project, 0, 14650, {'at_least': 100}, 20)        # "at least 100": many as well
        self.assertEqual(parts.ideas_per_part(t, 12), 20)
        a = SimpleNamespace(any_count=False, clips=None, at_least=None, at_most=None, deep=None, mode=None,
                            no_limit=True)
        self.assertEqual(parts.update_wish({'wish': {'at_most': 5}}, a), {'no_limit': True})   # no limit wins
        a = SimpleNamespace(any_count=True, clips=None, at_least=None, at_most=None, deep=None, mode=None)
        self.assertEqual(parts.update_wish({'wish': {'no_limit': True}}, a), {})                # forgotten again


class StarterSounds(unittest.TestCase):
    """v2.7: a free starter set of mood sounds (Mixkit), only for mood folders that are still empty."""

    def test_starter_set_covers_every_mood(self):
        from clipper import sfx
        self.assertEqual(set(sfx.STARTER), set(sfx.MOODS))
        for mood, items in sfx.STARTER.items():
            self.assertGreaterEqual(len(items), 2, mood)                     # so clips don't all sound alike
        self.assertIn('{id}', sfx.STARTER_URL)

    def test_own_sounds_are_never_touched_and_moods_needed(self):
        from unittest import mock
        from clipper import sfx
        with tempfile.TemporaryDirectory() as d:
            mine = Path(d)
            with mock.patch.object(sfx, 'MINE', mine), mock.patch.object(sfx, 'CATALOG', mine / '.catalog.json'):
                sfx.make_folders()
                for m in sfx.MOODS:                                          # every mood already has a sound
                    (mine / m / 'mine.mp3').write_bytes(b'x' * 10)
                with mock.patch('urllib.request.urlopen') as net:
                    self.assertEqual(sfx.starter(quiet=True), 0)
                    net.assert_not_called()
                self.assertEqual(sorted(p.name for p in (mine / 'funny').iterdir()), ['mine.mp3'])
            with mock.patch.object(sfx, 'moods_available', return_value={'funny': 3}):
                want, missing = sfx.needed([{'sfx': [[5.0, 'funny'], [9.0, 'shock']]}, {'sfx': [[2.0, 'funny']]}, {}])
            self.assertEqual(want, {'funny': 2, 'shock': 1})
            self.assertEqual(missing, ['shock'])


class PrivateDetails(unittest.TestCase):
    """v2.7: an email address or phone number said out loud never ends up in a clip."""

    @staticmethod
    def said(text, t0=100.0, step=0.4):
        return [W(w, round(t0 + k * step, 2), round(t0 + k * step + 0.3, 2)) for k, w in enumerate(text.split())]

    def test_spelled_email_and_phone_found(self):
        from clipper import private
        words = self.said('ab mera email ID hai r k 9 dot s h a r m a 2 1 at gmail dot com yaar')
        sp = private.spans(words)
        self.assertEqual(len(sp), 1)
        self.assertLessEqual(sp[0][0], words[2]['s'])                         # from "email"
        self.assertGreaterEqual(sp[0][1], words[-2]['e'])                     # to "com"
        words = self.said('mera number hai nine eight seven six five four three two one zero theek hai')
        self.assertEqual(private.spans(words)[0][2], 'a phone number')

    def test_talk_about_email_counting_and_buttons_are_left_alone(self):
        from clipper import private
        for text in ('naam ke saath mail ID bhej do sab log jaldi bhejo bhai',          # talk about an email
                     '1 2 3 4 5 6 7 8 9 10 11 12 13',                                   # counting
                     'look at the package x dabao phir R 2 aur L 1 se aim',             # game buttons
                     'tera number 1 .5 kauri meter 1 .5 kauri meter 1 .5 kauri meter'):  # a garbled loop
            self.assertEqual(private.spans(self.said(text)), [], text)

    def test_seconds_taken_out_and_lines_hidden(self):
        from clipper import private
        sp = [(110.0, 120.0, 'a phone number')]
        self.assertEqual(private.subtract([[100.0, 130.0]], sp), [[100.0, 110.0], [120.0, 130.0]])
        self.assertEqual(private.subtract([[112.0, 118.0]], sp), [])                    # all of it private
        lines = [{'s': 100.0, 'e': 108.0, 'text': 'a'}, {'s': 109.0, 'e': 113.0, 'text': 'b'},
                 {'s': 114.0, 'e': 119.0, 'text': 'c'}, {'s': 121.0, 'e': 125.0, 'text': 'd'}]
        out = private.hide_lines(lines, sp)
        self.assertEqual([ln.get('text') for ln in out], ['a', None, 'd'])
        self.assertIn('PRIVATE DETAILS', out[1]['marker'])
        self.assertIn('2 line(s)', out[1]['marker'])
        self.assertFalse(private.enabled({'private_details': 'keep'}))                  # the way back


class CarefulListening(unittest.TestCase):
    """v2.7: noisy Hindi / Hinglish streams: two more hearings, word-check packets, answers applied safely."""

    def project(self, d):
        pdir = Path(d)
        (pdir / 'transcript').mkdir()
        words = [W('Kisko', 10.0, 10.3), W('khaao', 10.4, 10.7), W('yaar', 10.8, 11.0),
                 W('vah', 12.0, 12.2), W('bhaag', 12.3, 12.6), W('gaya', 12.7, 13.0),
                 W('Thank', 14.0, 14.2), W('you.', 14.3, 14.5),
                 W('main', 16.0, 16.2), W('aaunga', 16.3, 16.7)]
        lines = [{'s': 10.0, 'e': 11.0, 'i0': 0, 'i1': 2}, {'s': 12.0, 'e': 13.0, 'i0': 3, 'i1': 5},
                 {'s': 14.0, 'e': 14.5, 'i0': 6, 'i1': 7}, {'s': 16.0, 'e': 16.7, 'i0': 8, 'i1': 9}]
        for name, data in (('words.json', words), ('sentences.json', lines)):
            (pdir / 'transcript' / name).write_text(json.dumps(data, ensure_ascii=False), encoding='utf-8')
        (pdir / 'project.json').write_text(json.dumps({'language': 'hinglish', 'title': 'GTA stream'}))
        (pdir / 'clips.json').write_text(json.dumps({'clips': [{'id': 1, 'title': 'A', 'ranges': [[9.5, 17.0]]}]}))
        return pdir

    def test_only_for_hindi_streams_on_a_graphics_card(self):
        from unittest import mock
        from clipper import gpu, hearing
        stream = {'language': 'hinglish', 'video_kind': {'live': True}}
        with mock.patch.object(gpu, 'cuda_device_count', return_value=1):
            self.assertTrue(hearing.wanted(stream, {})[0])
            self.assertFalse(hearing.wanted(dict(stream, language='en'), {})[0])
            self.assertFalse(hearing.wanted({'language': 'hinglish', 'video_kind': {}}, {})[0])    # a podcast
            self.assertFalse(hearing.wanted(stream, {'careful_listening': False})[0])           # the way back
        with mock.patch.object(gpu, 'cuda_device_count', return_value=0):
            self.assertFalse(hearing.wanted(stream, {})[0])                                     # no card: no

    def test_packets_show_three_hearings(self):
        from unittest import mock
        from clipper import hearing
        with tempfile.TemporaryDirectory() as d:
            pdir = self.project(d)
            (pdir / 'second-hearing' / 'clips').mkdir(parents=True)
            heard = {'1': [{'range': [9.5, 17.0], 'words': [['किसको', 10.0, 10.3], ['खाऊं', 10.4, 10.7]]}]}
            (pdir / 'second-hearing' / 'clips' / 'capsbro.json').write_text(json.dumps(heard, ensure_ascii=False))
            with mock.patch('clipper.voices.game_words', return_value={6, 7}):
                files = hearing.packets(pdir)
            text = files[0].read_text(encoding='utf-8')
            self.assertIn('CAPTIONS NOW', text)
            self.assertIn('[10.00] किसको खाऊं', text)                              # hearing B
            self.assertIn('(nothing heard)', text)                                 # hearing C missing
            self.assertIn('GAME [14.00-14.50] Thank you.', text)                   # hidden by the game-voice rule

    def test_answers_applied_safely(self):
        from unittest import mock
        from clipper import hearing
        with tempfile.TemporaryDirectory() as d:
            pdir = self.project(d)
            (pdir / 'wordcheck').mkdir()
            answer = [{'id': 1,
                       'fixes': [{'at': 10.4, 'wrong': 'khaao', 'right': 'khaaoon'},
                                 {'at': 16.0, 'wrong': 'main aaunga', 'right': 'main nahin aaunga'}],   # meaning flip
                       'doubts': [{'at': 12.3, 'heard': 'bhaag', 'maybe': ['bhaagh'], 'context': 'x'}],
                       'friend_english': [14.0], 'game_english': [], 'problem': None}]
            (pdir / 'wordcheck' / 'batch-01.json').write_text(json.dumps(answer))
            with mock.patch.object(hearing, 'settings', return_value={}):
                n = hearing.apply(pdir)
            words = json.loads((pdir / 'transcript' / 'words.json').read_text(encoding='utf-8'))
            self.assertEqual(words[1]['w'], 'khaaoon')                              # agreed fix written
            self.assertTrue(words[4].get('unsure'))                                 # doubt: no caption
            self.assertTrue(words[8].get('unsure') and words[9].get('unsure'))      # never a meaning flip
            self.assertEqual([w['w'] for w in words[8:10]], ['main', 'aaunga'])
            clips = json.loads((pdir / 'clips.json').read_text())['clips']
            self.assertEqual(clips[0]['show_captions'], [[13.95, 14.55]])         # a friend's English shown
            self.assertEqual((n['fixed'], n['meaning'], n['shown_lines']), (1, 1, 1))
            self.assertTrue((pdir / 'transcript' / 'words-before-wordcheck.json').exists())

    def test_ask_mode_lists_doubts_instead(self):
        from unittest import mock
        from clipper import hearing
        with tempfile.TemporaryDirectory() as d:
            pdir = self.project(d)
            (pdir / 'wordcheck').mkdir()
            (pdir / 'wordcheck' / 'batch-01.json').write_text(json.dumps(
                [{'id': 1, 'doubts': [{'at': 12.3, 'heard': 'bhaag', 'context': 'x'}]}]))
            with mock.patch.object(hearing, 'settings', return_value={'unsure_words': 'ask'}):
                hearing.apply(pdir)
            words = json.loads((pdir / 'transcript' / 'words.json').read_text(encoding='utf-8'))
            self.assertFalse(words[4].get('unsure'))                                # not hidden
            doubts = json.loads((pdir / 'word-check.json').read_text())['doubts']
            self.assertEqual((doubts[0]['heard'], doubts[0]['correct']), ('bhaag', ''))

    def test_a_models_loop_is_cut(self):
        from clipper import hearing
        ws = [['Are', 1.0, 1.1]] + [['bhai,', 1.2 + k / 10, 1.25 + k / 10] for k in range(40)] + [['itna', 6.0, 6.2]]
        out = hearing.no_loops(ws)
        self.assertEqual([w[0] for w in out], ['Are', 'bhai,', 'bhai,', 'bhai,', 'itna'])
        loop = [[t, 0, 0] for t in 'Raahul gaandhi kaary maal kar rahe the.'.split()] * 10 + [['Tabhi', 0, 0]]
        self.assertEqual(' '.join(w[0] for w in hearing.no_loops(loop)),
                         'Raahul gaandhi kaary maal kar rahe the. Tabhi')               # a phrase loop: kept once
        chant = [[t, 0, 0] for t in 'GTA six GTA six GTA six aa gaya'.split()]
        self.assertEqual(len(hearing.no_loops(chant)), 8)                                 # said three times: stays

    def test_readers_get_their_stretch_of_the_second_hearing(self):
        from clipper import hearing
        with tempfile.TemporaryDirectory() as d:
            pdir = Path(d)
            (pdir / 'second-hearing').mkdir()
            (pdir / 'second-hearing' / 'full.json').write_text(json.dumps(
                {'model': hearing.SECOND, 'complete': True,
                 'segments': [{'s': 5.0, 'e': 9.0, 't': 'पहले'}, {'s': 100.0, 'e': 104.0, 't': 'बाद में'}]},
                ensure_ascii=False), encoding='utf-8')
            text = hearing.part_text(pdir, 1, 2, (0.0, 50.0), (0.0, 60.0))
            self.assertIn('पहले', text)
            self.assertNotIn('बाद में', text)                                           # outside this part
            self.assertIn('Never quote it', text)


class ReleaseReviewFixes(unittest.TestCase):
    """v2.7.1 review (2026-11-21): what the review before the release found, each fixed and kept fixed."""

    @staticmethod
    def said(text, start=0.0, dur=0.3, gap=0.08):
        out, t = [], start
        for w in text.split():
            out.append(W(w, round(t, 2), round(t + dur, 2)))
            t += dur + gap
        return out

    def test_private_details_leave_everyday_talk_alone(self):
        from clipper import private
        for text in ('The number of people who quit at 25 is huge. One in two founders fail at 30, and at that point '
                     'you have maybe two options left.',
                     'My phone was dead, so I waited at the station for one hour, two hours, and at 9 I got home.',
                     'मेरा नंबर एक पे आया था, फिर दो साल बाद 2019 में मैंने एक और try किया, और 3 महीने में हो गया।',
                     'मुझे नहीं पता था कि एक दिन ऐसा होगा, दो साल पहले मैंने 5 लाख लगाए थे और 2020 में सब डूब गया',
                     'From 1999 2000 2001 the company grew very fast.'):
            self.assertEqual(private.spans(self.said(text)), [], text)
        for text in ('email ID hai x x 1 2 1 1 at the rate gmail dot com',
                     'Thik hai email ID aapki yahi sahi hai na. Haan, aman bhi baat hai 1211. 1 1. Bataana kaha aap '
                     'mujhe. AMAN. Haan. UP8. DH. YAY. 1 2 1 1.',                       # the real one, from a stream
                     'Kya tha 0 7 double 0 7 7 double 0. 77, haan, aage',
                     'mera number hai nine eight seven six five four three two one zero'):
            self.assertTrue(private.spans(self.said(text)), text)
        podcast, stream = {'title': 'Business talk', 'video_kind': {}}, {'video_kind': {'live': True}}
        self.assertFalse(private.wanted(podcast, {}))                  # gameplay and streams only, by default
        self.assertTrue(private.wanted(stream, {}))
        self.assertTrue(private.wanted(podcast, {'private_details': 'all'}))
        self.assertFalse(private.wanted(stream, {'private_details': 'keep'}))

    def test_long_clips_are_heard_in_windows(self):
        import wave
        from unittest import mock
        import numpy as np
        from clipper import hearing
        sr = 16000
        self.assertIsNone(hearing._windows(np.zeros(20 * sr, np.float32)))     # short: heard whole, as before
        audio = (np.random.default_rng(1).standard_normal(45 * sr) * 0.3).astype(np.float32)
        audio[int(24.5 * sr):int(25.5 * sr)] = 0.0                             # a pause at 25 s
        win = hearing._windows(audio)
        self.assertEqual((win[0]['start'], win[-1]['end']), (0.0, 45.0))
        odd = hearing._windows(np.zeros(650_207, np.float32))                  # 40.6379 s: never past the last sample
        self.assertLessEqual(int(odd[-1]['end'] * sr), 650_207)
        self.assertTrue(all(w['end'] - w['start'] <= 28.0 for w in win))
        self.assertTrue(24.5 <= win[0]['end'] <= 25.5)                          # split in the pause
        seen = []

        class Stub:                                    # faster-whisper's batch mode, as strict as the real one
            def transcribe(self, audio, **kw):
                if kw.get('clip_timestamps') is None and len(audio) / sr >= 30:
                    raise RuntimeError('No clip timestamps found.')
                seen.append(kw.get('clip_timestamps'))
                return [], None
        with tempfile.TemporaryDirectory() as d:
            pdir = Path(d)
            (pdir / 'source').mkdir()
            with wave.open(str(pdir / 'source' / 'audio16k.wav'), 'wb') as w:
                w.setnchannels(1)
                w.setsampwidth(2)
                w.setframerate(sr)
                w.writeframes((audio * 20000).astype(np.int16).tobytes())
            (pdir / 'clips.json').write_text(json.dumps({'clips': [{'id': 1, 'ranges': [[6.0, 40.0]]},
                                                                   {'id': 2, 'ranges': [[10.0, 25.0]]}]}))
            with mock.patch.object(hearing, '_pipeline', return_value=(object(), Stub())):
                hearing.hear_clips(pdir, quiet=True)                           # crashed on clip 1 before
        self.assertEqual(len(seen), 4)                                         # 2 clips x 2 models
        self.assertTrue(seen[0] and seen[1] is None)                           # long: windows; short: whole

    def test_never_on_the_graphics_card_when_live_or_on_the_processor(self):
        import os
        from unittest import mock
        from clipper import gpu, hearing, watch
        stream = {'language': 'hinglish', 'video_kind': {'live': True}}
        with mock.patch.object(gpu, 'cuda_device_count', return_value=1):
            self.assertTrue(hearing.wanted(stream, {})[0])
            self.assertFalse(hearing.wanted(stream, {}, device='cpu')[0])          # live clipping chose the processor
            self.assertFalse(hearing.wanted(stream, {'device': 'cpu'})[0])
            with mock.patch.dict(os.environ, {'CLIPKARO_LIVE': '1'}):
                self.assertFalse(hearing.wanted(stream, {})[0])
                self.assertFalse(watch.wanted(stream, {})[0])

    def test_no_flip_of_a_nahin_in_any_spelling(self):
        from clipper import hearing
        n = hearing._negations
        self.assertNotEqual(n("don't go"), n('go'))                                # was applied before
        self.assertNotEqual(n('nahin-aaunga'), n('aaunga'))
        self.assertNotEqual(n('main nahiii jaunga'), n('main jaunga'))
        self.assertEqual(n('main nahi aaunga'), n('main nahin aaunga'))           # a respelling keeps the meaning
        self.assertEqual(n('मैं नहीं आऊंगा'), n('main nahin aaunga'))

    def test_a_hidden_flip_stays_hidden(self):
        from unittest import mock
        from clipper import hearing
        with tempfile.TemporaryDirectory() as d:
            pdir = CarefulListening.project(None, d)
            (pdir / 'wordcheck').mkdir()
            (pdir / 'wordcheck' / 'batch-01.json').write_text(json.dumps([
                {'id': 1, 'fixes': [{'at': 16.0, 'wrong': 'main aaunga', 'right': 'main nahin aaunga'}]},
                {'id': 2, 'fixes': [{'at': 16.0, 'wrong': 'main aaunga', 'right': 'main aaoonga'},
                                    {'wrong': 'yaar', 'right': 'yar'}]}]))         # no "at": skipped, no crash
            with mock.patch.object(hearing, 'settings', return_value={}):
                hearing.apply(pdir)
            words = json.loads((pdir / 'transcript' / 'words.json').read_text(encoding='utf-8'))
            self.assertTrue(words[8].get('unsure') and words[9].get('unsure'))     # a later fix can't show it again
            self.assertTrue((pdir / 'transcript' / 'words-before-fixes.json').exists())   # words as first heard

    def test_game_line_marks_its_own_line(self):
        from unittest import mock
        from clipper import hearing
        with tempfile.TemporaryDirectory() as d:
            pdir = Path(d)
            (pdir / 'transcript').mkdir()
            words = [W('bhai', 10.0, 10.4), W('chal.', 10.5, 11.0), W('Get', 11.1, 11.4), W('down!', 11.5, 12.0)]
            lines = [{'s': 10.0, 'e': 11.0, 'i0': 0, 'i1': 1}, {'s': 11.1, 'e': 12.0, 'i0': 2, 'i1': 3}]
            (pdir / 'transcript' / 'words.json').write_text(json.dumps(words))
            (pdir / 'transcript' / 'sentences.json').write_text(json.dumps(lines))
            (pdir / 'project.json').write_text('{}')
            (pdir / 'clips.json').write_text(json.dumps({'clips': [{'id': 1, 'ranges': [[9.5, 12.5]]}]}))
            (pdir / 'wordcheck').mkdir()
            (pdir / 'wordcheck' / 'batch-01.json').write_text(json.dumps([{'id': 1, 'game_english': [11.1]}]))
            with mock.patch.object(hearing, 'settings', return_value={}):
                hearing.apply(pdir)
            clip = json.loads((pdir / 'clips.json').read_text())['clips'][0]
            self.assertEqual(clip['hide_captions'], [[11.05, 12.05]])              # not the friend's line before it

    def events(self, clips, events, cfg=None):
        from unittest import mock
        from clipper import watch
        with tempfile.TemporaryDirectory() as d:
            pdir = Path(d)
            (pdir / 'frames').mkdir()
            (pdir / 'project.json').write_text(json.dumps({'duration': 600.0}))
            (pdir / 'clips.json').write_text(json.dumps({'clips': clips}))
            (pdir / 'frames' / 'events.json').write_text(json.dumps(
                [dict({'spot': 1, 'where': 'game', 'title': 'Crash', 'why': 'x'}, **e) for e in events]))
            with mock.patch.object(watch, 'settings', return_value=cfg or {}), \
                    mock.patch.object(watch, '_video', return_value=None), mock.patch.object(watch, 'exact_sheet'):
                done = watch.apply_events(pdir)
            return [(what, cid) for what, cid, _ in done], json.loads((pdir / 'clips.json').read_text())['clips'] \
                if done else clips

    def test_event_starts(self):
        ev = {'event_at': 100.0, 'end': 130.0}
        done, clips = self.events([{'id': 1, 'ranges': [[102.0, 130.0]]}], [ev])
        self.assertEqual(done, [('starts at its event', 1)])                      # 2 s after: it gets its lead-in
        self.assertEqual(clips[0]['ranges'][0][0], 98.5)
        done, _ = self.events([{'id': 1, 'ranges': [[60.0, 120.0]]}, {'id': 2, 'ranges': [[118.0, 150.0]]}], [ev])
        self.assertEqual(done, [('already shows it', 1)])                         # never a second clip of it
        done, _ = self.events([{'id': 1, 'ranges': [[125.0, 210.0]]}], [ev])
        self.assertEqual(done, [('reaction clip kept', 1)])                       # would pass 90 s
        done, _ = self.events([{'id': 1, 'ranges': [[110.0, 140.0]]}], [ev], {'event_lead_in': False})
        self.assertEqual(done, [('reaction clip kept', 1)])                       # no near-copy next to it
        done, clips = self.events([], [{'event_at': 300.0, 'end': 500.0}, {'event_at': 599.5, 'end': 640.0}])
        self.assertEqual(done, [('new clip', 1)])                                 # past the end: nothing
        self.assertEqual(clips[0]['ranges'], [[298.5, 388.5]])                    # at most 90 s

    def test_joined_clips_dont_say_so_in_posts(self):
        import contextlib
        import io
        from unittest import mock
        from clipper import common, post
        line = 'From 3 moments of the full video: 2:30:20 · 2:52:29 · 2:53:36'
        clip = {'id': 1, 'title': 'Club Ki Talash', 'ranges': [[0.0, 20.0]], 'deep': {'moments': ['2:30:20']},
                'caption': f'{line}\nClub dhoondha, jannat mil gayi #GTA6\nFull video: https://www.twitch.tv/videos/1',
                'post': {'youtube': {'title': 'Club Dhoondha, Jannat Mili | GTA 6 Hindi #Shorts (3 moments joined)',
                                     'description': f'{line}\nStory missions skip karke club pahunch gaye.'},
                         'instagram': {'caption': f'{line}\nYah to jannat aa gaya 😍 #GTA6'}}}
        with tempfile.TemporaryDirectory() as d:
            pdir = Path(d)
            (pdir / 'edited').mkdir()
            (pdir / 'edited' / '01-club.mp4').write_bytes(b'')
            (pdir / 'clips.json').write_text(json.dumps({'clips': [clip]}, ensure_ascii=False), encoding='utf-8')
            (pdir / 'project.json').write_text('{}')
            saved = common.settings
            try:
                for joined in (None, True):
                    common.settings = lambda: dict(common.DEFAULT_SETTINGS, **({} if joined is None else
                                                                               {'joined_note': joined}))
                    with contextlib.redirect_stderr(io.StringIO()), contextlib.redirect_stdout(io.StringIO()), \
                            mock.patch.object(post, 'settings', common.settings):
                        c = post.build(pdir)[0]['clips'][0]
                    texts = [c['caption'], c['text']['youtube']['title'], c['text']['youtube']['description'],
                             c['text']['instagram']['caption']]
                    if joined is None:                    # the default: for us, not for viewers
                        self.assertFalse(any('moments' in t for t in texts), texts)
                        self.assertEqual(c['text']['youtube']['title'], 'Club Dhoondha, Jannat Mili | GTA 6 Hindi #Shorts')
                        self.assertEqual(c['caption'], 'Club dhoondha, jannat mil gayi #GTA6\n'
                                                       'Full video: https://www.twitch.tv/videos/1')
                    else:                                 # the way back
                        self.assertTrue(all('moments' in t for t in texts))
            finally:
                common.settings = saved

    def test_frame_sheets_safe_on_windows(self):
        import numpy as np
        from clipper import watch
        from clipper.common import imwrite
        self.assertIsNone(watch.compose([], Path(tempfile.gettempdir()) / 'none.jpg'))   # no frames: no sheet, no crash
        src = Path(watch.__file__).read_text(encoding='utf-8')
        self.assertNotIn('cv2.imread(', src)              # OpenCV's own file calls fail on Hindi letters on Windows
        self.assertNotIn('cv2.imwrite(', src)
        with tempfile.TemporaryDirectory() as d:
            folder = Path(d) / 'gta-6-दिन-एक'
            folder.mkdir()
            imwrite(folder / 'f.jpg', np.full((180, 320, 3), 90, np.uint8))
            self.assertTrue(watch.compose([(folder / 'f.jpg', '0:10', True, 'bhaag', False)], folder / 'sheet.jpg'))


class PartOfVideo(unittest.TestCase):
    """v2.8: "only the first hour" writes down and clips only that part, on the full video's clock."""

    def test_times(self):
        from clipper.fetch import parse_time
        for text, secs in (('1:05:30', 3930), ('20:00', 1200), ('90', 90), ('1h', 3600), ('1h30m', 5400),
                           ('45m', 2700), ('30s', 30), (None, None), ('', None)):
            self.assertEqual(parse_time(text), secs, text)
        with self.assertRaises(SystemExit):
            parse_time('soon')

    def test_ranges(self):
        from clipper.fetch import video_range
        self.assertIsNone(video_range(None, None, 3600))                          # the whole video, as before
        self.assertEqual(video_range(None, '1:00:00', 14650), [0.0, 3600.0])      # "only the first hour"
        self.assertEqual(video_range('20:00', '1:10:00', 14650), [1200.0, 4200.0])
        self.assertEqual(video_range('2:00:00', None, 14650), [7200.0, 14650.0])  # to the end
        self.assertEqual(video_range(None, '9:00:00', 3600), [0.0, 3600.0])       # never past the end
        with self.assertRaises(SystemExit):
            video_range('10:00', '10:20', 3600)                                   # too short

    def test_transcript_says_which_part(self):
        from clipper import fetch
        with tempfile.TemporaryDirectory() as d:
            pdir = Path(d)
            (pdir / 'transcript').mkdir()
            words = sentence('this part was asked for by the owner.', 3600.0)
            project = {'title': 'Stream', 'language': 'en', 'duration': 14650, 'range': [3600.0, 7200.0]}
            tx, _ = fetch.write_transcript(pdir, words, project)
            head = Path(tx).read_text(encoding='utf-8')
        self.assertIn('only part of the video is written down: 1:00:00 to 2:00:00', head)


class LiveSettings(unittest.TestCase):
    """settings.json ships "<...>" placeholders for the user's own live settings (OBS folder, Twitch
    channel): they count as not set, so Claude asks for them and a placeholder is never used as a path."""

    def test_placeholder(self):
        from clipper import common
        self.assertTrue(common.is_placeholder('<your OBS recording folder>'))
        self.assertTrue(common.is_placeholder(' <your Twitch channel> '))
        for real in ('D:/OBS_Recording', 'allthingsaman', None, 10, '', 'a <b> c'):
            self.assertFalse(common.is_placeholder(real))

    def test_settings_turn_placeholders_into_none(self):
        from unittest import mock
        from clipper import common
        fake = {'live_folder': '<your OBS recording folder>', 'twitch_channel': 'allthingsaman', 'live_post': 'now'}
        with mock.patch.object(common, 'load_json', return_value=fake):
            s = common.settings()
        self.assertIsNone(s['live_folder'])
        self.assertEqual(s['twitch_channel'], 'allthingsaman')
        self.assertEqual(s['live_post'], 'now')


class Posting(unittest.TestCase):
    def test_honesty_note(self):
        from clipper.post import honesty_note
        self.assertEqual(honesty_note({'deep': {'honesty_note': {'role': 'viewer', 'reason': 'x'}}}), 'x')
        self.assertIsNone(honesty_note({}))


class BrandKit(unittest.TestCase):
    """v2.4: your logo bottom right, your outro after the clip, "(C) Channel" bottom left (YouTube links)."""

    def test_credit_only_for_youtube_links(self):
        from clipper import brandkit
        yt = {'kind': 'youtube', 'channel': 'Raj Shamani'}
        self.assertEqual(brandkit.credit_text(yt), '© Raj Shamani')
        self.assertIsNone(brandkit.credit_text({'kind': 'local', 'channel': None}))   # your own file
        self.assertIsNone(brandkit.credit_text(yt, on=False))                         # "source_credit": false
        self.assertIsNone(brandkit.credit_text({'kind': 'youtube', 'channel': '  '}))
        long = brandkit.credit_text({'kind': 'youtube', 'channel': 'A very long channel name ' * 4})
        self.assertLessEqual(len(long), brandkit.CREDIT_MAX + 2)
        self.assertTrue(long.endswith('…'))
        cr = brandkit.credit(yt)
        self.assertEqual((cr['x'], cr['y']), (brandkit.PAD, 1920 - brandkit.PAD))       # bottom left, padded
        self.assertEqual(brandkit.credit({'kind': 'youtube', 'channel': 'खान सर'})['font_file'],
                         'Poppins-ExtraBold.ttf')                                       # Hindi letters

    def test_credit_names_twitch_and_kick(self):
        # v2.7: a streamer's name alone read like their (different) YouTube channel
        from unittest import mock
        from clipper import brandkit
        tw = {'kind': 'youtube', 'channel': 'allthingsaman', 'source': 'https://www.twitch.tv/videos/2933339699'}
        self.assertEqual(brandkit.credit_text(tw), '© twitch.tv/allthingsaman')
        self.assertEqual(brandkit.credit_text(dict(tw, channel='twitch.tv/allthingsaman')),
                         '© twitch.tv/allthingsaman')                                   # never twice
        self.assertEqual(brandkit.credit_text({'kind': 'youtube', 'channel': 'xqc', 'source': 'https://kick.com/xqc'}),
                         '© kick.com/xqc')
        self.assertEqual(brandkit.credit_text({'kind': 'youtube', 'channel': 'Raj Shamani',
                                               'source': 'https://youtu.be/abc'}), '© Raj Shamani')
        with mock.patch.object(brandkit, 'settings', return_value={'credit_text': 'clipped from {channel}'}):
            self.assertEqual(brandkit.credit_text(tw), 'clipped from twitch.tv/allthingsaman')

    def test_logo_bottom_right_with_padding(self):
        from clipper import brandkit
        for w, h in ((400, 400), (800, 200), (300, 900)):
            lw, lh, x, y = brandkit.logo_box(w, h)
            self.assertLessEqual(lw, brandkit.LOGO_MAX_W)
            self.assertLessEqual(lh, brandkit.LOGO_MAX_H)
            self.assertEqual((x + lw, y + lh), (1080 - brandkit.PAD, 1920 - brandkit.PAD))
            self.assertLess(abs(lw / lh - w / h), 0.1)                                  # not stretched
        self.assertEqual(brandkit.logo_box(400, 400)[:2], (120, 120))

    def test_outro_length_and_shape(self):
        from clipper import brandkit
        self.assertEqual(brandkit.outro_check(4.0, 1080, 1920), (True, []))
        ok, msgs = brandkit.outro_check(7.0, 1080, 1920)
        self.assertTrue(ok and len(msgs) == 1)                  # a warning: 3-5 s is ideal
        ok, msgs = brandkit.outro_check(12.0, 1080, 1920)
        self.assertFalse(ok)                                    # never longer than the clip itself
        ok, msgs = brandkit.outro_check(4.0, 1920, 1080)
        self.assertTrue(ok and 'blurred' in msgs[0])            # not standing: fitted

    def test_files_found_in_the_folder(self):
        from clipper import brandkit
        with tempfile.TemporaryDirectory() as d:
            self.assertIsNone(brandkit.find('logo', brandkit.IMAGE_EXT, d))
            (Path(d) / 'logo.txt').write_text('x')
            (Path(d) / 'Logo.PNG').write_bytes(b'x')
            self.assertEqual(brandkit.find('logo', brandkit.IMAGE_EXT, d).name, 'Logo.PNG')
            self.assertEqual(brandkit.logo(True, d)[0], None)   # not a real picture: left out, with a note
            self.assertTrue(brandkit.logo(True, d)[1])
            kit, _ = brandkit.resolve({'kind': 'local'}, d, where=d)
            self.assertEqual(kit, {'credit': None, 'logo': None, 'outro': None})

    def test_logo_before_the_outro(self):
        from clipper import brandkit
        lg = {'w': 120, 'h': 120, 'x': 920, 'y': 1760, 'alpha': 0.9}
        g = brandkit.video_graph('ass=x.ass', 30, lg, {'duration': 4}, 2, 3)
        self.assertIn('overlay=920:1760', g)
        self.assertLess(g.index('overlay=920:1760'), g.index('concat=n=2'))       # no logo on the outro
        self.assertTrue(g.endswith('[v]'))
        self.assertEqual(brandkit.inputs({'logo': {'file': 'l.png'}, 'outro': None}), (['-i', 'l.png'], 2, None))

    def test_credit_in_the_captions_file(self):
        from clipper import brandkit, edit
        p = plan.build(meta_for(sentence('this is the first point.', 0.0)),
                       {'accent': '#FFD60A', 'text': '#FFFFFF', 'outline': '#000000'}, V11)
        p['credit'] = brandkit.credit({'kind': 'youtube', 'channel': 'Raj Shamani'})
        with tempfile.TemporaryDirectory() as d:
            ass = Path(d) / 'x.ass'
            edit.write_ass(p, ass)
            text = ass.read_text(encoding='utf-8')
        self.assertIn('Style: Credit,', text)
        self.assertIn(',&H4DFFFFFF,', text)                     # 70 % visible, like the logo
        self.assertEqual(brandkit.logo_box(400, 400)[:2], (120, 120))
        self.assertIn('{\\an1\\pos(0,1920)}© Raj Shamani', text)          # right in the corner

    def test_corners_from_settings(self):
        from clipper import brandkit
        self.assertEqual(brandkit.corner('bot right', 'x'), ('bottom-right', None))
        self.assertEqual(brandkit.corner('Top_Left', 'x'), ('top-left', None))
        self.assertEqual(brandkit.corner('TR', 'x'), ('top-right', None))
        c, note = brandkit.corner('middle', 'bottom-left')
        self.assertEqual(c, 'bottom-left')                     # only the four corners
        self.assertTrue(note)
        self.assertEqual(brandkit.logo_box(400, 400, 'top-left'), (120, 120, 0, 0))   # no gap
        self.assertEqual(brandkit.logo_box(400, 400, 'bottom-right'), (120, 120, 960, 1800))
        cr = brandkit.credit({'kind': 'youtube', 'channel': 'X'}, where='top-right')
        self.assertEqual((cr['an'], cr['x'], cr['y']), (9, 1080, 0))
        # both in one corner: the credit goes next to the logo (above it at the bottom), never under it
        lg = {'x': 960, 'y': 1800, 'w': 120, 'h': 120, 'corner': 'bottom-right'}
        cr = brandkit.share_corner(brandkit.credit({'kind': 'youtube', 'channel': 'X'}, where='bottom-right'), lg)
        self.assertEqual(cr['y'], 1800)
        with tempfile.TemporaryDirectory() as d:
            kit, notes = brandkit.resolve({'kind': 'youtube', 'channel': 'X'}, d, where=d,
                                          logo_corner='top-left', credit_corner='nowhere')
            self.assertEqual(kit['credit']['corner'], 'bottom-left')
            self.assertEqual(len(notes), 1)

    def test_plain_logo_background_made_see_through(self):
        import cv2
        import numpy as np
        from clipper import brandkit
        img = np.zeros((200, 200, 3), np.uint8)                   # a logo on a black square:
        cv2.circle(img, (100, 100), 60, (255, 200, 0), 14)        # a ring, black inside it
        self.assertEqual(brandkit.plain_background(img), (0, 0, 0))
        out = brandkit.see_through(img, (0, 0, 0))
        self.assertEqual(out[2, 2, 3], 0)                         # the background: see-through
        self.assertEqual(out[100, 40, 3], 255)                    # the ring: solid
        self.assertEqual(out[100, 100, 3], 255)                   # black inside the logo stays
        noisy = np.random.default_rng(1).integers(0, 255, (200, 200, 3), dtype=np.uint8)
        self.assertIsNone(brandkit.plain_background(noisy))       # a photo: left alone
        clear = np.dstack([img, np.full((200, 200), 255, np.uint8)])
        clear[:5] = 0
        self.assertIsNone(brandkit.plain_background(clear))       # already see-through: left alone
        with tempfile.TemporaryDirectory() as d:
            f = Path(d) / 'logo.png'
            cv2.imwrite(str(f), img)
            use, note, size = brandkit.clean_logo(f, d)
            self.assertNotEqual(use, f)
            self.assertIn('black background', note)
            self.assertEqual(cv2.imread(str(use), cv2.IMREAD_UNCHANGED).shape[2], 4)
            self.assertLess(size[0], 200)                         # the empty margin trimmed: right in the corner
            self.assertEqual(brandkit.clean_logo(f, d, keep=True), (f, None, (200, 200)))   # "keep"

    def test_way_back(self):
        from clipper import edit
        from clipper.common import DEFAULT_SETTINGS
        self.assertTrue(DEFAULT_SETTINGS['source_credit'] and DEFAULT_SETTINGS['logo'] and DEFAULT_SETTINGS['outro'])
        self.assertEqual((DEFAULT_SETTINGS['logo_corner'], DEFAULT_SETTINGS['credit_corner']),
                         ('bottom-right', 'bottom-left'))
        self.assertEqual(DEFAULT_SETTINGS['logo_background'], 'remove')
        # no logo, no outro: the encoder gets exactly the picture arguments it got before v2.4
        self.assertEqual(edit.finish_args({'fps': 30}, 'null'), ([], ['-vf', 'null', '-map', '0:v']))


class WindowsAndMac(unittest.TestCase):
    """Install check for Windows and macOS (v2.5): things this Linux laptop can still check."""

    def test_pictures_in_a_hindi_folder(self):
        import numpy as np
        from clipper.common import imread, imwrite
        with tempfile.TemporaryDirectory() as d:
            folder = Path(d) / 'black-myth-wukong-इतना-मुश्किल'
            folder.mkdir()
            img = np.zeros((20, 30, 3), np.uint8)
            img[5:10, 5:10] = (0, 128, 255)
            f = folder / 'frame.png'
            self.assertTrue(imwrite(f, img))
            back = imread(f)
            self.assertEqual(back.shape, img.shape)
            self.assertTrue((back == img).all())
            self.assertIsNone(imread(folder / 'missing.png'))

    def test_caption_file_names(self):
        from clipper.edit import ass_name
        self.assertEqual(ass_name('01-final-boss'), '01-final-boss.ass')          # as before
        name = ass_name('02-पहली-बड़ी-डकैती')
        self.assertTrue(name.isascii() and name.endswith('.ass'))
        self.assertNotEqual(name, ass_name('02-पहली-बड़ी-चोरी'))                       # two clips never share one
        self.assertTrue(ass_name('03-हिंदी', '.credit').endswith('.credit.ass'))

    def test_python_versions(self):
        import install
        self.assertIsNone(install.python_problem((3, 12), 'nt', 'AMD64'))
        self.assertIsNone(install.python_problem((3, 14), 'darwin', 'arm64'))
        self.assertIsNone(install.python_problem((3, 13), 'darwin', 'x86_64'))
        self.assertIn('too new', install.python_problem((3, 15), 'darwin', 'arm64'))   # "brew install python"
        self.assertIn('Intel Mac', install.python_problem((3, 14), 'darwin', 'x86_64'))
        self.assertIn('3.10', install.python_problem((3, 9), 'fedora', 'x86_64'))

    def test_mac_finds_the_full_ffmpeg(self):
        import os
        import sys
        from unittest import mock
        import run
        full = '/opt/homebrew/opt/ffmpeg-full/bin'
        with mock.patch.object(sys, 'platform', 'darwin'), \
                mock.patch('os.path.isfile', lambda p: p == full + '/ffmpeg'), \
                mock.patch.dict(os.environ, {'PATH': '/usr/bin:/opt/homebrew/bin'}):
            run.find_ffmpeg()
            self.assertTrue(os.environ['PATH'].startswith(full + os.pathsep))     # ahead of a plain ffmpeg
        with mock.patch.object(sys, 'platform', 'darwin'), mock.patch('shutil.which', lambda n: None), \
                mock.patch('os.path.isfile', lambda p: p == '/opt/homebrew/bin/ffmpeg'), \
                mock.patch.dict(os.environ, {'PATH': '/usr/bin:/bin'}):
            run.find_ffmpeg()                                     # a background app without Homebrew's folder
            self.assertTrue(os.environ['PATH'].endswith(os.pathsep + '/opt/homebrew/bin'))


class YouTubeSignIn(unittest.TestCase):
    """2026-11-17: YouTube's sign-in check on Windows, where Chrome, Edge and Brave lock their logins.
    A cookies file in the ClipKaro folder is used, but only when YouTube asks."""

    BOT = ("ERROR: [youtube] CswOUBuokjo: Sign in to confirm you're not a bot. Use --cookies-from-browser or "
           '--cookies for the authentication.')

    def setUp(self):
        from clipper import fetch
        self.fetch = fetch
        fetch.signed_in['file'] = None
        self.addCleanup(fetch.signed_in.update, {'file': None})

    def test_finds_the_cookies_file(self):
        import os
        import time
        find = self.fetch.find_cookies_file
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            self.assertIsNone(find({}, root))                                     # none: as before
            ext = root / 'www.youtube.com_cookies.txt'                            # the extension's own name
            ext.write_text('# Netscape HTTP Cookie File\n', encoding='utf-8')
            self.assertEqual(find({}, root), ext)
            plain = root / 'cookies.txt'
            plain.write_text('# Netscape HTTP Cookie File\n', encoding='utf-8')
            os.utime(ext, (time.time() + 60, time.time() + 60))                   # newer, but cookies.txt wins
            self.assertEqual(find({}, root), plain)
            (root / 'mine').mkdir()
            own = root / 'mine' / 'yt.txt'
            own.write_text('x', encoding='utf-8')
            self.assertEqual(find({'cookies_file': 'mine/yt.txt'}, root), own)  # settings.json wins
            self.assertEqual(find({'cookies_file': 'gone.txt'}, root), plain)    # missing: falls back

    def test_used_only_when_youtube_asks(self):
        from types import SimpleNamespace as R
        from unittest import mock
        calls = []

        def answers(*replies):
            it = iter(replies)
            return lambda cmd: (calls.append(cmd), next(it))[1]

        ok, bot = R(returncode=0, stdout='{}', stderr=''), R(returncode=1, stdout='', stderr=self.BOT)
        spare = Path('C:/ClipKaro/cookies.txt')
        # no check: the same command as before, no login sent
        with mock.patch.object(self.fetch, 'run_ytdlp', answers(ok)), \
                mock.patch.object(self.fetch, 'find_cookies_file', lambda: spare):
            self.assertEqual(self.fetch.ytdlp(['URL']), '{}')
        self.assertNotIn('--cookies', calls[-1])
        self.assertIsNone(self.fetch.signed_in['file'])
        # the check: tried again with the file, which the next downloads then use at once
        calls.clear()
        with mock.patch.object(self.fetch, 'run_ytdlp', answers(bot, ok, ok)), \
                mock.patch.object(self.fetch, 'find_cookies_file', lambda: spare):
            self.fetch.ytdlp(['URL'])
            self.assertEqual(calls[1][calls[1].index('--cookies') + 1], str(spare))
            self.fetch.ytdlp(['AUDIO'])
        self.assertEqual(len(calls), 3)
        self.assertIn('--cookies', calls[2])
        # a browser named by hand: used as before, never mixed with the file
        self.fetch.signed_in['file'] = None
        cmd = self.fetch.ytdlp_cmd('firefox', spare)
        self.assertEqual(cmd[cmd.index('--cookies-from-browser') + 1], 'firefox')
        self.assertNotIn('--cookies', cmd)
        # the check and no file: stops, with the way to make one
        with mock.patch.object(self.fetch, 'run_ytdlp', answers(bot)), \
                mock.patch.object(self.fetch, 'find_cookies_file', lambda: None), \
                self.assertRaises(SystemExit):
            self.fetch.ytdlp(['URL'])

    def test_plain_words_for_each_problem(self):
        problem = self.fetch.ytdlp_problem
        dpapi = problem('ERROR: Failed to decrypt with DPAPI. See https://github.com/yt-dlp/yt-dlp/issues/10927',
                        'brave', windows=True)
        self.assertIn('Get cookies.txt LOCALLY', dpapi)
        self.assertIn('without --cookies-from-browser', dpapi)
        locked = problem('ERROR: Could not copy Chrome cookie database. See ...', 'brave', windows=True)
        self.assertIn('Close it completely', locked)
        self.assertIn('Get cookies.txt LOCALLY', locked)
        self.assertNotIn('Get cookies.txt', problem('ERROR: Could not copy Chrome cookie database.', 'chrome',
                                                     windows=False))
        self.assertIn('firefox', problem(self.BOT, windows=True))
        self.assertIn('probably old', problem(self.BOT, None, 'C:/ClipKaro/cookies.txt'))
        self.assertEqual(problem('ERROR: Video unavailable'), 'ERROR: Video unavailable')   # others: as before

    def test_never_committed(self):
        from fnmatch import fnmatch
        root = Path(__file__).resolve().parent.parent
        rules = [ln.strip() for ln in (root / '.gitignore').read_text(encoding='utf-8').splitlines()
                 if ln.strip() and not ln.startswith(('#', '!'))]
        for name in ('cookies.txt', 'www.youtube.com_cookies.txt', 'youtube_cookies.txt'):
            self.assertTrue(any(fnmatch(name, r) for r in rules), name)


class LiveClipping(unittest.TestCase):
    """v2.6: clips while the stream runs (OBS pieces, Twitch chat and viewer clips as hints)."""

    def test_chat_lines(self):
        from clipper import twitch
        self.assertEqual(twitch.parse_privmsg(':ravi!ravi@ravi.tmi.twitch.tv PRIVMSG #gamingthings :KEKW bhai'),
                         ('ravi', 'KEKW bhai'))
        self.assertIsNone(twitch.parse_privmsg(':tmi.twitch.tv 001 justinfan123 :Welcome'))
        self.assertEqual(twitch.reaction(['KEKW', 'kekw bro', 'nice']), 'KEKW')
        self.assertEqual(twitch.reaction(['nice', 'ok']), '')

    def test_chat_spike_lands_before_the_reaction(self):
        from clipper import twitch
        t0 = 1_000_000.0
        chat = [{'t': t0 + i * 5, 'u': 'a', 'm': 'hi'} for i in range(120)]             # one message per 5 s
        chat += [{'t': t0 + 300 + k * 0.4, 'u': f'u{k}', 'm': 'KEKW'} for k in range(12)]  # 12 in 5 s at +300 s
        spikes = twitch.chat_spikes(sorted(chat, key=lambda c: c['t']), start=t0 + 100, end=t0 + 700, delay=10)
        self.assertEqual(len(spikes), 1)
        a, b, note = spikes[0]
        self.assertAlmostEqual(a, 190, delta=5)               # 300 s - 10 s delay - 100 s piece start
        self.assertIn('chat exploded', note)
        self.assertIn('KEKW', note)
        self.assertEqual(twitch.chat_spikes([], t0, t0 + 600), [])

    def test_viewer_clips(self):
        from clipper import twitch
        t0 = 2_000_000.0
        clips = [{'created': t0 + 100, 'duration': 30}, {'created': t0 + 110, 'duration': 30},
                 {'created': t0 + 900, 'duration': 30}]                                # the last one: another piece
        marks = twitch.clip_marks(clips, t0, t0 + 600, delay=10)
        self.assertEqual(len(marks), 1)
        a, b, note = marks[0]
        self.assertEqual((a, b), (60.0, 100.0))
        self.assertIn('x2', note)

    def test_obs_pieces(self):
        import os
        import time
        from clipper import live
        from datetime import datetime
        self.assertEqual(live.piece_start('/x/2026-11-19 00-10-03.mkv'), datetime(2026, 11, 19, 0, 10, 3).timestamp())
        with tempfile.TemporaryDirectory() as d:
            a, b = Path(d) / '2026-11-19 00-00-00.mkv', Path(d) / '2026-11-19 00-10-00.mkv'
            a.write_bytes(b'x' * 10)
            b.write_bytes(b'y' * 10)
            os.utime(a, (time.time() - 50, time.time() - 50))
            (Path(d) / 'notes.txt').write_text('not a video')
            sizes = {}
            self.assertEqual(live.finished_pieces(d, 0, sizes), [a])                  # the newest is still recording
            now = time.time()
            self.assertEqual(live.finished_pieces(d, 0, sizes, now=now + live.IDLE_S + 1), [a, b])  # stream ended

    def test_twitch_notes_are_hints(self):
        from clipper import hints
        self.assertEqual(hints.strip_hints('kya hua [chat exploded ~15 s: KEKW] [viewers clipped this x2]').split(),
                         ['kya', 'hua'])
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / 'transcript').mkdir()
            (Path(d) / 'transcript' / 'twitch.json').write_text('[[10.0, 25.0, "[viewers clipped this]"]]')
            self.assertEqual(hints.twitch_events(Path(d)), [(10.0, 25.0, '[viewers clipped this]')])
            self.assertEqual(hints.twitch_events(Path(d) / 'nothing'), [])

    def test_heavy_steps_step_aside_for_obs(self):
        import os
        import time
        from unittest import mock
        import run
        with tempfile.TemporaryDirectory() as d:
            with mock.patch.object(run, 'ROOT', Path(d)):
                self.assertFalse(run.live_running())
                hb = Path(d) / 'output' / '_live' / 'gta6'
                hb.mkdir(parents=True)
                (hb / 'heartbeat').write_text(str(time.time()))
                self.assertTrue(run.live_running())
                (hb / 'heartbeat').write_text(str(time.time() - 600))                 # a session that stopped
                self.assertFalse(run.live_running())
        self.assertIn('edit', run.HEAVY)
        self.assertNotIn('live', run.HEAVY)


class BoldClips(unittest.TestCase):
    """Nothing censored, bold takes count extra (the owner's choice, 2026-11-19): the blind critic learns the
    choice from one line in its packet, and "bold_clips": "neutral" leaves it out (the critic's old rule)."""

    def packet(self, setting):
        import contextlib
        import io
        from unittest import mock
        from clipper import common, critic, sound
        words = (sentence('honestly most fitness advice on youtube is complete garbage and you know it.', 0.0)
                 + sentence('bhai sach bolun toh ye log sirf paise ke liye bolte hain yaar.', 5.0))
        lines = [{'s': words[0]['s'], 'e': words[12]['e'], 'text': ' '.join(w['w'] for w in words[:13])},
                 {'s': words[13]['s'], 'e': words[-1]['e'], 'text': ' '.join(w['w'] for w in words[13:])}]
        with tempfile.TemporaryDirectory() as d:
            pdir = Path(d) / 'output' / 'bold-test'
            (pdir / 'transcript').mkdir(parents=True)
            (pdir / 'transcript' / 'words.json').write_text(json.dumps(words))
            (pdir / 'transcript' / 'sentences.json').write_text(json.dumps(lines))
            (pdir / 'project.json').write_text(json.dumps({'language': 'en', 'duration': 12.0}))
            (pdir / 'clips.json').write_text(json.dumps({'clips': [
                {'title': 'Fitness advice is garbage', 'ranges': [[0.0, words[12]['e']]]},
                {'title': 'Sirf paise ke liye', 'ranges': [[words[13]['s'], words[-1]['e']]]}]}))
            saved = common.settings
            common.settings = lambda: dict(common.DEFAULT_SETTINGS, **setting)
            try:
                with mock.patch.object(sound, 'ensure', return_value=None), \
                        contextlib.redirect_stdout(io.StringIO()):
                    critic.prepare(pdir, 'clips', 1)
            finally:
                common.settings = saved
            return (pdir / 'critic' / 'run-1.txt').read_text(encoding='utf-8')

    def test_boost_note_in_the_critic_packet_by_default(self):
        from clipper import common
        self.assertEqual(common.DEFAULT_SETTINGS['bold_clips'], 'boost')
        text = self.packet({})
        self.assertIn('# Bold takes: BOOST', text)
        self.assertIn('caste slur on its own earns nothing', text)
        self.assertIn('fitness advice', text)                  # the clips are still there, word for word

    def test_neutral_leaves_the_critic_packet_as_before(self):
        self.assertNotIn('Bold takes', self.packet({'bold_clips': 'neutral'}))
        self.assertNotIn('Bold takes', self.packet({'bold_clips': False}))

    def test_readers_and_the_live_helper_get_the_same_choice(self):
        from clipper import common
        saved = common.settings
        try:
            common.settings = lambda: dict(common.DEFAULT_SETTINGS)
            self.assertIn('strong-claim', common.bold_note('reader'))
            self.assertIn('bold takes count extra', common.bold_note('live'))
            common.settings = lambda: dict(common.DEFAULT_SETTINGS, bold_clips='neutral')
            self.assertEqual(common.bold_note('reader'), '')
            self.assertEqual(common.bold_note('live'), '')
        finally:
            common.settings = saved


class StarredWords(unittest.TestCase):
    """Rude words with stars in the text only (the owner's choice, 2026-11-19): "F******" in the captions and
    posting texts; the sound and the transcript keep every word; "star_words": false shows them in full."""

    def caption_text(self, **meta_extra):
        meta = meta_for(sentence('what the fuck is this chutiya plan yaar.', 0.0))
        meta.update(meta_extra)
        return ' '.join(w['text'] for g in plan.caption_groups(meta) for w in g['words'])

    def test_captions_get_stars(self):
        self.assertEqual(self.caption_text(star_words=True), 'WHAT THE F*** IS THIS C****** PLAN YAAR')
        self.assertIn('P***', self.caption_text(star_words=True, stars=['plan']))       # a word Claude marked
        self.assertEqual(self.caption_text(), 'WHAT THE FUCK IS THIS CHUTIYA PLAN YAAR')  # a bare plan: in full
        self.assertEqual(self.caption_text(star_words=False), 'WHAT THE FUCK IS THIS CHUTIYA PLAN YAAR')

    def test_hinglish_caption_and_devanagari(self):
        from clipper import stars
        w = sentence('ye banda', 0.0) + [W('chutiya', 0.8, 1.2, orig='चूतिया')]
        meta = meta_for(w)
        meta['star_words'] = True
        caps = ' '.join(x['text'] for g in plan.caption_groups(meta) for x in g['words'])
        self.assertEqual(caps, 'YE BANDA C******')
        self.assertEqual(stars.star('चूतिया'), 'चू**')
        self.assertEqual(stars.star('fucking!'), 'f******!')

    def test_harmless_words_stay(self):
        from clipper import stars
        for word in ('chodo', 'chhodo', 'गाड़ी', 'लड़ाई', 'ganda', 'Dickens', 'cocktail', 'Gandhi', 'class',
                     'assessment', 'saala', 'sex'):
            self.assertFalse(stars.is_rude(word), word)

    def test_posting_texts(self):
        from clipper import stars
        self.assertEqual(stars.star_text('Ye banda poora chutiya hai, what the fuck | GTA 6 Hindi #Shorts'),
                         'Ye banda poora c****** hai, what the f*** | GTA 6 Hindi #Shorts')
        self.assertEqual(stars.star_text('Already F****** starred'), 'Already F****** starred')
        self.assertTrue(stars.on({}) and not stars.on({'star_words': False}))

    def test_post_json_gets_stars(self):
        import contextlib
        import io
        from clipper import common, post
        clip = {'id': 1, 'title': 'Chutiya plan', 'ranges': [[0.0, 20.0]], 'caption': 'what the fuck #gta6',
                'stars': ['cheater'],
                'post': {'youtube': {'title': 'Ye cheater nikla, what the fuck | GTA 6 #Shorts', 'description': 'x'},
                         'instagram': {'caption': 'Bhenchod kya scene hai'}}}
        with tempfile.TemporaryDirectory() as d:
            pdir = Path(d)
            (pdir / 'edited').mkdir()
            (pdir / 'edited' / '01-chutiya-plan.mp4').write_bytes(b'')
            (pdir / 'clips.json').write_text(json.dumps({'clips': [clip]}))
            (pdir / 'project.json').write_text('{}')
            saved = common.settings
            try:
                for on, want in ((None, 'Ye c****** nikla, what the f*** | GTA 6 #Shorts'),
                                 (False, 'Ye cheater nikla, what the fuck | GTA 6 #Shorts')):
                    common.settings = lambda: dict(common.DEFAULT_SETTINGS, **({} if on is None else {'star_words': on}))
                    with contextlib.redirect_stderr(io.StringIO()), contextlib.redirect_stdout(io.StringIO()):
                        kit, _ = post.build(pdir)
                    c = kit['clips'][0]
                    self.assertEqual(c['text']['youtube']['title'], want)
                    if on is None:
                        self.assertEqual((c['title'], c['caption'], c['text']['instagram']['caption']),
                                         ('C****** plan', 'what the f*** #gta6', 'B******* kya scene hai'))
            finally:
                common.settings = saved


if __name__ == '__main__':
    unittest.main()


class FacecamFinder(unittest.TestCase):
    """v2.7: a rectangular cam with two people in it (they move and look down, so no single face stays put)."""

    @staticmethod
    def frames(with_box=True, n=24, seed=1):
        import numpy as np
        rng = np.random.default_rng(seed)
        out = []
        for _ in range(n):
            f = rng.integers(0, 140, (360, 640, 3), dtype=np.uint8)            # the game: changes every frame
            if with_box:
                f[140:230, 486:640] = rng.integers(170, 230, (90, 154, 3), dtype=np.uint8)   # the cam: a bright room
            out.append(f)
        return out

    @staticmethod
    def faces(n=24, seed=2):
        import numpy as np
        rng = np.random.default_rng(seed)
        per = []
        for i in range(n):                    # two people side by side, leaning; often nobody is found
            fs = []
            if i % 3:
                fs.append((520 + rng.uniform(-14, 14), 170 + rng.uniform(-6, 6), 26.0))
            if i % 2:
                fs.append((600 + rng.uniform(-14, 14), 172 + rng.uniform(-6, 6), 25.0))
            per.append(fs)
        return per

    def test_two_people_cam_found_by_its_border(self):
        from clipper import facecam
        box = facecam.framed_box(self.frames(), self.faces(), 640, 360)
        self.assertIsNotNone(box)
        self.assertEqual(box['shape'], 'rect')
        self.assertAlmostEqual(box['x'], 486, delta=3)
        self.assertAlmostEqual(box['y'], 140, delta=3)
        self.assertAlmostEqual(box['y'] + box['h'], 230, delta=3)

    def test_two_person_finder_only_for_gameplay_and_streams(self):
        # v2.7: a podcast recorded in boxes must never be taken for a webcam (it would then count as gameplay)
        import numpy as np
        from unittest import mock
        from clipper import facecam, kind
        rng = np.random.default_rng(5)                 # people moving about the whole box, as on the GTA stream
        frames = self.frames()
        faces = [[(float(rng.uniform(500, 625)), float(170 + rng.uniform(-6, 6)), 26.0)] if i % 3 else []
                 for i in range(24)]
        with mock.patch.object(facecam, '_sample', return_value=frames), \
                mock.patch.object(facecam, '_faces_px', side_effect=faces):
            self.assertIsNone(facecam.detect('v.mp4', 600, 640, 360))                 # a normal video: no
        with mock.patch.object(facecam, '_sample', return_value=frames), \
                mock.patch.object(facecam, '_faces_px', side_effect=faces):
            self.assertIsNotNone(facecam.detect('v.mp4', 600, 640, 360, framed=True))  # gameplay / a stream: yes
        self.assertEqual(kind.stream_hint({'title': 'Figuring Out with Khan Sir', 'source': 'https://youtu.be/x'}), [])
        self.assertTrue(kind.stream_hint({'title': 'GTA 6 day one', 'source': 'https://youtu.be/x'}))
        self.assertTrue(kind.stream_hint({'title': 'Chill evening', 'source': 'https://www.twitch.tv/videos/1'}))
        self.assertTrue(kind.stream_hint({'title': 'x', 'categories': ['Gaming']}))

    def test_no_box_no_cam(self):
        # people near a side but no fixed box around them (a normal video): never taken for a cam
        from clipper import facecam
        self.assertIsNone(facecam.framed_box(self.frames(with_box=False), self.faces(), 640, 360))

    @staticmethod
    def low_faces(n=24, seed=3):
        # as on the stream, scaled to these frames: one friend higher, one low in the cam (centres 531-620 of a
        # 410-670 cam, faces 87 px)
        import numpy as np
        rng = np.random.default_rng(seed)
        per = []
        for i in range(n):
            fs = []
            if i % 2:
                fs.append((530 + rng.uniform(-10, 10), 180 + rng.uniform(-2, 2), 29.0))
            if i % 3:
                fs.append((600 + rng.uniform(-10, 10), 210 + rng.uniform(-2, 2), 29.0))
            per.append(fs)
        return per

    def test_game_edge_below_the_cam_is_not_its_border(self):
        # 2026-11-21, a GTA 6 stream: the friends sat low in the cam, so the bottom border was searched below them
        # and a fixed line of the game 200 px lower was taken for it; the 16:9 cam came out square and the layout
        # shrank the faces. The box now ends at the cam's own border, where a 16:9 picture ends.
        from clipper import facecam
        frames = self.frames()
        for f in frames:
            f[296:300, 486:640] = 250                        # a fixed bright line of the game below the cam
        box = facecam.framed_box(frames, self.low_faces(), 640, 360)
        self.assertIsNotNone(box)
        self.assertAlmostEqual(box['y'], 140, delta=3)
        self.assertAlmostEqual(box['y'] + box['h'], 230, delta=3)      # was 296: the game line
        self.assertFalse(facecam.is_tall(box))

    def test_a_line_in_the_room_above_the_faces_is_not_a_border(self):
        # a tall cam with a shelf across it, the people below the shelf: the shelf is never taken for the border
        import numpy as np
        from clipper import facecam
        rows = np.full(359, 1.0)
        rows[139], rows[229], rows[299] = 40.0, 40.0, 40.0              # top border, a shelf, bottom border
        self.assertEqual(facecam.camera_shape(rows, 154, 140, 300, True, True, (245, 270)), (140, 300))
        self.assertEqual(facecam.camera_shape(rows, 154, 140, 300, True, True, (170, 215)), (140, 230))
        self.assertEqual(facecam.camera_shape(rows, 154, 140, 228, True, True, (170, 215)), (140, 228))   # 16:9 already
        self.assertTrue(facecam.is_tall({'shape': 'rect', 'w': 154, 'h': 160}))
        self.assertFalse(facecam.is_tall({'shape': 'circle', 'w': 154, 'h': 154}))

    def test_cam_fills_its_panel_up_to_the_margins(self):
        # the owner's choice, 2026-11-21: 50 px free left, right and top (captions), 30 px at the bottom; the cam
        # grows evenly until one side reaches them (a 16:9 cam fills the width, a round or 4:3 one the height)
        from clipper import facecam
        from clipper.common import DEFAULT_SETTINGS
        m = facecam.margins(DEFAULT_SETTINGS['facecam_margins'])
        self.assertEqual(m, {'left': 50, 'right': 50, 'top': 50, 'bottom': 30})
        wide = facecam.geometry({'x': 1458, 'y': 410, 'w': 462, 'h': 260, 'shape': 'rect'}, 1920, 1080, m)
        self.assertEqual((wide['cam_w'], wide['cam_h'], wide['cam_x'], wide['cam_y']), (980, 550, 50, 120))
        rnd = facecam.geometry({'x': 1500, 'y': 400, 'w': 300, 'h': 300, 'shape': 'circle'}, 1920, 1080, m)
        self.assertEqual((rnd['cam_w'], rnd['cam_h'], rnd['cam_y']), (690, 690, 50))
        before = facecam.margins({'left': 60, 'right': 60, 'top': 90, 'bottom': 30})     # the way back
        old = facecam.geometry({'x': 1458, 'y': 410, 'w': 462, 'h': 260, 'shape': 'rect'}, 1920, 1080, before)
        self.assertEqual((old['cam_w'], old['cam_h'], old['cam_x'], old['cam_y']), (958, 540, 61, 145))   # as v2.7.1
        self.assertEqual(facecam.margins([60, 60, 90, 30]), before)
        self.assertEqual(facecam.margins({'top': 'x', 'left': 20}), {'left': 20, 'right': 50, 'top': 50, 'bottom': 30})
        self.assertEqual(facecam.geometry({'x': 1458, 'y': 410, 'w': 462, 'h': 260, 'shape': 'rect'}, 1920, 1080), wide)

    def test_doubtful_box_gets_a_picture(self):
        import subprocess
        import tempfile
        from pathlib import Path
        from clipper import facecam
        with tempfile.TemporaryDirectory() as d:
            v = Path(d) / 'v.mp4'
            subprocess.run(['ffmpeg', '-v', 'error', '-y', '-f', 'lavfi', '-i', 'color=gray:s=640x360:d=1', str(v)],
                           check=True)
            out = facecam.box_sheet(v, {'x': 486, 'y': 140, 'w': 154, 'h': 160}, 0.5, Path(d) / 'f' / 'box.jpg')
            self.assertTrue(out.exists())


class SoundTiming(unittest.TestCase):
    """v2.7: a mood sound never starts before its moment (clip 159: a trombone started 1 s before the crash)."""

    @staticmethod
    def cues(peak, onset):
        from unittest import mock
        from clipper import plan
        sound = {'file': 's.mp3', 'path': 'sounds/fail/s.mp3', 'variant': 0, 'start': 0.0, 'length': 2.6, 'peak': peak,
                 'norm_db': 0.0}
        with mock.patch.object(plan.sfxlib, 'pick', side_effect=lambda role, *a, **k: None if role == 'whoosh' else sound):
            out = plan.sfx_cues([], [], 20.0, moods=[(5.0, 'fail')], onset=onset)
        return [c for c in out if c['role'] == 'fail'][0]['at']

    def test_slow_sound_starts_on_the_moment(self):
        self.assertAlmostEqual(self.cues(1.06, 'moment'), 4.9, places=3)     # was 3.94: a second early
        self.assertAlmostEqual(self.cues(1.06, 'peak'), 3.94, places=3)      # "sound_onset": "peak": as before

    def test_quick_sound_lands_as_before(self):
        self.assertAlmostEqual(self.cues(0.02, 'moment'), 4.98, places=3)
        self.assertAlmostEqual(self.cues(0.02, 'peak'), 4.98, places=3)


class FrameSheets(unittest.TestCase):
    """v2.7, gameplay and streams only: frame sheets, close-ups where the readers point, clips from the event."""

    def test_only_for_gameplay_and_streams(self):
        from clipper import watch
        self.assertFalse(watch.wanted({'title': 'Figuring Out with Khan Sir', 'video_kind': {}}, {})[0])
        self.assertTrue(watch.wanted({'title': 'x', 'video_kind': {'live': True}}, {})[0])
        self.assertTrue(watch.wanted({'title': 'GTA 6 day one gameplay', 'video_kind': {}}, {})[0])
        self.assertFalse(watch.wanted({'video_kind': {'live': True}}, {'watch_gameplay': False})[0])   # way back
        # v2.7.1 review: a game or console in the title of a podcast or a review is not gameplay
        self.assertFalse(watch.wanted({'title': 'PS5 Pro review in Hindi', 'video_kind': {}}, {})[0])
        self.assertFalse(watch.wanted({'title': 'Gaming addiction in kids | Doctor podcast', 'video_kind': {}}, {})[0])
        self.assertTrue(watch.wanted({'title': 'x', 'source': 'https://www.twitch.tv/videos/1', 'video_kind': {}}, {})[0])

    def test_sheet_of_21_frames_with_marks(self):
        import cv2
        import numpy as np
        from clipper import watch
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            tiles = []
            for k in range(21):
                f = d / f'f{k:02d}.jpg'
                cv2.imwrite(str(f), np.full((180, 320, 3), 90, np.uint8))
                tiles.append((f, f'0:00:{k * 10:02d}', k == 4, 'bhaag' if k == 5 else '', False))
            out = watch.compose(tiles, d / 'sheet.jpg')
            img = cv2.imread(str(out))
            self.assertEqual(img.shape[:2], (3 * watch.TILE_H, 7 * watch.TILE_W))      # 7 across, 3 down
            b, g, r = img[watch.TILE_H // 2, 4 * watch.TILE_W + 2]                        # frame 5's left border
            self.assertGreater(int(r), 150)
            self.assertLess(int(b), 100)                                                  # red: the sound jumps

    def test_red_border_only_on_the_loudest(self):
        # a stream with friends is loud everywhere: at a fixed 6 dB, 53 % of the GTA stream's frames were red
        import numpy as np
        from clipper import watch
        rng = np.random.default_rng(3)
        loud_stream = rng.uniform(4, 14, 3600).astype(np.float32)
        level = watch.loud_level(loud_stream)
        slots = [loud_stream[t:t + 10].max() for t in range(0, 3600, 10)]
        self.assertAlmostEqual(np.mean(np.array(slots) >= level), watch.LOUD_SHARE, delta=0.03)
        self.assertEqual(watch.loud_level(np.zeros(600, np.float32)), watch.LOUD_DB)      # a calm video: the floor

    def test_spots_merged_and_events_collected(self):
        from clipper import watch
        with tempfile.TemporaryDirectory() as d:
            pdir = Path(d)
            (pdir / 'parts').mkdir()
            (pdir / 'frames').mkdir()
            (pdir / 'parts' / 'part-01.json').write_text(json.dumps({'look_closer': [
                {'at': 100, 'where': 'game', 'why': 'fire'}, {'at': 108, 'where': 'game', 'why': 'running'},
                {'at': 300, 'where': 'webcam', 'why': 'someone falls'}]}))
            spots = watch.requests(pdir)
            self.assertEqual([(s['at'], s['where']) for s in spots], [(100.0, 'game'), (300.0, 'webcam')])
            (pdir / 'frames' / 'spots.json').write_text(json.dumps(spots))
            (pdir / 'frames' / 'zoom-batch-01.json').write_text(json.dumps([
                {'spot': 1, 'verdict': 'clip', 'event_at': 98, 'end': 130, 'title': 'Aag', 'why': 'bike fire'},
                {'spot': 2, 'verdict': 'no', 'event_at': None, 'end': None}]))
            events = watch.collect(pdir)
            self.assertEqual([(e['event_at'], e['end'], e['where']) for e in events], [(98.0, 130.0, 'game')])

    def test_clips_start_at_their_event(self):
        from unittest import mock
        from clipper import watch
        with tempfile.TemporaryDirectory() as d:
            pdir = Path(d)
            (pdir / 'frames').mkdir()
            (pdir / 'project.json').write_text('{}')
            (pdir / 'clips.json').write_text(json.dumps({'clips': [
                {'id': 1, 'ranges': [[110.0, 140.0]]},                       # starts on the reaction
                {'id': 2, 'ranges': [[500.0, 540.0]]}]}))                    # shows its event already
            (pdir / 'frames' / 'events.json').write_text(json.dumps([
                {'spot': 1, 'event_at': 100.0, 'end': 140.0, 'where': 'game', 'title': 'A', 'why': ''},
                {'spot': 2, 'event_at': 510.0, 'end': 530.0, 'where': 'game', 'title': 'B', 'why': ''},
                {'spot': 3, 'event_at': 900.0, 'end': 925.0, 'where': 'webcam', 'title': 'C', 'why': 'chair'}]))
            with mock.patch.object(watch, '_video', return_value=Path('v.mp4')), \
                    mock.patch.object(watch, 'exact_sheet') as sheet:
                done = watch.apply_events(pdir)
            self.assertEqual([w for w, _, _ in done], ['starts at its event', 'already shows it', 'new clip'])
            clips = json.loads((pdir / 'clips.json').read_text())['clips']
            self.assertEqual((clips[0]['ranges'][0][0], clips[0]['event_at']), (98.5, 100.0))
            self.assertEqual((clips[2]['id'], clips[2]['ranges'], clips[2]['event_where']), (3, [[898.5, 925.0]], 'webcam'))
            self.assertEqual(sheet.call_count, 2)                            # an exact-frame sheet for each
            done = watch.apply_events(pdir, dry=True)                         # run again: nothing moves twice
            self.assertEqual([w for w, _, _ in done], ['already shows it'] * 3)

    def test_the_event_plays_whole(self):
        # pause cutting leaves the event's first seconds alone; the talk after it is tightened as usual
        words = [W('Are', 105.0, 105.3), W('bhaag', 107.5, 107.9), W('bhaag', 109.5, 109.9),
                 W('phir', 115.0, 115.3), W('bike', 116.5, 116.8), W('phat', 118.0, 118.3), W('gayi', 118.4, 118.7)]
        clip = {'ranges': [[98.5, 119.0]], 'event_at': 100.0}
        out = cut.with_jump_cuts(clip, words, {}, True)
        self.assertTrue(out['ranges'][0][0] == 98.5 and out['ranges'][0][1] > 109.9)      # 98.5 to past "bhaag bhaag"
        self.assertGreater(len(out['ranges']), 1)                                          # later pauses still cut
        plain = cut.with_jump_cuts({'ranges': [[98.5, 119.0]]}, words, {}, True)
        self.assertLess(plain['ranges'][0][1], 109.0)                                     # without an event: cut
        r = cut.snap_piece(clip, 98.5, out['ranges'][0][1], words)
        self.assertEqual(r[0], 98.5)                                                       # starts on the event


class NormalVideosUntouched(unittest.TestCase):
    """v2.7 release check: everything new for gameplay and streams stays off for a normal video (a podcast, a talk),
    so it does no extra work there and nothing v2.6 did changes for it (the owner's rule: only upgrades)."""

    PODCAST = {'title': 'Figuring Out with Khan Sir | Episode 12', 'source': 'https://youtu.be/abc',
               'categories': ['People & Blogs'], 'live_status': 'not_live', 'language': 'hinglish',
               'video_kind': {'live': False, 'gaming': False, 'facecam': False}}

    def test_no_gameplay_work_on_a_podcast(self):
        from unittest import mock
        from clipper import common, gpu, hearing, kind, voices, watch
        p = self.PODCAST
        self.assertEqual(kind.stream_hint(p), [])                                   # not taken for a stream
        self.assertFalse(watch.wanted(p, {})[0])                                    # no frame sheets
        with mock.patch.object(gpu, 'cuda_device_count', return_value=1):
            self.assertFalse(hearing.wanted(p, {})[0])                              # no careful listening
        with mock.patch.object(common, 'settings', return_value={}):
            self.assertEqual(common.overlap_mode(p), 'avoid')                       # one clip per moment, as in v2.6
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(voices.game_words(Path(d), p, [W('hello', 0.0, 0.4)]), set())   # no game-voice rule
