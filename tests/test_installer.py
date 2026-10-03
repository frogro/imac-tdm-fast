import copy
import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('installer', Path(__file__).resolve().parents[1] / 'scripts/install-usb.py')
installer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(installer)


def disk():
    return dict(path='/dev/testusb', type='disk', tran='usb', ro=False,
                size=1024**3, model='Test', serial='123', **{'maj:min': '8:99'},
                mountpoints=[], children=[])


class InstallerTests(unittest.TestCase):
    def test_rejects_unsafe_targets(self):
        for changes in [dict(type='part'), dict(tran='nvme'), dict(ro=True),
                        dict(size=0), dict(mountpoints=['/']),
                        dict(children=[dict(path='/dev/testusb1', type='part', mountpoints=['/home'])]),
                        dict(children=[dict(path='/dev/testusb1', type='part', mountpoints=['[SWAP]'])]),
                        dict(children=[dict(path='/dev/testmapper', type='crypt', mountpoints=[])])]:
            with self.subTest(changes=changes):
                target = disk()
                target.update(changes)
                with self.assertRaises(ValueError):
                    installer.validate(target)
        installer.validate(disk())

    def test_dry_run_and_cancel_never_install(self):
        target = disk()
        target['path'] = '/dev/null'
        with patch.object(installer, 'inventory', return_value=[target]), \
             patch.object(installer.stat, 'S_ISBLK', return_value=True), \
             patch.object(installer.shutil, 'which', return_value='/mock/tool'), \
             patch.object(installer.os, 'geteuid', return_value=0), \
             patch.object(installer.sys.stdin, 'isatty', return_value=True), \
             patch('builtins.input', return_value='nein') as prompt, \
             patch.object(installer, 'install') as install:
            installer.main(['--device', '/dev/null', '--dry-run', '--source', str(installer.ROOT)])
            prompt.assert_not_called()
            with self.assertRaises(ValueError):
                installer.main(['--device', '/dev/null', '--source', str(installer.ROOT)])
            install.assert_not_called()

    def test_device_changed_before_write(self):
        original = disk()
        changed = disk()
        changed['serial'] = '456'
        with patch.object(installer, 'inventory', return_value=[changed]), patch.object(installer, 'run') as run:
            with self.assertRaises(ValueError):
                installer.install(original, [])
            run.assert_not_called()

    def test_install_commands_and_copies_without_real_disk(self):
        original = disk()
        partitioned = copy.deepcopy(original)
        partitioned['children'] = [dict(path='/dev/testusb1', type='part', mountpoints=[])]
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp) / 'mount'
            directory.mkdir()
            # Model mount/umount by moving the test mount contents aside.
            def fake_run(*args, **kwargs):
                if args[0] == 'umount':
                    directory.rename(Path(tmp) / 'written')
                    directory.mkdir()
            with patch.object(installer, 'inventory', side_effect=[[original], [partitioned]]), \
                 patch.object(installer.tempfile, 'mkdtemp', return_value=str(directory)), \
                 patch.object(installer, 'run', side_effect=fake_run) as run:
                files = installer.payload_files()
                installer.install(original, files)
            commands = [call.args[0] for call in run.call_args_list]
            self.assertEqual(commands, ['parted', 'partprobe', 'udevadm', 'mkfs.vfat', 'mount', 'sync', 'umount'])
            self.assertEqual((Path(tmp) / 'written/boot/fast.gz').read_bytes(),
                             (installer.ROOT / 'boot/fast.gz').read_bytes())
            self.assertFalse(directory.exists())

    def test_unmount_failure_preserves_files(self):
        original = disk()
        partitioned = copy.deepcopy(original)
        partitioned['children'] = [dict(path='/dev/testusb1', type='part', mountpoints=[])]
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp) / 'mount'
            directory.mkdir()
            def fake_run(*args, **kwargs):
                if args[0] == 'umount':
                    raise OSError('busy')
            with patch.object(installer, 'inventory', side_effect=[[original], [partitioned]]), \
                 patch.object(installer.tempfile, 'mkdtemp', return_value=str(directory)), \
                 patch.object(installer, 'run', side_effect=fake_run):
                with self.assertRaises(OSError):
                    installer.install(original, [installer.ROOT / 'grub.cfg'])
            self.assertTrue((directory / 'grub.cfg').is_file())


if __name__ == '__main__':
    unittest.main()
