# iMac TDM Fast

Ein USB-Stick macht den **27″-iMac von Ende 2009** direkt zum Monitor.
Kein Pi, kein WLAN-Taster und kein Bootmenü nötig.

Alternativ lässt sich das System mit dem separaten
[USB-Installer auf die interne HDD installieren](docs/internal-installer.md).
Danach wird kein USB-Stick mehr benötigt.

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
Die Darstellung wurde in QEMU geprüft und am iMac bestätigt.
Sehr frühe Anzeigen der Mac-Firmware oder des EFI-Laders liegen davor und können
kurz sichtbar bleiben. Das Projekt ist kein Apple-Produkt.

## Temperatur und Stromverbrauch

Nach der Displayumschaltung aktiviert das System den CPU-Energiesparmodus,
soweit der Prozessor ihn unterstützt. Es liest alle 15 Sekunden verfügbare
Temperaturen und Lüfterdrehzahlen. Die automatische Lüfterregelung bleibt beim
SMC des iMac. Auf dem getesteten iMac11,1 werden die Mindestdrehzahlen erhöht:
ODD und HDD auf 1.800, CPU auf 1.500 U/min. Bereits höhere Mindestwerte bleiben
erhalten; bei Bedarf kann der SMC weiter hochregeln. Andere Modelle bleiben unverändert.
Mit `tdm.fans=0` in der Linux-Bootzeile lässt sich diese Anpassung beim Start überspringen.
**Es wird kein Grafiktreiber geladen.** Das Startlogo nutzt nur den vorhandenen
Framebuffer. Im gut fünfminütigen Lüftertest am iMac11,1 sank der Netzteil-Sensor
`Tp2H` von 78,8 auf 72,0 °C und die GPU-Diode von 61,8 auf 56,5 °C.
Die höheren Mindestdrehzahlen können hörbarer sein; die Werte sind Messungen
an diesem Gerät, keine Temperaturgrenzwerte.

Zur Diagnose eine leere Datei **`diagnostics.txt`** im Hauptverzeichnis des
USB-Sticks anlegen. Beim nächsten Start bleibt der iMac auf seiner internen
Anzeige und zeigt die Messwerte statt in TDM umzuschalten. Datei anschließend
löschen, um wieder direkt in TDM zu starten. Temperaturen in diesem Diagnosemodus
können vom tatsächlichen Monitorbetrieb abweichen.

Im normalen Betrieb bleiben die Messwerte auf der seriellen Konsole und in
`/run/health.txt` im RAM; es gibt keinen SSH-Zugang und keine Speicherung auf dem Stick.

## Ton über DisplayPort

Bild und Ton wurden am **iMac11,1 (27″, Ende 2009) mit Cirrus CS4206** bestätigt:
Testtöne und YouTube vom angeschlossenen Mini-PC sind über die iMac-Lautsprecher hörbar.
Nach der Bildumschaltung startet automatisch die Weiterleitung des digitalen
Audioeingangs auf die Lautsprecher. Die Lautstärke lässt sich an der Bildquelle regeln.
Für andere iMac-Modelle ist diese Tonweiterleitung noch nicht freigeschaltet.

Die Weiterleitung läuft dauerhaft im RAM, ohne Grafiktreiber, Testtöne oder
zeitgesteuertes Ausschalten. Falls der Audioprozess endet, wird er erneut gestartet.
Die Initialisierung läuft im Hintergrund und verzögert die Bildumschaltung nicht.

Die separate [USB-Audiodiagnose](docs/audio-diagnostic.md) ist nur für Fehlersuche
bestimmt; sie erzeugt Testtöne und schaltet danach automatisch aus.

Für Live-Fehlersuche gibt es außerdem eine separate [LAN-/SSH-Diagnosefassung](docs/ssh-diagnostic.md). Sie lässt die interne Installation unverändert.

### Linux-Abspielrechner: Aussetzer nach Pausen vermeiden

Für den angeschlossenen Linux-Rechner empfehlen wir, den automatischen
Audio-Ruhezustand des DisplayPort-Ausgangs und die HD-Audio-Stromsparfunktion
abzuschalten. Im Vergleichstest traten mit den bisherigen Einstellungen nach
Pause/Fortsetzen kurze Aussetzer auf; mit beiden Anpassungen blieben drei
Wiederholungen sauber. Das ist kein Nachweis für alle Geräte oder Langzeitbetrieb.
Die Einstellungen gehören auf den **Abspielrechner**, nicht auf den iMac.

**1. PipeWire/WirePlumber 0.5: DisplayPort-Ausgang aktiv lassen.**
Mit `pactl list short sinks` den Namen des verwendeten Ausgangs ermitteln.
`~/.config/wireplumber/wireplumber.conf.d/51-imac-displayport-no-suspend.conf`
anlegen (Verzeichnis gegebenenfalls mit `mkdir -p` erstellen):

