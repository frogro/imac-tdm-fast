# Prüfung und Grenzen

## Automatisiert

Dreizehn Python-Tests prüfen Installer-Schutzmaßnahmen, Gerätewechsel vor dem Schreiben,
Abbruch und Probelauf, Kopieren und Prüfsummen, Fehler beim Aushängen, das enge
Downloadmanifest, Commit-Pinning und den tatsächlichen Inhalt des RAM-Dateisystems.
Die vier ELF-Programme haben keinen dynamischen Interpreter. GRUB prüft die
Konfigurationssyntax. Die C-Programme werden mit `-Wall -Wextra -Werror` gebaut.

`scripts/test-qemu.py` erstellt eine temporäre GPT/FAT32-USB-Disk und startet sie
mit x86_64-OVMF. Es verwendet den ausgelieferten EFI-Bootloader, Kernel und das
RAM-Dateisystem. Nur die Testkopie der GRUB-Konfiguration ergänzt eine serielle
Konsole und `tdm.test=1`, um alle SMC-Schreibzugriffe auszuschalten.

Geprüft am 3. Oktober 2026:

- Firmware → USB-Boot → GRUB → Kernel → minimales `/init` erfolgreich.
- RAM-System nach etwa **3,0 Sekunden Kernel-Laufzeit** bereit.
- Gesamter QEMU-/OVMF-/USB-Start bis zur Testbereitschaft etwa **8,0 Sekunden**.
- ACPI-Power-Tastendruck über QMP wird erkannt; die virtuelle Maschine schaltet aus.

Diese Zeiten gelten für QEMU mit Softwareemulation auf dem Build-Rechner, nicht
für den iMac. Im Test wird die einsekündige SMC-Pause nicht ausgeführt, weil alle
SMC-Zugriffe deaktiviert sind. Hardwarezeiten dürfen daraus nicht abgeleitet werden.

## Noch am iMac zu prüfen

- Automatische USB-Priorität bei eingestecktem Stick und internes OS ohne Stick.
- Umschaltung mit angeschlossenem DisplayPort-Signal direkt aus dem frühen RAM-System.
- Kurzer physischer Power-Tastendruck und hardwareseitiges langes Gedrückthalten.
- Zeit vom Einschalten bis zum tatsächlichen externen Bild.
- Verhalten bei fehlendem Bildsignal sowie Neustart nach dem Ausschalten.

Das ursprüngliche TDM-System funktionierte laut Besitzer am Originalstick.
Der Besitzer hat den Start am iMac bestätigt; die neue CPU-/Sensorergänzung ist dort noch nicht geprüft. Die physische
Bildumschaltung wird nicht aus einer erfolgreichen SMC-Rückgabe abgeleitet.
Ein per SHA-256 übernommener Kernel reduziert Änderungen an der Hardwarebasis;
ein individuell verkleinerter Kernel ist eine mögliche spätere Optimierung.

## Aufbau

Der Kernel startet `/init` als PID 1. Es bindet nur `/proc` und `/sys` ein und
verwendet `/dev` im RAM. Da der TinyCore-Kernel kein devtmpfs bereitstellt,
erzeugt es die Eingabegerätedateien anhand der vom Kernel gelieferten sysfs-Daten.
Nach Abschluss der direkten SMC-Umschaltung lädt ein separates Programm
`acpi-cpufreq`, `cpufreq_powersave`, `coretemp` und `applesmc` für exakt diesen Kernel.
Dadurch laufen direkte SMC-Befehle und der SMC-Treiber nicht gleichzeitig.
GPU-Module sind nicht enthalten. Interne Laufwerke und der Stick bleiben ungemountet.

Ein Kindprozess führt die originale Befehlsfolge aus: `MVHR=1`, eine Sekunde Pause,
`MVMR=2`. Fehler brechen die Folge ab. Schreibfehler im übernommenen SMC-Programm
liefern jetzt einen Fehlerstatus statt fälschlich Erfolg. Kein automatisches
Wiederholen des Umschaltbefehls und keine unbestätigte Statusinterpretation.

