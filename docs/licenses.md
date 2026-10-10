# Sources and licenses

New project sources are licensed under GPL-2.0-only; see [LICENSE](../LICENSE).
The installer and original SMC code come from
[frogro/tinycore-tdm](https://github.com/frogro/tinycore-tdm/tree/ae161a92deb09950d4419b2a60188cc7b92ac623).
The original SMC author is Gabriel L. Somlo; the TDM extension comes from
[floe/smc_util](https://github.com/floe/smc_util). Original copyright and license
notices are preserved in `src/smc/SmcDumpKey.c` and `src/smc/COPYING`.

## Bundled components

| Component | Source | License |
| --- | --- | --- |
| Linux 6.6.8-tinycore64 | Unmodified `boot/vmlinuz` from the pinned upstream commit | GPL-2.0; see kernel sources for details |
| GRUB 2.14-2ubuntu2.1 | EFI image built from Ubuntu modules using `grub-mkstandalone` | GPL-3.0-or-later; see `licenses/grub-copyright.txt` |
| musl 1.2.5-3build1 | Statically linked into the project executables | MIT and included notices; see `licenses/musl-copyright.txt` |

Complete kernel sources, including TinyCore patches and kernel configuration,
GRUB sources with Ubuntu patches, and musl sources are available in the
[source release](https://github.com/frogro/imac-tdm/releases/tag/sources-v1).
Original download URLs and SHA-256 hashes are recorded in
[source-archives.json](../source-archives.json). These are development sources;
the USB installer downloads only the small boot payload.

`scripts/build.py` contains the commands used to build the initramfs and EFI image.
Rebuilding on another distribution may use different musl/GRUB versions and
produce different binaries; that distribution provides the corresponding package
sources. The build explicitly verifies the kernel against `sources.json`.

## Boot artwork

The Apple icon comes from [Simple Icons](https://github.com/simple-icons/simple-icons/blob/develop/icons/apple.svg).
Its CC0 license is in `assets/simple-icons-LICENSE.md`. `assets/splash.svg`
places the icon on a black background. Apple and the Apple logo are trademarks
of Apple Inc.; this project is not affiliated with Apple.
The embedded ASCII font comes from GRUB; its license notices are included in
`licenses/grub-copyright.txt`.

## Kernel modules

The unmodified modules in `vendor/modules/` belong to Linux 6.6.8-tinycore64.
Sources and checksums are recorded in
[`vendor/modules/manifest.json`](../vendor/modules/manifest.json).
CPU modules come from the original TinyCore initramfs; sensor modules come from
the official TinyCore extension `hwmon-6.6.8-tinycore64.tcz`.
Audio modules come from `alsa-modules-6.6.8-tinycore64.tcz`. Its MD5 was checked
against TinyCore's published checksum; SHA-256 hashes also record the archive
and individual modules. Corresponding GPL kernel sources and configuration are
included in the source release linked above.

## Audio runtime

BusyBox (GPL-2.0), ALSA-utils (GPL-2.0), ALSA-lib and glibc (primarily LGPL),
and libsamplerate (BSD-2-Clause) are taken from Ubuntu packages.
Full license notices are in `licenses/`; package versions for the shipped image
are recorded in `vendor/audio-runtime.json`.
Corresponding upstream sources and distribution patches are also available in
the source release and `source-archives.json`. Libraries remain dynamically
linked; the builder can generate a new image using modified libraries.
No signature check prevents such modifications.
