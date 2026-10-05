#!/usr/bin/env python3
"""Build a separate USB-only audio diagnostic, never an internal installer."""
import argparse,gzip,hashlib,importlib.util,json,re,shutil,stat,subprocess,io,math,struct,wave
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('b',ROOT/'scripts/build.py');b=importlib.util.module_from_spec(spec);spec.loader.exec_module(b)
def build(out,serial,test=False):
    if not re.fullmatch(r'[A-Za-z0-9_-]{1,64}',serial):raise ValueError('Invalid USB serial')
    out.mkdir(parents=True,exist_ok=False)
    for n in ('EFI/BOOT','boot'): (out/n).mkdir(parents=True,exist_ok=True)
    for n in ('EFI/BOOT/BOOTX64.EFI','boot/vmlinuz','boot/splash.png'):shutil.copyfile(ROOT/n,out/n)
    cfg='''search --no-floppy --label TDMFAST --set=root
terminal_output console
linux /boot/vmlinuz rdinit=/init console=tty0 quiet loglevel=3
initrd /boot/fast.gz
boot
'''
    if test: cfg=cfg.replace('console=tty0','console=ttyS0,115200 diag.test=1')
    (out/'grub.cfg').write_text(cfg)
    files={}
    def add(n,data,mode=0o644):files[n]=(data,stat.S_IFREG|mode,0,0)
    add('bin/busybox',Path('/bin/busybox').read_bytes(),0o755)
    if 'statically linked' not in subprocess.check_output(['file','/bin/busybox'],text=True):raise ValueError('busybox-static required')
    for cmd in ('amixer','aplay','arecord','lspci','alsaloop'):
        p=Path(shutil.which(cmd));add('bin/'+cmd,p.read_bytes(),0o755)
        for dep in re.findall(r'(/[^\s()]+)',subprocess.check_output(['ldd',str(p)],text=True)):
            add(dep.lstrip('/'),Path(dep).read_bytes(),0o755)
    for p in Path('/usr/share/alsa').rglob('*'):
        if p.is_file():add(str(p).lstrip('/'),p.read_bytes())
    # Reuse the checked static programs and exact modules from the normal image.
    manifest=json.loads((ROOT/'install-manifest.json').read_text())
    expected=next(x['sha256'] for x in manifest['files'] if x['path']=='boot/fast.gz')
    blob=(ROOT/'boot/fast.gz').read_bytes()
    if hashlib.sha256(blob).hexdigest()!=expected:raise ValueError('Normal payload hash mismatch')
    data=gzip.decompress(blob);pos=0
    while data[pos:pos+6]==b'070701':
        h=[int(data[pos+6+i*8:pos+14+i*8],16) for i in range(13)]
        n=data[pos+110:pos+110+h[11]-1].decode();pos=(pos+110+h[11]+3)&~3
        content=data[pos:pos+h[6]];pos=(pos+h[6]+3)&~3
        if n=='TRAILER!!!':break
        if n in ('smc','audio') or (n.startswith('modules/') and n.endswith('.ko')):add(n,content,0o755 if n in ('smc','audio') else 0o644)
    add('init',(ROOT/'src/audio-diagnostic-init.sh').read_bytes(),0o755)
    add('audio-route-test.sh',(ROOT/'src/audio-route-test.sh').read_bytes(),0o755)
    tone=io.BytesIO()
    with wave.open(tone,'wb') as wav:
        wav.setparams((2,2,48000,0,'NONE','not compressed'))
        frames=bytearray()
        for i in range(48000*3):
            t=i/48000; phase=t%1
            v=int(5000*math.sin(2*math.pi*440*t)*min(1,phase*50,max(0,(0.5-phase)*50))) if phase<0.5 else 0
            frames.extend(struct.pack('<hh',v,v))
        wav.writeframes(frames)
    add('speaker-test.wav',tone.getvalue())
    add('usb-serial' ,(serial+'\n').encode())
    add('expected-grub',(hashlib.sha256(cfg.encode()).hexdigest()+'  /source/grub.cfg\n').encode())
    files['dev/console']=(b'',stat.S_IFCHR|0o600,5,1);files['dev/null']=(b'',stat.S_IFCHR|0o666,1,3)
    dirs={'proc','sys','dev','run','tmp','source'}
    for n in files:
        dirs.update(str(p) for p in Path(n).parents if str(p)!='.')
    records=[(n,b'',stat.S_IFDIR|0o755,0,0) for n in sorted(dirs,key=lambda n:(n.count('/'),n))]+[(n,*v) for n,v in sorted(files.items())]+[('TRAILER!!!',b'',0,0,0)]
    archive=b''.join(b.entry(n,d,m,i,a,c) for i,(n,d,m,a,c) in enumerate(records,1))
    (out/'boot/fast.gz').write_bytes(gzip.compress(archive,mtime=0))
    manifest['files']=[dict(path=x['path'],size=(out/x['path']).stat().st_size,sha256=hashlib.sha256((out/x['path']).read_bytes()).hexdigest()) for x in manifest['files']]
    (out/'install-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(out)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('output',type=Path);p.add_argument('--usb-serial',required=True);p.add_argument('--test',action='store_true',help='VM only: skip SMC writes');a=p.parse_args();build(a.output.resolve(),a.usb_serial,a.test)
