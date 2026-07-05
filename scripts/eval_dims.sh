#!/usr/bin/env bash
# So sanh chat luong theo chieu vector (Matryoshka truncation) tren bo mau.
set -e
cd "$(dirname "${BASH_SOURCE[0]}")/.."
for D in 2560 1024 768; do
  echo "===== EMBED_DIM=$D ====="
  EMBED_DIM=$D python3 -m legal_search.ingest --input data/thuvienphapluat-chunks-sample-100.json --recreate 2>&1 | tail -1
  EMBED_DIM=$D python3 -m legal_search.eval --questions data/eval_questions.json --alpha 0.7 2>&1 | grep -E 'Mode|keyword|vector|hybrid'
  echo
done
