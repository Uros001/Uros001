#!/bin/sh
# export every scene variant as an editable .blend (one process per variant to keep memory low)
for j in scene_dock:default scene_dock:canoe scene_camp:day scene_camp:dusk scene_fort:winter scene_fort:summer scene_plain:plain \
         scene_plain:herd scene_plain:horizon scene_plain:carts scene_desk:default scene_store:default; do
  python3 make_blends.py $j
done
