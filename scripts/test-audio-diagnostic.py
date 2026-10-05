#!/usr/bin/env python3
"""VM test: persistent USB report, HDA inventory, internal disk unchanged."""
from pathlib import Path
import hashlib,subprocess,tempfile,shutil,time,sys
ROOT=Path(__file__).resolve().parents[1]
with tempfile.TemporaryDirectory(prefix='tdm-audio-vm-') as tmp:
 w=Path(tmp);payload=w/'payload'
 subprocess.run([sys.executable,str(ROOT/'scripts/build-audio-diagnostic.py'),str(payload),'--usb-serial','TDMAUDIOTEST','--test'],check=True)
 fat=w/'fat.img';fat.write_bytes(b'');subprocess.run(['truncate','-s','126M',str(fat)],check=True)
 subprocess.run(['mkfs.vfat','-F','32','-n','TDMFAST',str(fat)],check=True,stdout=subprocess.DEVNULL)
 for n in ('EFI','boot','grub.cfg'):subprocess.run(['mcopy','-s','-i',str(fat),str(payload/n),'::/'],check=True)
 disk=w/'usb.img';subprocess.run(['truncate','-s','128M',str(disk)],check=True)
 subprocess.run(['sfdisk',str(disk)],input=b'label: gpt\nunit: sectors\n\nstart=2048,size=258048,type=U\n',check=True,stdout=subprocess.DEVNULL)
 with disk.open('r+b') as f,fat.open('rb') as src:f.seek(1048576);shutil.copyfileobj(src,f)
 internal=w/'internal.img';internal.write_bytes(b'KEEP_INTERNAL_DISK_UNCHANGED\n'*1000)
 with internal.open('ab') as f:f.truncate(16*1024**2)
 before=hashlib.sha256(internal.read_bytes()).hexdigest()
 shutil.copyfile('/usr/share/OVMF/OVMF_VARS_4M.fd',w/'vars.fd')
 args=['qemu-system-x86_64','-machine','q35','-m','512','-display','none','-no-reboot','-serial','file:'+str(w/'serial.log'),
 '-drive','if=pflash,format=raw,readonly=on,file=/usr/share/OVMF/OVMF_CODE_4M.fd','-drive','if=pflash,format=raw,file='+str(w/'vars.fd'),
 '-device','ich9-usb-ehci1,id=ehci','-drive','if=none,id=stick,format=raw,file='+str(disk),'-device','usb-storage,bus=ehci.0,drive=stick,serial=TDMAUDIOTEST,bootindex=1',
 '-drive','format=raw,file='+str(internal),'-device','intel-hda','-device','hda-duplex']
 with (w/'qemu.log').open('w') as err:
  p=subprocess.Popen(args,stderr=err,stdout=err)
  try:p.wait(timeout=90)
  except BaseException:p.kill();p.wait();print((w/'serial.log').read_text());raise
 log=(w/'serial.log').read_text(errors='replace')
 assert p.returncode==0 and 'AUDIO_DIAGNOSTIC_COMPLETE' in log,log
 assert hashlib.sha256(internal.read_bytes()).hexdigest()==before
 for name in ('before.txt','after.txt','final.txt','COMPLETE.txt'):
  subprocess.run(['mcopy','-i',str(disk)+'@@1048576','::/audio-diag-1/'+name,str(w/name)],check=True)
 report=(w/'after.txt').read_text()
 assert 'HDA Intel' in report and 'Codec:' in report and 'Capture' in report,report
 print('PASS: USB reports persisted, HDA codec/capture inventoried, internal disk unchanged, automatic poweroff')
