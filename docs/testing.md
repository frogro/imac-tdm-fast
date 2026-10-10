# Testing and limitations

## Automated checks

Fourteen Python tests check installer safeguards, device changes before writes,
cancellation and dry runs, copying and checksums, unmount failures, the restricted
download manifest, commit pinning, and the actual contents of the RAM filesystem.
The five project ELF executables have no dynamic interpreter. GRUB checks the
configuration syntax. C programs are built with `-Wall -Wextra -Werror`.

`scripts/test-qemu.py` creates a temporary GPT/FAT32 USB disk and boots it with
x86_64 OVMF, using the shipped EFI bootloader, kernel, and RAM filesystem.
Only the test copy of the GRUB configuration adds a serial console and
`tdm.test=1` to disable all SMC writes.

Initial results from October 3, 2026:

- Firmware → USB boot → GRUB → kernel → minimal `/init` completed successfully.
- The RAM system was ready after about **3.0 seconds of kernel runtime**.
- Total QEMU/OVMF/USB startup to test readiness took about **8.0 seconds**.
- An ACPI power-button event sent through QMP was detected and powered off the VM.

These are software-emulated QEMU timings on the build host, not iMac timings.
The test skips the one-second SMC delay because all SMC access is disabled.
Hardware boot times cannot be inferred from these results.

## Physical hardware checks

The owner confirmed booting, display switching, and audio on the tested iMac11,1.
Physical display switching is not inferred solely from a successful SMC return code.
The additional iMac10,1 and iMac11,3 models are enabled but not hardware-tested.
Checks on each physical setup include:

- Automatic USB priority with the drive inserted and internal OS boot without it.
- Switching from the early RAM system with an active DisplayPort signal.
- A short physical power-button press and the hardware long-press shutdown.
- Time from power-on to the actual external picture.
- Behavior without an input signal and restarting after poweroff.

Using the SHA-256-pinned kernel reduces hardware-related changes.
A custom reduced kernel remains a possible future optimization.

## Architecture

The kernel starts `/init` as PID 1. It mounts only `/proc` and `/sys` and uses
RAM-backed `/dev`. Because the TinyCore kernel does not provide devtmpfs, it
creates input-device nodes from kernel-provided sysfs data.
After direct SMC switching completes, a separate program loads `acpi-cpufreq`,
`cpufreq_powersave`, `coretemp`, and `applesmc` for this exact kernel.
Direct SMC commands and the SMC driver therefore do not run concurrently.
GPU drivers are not included. Internal drives and the USB drive remain unmounted.

A child process executes the original sequence: `MVHR=1`, a one-second delay,
then `MVMR=2`. Errors abort the sequence. Write failures in the inherited SMC
program return an error instead of incorrectly reporting success. Switching
commands are not automatically retried and no unverified status interpretation is used.

PID 1 independently monitors input devices with `KEY_POWER`. A new press requests
`RB_POWER_OFF`. A button held during discovery is armed only after release.
No shutdown services or filesystem backup are needed because the system writes
no persistent data. Long-press shutdown is a hardware function requiring no program.

## Static boot artwork

GRUB enters graphics mode and loads `boot/splash.png`. Linux uses
`gfxpayload=keep`, a serial console, and `fbcon=map:1`; normal messages are kept
off the display. Because the kernel may still clear the framebuffer, `/init`
redraws the logo through `/dev/fb0`. If no supported framebuffer is available,
TDM startup continues without graphics.

The QEMU test reads back the entire display after kernel startup and compares
every RGB pixel with the expected centered logo on black. It then tests the ACPI
power button. `--screenshot /path/image.png` also saves a PNG of the running VM.

## CPU and sensors

Fixture tests check powersave selection, model checks for fan adjustments,
missing sensors, and checksums of shipped kernel modules. QEMU also checks
monitor startup and graceful handling of unsupported virtual sensors.
`tdm.test=1` prevents loading `applesmc`. QEMU cannot verify iMac fan control or temperatures.

A `diagnostics.txt` file on the drive enables a text console and skips display
switching. Without it, normal startup with the logo remains active.
Sensor monitoring does not provide an additional overheating safeguard.
On the tested iMac11,1, fan minima are raised without enabling manual fan mode.
CPU frequency, temperatures, and fan speeds require physical hardware verification.

## Continuous audio forwarding

On October 5, 2026, the owner confirmed local test tones and YouTube audio from
the DisplayPort mini-PC on iMac11,1 / Mac-F2268DAE / Cirrus CS4206 (subsystem 106b5100).
The normal build uses those verified settings: Master -12 dB, Speaker/Bass Speaker
-6 dB, and IEC958 Capture enabled. `alsaloop` connects `hw:0,1` to `plughw:0,0`
using stereo S16_LE at 48 kHz, a 50 ms target buffer, and simple clock synchronization.
The card number is discovered from the codec. There is no microphone forwarding,
test tone, or timed shutdown. The same CS4206 route is now enabled experimentally
on iMac10,1 and iMac11,3; it remains untested on those models.

QEMU checks both PCM directions in RUNNING state, initialization, the unchanged
logo, and ACPI poweroff. Virtual tests do not replace hardware evidence or establish
comprehensive long-term operation with other sources. ALSA processes run alongside
sensor monitoring; disks remain unmounted during normal TDM operation.

## Pause/resume comparison on October 6, 2026

A local 90-second tone on the iMac and the same continuous tone sent from the
Linux mini-PC over DisplayPort were audibly clean. Three pause/resume cycles
with local playback on the mini-PC produced additional audible glitches.
After disabling WirePlumber suspend for that output and setting
`snd_hda_intel.power_save=0`, the owner reported a clean repeat. The ALSA output
remained RUNNING during pauses with an unchanged trigger timestamp.
These comparisons used a 100 ms target buffer on the iMac. The target was then
restored to the original 50 ms. Source-computer instructions are in the README.
Both changes were tested together; their individual contributions were not isolated.
