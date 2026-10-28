# PRODUCTION STATUS — "The Survival Food That Was Banned in 1814 — and Started a War"

Persistent log so work can be resumed from verified artifacts. Update after every phase.

**Production dir:** `productions/pemmican-1814/` · **Target:** ~15:00, 1920×1080, 30 fps, H.264 CRF 18, AAC 48 kHz
**Scratch (not in git, re-creatable):** `$SCRATCH` = `/tmp/claude-0/-home-user-Uros001/3fb62f56-fe2e-5049-93c6-b75c237443df/scratchpad`
- `$SCRATCH/dl/kokoro-v1.0.onnx`, `voices-v1.0.bin`: Kokoro TTS (github.com/thewh1teagle/kokoro-onnx release "model-files-v1.0")
- `$SCRATCH/dl/sherpa-onnx-whisper-small.en/`: Whisper ASR for QA (github.com/k2-fsa/sherpa-onnx release "asr-models")
- `$SCRATCH/lib/vsco/`: VSCO-2-CE CC0 samples (sparse checkout of github.com/sgossner/VSCO-2-CE)

## Environment facts (verified 2026-10-28)
- Tools: FFmpeg ✅ · Blender 5.2.3 LTS as Python module `bpy` (pip) ✅, Cycles CPU ✅, EEVEE via software GL only (very slow) · Python 3.13 + skia-python, PyAV, numpy, librosa, pyloudnorm ✅ · SoX ✅ (apt) · After Effects / Resolve / Kdenlive ❌ not installed.
- Network: YouTube, Wikimedia, LOC, NARA, archive.org, NPS, HF, PMC are **blocked** by the environment policy. GitHub (raw and releases), PyPI, npm and apt are allowed.
- NexLev: free plan (no Studio analytics, no "watch" tool). Higgsfield: 0 credits (no generation used).

## Phase log
| Phase | Status | Artifacts |
|---|---|---|
| 1 Channel audit | ✅ done | research/CHANNEL_AUDIT.md |
| 2 Competitor analysis | ✅ done | research/COMPETITOR_ANALYSIS.md |
| 3 Topic selection | ✅ done (Pemmican 1814) | research/TOPIC_SELECTION.md |
| 4 Fact check | ✅ done | research/FACT_CHECK.md |
| 5 Script | ✅ narration v2 (42 paragraphs) | script/NARRATION.txt, script/PRONUNCIATION_GUIDE.md, script/FINAL_SCRIPT.md (pending timing) |
| 6 Narration | 🔄 v2 at speed 0.82 generating | audio/narration/raw/sentences/*.wav + sentences.json |
| 7 Shot plan / assets | ⏳ | production/SHOT_PLAN.md, production/ASSET_MANIFEST.md |
| 8 Blender + graphics | ⏳ | assets/blender/*.py, renders/shots/ |
| 9 Edit | ⏳ | tools/timeline*.py |
| 10 Audio mix/master | ⏳ | audio/mix/ |
| 11 Final render | ⏳ | delivery/ |
| 12 QA + delivery | ⏳ | delivery/QA_REPORT.md |

## Decisions
- Voice: Kokoro `af_heart` (the model's top-graded voice; Whisper WER v1 = 4.1%, nearly all formatting).
- Speech speed 0.94 measured at ~190 wpm (too fast), so moved to 0.82 (~160–170 wpm).
- No AI-generated imagery; all visuals are original 3D, real geodata maps and typography.

## Open issues / errors
- (none blocking)