```ini
monitor.alsa.rules = [
  {
    matches = [ { node.name = "DEIN_DISPLAYPORT_AUSGANG" } ]
    actions = {
      update-props = {
        session.suspend-timeout-seconds = 0
        node.pause-on-idle = false
      }
    }
  }
]
```

`DEIN_DISPLAYPORT_AUSGANG` durch den vollständigen Namen aus der Liste ersetzen.
Ein DisplayPort-Ausgang kann im Namen `hdmi` enthalten. Danach
`systemctl --user restart wireplumber` ausführen; dabei wird der Ton kurz
unterbrochen. Wiedergabe gegebenenfalls erneut starten.

**2. Bei Verwendung von `snd_hda_intel`: `power_save=0` setzen.**
Den bisherigen Wert mit `cat /sys/module/snd_hda_intel/parameters/power_save`
notieren. Falls die Datei fehlt, gilt dieser Schritt nicht für den verwendeten
Treiber. Eine vorhandene gleichnamige Konfigurationsdatei vorher sichern.

```bash
# Sofort wirksam:
echo 0 | sudo tee /sys/module/snd_hda_intel/parameters/power_save
# Für folgende Starts:
echo 'options snd_hda_intel power_save=0' | sudo tee /etc/modprobe.d/99-tdm-audio-powersave.conf
# Unter Ubuntu/Debian auch das Startabbild aktualisieren:
sudo update-initramfs -u
```

Dies gilt für alle vom Treiber `snd_hda_intel` verwalteten Audiogeräte.
Andere Distributionen verwenden gegebenenfalls einen anderen Befehl zum
Aktualisieren des Startabbilds. Der Rechner kann im Leerlauf etwas mehr Strom
verbrauchen. Der DisplayPort-Ausgang bleibt für direkten exklusiven ALSA-Zugriff
belegt; normale PipeWire-Anwendungen können ihn weiter gemeinsam verwenden.

Zum Rückgängigmachen die neu angelegten Dateien entfernen beziehungsweise ihre
Sicherungen zurückspielen, WirePlumber neu starten und das Startabbild erneut
aktualisieren. Den zuvor notierten `power_save`-Wert wieder in die Datei unter
`/sys/module/` schreiben oder den Rechner neu starten.

Details: [WirePlumber-Audio-Ruhezustand](https://pipewire.pages.freedesktop.org/wireplumber/daemon/configuration/alsa.html)
und [Linux-HD-Audio-Stromsparfunktion](https://docs.kernel.org/sound/designs/powersave.html).

## Was ist schneller?

Das Projekt basiert auf [tinycore-tdm](https://github.com/frogro/tinycore-tdm),
verwendet aber **kein normales TinyCore-System**: Der bewährte 64-Bit-Linux-Kernel
startet ein kleines RAM-Programm direkt als `/init`.

Es gibt keine Menüwartezeit, keinen USB-Such-Timer, keine Netzwerkanmeldung,
keine Paketverwaltung und keine Diagnose vor dem Umschalten. Das vollständige
Bootpaket ist rund **12,8 MB** groß; das komprimierte RAM-Dateisystem rund **5,3 MB**.
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
sudo apt install python3 gcc musl-tools linux-libc-dev binutils grub-efi-amd64-bin grub-common busybox-static alsa-utils file
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
Eine vorhandene, markierte TDM-Fast-Installation wird ohne neue Partitionierung
aktualisiert. Dieser Sondermodus startet automatisch und wird separat gebaut.

### GPU-Stromverbrauch beim getesteten iMac11,1

Auf dem Board `Mac-F2268DAE` mit Radeon `1002:944a` wird nach dem TDM-Start die PCIe-Verbindung einmal für 30 Sekunden unterbrochen und anschließend wiederhergestellt. Zwei Hardwaretests zeigten dabei einen Rückgang der internen GPU-Leistungsanzeige von ungefähr 34 W auf 12–13 W bei erhaltenem Bild und Ton. Das ist keine vollständige Stromabschaltung und keine Messung des Gesamtverbrauchs an der Steckdose. Andere Modelle werden übersprungen; ein Radeon-Treiber wird nicht geladen.

Der Vorgang läuft im Hintergrund, sobald Audio und Temperatursensor verfügbar sind. Er betrifft auch die ungenutzte HDMI-Audiofunktion der Radeon, nicht die Cirrus-Audio-Schleife. Protokoll: `/run/gpu-idle.log`. Zum Abschalten der Anpassung `tdm.gpu_idle=0` an die Linux-Bootzeile anhängen. Die Rückkehr zur internen Grafikausgabe nach diesem Vorgang ist nicht geprüft.

Die Audiovermittlung verwendet einen Zielpuffer von 50 ms. Begrenzte Fehlerprotokolle liegen nur im RAM unter `/run/audio-0.log` und `/run/audio-1.log`; sie verschwinden beim Neustart.
