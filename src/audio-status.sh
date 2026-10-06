#!/bin/busybox sh
export PATH=/bin
# Read-only snapshot: no mixer writes, no recording and no process restart.
date
cat /run/ssh-address.txt /run/audio.txt /run/audio-route.txt /run/audio-loop.txt 2>/dev/null
for c in /proc/asound/card[0-9]*; do
 card=${c##*card}
 echo "=== Card $card mixer ==="
 amixer -c "$card" contents
 cat "$c"/pcm*/sub*/status "$c"/pcm*/sub*/hw_params 2>/dev/null
done
ps
cat /run/health.txt 2>/dev/null
