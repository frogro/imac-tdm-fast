#!/bin/busybox sh
# Optional RAM-only LAN/SSH diagnostic. Never mount a data disk.
export PATH=/bin
busybox --install -s /bin
mkdir -p /dev/pts /tmp /root/.ssh /etc/dropbear /var/run
chmod 1777 /tmp
mdev -s
mount -t devpts devpts /dev/pts
[ -c /dev/ptmx ] || mknod /dev/ptmx c 5 2
exec >>/run/ssh.log 2>&1
insmod /network/tg3.ko || true
insmod /network/e1000.ko || true
hostname tdm-imac
ifconfig lo up
# DHCP runs independently of TDM/audio and retries if the LAN cable arrives later.
for net in /sys/class/net/*; do
 interface=${net##*/}
 [ -e "$net/device" ] || continue
 ifconfig "$interface" up
 udhcpc -x hostname:tdm-imac -i "$interface" -s /dhcp.sh -p /run/dhcp-$interface.pid -t 3 -T 3 -A 10 -S &
done
exec dropbear -F -E -s -j -k -r /etc/dropbear/hostkey -P /run/dropbear.pid
