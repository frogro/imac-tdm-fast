# USB audio diagnostics for the 2009 iMac

This separate test build examines the sound chip and its capture/playback devices
before and after the existing TDM commands. It does not install anything on the
internal disk, record microphone audio, or switch an unknown audio multiplexer.
It performs the experimental HDA/mixer initialization without loading a GPU driver.

Linux boot messages remain visible. About ten seconds after switching to TDM,
the audio test plays three short local beeps, measures the digital input for
three seconds, and forwards digital audio to the speakers for about 45 seconds.
It then synchronizes and unmounts the USB drive and automatically powers off
the iMac. The external picture disappears at that point as expected.

The USB drive receives `audio-diag-1`, `audio-diag-2`, etc., containing `before.txt`,
`after.txt`, `final.txt`, `tdm.txt`, and `COMPLETE.txt`. Only `COMPLETE.txt` confirms
a full run. Reports include the DMI model, board identifier, PCI IDs, ALSA devices,
mixer settings, HDA codec dumps, and kernel messages. Three seconds of digital
input are buffered only in RAM, analyzed for signal levels, and immediately
deleted. No audio data is saved to USB and no microphone input is used.
Review reports before publishing them.

## Build and install

Use x86_64 Linux with `busybox-static`, `alsa-utils`, `pciutils`, Python 3, and
the normal build tools. The builder copies programs and libraries from the build
host; this is a local diagnostic build, not a new prebuilt release.

```sh
python3 scripts/build-audio-diagnostic.py /tmp/audio-test --usb-serial SERIAL_NUMBER
sudo python3 scripts/install-usb.py --source /tmp/audio-test --device /dev/sdX
```

Replace `SERIAL_NUMBER` and `/dev/sdX` with the selected USB drive's details.
Only that drive is reformatted during installation. At boot, the log destination
is verified by USB transport, exact serial number, and the SHA-256 hash of the
matching GRUB configuration. Other detected SATA/NVMe disks are additionally
marked read-only and not mounted. Diagnostics abort if the log destination is missing.

Hold Option/Alt on the iMac and explicitly select the USB drive. The connected
video source can play audio as usual without configuration changes. After automatic
poweroff, connect the USB drive to the analysis computer.

## Test

`python3 scripts/test-audio-diagnostic.py` builds a separate VM image with `--test`.
It skips SMC writes and hardware delays. QEMU checks persistent USB reports,
codec/capture inventory, unchanged bytes on a virtual internal disk, and automatic
poweroff. This does not replace a physical iMac audio-input test.
Do not use `--test` on the iMac.

## Diagnostic digital forwarding test

The separate diagnostic route test is restricted to the hardware identified in
the initial report: iMac11,1, board Mac-F2268DAE, CS4206 subsystem 0x106b5100.
It enables IEC958 Capture, uses device 1 for input and analog device 0 for output,
and sets Master to -12 dB and Speaker/Bass to -6 dB. These values replace the
unsuitable 40% of the numeric control range used in the initial test.
This diagnostic build does not modify the normal boot files.

`route-test.txt` records return codes, digital signal levels, and active PCM
parameters. `alsaloop` compensates for clock differences using mode 1.
The test does not change the DisplayPort mux selection; a silent input may still
indicate missing input selection. Listen for three local beeps followed by audio
from the connected video source. The iMac automatically powers off after about
one to two minutes. A successful virtual test does not establish physical TDM audio support.
