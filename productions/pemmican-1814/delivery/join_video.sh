#!/bin/sh
# Rebuild The_Pemmican_War_1080p.mp4 from its parts and verify the checksum.
set -e
cd "$(dirname "$0")"
cat The_Pemmican_War_1080p.mp4.part-* > The_Pemmican_War_1080p.mp4
echo "d71172f55cc7debf1fd0a227ae374ba190f3eaa518ff3660615a0bef4068baa1  The_Pemmican_War_1080p.mp4" | sha256sum -c -
