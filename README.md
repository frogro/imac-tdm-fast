# iMac TDM Fast

Use a **27-inch Late 2009 iMac** as a DisplayPort monitor. The system starts automatically in Target Display Mode (TDM), with **video and audio over DisplayPort** and sound through the iMac speakers.

Choose either installation method:

- **USB:** boot from a USB drive and leave the internal disk unchanged.
- **Internal HDD:** install on the supported internal disk and boot without a USB drive.

Both methods run the same TDM system.

## Requirements

- A 27-inch Late 2009 iMac (`iMac10,1` or `iMac11,1`). The 21.5-inch model is not supported.
- A DisplayPort source connected to the iMac's Mini DisplayPort input, using a suitable cable or adapter.
- Audio forwarding is supported on `iMac11,1` with the Cirrus CS4206 audio codec.

An HDMI source requires an active HDMI-to-DisplayPort converter compatible with the iMac's input; a passive cable is not sufficient.

## Installation

### Option 1: USB drive

Prepare a USB drive of at least 512 MB on a Linux computer. **The selected USB drive will be erased.**

```bash
sudo apt install python3 dosfstools parted util-linux udev
curl -fL https://raw.githubusercontent.com/frogro/imac-tdm-fast/main/scripts/install-usb.py -o install-usb.py
python3 install-usb.py --list
```

Replace `/dev/sdX` with the whole USB device, unmount its partitions, then run:

```bash
python3 install-usb.py --device /dev/sdX --dry-run
sudo python3 install-usb.py --device /dev/sdX
```

The installer verifies the downloaded files and asks you to type `LOESCHEN /dev/sdX` before erasing the selected drive.

Insert the drive into the powered-off iMac and turn it on. If necessary, hold **Option/Alt** and select **EFI Boot**.

### Option 2: Internal HDD

Use a separate, one-time installation USB drive to install the same system on the internal HDD. After installation, remove the USB drive and boot from the internal disk.

**The internal installer currently accepts only a Seagate ST31000528AS 1 TB SATA disk in a supported iMac. A first installation erases that disk. Back up its contents first.** An existing marked TDM Fast installation is updated without repartitioning.

On a Linux computer, prepare the installer from the repository:

```bash
git clone https://github.com/frogro/imac-tdm-fast.git
cd imac-tdm-fast
sudo apt install python3 busybox-static util-linux dosfstools file grub-efi-amd64-bin grub-common parted udev
python3 scripts/build-disk-installer.py work/internal-installer
sudo python3 scripts/install-usb.py --source work/internal-installer --device /dev/sdX
sudo fatlabel /dev/sdX1 TDMSETUP
```

Replace `/dev/sdX` with the installation USB drive. This is an **automatic installation medium**, not a normal TDM boot drive.

Boot the iMac from this USB drive using **Option/Alt**. Installation starts automatically after a 15-second countdown. When the iMac switches off, remove the USB drive and turn it on again. Select the internal **EFI Boot** entry if necessary.

See the [internal installer instructions](docs/internal-installer.md) for supported disks, updates and recovery details.

## Everyday use

1. Connect the DisplayPort source to the iMac.
2. Turn on the iMac and boot the selected USB or internal installation.
3. The display switches automatically to the external source.
4. Select the DisplayPort audio output on the source computer and adjust volume there.
5. Briefly press the iMac's power button to switch it off. Hold it down only if a forced shutdown is needed.

To save the preferred boot device, hold **Option/Alt** at startup, select its EFI entry, then hold **Control** while starting it. Check that the firmware retains the selection on the next boot.

## Linux audio: avoid dropouts after pauses

Apply these settings on the **source computer**, not on the iMac, if DisplayPort audio drops out after pausing and resuming playback.

### PipeWire with WirePlumber 0.5

Find the output name:

```bash
pactl list short sinks
mkdir -p ~/.config/wireplumber/wireplumber.conf.d
```

Create `~/.config/wireplumber/wireplumber.conf.d/51-imac-displayport-no-suspend.conf`:

```ini
monitor.alsa.rules = [
  {
    matches = [ { node.name = "YOUR_DISPLAYPORT_OUTPUT" } ]
    actions = {
      update-props = {
        session.suspend-timeout-seconds = 0
        node.pause-on-idle = false
      }
    }
  }
]
```

Replace `YOUR_DISPLAYPORT_OUTPUT` with the full sink name. DisplayPort outputs may have `hdmi` in their names. Apply the change with:

```bash
systemctl --user restart wireplumber
```

This briefly interrupts audio; restart playback if needed.

### Sources using the `snd_hda_intel` driver

If `/sys/module/snd_hda_intel/parameters/power_save` exists, record its current value and back up any existing configuration file before applying:

```bash
# Apply immediately:
echo 0 | sudo tee /sys/module/snd_hda_intel/parameters/power_save
# Keep the setting after reboot:
echo 'options snd_hda_intel power_save=0' | sudo tee /etc/modprobe.d/99-tdm-audio-powersave.conf
# Ubuntu/Debian:
sudo update-initramfs -u
```

This applies to all audio devices managed by that driver. Other distributions may use a different initramfs update command.

To undo the changes, remove the newly created files or restore their backups, restart WirePlumber, update the initramfs and reboot.

References: [WirePlumber ALSA configuration](https://pipewire.pages.freedesktop.org/wireplumber/daemon/configuration/alsa.html) and [Linux HD-audio configuration](https://docs.kernel.org/sound/designs/powersave.html).

## License

See [LICENSE](LICENSE) and [third-party component licenses](docs/licenses.md).
