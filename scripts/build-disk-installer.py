#!/usr/bin/env python3
"""Build the one-shot, model-restricted internal-disk installer (Linux x86_64)."""
import gzip
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import shutil
import stat
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('payload_build', ROOT/'scripts/build.py')
b = importlib.util.module_from_spec(spec)
spec.loader.exec_module(b)

def build(destination, payload_root=ROOT):
    destination.mkdir(parents=True, exist_ok=False)
    files = {}
    def add(path, data, mode=0o644):
        files[path] = (data, stat.S_IFREG | mode, 0, 0)
    busybox = Path('/bin/busybox')
    if 'statically linked' not in subprocess.check_output(['file', str(busybox)], text=True):
        raise ValueError('Install busybox-static; a static BusyBox is required')
    add('bin/busybox', busybox.read_bytes(), 0o755)
    for program in ('sfdisk', 'mkfs.fat', 'blkid'):
        source = Path(shutil.which(program) or '/missing')
        add('bin/'+program, source.read_bytes(), 0o755)
        deps = subprocess.check_output(['ldd', str(source)], text=True)
        for dep in re.findall(r'(/[^\s()]+)', deps):
            path = Path(dep)
            add(dep.lstrip('/'), path.read_bytes(), 0o755)
    manifest = json.loads((payload_root/'install-manifest.json').read_text())
    checksums = []
    for item in manifest['files']:
        data = (payload_root/item['path']).read_bytes()
        if hashlib.sha256(data).hexdigest() != item['sha256'] or len(data) != item['size']:
            raise ValueError('Invalid payload: '+item['path'])
        add('payload/'+item['path'], data)
        checksums.append(item['sha256']+'  '+item['path'])
    add('payload/SHA256SUMS', ('\n'.join(checksums)+'\n').encode())
    add('init', (ROOT/'src/disk-installer-init.sh').read_bytes(), 0o755)
    files['dev/console'] = (b'', stat.S_IFCHR | 0o600, 5, 1)
    files['dev/null'] = (b'', stat.S_IFCHR | 0o666, 1, 3)
    directories = {'dev', 'proc', 'sys', 'run', 'source', 'target', 'tmp'}
    for name in files:
        for parent in Path(name).parents:
            if str(parent) != '.': directories.add(str(parent))
    records = [(n, b'', stat.S_IFDIR | 0o755, 0, 0) for n in sorted(directories, key=lambda n: (n.count('/'), n))]
    records += [(n, *v) for n,v in sorted(files.items())]
    records.append(('TRAILER!!!', b'', 0, 0, 0))
    archive = b''.join(b.entry(n, data, mode, i, major, minor) for i,(n,data,mode,major,minor) in enumerate(records, 1))
    (destination/'boot').mkdir()
    (destination/'EFI/BOOT').mkdir(parents=True)
    (destination/'boot/fast.gz').write_bytes(gzip.compress(archive, mtime=0))
    for name in ('boot/vmlinuz', 'boot/splash.png'):
        shutil.copyfile(ROOT/name, destination/name)
    (destination/'grub.cfg').write_text('''# One-shot internal disk installer; deliberately visible status output.
search --no-floppy --label TDMSETUP --set=root
terminal_output console
linux /boot/vmlinuz rdinit=/init console=tty0 quiet loglevel=3
initrd /boot/fast.gz
boot
echo "Installer failed to start."
sleep 30
''')
    embedded = destination/'embedded.cfg'
    embedded.write_text('search --no-floppy --label TDMSETUP --set=root\nconfigfile /grub.cfg\n')
    subprocess.run(['grub-mkstandalone', '-O', 'x86_64-efi', '--locales=', '--fonts=',
        '--install-modules='+b.MODULES, '--modules='+b.MODULES,
        '-o', str(destination/'EFI/BOOT/BOOTX64.EFI'), 'boot/grub/grub.cfg='+str(embedded)], check=True)
    embedded.unlink()
    payload=[]
    for item in manifest['files']:
        path=item['path'];data=(destination/path).read_bytes()
        payload.append(dict(path=path,size=len(data),sha256=hashlib.sha256(data).hexdigest()))
    (destination/'install-manifest.json').write_text(json.dumps(dict(version=1,files=payload),indent=2)+'\n')
    print(destination)

if __name__=='__main__':
    if len(sys.argv)!=2: raise SystemExit('Usage: build-disk-installer.py NEW_OUTPUT_DIRECTORY')
    build(Path(sys.argv[1]).resolve())
