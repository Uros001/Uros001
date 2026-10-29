# Production toolset — Lost Tribe Knowledge

Everything here is free to use: open-source software or CC0 assets. No paid service or account is needed.
`sh studio/setup_tools.sh` reinstalls all of it in a new session. Large files (`library/`, `models/*.onnx`) are not
kept in git: the scripts and the lists are.

Rules that still apply: real archival material first; 3D only where no archival picture exists, labelled as a
reconstruction; no AI-generated pictures presented as historical evidence.

## Motion graphics and editing

| Tool | Version | Licence | What it is for | Checked here |
|---|---|---|---|---|
| HyperFrames CLI (HeyGen) | 0.8.216 | Apache-2.0 | Animated titles, maps, timelines, charts, kinetic type and overlays written as HTML/CSS + GSAP and rendered to MP4 (headless Chrome + FFmpeg), about 450 ready blocks (`hyperframes catalog`) | 4 s chapter card in the film's fonts and palette, 1920×1080/30 fps, rendered in 20 s |
| HyperFrames agent skills | core set: `hyperframes`, `hyperframes-cli`, `hyperframes-registry`, `media-use` | Apache-2.0 | How to write, check and render compositions; installed globally (`~/.claude/skills`), not in this repository | installed |
| OpenTimelineIO + adapters | 0.18.1 | Apache-2.0 | Export the film's edit (EDL) as FCP XML / FCPX XML / CMX 3600 EDL so it can be opened in DaVinci Resolve or Premiere for manual finishing | adapters `fcp_xml`, `fcpx_xml`, `cmx_3600` load |
| PySceneDetect | 0.7.2 | BSD-3-Clause | Measure cut rhythm (shot lengths) of reference documentaries and of our own films | imports |
| FFmpeg (system) | 6.1.1 | LGPL/GPL | Already had: `zscale`, `lut3d`, `haldclut`, `tonemap`, `colorspace`, `deband`, `nlmeans`, `bm3d`, `vidstab`, `minterpolate`, `loudnorm`, `arnndn`, `afftdn`, `dialoguenhance`, `frei0r` | filter list checked |

HyperFrames rules for our use: render locally only (no `cloud`, `publish`, HeyGen account or paid HeyGen media);
telemetry is switched off (`hyperframes telemetry disable`).

## Realistic 3D (Blender 5.2.3, Cycles)

| Tool | Version | Licence | What it is for |
|---|---|---|---|
| Sun Position | 4.4.0 | GPL-3.0+ | Sun direction for a real place, date and hour (for example Frog Plain, 19 June 1816, evening) |
| Sapling Tree Gen | 0.3.7 | GPL-3.0+ | Procedural trees with real branching (bur oaks) |
| Modular Tree | 5.6.0 | GPL-3.0+ | Node-based high-detail trees |
| A.N.T. Landscape | 0.2.0 | GPL-2.0+ | Terrain meshes |
| Erosion Terrain | 1.0.0 | GPL-3.0+ | Water and thermal erosion on terrain, so ground does not look procedural |
| SRTM Terrain Importer | 1.0.5 | GPL-3.0+ | Real elevation data for a real valley |
| Weathered Board | 0.1.6 | GPL-3.0+ | Weathered planks (palisades, storehouses, canoes, carts) |
| Scatter Objects | 0.2.0 | GPL-2.0+ | Scatter grass, stones and branches |
| Extra Mesh Objects | 0.4.1 | GPL-3.0+ | Extra primitives |
| Dynamic Sky | 1.1.0 | GPL-3.0+ | Procedural sky |
| OpenImageDenoise | built into Cycles | Apache-2.0 | Removes render noise; already on in `assets/blender/lib.py` |

The extensions are installed from extensions.blender.org after checking each archive's SHA-256
(`studio/install_blender_extensions.py`). A script enables what it uses:
`addon_utils.enable('bl_ext.user_default.sun_position', default_set=True)`.

### CC0 asset library (`studio/library/`, list in `LIBRARY.json`, fetched by `fetch_assets.py`)

- **Sky HDRIs, 4k (Poly Haven):** partly cloudy midday ×2, sunset, dusk, misty morning, overcast ×2, snow-field sky,
  clear autumn, sunrise. Only "pure sky" images, so no modern building can appear in a reflection or background.
- **PBR textures, 2k (Poly Haven):** mud and leaves, forest ground, dry mud, leaves, rocky ground, river pebbles,
  weathered planks ×2, rough wood, grey planks, brown bark, willow bark, brown leather, leather fabric, snow, aerial
  grass and rock.
- **Scanned / modelled props, glTF 2k (Poly Haven):** grass clumps ×3, dry branches, dead tree trunk, boulder, mossy
  rocks, shrub, wooden barrel (kegs of grease), wooden crate, wooden pier (canoe landing), small tree.
- **Materials, 2K (ambientCG):** worn dark leather and brown leather (rawhide bags), rope, oak bark.

Checked here: an HDRI-lit Cycles test with the scanned barrel, grass and a Poly Haven ground texture rendered and
denoised in about 20 s at 960×540, 24 samples.

## Archival photographs: 2.5D camera moves

| Tool | Version | Licence | What it is for | Checked here |
|---|---|---|---|---|
| Depth Anything V2 Small (ONNX export by fabio-sim) | v2.0.0 | Apache-2.0 (the Small model only; Base/Large are non-commercial and not used) | A depth map from a still photograph, so a real archival image can be given a slow parallax move (foreground, middle, far) instead of a flat pan | 1860 Fort Colville photograph: logs, buildings and sky separated correctly, 1.4 s on the CPU |

The depth map only moves the existing pixels; it adds nothing to the picture. Gaps opened by the parallax are kept
small (gentle moves) and filled from neighbouring pixels.

## Sound

| Tool | Version | Licence | What it is for |
|---|---|---|---|
| pedalboard (Spotify) | 0.9.26 | GPL-3.0 | Studio effects on our own sounds: convolution reverb, EQ, compression, limiting |
| noisereduce | 3.0.3 | MIT | Clean hiss from recordings |
| (already had) pyloudnorm, Kokoro TTS, Whisper (sherpa-onnx) | | MIT / Apache-2.0 | Loudness, synthetic narration (disclosed), speech check |

## Colour and procedural detail

| Tool | Version | Licence | What it is for |
|---|---|---|---|
| colour-science | 0.4.7 | BSD-3-Clause | Build our own 3D LUTs (`.cube`) for one consistent film look across 3D, archival and graphics |
| opensimplex | 0.4.5.1 | MIT | Natural noise for wind, cloud drift, ground variation |

## Considered and not installed

- **FFmpeg 7.1 static build with VMAF** (objective encode quality): downloading and running a prebuilt binary was
  refused by this environment's safety check; not worked around. The system FFmpeg covers everything else.
- **AI upscalers (Real-ESRGAN) for archival images:** they invent detail, which would misrepresent historical
  photographs. Not used. Classic resampling only.
- **AI video generators (Higgsfield, vidIQ b-roll):** not for historical scenes (no AI imagery as evidence); also
  paid credits.
- **Remotion:** licence requires a paid company licence at 4+ people; HyperFrames does the same job under Apache-2.0.
- **Quixel Megascans:** free only inside Unreal Engine; licence does not cover Blender renders.
- **Motion Canvas, Manim:** overlap with HyperFrames; can be added later if a specific need appears.
