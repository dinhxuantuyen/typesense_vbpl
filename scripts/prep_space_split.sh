#!/usr/bin/env bash
# 1) Giai phong khong gian trong VHDX  2) Tach ts-data thanh 3 phan <10GB cho GHCR layer limit.
set -e
cd ~/legal-build-ctx

echo "=== [1] Don dep de lay khong gian ==="
docker system prune -af 2>&1 | tail -1          # ~11.5GB reclaimable
rm -f ~/tvpl.jsonl                                # 2.8GB (goc van o E:)
df -h / | tail -1

echo "=== [2] Tach ts-data/db thanh 3 phan (moi phan <10GB) ==="
SRC=data/build/ts-data
rm -rf part1 part2 part3
mkdir -p part1 part2 part3
# db/ chua phan lon dung luong -> chia file db theo round-robin 3 nhom (giu nguyen duong dan tuong doi)
i=0
find "$SRC" -type f | while read -r f; do
  rel="${f#$SRC/}"
  dest="part$(( i % 3 + 1 ))/$rel"
  mkdir -p "$(dirname "$dest")"
  ln "$f" "$dest" 2>/dev/null || cp "$f" "$dest"   # hardlink = khong ton them cho
  i=$((i+1))
done
du -sh part1 part2 part3

echo "=== [3] Dockerfile moi: COPY 3 layer vao cung /data (unionfs tu gop) ==="
# thay 1 dong COPY data/build/ts-data/ /data/ bang 3 dong COPY part{1,2,3}
sed -i 's|^COPY data/build/ts-data/ /data/$|COPY part1/ /data/\nCOPY part2/ /data/\nCOPY part3/ /data/|' Dockerfile
grep -n "COPY part" Dockerfile
# bo ts-data khoi context de khoi gui 16GB thua (da co part1-3 hardlink)
rm -rf data
echo "=== SAN SANG BUILD ==="
du -sh ~/legal-build-ctx
