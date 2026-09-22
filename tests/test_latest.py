import copy
import importlib.util
from pathlib import Path
import sys
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from common import ROOT,read_json,sha
from verify_latest import EXPERIMENT,rows,verify_ledger

class LatestTests(unittest.TestCase):
    def fixture(self):
        path=EXPERIMENT/'fresh-study/stratum-0/checkpoint'
        data=sorted(rows(path/'inputs.tsv.gz'),key=lambda r:int(r['index']))[:64]
        batch=[r for r in rows(path/'batches.tsv') if r['batch']=='0']
        return data,batch

    def test_batch_reconciliation(self):
        data,batches=self.fixture()
        self.assertEqual(verify_ledger(data,batches,64,1,oracle=False)['n'],64)

    def test_missing_duplicate_and_wrong_flags_rejected(self):
        data,batches=self.fixture()
        for mutation in ['missing','duplicate','flags','address','batch_total']:
            ds,bs=copy.deepcopy(data),copy.deepcopy(batches)
            if mutation=='missing':ds.pop()
            if mutation=='duplicate':ds[-1]=copy.deepcopy(ds[0])
            if mutation=='flags':ds[0]['any_failure']='1'
            if mutation=='address':ds[0]['got_address']='0xffffffffffff'
            if mutation=='batch_total':bs[0]['shots']='63'
            with self.assertRaises(AssertionError,msg=mutation):verify_ledger(ds,bs,64,1,oracle=False)

    def test_frozen_source_matches(self):
        for name,digest in read_json(EXPERIMENT/'fresh-study/freeze.json')['source'].items():
            self.assertEqual(sha(EXPERIMENT/'source'/name),digest,name)

    def test_negative_results_retained(self):
        ds=rows(EXPERIMENT/'diagnostics/schedule-points-w4.tsv')
        self.assertEqual(sum(int(r['classical']) for r in ds),48)
        self.assertEqual(sum(int(r['phase']) for r in ds),25)
        result=read_json(ROOT/'experiments/13-safegcd-reference/pingpong-768-results.json')
        self.assertTrue(all(r['any_failures']==12 for r in result['reports']))

    def test_schedule_counterexamples(self):
        spec=importlib.util.spec_from_file_location('schedule_model',ROOT/'experiments/12-schedule-audit/model.py')
        model=importlib.util.module_from_spec(spec);spec.loader.exec_module(model)
        self.assertEqual(model.walk(3,4096)['first_terminal_round'],1135)
        self.assertEqual(model.walk(2**255,4096)['first_terminal_round'],1239)
        self.assertEqual(model.walk(1,4096)['misses']['candidate768']['k'],177)

if __name__=='__main__':unittest.main()
