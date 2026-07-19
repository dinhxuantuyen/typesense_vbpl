#!/usr/bin/env bash
V=/var/lib/docker/volumes/legal-data/_data
echo "=== Duong dan goc index song (trong WSL) ==="
echo "$V"
echo
echo "=== Cay thu muc + dung luong ==="
sudo -n du -sh "$V" 2>/dev/null || du -sh "$V" 2>/dev/null
echo "--- cac thu muc con ---"
sudo -n du -sh "$V"/* 2>/dev/null || ls -la "$V" 2>/dev/null
echo
echo "=== Vai file .sst thuc te (RocksDB store) ==="
sudo -n find "$V/db" -name "*.sst" 2>/dev/null | head -3
sudo -n ls "$V/state/snapshot" 2>/dev/null
