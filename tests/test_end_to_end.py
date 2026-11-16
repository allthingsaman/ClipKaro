"""One tiny made-up video, start to end: cut -> edit -> qa (roadmap item 18).

The other tests check the pieces one by one; this one runs the real commands on an 8-second video
that ffmpeg draws (a moving test picture and a tone), with a transcript written by hand, so a break
anywhere in the chain shows up before a real video does. No speech model, no internet: about 15-30 s.
Skipped when ffmpeg isn't installed.
"""
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def W(text, s, e):
    return {'w': text, 's': round(s, 3), 'e': round(e, 3), 'p': 0.95}


def sentence(text, start, gap=0.08, dur=0.3):
    out, t = [], start
    words = text.split()
    for i, w in enumerate(words):
        out.append(W(w + ('.' if i == len(words) - 1 else ''), t, t + dur))
        t += dur + gap
    return out


def run(*args, brand=None):
    import os
    # your brand folder stays out of the test (an empty one), unless the test brings its own
    env = dict(os.environ, CLIPKARO_BRAND=str(brand or Path(tempfile.gettempdir()) / 'clipkaro-no-brand'))
    r = subprocess.run([sys.executable, str(ROOT / 'run.py'), *args], cwd=ROOT, capture_output=True, text=True,
                       encoding='utf-8', errors='replace', timeout=600, env=env)
    return r.returncode, r.stdout + r.stderr


@unittest.skipUnless(shutil.which('ffmpeg') and shutil.which('ffprobe'), 'no ffmpeg')
class EndToEnd(unittest.TestCase):
    def test_tiny_video_cut_edit_qa(self):
        with tempfile.TemporaryDirectory() as d:
            pdir = Path(d) / 'tiny-test-video'
            (pdir / 'source').mkdir(parents=True)
            (pdir / 'transcript').mkdir()
            video = pdir / 'source' / 'video.mp4'
            subprocess.run(['ffmpeg', '-v', 'error', '-f', 'lavfi', '-i', 'testsrc2=s=640x360:r=25:d=8',
                            '-f', 'lavfi', '-i', 'sine=f=220:d=8:sample_rate=44100', '-shortest',
                            '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-c:a', 'aac', str(video)], check=True)
            # a pause of 1.2 s inside the clip (a jump cut) and "um" (a filler, cut out)
            words = sentence('so this is the first point', 0.5) + sentence('and here is the second one', 4.0) \
                + [W('um', 6.4, 6.6)] + sentence('the end', 6.75)
            (pdir / 'transcript' / 'words.json').write_text(json.dumps(words), encoding='utf-8')
            (pdir / 'project.json').write_text(json.dumps({
                'kind': 'local', 'source': str(video), 'video': str(video), 'title': 'Tiny test video',
                'duration': 8, 'width': 640, 'height': 360, 'language': 'en', 'facecam': False}), encoding='utf-8')
            (pdir / 'clips.json').write_text(json.dumps({'clips': [{
                'id': 1, 'title': 'Tiny test clip', 'ranges': [[0.4, 7.6]], 'hook': 'so this is the first point',
                'emphasis': ['first', 'second'], 'clip_score': 7, 'caption': 'A tiny test clip #test'}]}),
                encoding='utf-8')

            code, out = run('cut', str(pdir))
            self.assertEqual(code, 0, out)
            self.assertIn('jump cuts:', out)                     # the pause and the "um" were cut out
            raw = sorted((pdir / 'clips').glob('01-*.mp4'))
            self.assertEqual(len(raw), 1, out)
            meta = json.loads(raw[0].with_suffix('.json').read_text(encoding='utf-8'))
            self.assertNotIn('um', [w['w'] for w in meta['words']])
            self.assertLess(meta['duration'], 7.2 - 1.0)          # shorter than the range by the cuts

            code, out = run('edit', str(pdir), '--workers', '1')
            self.assertEqual(code, 0, out)
            edited = sorted((pdir / 'edited').glob('01-*.mp4'))
            self.assertEqual(len(edited), 1, out)
            self.assertTrue(edited[0].with_suffix('.srt').exists())
            probe = subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries',
                                    'stream=width,height', '-of', 'csv=p=0', str(edited[0])],
                                   capture_output=True, text=True)
            self.assertEqual(probe.stdout.strip(), '1080,1920')

            code, out = run('qa', str(pdir))
            self.assertEqual(code, 0, out)                       # nothing to fix
            self.assertIn('0 to fix', out)

            # v2.4: a logo, an outro and the credit (as for a YouTube link): the outro comes after the clip,
            # and the quality check still finds nothing to fix
            kit = Path(d) / 'brand'
            kit.mkdir()
            subprocess.run(['ffmpeg', '-v', 'error', '-f', 'lavfi', '-i', 'color=c=blue:s=200x200', '-frames:v', '1',
                            str(kit / 'logo.png')], check=True)
            subprocess.run(['ffmpeg', '-v', 'error', '-f', 'lavfi', '-i', 'color=c=black:s=1080x1920:r=30:d=3',
                            '-f', 'lavfi', '-i', 'sine=f=440:d=3:sample_rate=48000', '-shortest', '-c:v', 'libx264',
                            '-pix_fmt', 'yuv420p', '-c:a', 'aac', str(kit / 'outro.mp4')], check=True)
            proj = json.loads((pdir / 'project.json').read_text(encoding='utf-8'))
            proj.update(kind='youtube', channel='Test Channel')
            (pdir / 'project.json').write_text(json.dumps(proj), encoding='utf-8')
            code, out = run('edit', str(pdir), '--workers', '1', brand=kit)
            self.assertEqual(code, 0, out)
            self.assertIn('credit "© Test Channel"', out)
            dur = float(subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of',
                                        'csv=p=0', str(edited[0])], capture_output=True, text=True).stdout)
            self.assertAlmostEqual(dur, meta['duration'] + 3.0, delta=0.25)
            code, out = run('qa', str(pdir))
            self.assertEqual(code, 0, out)
            self.assertIn('0 to fix', out)


if __name__ == '__main__':
    unittest.main()
