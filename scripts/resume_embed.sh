#!/usr/bin/env bash
# Resume job embed + auto_finalize (chay nen, detached). An toan chay lai nhieu lan.
cd "$(dirname "${BASH_SOURCE[0]}")/.."

if pgrep -f '[l]egal_search.embed_offline' >/dev/null; then
  echo "Embed dang chay san roi."; exit 0
fi

setsid nohup python3 -m legal_search.embed_offline \
  --input ~/tvpl.jsonl --outdir data/build --workers 16 --window 800 \
  > data/build/embed.log 2>&1 < /dev/null &
echo "started embed_offline"
sleep 2

if ! pgrep -f '[a]uto_finalize' >/dev/null; then
  setsid nohup bash scripts/auto_finalize.sh > data/build/auto_finalize.log 2>&1 < /dev/null &
  echo "started auto_finalize"
fi
