#!/bin/busybox sh
# Continuous digital-input -> speaker route, verified on iMac11,1/CS4206.
export PATH=/bin
B=/bin/busybox
if [ "$1" = --test ]; then /audio --test; else /audio; fi
[ "$?" = 0 ] || exit 1
$B mdev -s
if [ "$1" = --test ]; then
 card=0; capture=hw:0,0
else
 [ "$($B cat /sys/class/dmi/id/product_name)" = iMac11,1 ] || exit 0
 [ "$($B cat /sys/class/dmi/id/board_name)" = Mac-F2268DAE ] || exit 0
 card=''
 for c in /proc/asound/card[0-9]*; do
  [ -f "$c/codec#0" ] || continue
  $B grep -q '^Vendor Id: 0x10134206$' "$c/codec#0" || continue
  $B grep -q '^Subsystem Id: 0x106b5100$' "$c/codec#0" || continue
  card=${c##*card}; break
 done
 [ -n "$card" ] || exit 1
 capture=hw:$card,1
fi
# Preserve the exact dB settings validated with the owner's YouTube test.
amixer -c "$card" -- sset Master -12dB unmute > /run/audio-route.txt 2>&1 || exit 1
if [ "$1" != --test ]; then
 amixer -c "$card" -- sset Speaker -6dB unmute >> /run/audio-route.txt 2>&1 || exit 1
 amixer -c "$card" -- sset 'Bass Speaker' -6dB unmute >> /run/audio-route.txt 2>&1 || exit 1
 amixer -c "$card" cset name='IEC958 Capture Switch' on >> /run/audio-route.txt 2>&1 || exit 1
fi
# Two rotating RAM logs, at most 256 lines of 512 characters each per file.
$B rm -f /run/audio-log.pipe
$B mkfifo /run/audio-log.pipe || exit 1
# Keep the FIFO open across alsaloop retries.
exec 3<>/run/audio-log.pipe
$B awk '
BEGIN { n=0; slot=0; file="/run/audio-0.log"; printf "" > file }
{
 if(n>=256) {close(file); slot=1-slot; file="/run/audio-" slot ".log"; printf "" > file; n=0}
 print systime(), substr($0,1,512) > file; fflush(file); n++
}' < /run/audio-log.pipe &
logger=$!
trap 'kill "$logger" 2>/dev/null' EXIT
while :; do
 alsaloop -C "$capture" -P "plughw:$card,0" -f S16_LE -r 48000 -c 2 -t 100000 -S 1 -U > /run/audio-log.pipe 2>&1 &
 child=$!
 $B sleep 1
 if [ "$1" = --test ]; then
  $B cat /proc/asound/card"$card"/pcm0c/sub0/status /proc/asound/card"$card"/pcm0p/sub0/status
  echo 'audio-loop: started continuous route'
 fi
 wait "$child"
 echo "alsaloop exited: $?; retrying" > /run/audio-loop.txt
 $B sleep 2
done
