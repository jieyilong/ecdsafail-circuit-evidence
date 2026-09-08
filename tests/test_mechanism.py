import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from common import ROOT, read_json
from verify_mechanism import verify_mechanism, verify_preserved_v1_science


class MechanismTests(unittest.TestCase):
    def test_previous_science_is_unchanged(self):
        self.assertGreater(verify_preserved_v1_science(), 500)

    def test_portable_record_verifiers(self):
        report = verify_mechanism()
        self.assertEqual(report["status"], "PASS")
        self.assertEqual(report["algebra_cases"], 1008)
        self.assertEqual(report["accounting_math_checks"], 247)
        self.assertEqual(report["experiments"]["06-resource-accounting"]["matching_stream_receipt_pairs"], 12)
        self.assertFalse(report["experiments"]["07-boundary-diagnosis"]["checks"]["local_regression"]["integrated_into_replay"])

    def test_failed_verifier_status_is_rejected(self):
        with patch("verify_mechanism.run_json", return_value={"status": "FAIL"}):
            with self.assertRaisesRegex(RuntimeError, "did not pass"):
                verify_mechanism()

    def test_ablation_failures_are_retained(self):
        data = read_json(ROOT / "experiments/06-resource-accounting/receipts/integration-summary.json")
        self.assertEqual(data["ablation_controls"]["legacy"]["static_toffoli_reduction"], 340442)
        for name in data["ablation"]:
            row = data["smoke"][name]
            self.assertEqual(row["identity_rows"], 5)
            self.assertEqual(row["failures"]["any_failure"], 6 if "pingpong" in name else 5)


if __name__ == "__main__":
    unittest.main()
