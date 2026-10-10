# Live audio analysis over SSH

The separate diagnostic build boots directly into TDM with the same audio route
as the normal version. It also obtains an IP address over Ethernet/DHCP and starts
SSH. It produces no test tones, does not shut down automatically, and does not
install anything on the internal disk. The video source needs no changes.

Connect the iMac by Ethernet to the same router as the analysis computer.
Find the new Ethernet device in the router. Log in as `root` using the SSH key
specified at build time; password authentication and port forwarding are disabled.
The normal TDM build does not include this SSH access.

## Build a private image

Use x86_64 Linux with the normal build dependencies plus `dropbear-bin` and
`openssh-client`:

```sh
python3 scripts/build-ssh-diagnostic.py /tmp/tdm-ssh \
  --authorized-key ~/.ssh/id_ed25519.pub
python3 scripts/test-ssh-diagnostic.py /tmp/tdm-ssh \
  --identity ~/.ssh/id_ed25519
sudo python3 scripts/install-usb.py --source /tmp/tdm-ssh --device /dev/sdX
```

Replace `/dev/sdX` with the selected USB drive. **The drive will be erased.**
On the iMac, use Option/Alt to explicitly boot this USB drive; the internal
installation remains unchanged. The filesystem label stays `TDMFAST`, not
`TDMSETUP`. Remove the drive to return to the internal version.

The builder generates a dedicated SSH host key for this image.
**The generated image is private and must not be published on GitHub:** it contains
the host key and the authorized public user key. The private user key is neither
read nor copied to the drive. `ssh-host-key.pub` in the output directory contains
the public server identity for verification.

## Connect and inspect

Replace `192.168.178.X` with the address shown by the router.
First compare the server fingerprint with the locally generated file:

```sh
ssh-keygen -lf /tmp/tdm-ssh/ssh-host-key.pub
ssh -i ~/.ssh/id_ed25519 root@192.168.178.X
```

In the SSH shell:

```sh
tdm-audio-status
cat /run/ssh.log
cat /run/audio-loop.txt
```

`tdm-audio-status` reads mixer settings, PCM state and buffer parameters,
the process list, and temperature logs. It does not change controls or start
recording. To capture a time series on the analysis computer:

```sh
ssh root@192.168.178.X 'while :; do tdm-audio-status; sleep 2; done' > audio-live.txt
```

Stop with Ctrl+C and note the times of audible fluctuations. Logs on the iMac
exist only in RAM and disappear at poweroff. The SSH shell has administrator
privileges; disk-writing commands are not part of this analysis.

## Implementation and testing

The `tg3` (physical Broadcom Ethernet) and `e1000` (QEMU) network modules come
from the existing TinyCore 6.6.8 initramfs. Their source and SHA-256 hashes are
recorded in `vendor/network/manifest.json`. Kernel sources are already included
in the source release. Dropbear and its libraries come from the build host and
retain their package licenses. `--tools-root` accepts a directory of extracted
packages instead of installed packages.

QEMU checks DHCP, SSH with a pinned server identity, an interactive shell,
running audio streams, and the absence of mounted data disks. Physical Ethernet
connectivity and the cause of volume fluctuations require testing on the iMac.
