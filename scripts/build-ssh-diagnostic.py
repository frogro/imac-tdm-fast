#!/usr/bin/env python3
"""Build a private USB-only TDM image with LAN and key-only SSH."""
import argparse
import gzip
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import stat
import subprocess as sp
import tempfile

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('payload_build', ROOT/'scripts/build.py')
b = importlib.util.module_from_spec(spec)
spec.loader.exec_module(b)

def build(out, public_key, tools_root):
    key = public_key.read_text().strip()
    if '\n' in key or not key.startswith(('ssh-ed25519 ', 'ssh-rsa ', 'ecdsa-sha2-')):
        raise ValueError('Provide one OpenSSH public key, never a private key')
    sp.run(['ssh-keygen', '-lf', str(public_key)], check=True, stdout=sp.DEVNULL)
    manifest = json.loads((ROOT/'install-manifest.json').read_text())
    files = {}
    for item in manifest['files']:
        data = (ROOT/item['path']).read_bytes()
        if hashlib.sha256(data).hexdigest() != item['sha256']:
            raise ValueError('Normal payload checksum mismatch')
    data = gzip.decompress((ROOT/'boot/fast.gz').read_bytes()); pos=0
    while data[pos:pos+6] == b'070701':
        h=[int(data[pos+6+i*8:pos+14+i*8],16) for i in range(13)]
        n=data[pos+110:pos+110+h[11]-1].decode();pos=(pos+110+h[11]+3)&~3
        content=data[pos:pos+h[6]];pos=(pos+h[6]+3)&~3
        if n=='TRAILER!!!': break
        files[n]=(content,h[1],h[9],h[10])
    def add(n, data, mode=0o644): files[n]=(data,stat.S_IFREG|mode,0,0)
    # Binary packages may be installed or merely extracted to --tools-root.
    libdir=tools_root/'usr/lib/x86_64-linux-gnu'
    env=dict(os.environ,LD_LIBRARY_PATH=str(libdir))
    for name,rel in [('dropbear','usr/sbin/dropbear')]:
        program=tools_root/rel
        add('bin/'+name,program.read_bytes(),0o755)
        deps=sp.check_output(['ldd',str(program)],env=env,text=True)
        if 'not found' in deps: raise ValueError(deps)
        for path in re.findall(r'(/[^\s()]+)',deps):
            p=Path(path)
            dest=str(p.relative_to(tools_root)) if tools_root != Path('/') and p.is_relative_to(tools_root) else path.lstrip('/')
            add(dest,p.read_bytes(),0o755)
    out.mkdir(parents=True,exist_ok=False,mode=0o700)
    with tempfile.TemporaryDirectory() as tmp:
        tmp=Path(tmp)
        sp.run(['musl-gcc','-DTDM_SSH_DIAGNOSTIC','-idirafter','/usr/include','-idirafter','/usr/include/x86_64-linux-gnu','-static','-Os','-s','-Wall','-Wextra','-Werror','-o',str(tmp/'init'),str(ROOT/'src/init.c')],check=True)
        add('init',(tmp/'init').read_bytes(),0o755)
        keyfile=tmp/'hostkey'
        sp.run([str(tools_root/'usr/bin/dropbearkey'),'-t','ed25519','-f',str(keyfile)],env=env,check=True,stdout=sp.DEVNULL)
        host=sp.check_output([str(tools_root/'usr/bin/dropbearkey'),'-y','-f',str(keyfile)],env=env,text=True)
        hostpub=next(line for line in host.splitlines() if line.startswith('ssh-ed25519 '))
        (out/'ssh-host-key.pub').write_text(hostpub+'\n')
        add('etc/dropbear/hostkey',keyfile.read_bytes(),0o600)
    add('root/.ssh/authorized_keys',(key+'\n').encode(),0o600)
    add('etc/passwd',b'root:x:0:0:TDM diagnostic:/root:/bin/sh\n')
    add('etc/shadow',b'root::0:0:99999:7:::\n',0o600)
    add('etc/group',b'root:x:0:\n')
    add('etc/shells',b'/bin/sh\n')
    add('ssh-start.sh',(ROOT/'src/ssh-start.sh').read_bytes(),0o755)
    add('dhcp.sh',(ROOT/'src/ssh-dhcp.sh').read_bytes(),0o755)
    add('bin/tdm-audio-status',(ROOT/'src/audio-status.sh').read_bytes(),0o755)
    network=json.loads((ROOT/'vendor/network/manifest.json').read_text())
    for item in network['files']:
        content=(ROOT/'vendor/network'/item['file']).read_bytes()
        if hashlib.sha256(content).hexdigest()!=item['sha256']:raise ValueError('Network module checksum')
        add('network/'+item['file'],content)
    for name in list(files):
        for p in Path(name).parents:
            if str(p)!='.':files.setdefault(str(p),(b'',stat.S_IFDIR|0o755,0,0))
    files['root']=(b'',stat.S_IFDIR|0o700,0,0)
    files['root/.ssh']=(b'',stat.S_IFDIR|0o700,0,0)
    records=sorted(files.items(),key=lambda item:(item[0].count('/'),item[0]))
    records.append(('TRAILER!!!',(b'',0,0,0)))
    archive=b''.join(b.entry(n,d,m,i,a,c) for i,(n,(d,m,a,c)) in enumerate(records,1))
    for item in manifest['files']:
        dest=out/item['path'];dest.parent.mkdir(parents=True,exist_ok=True)
        if item['path']=='boot/fast.gz':dest.write_bytes(gzip.compress(archive,mtime=0))
        else:shutil.copyfile(ROOT/item['path'],dest)
        item['size']=dest.stat().st_size;item['sha256']=hashlib.sha256(dest.read_bytes()).hexdigest()
    (out/'install-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print('Private SSH diagnostic image:',out)
    print('Host identity:',hostpub.split()[1][:24]+'…; public key in ssh-host-key.pub')

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('output',type=Path)
    p.add_argument('--authorized-key',required=True,type=Path)
    p.add_argument('--tools-root',type=Path,default=Path('/'))
    a=p.parse_args();build(a.output.resolve(),a.authorized_key.resolve(),a.tools_root.resolve())
