import copy
import gzip
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('installer_payload', ROOT/'scripts/install-usb.py')
installer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(installer)


class PayloadTests(unittest.TestCase):
    def test_manifest_and_static_initramfs(self):
        self.assertEqual(len(installer.payload_files()), 5)
        archive = gzip.decompress((ROOT/'boot/fast.gz').read_bytes())
        pos = 0
        files = {}
        while True:
            self.assertEqual(archive[pos:pos+6], b'070701')
            fields = [int(archive[pos+6+i*8:pos+14+i*8], 16) for i in range(13)]
            size, namesize = fields[6], fields[11]
            name = archive[pos+110:pos+110+namesize-1].decode()
            pos = (pos+110+namesize+3)&~3
            data = archive[pos:pos+size]
            pos = (pos+size+3)&~3
            if name == 'TRAILER!!!': break
            files[name] = data
        modules = json.loads((ROOT/'vendor/modules/manifest.json').read_text())
        self.assertTrue(( {'dev', 'proc', 'sys', 'dev/console', 'dev/null',
            'init', 'smc', 'audio', 'splash.gray', 'health', 'modules', 'run'} |
            {'modules/'+item['file'] for item in modules['files']}) <= set(files))
        for name in ('bin/busybox','bin/amixer','bin/alsaloop','audio-start.sh','gpu-start.sh','gpu-idle','usr/share/alsa/alsa.conf'):
            self.assertIn(name, files)
        self.assertNotIn('speaker-test.wav',files)
        self.assertNotIn('audio-route-test.sh',files)
        with tempfile.TemporaryDirectory() as tmp:
            for name in ('init', 'smc', 'health', 'audio', 'gpu-idle'):
                path = Path(tmp)/name; path.write_bytes(files[name])
                header = subprocess.check_output(['readelf', '-l', str(path)], text=True)
                self.assertNotIn('INTERP', header)
                self.assertEqual(files[name][:5], b'\x7fELF\x02')

    def test_manifest_rejects_path_injection_missing_files_and_hash_errors(self):
        manifest = json.loads((ROOT/'install-manifest.json').read_text())
        for path in ('../bad', '/etc/passwd', 'boot/custom.gz'):
            bad=copy.deepcopy(manifest); bad['files'][0]['path']=path
            with self.assertRaises(ValueError): installer.manifest_entries(bad)
        bad=copy.deepcopy(manifest); bad['files'].pop()
        with self.assertRaises(ValueError): installer.manifest_entries(bad)
        with tempfile.TemporaryDirectory() as tmp:
            target=Path(tmp)
            (target/'install-manifest.json').write_text(json.dumps(manifest))
            for entry in manifest['files']:
                p=target/entry['path'];p.parent.mkdir(parents=True,exist_ok=True)
                p.write_bytes((ROOT/entry['path']).read_bytes())
            (target/'grub.cfg').write_text('corrupt')
            with self.assertRaises(ValueError): installer.payload_files(target)

    def test_download_pins_all_files_to_one_commit(self):
        manifest=(ROOT/'install-manifest.json').read_bytes()
        commit='a'*40
        urls=[]
        def fetch(url, limit):
            urls.append(url)
            if '/commits/' in url: return json.dumps({'sha':commit}).encode()
            self.assertIn('/'+commit+'/', url)
            name=url.split('/'+commit+'/',1)[1]
            return manifest if name=='install-manifest.json' else (ROOT/name).read_bytes()
        with tempfile.TemporaryDirectory() as tmp, patch.object(installer,'fetch',side_effect=fetch):
            files=installer.download_payload(Path(tmp),'main')
            self.assertEqual(len(files),5)
            self.assertEqual((Path(tmp)/'SOURCE-COMMIT.txt').read_text().strip(),commit)
        self.assertEqual(len(urls),7)

    def test_no_menu_or_boot_wait_and_grub_syntax(self):
        cfg=(ROOT/'grub.cfg').read_text()
        for token in ('menuentry', 'waitusb=', 'corepure64', 'tdm.test=1'):
            self.assertNotIn(token,cfg)
        self.assertNotIn('sleep',cfg.split('\nboot\n')[0])
        subprocess.run(['grub-script-check',str(ROOT/'grub.cfg')],check=True)


if __name__ == '__main__': unittest.main()
