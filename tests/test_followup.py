import json
from pathlib import Path
import subprocess
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from verify_followup import verify_followup

class FollowupPublication(unittest.TestCase):
    def test_preserved_science_and_followup(self):
        result=verify_followup()
        self.assertEqual(result['status'],'PASS')
        self.assertEqual(result['preserved_original_files'],148)
        self.assertEqual(result['tail_trials_recorded'],10000000)
        self.assertEqual(result['guard_cases_recorded'],99997)

    def test_reproduction_rejects_publication_directory(self):
        command=[sys.executable,str(ROOT/'experiments/08-followup-diagnostics/reproduce.py'),'prepare','--work-dir',str(ROOT/'experiments/08-followup-diagnostics')]
        result=subprocess.run(command,capture_output=True,text=True)
        self.assertNotEqual(result.returncode,0)
        self.assertIn('new subdirectory',result.stderr)

    def test_correctness_reference_not_in_release(self):
        new=ROOT/'experiments/08-followup-diagnostics/source/src/point_add'
        self.assertFalse((new/'canonical_replay.rs').exists())
        self.assertNotIn('QIP_CANONICAL_REPLAY',(new/'pingpong_div.rs').read_text())

if __name__=='__main__':unittest.main()
