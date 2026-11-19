"""Verify FPGA output isolation and migration/report preservation, without a board."""
import contextlib
import datetime
import hashlib
import io
import json
from pathlib import Path
import shlex
import sys
import unittest
from unittest.mock import patch
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from fpga import run
from fpga import workspace as paths


class WorkspaceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        cls.base = paths.workspace() / "tests" / ("workspace_checks_" + stamp)
        cls.base.mkdir(parents=True)

    def directory(self, name=None):
        directory = self.base / (name or self._testMethodName)
        directory.mkdir()
        return directory

    def test_rejects_repository_outputs_after_resolving(self):
        for path in (ROOT, ROOT / "fpga/local_output", ROOT / ".." / ROOT.name / "fpga/local_output"):
            # The last input reaches the same checkout through '..'.
            with self.subTest(path=path), self.assertRaisesRegex(ValueError, "outside the repository"):
                paths.external(path)
        with patch.dict("os.environ", {"FPGA_WORKSPACE": str(ROOT / "local_fpga")}):
            with self.assertRaises(ValueError):
                paths.workspace()

    def test_explicit_and_environment_workspaces(self):
        first = self.base / "first"
        second = self.base / "second"
        with patch.dict("os.environ", {"FPGA_WORKSPACE": str(first)}):
            self.assertEqual(paths.workspace(), first)
            self.assertEqual(paths.workspace(second), second)
            self.assertEqual(paths.firmware_dir(work=second), second / "firmware")

    def test_process_cwd_and_logs_stay_external(self):
        directory = self.directory()
        with contextlib.redirect_stdout(io.StringIO()):
            run.launch([sys.executable, "-c", "from pathlib import Path; Path('generated.log').write_text('outside'); print('ok')"],
                       directory, directory / "command.log")
        self.assertEqual((directory / "generated.log").read_text(), "outside")
        self.assertIn("ok", (directory / "command.log").read_text())
        with self.assertRaises(ValueError):
            run.launch([sys.executable, "-c", "raise RuntimeError('must not run')"],
                       directory, ROOT / "fpga/forbidden.log")

    def test_failed_command_retains_external_log(self):
        directory = self.directory()
        with contextlib.redirect_stdout(io.StringIO()), self.assertRaisesRegex(RuntimeError, "exit evidence"):
            run.launch([sys.executable, "-c", "print('exit evidence'); raise SystemExit(7)"],
                       directory, directory / "failed.log")
        self.assertIn("exit evidence", (directory / "failed.log").read_text())

    def test_initialize_preserves_local_openocd_configuration(self):
        directory = self.directory()
        run.initialize(directory)
        config = directory / "config/cv32e40p.cfg"
        self.assertEqual(config.read_bytes(), (ROOT / "fpga/config/cv32e40p.cfg").read_bytes())
        config.write_bytes(b"# locally customized adapter\nadapter speed 20\n")
        run.initialize(directory)
        self.assertEqual(config.read_bytes(), b"# locally customized adapter\nadapter speed 20\n")

    def test_gdb_launcher_quotes_external_paths_without_gdb_python(self):
        directory = self.directory("work with spaces and ' quote")
        gdb = paths.write_gdb_launchers(directory)
        self.assertEqual((gdb / "load_soc_image.gdb").read_bytes(), (ROOT / "fpga/load_soc_image.gdb").read_bytes())
        lines = (gdb / "test_all_firmware.gdb").read_text().splitlines()
        command = next(line[6:] for line in lines if line.startswith("shell "))
        words = shlex.split(command)
        self.assertEqual(words, ["python3", paths.wsl_path(ROOT / "fpga/firmware_batch.py"),
                                 "--run", "--workspace", paths.wsl_path(directory)])
        self.assertLess(lines.index("disconnect"), lines.index("shell " + command))
        self.assertIn("target extended-remote :3333", lines)
        self.assertNotIn("python", [line.strip() for line in lines])

    def test_moved_xpr_references_current_sources_and_preserves_bitstream(self):
        directory = self.directory()
        project = directory / "final_project"
        project.mkdir()
        old_repo = self.base / "old_checkout"
        old_project = old_repo / "fpga/final_project"
        tree = ET.Element("Project", Path=(old_project / "final_project.xpr").as_posix())
        for name in ("$PPRDIR/../../rtl/soc/bootram.sv", "$PPRDIR/../fpga_top.sv", "$PPRDIR/../fpga_top.xdc",
                     (old_repo / "fpga/firmware/int8_selftest.hex").as_posix()):
            ET.SubElement(tree, "File", Path=name)
        path = project / "final_project.xpr"
        ET.ElementTree(tree).write(path, encoding="utf-8")
        bit = project / "fpga_top.bit"
        bit.write_bytes(b"preserved binary fixture\x00\xff")
        before = bit.read_bytes()
        run.relocate_project(directory, old_repo)
        result = ET.parse(path).getroot()
        self.assertEqual(result.get("Path"), (project / "final_project.xpr").as_posix())
        names = [entry.get("Path") for entry in result.findall("File")]
        self.assertEqual(names, [(ROOT / "rtl/soc/bootram.sv").as_posix(),
                                 (ROOT / "fpga/src/fpga_top.sv").as_posix(),
                                 (ROOT / "fpga/src/fpga_top.xdc").as_posix(),
                                 (directory / "firmware/int8_selftest.hex").as_posix()])
        self.assertEqual(bit.read_bytes(), before)

    def test_collect_preserves_evidence_scope_and_excludes_artifacts(self):
        directory = self.directory()
        evidence = directory / "fixture_run"
        evidence.mkdir()
        payload = dict(status="PASS", environment="Offline fixture; not FPGA execution")
        (evidence / "result.json").write_text(json.dumps(payload))
        (evidence / "summary.md").write_text("Offline fixture; not FPGA execution\n")
        (evidence / "fpga_top.bit").write_bytes(b"not a report")
        (evidence / "commands.log").write_text("raw log stays outside")
        checkout = directory / "checkout"
        with patch.object(run, "ROOT", checkout), contextlib.redirect_stdout(io.StringIO()):
            run.collect(directory, evidence, "fixture_report")
            with self.assertRaises(FileExistsError):
                run.collect(directory, evidence, "fixture_report")
        copied = checkout / "fpga/results/fixture_report"
        self.assertEqual({p.name for p in copied.iterdir()}, {"result.json", "summary.md", "receipt.json"})
        self.assertEqual((copied / "result.json").read_bytes(), (evidence / "result.json").read_bytes())
        receipt = json.loads((copied / "receipt.json").read_text())
        self.assertEqual(receipt["environment"], payload["environment"])
        self.assertEqual(receipt["files_sha256"]["summary.md"], hashlib.sha256((evidence / "summary.md").read_bytes()).hexdigest())

    def test_collect_rejects_path_traversal_before_creating_report(self):
        directory = self.directory()
        for name in ("..", "../escape", "a/b", "a\\b", "."):
            with self.subTest(name=name), self.assertRaises(ValueError):
                run.collect(directory, directory, name)


if __name__ == "__main__":
    unittest.main(verbosity=2)
