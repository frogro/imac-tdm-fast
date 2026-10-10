#!/bin/busybox sh
# SPDX-License-Identifier: GPL-2.0-only
# Dedicated installer for a single internal SATA disk in a supported iMac.
export PATH=/bin
/bin/busybox --install -s /bin
mount -t proc proc /proc
mount -t sysfs sysfs /sys
# TinyCore's kernel has no devtmpfs; populate the RAM /dev using sysfs.
mdev -s
exec </dev/console >/dev/console 2>&1
fail() {
    echo "INSTALLATION STOPPED: $*"
    echo 'No further writes. Hold the power button to switch off.'
    while :; do sleep 3600; done
}
finish() {
    sync
    echo "$*"
    echo 'Remove the USB drive after shutdown, then turn on the iMac.'
    sleep 5
    poweroff -f
    fail 'Poweroff failed'
}
echo 'iMac TDM Fast - one-time installation to an internal SATA disk'
[ "$(cat /sys/class/dmi/id/sys_vendor)" = 'Apple Inc.' ] || fail 'Not an Apple iMac'
case "$(cat /sys/class/dmi/id/product_name)" in iMac10,1|iMac11,1|iMac11,3) ;; *) fail 'Unsupported iMac model';; esac
# Wait for USB and SATA enumeration, bounded to 30 seconds.
tries=0
while :; do
    mdev -s
    sources=$(blkid | sed -n '/LABEL="TDMSETUP"/s/:.*//p')
    [ -n "$sources" ] && break
    tries=$((tries+1)); [ "$tries" -lt 30 ] || fail 'Installation USB drive not found'
    sleep 1
done
[ "$(echo "$sources" | wc -l)" -eq 1 ] || fail 'Multiple installation USB drives found'
source_device=$sources
mount -t vfat -o rw,nosuid,nodev,noexec "$source_device" /source || fail 'USB drive is not writable'
if [ -f /source/INSTALLATION_STARTED ] || [ -f /source/INSTALLATION_DONE ]; then
    umount /source || fail 'Unmount USB drive'
    finish 'This USB drive has already been used. No further erasure.'
fi
(cd /payload && sha256sum -c SHA256SUMS) || fail 'Damaged installation files'
# SATA only, nonremovable, exactly one candidate; no vendor or capacity whitelist.
target=''
for disk in /sys/block/sd*; do
    [ -e "$disk/device/model" ] || continue
    [ "$(cat "$disk/removable")" = 0 ] || continue
    real=$(readlink -f "$disk/device")
    case "$real" in */usb*) continue;; esac
    case "$real" in */ata*/*) ;; *) continue;; esac
    [ -z "$target" ] || fail 'Multiple internal SATA disks: target is ambiguous. Disconnect other internal disks before installation.'
    target=/dev/${disk##*/}
done
[ -n "$target" ] || fail 'No internal SATA disk found'
model=$(cat /sys/class/block/${target##*/}/device/model)
sectors=$(cat /sys/class/block/${target##*/}/size)
[ "$sectors" -ge 2097152 ] || fail 'Internal disk is smaller than 1 GiB'
size_mib=$((sectors / 2048))
source_parent=$(basename "$(dirname "$(readlink -f /sys/class/block/${source_device##*/})")")
[ "$target" != "/dev/$source_parent" ] || fail 'Source and target are identical'
# A marked installation can be updated without repartitioning.
installed_partition=
for partition in /sys/class/block/${target##*/}[0-9]*; do
    [ -e "$partition/partition" ] || continue
    if mount -t vfat -o ro,nosuid,nodev,noexec "/dev/${partition##*/}" /target 2>/dev/null; then
        if [ -e /target/TDM_FAST_INSTALLED ]; then
            [ -z "$installed_partition" ] || fail 'Multiple marked installations found'
            if (cd /target && sha256sum -c /payload/SHA256SUMS) >/dev/null 2>&1; then
                umount /target || fail 'Unmount target'
                umount /source || fail 'Unmount USB drive'
                finish 'TDM Fast is already installed. Current version; no changes.'
            fi
            installed_partition=/dev/${partition##*/}
        fi
        umount /target || fail 'Unmount target'
    fi
done
echo "Target: $target - $model, $size_mib MiB"
if [ -n "$installed_partition" ]; then
    echo 'Updating the existing TDM Fast installation. Partition layout will be preserved.'
else
    echo 'WARNING: ALL DATA ON THE TARGET DISK WILL BE ERASED.'
    echo 'All existing partitions and filesystems will be removed. Back up your data first.'
fi
echo 'Starting in 15 seconds. To cancel, switch off now (hold the power button).'
sleep 15
# A durable one-shot latch BEFORE the first internal-disk write. A failed or
# interrupted attempt requires manually preparing the installer again.
printf 'target=%s\nmodel=%s\nsize_mib=%s\n' "$target" "$model" "$size_mib" > /source/INSTALLATION_STARTED || fail 'USB start marker'
sync
umount /source || fail 'Could not safely save the start marker'
mount -t vfat -o rw,nosuid,nodev,noexec "$source_device" /source || fail 'Remount USB drive'
[ -s /source/INSTALLATION_STARTED ] || fail 'Start marker missing'
if [ -z "$installed_partition" ]; then
# Remove filesystem signatures at former partition starts before replacing GPT.
for partition in /sys/class/block/${target##*/}[0-9]*; do
    [ -e "$partition/partition" ] || continue
    dd if=/dev/zero of="/dev/${partition##*/}" bs=512 count=2048 || fail 'Old partition signature'
done
sectors=$(cat /sys/class/block/${target##*/}/size)
dd if=/dev/zero of="$target" bs=1M count=16 || fail 'Start of disk'
dd if=/dev/zero of="$target" bs=512 seek=$((sectors-2048)) count=2048 || fail 'End of disk'
printf 'label: gpt\n\nstart=1MiB,size=512MiB,type=U\n' | sfdisk --wipe always --wipe-partitions always "$target" || fail 'Create GPT'
sync
mdev -s
partition=${target}1
[ -b "$partition" ] || fail 'New EFI partition missing'
mkfs.fat -F 32 -n TDMFAST "$partition" || fail 'EFI filesystem'
else
    partition=$installed_partition
fi
mount -t vfat -o rw,nosuid,nodev,noexec "$partition" /target || fail 'Mount EFI partition'
cp -R /payload/EFI /payload/boot /payload/grub.cfg /payload/SHA256SUMS /target/ || fail 'Copy files'
(cd /target && sha256sum -c SHA256SUMS) || fail 'Checksums'
echo 'iMac TDM Fast installed by one-shot installer v2' > /target/TDM_FAST_INSTALLED || fail 'Target marker'
sync
umount /target || fail 'Unmount EFI partition'
# Re-read the files after unmounting to check the installed filesystem.
mount -t vfat -o ro,nosuid,nodev,noexec "$partition" /target || fail 'Mount EFI partition for readback'
(cd /target && sha256sum -c SHA256SUMS) || fail 'Readback checksums'
umount /target || fail 'Unmount EFI partition after verification'
echo 'Installation successful' > /source/INSTALLATION_DONE || fail 'USB completion marker'
sync
umount /source || fail 'Final USB unmount'
finish 'SUCCESS: TDM Fast installed internally and verified.'
