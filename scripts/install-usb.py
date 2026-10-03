#!/usr/bin/env python3
"""Install this repository onto an explicitly selected USB disk (Linux only)."""
import argparse
import hashlib
import json
import os
import re
import urllib.parse
import urllib.request
from pathlib import Path
import shutil
import stat
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
REPOSITORY = 'frogro/imac-tdm-fast'
REQUIRED = {'EFI/BOOT/BOOTX64.EFI', 'boot/vmlinuz', 'boot/fast.gz', 'boot/splash.png', 'grub.cfg'}
OPTIONAL = set()
COLUMNS = 'NAME,PATH,TYPE,SIZE,TRAN,RO,MODEL,SERIAL,MAJ:MIN,MOUNTPOINTS'


def run(*args, **kwargs):
    return subprocess.run(args, check=True, **kwargs)


def inventory():
    result = run('lsblk', '--json', '--bytes', '--tree', '--output', COLUMNS,
                 capture_output=True, text=True)
    return json.loads(result.stdout)['blockdevices']


def walk(device):
    yield device
    for child in device.get('children', []):
        yield from walk(child)


def find_disk(devices, path):
    for device in devices:
        for node in walk(device):
            if node['path'] == path:
                return node
    raise ValueError(f'Gerät nicht gefunden: {path}')


def validate(device):
    if device['type'] != 'disk' or device.get('tran') != 'usb':
        raise ValueError('Nur ein vollständiges USB-Laufwerk ist erlaubt, keine Partition.')
    if device.get('ro') or int(device['size']) < 512 * 1024 * 1024:
        raise ValueError('Das Ziel muss beschreibbar und mindestens 512 MiB groß sein.')
    for node in walk(device):
        if any(node.get('mountpoints') or []):
            raise ValueError(f"{node['path']} ist eingehängt oder als Swap aktiv. Erst aushängen.")
        if node['type'] not in ('disk', 'part'):
            raise ValueError('Das Ziel wird von RAID, LVM oder einem anderen Mapper verwendet.')
        holders = Path('/sys/class/block') / Path(node['path']).name / 'holders'
        if holders.exists() and any(holders.iterdir()):
            raise ValueError(f"{node['path']} wird von einem anderen Blockgerät verwendet.")


def identity(device):
    return tuple(device.get(k) for k in ('path', 'size', 'model', 'serial', 'maj:min'))


def describe(device):
    return (f"{device['path']} | {int(device['size']) / 1024**3:.2f} GiB | "
            f"{(device.get('model') or '').strip()} | Seriennummer: {device.get('serial') or 'unbekannt'}")


def manifest_entries(manifest):
    if not isinstance(manifest, dict) or manifest.get('version') != 1:
        raise ValueError('Unbekanntes Download-Manifest.')
    entries = manifest.get('files')
    optional = manifest.get('optional_files', [])
    if not isinstance(optional, list):
        raise ValueError('Ungültige optionale Dateiliste.')
    if not isinstance(entries, list) or not 1 <= len(entries) <= 100:
        raise ValueError('Ungültige Dateiliste im Manifest.')
    base_entries = entries
    entries = entries + optional
    seen = set()
    for entry in entries:
        if not isinstance(entry, dict):
            raise ValueError('Ungültiger Dateieintrag.')
        name = entry.get('path', '')
        # Deliberately narrow: never accept personal backups or arbitrary paths.
        if not isinstance(name, str) or name not in REQUIRED | OPTIONAL:
            raise ValueError(f'Nicht erlaubter Installationspfad: {name!r}')
        if name in seen or not re.fullmatch(r'[0-9a-f]{64}', str(entry.get('sha256', ''))):
            raise ValueError('Doppelter Dateieintrag oder ungültige SHA-256-Prüfsumme.')
        size = entry.get('size')
        if type(size) is not int or not 0 < size <= 64 * 1024**2:
            raise ValueError('Ungültige Dateigröße.')
        seen.add(name)
    if {e['path'] for e in base_entries} != REQUIRED or any(e['path'] not in OPTIONAL for e in optional):
        raise ValueError('Das Manifest enthält nicht alle benötigten Bootdateien.')
    return entries


