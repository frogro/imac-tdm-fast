# USB-Audiodiagnose am iMac 2009

Diese separate Testfassung untersucht den Soundchip und seine Aufnahme- und
Wiedergabegeraete vor und nach den bisherigen TDM-Befehlen. Sie installiert nichts
auf die interne Platte, nimmt keinen Mikrofonton auf und schaltet noch keinen
unbekannten Audio-Multiplexer um. Die bekannte experimentelle HDA-/Mixer-
Initialisierung wird ausgefuehrt. Kein Grafiktreiber wird geladen.

Der Linux-Start bleibt sichtbar. Nach der TDM-Umschaltung werden nach etwa 10 und
30 Sekunden weitere Berichte geschrieben. Anschliessend wird der Stick
synchronisiert und ausgehaengt und der iMac automatisch ausgeschaltet. Das
externe Bild verschwindet dabei erwartungsgemaess.

Auf dem Stick entstehen `audio-diag-1`, `audio-diag-2`, ... mit `before.txt`,
`after.txt`, `final.txt`, `tdm.txt` und `COMPLETE.txt`. Nur ein vorhandenes
`COMPLETE.txt` bestaetigt den vollstaendigen Durchlauf. Es werden DMI-Modell,
Boardkennung, PCI-IDs, ALSA-Geraete, Mixerwerte, HDA-Codec-Dumps und Kernelmeldungen
gespeichert. Keine Audioaufnahmen. Berichte vor einer Veroeffentlichung pruefen.

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
