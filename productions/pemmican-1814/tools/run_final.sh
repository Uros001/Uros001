#!/bin/sh
# Resumable final pipeline. Every step skips work that is already done, and several render processes can
# share the chunk list (per-chunk lock files), so this can be re-run at any time:
#   remaining plates (B1 excluded) -> picture chunks that do not need B1 -> B1 alone (~7 GB)
#   -> full picture pass (renders the rest, re-renders stale chunks, concatenates) -> mux with the master mix.
# Optional: WAIT_PIDS="pid ..." waits for earlier render processes before the B1 step.
ROOT=$(cd "$(dirname "$0")/.." && pwd)
LOG=$ROOT/delivery/render_final.log
cd "$ROOT/assets/blender" && python3 render_queue.py jobs8.txt >> ../../renders/plates/queue8.log 2>&1
cd "$ROOT/tools"
python3 -m film.render video ../delivery/picture.mp4 --workers 2 --pending plain_B1 >> $LOG 2>&1
for p in $WAIT_PIDS; do while kill -0 $p 2>/dev/null; do sleep 15; done; done
cd "$ROOT/assets/blender" && python3 render_queue.py jobs9.txt >> ../../renders/plates/queue9.log 2>&1
cd "$ROOT/tools"
for i in 1 2 3; do
  python3 -m film.render video ../delivery/picture.mp4 --workers 4 >> $LOG 2>&1 && break
  echo "final pass attempt $i failed" >> $LOG
done
cd "$ROOT"
[ -f delivery/picture.mp4 ] && ffmpeg -hide_banner -loglevel error -y -i delivery/picture.mp4 -i audio/mix/pemmican_mix_master.wav \
  -map 0:v -map 1:a -c:v copy -c:a aac -b:a 320k -ar 48000 -ac 2 -shortest -movflags +faststart \
  delivery/The_Pemmican_War_1080p.mp4 && echo "MUX DONE" >> $LOG
