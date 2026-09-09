import csv
import json
import math
from pathlib import Path
import tempfile
import unittest

from analyze import cp_upper,read_case,paired


class LedgerTests(unittest.TestCase):
    def fixture(self, root):
        c=Path(root)/"checkpoint"
        c.mkdir()
        (c/"manifest.tsv").write_text("target_shots\t2\nqubits\t10\nseed\ttest\nqip_table_beta\t0x1\n")
        rows=[]
        for i in range(2):
            rows.append(dict(index=str(i),batch="0",address=str(i+1),target_x="0x1",target_y="0x2",
                addend_x="0x3",addend_y="0x4",expected_x="0x5",expected_y="0x6",got_x="0x5",got_y="0x6",
                got_address=hex(i+1),classical_failure="0",phase_failure="0",ancilla_failure="0",any_failure="0"))
        batch=dict(batch="0",shots="2",toffoli="20",clifford="100",classical_failures="0",phase_failure_shots="0",ancilla_failure_shots="0",any_failure_shots="0")
        self.write(c/"inputs.tsv",rows)
        self.write(c/"batches.tsv",[batch])
        return c,rows,batch

    def write(self,path,rows):
        with path.open("w",newline="") as f:
            w=csv.DictWriter(f,fieldnames=list(rows[0]),delimiter="\t")
            w.writeheader();w.writerows(rows)

    def test_valid_partial_batch(self):
        with tempfile.TemporaryDirectory() as root:
            self.fixture(root)
            _,_,s=read_case(root)
            self.assertEqual(s["QT"],"100")

    def test_rejects_wrong_index_domain(self):
        with tempfile.TemporaryDirectory() as root:
            c,r,b=self.fixture(root);r[0]["index"]="9";self.write(c/"inputs.tsv",r)
            with self.assertRaises(AssertionError):read_case(root)

    def test_rejects_batch_marginal_mismatch(self):
        with tempfile.TemporaryDirectory() as root:
            c,r,b=self.fixture(root);b["classical_failures"]="1";self.write(c/"batches.tsv",[b])
            with self.assertRaises(AssertionError):read_case(root)

    def test_rejects_unflagged_wrong_output(self):
        with tempfile.TemporaryDirectory() as root:
            c,r,b=self.fixture(root);r[0]["got_x"]="0x9";self.write(c/"inputs.tsv",r)
            with self.assertRaises(AssertionError):read_case(root)

    def test_zero_failure_bound(self):
        self.assertAlmostEqual(cp_upper(0,100000),-math.expm1(math.log(0.05)/100000))
        self.assertLess(cp_upper(1,100000),cp_upper(2,100000))

    def test_paired_direction(self):
        a={0:{"any_failure":"1"},1:{"any_failure":"0"}}
        b={0:{"any_failure":"0"},1:{"any_failure":"0"}}
        self.assertEqual(paired(a,b)["baseline_only"],1)


if __name__=="__main__":unittest.main()
