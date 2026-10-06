#!/bin/busybox sh
# Background, one-shot workaround; never delays TDM or changes the audio route.
export PATH=/bin
/bin/busybox mkdir -p /run
exec > /run/gpu-idle.log 2>&1
[ "$(/bin/busybox cat /sys/class/dmi/id/product_name)" = iMac11,1 ] || exit 0
[ "$(/bin/busybox cat /sys/class/dmi/id/board_name)" = Mac-F2268DAE ] || exit 0
case " $(/bin/busybox cat /proc/cmdline) " in *" tdm.gpu_idle=0 "*) exit 0;; esac
n=0
while [ "$n" -lt 30 ]; do
 if /bin/busybox grep -q '^state: RUNNING' /proc/asound/card0/pcm0p/sub0/status 2>/dev/null &&
    /bin/busybox grep -q '^state: RUNNING' /proc/asound/card0/pcm1c/sub0/status 2>/dev/null &&
    [ -r /sys/class/hwmon/hwmon1/device/temp10_input ]; then break; fi
 /bin/busybox sleep 1; n=$((n+1))
done
[ "$n" -lt 30 ] || { echo 'SKIP: audio or thermal monitoring not ready'; exit 0; }
[ "$(/bin/busybox cat /sys/bus/pci/devices/0000:01:00.1/vendor)" = 0x1002 ] || exit 1
[ "$(/bin/busybox cat /sys/bus/pci/devices/0000:01:00.1/device)" = 0xaa30 ] || exit 1
/bin/busybox grep -q '^closed' /proc/asound/card1/pcm3p/sub0/status || exit 1
[ "$(/bin/busybox readlink /sys/bus/pci/devices/0000:01:00.1/driver)" = '../../../../bus/pci/drivers/snd_hda_intel' ] || exit 1
child=
unbound=0
cleanup() {
 trap - EXIT INT TERM HUP
 if [ -n "$child" ]; then kill -TERM "$child" 2>/dev/null; wait "$child"; fi
 if [ "$unbound" = 1 ]; then echo 0000:01:00.1 > /sys/bus/pci/drivers/snd_hda_intel/bind; fi
}
trap cleanup EXIT
trap 'exit 1' INT TERM HUP
echo 0000:01:00.1 > /sys/bus/pci/drivers/snd_hda_intel/unbind || exit 1
unbound=1
/gpu-idle --apply &
child=$!
wait "$child"
result=$?
child=
exit "$result"
