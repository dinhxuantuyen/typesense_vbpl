#!/usr/bin/env bash
# Chi dung auto_finalize, KHONG dung embed.
for p in $(pgrep -f "[a]uto_finalize"); do kill "$p" 2>/dev/null; done
sleep 1
pgrep -f "[a]uto_finalize" >/dev/null && echo "auto_finalize: STILL RUNNING" || echo "auto_finalize: STOPPED"
echo -n "embed alive: "; pgrep -f "[l]egal_search.embed_offline" >/dev/null && echo YES || echo NO
