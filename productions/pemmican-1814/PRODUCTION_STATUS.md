# PRODUCTION STATUS — "The Survival Food That Was Banned in 1814 — and Started a War"

Persistent log so work can be resumed from verified artifacts. Update after every phase.

**Production dir:** `productions/pemmican-1814/` · **Target:** 15:00 exactly, 1920×1080, 30 fps, H.264 CRF 18, AAC 48 kHz stereo
**Branch:** `ccr-43a825bb-9p6uqi` (pushed)
**Scratch (not in git, re-creatable):** `$SCRATCH` = `/tmp/claude-0/-home-user-Uros001/3fb62f56-fe2e-5049-93c6-b75c237443df/scratchpad`
- `$SCRATCH/dl/kokoro-v1.0.onnx`, `voices-v1.0.bin`: Kokoro TTS (github.com/thewh1teagle/kokoro-onnx release "model-files-v1.0")
- `$SCRATCH/dl/sherpa-onnx-whisper-small.en/`: Whisper ASR for QA (github.com/k2-fsa/sherpa-onnx release "asr-models")
- `$SCRATCH/lib/vsco/`: VSCO-2-CE CC0 samples (sparse checkout of github.com/sgossner/VSCO-2-CE)

## Environment facts (verified 2026-10-28)
- Tools: FFmpeg 6.1.1 ✅ · Blender 5.2.3 LTS as Python module `bpy` ✅, Cycles CPU ✅ (4 cores, 15 GB RAM) · EEVEE only via software GL (unusable) · skia-python, OpenCV, SciPy, pyloudnorm ✅ · no NLE (Resolve/AE/Kdenlive) installed, so editing is done by the Python compositor in `tools/film/`.
- Network: YouTube, Wikimedia, LOC, NARA, archive.org, NPS, HF, PMC, **Pexels, Pixabay, Unsplash, Poly Haven, ambientCG, Mixkit, Videvo** are blocked by the environment policy (verified with curl). GitHub, PyPI, npm and apt are allowed.
- Git: normal pushes work (large pushes may need a retry). **Git LFS uploads are refused by the proxy (403 on lfs.github.com)**, so no LFS; files over 100 MB cannot be pushed.
- NexLev: free plan (no Studio analytics, no "watch" tool). Higgsfield: 0 credits (no generation used).

