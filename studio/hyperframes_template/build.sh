#!/bin/sh
# Render a HyperFrames shot in the channel's look:  sh build.sh <output.mp4>   (run from anywhere)
# Copies the film's fonts (OFL) and GSAP into assets/ (not kept in git), lints, renders 1920x1080 at 30 fps.
set -e
HERE=$(cd "$(dirname "$0")" && pwd)
OUT=${1:-$HERE/out.mp4}
REPO=$(cd "$HERE" && git rev-parse --show-toplevel)
FONTS=$REPO/productions/pemmican-1814/assets/fonts
mkdir -p "$HERE/assets"
cp "$FONTS/cormorantgaramond_CormorantGaramond[wght].ttf" "$HERE/assets/cormorant.ttf"
cp "$FONTS/cormorantgaramond_CormorantGaramond-Italic[wght].ttf" "$HERE/assets/cormorant_italic.ttf"
cp "$FONTS/oswald_Oswald[wght].ttf" "$HERE/assets/oswald.ttf"
cp /usr/share/fonts/opentype/inter/Inter-Medium.otf /usr/share/fonts/opentype/inter/Inter-SemiBold.otf "$HERE/assets/"
if [ ! -s "$HERE/assets/gsap.min.js" ]; then
  (cd "$HERE" && npm pack gsap@3.14.2 --silent >/dev/null && tar -xzf gsap-3.14.2.tgz package/dist/gsap.min.js \
   && mv package/dist/gsap.min.js assets/ && rm -rf package gsap-3.14.2.tgz)
fi
[ -f "$HERE/hyperframes.json" ] || cp "$REPO/studio/tests/souris_map/hyperframes.json" "$REPO/studio/tests/souris_map/meta.json" \
   "$REPO/studio/tests/souris_map/package.json" "$HERE/"
cd "$HERE" && hyperframes lint && hyperframes render --output "$OUT"
