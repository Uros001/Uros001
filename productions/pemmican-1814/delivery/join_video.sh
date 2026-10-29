#!/bin/sh
# Rebuild The_Pemmican_War_1080p.mp4 from its parts and verify the checksum.
set -e
cd "$(dirname "$0")"
cat The_Pemmican_War_1080p.mp4.part-* > The_Pemmican_War_1080p.mp4
echo "42525c32d32b1fe3429a9915c47d4583df1c807016497bdbd0abe43cca6bc325  The_Pemmican_War_1080p.mp4" | sha256sum -c -
