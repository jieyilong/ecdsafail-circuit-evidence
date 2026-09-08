import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from common import ROOT, FRESH, atomic_write, read_json, safe_path, verify_original, verify_sources, work_path
from reproduce import clean_env, emit, expected_rows, sample_size
from results import render, tsv


class EvidenceTests(unittest.TestCase):
    def test_original_bytes(self):
        self.assertEqual(verify_original(),235)

    def test_source_archives_and_trees(self):
        self.assertEqual(verify_sources(),4)

    def test_rejects_escaping_paths(self):
        with tempfile.TemporaryDirectory() as d:
            for path in ("../outside","/tmp/outside","x/../../outside","x\\outside"):
                with self.assertRaises(ValueError):
                    safe_path(d,path)

    def test_rejects_symlink_escape(self):
        with tempfile.TemporaryDirectory() as d, tempfile.TemporaryDirectory() as out:
            (Path(d)/"link").symlink_to(out,target_is_directory=True)
            with self.assertRaises(ValueError):
                safe_path(d,"link/file")

    def test_rejects_work_root_alias(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            (root/".work").symlink_to(root,target_is_directory=True)
            with self.assertRaises(ValueError):
                work_path(".work/provenance/freeze.json",root=root)

    def test_rejects_nested_output_alias(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            (root/".work").mkdir()
            (root/"data").mkdir()
            (root/".work/case").symlink_to(root/"data",target_is_directory=True)
            with self.assertRaises(ValueError):
                work_path(".work/case/eval.log",root=root)

    def test_atomic_write_preserves_hardlinked_original(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);(root/".work").mkdir()
            original=root/"original.json";original.write_text("original")
            dest=root/".work/result.json";os.link(original,dest)
            atomic_write(dest,"new",root=root)
            self.assertEqual(original.read_text(),"original")
            self.assertEqual(dest.read_text(),"new")

    def test_render_checks_probe_source(self):
        with patch("results.verify_sources",side_effect=AssertionError("edited probe")):
            with self.assertRaisesRegex(AssertionError,"edited probe"):
                render()

    def check_emission_alias(self, hardlink):
        (ROOT/".work").mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=ROOT/".work") as d:
            root=Path(d);original=root/"original.json";original.write_text("frozen")
            (root/"emitted").mkdir();ops=root/"emitted/ops.bin"
            temp=ops.with_name("ops.bin.tmp")
            if hardlink:
                os.link(original,temp)
            else:
                temp.symlink_to(original)
            with patch("reproduce.binary",return_value=root/"builder"),patch("reproduce.configuration",return_value={"settings":{},"ops_sha256":"unused"}),patch("reproduce.ops_path",return_value=ops),patch("reproduce.run_logged") as launch:
                with self.assertRaises(ValueError):
                    emit("conservative-pingpong")
                launch.assert_not_called()
            self.assertEqual(original.read_text(),"frozen")

    def test_emitter_temporary_symlink_is_rejected(self):
        self.check_emission_alias(False)

    def test_emitter_temporary_hardlink_is_rejected(self):
        self.check_emission_alias(True)

    def test_rendered_results_are_current(self):
        for path,content in render().items():
            self.assertEqual(path.read_text(),content,str(path))

    def test_smoke_size_is_explicit(self):
        self.assertEqual(sample_size(None,11111),11111)
        self.assertEqual(sample_size(128,11111),128)
        for n in (0,-1,1,64,129,11136):
            with self.assertRaises(ValueError):
                sample_size(n,11111)

    def test_environment_drops_arithmetic_overrides(self):
        with patch.dict(os.environ,{"QIP_PINGPONG_PROFILE":"wrong","TLM_MSBS":"1","RUSTFLAGS":"wrong","EVAL_ONLY_BATCH":"2"}):
            env=clean_env()
        self.assertFalse(set(env)&{"QIP_PINGPONG_PROFILE","TLM_MSBS","RUSTFLAGS","EVAL_ONLY_BATCH"})
        self.assertEqual(env["LC_ALL"],"C")

    def test_expected_rows_expand_equality_markers(self):
        rows=expected_rows("conservative-pingpong","G-s0",128)
        self.assertEqual(set(rows),set(range(128)))
        for row in rows.values():
            self.assertEqual(row["got_x"],row["expected_x"])
            self.assertEqual(row["got_y"],row["expected_y"])
            self.assertEqual(int(row["got_address"],16),int(row["address"]))

    def test_failure_index_is_complete(self):
        import csv
        with (FRESH/"failures.csv").open() as f:
            rows=list(csv.DictReader(f))
        self.assertEqual(len(rows),254)
        self.assertEqual(sum(r["candidate"]=="original-pingpong" for r in rows),39)
        self.assertEqual(sum(r["candidate"]=="jump2" for r in rows),215)
        self.assertFalse(any(r["candidate"]=="conservative-pingpong" for r in rows))


if __name__=="__main__":
    unittest.main()
