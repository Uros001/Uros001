#!/bin/sh
# light scenes only; the furred herd variants are exported after the render queue (memory)
for j in scene_dock:default scene_dock:canoe scene_camp:day scene_camp:dusk scene_fort:winter scene_fort:summer scene_plain:plain scene_desk:default scene_store:default; do
  python3 make_blends.py $j
done
