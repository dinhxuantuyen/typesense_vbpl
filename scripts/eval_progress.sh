#!/usr/bin/env bash
PID=$(pgrep -f '[l]egal_search.eval' | head -1)
[ -z "$PID" ] && { echo "eval khong chay"; exit 0; }
A=$(awk '/rchar/{print $2}' /proc/$PID/io)
sleep 8
B=$(awk '/rchar/{print $2}' /proc/$PID/io)
echo "eval PID=$PID | doc them $(( (B-A)/1024 )) KB trong 8s ($([ $B -gt $A ] && echo DANG CHAY || echo CO THE TREO))"
ps -o etime=,rss= -p $PID | awk '{print "runtime:", $1, "| RAM:", int($2/1024), "MB"}'
