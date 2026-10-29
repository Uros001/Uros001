#!/bin/sh
# Rebuild The_Pemmican_War_1080p.mp4 from its parts and verify the checksum.
set -e
cd "$(dirname "$0")"
cat The_Pemmican_War_1080p.mp4.part-* > The_Pemmican_War_1080p.mp4
echo "aaaae6b118cad54a7ed2fd7eca2ce6d33ab210dc369d2b5c1af98cb940a60cd4  The_Pemmican_War_1080p.mp4" | sha256sum -c -
