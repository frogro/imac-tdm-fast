# iMac TDM Fast

Ein USB-Stick macht den **27″-iMac von Ende 2009** direkt zum Monitor.
Kein Pi, kein WLAN-Taster und kein Bootmenü nötig.

- **Stick eingesteckt:** Der iMac startet vom Stick und schaltet automatisch auf den externen Bildeingang.
- **Stick entfernt:** Die Mac-Firmware kann auf ein vorhandenes bootfähiges internes Betriebssystem zurückfallen; dieses Verhalten am eigenen iMac prüfen.
- **Powerknopf kurz drücken:** Das RAM-System fordert sofortiges Ausschalten an.
- **Powerknopf länger gedrückt halten:** Die Hardware erzwingt das Ausschalten, auch wenn Software hängt.

Voraussetzung für die automatische Auswahl: Die Mac-Firmware muss den eingesteckten
USB-Stick bevorzugen. Das verändert dieser Installer nicht. Falls nötig, beim
Einschalten **Alt/Option** halten und **EFI Boot** auswählen.

Zum Speichern als Standard im Apple-Startmenü **Ctrl/Control** gedrückt halten:
Wenn der Pfeil unter dem gewählten Laufwerk zu einem Kreispfeil wird, mit weiterhin
gehaltener Ctrl-Taste starten. Danach einmal mit und einmal ohne Stick testen.
Unter macOS gibt es außerdem **Systemeinstellungen → Startvolume**; reine Linux-
EFI-Sticks werden dort nicht immer angeboten. Apple beschreibt die allgemeine
[Wahl des Standard-Startlaufwerks](https://support.apple.com/en-sg/guide/mac-help/mchlp1034/mac).
Die Ctrl-Methode ist auch im
[rEFInd-Projektforum](https://sourceforge.net/p/refind/discussion/general/thread/b9b50e68e3/)
beschrieben. Ob die Firmware dieses iMac den Eintrag dauerhaft übernimmt, muss
am Gerät geprüft werden.

Wenn intern gar kein bootfähiges OS vorhanden ist, kann der Mac den USB-Stick
auch ohne gespeicherte USB-Priorität als einziges Bootziel finden. Ohne Stick
startet in diesem Fall selbstverständlich kein internes System.
Der iMac wird ausgeschaltet, bleibt am Stromnetz aber im Standby.

## Was ist schneller?

Das Projekt basiert auf [tinycore-tdm](https://github.com/frogro/tinycore-tdm),
verwendet aber **kein normales TinyCore-System**: Der bewährte 64-Bit-Linux-Kernel
startet ein kleines RAM-Programm direkt als `/init`.

Es gibt keine Menüwartezeit, keinen USB-Such-Timer, keine Netzwerkanmeldung,
keine Paketverwaltung und keine Diagnose vor dem Umschalten. Das vollständige
Bootpaket ist rund **7,3 MB** groß; das RAM-Dateisystem selbst nur rund **51 KB**.
Die einsekündige Pause zwischen den beiden SMC-Befehlen des funktionierenden
Originalsticks bleibt vorerst erhalten. Nach dem letzten Befehl folgt keine Pause.

**USB-/UEFI-Start und kurzer Power-Tastendruck sind in QEMU geprüft.**
Die tatsächliche Displayumschaltung, die Power-Taste des iMac und die Startzeit
am echten iMac müssen noch geprüft werden. Eine absolute Mindeststartzeit ist
nicht nachgewiesen. Details: [Tests](docs/testing.md).

## USB-Stick unter Linux erstellen

Ein USB-Stick ab 512 MB reicht. Der gewählte Stick wird vollständig gelöscht.
Andere Laufwerke werden nicht verändert. Ein vorhandener funktionierender
TDM-Stick sollte für den ersten Test als Rückfallmöglichkeit erhalten bleiben.

```bash
sudo apt install python3 dosfstools parted util-linux udev
curl -fL https://raw.githubusercontent.com/frogro/imac-tdm-fast/main/scripts/install-usb.py -o install-usb.py
python3 install-usb.py --list
```

Das gewünschte **ganze USB-Gerät** aus der Liste wählen. `/dev/sdX` ist ein Platzhalter.
Seine Partitionen vorher aushängen; der Installer lehnt benutzte Laufwerke ab.

```bash
python3 install-usb.py --device /dev/sdX --dry-run
sudo python3 install-usb.py --device /dev/sdX
```

Der Installer lädt die vier Bootdateien von einem fest aufgelösten GitHub-Commit,
prüft Größen und SHA-256 und verlangt vor dem Löschen die Eingabe
`LOESCHEN /dev/sdX`. Danach erstellt er GPT und eine FAT32-EFI-Partition,
kopiert und prüft die Dateien und hängt den Stick aus.

Auch ohne Download bei der Installation möglich:

```bash
python3 install-usb.py --download-only ./tdm-dateien
sudo python3 install-usb.py --source ./tdm-dateien --device /dev/sdX
```

## Am iMac verwenden

1. iMac ausschalten und Stick einstecken.
2. Bildquelle mit dem **Mini-DisplayPort-Eingang** verbinden.
3. iMac einschalten. Sobald die Umschaltung erfolgt, erscheint das externe Bild.
4. Zum Ausschalten den normalen Powerknopf kurz drücken.

Ein HDMI-Gerät benötigt einen geeigneten aktiven HDMI→DisplayPort-Konverter.
Das Bootprogramm erzeugt selbst kein externes Videosignal.

Der Laufzeitbetrieb findet ausschließlich im RAM statt. Weder Stick noch interne
Laufwerke werden von `/init` eingebunden oder beschrieben. Deshalb sind beim
Ausschalten keine Dateisysteme zu sichern. Es gibt keinen Desktop, SSH oder
Shell-Zugang und keine Tastaturlayout-Einrichtung.

Die SMC-Umschaltung ist auf die Modellkennungen `iMac10,1` und `iMac11,1` begrenzt;
`iMac10,1` gibt es auch als 21,5″-Gerät, das hier **nicht unterstützt** wird.
Auf anderen Modellkennungen unterbleiben SMC-Schreibzugriffe. Ein Fehler bleibt
auf der Konsole sichtbar; der Powerknopf wird weiterhin überwacht.

## Selbst bauen

Auf x86_64-Linux, beispielsweise Debian/Ubuntu:

```bash
sudo apt install python3 gcc musl-tools linux-libc-dev binutils grub-efi-amd64-bin grub-common
python3 scripts/build.py
python3 -m unittest discover -s tests -v
```

Das baut `/init`, das SMC-Programm, `boot/fast.gz`, den EFI-Bootloader und das
Downloadmanifest neu. `boot/vmlinuz` bleibt der per SHA-256 festgelegte Kernel aus
dem ursprünglichen Repository. Es werden keine Systemdateien des Build-Rechners verändert.

Für den vollständigen EFI-/USB-/Power-Test zusätzlich:

```bash
sudo apt install qemu-system-x86 ovmf dosfstools mtools fdisk
python3 scripts/test-qemu.py
```

Der Test verwendet ausschließlich eine temporäre Image-Datei. Er schaltet nur die
virtuelle Maschine aus und deaktiviert SMC-Zugriffe ausdrücklich mit `tdm.test=1`.
Dieser Parameter gehört nicht auf den echten TDM-Stick.

Herkunft und Lizenzen: [Drittkomponenten](docs/licenses.md), [sources.json](sources.json).
