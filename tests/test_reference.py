import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import unittest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from verify_reference import verify_reference

class CanonicalReferencePublication(unittest.TestCase):
    def test_reference_records_and_prior_science(self):
        r=verify_reference()
        self.assertEqual(r['status'],'PASS')
        self.assertEqual(r['pilot_rows'],4096)
        self.assertEqual(r['static_toffoli'],5188043)
        self.assertEqual(r['noncanonical_cell_cases_retained'],124)
        self.assertEqual(r['replay_only_failure_counts'],[30,38])
        self.assertFalse(r['fresh_circuit_execution'])

    def test_reproduction_cannot_write_public_records(self):
        folder=ROOT/'experiments/09-canonical-reference'
        run=subprocess.run([sys.executable,str(folder/'reproduce.py'),'prepare','--work-dir',str(folder)],capture_output=True,text=True)
        self.assertNotEqual(run.returncode,0)
        self.assertIn('.work',run.stderr)

    def test_original_low_cost_results_unchanged(self):
        fresh=json.loads((ROOT/'experiments/02-fresh-windowed/analysis.json').read_text())
        self.assertEqual(fresh['circuits']['pingpong_conservative']['any_failure'],0)
        self.assertFalse((ROOT/'experiments/08-followup-diagnostics/source/src/point_add/canonical_replay.rs').exists())
        self.assertTrue((ROOT/'experiments/09-canonical-reference/source/src/point_add/canonical_replay.rs').exists())

if __name__=='__main__':unittest.main()
