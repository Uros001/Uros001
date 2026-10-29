#!/bin/sh
# Test shot: the Souris River map (film 8:15, "479 bags") as a HyperFrames composition.
# Rebuilds the assets that are not kept in git, then renders:  sh studio/tests/souris_map/build.sh
set -e
HERE=$(cd "$(dirname "$0")" && pwd)
REPO=$(cd "$HERE/../../.." && pwd)
P=$REPO/productions/pemmican-1814
python3 "$HERE/export_basemap.py"
cp "$P/assets/fonts/cormorantgaramond_CormorantGaramond[wght].ttf" "$HERE/assets/cormorant.ttf"
cp /usr/share/fonts/opentype/inter/Inter-Medium.otf /usr/share/fonts/opentype/inter/Inter-SemiBold.otf \
   /usr/share/fonts/opentype/inter/Inter-Italic.otf "$HERE/assets/"
cd "$HERE" && npm pack gsap@3.14.2 --silent >/dev/null && tar -xzf gsap-3.14.2.tgz package/dist/gsap.min.js \
  && mv package/dist/gsap.min.js assets/ && rm -rf package gsap-3.14.2.tgz
hyperframes lint && hyperframes render --output "$HERE/souris_map.mp4"
