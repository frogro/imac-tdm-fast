#!/bin/busybox sh
export PATH=/bin
case "$1" in
 deconfig) ifconfig "$interface" 0.0.0.0 ;;
 bound|renew)
  ifconfig "$interface" "$ip" netmask "$subnet"
  route del default dev "$interface" 2>/dev/null || true
  for gw in $router; do route add default gw "$gw" dev "$interface" && break; done
  echo "$interface $ip" > /run/ssh-address.txt
 ;;
esac