## Phase log
| Phase | Status | Artifacts |
|---|---|---|
| 1 Channel audit | ✅ | research/CHANNEL_AUDIT.md |
| 2 Competitor analysis | ✅ | research/COMPETITOR_ANALYSIS.md |
| 3 Topic selection | ✅ Pemmican 1814 | research/TOPIC_SELECTION.md |
| 4 Fact check | ✅ (+F8 Buffalo Treaty, +B3a ration correction) | research/FACT_CHECK.md |
| 5 Script | ✅ 42 paragraphs, 2,065 words | script/NARRATION.txt, PRONUNCIATION_GUIDE.md, FINAL_SCRIPT.md (generated from EDL) |
| 6 Narration | ✅ 900.0 s timeline, master −18 LUFS | audio/narration/narration_master.wav, timing.json |
| 7 Shot plan / assets | ✅ generated from EDL | production/SHOT_PLAN.md, production/ASSET_MANIFEST.md |
| 8 3D + graphics | ✅ 29 plates (realism pass + QA fixes), editable scenes in assets/blender/blend/ | assets/blender/*.py, renders/plates/, tools/film/{gfx,mapseq,life}.py |
| 9 Edit | ✅ EDL (105 clips) + renderer | tools/film/edl.py, render.py |
| 10 Audio | ✅ score, SFX, mix −14.0 LUFS / −1.4 dBTP (re-mix after final EDL for SFX cuts) | audio/music, audio/sfx, audio/mix |
| 11 Final render | ✅ 15:00.000, 1920×1080, 30 fps, H.264 CRF 18 + AAC 48 kHz, −14.1 LUFS / −1.3 dBTP; in git as 16 parts + `join_video.sh` (SHA-256 checked); version 3 (Smithsonian + Library of Congress images); v1 at 79ee180, v2 at c56cd31 | delivery/The_Pemmican_War_1080p.mp4 |
| 12 QA + delivery | ✅ automated + sampled-frame QA passed after fixes; Short 58.5 s; thumbnails, SRT, metadata | production/QA_REPORT.md, delivery/ |

## Decisions
- Voice: Kokoro `af_heart`; speed 0.82 (~165 wpm while speaking). Whisper WER ≈ 4% (formatting only).
- No AI-generated imagery. Visuals: Smithsonian CC0 paintings and photographs (v2), original Blender
  reconstructions, Natural Earth maps, original graphics.
- **User feedback (mid-production): "The video needs to look realistic, not generic."** Response:
  - Bison: lofted anatomy reworked (hump, low head, beard), dense hair-curve fur (200k strands per prototype); herd shots re-framed as backlit telephoto wildlife shots (B1 100 mm, B2 135 mm sunset).
  - Trees: leaf-card canopies from a generated oak-leaf atlas (250k cards), straighter, thicker trunks with root flare.
  - Camp: weathered lodge covers (smoke-darkened tops, seams), lacing pins, door covers, wider camp circle, travois.
  - Fort: woodpile; visible chimney smoke (compositor; first version was too faint to read); snow drifts sunk into the
    ground so their dark undersides no longer show.
  - Compositor "life" (`tools/film/life.py`): wind in grass and leaves (texture-masked so solid objects stay rigid), water ripple, drifting cloud decks, smoke from chimneys, lodges and fire, heat haze over the kettle, lens chromatic aberration.
  - Graphics moved onto the live moving 3D shots instead of black backgrounds; two long maps split with live shots.
  - Fixed square sun glow (HDR clamp before the fog blur).
- Ration line corrected: "roughly two weeks of food" conflicted with the 2 lb/day figure, so P16 was re-voiced and the timing re-solved.

## Archival pass (v2) — "realistic, with real images and scenes"
- Network policy still blocks Wikimedia, LOC, archive.org, Pexels and similar; the Smithsonian Open Access bucket
  (`smithsonian-open-access.s3-us-west-2.amazonaws.com`) is reachable. Its catalogue was searched (SAAM, SIA,
  NMAH, NZP, NMAI, NAA, NMNH) for CC0 items; 15 images were chosen (see production/ASSET_MANIFEST.md §1b,
  research/FACT_CHECK.md §J).
- All 3D bison shots were replaced with real material: Catlin's 1832–39 hunt and herd paintings, Muybridge's
  1884–86 photographs of a galloping bison (animated from 8 consecutive views), Hornaday and his 1887 bison group,
  zoo bison in 2014, and in version 3 the Library of Congress items (Red River carts photograph, two 1874 hide-trade engravings, 1900s herd photograph). Catlin's camp (meat drying), a Cree woman and an Assiniboine woman (1832),
  the Comanche village (women's work), the Sault Ste. Marie canoe race and Fort Union (1832) replace other 3D or
  generic shots. The bag, cutaway diagrams, maps and Frog Plain stay 3D/graphic (no authentic imagery exists).
- New shot types in tools/film/shots.py: `Archive` (rostrum-camera move kept inside the image), `Diptych`
  (portraits), `Sequence` (Muybridge print); on-screen credits for every archival image (edl.archive_credits).
- Sound: archival shots get place beds (wind, water, room) instead of graphic whooshes; hoofbeats under the
  Muybridge loop; bison calls under the herd paintings.
- Renderer: each finished chunk now stores a signature of the edit around it, so only chunks whose edit changed
  are re-rendered (`--stamp` recorded signatures for chunks rendered before).

## Network, and what came from it (updated)
- Hours earlier the environment's network policy rejected Wikimedia, Library of Congress, archive.org and the stock sites.
  After the environment's network setting was changed they are no longer rejected: the proxy status
  (`curl $HTTPS_PROXY/__agentproxy/status`) now lists only photogallery.nrcs.usda.gov, iiif.artic.edu, data.gc.ca,
  iiif.rijksmuseum.nl, cdn.rawpixel.com and cdn-lfs.huggingface.co as rejected.
- Wikimedia Commons answered one search with HTTP 429 ("too many requests"; the egress address is shared), and the
  session's permission checker then refused a repeat request to the same host as a containment escape. It was not retried.
- The Library of Congress answered normally (JSON search and item records, master TIFFs from tile.loc.gov); its
  search for this subject is noisy, so four relevant items were found and used (see ASSET_MANIFEST §1b).
- Still open: Rindisbacher's Red River watercolours (1820s), Paul Kane's Métis hunt (1840s), Hopkins's voyageur canoe
  (LAC C-002771), the 1892 bison-skull photograph (Commons says public domain, the Detroit library says rights retained:
  read both before using), CC0 skies and textures (Polyhaven, ambientCG). Their hosts are open at network level but need a
  fetch method that does not trigger Wikimedia's rate limit or the permission checker.

## Version 4 — archival first (2026-10-29)
- Request: real archival material wherever it exists; reconstruct only what cannot be found. Done for documents and
  posts; see production/QA_REPORT.md §7 for the real/3D table (real archival 196 s = 21.7 %, 3D 317 s = 35.2 %).
- New: `DocPage` shot (tools/film/shots.py): a scanned page on a dark ground with a rostrum move and highlighter marks
  drawn on in step with the narration; `tools/doc_marks.py` crops the pages from the Internet Archive scan of the 1819
  *Report of the proceedings … York … 1818* (public domain) and finds each highlighted phrase from the scan's OCR word
  boxes; `tools/fetch_documents.sh` re-fetches the originals (not kept in git). Pages: p. 134 (proclamation of
  8 Jan 1814), p. xiv (glossary: Pemican, Taureau 90 lbs), title page.
- Replaced: 5 generated "prop document" shots and the order paraphrase graphic (real page), the chapter III background,
  3 3D post shots (1860 photographs of Hudson's Bay Company posts, LOC), credits page text, Short, sound beds.
- Facts: the proclamation's wording differs between 1819 printings (FACT_CHECK C4); the film follows the page it shows.
- Network (this session): archive.org, tile.loc.gov and the Smithsonian bucket answered; the Smithsonian API's shared demo
  key was rate limited (not worked around); Wikimedia and LAC not requested again.
- Renderer: chunk signatures do not include gfx code; the credits chunk `.ok` was removed by hand after the text change.
- Master `delivery/The_Pemmican_War_1080p.mp4` is now v4 (1.6 GB, 15:00.000, −14.1 LUFS); v3 is kept locally as
  `…_v3.mp4` (and in git history as parts). **v4 is not committed as parts** (each master adds ~1.6 GB to the
  repository); it is awaiting the owner's go-ahead.

## Errors and recoveries (render stage)
- OOM: the furred bison close-up (B1, ~7 GB in Blender) plus two compositor workers exceeded 15 GB; the kernel killed
  B1 and one compositor worker. B1 now renders alone; the chunk renderer uses a process executor so a killed worker
  stops the pass instead of hanging it, and `run_final.sh` retries.
- Container restart mid-render (all background processes lost, files kept): resumed with `run_final.sh`; finished
  chunks (`delivery/picture.mp4.parts/*.ok`) are reused, stale ones (plates newer than the chunk) re-rendered.

- Realism defects found while checking the realism-pass renders (all fixed):
  - Winter fort: the foreground pass hid the ground, so the buried half of each snow drift showed as a dark band
    under the palisade. Background objects are now holdouts in that pass (`fg_holdout`).
  - Rolling-prairie shots (B1 bison close-up, B2 sunset herd, B3 cart line): the flat far-ground sheet sat at −1 m,
    but the terrain dips to about −4 m there, so the sheet flooded the hollow like a pale lake over the grass, right
    where the animals stand. Moved to −6 m; B1–B3 re-rendered.
  - Grass close-up (G2): 16-sample render noise in the defocused oaks; softened with a constant foreground blur
    (`DENOISE_FG`); B1 rendered at 32 samples.
  - Short: captions were hard to read over snow (dark plate added); end-card title was wider than the 1080 px frame.

## Open issues
- Final MP4 (1.6 GB) exceeds GitHub's 100 MB file limit and LFS is blocked here: version 3 is committed as 16 parts
  (`sh delivery/join_video.sh` rebuilds and verifies it); version 4 exists only in this session's container until
  it is split and pushed or handed over another way.
- Not done by design: no YouTube upload (needs the channel owner's explicit go-ahead).
- Recommended before publishing: one human viewing and listening pass of the full film (this production could only
  check sampled frames and measurements, see QA_REPORT §3–4).
