#!/usr/bin/env bash
PID=$(pgrep -f '[m]ainstream_extract' | head -1)
[ -z "$PID" ] && { echo "pass1 khong chay (co the xong)"; tail -14 /mnt/d/claude_code/typesense/data/build/pass1.log; exit 0; }
A=$(awk '/rchar/{print $2}' /proc/$PID/io)
sleep 8
B=$(awk '/rchar/{print $2}' /proc/$PID/io)
GB=$(awk "BEGIN{print ($B)/1073741824}")
echo "PID=$PID | da doc ~${GB} GB / 19GB | toc do $(( (B-A)/1024/1024 )) MB/8s"
ps -o etime=,rss= -p $PID | awk '{print "runtime:",$1,"| RAM:",int($2/1024),"MB"}'
