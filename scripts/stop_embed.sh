#!/usr/bin/env bash
cd "$(dirname "${BASH_SOURCE[0]}")/.."
for p in $(pgrep -f '[a]uto_finalize'); do kill "$p" 2>/dev/null; done
for p in $(pgrep -f '[l]egal_search.embed_offline'); do kill "$p" 2>/dev/null; done
sleep 3
echo -n 'embed: ';         pgrep -f '[l]egal_search.embed_offline' >/dev/null && echo STILL_ALIVE || echo STOPPED
echo -n 'auto_finalize: '; pgrep -f '[a]uto_finalize' >/dev/null && echo STILL_ALIVE || echo STOPPED
echo -n 'done.txt (checkpoint) = '; wc -l < data/build/done.txt
