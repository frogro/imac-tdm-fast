#!/bin/busybox sh
# SPDX-License-Identifier: GPL-2.0-only
# Dedicated installer for the explicitly approved late-2009 iMac disk.
export PATH=/bin
/bin/busybox --install -s /bin
mount -t proc proc /proc
mount -t sysfs sysfs /sys
# TinyCore's kernel has no devtmpfs; populate the RAM /dev using sysfs.
mdev -s
exec </dev/console >/dev/console 2>&1
fail() {
    echo "INSTALLATION GESTOPPT: $*"
    echo 'Keine weiteren Schreibzugriffe. Zum Ausschalten Powerknopf lange halten.'
    while :; do sleep 3600; done
}
finish() {
    sync
    echo "$*"
    echo 'USB-Stick nach dem Ausschalten abziehen. Danach iMac einschalten.'
    sleep 5
    poweroff -f
    fail 'Ausschalten fehlgeschlagen'
}
echo 'iMac TDM Fast - einmalige Installation auf interne Seagate 1 TB'
[ "$(cat /sys/class/dmi/id/sys_vendor)" = 'Apple Inc.' ] || fail 'Kein Apple-iMac'
case "$(cat /sys/class/dmi/id/product_name)" in iMac10,1|iMac11,1) ;; *) fail 'Falsches iMac-Modell';; esac
# Wait for USB and SATA enumeration, bounded to 30 seconds.
tries=0
while :; do
    mdev -s
    sources=$(blkid | sed -n '/LABEL="TDMSETUP"/s/:.*//p')
    [ -n "$sources" ] && break
    tries=$((tries+1)); [ "$tries" -lt 30 ] || fail 'Installationsstick fehlt'
    sleep 1
done
[ "$(echo "$sources" | wc -l)" -eq 1 ] || fail 'Mehrere Installationssticks'
source_device=$sources
mount -t vfat -o rw,nosuid,nodev,noexec "$source_device" /source || fail 'USB nicht beschreibbar'
if [ -f /source/INSTALLATION_STARTED ] || [ -f /source/INSTALLATION_DONE ]; then
    umount /source || fail 'USB aushaengen'
    finish 'Dieser Stick wurde bereits verwendet. Keine erneute Loeschung.'
fi
(cd /payload && sha256sum -c SHA256SUMS) || fail 'Beschaedigte Installationsdateien'
# SATA only, exact model, nonremovable, one candidate, expected 1-TB capacity.
target=''
for disk in /sys/block/sd*; do
    [ -e "$disk/device/model" ] || continue
    model=$(cat "$disk/device/model" | tr -d ' ')
    [ "$model" = ST31000528AS ] || continue
    [ "$(cat "$disk/removable")" = 0 ] || continue
    real=$(readlink -f "$disk/device")
    case "$real" in */usb*) continue;; esac
    case "$real" in */ata*/*) ;; *) continue;; esac
    sectors=$(cat "$disk/size")
    [ "$sectors" -ge 1950000000 ] && [ "$sectors" -le 1960000000 ] || continue
    [ -z "$target" ] || fail 'Mehrere passende interne Platten'
    target=/dev/${disk##*/}
done
[ -n "$target" ] || fail 'Interne ST31000528AS mit 1 TB nicht gefunden'
source_parent=$(basename "$(dirname "$(readlink -f /sys/class/block/${source_device##*/})")")
[ "$target" != "/dev/$source_parent" ] || fail 'Quelle und Ziel sind identisch'
# Refuse repeat installations on an already installed internal disk, even with a fresh USB.
for partition in /sys/class/block/${target##*/}[0-9]*; do
    [ -e "$partition/partition" ] || continue
    if mount -t vfat -o ro,nosuid,nodev,noexec "/dev/${partition##*/}" /target 2>/dev/null; then
        if [ -e /target/TDM_FAST_INSTALLED ]; then
            umount /target || fail 'Ziel aushaengen'
            umount /source || fail 'USB aushaengen'
            finish 'TDM Fast ist bereits installiert. Keine erneute Loeschung.'
        fi
        umount /target || fail 'Ziel aushaengen'
    fi
done
echo "Ziel: $target - Seagate ST31000528AS, 1 TB"
echo 'ALLE BISHERIGEN PARTITIONEN UND DATEISYSTEME AUF DIESEM LAUFWERK WERDEN ENTFERNT.'
echo 'Start in 15 Sekunden. Zum Abbrechen jetzt ausschalten (Powerknopf lange halten).'
sleep 15
# A durable one-shot latch BEFORE the first internal-disk write. A failed or
# interrupted attempt requires manually preparing the installer again.
printf 'target=%s\nmodel=ST31000528AS\n' "$target" > /source/INSTALLATION_STARTED || fail 'USB-Startmarker'
sync
umount /source || fail 'Startmarker konnte nicht sicher gespeichert werden'
mount -t vfat -o rw,nosuid,nodev,noexec "$source_device" /source || fail 'USB erneut einbinden'
[ -s /source/INSTALLATION_STARTED ] || fail 'Startmarker fehlt'
# Remove filesystem signatures at former partition starts before replacing GPT.
for partition in /sys/class/block/${target##*/}[0-9]*; do
    [ -e "$partition/partition" ] || continue
    dd if=/dev/zero of="/dev/${partition##*/}" bs=512 count=2048 || fail 'Alte Partitionssignatur'
done
sectors=$(cat /sys/class/block/${target##*/}/size)
dd if=/dev/zero of="$target" bs=1M count=16 || fail 'Plattenanfang'
dd if=/dev/zero of="$target" bs=512 seek=$((sectors-2048)) count=2048 || fail 'Plattenende'
printf 'label: gpt\nunit: sectors\n\nstart=2048,size=1048576,type=U\n' | sfdisk --wipe always --wipe-partitions always "$target" || fail 'GPT anlegen'
sync
mdev -s
partition=${target}1
[ -b "$partition" ] || fail 'Neue EFI-Partition fehlt'
mkfs.fat -F 32 -n TDMFAST "$partition" || fail 'EFI-Dateisystem'
mount -t vfat -o rw,nosuid,nodev,noexec "$partition" /target || fail 'EFI einbinden'
cp -R /payload/EFI /payload/boot /payload/grub.cfg /payload/SHA256SUMS /target/ || fail 'Dateien kopieren'
(cd /target && sha256sum -c SHA256SUMS) || fail 'Pruefsummen'
echo 'iMac TDM Fast installed by one-shot installer v1' > /target/TDM_FAST_INSTALLED || fail 'Zielmarker'
sync
umount /target || fail 'EFI aushaengen'
# Re-read the files after unmounting to check the installed filesystem.
mount -t vfat -o ro,nosuid,nodev,noexec "$partition" /target || fail 'EFI Kontrolllesen'
(cd /target && sha256sum -c SHA256SUMS) || fail 'Kontroll-Pruefsummen'
umount /target || fail 'EFI nach Kontrolle aushaengen'
echo 'Installation erfolgreich' > /source/INSTALLATION_DONE || fail 'USB-Endmarker'
sync
umount /source || fail 'USB abschliessend aushaengen'
finish 'ERFOLGREICH: TDM Fast intern installiert und geprueft.'
