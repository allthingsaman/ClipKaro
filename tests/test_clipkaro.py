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


if __name__ == '__main__':
    unittest.main()
