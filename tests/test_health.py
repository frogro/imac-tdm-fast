import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]


class HealthTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp=tempfile.TemporaryDirectory()
        cls.binary=Path(cls.tmp.name)/'health'
        subprocess.run(['gcc','-Wall','-Wextra','-Werror','-O2','-o',str(cls.binary),str(ROOT/'src/health.c')],check=True)

    @classmethod
    def tearDownClass(cls): cls.tmp.cleanup()

    def fixture(self, root, name, value):
        path=root/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_text(value+'\n');return path

    def test_cpu_powersave_and_read_only_fan_telemetry(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            base='sys/devices/system/cpu/cpufreq/policy0/'
            self.fixture(root,base+'scaling_driver','acpi-cpufreq')
            self.fixture(root,base+'scaling_available_governors','performance powersave schedutil')
            governor=self.fixture(root,base+'scaling_governor','performance')
            self.fixture(root,base+'scaling_cur_freq','800000')
            hw='sys/class/hwmon/hwmon0/'
            self.fixture(root,hw+'name','applesmc')
            values={hw+'device/fan1_manual':'0',hw+'device/fan1_min':'1000',hw+'device/fan1_input':'1250',hw+'device/temp1_input':'57000',hw+'device/temp1_label':'TC0P'}
            saved={name:self.fixture(root,name,value).read_bytes() for name,value in values.items()}
            result=subprocess.run([str(self.binary),'--fixture',tmp],check=True,text=True,capture_output=True)
            self.assertEqual(governor.read_text(),'powersave\n')
            for name,contents in saved.items(): self.assertEqual((root/name).read_bytes(),contents)
            self.assertIn('fan1_input=1250',result.stdout)
            self.assertIn('temp1_input=57000',result.stdout)
            self.assertIn('scaling_cur_freq=800000',result.stdout)

    def test_unknown_driver_and_missing_governor_remain_unchanged(self):
        for driver,available in [('unknown','powersave performance'),('acpi-cpufreq','performance notpowersave')]:
            with self.subTest(driver=driver), tempfile.TemporaryDirectory() as tmp:
                root=Path(tmp);base='sys/devices/system/cpu/cpufreq/policy0/'
                self.fixture(root,base+'scaling_driver',driver)
                self.fixture(root,base+'scaling_available_governors',available)
                governor=self.fixture(root,base+'scaling_governor','performance')
                subprocess.run([str(self.binary),'--fixture',tmp],check=True,stdout=subprocess.DEVNULL)
                self.assertEqual(governor.read_text(),'performance\n')

    def test_missing_sensors_are_explicit_not_cooling_success(self):
        with tempfile.TemporaryDirectory() as tmp:
            text=subprocess.check_output([str(self.binary),'--fixture',tmp],text=True)
            self.assertIn('cooling is NOT verified',text)
            self.assertIn('CPU frequency scaling unavailable',text)

    def test_pinned_modules_match_kernel_and_exclude_gpu(self):
        manifest=json.loads((ROOT/'vendor/modules/manifest.json').read_text())
        self.assertEqual(manifest['kernel'],json.loads((ROOT/'sources.json').read_text())['kernel_version'])
        self.assertEqual({i['file'] for i in manifest['files']},
            {'applesmc.ko','coretemp.ko','acpi-cpufreq.ko','cpufreq_powersave.ko'} |
            {n+'.ko' for n in 'soundcore snd snd-timer snd-pcm snd-hwdep snd-hda-core snd-hda-codec snd-hda-codec-generic snd-hda-codec-cirrus snd-hda-codec-realtek snd-intel-dspcfg snd-hda-intel'.split()})
        for item in manifest['files']:
            data=(ROOT/'vendor/modules'/item['file']).read_bytes()
            self.assertEqual(hashlib.sha256(data).hexdigest(),item['sha256'])
            self.assertIn(b'vermagic=6.6.8-tinycore64 ',data)


if __name__ == '__main__': unittest.main()
