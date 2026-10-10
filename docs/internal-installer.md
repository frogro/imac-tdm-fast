# Einmaliger Installer fuer die interne iMac-Platte

Dieser Modus akzeptiert interne **SATA-HDDs und SATA-SSDs beliebiger Hersteller
ab 1 GiB**, sofern genau ein internes SATA-Laufwerk vorhanden ist.
**Bei einer Erstinstallation werden alle Daten und Partitionen der Zielplatte
gelöscht. Benötigte Daten vorher extern sichern.** Eine bereits mit
`TDM_FAST_INSTALLED` markierte Installation erhält stattdessen nur die neuen
Bootdateien. Es ist keine Datensicherung enthalten.

USB-Ziellaufwerke werden ausgeschlossen. Bei mehreren internen SATA-Platten
stoppt der Installer, statt automatisch eine auszuwählen; die anderen internen
Platten müssen vor der Installation getrennt werden. Angezeigt werden das
tatsächlich erkannte Modell und seine Größe. Die Modellkennung des iMac muss
`iMac10,1` oder `iMac11,1` sein; unterstützt ist nur der 27-Zoll-iMac von Ende 2009.
Die reale Installation wurde auf einer Seagate ST31000528AS mit 1 TB getestet;
andere Hersteller und Kapazitäten sind freigegeben, aber nicht alle physisch geprüft.

Der Stick zeigt das Ziel an und wartet 15 Sekunden. In dieser Zeit kann man durch
langes Druecken des Powerknopfs ausschalten. Bei einer Erstinstallation legt er eine GPT mit einer
512-MiB-FAT32-EFI-Partition an und installiert die normale TDM-Fast-Fassung.
Der Rest der Platte bleibt unpartitioniert. Partitionstabellen und alte
Dateisystemsignaturen werden entfernt; dies ist **keine sichere Vollueberschreibung**
der persönlichen Daten auf der gesamten Platte.

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
internen EFI-Partition: Stimmen die Bootdateien mit der neuen Version überein,
ändert er nichts. Andernfalls aktualisiert er diese Partition nach der Wartezeit
und prüft die neuen Dateien. Auch Updates sind durch den USB-Einmalmarker geschützt.

Zum bewussten Wiederholen nach einem Fehler muss der Stick neu vorbereitet werden.
Die Fehlermeldung vorher klaeren; Marker nicht einfach unbeaufsichtigt entfernen.

## Fertiges Installationspaket

Das ältere Paket mit Audioweiterleitung steht im
[Release v0.2.0-audio](https://github.com/frogro/imac-tdm-fast/releases/tag/v0.2.0-audio).
**Dieses Release enthält nicht automatisch die späteren Änderungen aus `main`.**
Für die aktuelle Fassung ohne Seagate-/1-TB-Bindung, mit 50-ms-Audiozielpuffer
und den aktuellen Kühlungs- und GPU-Anpassungen den Installer wie unten beschrieben
aus `main` neu erzeugen. Das alte Release hat weiterhin die alte Plattenbeschränkung.

Für den älteren Release-Stand `imac-tdm-fast-hdd-installer.tar.gz` herunterladen und entpacken. Im enthaltenen
Verzeichnis liegt auch `install-usb.py`; damit den gewünschten USB-Stick schreiben:

```sh
sudo apt install python3 dosfstools parted util-linux udev
cd imac-tdm-fast-hdd-installer
sudo python3 install-usb.py --source . --device /dev/sdX
sudo fatlabel /dev/sdX1 TDMSETUP
```

`/dev/sdX` unbedingt durch den richtigen USB-Stick ersetzen. Danach am iMac mit
Alt/Option vom USB-Stick starten. Die Installation beziehungsweise Aktualisierung
beginnt nach 15 Sekunden automatisch und endet mit dem Ausschalten.

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
SATA-Platten unterschiedlicher Modelle und Größen sowie eine simulierte
iMac-DMI-Kennung. Er prüft die Ablehnung zu kleiner, externer USB- und mehrdeutiger
interner Ziele, Installation auf 8-GiB-, 1-TB- und 3-TiB-Platten, Einmalsperre, Erkennung einer bereits
installierten Platte, Aktualisierung mit verändertem Payload und anschliessenden Start von der internen Platte ohne USB.
Bei diesem letzten Test gilt wieder die normale QEMU-DMI-Kennung, damit keine
SMC-Umschaltbefehle ausgefuehrt werden. Die reale Displayumschaltung und die
Startlaufwerksauswahl des iMac lassen sich damit nicht nachweisen.
