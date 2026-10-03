#!/usr/bin/env python3
"""Build the minimal RAM system and standalone x86_64 EFI loader."""
import gzip
import hashlib
import json
import os
from pathlib import Path
import platform
import stat
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
MODULES = 'part_gpt part_msdos fat search search_label normal configfile linux boot echo sleep'


def entry(name, data, mode, inode, major=0, minor=0):
    name = name.encode() + b'\0'
    fields = (inode, mode, 0, 0, 1, 0, len(data), 0, 0, major, minor, len(name), 0)
    record = b'070701' + ''.join(f'{v:08x}' for v in fields).encode() + name
    record += b'\0' * (-len(record) % 4)
    record += data + b'\0' * (-len(data) % 4)
    return record


def build():
    if platform.machine() != 'x86_64':
        raise SystemExit('Build on x86_64 Linux (not the Pi)')
    provenance = json.loads((ROOT/'sources.json').read_text())
    kernel = (ROOT/'boot/vmlinuz').read_bytes()
    if hashlib.sha256(kernel).hexdigest() != provenance['kernel_sha256']:
        raise ValueError('Kernel differs from pinned upstream')
    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp)
        env = dict(os.environ, SOURCE_DATE_EPOCH='0')
        for name, source in [('init', 'src/init.c'), ('smc', 'src/smc/SmcDumpKey.c')]:
            subprocess.run(['musl-gcc', '-idirafter', '/usr/include', '-idirafter', '/usr/include/x86_64-linux-gnu', '-static', '-Os', '-s', '-Wall', '-Wextra', '-Werror',
                '-fno-ident', '-Wl,--build-id=none', '-o', str(work/name), str(ROOT/source)], check=True, env=env)
        records = []
        for name in ('dev', 'proc', 'sys'):
            records.append((name, b'', stat.S_IFDIR | 0o755, 0, 0))
        records += [('dev/console', b'', stat.S_IFCHR | 0o600, 5, 1),
                    ('dev/null', b'', stat.S_IFCHR | 0o666, 1, 3)]
        for name in ('init', 'smc'):
            records.append((name, (work/name).read_bytes(), stat.S_IFREG | 0o755, 0, 0))
        records.append(('TRAILER!!!', b'', 0, 0, 0))
        payload = b''.join(entry(n, d, m, i, a, b) for i, (n,d,m,a,b) in enumerate(records, 1))
        payload += b'\0' * (-len(payload) % 512)
        (ROOT/'boot/fast.gz').write_bytes(gzip.compress(payload, compresslevel=9, mtime=0))
        embedded = work/'grub.cfg'
        embedded.write_text('search --no-floppy --label TDMFAST --set=root\nconfigfile /grub.cfg\n')
        subprocess.run(['grub-mkstandalone', '-O', 'x86_64-efi', '--locales=', '--fonts=',
            '--install-modules='+MODULES, '--modules='+MODULES,
            '-o', str(ROOT/'EFI/BOOT/BOOTX64.EFI'), 'boot/grub/grub.cfg='+str(embedded)], check=True, env=env)
    names = ['EFI/BOOT/BOOTX64.EFI', 'boot/vmlinuz', 'boot/fast.gz', 'grub.cfg']
    files = []
    for name in names:
        data = (ROOT/name).read_bytes()
        files.append(dict(path=name, size=len(data), sha256=hashlib.sha256(data).hexdigest()))
    (ROOT/'install-manifest.json').write_text(json.dumps(dict(version=1, files=files), indent=2)+'\n')
    print('Boot payload:', sum(x['size'] for x in files), 'bytes')


if __name__ == '__main__':
    build()
