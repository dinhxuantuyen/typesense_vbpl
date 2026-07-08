#!/usr/bin/env bash
for p in $(pgrep -f '[l]egal_search.eval'); do kill "$p" 2>/dev/null; done
sleep 2
pgrep -f '[l]egal_search.eval' >/dev/null && echo "eval: STILL RUNNING" || echo "eval: STOPPED"
