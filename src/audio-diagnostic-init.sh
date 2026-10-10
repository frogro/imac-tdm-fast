#!/bin/busybox sh
export PATH=/bin
/bin/busybox --install -s /bin
mount -t proc proc /proc
mount -t sysfs sysfs /sys
exec </dev/console >/dev/console 2>&1
mkdir -p /dev/snd
mdev -s
fail() { echo "DIAGNOSE ABGEBROCHEN: $*"; echo 'Keine Platte wird installiert.'; sleep 15; poweroff -f; while :; do sleep 60; done; }
# Only the explicitly selected USB disk may receive diagnostic text logs.
serial=$(cat /usb-serial)
usb=''
for attempt in 1 2 3 4 5 6 7 8 9 10; do
 mdev -s
 for d in /sys/block/sd*; do
  [ -f "$d/dev" ] || continue
  link=$(readlink -f "$d/device")
  case "$link" in */usb*/*) ;; *) continue;; esac
  p="$link"; found=''
  while [ "$p" != / ]; do
   if [ -f "$p/serial" ] && [ "$(cat "$p/serial")" = "$serial" ]; then found=yes; break; fi
   p=${p%/*}; [ -n "$p" ] || p=/
  done
  [ "$found" = yes ] || continue
  [ -z "$usb" ] || [ "$usb" = "/dev/${d##*/}" ] || fail 'Mehrere passende USB-Geraete'
  usb=/dev/${d##*/}
 done
 [ -b "${usb}1" ] && break
 sleep 1
done
[ -n "$usb" ] && [ -b "${usb}1" ] || fail 'Erwarteter USB-Stick nicht gefunden'
# Additional read-only guard for every other detected disk.
for d in /sys/block/sd* /sys/block/nvme*n*; do
 [ -f "$d/dev" ] || continue
 [ "/dev/${d##*/}" = "$usb" ] || blockdev --setro "/dev/${d##*/}"
done
mount -t vfat -o ro,nosuid,nodev,noexec "${usb}1" /source || fail 'USB nicht lesbar'
sha256sum -c /expected-grub >/dev/null 2>&1 || { umount /source; fail 'Falsches Diagnose-Bootmedium'; }
mount -o remount,rw /source || fail 'USB nicht beschreibbar'
n=1
while [ -e "/source/audio-diag-$n" ]; do n=$((n+1)); done
out="/source/audio-diag-$n"
mkdir "$out" || fail 'Log-Verzeichnis nicht anlegbar'
echo 'Audio-Diagnose: interne Laufwerke bleiben unangetastet.'
echo "Berichte: audio-diag-$n auf USB. Automatisches Ausschalten nach Abschluss."
report() {
 echo "=== $1 ==="
 for f in sys_vendor product_name board_name bios_version; do printf '%s: ' "$f"; cat /sys/class/dmi/id/$f; done
 lspci -nn
 cat /proc/asound/cards /proc/asound/pcm 2>/dev/null
 aplay -l; arecord -l
 for c in /proc/asound/card[0-9]*; do
  [ -d "$c" ] || continue
  amixer -c "${c##*card}" contents
  for f in "$c"/codec*; do [ -f "$f" ] && { echo "=== $f ==="; cat "$f"; }; done
 done
 [ ! -f /run/audio.txt ] || cat /run/audio.txt
 dmesg
}
model=$(cat /sys/class/dmi/id/product_name)
case " $(cat /proc/cmdline) " in *' diag.test=1 '*) test=yes;; *) test=no;; esac
if [ "$test" = yes ]; then timeout 20 /audio --test; else
 case "$model" in iMac10,1|iMac11,1|iMac11,3) ;; *) umount /source; fail 'Nicht unterstuetztes iMac-Modell';; esac
 [ "$(cat /sys/class/dmi/id/sys_vendor)" = 'Apple Inc.' ] || { umount /source; fail 'Kein Apple iMac'; }
 timeout 20 /audio
fi
mdev -s
report BEFORE_TDM > "$out/before.txt" 2>&1
sync
if [ "$test" != yes ]; then
 { /smc MVHR 1 && sleep 1 && /smc MVMR 2; } > "$out/tdm.txt" 2>&1
 sleep 10
fi
report AFTER_TDM > "$out/after.txt" 2>&1
timeout 85 /audio-route-test.sh "$out" "$test"
echo "ROUTE_SCRIPT_RESULT=$?" > "$out/route-status.txt"
report FINAL > "$out/final.txt" 2>&1
echo 'DIAG_COMPLETE: Digitaler Audiotest abgeschlossen; keine Audio-Mux-Schreibzugriffe.' > "$out/COMPLETE.txt"
sync
umount /source || fail 'USB konnte nicht ausgehaengt werden'
echo 'AUDIO_DIAGNOSTIC_COMPLETE'
poweroff -f
while :; do sleep 60; done
