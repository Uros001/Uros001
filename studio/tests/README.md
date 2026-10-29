# Test shots (not in the film)

Two A/B tests made for the next films, compared with version 4 of "The Pemmican War" at the same moment and with the
same narration. The film's edit list is unchanged.

1. **2.5D move on an archival photograph** (film 7:04, Fort Colville, 1860, under Macdonell's lower third).
   Depth map: `python3 -I productions/pemmican-1814/tools/depth_map.py hbc_fort_colville_officers_house`, then
   ```
   python3 studio/tests/render_variant.py 'P21.0-0.45' 423.8 430.4 colville_depth.mp4 \
     "shots.ArchiveDepth(os.path.join(core.ROOT,'assets/archival/work/hbc_fort_colville_officers_house.jpg'), (0.5, 0.6, 0.94), (0.44, 0.6, 0.80), dolly=0.06, shift=(0.018, 0.0), mono=0.2)"
   ```
   Pixels are only displaced by depth (near logs move and grow more than the buildings, the sky stays); nothing is added.
2. **HyperFrames map** (film 8:15, the sheriff's party to the North West Company post on the Souris): same base map
   and positions as the film's `mapseq.souris`, rebuilt as an HTML/GSAP composition: `sh studio/tests/souris_map/build.sh`.
