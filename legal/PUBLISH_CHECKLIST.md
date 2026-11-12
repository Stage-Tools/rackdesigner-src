# Rack Designer 0.1.21 - publishing checklist

Status when written (2026-11-12): everything below is **local only**. Nothing has been pushed,
made public, released, deleted or edited on GitHub or on the website.

Repos involved
- `Stage-Tools/rackdesigner-src` - source repo, currently **private**; remote `main` = `ee3024e` (old, Gmail address; to be replaced by the force-push in step 0).
- `Stage-Tools/RackDesigner` - public download repo (README only + releases v0.1.18-v0.1.20).
- `Stage-Tools/stagetools` - website (GitHub Pages).

Local state to publish (ALL commits, including the root commit, use the GitHub noreply address;
history was rebuilt on 2026-11-12, so these hashes replace every earlier one)

| Ref | Commit | Notes |
|---|---|---|
| `main` | tip = latest checklist commit (after `6dc74af`) | root `e5922ab` (rewritten import commit), then `6dc74af` (0.1.21, tagged), then checklist commits. **Not** a descendant of the remote's `ee3024e`: needs a force-push |
| `reconstructed-releases` | `99d954f` | orphan branch, 4 commits, one per version |
| `v0.1.17` | `c983b93` | reconstructed |
| `v0.1.18` | `a230e3e` | reconstructed |
| `v0.1.19` | `4f895fd` | reconstructed |
| `v0.1.20` | `99d954f` | reconstructed |
| `v0.1.21` | `6dc74af` | on `main` |

Local release files in `release/v0.1.21/` (gitignored), SHA-256:
- `RackDesigner_v0.1.21_Setup.exe` `3120d25e174ce13715cc4b5c76846f3a995570c059181a2f5cfbad64e068a690`
- `RackDesigner_v0.1.21_UserManual.docx` `6f3b5806ec977c523addc1a62a767d25b9f67cd35e20b4f45e1e1de4c4a2ab90`
- `RackDesigner_v0.1.21_UserManual.pdf` `14364224afc7cc52ab2625d574b90be7a76727c1e3a640ccc3927bcb83c218fc`
- `legal/THIRD-PARTY-NOTICES.txt` (inside the Setup, verified) `8461da684c44a8abe2050cd16042fd10f5a5d5bff8cbc301a0e311f74bbabe22`

## 0. Force-push main to rackdesigner-src while it is still private
Force-push `main` to rackdesigner-src while it is still private, then verify that no commit in
any branch or tag contains the Gmail address (`git log --all --format='%ae %ce'`), only then
make the repo public.

Why: the remote's current `main` (`ee3024e`) carries the Gmail address. The local
history was rewritten (root commit included) to the noreply address, so it no longer descends
from `ee3024e` and a plain push is rejected.

1. `git push --force-with-lease=main:ee3024ec1446b3d5e24606595daebd4e441ef8cb origin main`
   (replaces remote `main`; the lease makes it fail if anything else changed on the remote).
2. `git push origin reconstructed-releases v0.1.17 v0.1.18 v0.1.19 v0.1.20 v0.1.21`
3. Verify on the **remote**: `git fetch origin --prune`, then
   `git log --all --format='%ae %ce' | sort -u` must print only
   `276313541+NessiRiccardo@users.noreply.github.com 276313541+NessiRiccardo@users.noreply.github.com`.
   `git fetch` keeps the old `ee3024e` only in your local reflog/object store, not on GitHub;
   if `git log --all` still lists it, run `git reflog expire --expire=now --all && git gc --prune=now`
   and check again. Also check that GitHub no longer serves `ee3024e`:
   `gh api repos/Stage-Tools/rackdesigner-src/commits/ee3024e` should fail or show it only as
   an unreachable object. If it is still fetchable by hash, contact GitHub Support to purge it
   before going public (force-pushed commits can stay reachable by SHA on GitHub).
4. Only when all of this is clean, go on to step 1 and make the repo public.

## 1. rackdesigner-src: push, then make public
1. (Pushes are done in step 0.)
2. Check on GitHub: `main` at the local tip, branch `reconstructed-releases`, 5 tags.
3. Make the repo **public** (Settings > General > Danger Zone > Change visibility).
   Before that, re-check `legal/BRIEF_LICENSING.md` and `docs/` are fine to publish (they are
   committed).
