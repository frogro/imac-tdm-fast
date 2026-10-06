# Live-Audioanalyse per SSH

Die separate Diagnosefassung startet direkt in TDM mit derselben Audioweiterleitung
wie die normale Version. Zusätzlich erhält der iMac per LAN/DHCP eine IP-Adresse
und startet SSH. Es gibt keine Testtöne, keine automatische Abschaltung und keine
Installation auf die interne Platte. Die Bildquelle muss nicht verändert werden.

Den iMac per LAN-Kabel mit demselben Router wie den Analyse-Rechner verbinden.
Im Router nach dem neuen LAN-Gerät suchen. Anmeldung als `root` mit dem beim
Bauen angegebenen SSH-Schlüssel; Passwortanmeldung und Portweiterleitung sind
deaktiviert. Der normale TDM-Build enthält diesen SSH-Zugang nicht.

## Privates Image bauen

Auf x86_64-Linux mit den normalen Build-Abhängigkeiten und zusätzlich
`dropbear-bin`, `openssh-client`:

```sh
python3 scripts/build-ssh-diagnostic.py /tmp/tdm-ssh \
  --authorized-key ~/.ssh/id_ed25519.pub
python3 scripts/test-ssh-diagnostic.py /tmp/tdm-ssh \
  --identity ~/.ssh/id_ed25519
sudo python3 scripts/install-usb.py --source /tmp/tdm-ssh --device /dev/sdX
```

`/dev/sdX` durch den ausgewählten USB-Stick ersetzen. Der Stick wird gelöscht.
Am iMac mit Alt/Option ausdrücklich diesen USB-Stick starten; die interne
Installation bleibt unverändert. Es gilt weiterhin das Label `TDMFAST`, nicht
`TDMSETUP`. Nach Entfernen des Sticks startet wieder die interne Fassung.

Der Builder erzeugt einen eigenen SSH-Hostschlüssel für dieses Image.
**Das erzeugte Image ist privat und gehört nicht in GitHub:** Es enthält den
Hostschlüssel und den zugelassenen öffentlichen Benutzerschlüssel. Der private
Benutzerschlüssel wird weder gelesen noch auf den Stick kopiert. `ssh-host-key.pub`
im Ausgabeverzeichnis enthält die überprüfbare öffentliche Serveridentität.

## Verbinden und auslesen

Die Adresse aus dem Router anstelle von `192.168.178.X` einsetzen.
Den Fingerabdruck zuerst mit der lokal erzeugten Datei vergleichen:

```sh
ssh-keygen -lf /tmp/tdm-ssh/ssh-host-key.pub
ssh -i ~/.ssh/id_ed25519 root@192.168.178.X
```

In der SSH-Shell:

```sh
tdm-audio-status
cat /run/ssh.log
cat /run/audio-loop.txt
```

`tdm-audio-status` liest Mixerwerte, PCM-Status und Pufferparameter,
Prozessliste sowie Temperaturlog. Es verändert keine Regler und startet keine
Aufnahme. Für einen zeitlichen Vergleich auf dem Analyse-Rechner speichern:

```sh
ssh root@192.168.178.X 'while :; do tdm-audio-status; sleep 2; done' > audio-live.txt
```

Mit Strg+C beenden und die Uhrzeit hörbarer Schwankungen notieren. Logs im iMac
liegen ausschließlich im RAM und verschwinden beim Ausschalten. Die SSH-Shell
hat Administratorrechte; Schreibbefehle auf Datenträger gehören nicht zur Analyse.

## Technik und Prüfung

Die Netzwerkmodule `tg3` (reale Broadcom-LAN-Hardware) und `e1000` (QEMU)
stammen aus dem bestehenden TinyCore-6.6.8-Initramfs; Herkunft und SHA-256
stehen in `vendor/network/manifest.json`. Die Kernelquellen sind bereits im
Quellen-Release vorhanden. Dropbear und seine Bibliotheken stammen aus dem
Build-System und behalten ihre Paketlizenzen. Mit `--tools-root` kann statt
installierter Pakete ein Verzeichnis mit entpackten Paketen verwendet werden.

QEMU prüft DHCP, SSH mit festgelegter Serveridentität, eine interaktive Shell,
laufende Audiostreams und fehlende Datenträgermounts. Die reale LAN-Verbindung
und die Ursache der Lautstärkeschwankungen müssen anschließend am iMac geprüft werden.
