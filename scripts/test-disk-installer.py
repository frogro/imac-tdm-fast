#!/usr/bin/env python3
"""Test the internal installer using disposable QEMU disks only."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import socket
import subprocess as sp
import tempfile
import time

ROOT=Path(__file__).resolve().parents[1]

def run(*args,**kwargs):
    return sp.run(args,check=True,stdout=sp.PIPE,stderr=sp.PIPE,**kwargs)

def usb_image(work,payload,name):
    fat=work/(name+'.fat')
    with fat.open('wb') as f:f.truncate(126*1024**2)
    run('mkfs.vfat','-F','32','-n','TDMSETUP',str(fat))
    staging=work/(name+'-files');staging.mkdir()
    for n in ('EFI','boot'):shutil.copytree(payload/n,staging/n)
    (staging/'grub.cfg').write_text((payload/'grub.cfg').read_text().replace('console=tty0','console=ttyS0,115200'))
    for n in ('EFI','boot','grub.cfg'):run('mcopy','-s','-i',str(fat),str(staging/n),'::/')
    image=work/(name+'.img')
    with image.open('wb') as f:f.truncate(128*1024**2)
    run('sfdisk',str(image),input=b'label: gpt\nunit: sectors\n\nstart=2048,size=258048,type=U\n')
    with image.open('r+b') as f,fat.open('rb') as src:f.seek(1024**2);shutil.copyfileobj(src,f)
    fat.unlink()
    return image

def boot(work,target,usb,tag,expect,model='ST31000528AS',shutdown=True,internal=False):
    vars=work/(tag+'.vars');shutil.copyfile('/usr/share/OVMF/OVMF_VARS_4M.fd',vars)
    log=work/(tag+'.log');qmp=work/(tag+'.qmp')
    args=['qemu-system-x86_64','-machine','q35','-m','256','-display','none','-no-reboot',
          '-serial','file:'+str(log),'-qmp','unix:'+str(qmp)+',server=on,wait=off',
          '-smbios','type=1,manufacturer=Apple Inc.,product=iMac11,,1',
          '-drive','if=pflash,format=raw,readonly=on,file=/usr/share/OVMF/OVMF_CODE_4M.fd',
          '-drive','if=pflash,format=raw,file='+str(vars),
          '-drive','if=none,id=internal,format=qcow2,file='+str(target),
          '-device','ide-hd,drive=internal,bus=ide.0,model='+model+',serial=TDM-INSTALL-TEST,bootindex=2']
    if internal:
        i=args.index('-smbios');del args[i:i+2]
    if usb:
        args+=['-device','ich9-usb-ehci1,id=ehci','-drive','if=none,id=stick,format=raw,file='+str(usb),
               '-device','usb-storage,bus=ehci.0,drive=stick,bootindex=1']
    with (work/(tag+'.stderr')).open('w') as err:
        proc=sp.Popen(args,stdout=err,stderr=err)
        try:
            deadline=time.monotonic()+90
            while time.monotonic()<deadline:
                text=log.read_text(errors='replace') if log.exists() else ''
                if expect in text:break
                if proc.poll() is not None:raise RuntimeError(tag+': early exit\n'+text+ (work/(tag+'.stderr')).read_text())
                time.sleep(.2)
            else:raise RuntimeError(tag+': timeout\n'+text)
            if internal:
                with socket.socket(socket.AF_UNIX) as sock:
                    sock.settimeout(5);sock.connect(str(qmp));stream=sock.makefile('rwb',buffering=0);stream.readline()
                    for cmd in ('qmp_capabilities','system_powerdown'):
                        stream.write(json.dumps({'execute':cmd}).encode()+b'\n')
                        while True:
                            answer=json.loads(stream.readline())
                            if 'error' in answer:raise RuntimeError(answer)
                            if 'return' in answer:break
            if shutdown:
                proc.wait(timeout=15)
                if proc.returncode:raise RuntimeError(tag+': QEMU failed')
            print('PASS:',tag,flush=True)
        finally:
            if proc.poll() is None:proc.kill();proc.wait()

def main(payload):
    with tempfile.TemporaryDirectory(prefix='tdm-installer-test-') as tmp:
        w=Path(tmp);target=w/'internal.qcow2'
        run('qemu-img','create','-f','qcow2',str(target),'1000204886016')
        usb=usb_image(w,payload,'usb')
        # Wrong-model guard must stop before allocating any guest disk sectors.
        before=run('qemu-img','map','--output=json',str(target)).stdout
        boot(w,target,usb,'wrong-model','Interne ST31000528AS mit 1 TB nicht gefunden',model='OTHER-DISK',shutdown=False)
        assert before==run('qemu-img','map','--output=json',str(target)).stdout
        boot(w,target,usb,'install','ERFOLGREICH: TDM Fast intern installiert und geprueft.')
        reference=w/'installed-reference.qcow2';shutil.copyfile(target,reference)
        boot(w,target,usb,'used-usb','Dieser Stick wurde bereits verwendet.')
        run('qemu-img','compare',str(reference),str(target))
        fresh=usb_image(w,payload,'fresh-usb')
        boot(w,target,fresh,'existing-install','TDM Fast ist bereits installiert.')
        run('qemu-img','compare',str(reference),str(target))
        # Build a different valid payload to exercise updating an existing install.
        variant=w/'variant';variant.mkdir()
        manifest=json.loads((ROOT/'install-manifest.json').read_text())
        for item in manifest['files']:
            dest=variant/item['path'];dest.parent.mkdir(parents=True,exist_ok=True)
            data=(ROOT/item['path']).read_bytes()
            if item['path']=='grub.cfg': data+=b'\n# update regression fixture\n'
            dest.write_bytes(data);item['size']=len(data);item['sha256']=hashlib.sha256(data).hexdigest()
        (variant/'install-manifest.json').write_text(json.dumps(manifest))
        spec=importlib.util.spec_from_file_location('installer_builder',ROOT/'scripts/build-disk-installer.py')
        builder=importlib.util.module_from_spec(spec);spec.loader.exec_module(builder)
        newer=w/'newer';builder.build(newer,variant)
        update_usb=usb_image(w,newer,'update-usb')
        boot(w,target,update_usb,'update-install','ERFOLGREICH: TDM Fast intern installiert und geprueft.')
        assert 'Partitionierung bleibt erhalten' in (w/'update-install.log').read_text()
        latest=usb_image(w,newer,'latest-usb')
        updated_reference=w/'updated-reference.qcow2';shutil.copyfile(target,updated_reference)
        boot(w,target,latest,'updated-noop','Aktuelle Version; keine Aenderung.')
        run('qemu-img','compare',str(updated_reference),str(target))
        # Normal QEMU DMI avoids raw SMC I/O; installed files remain unchanged.
        boot(w,target,None,'internal-boot','Power button ready',internal=True)
        print('PASS: all installer checks; only temporary virtual disks used',flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('payload',type=Path)
    main(p.parse_args().payload.resolve())
