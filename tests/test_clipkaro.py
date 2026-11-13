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
