#!/bin/sh
# Fetch the Smithsonian Open Access (CC0) originals used by tools/prep_archival.py from the public S3 bucket.
set -e
B=https://smithsonian-open-access.s3-us-west-2.amazonaws.com/media
cd "$(dirname "$0")/../assets/archival"
mkdir -p si si_tif
for k in saam/SAAM-1985.66.415_1 saam/SAAM-1985.66.377_1 saam/SAAM-1985.66.434_1 saam/SAAM-1985.66.388_1 sia/SIA-2004-44793; do
  curl -sSf -o si_tif/$(basename $k).tif "$B/$k.tif"
done
for k in saam/SAAM-1985.66.178_1 saam/SAAM-1985.66.181_1 saam/SAAM-1985.66.400_1 saam/SAAM-1985.66.416_1 saam/SAAM-1985.66.424_1 \
         sia/SIA-MNH-3687-000004 sia/SIA-SIA_000095_B43_F01_005 sia/SIA-SIA_000095_B46_F13_014 nzp/NZP-20141105-008CPM; do
  curl -sSf -o si/$(basename $k).jpg "$B/$k.jpg"
done
echo "fetched; catalogue records for the credits are in ARCHIVAL_SOURCES.json"
