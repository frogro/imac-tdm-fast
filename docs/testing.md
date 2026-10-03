# Prüfung und Grenzen

## Automatisiert

Neun Python-Tests prüfen Installer-Schutzmaßnahmen, Gerätewechsel vor dem Schreiben,
Abbruch und Probelauf, Kopieren und Prüfsummen, Fehler beim Aushängen, das enge
Downloadmanifest, Commit-Pinning und den tatsächlichen Inhalt des RAM-Dateisystems.
Die beiden ELF-Programme haben keinen dynamischen Interpreter. GRUB prüft die
Konfigurationssyntax. Die C-Programme werden mit `-Wall -Wextra -Werror` gebaut.

`scripts/test-qemu.py` erstellt eine temporäre GPT/FAT32-USB-Disk und startet sie
mit x86_64-OVMF. Es verwendet den ausgelieferten EFI-Bootloader, Kernel und das
RAM-Dateisystem. Nur die Testkopie der GRUB-Konfiguration ergänzt eine serielle
Konsole und `tdm.test=1`, um alle SMC-Schreibzugriffe auszuschalten.

Geprüft am 3. Oktober 2026:

- Firmware → USB-Boot → GRUB → Kernel → minimales `/init` erfolgreich.
- RAM-System nach etwa **3,0 Sekunden Kernel-Laufzeit** bereit.
- Gesamter QEMU-/OVMF-/USB-Start bis zur Testbereitschaft etwa **7,0 Sekunden**.
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
Diese neue Startumgebung wurde noch nicht am iMac getestet. Die physische
Bildumschaltung wird nicht aus einer erfolgreichen SMC-Rückgabe abgeleitet.
Ein per SHA-256 übernommener Kernel reduziert Änderungen an der Hardwarebasis;
ein individuell verkleinerter Kernel ist eine mögliche spätere Optimierung.

## Aufbau

Der Kernel startet `/init` als PID 1. Es bindet nur `/proc` und `/sys` ein und
verwendet `/dev` im RAM. Da der TinyCore-Kernel kein devtmpfs bereitstellt,
erzeugt es die Eingabegerätedateien anhand der vom Kernel gelieferten sysfs-Daten.
Es lädt keine Module, insbesondere kein `applesmc`, das mit direkten SMC-Zugriffen
kollidieren könnte. Interne Laufwerke und der Stick bleiben ungemountet.

Ein Kindprozess führt die originale Befehlsfolge aus: `MVHR=1`, eine Sekunde Pause,
`MVMR=2`. Fehler brechen die Folge ab. Schreibfehler im übernommenen SMC-Programm
liefern jetzt einen Fehlerstatus statt fälschlich Erfolg. Kein automatisches
Wiederholen des Umschaltbefehls und keine unbestätigte Statusinterpretation.

PID 1 überwacht unabhängig davon Eingabegeräte mit `KEY_POWER`. Bei einem neuen
Druck fordert es `RB_POWER_OFF` an. Eine schon beim Erkennen gehaltene Taste wird
erst nach dem Loslassen wieder scharf geschaltet. Keine Shutdown-Dienste oder
Dateisystemsicherung sind nötig, weil das System keine persistenten Daten schreibt.
Langes Gedrückthalten ist die hardwareseitige Funktion und braucht kein Programm.