def payload_files(root=ROOT):
    manifest = json.loads((root / 'install-manifest.json').read_text())
    files = []
    for entry in manifest_entries(manifest):
        path = root / entry['path']
        if path.is_symlink() or not path.is_file():
            raise ValueError(f'Bootdatei fehlt oder ist ein Symlink: {entry["path"]}')
        if path.stat().st_size != entry['size'] or digest(path).hex() != entry['sha256']:
            raise ValueError(f'Prüfsummenfehler: {entry["path"]}')
        files.append(path)
    return files


def fetch(url, limit):
    request = urllib.request.Request(url, headers={'User-Agent': 'imac-tdm-fast-installer/1'})
    with urllib.request.urlopen(request, timeout=60) as response:
        data = response.read(limit + 1)
    if len(data) > limit:
        raise ValueError('Download überschreitet die erwartete Größe.')
    return data


def download_payload(destination, ref):
    # Resolve mutable branches/tags once, then fetch every file at that commit.
    if re.fullmatch(r'[0-9a-fA-F]{40}', ref):
        commit = ref.lower()
    else:
        url = f'https://api.github.com/repos/{REPOSITORY}/commits/{urllib.parse.quote(ref, safe="")}'
        commit = json.loads(fetch(url, 2 * 1024**2)).get('sha', '')
        if not re.fullmatch(r'[0-9a-f]{40}', commit):
            raise ValueError('GitHub lieferte keine gültige Commit-ID.')
    base = f'https://raw.githubusercontent.com/{REPOSITORY}/{commit}'
    raw = fetch(f'{base}/install-manifest.json', 64 * 1024)
    entries = manifest_entries(json.loads(raw))
    print(f'Download von {REPOSITORY}, Commit {commit}', flush=True)
    for entry in entries:
        name = entry['path']
        print(f'  {name} ({entry["size"]} Bytes)', flush=True)
        data = fetch(f'{base}/{name}', entry['size'])
        if len(data) != entry['size'] or hashlib.sha256(data).hexdigest() != entry['sha256']:
            raise ValueError(f'Download-Prüfsumme stimmt nicht: {name}')
        path = destination / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    (destination / 'install-manifest.json').write_bytes(raw)
    (destination / 'SOURCE-COMMIT.txt').write_text(commit + '\n')
    return payload_files(destination)


def digest(path):
    result = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            result.update(block)
    return result.digest()