PID 1 überwacht unabhängig davon Eingabegeräte mit `KEY_POWER`. Bei einem neuen
Druck fordert es `RB_POWER_OFF` an. Eine schon beim Erkennen gehaltene Taste wird
erst nach dem Loslassen wieder scharf geschaltet. Keine Shutdown-Dienste oder
Dateisystemsicherung sind nötig, weil das System keine persistenten Daten schreibt.
Langes Gedrückthalten ist die hardwareseitige Funktion und braucht kein Programm.

## Statische Startgrafik

GRUB schaltet in den Grafikmodus und lädt `boot/splash.png`. Linux verwendet
`gfxpayload=keep`, eine serielle Konsole und `fbcon=map:1`; normale Meldungen werden
nicht auf den Bildschirm geschrieben. Da der Kernel den Framebuffer trotzdem
löschen kann, zeichnet `/init` das Logo über `/dev/fb0` erneut. Fehlt ein
unterstützter Framebuffer, läuft der TDM-Start ohne Grafik weiter.

Der QEMU-Test liest nach dem Kernelstart den vollständigen Bildschirm zurück und
vergleicht jedes RGB-Pixel mit dem erwarteten zentrierten Logo auf Schwarz. Danach
prüft er wie bisher die ACPI-Power-Taste. Mit `--screenshot /pfad/bild.png` wird
zusätzlich ein PNG der laufenden VM gespeichert.

## CPU und Sensoren

Fixture-Tests prüfen die Auswahl des Energiesparmodus, die Modellprüfung der Lüfteranpassung,
den Umgang mit fehlenden Sensoren und die Prüfsummen der ausgelieferten Kernelmodule.
QEMU prüft zusätzlich den Start der Überwachung und verträgliche Fehler bei
nicht unterstützten virtuellen Sensoren. `tdm.test=1` verhindert auch das Laden
von `applesmc`. QEMU kann weder Lüfterregelung noch Temperaturen des iMac bestätigen.

`diagnostics.txt` auf dem Stick aktiviert eine Textkonsole und überspringt die
Displayumschaltung. Ohne diese Datei bleibt der normale Start mit Logo aktiv.
Die Sensorüberwachung ist kein zusätzlicher Überhitzungsschutz. Beim getesteten
iMac11,1 werden erhöhte Mindestdrehzahlen gesetzt, ohne den manuellen Modus zu aktivieren.
CPU-Frequenz, Temperaturen und Lüfterdrehzahlen müssen
am echten iMac überprüft werden.

## Dauerhafte Audioweiterleitung

Am 5. Oktober 2026 bestätigte der Besitzer lokale Testtöne und YouTube-Ton vom
DisplayPort-Mini-PC am iMac11,1 / Mac-F2268DAE / Cirrus CS4206 (Subsystem 106b5100).
Die normale Fassung übernimmt die geprüften Einstellungen: Master −12 dB,
Speaker/Bass Speaker −6 dB, IEC958 Capture aktiv. `alsaloop` verbindet `hw:0,1`
mit `plughw:0,0`, Stereo S16_LE/48 kHz, 50 ms Pufferziel und einfacher
Taktsynchronisation. Die Kartennummer wird anhand des Codecs ermittelt.
Es gibt keine Mikrofonweiterleitung, Testtöne oder zeitgesteuerte Abschaltung.
Andere Modelle erhalten keine unbestätigte digitale Audioroute.

QEMU prüft beide PCM-Richtungen im Zustand RUNNING, die Initialisierung,
das unveränderte Logo und Ausschalten per ACPI-Taste. Der virtuelle Test ersetzt
nicht den Hardwarebeleg. Langzeitbetrieb und weitere Signalquellen sind damit
nicht umfassend getestet. ALSA-Prozesse laufen parallel zur Sensorüberwachung;
Datenträger bleiben im normalen TDM-Betrieb ungemountet.
