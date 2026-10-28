#!/bin/sh
# Split a large deliverable into <95 MB parts (GitHub file limit; LFS unavailable here) and write a join script.
set -e
f="$1"; d=$(dirname "$f"); b=$(basename "$f")
cd "$d"
rm -f "$b".part-*
split -b 95m -d -a 2 "$b" "$b.part-"
sha=$(sha256sum "$b" | cut -d' ' -f1)
cat > join_video.sh <<EOS
#!/bin/sh
# Rebuild $b from its parts and verify the checksum.
set -e
cd "\$(dirname "\$0")"
cat $b.part-* > $b
echo "$sha  $b" | sha256sum -c -
EOS
chmod +x join_video.sh
ls -la "$b".part-* | awk '{print $5, $9}'
