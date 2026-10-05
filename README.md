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

## Startanzeige

Beim Start erscheint ein weißes Apple-Logo auf schwarzem Hintergrund, ohne Menü,
Text, Animation oder zusätzliche Wartezeit. Das RAM-System zeichnet das Logo
nach dem Kernelstart erneut; anschließend übernimmt das externe TDM-Bild.
Die Darstellung wurde in QEMU geprüft und muss am iMac noch bestätigt werden.
Sehr frühe Anzeigen der Mac-Firmware oder des EFI-Laders liegen davor und können
kurz sichtbar bleiben. Das Projekt ist kein Apple-Produkt.

## Temperatur und Stromverbrauch

Nach der Displayumschaltung aktiviert das System den CPU-Energiesparmodus,
soweit der Prozessor ihn unterstützt. Es liest alle 15 Sekunden verfügbare
Temperaturen und Lüfterdrehzahlen. Die automatische Lüfterregelung bleibt beim
SMC des iMac; das Programm verändert keine Lüftervorgaben.
**Es wird kein Grafiktreiber geladen.** Das Startlogo nutzt nur den vorhandenen
Framebuffer. Ob der iMac dadurch kühler läuft, muss am Gerät gemessen werden.

Zur Diagnose eine leere Datei **`diagnostics.txt`** im Hauptverzeichnis des
USB-Sticks anlegen. Beim nächsten Start bleibt der iMac auf seiner internen
Anzeige und zeigt die Messwerte statt in TDM umzuschalten. Datei anschließend
löschen, um wieder direkt in TDM zu starten. Temperaturen in diesem Diagnosemodus
können vom tatsächlichen Monitorbetrieb abweichen.

Im normalen Betrieb bleiben die Messwerte auf der seriellen Konsole und in
`/run/health.txt` im RAM; es gibt keinen SSH-Zugang und keine Speicherung auf dem Stick.

## Ton: experimentelle Unterstützung

Nach der Bildumschaltung werden HDA-Soundtreiber geladen. Vorhandene Master- und
Lautsprecherregler werden aktiviert und auf 40 % ihres Reglerbereichs gesetzt.
Dies läuft im Hintergrund und wartet nicht vor der TDM-Umschaltung.
Es werden weiterhin keine Grafiktreiber geladen.

**DisplayPort-Ton ist am iMac noch nicht bestätigt.** Diese Testfassung prüft,
ob die normale Initialisierung des Audiochips genügt. Sie implementiert keine
nachgewiesene zusätzliche DisplayPort-Audioumschaltung. Auch im
[ursprünglichen SMC-Projekt](https://github.com/floe/smc_util/issues/6) ist Ton
unter Linux eine offene Frage. Ein stummes Ergebnis bedeutet daher nicht,
dass Lautsprecher oder Kabel defekt sind.

Die Treiber- und Mixerdiagnose liegt nur im RAM unter `/run/audio.txt`.
Für diesen Test den normalen USB-Installer verwenden: Er erstellt ein direkt
bootendes RAM-System und installiert beim Start **nichts auf die interne Platte**.
Am iMac mit Alt/Option ausdrücklich den USB-Stick wählen, falls intern bereits
TDM Fast installiert ist. Danach Ton auf der angeschlossenen Bildquelle abspielen.

Die separate [USB-Audiodiagnose](docs/audio-diagnostic.md) speichert Hardwareberichte
auf dem ausgewaehlten Stick und schaltet den iMac danach automatisch aus.

## Was ist schneller?

Das Projekt basiert auf [tinycore-tdm](https://github.com/frogro/tinycore-tdm),
verwendet aber **kein normales TinyCore-System**: Der bewährte 64-Bit-Linux-Kernel
startet ein kleines RAM-Programm direkt als `/init`.

Es gibt keine Menüwartezeit, keinen USB-Such-Timer, keine Netzwerkanmeldung,
keine Paketverwaltung und keine Diagnose vor dem Umschalten. Das vollständige
Bootpaket ist rund **7,9 MB** groß; das komprimierte RAM-Dateisystem rund **422 KB**.
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

Der Installer lädt die fünf Bootdateien von einem fest aufgelösten GitHub-Commit,
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
Auf anderen Modellkennungen unterbleiben SMC-Schreibzugriffe. Die Power-Taste wird auch bei einem TDM-Fehler weiterhin überwacht.

## Selbst bauen

Auf x86_64-Linux, beispielsweise Debian/Ubuntu:

```bash
sudo apt install python3 gcc musl-tools linux-libc-dev binutils grub-efi-amd64-bin grub-common
python3 scripts/build.py
python3 -m unittest discover -s tests -v
```

Das baut `/init`, die Audioinitialisierung, die Sensorüberwachung, das SMC-Programm, `boot/fast.gz`, den EFI-Bootloader und das
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

Die Grafikquellen liegen unter `assets/`. Zum Neuerzeugen der Rasterdateien:

```bash
sudo apt install imagemagick librsvg2-bin
convert -background black assets/splash.svg -alpha off -depth 8 PNG24:boot/splash.png
convert boot/splash.png -crop 180x180+1190+630 +repage -depth 8 gray:assets/apple.gray
python3 scripts/build.py
```

## Installation auf die interne Platte

Ein separater [einmaliger Installationsstick](docs/internal-installer.md) kann die
interne Seagate ST31000528AS mit 1 TB loeschen und TDM Fast dort installieren.
Dieser Sondermodus startet die Installation automatisch und wird separat gebaut.
