#!/bin/sh
# Fetch the page scans and OCR word boxes of the 1819 "Report of the proceedings ... York ... October 1818" from the
# Internet Archive (item reportofproceedi00wilc, University of Toronto copy; printed 1819). Then: python3 -I tools/doc_marks.py
# Plain requests, one at a time. The originals (about 25 MB) are not kept in git.
set -eu
cd "$(dirname "$0")/../assets/archival"
mkdir -p ia
B=reportofproceedi00wilc
curl -sS -m 120 -o ia/meta_$B.json "https://archive.org/metadata/$B"
curl -sS -m 300 -o ia/${B}_djvu.xml "https://archive.org/download/$B/${B}_djvu.xml"
for n in 6 19 167; do
  curl -sS -m 120 -o ia/report_n$n.jpg "https://archive.org/download/$B/page/n$n.jpg"
  sleep 2
done
echo "fetched; run: python3 -I tools/doc_marks.py"