4. Set the repo description (replace "private backup") and the licence is auto-detected from
   `LICENSE` (AGPL-3.0).
5. **No releases** in this repo: tags only. GitHub provides the source zips per tag.

## 2. RackDesigner (public download repo)
1. Delete these release assets (and nothing else):
   - v0.1.20: `RackDesigner_v0.1.20_Setup.exe`, `RackDesigner_v0.1.20_Portable.zip`
   - v0.1.19: `RackDesigner_v0.1.19_Setup.exe`
   - v0.1.18: `RackDesigner_v0.1.18_Setup.exe`
   Keep the three manual PDFs.
2. Edit the notes of v0.1.18, v0.1.19, v0.1.20:
   `Binaries withdrawn. Source code: https://github.com/Stage-Tools/rackdesigner-src/tree/<tag>`
   with `<tag>` = `v0.1.18`, `v0.1.19`, `v0.1.20` respectively.
   (There is no v0.1.17 release in this repo; nothing to edit. Tag `v0.1.17` exists only in
   rackdesigner-src.)
3. Create release `v0.1.21` (new tag in this repo on its `main`, or release without moving code):
   - Assets: `RackDesigner_v0.1.21_Setup.exe`, `RackDesigner_v0.1.21_UserManual.docx`,
     `RackDesigner_v0.1.21_UserManual.pdf`, and the source zip.
   - Source zip: from the local repo, `git archive --format=zip --prefix=rackdesigner-0.1.21/
     -o RackDesigner_v0.1.21_Source.zip v0.1.21`.
   - Notes: "Free software under GNU AGPL-3.0-or-later. Source code:
     https://github.com/Stage-Tools/rackdesigner-src/tree/v0.1.21. No warranty."
   - No portable zip.
4. README of `RackDesigner`: add a **Licence** section - GNU AGPL-3.0-or-later,
   Copyright (C) 2026 Riccardo Nessi, no warranty, link to
   https://github.com/Stage-Tools/rackdesigner-src. Keep the rest.
   Optional: add the `LICENSE` file there too.

## 3. Website (Stage-Tools/stagetools) - same step as section 2
Change only these two files; keep the existing style; do not touch other pages.
- `rackdesigner.html`
  - Setup button -> `https://github.com/Stage-Tools/RackDesigner/releases/download/v0.1.21/RackDesigner_v0.1.21_Setup.exe`
  - Manual button -> `.../download/v0.1.21/RackDesigner_v0.1.21_UserManual.pdf`
  - **Remove** the Portable button (`RackDesigner_v0.1.20_Portable.zip`).
  - Add "Open source - GNU AGPL v3" with a link to https://github.com/Stage-Tools/rackdesigner-src.
  - Update any visible version text 0.1.20 -> 0.1.21.
- `index.html`
  - Rack Designer link `.../download/v0.1.20/RackDesigner_v0.1.20_Setup.exe` -> v0.1.21 Setup.

The v0.1.20 links break as soon as the old assets are deleted, so the site change and the
asset deletion must happen together (publish the v0.1.21 release first, then update the site,
then delete the old assets).

## 4. Suggested order (matches the approved decisions)
1. Resolve section 0, then push to rackdesigner-src and make it public (section 1).
2. Create the v0.1.21 release in `RackDesigner` with its assets (section 2.3).
3. Update the website (section 3).
4. Delete the four old binaries, edit the v0.1.18-0.1.20 notes, update the README (sections 2.1, 2.2, 2.4).

## 5. Final verification
- Download the v0.1.21 Setup from the site; the wizard shows the AGPL; `LICENSE` and
  `THIRD-PARTY-NOTICES.txt` land in the install folder; the latter hashes to the value above.
- About screen shows copyright, no-warranty text, AGPL link and source link.
- Every old link on the site and README resolves; no `0.1.20` download URL remains.
- Repo is public and shows "AGPL-3.0" as its licence.

## Notes
- Tags before 0.1.21 are reconstructed from archived source folders (README and changelog say so).
  No `.iss` installer script was archived for 0.1.17-0.1.19.
- `RackLibrary - Refernce.csv` is intentionally not committed.
