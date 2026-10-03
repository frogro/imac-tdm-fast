# Einmaliger Installer fuer die interne iMac-Platte

Dieser Modus ist ausschliesslich fuer den freigegebenen iMac mit interner
**Seagate ST31000528AS, 1 TB, SATA** bestimmt. Er entfernt beim Start automatisch
alle bisherigen Partitionen auf dieser Platte. **Keine Datensicherung ist enthalten.**
Andere Modelle, USB-Ziellaufwerke und mehrere passende Platten werden abgelehnt.
Die Modellkennung des iMac muss `iMac10,1` oder `iMac11,1` sein; unterstuetzt ist
nur der 27-Zoll-iMac von Ende 2009.

Der Stick zeigt das Ziel an und wartet 15 Sekunden. In dieser Zeit kann man durch
langes Druecken des Powerknopfs ausschalten. Danach legt er eine GPT mit einer
512-MiB-FAT32-EFI-Partition an und installiert die normale TDM-Fast-Fassung.
Der Rest der Platte bleibt unpartitioniert. Partitionstabellen und alte
Dateisystemsignaturen werden entfernt; dies ist **keine sichere Vollueberschreibung**
der persoenlichen Daten auf der gesamten 1-TB-Platte.

Nach Kopieren und erneutem Lesen mit SHA-256-Pruefung schaltet sich der iMac aus.
Den USB-Stick abziehen und den iMac wieder einschalten. Falls die Mac-Firmware
die interne Installation nicht selbst findet, mit Alt/Option starten und den
internen EFI-Boot-Eintrag waehlen. Der Installer veraendert keine NVRAM-Startauswahl.

## Schutz gegen Wiederholung

Vor dem ersten Schreibzugriff auf die interne Platte wird `INSTALLATION_STARTED`
auf dem USB-Stick geschrieben, ausgehangen, erneut eingebunden und kontrolliert.
Ist dieser Marker bei einem spaeteren Start vorhanden, wird nichts mehr geloescht.
Das gilt auch nach einer fehlgeschlagenen oder unterbrochenen Installation.
Ein frischer Installationsstick erkennt ausserdem `TDM_FAST_INSTALLED` auf der
internen EFI-Partition und verweigert eine erneute Installation.

Zum bewussten Wiederholen nach einem Fehler muss der Stick neu vorbereitet werden.
Die Fehlermeldung vorher klaeren; Marker nicht einfach unbeaufsichtigt entfernen.

## Erzeugen unter Linux

```sh
sudo apt install busybox-static util-linux dosfstools file grub-efi-amd64-bin grub-common
python3 scripts/build-disk-installer.py work/internal-installer
python3 scripts/test-disk-installer.py work/internal-installer
```

Das Ausgabeverzeichnis muss neu sein. Die Ausgabe enthaelt eine eigene EFI-Datei,
Kernel, Installer-Initramfs, Konfiguration und Manifest. Der Installer laeuft
ausschliesslich im RAM; die TDM-Dateien sind im Initramfs enthalten, ohne Netzwerk.

Mit dem vorhandenen USB-Schreibprogramm auf den ausgewaehlten Stick installieren
und danach dessen FAT-Label auf **TDMSETUP** setzen. Beispiel mit Platzhalter:

```sh
sudo python3 scripts/install-usb.py --source work/internal-installer --device /dev/sdX
sudo fatlabel /dev/sdX1 TDMSETUP
```

Ohne dieses Label startet die Installer-Konfiguration nicht. **Der so erzeugte
Stick ist ein automatisches Loesch-/Installationsmedium, kein normaler TDM-Stick.**

Die normalen Projektdateien und das normale GitHub-USB-Installationsverfahren
bleiben reine TDM-Bootmedien. Der interne Installer wird separat erzeugt.

Die zusaetzlichen Programme BusyBox, util-linux und dosfstools samt benoetigten
Bibliotheken werden vom Build-System uebernommen. Fuer passende Quellpakete auf
diesem System die entsprechenden Distribution-Quellen verwenden; BusyBox und
dosfstools sind GPL-lizenziert, util-linux und die Bibliotheken besitzen ihre
jeweiligen Paketlizenzen. Der Builder installiert nichts auf dem Build-System.

## Tests

Der QEMU-Test verwendet ausschliesslich temporaere Images, eine virtuelle
1-TB-SATA-Platte und eine simulierte iMac-DMI-Kennung. Er prueft die Ablehnung
eines falschen Plattenmodells, Installation, Einmalsperre, Erkennung einer bereits
installierten Platte und anschliessenden Start von der internen Platte ohne USB.
Bei diesem letzten Test gilt wieder die normale QEMU-DMI-Kennung, damit keine
SMC-Umschaltbefehle ausgefuehrt werden. Die reale Displayumschaltung und die
Startlaufwerksauswahl des iMac lassen sich damit nicht nachweisen.
