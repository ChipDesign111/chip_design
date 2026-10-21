"""Small real-tar regressions for the explicitly pinned historical init source.

No EDA or private course artifacts are needed. Only the synthetic fixture's
archive digest and main-source pin are substituted; production archive reading,
member hashing, source selection and checkpoint/context validation run intact.
"""
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import tarfile
import tempfile
import unittest
from unittest import mock


spec = importlib.util.spec_from_file_location("legacy_init_timing_audit", Path(__file__).with_name("audit_timing.py"))
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)


class LegacyInitProvenanceTests(unittest.TestCase):
    def setUp(self):
        # Catch accidental expansion or replacement of the production exception.
        self.assertEqual(audit.LEGACY_INIT_SOURCE["invocation"], "20261021T055907515732Z-init")
        self.assertEqual(audit.LEGACY_INIT_SOURCE["archive_sha256"], "a96e02af90582a8403d54fc12a1419e64896dc36b56e9783244336c558c5d82c")
        self.assertEqual(audit.LEGACY_INIT_SOURCE["main_sha256"], "d2a319d67d3ef2d376a5dbd002c19db083723938d4d496c6c7a773b07ef7c491")
        self.workspace = Path(__file__).resolve().parents[1]/"work/legacy-init-audit-selftest"
        self.workspace.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=self.workspace)
        self.root = Path(self.temp.name)
        self.invocation = self.root/"invocations"/audit.LEGACY_INIT_SOURCE["invocation"]
        self.invocation.mkdir(parents=True)
        self.main = ("set checkpoint [file join $output_root backup ${stage}-${invocation_id}.enc]\n"
                     "saveDesign $checkpoint\n"
                     "save_physical_tcl_context ${checkpoint}.context.tcl\n"
                     'puts "PNR_STAGE_COMPLETE $stage"\n').encode()
        names = ("main", "config", "init", "floorplan", "io", "power", "place", "cts", "route", "finish",
                 "export", "settings", "mmmc", "geometry_helpers")
        self.members = {"eda/pnr/"+name+".tcl": self.main if name == "main" else ("# fixture "+name+"\n").encode()
                        for name in names}
        self.main_digest = hashlib.sha256(self.main).hexdigest()
        self.record = {"stages": ["init"], "completed_stages": ["init"], "resume": None,
                       "status": "COMPLETED", "exit_code": 0, "errors": [],
                       "scripts_sha256": {name: hashlib.sha256(data).hexdigest() for name, data in self.members.items()}}
        self.manifest = self.invocation/"manifest.json"
        self.manifest.write_text(json.dumps(self.record))
        self.archive = self.invocation/audit.LEGACY_INIT_SOURCE["archive"]
        with tarfile.open(self.archive, "w") as handle:
            for name, data in self.members.items():
                info = tarfile.TarInfo(name)
                info.size = len(data)
                handle.addfile(info, io.BytesIO(data))
        self.archive_bytes = self.archive.read_bytes()
        real_sha = audit.sha
        fixture_archive_digest = real_sha(self.archive)
        production_archive_pin = audit.LEGACY_INIT_SOURCE["archive_sha256"]

        def controlled_sha(path):
            actual = real_sha(path)
            # Changed fixture bytes do not receive the pinned identity.
            if Path(path).resolve() == self.archive.resolve() and actual == fixture_archive_digest:
                return production_archive_pin
            return actual

        pin_patch = mock.patch.dict(audit.LEGACY_INIT_SOURCE, {"main_sha256": self.main_digest})
        pin_patch.start()
        self.addCleanup(pin_patch.stop)
        sha_patch = mock.patch.object(audit, "sha", side_effect=controlled_sha)
        sha_patch.start()
        self.addCleanup(sha_patch.stop)
        stamp = audit.LEGACY_INIT_SOURCE["invocation"][:-len("-init")]
        self.node = {"stage": "init", "path": self.manifest, "record": self.record,
                     "checkpoint": "init-"+stamp+".enc.dat"}
        self.evidence = audit.Evidence(self.root)
        self.make_database(self.node)

    def tearDown(self):
        assert self.workspace.resolve() in self.root.resolve().parents
        self.temp.cleanup()

    def make_database(self, node):
        database = self.root/"backup"/node["checkpoint"]
        database.mkdir(parents=True)
        (database/"design.bin").write_bytes(b"synthetic nonempty checkpoint\n")

    def test_pinned_init_reads_all_fourteen_members_without_fabricating_source(self):
        main, provenance = audit.checkpoint_main_source(self.evidence, self.node)
        self.assertEqual(main.encode(), self.main)
        self.assertEqual(provenance["kind"], "explicit_pinned_legacy_init_source_tar")
        self.assertEqual(provenance["manifest_listed_sources_verified"], 14)
        self.assertEqual(set(provenance["manifest_member_sha256"]), set(self.members))
        self.assertEqual(self.evidence.hashes[str(self.archive.resolve())], audit.LEGACY_INIT_SOURCE["archive_sha256"])
        bound = audit.bind_saved_checkpoint(self.evidence, self.node, {})
        self.assertIsNone(bound["context"])  # Only this init restore needs no helper context.
        self.assertEqual(bound["database_file_count"], 1)
        self.assertFalse((self.invocation/"source").exists())
        self.assertEqual(self.archive.read_bytes(), self.archive_bytes)

    def test_missing_or_byte_changed_archive_never_receives_approval(self):
        self.archive.unlink()
        with self.assertRaisesRegex(audit.Incomplete, "Missing previously preserved"):
            audit.checkpoint_main_source(self.evidence, self.node)
        self.archive.write_bytes(self.archive_bytes+b"changed bytes\n")
        with self.assertRaisesRegex(audit.Violation, "archive SHA mismatch"):
            audit.checkpoint_main_source(self.evidence, self.node)

    def test_changed_manifest_or_present_source_cannot_fall_back_to_archive(self):
        scripts = self.record["scripts_sha256"]
        for member, reason in (("eda/pnr/main.tcl", "manifest main.tcl identity differs"),
                               ("eda/pnr/floorplan.tcl", "every original manifest-listed")):
            with self.subTest(member=member):
                original = scripts[member]
                scripts[member] = "0"*64
                try:
                    with self.assertRaisesRegex(audit.Violation, reason):
                        audit.checkpoint_main_source(self.evidence, self.node)
                finally:
                    scripts[member] = original
        source = self.invocation/"source/main.tcl"
        source.parent.mkdir()
        source.write_bytes(b"changed frozen source; archive is still intact\n")
        with self.assertRaisesRegex(audit.Violation, "snapshot SHA mismatch"):
            audit.checkpoint_main_source(self.evidence, self.node)

    def test_other_invocations_noninit_and_resumed_or_failed_init_are_rejected(self):
        for change in ({"stage": "floorplan"}, {"path": self.root/"invocations/20261021T060000000000Z-init/manifest.json"}):
            with self.subTest(change=change), self.assertRaisesRegex(audit.Incomplete, "no approved legacy source"):
                audit.checkpoint_main_source(self.evidence, dict(self.node, **change))
        for change in ({"stages": ["init", "floorplan"]}, {"completed_stages": ["init", "floorplan"]},
                       {"resume": "backup/older.enc.dat"}, {"status": "FAIL"}, {"exit_code": 1}, {"errors": ["failure"]}):
            record = dict(self.record, **change)
            with self.subTest(change=change), self.assertRaisesRegex(audit.Violation, "successful standalone initial init"):
                audit.checkpoint_main_source(self.evidence, dict(self.node, record=record))

    def test_noninit_checkpoint_still_requires_real_nonempty_saved_context(self):
        folder = self.root/"invocations/20261021T060000000000Z-floorplan"
        (folder/"source").mkdir(parents=True)
        (folder/"source/main.tcl").write_bytes(self.main)
        record = dict(self.record, stages=["floorplan"], completed_stages=["floorplan"],
                      resume=str(self.root/"backup"/self.node["checkpoint"]))
        (folder/"manifest.json").write_text(json.dumps(record))
        node = {"stage": "floorplan", "path": folder/"manifest.json", "record": record,
                "checkpoint": "floorplan-20261021T060000000000Z.enc.dat"}
        self.make_database(node)
        with self.assertRaisesRegex(audit.Incomplete, "Missing saved non-init checkpoint context"):
            audit.bind_saved_checkpoint(self.evidence, node, {})
        context = self.root/"backup"/(node["checkpoint"][:-4]+".context.tcl")
        context.write_text("")
        with self.assertRaisesRegex(audit.Incomplete, "Empty report"):
            audit.bind_saved_checkpoint(self.evidence, node, {})
        context.write_text("set source_identity synthetic-fixture\n")
        result = audit.bind_saved_checkpoint(self.evidence, node, {})
        self.assertEqual(result["context"]["sha256"], hashlib.sha256(context.read_bytes()).hexdigest())
        self.assertEqual(result["main_source_provenance"]["kind"], "invocation_source_snapshot")


if __name__ == "__main__":
    unittest.main()
