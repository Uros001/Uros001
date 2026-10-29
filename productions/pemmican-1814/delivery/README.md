# Delivery — The Pemmican War

| File | What it is |
|---|---|
| `The_Pemmican_War_1080p.mp4` | Final documentary (version 4: archival images from the Smithsonian and the Library of Congress, and real pages of an 1819 printed book; 3D only where no archival picture exists), 15:00, 1920×1080, 30 fps, H.264 High (CRF 18), AAC 48 kHz stereo, −14 LUFS |
| `The_Pemmican_War_1080p.mp4.part-00…15` + `join_video.sh` | **Version 3** of the film split into 16 parts under 100 MB (GitHub's file limit, LFS is not available from the production environment). Run `sh join_video.sh` to rebuild it and verify its SHA-256. Version 4 has not been pushed (each master adds about 1.6 GB to the repository); it is in the production container and goes into git or elsewhere on the owner's instruction. |
| `The_Pemmican_War_Short_1080x1920.mp4` | Vertical Short (58.5 s) cut from the cold open, with burned-in captions and an end card |
| `The_Pemmican_War_EN.srt` | English subtitles (sentence-timed from the narration) |
| `thumbnail_primary.png` / `_1920.png` | Primary thumbnail, "ILLEGAL CARGO" (1280×720 and 1920×1080) |
| `thumbnail_alt.png` / `_1920.png` | Alternative thumbnail, "LASTED YEARS" |
| `YOUTUBE_METADATA.md` | Titles, description with sources and disclosures, chapters, tags, settings |
| `../production/QA_REPORT.md` | Technical and editorial QA results |
| `../production/SHOT_PLAN.md`, `../production/ASSET_MANIFEST.md` | Shot list (generated from the EDL) and licences |
| `../script/FINAL_SCRIPT.md` | Narration with timings and the picture under each paragraph |

Version 1 (all 3D picture) is kept in git history at commit 79ee180, version 2 (Smithsonian images only) at c56cd31, version 3 (plus Library of Congress images) at 02465c7.

Nothing has been uploaded to YouTube. Publishing needs the channel owner's explicit go-ahead.

## Rebuilding the film from source

```
# 3D plates (Blender 5.2.3 as the bpy module; ~3–4 h on 4 CPU cores)
cd assets/blender && python3 render_queue.py jobs_camp.txt   # and jobs2..jobs9.txt (later lists re-render with --force)
# narration timing, score, sound, mix
python3 tools/assemble_narration.py && python3 tools/score.py <vsco_dir> audio/music/score_raw.wav
python3 tools/sfx.py audio/sfx/ambience.wav audio/sfx/fx.wav && python3 tools/mix.py audio/mix/pemmican_mix_master.wav
# picture (parallel chunks) and mux; tools/run_final.sh does the last plates, picture and mux in one resumable step
cd tools && python3 -m film.render video ../delivery/picture.mp4 --workers 4
ffmpeg -i ../delivery/picture.mp4 -i ../audio/mix/pemmican_mix_master.wav -map 0:v -map 1:a -c:v copy -c:a aac -b:a 320k \
       -ar 48000 -movflags +faststart ../delivery/The_Pemmican_War_1080p.mp4
```
