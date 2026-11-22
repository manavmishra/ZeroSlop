"""Offline checks for blinding and contamination boundaries."""
import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import unittest

spec=importlib.util.spec_from_file_location('blind_runner',Path(__file__).with_name('run.py'))
runner=importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)

class HarnessChecks(unittest.TestCase):
    def test_pinned_archive_omits_project_rules_and_uncommitted_text(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary)/'source'; root.mkdir()
            subprocess.run(['git','init','-q',str(root)],check=True)
            (root/'SKILL.md').write_text('committed instructions')
            (root/'AGENTS.md').write_text('private contaminated rules')
            subprocess.run(['git','-C',str(root),'add','.'],check=True)
            subprocess.run(['git','-C',str(root),'-c','user.name=Test','-c','user.email=test@example.invalid','commit','-qm','fixture'],check=True)
            (root/'SKILL.md').write_text('uncommitted candidate')
            dest=Path(temporary)/'runtime'
            receipt=runner.stage(root,'HEAD',dest,['SKILL.md','AGENTS.md'])
            self.assertEqual((dest/'SKILL.md').read_text(),'committed instructions')
            self.assertFalse((dest/'AGENTS.md').exists())
            self.assertEqual(set(receipt['files']),{'SKILL.md'})

    def test_packets_separate_methods_from_source_only_review(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary)
            for method in ('secret-method-one','secret-method-two'):
                runner.write(root/'outputs'/f'{method}.json',{'rewrites':[{'id':'dev-secret','text':'Final text.','findings':[{'span':'Original','action':'edit','reason':method}]}]})
            runner.packets(root,[{'id':'dev-secret','genre':'email','text':'Original text.','source':{'facts':'known'}}])
            packet=(root/'judge-packets'/'anonymous.json').read_text()
            self.assertNotIn('secret-method',packet)
            self.assertNotIn('dev-secret',packet)
            self.assertNotIn('findings',packet)
            self.assertEqual(len(json.loads(packet)[0]['candidates']),2)
            self.assertTrue((root/'private-maps'/'mapping.json').exists())

if __name__=='__main__': unittest.main()
