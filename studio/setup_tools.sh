#!/bin/sh
# Production toolset for Lost Tribe Knowledge films. Idempotent; run from the repository root:  sh studio/setup_tools.sh
# Installs: HyperFrames (HTML -> MP4 motion graphics, Apache-2.0) with its agent skills, Python libraries for sound,
# edit analysis, colour and timeline export, Blender extensions, the depth model, and the CC0 asset library.
# See studio/TOOLS.md for what each tool is for and its licence.
set -e
REPO=$(pwd)

# 1. HyperFrames CLI (needs Node 22+ and FFmpeg); telemetry off; headless Chrome; core skills (global, not in the repo)
npm install -g hyperframes@0.8.216
hyperframes telemetry disable
hyperframes browser ensure
(cd /tmp && hyperframes skills update)

# 2. Python libraries (OpenCV stays the headless build the film pipeline uses)
pip install --break-system-packages pedalboard==0.9.26 noisereduce==3.0.3 scenedetect==0.7.2 colour-science==0.4.7 \
    opensimplex==0.4.5.1 opentimelineio==0.18.1 otio-fcp-adapter==1.0.0 otio-fcpx-xml-adapter==1.0.0 otio-cmx3600-adapter==1.0.0
pip uninstall -y --break-system-packages opencv-python 2>/dev/null || true      # if anything pulled the GUI build in,
pip install --break-system-packages --force-reinstall --no-deps opencv-python-headless==5.0.0.93   # restore the shared cv2 files

# 3. Blender extensions (Sun Position, Sapling, Modular Tree, A.N.T. Landscape, erosion, SRTM terrain, weathered boards, ...)
python3 studio/install_blender_extensions.py

# 4. Depth model for 2.5D camera moves on archival photographs: Depth Anything V2 Small (Apache-2.0), ONNX export
mkdir -p studio/models
[ -s studio/models/depth_anything_v2_vits_dynamic.onnx ] || curl -sS -L -m 600 -o studio/models/depth_anything_v2_vits_dynamic.onnx \
    https://github.com/fabio-sim/Depth-Anything-ONNX/releases/download/v2.0.0/depth_anything_v2_vits_dynamic.onnx

# 5. CC0 asset library (Poly Haven skies, textures, scanned models; ambientCG materials), about 650 MB
python3 -I studio/fetch_assets.py
echo "tools ready"
