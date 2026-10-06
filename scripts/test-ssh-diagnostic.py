#!/usr/bin/env python3
"""Test LAN DHCP, pinned-host SSH, audio status and no disk mounts in QEMU."""
import argparse,importlib.util,json,shutil,socket,subprocess as sp,tempfile,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('disk_test',ROOT/'scripts/test-disk-installer.py')
b=importlib.util.module_from_spec(spec);spec.loader.exec_module(b)
def test(payload,identity):
 with tempfile.TemporaryDirectory(prefix='tdm-ssh-test-') as tmp:
  w=Path(tmp);staging=w/'payload';shutil.copytree(payload,staging)
  p=staging/'grub.cfg';p.write_text(p.read_text().replace('rdinit=/init','rdinit=/init tdm.test=1'))
  usb=b.usb_image(w,staging,'usb')
  b.run('mlabel','-i',str(usb)+'@@1048576','::TDMFAST')
  shutil.copyfile('/usr/share/OVMF/OVMF_VARS_4M.fd',w/'vars')
  with socket.socket() as s:s.bind(('127.0.0.1',0));port=s.getsockname()[1]
  host=(payload/'ssh-host-key.pub').read_text().strip().split()
  (w/'known_hosts').write_text('[127.0.0.1]:%d %s %s\n'%(port,host[0],host[1]))
  args=['qemu-system-x86_64','-machine','q35','-m','256','-display','none','-no-reboot',
   '-serial','file:'+str(w/'serial.log'),'-device','intel-hda','-device','hda-duplex',
   '-drive','if=pflash,format=raw,readonly=on,file=/usr/share/OVMF/OVMF_CODE_4M.fd',
   '-drive','if=pflash,format=raw,file='+str(w/'vars'),
   '-device','qemu-xhci','-drive','if=none,id=stick,format=raw,file='+str(usb),'-device','usb-storage,drive=stick',
   '-netdev',f'user,id=lan,hostfwd=tcp:127.0.0.1:{port}-:22','-device','e1000,netdev=lan']
  ssh=['ssh','-F','/dev/null','-o','BatchMode=yes','-o','IdentitiesOnly=yes','-o','ConnectTimeout=3',
       '-o','StrictHostKeyChecking=yes','-o','UserKnownHostsFile='+str(w/'known_hosts'),'-i',str(identity),'-p',str(port),'root@127.0.0.1']
  with (w/'qemu.log').open('w') as err:
   proc=sp.Popen(args,stdout=err,stderr=err)
   try:
    deadline=time.monotonic()+90
    while time.monotonic()<deadline:
     result=sp.run(ssh+['cat /run/ssh-address.txt'],capture_output=True,text=True)
     if result.returncode==0:break
     if proc.poll() is not None:raise RuntimeError((w/'qemu.log').read_text())
     time.sleep(1)
    else:raise RuntimeError(result.stderr+(w/'serial.log').read_text())
    assert '10.0.2.15' in result.stdout,result.stdout
    denied=sp.run(ssh[:-1]+['-o','PubkeyAuthentication=no',ssh[-1],'true'],capture_output=True,timeout=10)
    assert denied.returncode!=0, 'Login without a public key succeeded'
    print('PASS: DHCP and key-only SSH with pinned host identity',flush=True)
    result=sp.run(ssh+['tdm-audio-status; cat /proc/mounts'],capture_output=True,text=True,check=True)
    assert result.stdout.count('state: RUNNING')>=2,result.stdout
    assert '/dev/sd' not in result.stdout and '/dev/hd' not in result.stdout,result.stdout
    # A PTY is needed for an interactive maintenance shell.
    terminal=sp.Popen(ssh[:-1]+['-tt',ssh[-1],'tty'],stdin=sp.PIPE,stdout=sp.PIPE,stderr=sp.PIPE,text=True)
    try:
     terminal.wait(timeout=10)
     output=terminal.stdout.read()
     assert terminal.returncode==0 and '/dev/pts/' in output,output+terminal.stderr.read()
    finally:
     terminal.stdin.close()
     if terminal.poll() is None:terminal.kill();terminal.wait()
    print('PASS: running audio, read-only status, interactive PTY and no data disks mounted',flush=True)
    sp.run(ssh+['poweroff -f'],capture_output=True,timeout=10)
    proc.wait(timeout=10)
    print('PASS: diagnostic guest powered off',flush=True)
   finally:
    if proc.poll() is None:proc.kill();proc.wait()
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('payload',type=Path);p.add_argument('--identity',type=Path,required=True)
 a=p.parse_args();test(a.payload.resolve(),a.identity.resolve())
