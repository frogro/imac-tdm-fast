# Herkunft und Lizenzen

Die neuen Projektquellen stehen unter GPL-2.0-only, siehe [LICENSE](../LICENSE).
Installer und SMC-Ausgangscode stammen aus
[frogro/tinycore-tdm](https://github.com/frogro/tinycore-tdm/tree/ae161a92deb09950d4419b2a60188cc7b92ac623).
Der ursprüngliche SMC-Autor ist Gabriel L. Somlo; die TDM-Erweiterung stammt aus
[floe/smc_util](https://github.com/floe/smc_util). Die ursprünglichen Copyright-
und Lizenzhinweise bleiben in `src/smc/SmcDumpKey.c` und `src/smc/COPYING` erhalten.

## Mitgelieferte Komponenten

| Komponente | Herkunft | Lizenz |
| --- | --- | --- |
| Linux 6.6.8-tinycore64 | Unverändertes `boot/vmlinuz` aus dem festgelegten Upstream-Commit | GPL-2.0, Details im Kernelquelltext |
| GRUB 2.14-2ubuntu2.1 | EFI-Image aus den Ubuntu-Modulen mit `grub-mkstandalone` erstellt | GPL-3.0-or-later, siehe `licenses/grub-copyright.txt` |
| musl 1.2.5-3build1 | Statisch in die drei Programme eingebunden | MIT und enthaltene Hinweise, siehe `licenses/musl-copyright.txt` |

Die vollständigen Kernelquellen einschließlich TinyCore-Patches und Kernelkonfiguration,
die GRUB-Quellen einschließlich Ubuntu-Patches sowie musl-Quellen sind als Dateien
im [Quellen-Release](https://github.com/frogro/imac-tdm-fast/releases/tag/sources-v1)
verfügbar. Die ursprünglichen Downloadadressen und SHA-256-Werte stehen in
[source-archives.json](../source-archives.json). Das sind Entwicklerquellen;
für die Stick-Installation lädt der Installer nur das kleine Bootpaket.

`scripts/build.py` enthält die Befehle zum Erzeugen des Initramfs und des EFI-Images.
Beim Neubau auf einer anderen Distribution können musl-/GRUB-Versionen und damit
Binärdateien abweichen; die Distribution liefert die dazugehörigen Paketquellen.
Der verwendete Kernel wird beim Neubau ausdrücklich gegen `sources.json` geprüft.

## Startgrafik

Das Apple-Symbol stammt aus [Simple Icons](https://github.com/simple-icons/simple-icons/blob/develop/icons/apple.svg).
Die CC0-Lizenz liegt unter `assets/simple-icons-LICENSE.md`. `assets/splash.svg`
setzt das Symbol auf einen schwarzen Hintergrund. Apple und das Apple-Logo sind
Marken von Apple Inc.; das Projekt steht in keiner Verbindung zu Apple.
Die eingebettete ASCII-Schrift stammt aus dem GRUB-Paket, dessen Lizenzhinweise
unter `licenses/grub-copyright.txt` enthalten sind.

## Kernelmodule

Die vier unveränderten Module unter `vendor/modules/` gehören zu
Linux 6.6.8-tinycore64. Herkunft und Prüfsummen stehen in
[`vendor/modules/manifest.json`](../vendor/modules/manifest.json).
Die CPU-Module stammen aus dem ursprünglichen TinyCore-Initramfs, die
Sensormodule aus der offiziellen TinyCore-Erweiterung `hwmon-6.6.8-tinycore64.tcz`.
Die zugehörigen GPL-Kernelquellen und die Konfiguration sind im oben verlinkten
Quellen-Release enthalten.
