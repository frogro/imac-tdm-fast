#!/bin/busybox sh
# Bounded test: digital capture only, no microphone or raw codec/GPIO writes.
out=$1
test=$2
if [ "$test" = yes ]; then
 card=0; capture=hw:0,0; playback=plughw:0,0; duration=3
else
 [ "$(cat /sys/class/dmi/id/product_name)" = 'iMac11,1' ] || exit 2
 [ "$(cat /sys/class/dmi/id/board_name)" = 'Mac-F2268DAE' ] || exit 2
 card=''
 for c in /proc/asound/card[0-9]*; do
  [ -f "$c/codec#0" ] || continue
  grep -q '^Vendor Id: 0x10134206$' "$c/codec#0" || continue
  grep -q '^Subsystem Id: 0x106b5100$' "$c/codec#0" || continue
  card=${c##*card}; break
 done
 [ -n "$card" ] || exit 2
 capture=hw:$card,1; playback=plughw:$card,0; duration=45
fi
{
 echo "AUDIO_ROUTE_TEST card=$card capture=$capture playback=$playback"
 # dB values, not a fraction of the register range. No microphone gain changes.
 amixer -c "$card" -- sset Master -12dB unmute
 if [ "$test" != yes ]; then
  amixer -c "$card" -- sset Speaker -6dB unmute
  amixer -c "$card" -- sset 'Bass Speaker' -6dB unmute
  amixer -c "$card" cset name='IEC958 Capture Switch' on || exit 3
 fi
 echo 'LOCAL_SPEAKER_TEST_START'
 timeout 8 aplay -D "$playback" /speaker-test.wav
 echo "LOCAL_SPEAKER_TEST_RESULT=$?"
 echo 'DIGITAL_CAPTURE_TEST_START'
 timeout 8 arecord -D "$capture" -f S16_LE -r 48000 -c 2 -d 3 -t raw /run/digital.raw
 rc=$?
 echo "CAPTURE_RESULT=$rc"
 if [ "$rc" = 0 ]; then
  od -An -v -td2 /run/digital.raw | awk '{for(i=1;i<=NF;i++){n++;v=$i;if(v<0)v=-v;if(v>peak)peak=v;if(v!=0)nz++}} END {printf "CAPTURE samples=%d nonzero=%d peak=%d\n",n,nz,peak}'
 fi
 rm -f /run/digital.raw
 echo 'LOOP_START'
 timeout $((duration+8)) alsaloop -C "$capture" -P "$playback" -f S16_LE -r 48000 -c 2 -t 50000 -S 1 -s "$duration" -v &
 loop=$!
 sleep 1
 cat /proc/asound/card"$card"/pcm*/sub*/status /proc/asound/card"$card"/pcm*/sub*/hw_params 2>/dev/null
 wait "$loop"
 echo "LOOP_RESULT=$?"
 echo 'AUDIO_ROUTE_TEST_FINISHED'
} > "$out/route-test.txt" 2>&1
