# Standard production workflow — Lost Tribe Knowledge

Approved by the channel owner (2026-10-29): archival first, 2.5D moves on archival photographs, HyperFrames for
motion graphics. New sessions: `sh studio/setup_tools.sh` first (tools are not kept between sessions).

## 1. Picture: where each shot comes from, in this order

1. **Real archival picture or document.** Smithsonian Open Access (CC0), Library of Congress (only "No known
   restrictions on publication"), Internet Archive books printed before 1929. Read the rights record before using an
   item; record it in `assets/archival/ARCHIVAL_SOURCES.json`; every item gets an on-screen credit while shown.
2. **Photographs and paintings with a clear near/far: 2.5D move.** `ARD(key, a, b, dolly, shift)` in the edit list,
   after `python3 -I tools/depth_map.py <key>`. Start with dolly 0.03–0.06 and shift up to 0.02 of the frame. View the
   first and last frame at full size; if an object edge stretches, make the move smaller. Pixels are only moved,
   never added. Use the flat move `AR(...)` instead for documents, engravings with lettering, maps and close faces.
3. **Real document pages:** `DOC(...)`, highlight positions found from the scan's OCR word boxes
   (`tools/doc_marks.py`); the credit says "highlighting added".
4. **Only where no authentic picture exists: Blender reconstruction.** Sun Position set to the real place, date and
   hour; materials, skies and props from the CC0 library (`studio/library`); Cycles with OpenImageDenoise. Labelled
   "Reconstruction" on first appearance and in the credits.
5. **Never:** AI-generated images or video as historical scenes; AI upscaling of archival images.

## 2. Motion graphics: HyperFrames

- Title and chapter cards, maps, timelines, counters, lower thirds and on-screen text.
- Copy `studio/hyperframes_template` to `productions/<film>/motion/<shot>/` (it holds the film's palette, fonts,
  grain and vignette), write the shot, render with `sh build.sh ../<shot>.mp4`, place it in the edit with
  `MV('<shot>', 'description')` (shot type `Movie`).
- Maps use the film's own geography (Natural Earth through `tools/film/maps.py`): export the base map and the projected
  points as in `studio/tests/souris_map/export_basemap.py`; keep the "approximate" captions.
- `hyperframes lint` must show 0 errors; animate transforms and opacity only; GSAP bundled locally; render locally;
  telemetry off; no HeyGen cloud, publishing or paid media.
- Every date, name and number on screen must match a row in `research/FACT_CHECK.md`.

## 3. Edit, sound, QA

As in "The Pemmican War": chunked render (`tools/film/render.py`), synthesized sound and mix (`tools/sfx.py`,
`tools/mix.py`), `tools/qa.py` (1920×1080, 30 fps, −14 LUFS, true peak ≤ −1 dBTP, subtitles). In addition, view the
first and last frame of every `ARD` shot and every `MV` clip in the finished film.

## 4. Delivery and publishing

- The master film is not committed to git without the owner's go-ahead; deliver it in parts under 400 MiB with join
  scripts and a SHA-256, or as the owner says.
- No upload or publication to YouTube without the owner's explicit approval for that step; metadata through vidIQ
  only after approval of the exact values.
