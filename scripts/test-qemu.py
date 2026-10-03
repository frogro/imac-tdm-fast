#!/usr/bin/env python3
"""Boot a disposable USB image in OVMF and press its virtual ACPI power button."""
import json
from pathlib import Path
import shutil
import socket
import subprocess
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]


def test(screenshot=None):
    with tempfile.TemporaryDirectory(prefix='tdm-qemu-') as tmp:
        work = Path(tmp)
        fat = work/'esp.img'
        with fat.open('wb') as f: f.truncate(126*1024**2)
        subprocess.run(['mkfs.vfat', '-F', '32', '-n', 'TDMFAST', str(fat)], check=True, stdout=subprocess.DEVNULL)
        staging = work/'files'
        staging.mkdir()
        for name in ('EFI', 'boot'):
            shutil.copytree(ROOT/name, staging/name)
        cfg = (ROOT/'grub.cfg').read_text().replace('rdinit=/init', 'rdinit=/init console=ttyS0 tdm.test=1')
        (staging/'grub.cfg').write_text(cfg)
        for name in ('EFI', 'boot', 'grub.cfg'):
            subprocess.run(['mcopy', '-s', '-i', str(fat), str(staging/name), '::/'], check=True)
        image = work/'usb.img'
        with image.open('wb') as f: f.truncate(128*1024**2)
        subprocess.run(['sfdisk', str(image)], input=b'label: gpt\nunit: sectors\n\nstart=2048,size=258048,type=U\n', check=True, stdout=subprocess.DEVNULL)
        with image.open('r+b') as out, fat.open('rb') as src:
            out.seek(1024**2); shutil.copyfileobj(src,out)
        shutil.copyfile('/usr/share/OVMF/OVMF_VARS_4M.fd', work/'vars.fd')
        log = work/'serial.log'
        qmp_path = work/'qmp.sock'
        args = ['qemu-system-x86_64', '-machine', 'q35', '-m', '256', '-no-reboot',
            '-display', 'none', '-serial', 'file:'+str(log),
            '-drive', 'if=pflash,format=raw,readonly=on,file=/usr/share/OVMF/OVMF_CODE_4M.fd',
            '-drive', 'if=pflash,format=raw,file='+str(work/'vars.fd'),
            '-device', 'qemu-xhci', '-drive', 'if=none,id=stick,format=raw,file='+str(image),
            '-device', 'usb-storage,drive=stick', '-qmp', 'unix:'+str(qmp_path)+',server=on,wait=off']
        start = time.monotonic()
        with (work/'qemu.log').open('w') as err:
            proc = subprocess.Popen(args, stdout=err, stderr=err)
            try:
                deadline = start+60
                while time.monotonic() < deadline:
                    text = log.read_text(errors='replace') if log.exists() else ''
                    if 'Power button ready' in text and 'TEST: SMC hardware access disabled' in text: break
                    if proc.poll() is not None: raise RuntimeError('QEMU exited: '+(work/'qemu.log').read_text()+text)
                    time.sleep(.2)
                else: raise RuntimeError('Boot timed out: '+text)
                print('EFI/USB boot ready after %.2f s (QEMU/TCG, not iMac timing)' % (time.monotonic()-start), flush=True)
                with socket.socket(socket.AF_UNIX) as sock:
                    sock.settimeout(5); sock.connect(str(qmp_path))
                    stream=sock.makefile('rwb',buffering=0)
                    json.loads(stream.readline())
                    def command(name, arguments=None):
                        stream.write(json.dumps({'execute':name, 'arguments': arguments or {}}).encode()+b'\n')
                        while True:
                            response=json.loads(stream.readline())
                            if 'error' in response: raise RuntimeError(response)
                            if 'return' in response: return
                    command('qmp_capabilities')
                    check = work/'display.ppm'
                    command('screendump', {'filename': str(check), 'format': 'ppm'})
                    magic, dimensions, maximum, pixels = check.read_bytes().split(b'\n', 3)
                    if magic != b'P6' or maximum != b'255': raise RuntimeError('Unexpected screenshot format')
                    width, height = map(int, dimensions.split())
                    expected = bytearray(width * height * 3)
                    mask = (ROOT/'assets/apple.gray').read_bytes()
                    for y in range(180):
                        row = b''.join(bytes([g,g,g]) for g in mask[y*180:(y+1)*180])
                        start = (((height-180)//2+y)*width+(width-180)//2)*3
                        expected[start:start+len(row)] = row
                    if pixels != expected: raise RuntimeError('Display differs from centered logo on black')
                    print('PASS: screen contains only centered logo on black', flush=True)
                    if screenshot:
                        command('screendump', {'filename': str(Path(screenshot).resolve()), 'format': 'png'})
                    command('system_powerdown')
                proc.wait(timeout=10)
                text=log.read_text(errors='replace')
                if proc.returncode != 0 or 'Power button: immediate poweroff' not in text:
                    raise RuntimeError('ACPI poweroff failed: '+text)
                print(text[text.index('[tdm-fast'):], flush=True)
                print('PASS: EFI USB boot, minimal PID 1, ACPI power button, VM powered off')
            finally:
                if proc.poll() is None:
                    proc.kill(); proc.wait()


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--screenshot', type=Path)
    test(parser.parse_args().screenshot)
