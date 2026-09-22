"""Fast regressions. Run audit.py first to generate source-linked receipts."""
import csv
import hashlib
import io
import json
from pathlib import Path
import sys
import unittest

sys.dont_write_bytecode = True
from model import P, fits, initial, magnitude_walk, ordinary, small_pair_check, walk, width

ROOT = Path(__file__).resolve().parent


class AuditTests(unittest.TestCase):
    def test_signed_fit_endpoints(self):
        for w in (8, 11, 257, 258, 259):
            edge = 1 << (w - 1)
            self.assertTrue(fits(-edge, w))
            self.assertTrue(fits(edge - 1, w))
            self.assertFalse(fits(-edge - 1, w))
            self.assertFalse(fits(edge, w))

    def test_low_bits_negative_integers(self):
        for s in range(-63, 64, 2):
            for t in range(-63, 64, 2):
                new, total, sign = ordinary(s, t)
                self.assertEqual(sign, ((s >> 1) ^ (t >> 1)) & 1)
                self.assertEqual(total % 4, 2)
                self.assertEqual(new % 2, 1)

    def test_initial_four_arms(self):
        for d in list(range(1, 33)) + list(range(P - 32, P)):
            v = initial(d)
            self.assertEqual((2 * v - d) % P, 0)
            self.assertLess(abs(v), P)
            self.assertEqual(v % 2, 1)

    def test_domain_rejections(self):
        for d in (0, -1, P, P + 1):
            with self.assertRaises(ValueError):
                initial(d)

    def test_absorbing_signed_units(self):
        for u in (-1, 1):
            for v in (-1, 1):
                self.assertEqual(ordinary(u, v)[0], v)

    def test_width_breakpoints(self):
        self.assertEqual([width(k) for k in (0, 40, 304, 703, 735, 736, 742, 767)],
                         [259, 259, 183, 24, 11, 11, 8, 8])
        self.assertTrue(all(width(k) <= width(k - 1) for k in range(1, 768)))

    def test_explicit_schedule(self):
        with (ROOT / "width_schedule.csv").open() as f:
            rows = list(csv.DictReader(f))
        self.assertEqual(len(rows), 768)
        for k, row in enumerate(rows):
            self.assertEqual(int(row["k_zero_based"]), k)
            self.assertEqual(int(row["proposed_taper768"]), width(k))
            self.assertEqual(int(row["proposed_full259_768"]), 259)

    def test_768_counterexamples(self):
        for d, rounds in ((3, 1135), (2**255, 1239)):
            self.assertIsNone(walk(d, 768)["first_terminal_round"])
            self.assertEqual(walk(d, 4096)["first_terminal_round"], rounds)
            self.assertEqual(magnitude_walk(d), rounds)

    def test_termination_does_not_imply_taper(self):
        result = walk(1, 768)
        self.assertEqual(result["first_terminal_round"], 512)
        miss = result["misses"]["candidate768"]
        self.assertEqual((miss["k"], miss["kind"], miss["width"]), (177, "sum_width", 225))
        self.assertFalse(fits(int(miss["pre_halving_sum"]), 225))
        self.assertTrue(fits(int(miss["pre_halving_sum"]), 258))

    def test_small_signed_pairs(self):
        self.assertEqual(small_pair_check(), {"signed_coprime_pairs": 3300,
                                            "max_abs_input": 63, "max_rounds": 17})

    def test_fresh_native_and_structured_receipts(self):
        fresh = json.loads((ROOT / "independent_sample.json").read_text())
        self.assertTrue(fresh["gmp_crosscheck_all_10000"])
        self.assertEqual(sum(fresh["histogram"].values()), 10000)
        self.assertEqual(fresh["tail_counts"], {"704": 2, "736": 0, "768": 0, "800": 0})
        self.assertEqual(hashlib.sha256((ROOT / "independent.bin").read_bytes()).hexdigest(),
                         fresh["denominators_sha256"])
        structured = json.loads((ROOT / "structured_witnesses.json").read_text())
        self.assertTrue(structured["all_models_agree"])
        self.assertEqual(structured["native_capped4096"]["censored_at_4097"], 0)

    def test_frozen_scope(self):
        frozen = json.loads((ROOT / "frozen_audit.json").read_text())
        self.assertEqual(frozen["n"], 10000000)
        self.assertIsNone(frozen["width_misses_768_margin20"])
        self.assertFalse(frozen["old_data_hash_recomputed"])


if __name__ == "__main__":
    output = io.StringIO()
    result = unittest.TextTestRunner(stream=output, verbosity=2).run(
        unittest.defaultTestLoader.loadTestsFromTestCase(AuditTests))
    (ROOT / "test-results.txt").write_text(output.getvalue())
    print(output.getvalue(), end="")
    sys.exit(not result.wasSuccessful())
