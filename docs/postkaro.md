# PostKaro: posting your clips

**ClipKaro makes the clips; PostKaro posts them.** PostKaro is ClipKaro's partner app. It posts your
finished clips to **YouTube Shorts**, **Instagram Reels** and your **Facebook Page**, from your own
computer:
- **free**;
- **no posting service in between**;
- **your logins stay encrypted on your computer**.

It lives in its own folder, from its own repository:
[github.com/allthingsaman/PostKaro](https://github.com/allthingsaman/PostKaro).

**On this page**
1. [How it fits with ClipKaro](#how-it-fits-with-clipkaro)
2. [Install it (once)](#install-it-once)
3. [Opening PostKaro: the link with a key](#opening-postkaro-the-link-with-a-key)
4. [Connect your accounts (once)](#connect-your-accounts-once)
5. [Several pages or channels: the default account](#several-pages-or-channels-the-default-account)
6. [Posting your clips](#posting-your-clips) (every video)
7. [Live clipping](#live-clipping)
8. [Keeping it working](#keeping-it-working), [commands](#commands) and
   [when something doesn't work](#when-something-doesnt-work)

## How it fits with ClipKaro
```
ClipKaro: "clip this video: <link>"
   → finished clips in output/<video>/edited/, each with a title and caption for every platform
   → ends with a "Post them" link
          │
          ▼
PostKaro (a page in your browser, running on your own computer)
   → every clip already filled in: YouTube title and description, Instagram caption, Facebook caption
   → you check, change what you like, pick times (or "Plan for me"), press Schedule
          │
          ▼
YouTube Shorts, Instagram Reels, your Facebook Page: each post ends up as a live link
```
For [live clipping](live-clipping.md) there is no page and no review: each clip is posted at once.

## Install it (once)
Put PostKaro **next to** the ClipKaro folder, not inside it, and use the same Python as for ClipKaro
(3.11 or newer).

**The easy way:** in Claude Code, inside the ClipKaro folder, say **"install PostKaro too"**.

**By hand** (Windows; on a Mac use `python3.13`, on Linux `python3`):
```powershell
cd ..                                   # the folder that holds ClipKaro
git clone https://github.com/allthingsaman/PostKaro.git
cd PostKaro
python install.py
python run.py open
```
`install.py`:
- makes PostKaro's own private Python (`.venv`);
- sets PostKaro to **start by itself when you log in** (Windows: a login entry for your user, no
  admin rights; Mac: a login item; Linux: a systemd user service). That keeps the "Post them" link
  working, and lets Instagram posts go out at their time;
- keeps your logins in your computer's password store (Windows Credential Manager, the Mac
  Keychain, or the Linux keyring). On a Mac, if it asks whether Python may use the "postkaro"
  Keychain item, choose **Always Allow**.

Check it any time, in the PostKaro folder:
```
python run.py status
```
```
PostKaro 0.6.0  ·  running on http://127.0.0.1:8765  ·  starts at login: yes
Logins kept in: Windows Credential Manager
  [ok] Facebook  My Gaming Page
  [ok] Facebook  My Other Page (not in use)
  [ok] Instagram my.gaming.insta
  [ok] YouTube   My Gaming Channel
Queue: 0 waiting, 0 missed, 0 live, 0 failed
```

## Opening PostKaro: the link with a key
PostKaro is a page in your browser, but it only opens with **its own link**, which ends in a secret
key:
```
http://127.0.0.1:8765/?k=AbC123xyz...
```
The key keeps other programs on your computer from using your connected accounts. Typing just
`http://127.0.0.1:8765` shows **"Open PostKaro with its link"** instead: that's the key missing, not
a problem.

- **To open it:** in the PostKaro folder, run `python run.py open`. It opens the page with the key and
  prints the link.
- **Bookmark the full link**, `?k=…` included, so next time it's one click.
- **The "Post them" link** at the end of every ClipKaro video already has the key in it.
- The link works **only on this computer**. Don't share it: anyone who has it, on this computer, can
  post from your accounts.

## Connect your accounts (once)
About **30-45 minutes**, once. PostKaro posts through **your own** small "developer apps": one at Google
(for YouTube) and one at Meta (for Instagram and Facebook). They are free and need no review, no
company and no website of your own (except one small step for Google, below), because they only post
to **your own** accounts. You never type your Google or Facebook password into PostKaro: you log in
on Google's and Meta's own pages.

The full, click-by-click guide is in PostKaro:
**[docs/connect-accounts.md](https://github.com/allthingsaman/PostKaro/blob/main/docs/connect-accounts.md)**.
In short:

| Part | What you do | Watch out for |
|---|---|---|
| **0. Instagram** (5 min, on your phone) | Switch to a **professional** account (Creator or Business), and **link it to your Facebook Page** | Instagram only lets apps post to professional accounts linked to a Page |
| **A. YouTube** (10-15 min) | At console.cloud.google.com: a project, **YouTube Data API v3** on, the login screen, the `youtube` permission, a **Desktop app** client → download its JSON → PostKaro Accounts → YouTube → upload the JSON → **Connect YouTube** | Google says **"Google hasn't verified this app"**: normal for your own app; click **Advanced → Go to PostKaro (unsafe)**. While the app is in **Testing**, Google logs PostKaro out **every 7 days**: publish it (it needs a homepage and a privacy-policy link: PostKaro's README, "Your own website") |
| **B. Facebook and Instagram** (15-20 min) | At developers.facebook.com: an app (use case "Other", type Business), **Facebook Login for Business** (redirect URI `http://localhost:8765/oauth/meta`), **Instagram** (API setup with Facebook login) → copy the **App ID** and **App Secret** into PostKaro → **Connect Facebook and Instagram** → pick your Page and its Instagram, allow everything | Leave the Meta app in **Development mode** (don't switch it to Live). Facebook posting is for **Pages** only, not personal profiles |
| **C. Check** | `python run.py status`: every account `[ok]`. Then a quiet first test: YouTube visibility **unlisted**, post one clip to YouTube only | Instagram and Facebook have no "unlisted": post one real clip, or delete it afterwards |

**Two computers?** (for example a Windows laptop and a Linux PC) Logins don't move between computers
or between Windows and Linux: connect the accounts on each computer that posts. For live clipping,
that's the one that runs OBS.

## Several pages or channels: the default account
You can connect **several** Facebook Pages, Instagram accounts and YouTube channels. Each platform has
**one Default**: new posts go there.

- **See which is the default:** `python run.py status`. The ones marked **(not in use)** are not the
  default.
- **Change it:** PostKaro → **Accounts** → **Make default** next to the one you want.
- **Just for one post:** on the Post page, each platform's box has a **"to …"** list. It starts on the
  default; pick another for that post only. It can change until you press Schedule.
- **Live clipping always posts to the defaults.** Set them before you stream.

Keep one brand together: for a gaming channel, make your gaming YouTube channel, gaming Instagram and
gaming Facebook Page the defaults, so a clip doesn't land on your other page.

## Posting your clips
**After ClipKaro finishes a video**, its last line is **"Post them: http://127.0.0.1:8765/?k=…"**.
Click it. (For an older ClipKaro video: `python run.py open <path to ClipKaro>/output/<video folder>`
in the PostKaro folder.)

On the page:
1. **Check each clip's text** for each platform. The counters turn red over a platform's limit (for
   example YouTube titles: 100 characters; Instagram: at most 5 hashtags).
2. **Pick the times:**
   - **Plan for me** spreads the clips over the coming days at your usual times, best clips first;
   - or type times yourself. **Time for all platforms** (above each clip's three boxes) puts the same
     time on all three; change one box to give that platform its own time;
   - **an empty time** means "as soon as I press Schedule".
3. **Thumbnails** (optional): pick a frame from the clip, or upload an image (YouTube and Facebook).
4. **Remove** the clips you don't want, then press **Schedule**.
5. The **Queue** shows what's waiting. **Posted** shows the links. A desktop notification tells you
   when a post is live, or failed (with a **Retry** button).

**Post one clip right now:** **Post now** at the top of the clip.

**Fix a clip before posting it (the Studio, PostKaro 0.9 with ClipKaro v2.10):** press **Fix** at the top of a
clip (or open the **Studio** tab). Without typing anything you can:
- **move its start or end**: click the word it should start on, or the last word it should keep;
- **fix a caption word**: click it, type the right word (or switch its caption off); the sound never changes;
- **change the framing** (podcasts and interviews): automatic, the left or right person, both people, or the
  whole picture;
- **switch an emoji, a sound effect or the whooshes off** (or back on);
- **cut a part out of the middle** (v2.10.1): under **Words**, click the first word, "Cut out from here", then the
  last word;
- **add a moment** (v2.10.1): find words said anywhere in the video (or look at the 2 minutes before or after the
  clip), click the moment's first and last word, **Add**; it plays in its place in time;
- **put your own emoji or sound on a word** (v2.10.1): click the word, pick an emoji (or type any) or a sound
  mood from your library. Your emojis go first among the 3 a clip can show.

Then press **Make the clip again**. Only that clip is cut and edited again (about a minute), and the page
shows each step. **Undo last change** puts it back. A clip whose post is already uploaded (not live yet) can't
be changed until you cancel that post; a live post stays as it was.

**How each platform goes live**

| | Goes live at its time by itself? | Laptop on at that time? |
|---|---|---|
| YouTube | yes: uploaded at once as private, YouTube makes it public at the time | no |
| Facebook Page | yes: Facebook publishes it (10 minutes to 29 days ahead) | no |
| Instagram | no: Instagram can't schedule | **yes**: PostKaro publishes it at the time. If the laptop was off, it asks you what to do |

**Copyright:** PostKaro warns about clips of other people's videos. Warnings never block you: you
decide. Only post videos you own or have permission to use.

## Live clipping
During [live clipping](live-clipping.md), ClipKaro hands each finished piece's clips to PostKaro, which
posts them **at once, everywhere, to your default accounts**. There is no page and no review. A clip
that fails ClipKaro's quality check is never posted.

- **A test stream first:** with `"live_post": "dry"` in ClipKaro's `settings.json` (tell Claude "turn on
  test mode"), PostKaro only shows what it *would* post.
- **Watch it live:** PostKaro's **Queue** page shows each clip as it uploads; **Posted** has the links.

## Keeping it working
- **Logins run out now and then:**
  - **Instagram:** after about **60 days**, and Meta asks for a fresh login every 90 days;
  - **YouTube:** every **7 days**, while your Google app is still in "Testing".

  PostKaro warns you 7 days and 1 day before, and the top right of the page turns ochre. Click
  **Reconnect** on the Accounts page: it takes a minute.
- **PostKaro must be running** for the "Post them" link and for Instagram's scheduled posts. It starts
  by itself at login; `python run.py status` shows it.
- **Updating:** in the PostKaro folder, `git pull`, then `python install.py`.

## Commands
Run them in the **PostKaro** folder (Mac/Linux: `python3`):
```
python run.py open [folder | post.json]   open the page (and add a ClipKaro project)
python run.py status                      accounts (and which is the default), queue, and whether PostKaro runs
python run.py check                       check every login now
python run.py service on | off | status   start by itself at login
python run.py serve                       run it in this window (to see errors)
python run.py post-now <folder> [--dry]   (live clipping) post a project everywhere now
```

## When something doesn't work
| You see | Why | What to do |
|---|---|---|
| "Open PostKaro with its link" | you opened `127.0.0.1:8765` without its key | `python run.py open`, and bookmark the full link |
| The "Post them" link doesn't load | PostKaro isn't running | `python run.py status`; `python run.py service on`; or `python run.py serve` to see the error |
| ClipKaro's last line has no "Post them" link | ClipKaro can't find PostKaro | Run `python install.py` in the PostKaro folder again (it tells ClipKaro where PostKaro is) |
| A clip went to the wrong Page or account | another account is the default | Accounts → **Make default** ([above](#several-pages-or-channels-the-default-account)) |
| "Instagram: none found" after connecting | Instagram isn't professional, or isn't linked to the Page | Fix that on your phone (Part 0), then **Reconnect** |
| YouTube logs out after a week | the Google app is still in Testing | Publish it, then **Reconnect** once |
| "Access blocked … has not completed the Google verification process" | the app is in Testing and your account isn't a test user | Publish the app, or add your Gmail as a test user |
| `redirect_uri_mismatch` (Google) | you made a "Web application" client | Make a **Desktop app** client and upload its JSON |
| "URL blocked" or "redirect URI is not whitelisted" (Meta) | the redirect address is missing | Add `http://localhost:8765/oauth/meta` to Facebook Login for Business → Valid OAuth Redirect URIs |
| An Instagram post shows **missed** | the laptop was off at its time | Choose what to do in the Queue (post now, or a new time) |
| Instagram: "Meta error 1363008" | a fault on Meta's side that comes and goes | PostKaro tries again by itself (after 1, 2, 5, 15, 30, 60 and 120 minutes); **Retry** later if it still fails |

More, from PostKaro itself: its [README](https://github.com/allthingsaman/PostKaro#readme) and
[connect-accounts.md](https://github.com/allthingsaman/PostKaro/blob/main/docs/connect-accounts.md).
