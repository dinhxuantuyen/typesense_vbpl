#!/usr/bin/env bash
# Cho job embed_offline hoan tat SACH -> tu dong build index full + build image that.
# Chay nen: setsid nohup bash scripts/auto_finalize.sh > data/build/auto_finalize.log 2>&1 &
set -e
cd "$(dirname "${BASH_SOURCE[0]}")/.."

echo "[auto] $(date '+%F %T') Cho embed_offline hoan tat..."
while pgrep -f embed_offline >/dev/null 2>&1; do sleep 60; done

if ! grep -q '^DONE:' data/build/embed.log; then
  echo "[auto] CANH BAO: khong thay dong 'DONE:' trong embed.log -> embed co the da chet giua chung."
  echo "[auto] Dung auto-finalize. Kiem tra lai roi chay tay: bash scripts/finalize_image.sh"
  exit 1
fi

echo "[auto] $(date '+%F %T') Embed xong. done=$(wc -l < data/build/done.txt). Bat dau finalize..."
bash scripts/finalize_image.sh data/build/embedded.jsonl
echo "[auto] $(date '+%F %T') HOAN TAT. Image 'legal-mcp:latest' san sang."
echo "[auto] Chay: docker run -d --name legal-mcp -p 8000:8000 -e EMBED_API_KEY=sk-xxxx legal-mcp:latest"
