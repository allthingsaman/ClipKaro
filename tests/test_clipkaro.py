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
        self.assertEqual(rows, [(10.0, 'Franklin ko saari.', 'फ्रैंक्लिन को सारी।')])   # no made-up word, no game line


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

    def test_gameplay_keeps_long_quiet(self):
        words = sentence('so this is the first point', 0.0) + sentence('and here is the second one', 5.0)
        quiet = words[6]['s'] - words[5]['e']                                  # 2.8 s of gameplay
        self.assertGreater(quiet, cut.GAME_PAUSE)
        self.assertEqual(len(cut.jump_pieces(0.0, words[-1]['e'], words, lambda a, b: True, cut.GAME_PAUSE)), 1)
        self.assertEqual(len(cut.jump_pieces(0.0, words[-1]['e'], words, lambda a, b: True)), 2)


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
            left = [x['id'] for x in more.unused(p)]
            self.assertEqual(left, ['p1-c2', 'p2-c1'])     # C overlaps the better B


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


if __name__ == '__main__':
    unittest.main()
