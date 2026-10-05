# USB-Audiodiagnose am iMac 2009

Diese separate Testfassung untersucht den Soundchip und seine Aufnahme- und
Wiedergabegeraete vor und nach den bisherigen TDM-Befehlen. Sie installiert nichts
auf die interne Platte, nimmt keinen Mikrofonton auf und schaltet noch keinen
unbekannten Audio-Multiplexer um. Die bekannte experimentelle HDA-/Mixer-
Initialisierung wird ausgefuehrt. Kein Grafiktreiber wird geladen.

Der Linux-Start bleibt sichtbar. Nach der TDM-Umschaltung folgt nach etwa zehn Sekunden ein Audiotest:
drei kurze lokale Pieptoene, drei Sekunden digitale Eingangsmessung und
etwa 45 Sekunden digitale Weiterleitung an die Lautsprecher. Anschliessend wird der Stick
synchronisiert und ausgehaengt und der iMac automatisch ausgeschaltet. Das
externe Bild verschwindet dabei erwartungsgemaess.

Auf dem Stick entstehen `audio-diag-1`, `audio-diag-2`, ... mit `before.txt`,
`after.txt`, `final.txt`, `tdm.txt` und `COMPLETE.txt`. Nur ein vorhandenes
`COMPLETE.txt` bestaetigt den vollstaendigen Durchlauf. Es werden DMI-Modell,
Boardkennung, PCI-IDs, ALSA-Geraete, Mixerwerte, HDA-Codec-Dumps und Kernelmeldungen
gespeichert. Drei Sekunden des digitalen Eingangs werden ausschliesslich im RAM gepuffert,
auf Signalpegel untersucht und sofort geloescht. Es werden keine Audiodaten auf
dem Stick gespeichert und kein Mikrofoneingang verwendet. Berichte vor einer Veroeffentlichung pruefen.

## Bauen und installieren

Build-Rechner: x86_64 Linux mit `busybox-static`, `alsa-utils`, `pciutils`, Python3
und den normalen Build-Werkzeugen. Der Builder uebernimmt die Programme samt
Bibliotheken vom Build-Rechner; dies ist eine lokale Diagnosefassung und kein
neues vorgebautes Release.

```sh
python3 scripts/build-audio-diagnostic.py /tmp/audio-test --usb-serial SERIENNUMMER
sudo python3 scripts/install-usb.py --source /tmp/audio-test --device /dev/sdX
```

`SERIENNUMMER` und `/dev/sdX` durch den gewaehlten USB-Stick ersetzen. Nur dieser
Stick wird beim Installieren neu formatiert. Beim Booten wird das Logziel durch
USB-Transport, genaue Seriennummer und SHA-256 der passenden GRUB-Konfiguration
geprueft. Andere erkannte SATA/NVMe-Datentraeger werden zusaetzlich schreibgeschuetzt
und nicht eingebunden. Bei fehlendem Logziel wird abgebrochen.

Am iMac Alt/Option halten und explizit den USB-Stick starten. Die angeschlossene
Bildquelle kann wie gewohnt Ton abspielen; ihre Konfiguration muss nicht geaendert
werden. Nach dem automatischen Ausschalten den Stick am Analyse-Rechner einstecken.

## Test

`python3 scripts/test-audio-diagnostic.py` baut eine separate VM-Fassung mit
`--test`. Diese ueberspringt SMC-Schreibzugriffe und Hardwarewartezeiten. QEMU
prueft persistente USB-Berichte, Codec-/Capture-Inventur, unveraenderte Bytes einer
virtuellen internen Platte sowie automatisches Ausschalten. Das ersetzt keinen
Test des echten iMac-Audioeingangs. `--test` nicht fuer den iMac verwenden.

## Zweite Testfassung: digitale Weiterleitung

Die Tonweiterleitung ist auf die aus dem ersten Bericht bestaetigte Hardware
begrenzt: iMac11,1, Board Mac-F2268DAE, CS4206 mit Subsystem 0x106b5100.
Sie aktiviert IEC958 Capture und verwendet dessen Geraet 1 als Eingang sowie
Analog-Geraet 0 als Ausgang. Master wird auf -12 dB, Speaker/Bass auf -6 dB
gesetzt. Dies ersetzt die ungeeigneten 40 % des numerischen Reglerbereichs fuer
diesen Test. Die normalen Bootdateien werden dadurch nicht veraendert.

`route-test.txt` enthaelt Rueckgabewerte, digitale Signalpegel und die waehrend
der Weiterleitung aktiven PCM-Parameter. `alsaloop` gleicht Taktdifferenzen mit
Modus 1 aus. Die DisplayPort-Mux-Auswahl ist weiterhin unveraendert: Ein stummer
Eingang kann deshalb weiterhin auf die noch fehlende Eingangswahl hindeuten.
Bitte auf drei lokale Pieptoene und anschliessend auf den Ton der angeschlossenen
Bildquelle achten. Nach etwa ein bis zwei Minuten schaltet der iMac automatisch
aus. Dieser Test ist keine bestaetigte TDM-Audioloesung.