def install(device, files, root=ROOT):
    path = device['path']
    # Recheck after the user prompt, before the first write.
    fresh = find_disk(inventory(), path)
    validate(fresh)
    if identity(fresh) != identity(device):
        raise ValueError('Das Zielgerät hat sich seit der Auswahl geändert.')
    run('parted', '--script', '--align', 'optimal', path,
        'mklabel', 'gpt', 'mkpart', 'TDMFAST', 'fat32', '1MiB', '100%',
        'set', '1', 'esp', 'on')
    run('partprobe', path)
    run('udevadm', 'settle')
    fresh = find_disk(inventory(), path)
    validate(fresh)
    if identity(fresh) != identity(device):
        raise ValueError('Das Zielgerät hat sich während der Installation geändert.')
    partitions = fresh.get('children', [])
    if len(partitions) != 1 or partitions[0]['type'] != 'part':
        raise ValueError('Die neue Partition ist nicht eindeutig sichtbar. Abbruch.')
    partition = partitions[0]['path']
    run('mkfs.vfat', '-F', '32', '-n', 'TDMFAST', partition)
    directory = tempfile.mkdtemp(prefix='imac-tdm-fast-usb-')
    destination = Path(directory)
    mounted = False
    try:
        run('mount', '-t', 'vfat', '-o', 'nosuid,nodev,noexec', partition, directory)
        mounted = True
        for source in files:
            target = destination / source.relative_to(root)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)
        run('sync', '-f', directory)
        for source in files:
            if digest(source) != digest(destination / source.relative_to(root)):
                raise ValueError(f'Prüfsummenfehler: {source.relative_to(root)}')
    finally:
        if mounted:
            # If unmount fails, leave the mount and its files intact for recovery.
            try:
                run('umount', directory)
            except BaseException:
                print(f'Aushängen fehlgeschlagen. Mount bleibt unter {directory}.', file=sys.stderr)
                raise
        destination.rmdir()  # Never recursively delete a possible mount point.
    print('Fertig: Dateien geprüft und USB-Stick ausgehängt. Am iMac mit Alt/Option booten.')


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--list', action='store_true', help='USB-Laufwerke anzeigen')
    parser.add_argument('--device', help='Ganzes USB-Laufwerk, z. B. /dev/sdb')
    parser.add_argument('--dry-run', action='store_true', help='Nur prüfen und Plan anzeigen')
    parser.add_argument('--ref', default='main', help='GitHub-Branch, Tag oder Commit (Standard: main)')
    parser.add_argument('--source', type=Path, help='Statt Download ein lokales Verzeichnis mit Manifest verwenden')
    parser.add_argument('--download-only', type=Path, metavar='DIR', help='Nur herunterladen und prüfen; kein USB-Zugriff')
    args = parser.parse_args(argv)
    if args.download_only:
        if args.device or args.source or args.list or args.dry_run:
            parser.error('--download-only ist nicht mit Geräte-/Quelloptionen kombinierbar')
        destination = args.download_only.resolve()
        if destination.exists():
            raise ValueError('Download-Ziel existiert bereits; bitte neues Verzeichnis wählen.')
        destination.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix='.imac-tdm-fast-download-', dir=destination.parent) as temporary:
            staging = Path(temporary) / 'payload'
            staging.mkdir()
            download_payload(staging, args.ref)
            staging.rename(destination)
        print(f'Download vollständig geprüft: {destination}')
        return
    if not sys.platform.startswith('linux'):
        parser.error('Dieser Installer unterstützt Linux.')
    if not shutil.which('lsblk'):
        raise ValueError('lsblk fehlt (Paket util-linux).')
    if args.list:
        for device in inventory():
            if device.get('tran') == 'usb' and device['type'] == 'disk':
                print(describe(device))
                for node in walk(device):
                    if any(node.get('mountpoints') or []):
                        print(f"  Belegt: {node['path']} {node['mountpoints']}")
        return
    if not args.device:
        parser.error('--device oder --list angeben')
    path = str(Path(args.device).resolve())
    if not Path(path).exists() or not stat.S_ISBLK(Path(path).stat().st_mode):
        raise ValueError('Das Ziel ist kein vorhandenes Blockgerät.')
    device = find_disk(inventory(), path)
    validate(device)
    if not args.dry_run:
        for command in ('parted', 'partprobe', 'udevadm', 'mkfs.vfat', 'mount', 'umount', 'sync'):
            if not shutil.which(command):
                raise ValueError(f'Benötigter Befehl fehlt: {command}')
        if os.geteuid() != 0:
            raise ValueError('Installation benötigt root: mit sudo starten.')
        if not sys.stdin.isatty():
            raise ValueError('Installation benötigt eine interaktive Bestätigung im Terminal.')
    with tempfile.TemporaryDirectory(prefix='imac-tdm-fast-payload-') as temporary:
        if args.source:
            root = args.source.resolve()
            files = payload_files(root)
        else:
            root = Path(temporary) / 'download'
            root.mkdir()
            files = download_payload(root, args.ref)
        if sum(p.stat().st_size for p in files) + 64 * 1024**2 > int(device['size']):
            raise ValueError('Nicht genügend Platz für die Bootdateien.')
        print(describe(device))
        print('Plan: Alle Partitionen löschen; GPT + FAT32-ESP mit Label TDMFAST erstellen;')
        print(f'{len(files)} geprüfte Dateien kopieren, SHA-256 prüfen und aushängen.')
        if args.dry_run:
            print('Probelauf: Auf das USB-Laufwerk wurde nichts geschrieben.')
            return
        phrase = f'LOESCHEN {path}'
        if input(f'ALLE DATEN AUF {path} GEHEN VERLOREN. Zum Bestätigen "{phrase}" eingeben: ') != phrase:
            raise ValueError('Abgebrochen; nichts auf USB geschrieben.')
        # Revalidate downloads/local files before allowing destructive operations.
        files = payload_files(root)
        install(device, files, root)


if __name__ == '__main__':
    try:
        main()
    except (ValueError, OSError, subprocess.CalledProcessError, EOFError, KeyboardInterrupt) as error:
        print(f'Abbruch: {error}', file=sys.stderr)
        sys.exit(1)
