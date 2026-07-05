#!/usr/bin/env bash
cd "$(dirname "${BASH_SOURCE[0]}")/.."
A=$(wc -l < data/build/done.txt)
sleep 30
B=$(wc -l < data/build/done.txt)
D=$((B-A))
echo "done hien tai = $B"
echo "delta 30s = $D docs  ->  ~$((D/30))/s"
REM=$((365000-B))
if [ "$D" -gt 0 ]; then
  echo "con lai ~$REM docs  ->  ETA ~$(( REM*30/D/3600 ))h $(( (REM*30/D%3600)/60 ))m"
fi
