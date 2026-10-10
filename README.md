# iMac TDM Fast

Use a **27-inch Late 2009 or Mid 2010 iMac** as a DisplayPort monitor. The system starts automatically in Target Display Mode (TDM). **Video and audio over DisplayPort have been tested on an iMac11,1 with Cirrus CS4206**, with sound through the iMac speakers.

Choose either installation method:

- **USB:** boot from a USB drive and leave the internal disk unchanged.
- **Internal HDD:** install on an internal SATA HDD or SSD and boot without a USB drive.

Both methods run the same TDM system.

## Requirements

- A 27-inch Late 2009 or Mid 2010 iMac; see the tested and untested configurations below. The 21.5-inch 2009 model is not supported.
- A DisplayPort source connected to the iMac's Mini DisplayPort input, using a suitable cable or adapter.

### Tested and potentially compatible models

| Model | Status in this project |
| --- | --- |
| 27-inch Late 2009, `iMac11,1` | **Tested:** DisplayPort video and audio on board `Mac-F2268DAE`, Cirrus CS4206 (codec `1013:4206`, subsystem `106b:5100`). |
| 27-inch Late 2009, `iMac10,1` | **Enabled, not tested:** DisplayPort video switching and experimental CS4206 audio forwarding. Uses the same audio route as `iMac11,1`; sound is not verified on this model. |
| 27-inch Mid 2010, `iMac11,3` | **Enabled, not tested:** DisplayPort video switching and experimental CS4206 audio forwarding. Uses the same route as the tested 2009 model. |
| TDM-capable iMacs from 2011–2013 | **Not supported by this project.** They require Thunderbolt TDM, not the DisplayPort connection used here. |

The CS4206 is not unique to the tested model: [AppleALC documents it in the iMac12,2](https://github.com/acidanthera/AppleALC/blob/master/Resources/PinConfigs.kext/Contents/Info.plist).
A matching codec name does not establish matching audio wiring or TDM support.
Audio is enabled for the tested `iMac11,1` board/codec identifiers and experimentally for `iMac10,1` and `iMac11,3` with a CS4206 codec. These models do not require the `iMac11,1` board or subsystem ID; their input and speaker routing still need a hardware test.
The GPU power-saving workaround and raised fan minima remain specific to the tested `iMac11,1` hardware; they are not applied to the untested models.
The related [gpdm/tinycore-targetdisplaymode project](https://github.com/gpdm/tinycore-targetdisplaymode#does-this-work-on-all-macs) also reports testing only a 2009 iMac; its broader compatibility statement is theoretical. Its [open iMac13,2 / Late 2012 report](https://github.com/gpdm/tinycore-targetdisplaymode/issues/9) documents failed SMC switching. These reports do not establish support for later models in this project.
See also [Apple's TDM connection requirements](https://support.apple.com/en-us/105126) and the [2010 DisplayPort input specification](https://support.apple.com/en-ie/112566).

An HDMI source requires an active HDMI-to-DisplayPort converter compatible with the iMac's input; a passive cable is not sufficient.

## Installation

### Option 1: USB drive

Prepare a USB drive of at least 512 MB on a Linux computer. **The selected USB drive will be erased.**

```bash
sudo apt install python3 curl dosfstools parted util-linux udev
curl -fL https://raw.githubusercontent.com/frogro/imac-tdm/main/scripts/install-usb.py -o install-usb.py
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

**WARNING: A first installation deletes all data and partitions on the selected internal disk. Back up everything you need before booting the installation USB.** An existing marked TDM Fast installation is updated without repartitioning.

The installer accepts **internal SATA HDDs and SSDs from any manufacturer, at least 1 GiB**, in the supported iMac models. It displays the detected model and capacity before starting. USB disks are excluded. If more than one internal SATA disk is present, it stops without choosing one; disconnect the other internal disks before installing. The remaining space beyond the 512 MiB boot partition is left unallocated. Deleting partitions is not a secure overwrite of every data sector.

**Tested on real hardware:** Seagate ST31000528AS, 1 TB. Other brands and capacities are accepted, but have not all been physically tested. Apple offered the 27-inch Late 2009 iMac with a [1 TB HDD or optional 2 TB HDD](https://support.apple.com/en-gb/112564). Normal USB boot leaves the internal disk unchanged.

On an **x86-64 Linux computer** (the commands below use Ubuntu/Debian), prepare the installer from the repository:

```bash
sudo apt install git python3 busybox-static util-linux dosfstools file grub-efi-amd64-bin grub-common parted udev
git clone https://github.com/frogro/imac-tdm.git
cd imac-tdm
python3 scripts/build-disk-installer.py work/internal-installer
sudo python3 scripts/install-usb.py --source work/internal-installer --device /dev/sdX
sudo fatlabel /dev/sdX1 TDMSETUP
```

Replace `/dev/sdX` with the installation USB drive. This is an **automatic installation medium**, not a normal TDM boot drive.

Boot the iMac from this USB drive using **Option/Alt**. Installation starts automatically after a 15-second countdown. When the iMac switches off, remove the USB drive and turn it on again. Select the internal **EFI Boot** entry if necessary.

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
