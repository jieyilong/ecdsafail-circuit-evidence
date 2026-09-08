"""Small deterministic tests of the reporting code, independent of circuit outcomes."""
import tempfile
import unittest
from pathlib import Path

from analyze_results import paired, read_case, tsv, wilson, write_gzip_tsv


class StatisticsTests(unittest.TestCase):
    def test_wilson_zero_is_not_exact_zero_error(self):
        lo, hi = wilson(0, 100000)
        self.assertAlmostEqual(lo, 0)
        self.assertGreater(hi, 0)

    def test_paired_counts_and_direction(self):
        a = {i: {"any_failure": x} for i, x in enumerate([1, 1, 0, 0])}
        b = {i: {"any_failure": x} for i, x in enumerate([1, 0, 0, 0])}
        stats = paired(a, b, list(range(4)))
        self.assertEqual(stats["both_fail"], 1)
        self.assertEqual(stats["baseline_only_fail"], 1)
        self.assertEqual(stats["candidate_only_fail"], 0)
        self.assertEqual(stats["neither_fail"], 2)
        self.assertEqual(stats["candidate_minus_baseline_failure_rate"], -0.25)
        self.assertEqual(stats["exact_two_sided_sign_p"], 1)

    def test_symmetric_sign_test(self):
        a = {i: {"any_failure": int(i % 2 == 0)} for i in range(10)}
        b = {i: {"any_failure": int(i % 2 != 0)} for i in range(10)}
        self.assertEqual(paired(a, b, list(a))["exact_two_sided_sign_p"], 1)

    def test_reproducible_gzip_roundtrip(self):
        with tempfile.TemporaryDirectory() as name:
            first, second = Path(name) / "a.gz", Path(name) / "b.gz"
            rows = [{"index": "0", "value": "0x1234"}]
            for path in (first, second):
                write_gzip_tsv(path, ("index", "value"), rows)
            self.assertEqual(first.read_bytes(), second.read_bytes())
            self.assertEqual(tsv(first), rows)

    def test_incomplete_ledger_rejected(self):
        with tempfile.TemporaryDirectory() as name:
            path = Path(name)
            (path / "inputs.tsv").write_text("index\n0\n")
            with self.assertRaises(AssertionError):
                read_case(path)


if __name__ == "__main__":
    unittest.main()
