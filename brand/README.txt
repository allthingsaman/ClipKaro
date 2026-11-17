YOUR BRAND ON EVERY CLIP
========================

Put up to two files in this folder. ClipKaro adds them to every clip it edits from then on.

logo.png     Your logo. It goes right in the bottom-right corner (no gap), small and 70% visible
             (a little see-through), for the whole clip.
             - A PNG with a see-through background looks best (JPG and WebP work too). A logo on a
               plain square (black, white, one colour) gets that background removed by itself, so
               only the logo shows; "logo_background": "keep" in settings.json leaves it as it is.
             - Any size: ClipKaro makes it about 120 px tall (up to 220 px wide for a wide logo).

outro.mp4    Your outro: a short video added after the end of every clip.
             - Standing, 9:16 (1080 x 1920 is best). Other shapes are fitted over a blurred copy.
             - 3 to 5 seconds is ideal. Longer than 5 s: ClipKaro warns you. Longer than 10 s:
               it is left out, so an outro is never longer than the clip itself.
             - Its sound is evened out to the clip's volume. MOV, MKV and WebM work too.

There is no intro on purpose: a clip must open on its hook.

Another corner? In settings.json, "logo_corner" and "credit_corner" can each be "top-left",
"top-right", "bottom-left" or "bottom-right" (normally the logo bottom right, the credit bottom left).

Turning them off
- For one video, tell Claude "no logo" or "no outro".
- For good, take the file out of this folder, or set "logo": false / "outro": false in settings.json.

The "(c) Channel name" credit in the bottom-left corner is separate: it is added by itself to clips
made from a YouTube link (never to your own video files). Turn it off with "source_credit": false in
settings.json, or say "no credit" for one video.

The files you put here are yours: they are never uploaded or committed to GitHub.
