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
| 8 3D + graphics | 🔄 realism pass: plates re-rendering | assets/blender/*.py, renders/plates/, tools/film/{gfx,mapseq,life}.py |
| 9 Edit | ✅ EDL (105 clips) + renderer | tools/film/edl.py, render.py |
| 10 Audio | ✅ score, SFX, mix −14.0 LUFS / −1.4 dBTP (re-mix after final EDL for SFX cuts) | audio/music, audio/sfx, audio/mix |
| 11 Final render | 🔄 `sh tools/run_final.sh` (resumable: plates → chunks → mux; log delivery/render_final.log) | delivery/The_Pemmican_War_1080p.mp4 |
| 12 QA + delivery | ⏳ (SRT, thumbnails, metadata done) | delivery/ |

## Decisions
- Voice: Kokoro `af_heart`; speed 0.82 (~165 wpm while speaking). Whisper WER ≈ 4% (formatting only).
- No AI-generated imagery. All visuals: original Blender reconstructions, Natural Earth maps, original graphics.
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

## Errors and recoveries (render stage)
- OOM: the furred bison close-up (B1, ~7 GB in Blender) plus two compositor workers exceeded 15 GB; the kernel killed
  B1 and one compositor worker. B1 now renders alone; the chunk renderer uses a process executor so a killed worker
  stops the pass instead of hanging it, and `run_final.sh` retries.
- Container restart mid-render (all background processes lost, files kept): resumed with `run_final.sh`; finished
  chunks (`delivery/picture.mp4.parts/*.ok`) are reused, stale ones (plates newer than the chunk) re-rendered.

## Open issues
- Final MP4 will exceed GitHub's 100 MB file limit: delivered in the working directory + sent to the user; committed to git as split parts with a join script.
