"""Exercise failure boundaries and geometry; no commercial EDA license needed."""
import copy
import gzip
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
import unittest
from unittest import mock

EDA = Path(__file__).resolve().parents[1]
SERVER = EDA / 'server'
sys.path.insert(0, str(SERVER / 'tools'))
from checks import area_summary, antenna_count, placement, timing, require_clean_report, signal_connectivity, clear_step_outputs, archive_report_references, fanout_targets
from generate import generate_steps
spec = importlib.util.spec_from_file_location('eda_flow', SERVER / 'bin/flow.py')
flow = importlib.util.module_from_spec(spec)
spec.loader.exec_module(flow)


def summary(mode, count=0, wns='0.010', real=0, total=0):
    return ('| %s mode | all |\n| WNS (ns):| %s |\n| TNS (ns):| 0.000 |\n| Violating Paths:| %d |\n' % (mode, wns, count) +
            ''.join('| %s | %d (0) | 0.000 | %d (0) |\n' % (kind, real, total) for kind in ['max_cap', 'max_tran', 'max_fanout']))


class FlowTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def write(self, name, text):
        p = self.root / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding='utf-8')
        return p

    def both_modes(self, **kwargs):
        self.write('setup.summary', summary('Setup', **kwargs))
        self.write('hold.summary', summary('Hold'))

    def test_separate_clean_setup_hold_required(self):
        self.both_modes()
        self.assertEqual(set(timing(self.root, True)), {'Setup', 'Hold'})
        (self.root / 'hold.summary').unlink()
        with self.assertRaises(ValueError):
            timing(self.root, True)

    def test_rounded_negative_zero_not_accepted_with_violation(self):
        self.both_modes(count=1, wns='-0.000')
        with self.assertRaises(ValueError):
            timing(self.root, True)

    def test_real_zero_total_drv_nonzero_rejected(self):
        self.both_modes(real=0, total=1)
        with self.assertRaises(ValueError):
            timing(self.root, True)

    def test_missing_drv_is_not_zero(self):
        self.both_modes()
        p = self.root / 'setup.summary'
        p.write_text(summary('Setup').split('| max_cap')[0])
        with self.assertRaises(ValueError):
            timing(self.root, True)

    def test_actual_innovus_hold_format_omits_drv_table(self):
        self.both_modes()
        (self.root / 'hold.summary').write_text(summary('Hold').split('| max_cap')[0])
        result = timing(self.root, True)
        self.assertTrue(result['Hold']['targets_met'])
        self.assertFalse(result['Hold']['electrical_drv_table_reported_here'])
        self.assertTrue(result['Setup']['electrical_drv_table_reported_here'])

    def test_gzip_summary_is_supported(self):
        self.both_modes()
        p = self.root / 'hold.summary'
        with gzip.open(str(p) + '.gz', 'wt') as f:
            f.write(p.read_text())
        p.unlink()
        self.assertTrue(timing(self.root, True)['Hold']['targets_met'])

    def test_unknown_antenna_report_fails(self):
        p = self.write('ant.rpt', 'tool did not finish\n')
        with self.assertRaises(ValueError):
            antenna_count(p)
        p.write_text('Number of nets violated: 3\n')
        self.assertEqual(antenna_count(p), 3)
        p.write_text('No Violations Found\n')
        self.assertEqual(antenna_count(p), 0)

    def test_missing_report_is_not_clean(self):
        with self.assertRaises(ValueError):
            require_clean_report(self.root / 'missing.rpt', 'drc')

    def test_retry_removes_only_current_step_stale_outputs(self):
        stale = self.write('pnr/my_soc_top/reports/postFiller/old.summary.gz', 'stale')
        checkpoint = self.write('pnr/my_soc_top/backup/step32.enc', 'keep')
        previous = self.write('pnr/my_soc_top/reports/preCTS/old.summary', 'keep')
        source = self.write('config/design.json', '{}')
        clear_step_outputs(self.root, 33)
        self.assertFalse(stale.exists())
        self.assertTrue(checkpoint.exists())
        self.assertTrue(previous.exists())
        self.assertTrue(source.exists())

    def test_each_stage_archives_report_before_shared_name_is_overwritten(self):
        p = self.write('pnr/my_soc_top/my_soc_top_pg_drc.rpt', 'original stage15 report')
        value = {'drc': {'report': str(p)}}
        archive_report_references(self.root, 15, value)
        p.write_text('later stage21 report')
        archived = self.root / value['drc']['archived_report']
        self.assertEqual(archived.read_text(), 'original stage15 report')
        self.assertEqual(value['drc']['report_sha256'], hashlib.sha256(archived.read_bytes()).hexdigest())

    def test_connectivity_success_line_cannot_hide_problems(self):
        p = self.write('pg.rpt', 'Found no problems or warnings.\n2 Problem(s)\n')
        with self.assertRaises(ValueError):
            require_clean_report(p, 'connectivity')

    def io_report(self):
        return self.write('io_signal.rpt', 'Net VDDPST: no routing\nNet VSSPST: no routing\nBegin Summary\n 2 Problem(s) (IMPVFC-98): Net has no routing.\n 2 total info(s) created.\nEnd Summary\n')

    def io_proof(self):
        p = self.write('evidence/input_manifest.json', '{}\n')
        proof = {'input_manifest_sha256': hashlib.sha256(p.read_bytes()).hexdigest(), 'automatic_checks': {'io_native_geometry': {'native_rails_and_corner_turns_checked': True, 'actual_perimeter_continuity_checked_at_step': 12}}}
        self.write('evidence/step_22.json', json.dumps(proof))
        self.write('evidence/native_io_rails_check.json', '{}')

    def test_two_io_exceptions_need_actual_same_run_proof(self):
        p = self.io_report()
        with self.assertRaises(ValueError):
            signal_connectivity(self.root, p)
        self.io_proof()
        self.assertEqual(signal_connectivity(self.root, p)['unresolved_signal_problems'], 0)

    def test_extra_connectivity_problem_not_hidden_by_io_exception(self):
        p = self.io_report(); self.io_proof()
        p.write_text(p.read_text() + '1 Problem(s) (SHORT): signal short\n')
        with self.assertRaises(ValueError):
            signal_connectivity(self.root, p)

    def test_stale_native_io_proof_rejected(self):
        p = self.io_report(); self.io_proof()
        self.write('evidence/input_manifest.json', '{"changed":true}')
        with self.assertRaises(ValueError):
            signal_connectivity(self.root, p)

    def inherited_io_proof(self):
        self.io_proof()
        old_path = self.root / 'evidence/step_22.json'
        old = json.loads(old_path.read_text())
        old_sha = hashlib.sha256(old_path.read_bytes()).hexdigest()
        new_manifest = self.write('evidence/input_manifest.json', '{"new_controller":true}\n')
        identity = hashlib.sha256(new_manifest.read_bytes()).hexdigest()
        fixture = {'target_input_manifest_sha256': identity, 'reference_input_manifest_sha256': old['input_manifest_sha256'], 'inherited_stage_records_sha256': {'22': old_sha}}
        self.write('evidence/physical_fixture.json', json.dumps(fixture))
        reaudit = {'input_manifest_sha256': identity, 'source_step22_sha256': old_sha, 'automatic_checks': old['automatic_checks']}
        self.write('evidence/inherited_io_reaudit.json', json.dumps(reaudit))

    def test_inherited_io_needs_matching_source_record_and_fresh_reaudit(self):
        p = self.io_report(); self.inherited_io_proof()
        self.assertEqual(signal_connectivity(self.root, p)['unresolved_signal_problems'], 0)
        (self.root / 'evidence/inherited_io_reaudit.json').unlink()
        with self.assertRaises(ValueError):
            signal_connectivity(self.root, p)

    def test_changed_inherited_io_record_is_rejected(self):
        p = self.io_report(); self.inherited_io_proof()
        q = self.root / 'evidence/step_22.json'
        q.write_text(q.read_text() + '\n')
        with self.assertRaises(ValueError):
            signal_connectivity(self.root, p)

    def test_reaudit_from_another_target_input_is_rejected(self):
        p = self.io_report(); self.inherited_io_proof()
        q = self.root / 'evidence/inherited_io_reaudit.json'
        value = json.loads(q.read_text()); value['input_manifest_sha256'] = 'other-input'
        q.write_text(json.dumps(value))
        with self.assertRaises(ValueError):
            signal_connectivity(self.root, p)

    def test_placement_message_exception_needs_current_step_and_check(self):
        text = 'EDA_BEGIN_STEP 24\n**ERROR: (IMPSP-9099) placement diagnostic\n'
        self.assertEqual(len(flow.classify_tool_errors(self.root, text)[0]), 1)
        self.write('evidence/step_24.json', json.dumps({'automatic_checks': {'placement': {'unplaced': 0, 'no_other_listed_placement_violations': True}}}))
        self.assertEqual(len(flow.classify_tool_errors(self.root, text)[1]), 1)
        self.assertEqual(len(flow.classify_tool_errors(self.root, text.replace('STEP 24', 'STEP 30'))[0]), 1)

    def test_other_tool_errors_are_never_hidden_by_placement_proof(self):
        self.write('evidence/step_24.json', json.dumps({'automatic_checks': {'placement': {'unplaced': 0, 'no_other_listed_placement_violations': True}}}))
        text = 'EDA_BEGIN_STEP 24\n**ERROR: (TCLCMD-999) actual command error\n'
        self.assertEqual(len(flow.classify_tool_errors(self.root, text)[0]), 1)

    def test_area_does_not_use_net_or_total_area(self):
        p = self.write('area.rpt', 'my_soc_top 10 1000000 300000 1 2 3 4 0 6 401443.591 0 1300000\n')
        result = area_summary(p)
        self.assertEqual(result['cell_area_um2'], 1000000)
        self.assertEqual(result['net_area_um2'], 300000)
        self.assertEqual(result['latch_area_um2'], 0)

    def geometry(self, die=None):
        shutil.copytree(str(SERVER / 'tcl'), str(self.root / 'flow/tcl'))
        shutil.copytree(str(SERVER / 'config'), str(self.root / 'config'))
        (self.root / 'evidence').mkdir()
        generate_steps(self.root, die or [0, 0, 2700.32, 2701.44])
        return self.root / 'pnr/generated'

    def test_asymmetric_snapped_die_uses_both_dimensions(self):
        out = self.geometry()
        corners = (out / '05.tcl').read_text()
        self.assertIn('2585.320000', corners)
        self.assertIn('2586.440000', corners)
        checks = (out / '12_check.tcl').read_text()
        self.assertIn('2701.440000', checks)
        self.assertIn('2700.320000', checks)
        rects = json.loads((self.root / 'evidence/geometry.json').read_text())['pin_rectangles_um']
        self.assertAlmostEqual(rects['clk_i'][1], 2699.04)
        self.assertNotIn('1685.4', corners)

    def test_original_core_net_captured_before_port_detach(self):
        out = self.geometry()
        text = (out / '08.tcl').read_text()
        self.assertLess(text.index('set eda_core_object'), text.index('detachModulePort'))
        self.assertNotIn('i_dmi_jtag', text)

    def test_generated_macro_area_tracks_configured_location(self):
        self.geometry()
        cfg_path = self.root / 'config/design.json'
        cfg = json.loads(cfg_path.read_text()); cfg['macro_xy_um'] = [750, 850]
        cfg_path.write_text(json.dumps(cfg))
        generate_steps(self.root, [0, 0, 2700.32, 2701.44])
        text = (self.root / 'pnr/generated/18.tcl').read_text()
        self.assertIn('1304.595000', text)
        self.assertIn('1587.850000', text)

    def test_overlapping_pad_offsets_are_rejected(self):
        self.geometry()
        p = self.root / 'config/io_plan.json'
        obj = json.loads(p.read_text()); obj['signals'][0]['offset_um'] = 600
        p.write_text(json.dumps(obj))
        with self.assertRaises(ValueError):
            generate_steps(self.root, [0, 0, 2700, 2700])

    def test_input_change_invalidates_resume(self):
        self.write('src/top.sv', 'module top; endmodule')
        self.write('config/design.json', '{}')
        self.write('flow/bin/control.py', 'x=1')
        self.write('syn/scripts/main.tcl', 'puts original')
        self.write('evidence/input_manifest.json', json.dumps(flow.fingerprint_inputs(self.root)))
        flow.verify_inputs(self.root)
        self.write('syn/scripts/main.tcl', 'puts changed')
        with self.assertRaises(ValueError):
            flow.verify_inputs(self.root)

    def test_incomplete_or_too_small_fixed_core_is_rejected(self):
        shutil.copytree(str(SERVER / 'config'), str(self.root / 'config'))
        self.write('syn/my_soc_top/reports/area/area.rpt', 'my_soc_top 10 4000000 300000 1 2 3 4 0 6 401443.591 0 4300000\n')
        result = flow.sizing(self.root)
        self.assertGreater(result['core_size_um'], 1500)
        cfg = json.loads((self.root / 'config/design.json').read_text()); cfg['core_size_um'] = 1500
        (self.root / 'config/design.json').write_text(json.dumps(cfg))
        with self.assertRaises(ValueError):
            flow.sizing(self.root)

    def test_all_tcl_files_are_complete(self):
        try:
            import tkinter
        except ImportError:
            self.skipTest('tkinter not installed; remote tclsh validation is separate')
        tcl = tkinter.Tcl()
        out = self.geometry()
        paths = list(out.glob('*.tcl')) + list((SERVER / 'tcl').glob('*.tcl'))
        for p in paths:
            self.assertTrue(int(tcl.call('info', 'complete', p.read_text(encoding='utf-8'))), p.name)

    def tcl_helpers(self):
        try:
            import tkinter
        except ImportError:
            self.skipTest('tkinter not installed')
        tcl = tkinter.Tcl()
        source = (SERVER / 'tcl/driver.tcl').read_text(encoding='utf-8')
        source = source[source.index('proc eda_picture'):source.index('if {[catch {')]
        tcl.eval(source)
        return tcl

    def test_tcl_trace_resolves_macro_and_executes_in_global_scope(self):
        tcl = self.tcl_helpers()
        self.write('pnr/generated/08.tcl', 'set observed i_mainmem/i_mainmem\n')
        for key, value in [('eda_work', self.root.as_posix()), ('step', 8), ('eda_command_index', 0), ('eda_sram', 'i_mainmem/i_sram/i_macro')]:
            tcl.setvar(key, value)
        self.assertEqual(tcl.call('eda_run', '08.tcl'), 'i_mainmem/i_sram/i_macro')
        self.assertEqual(tcl.getvar('observed'), 'i_mainmem/i_sram/i_macro')
        records = list((self.root / 'evidence/commands/08').glob('*.tcl'))
        self.assertEqual(len(records), 1)
        self.assertIn('set observed i_mainmem/i_sram/i_macro', records[0].read_text())

    def test_tcl_timing_branch_uses_current_gzip_report_violation_count(self):
        tcl = self.tcl_helpers()
        with gzip.open(str(self.root / 'hold.summary.gz'), 'wt') as f:
            f.write(summary('Hold', count=1, wns='-0.000').split('| max_cap')[0])
        self.assertEqual(int(tcl.call('eda_timing_bad', self.root.as_posix(), 'Hold')), 1)

    def test_pad_rewire_preserves_core_when_detach_replaces_net_object(self):
        tcl = self.tcl_helpers()
        generated = self.geometry()
        # Model the observed Innovus behavior: the old net object stays with
        # the external port, while the internal pin moves onto a new core net.
        tcl.eval('''
            proc dbGet {args} {
                if {[lindex $args 0] eq "-e"} {set args [lrange $args 1 end]}
                set query [lindex $args 0]
                if {$query eq "top.terms.name"} {return term_[lindex $args 1]}
                if {[regexp {^term_(.*)\\.net$} $query -> port]} {return stale_$port}
                if {[regexp {^stale_(.*)\\.instTerms$} $query -> port]} {return anchor_$port}
                if {[regexp {^stale_(.*)\\.name$} $query -> port]} {return $port}
                if {[regexp {^anchor_(.*)\\.net.name$} $query -> port]} {return core_$port}
                if {[regexp {^term_(.*)\\.net.name$} $query -> port]} {return $port}
                error "Unexpected query $args"
            }
            foreach command {addNet detachModulePort attachModulePort saveNetlist} {proc $command {args} {}}
            proc attachTerm {instance pin net} {set ::connections($instance,$pin) $net}
        ''')
        tcl.eval((generated / '08.tcl').read_text(encoding='utf-8'))
        for signal in json.loads((SERVER / 'config/io_plan.json').read_text())['signals']:
            pad, port = 'i_pad_' + signal['pad'], signal['port']
            pin = 'I' if signal['direction'] == 'output' else 'C'
            self.assertEqual(tcl.getvar('connections(%s,%s)' % (pad, pin)), 'core_' + port)
            self.assertEqual(tcl.getvar('connections(%s,PAD)' % pad), port)

    def fanout_report(self):
        return ('weights/net_1\n    weights/driver/ZN 16.000 17.000 -1.000 INVD6BWP7T/ZN R\n'
                'weights/net_2\n    weights/driver2/Z 16.000 17.000 -1.000 BUFFD2BWP7T/Z R\n'
                '*info: there are 2 max fanout load violations in the design.\n'
                '*info: 2 violations are real (remark R).\n')

    def test_fanout_parser_extracts_real_report_targets(self):
        targets = fanout_targets(self.write('fanout.rpt', self.fanout_report()))
        self.assertEqual([r['net'] for r in targets], ['weights/net_1', 'weights/net_2'])
        self.assertEqual(targets[0]['maximum_load'], 16)
        self.assertEqual(targets[0]['actual_load'], 17)

    def test_fanout_missing_row_cannot_look_like_zero(self):
        text = self.fanout_report().splitlines()
        with self.assertRaises(ValueError):
            fanout_targets(self.write('fanout.rpt', '\n'.join(text[2:])))

    def test_fanout_nonreal_or_inconsistent_report_is_rejected(self):
        for value in [self.fanout_report().replace('2 violations are real', '1 violations are real'), self.fanout_report().replace('-1.000', '-2.000')]:
            with self.assertRaises(ValueError):
                fanout_targets(self.write('fanout.rpt', value))

    def test_fanout_branch_keeps_antenna_on_original_net(self):
        tcl = self.tcl_helpers()
        tcl.eval((SERVER / 'tcl/fanout.tcl').read_text(encoding='utf-8'))
        rows = [(i, 10, 'logic_%02d/A' % i, 'ND2D1BWP7T') for i in range(16)]
        rows.insert(0, (-1, 10, 'DIODE_11/I', 'ANTENNABWP7T'))
        selected = tcl.call('eda_choose_fanout_terms', tuple(rows))
        self.assertEqual(len(selected), 8)
        self.assertNotIn('DIODE_11/I', selected)
        self.assertEqual(list(selected), ['logic_%02d/A' % i for i in range(8)])

    def test_fanout_no_two_logical_receivers_requires_adaptation(self):
        tcl = self.tcl_helpers()
        tcl.eval((SERVER / 'tcl/fanout.tcl').read_text(encoding='utf-8'))
        with self.assertRaises(Exception):
            tcl.call('eda_choose_fanout_terms', ((1, 2, 'DIODE/I', 'ANTENNABWP7T'), (2, 3, 'logic/A', 'ND2D1BWP7T')))

    def test_fanout_regex_matches_literal_bus_and_special_net_name(self):
        tcl = self.tcl_helpers()
        tcl.eval((SERVER / 'tcl/fanout.tcl').read_text(encoding='utf-8'))
        name = 'weights/data[7].net*'
        pattern = tcl.call('eda_literal_net_pattern', name)
        self.assertEqual(int(tcl.call('regexp', pattern, name)), 1)
        self.assertEqual(int(tcl.call('regexp', pattern, 'weights/data7XnetANY')), 0)

    def test_deployment_archive_has_linux_checksum_and_no_libraries(self):
        archive = self.root / 'deploy.tar.gz'
        subprocess.run([sys.executable, str(EDA / 'package_server.py'), '--output', str(archive)], cwd=str(EDA.parent), check=True, stdout=subprocess.PIPE)
        checksum = archive.with_name(archive.name + '.sha256').read_bytes()
        self.assertNotIn(b'\r', checksum)
        with tarfile.open(str(archive), 'r:gz') as tar:
            names = tar.getnames()
            self.assertIn('server/bin/flow.py', names)
            self.assertIn('rtl/filelist.f', names)
            self.assertIn('source.json', names)
            self.assertFalse(any(n.startswith('/') or '..' in n.split('/') for n in names))
            self.assertFalse(any(any(s in ['.lib', '.lef', '.gds', '.vclef', '.cdl', '.spi'] for s in Path(n).suffixes) for n in names))
            for n in names:
                if n.endswith('.sh'):
                    self.assertNotIn(b'\r', tar.extractfile(n).read(), n)

    def test_delivery_keeps_large_reports_remote_and_records_size(self):
        self.write('evidence/last_step.txt', '34\n')
        self.write('evidence/doctor.json', '{"libraries_sha256":{}}')
        p = self.root / 'pnr/my_soc_top/huge_report.rpt'
        p.parent.mkdir(parents=True)
        with p.open('wb') as f:
            f.truncate(51 * 1024 * 1024)
        with mock.patch.object(flow, 'audit_step', return_value={}):
            flow.package(self.root)
        value = json.loads((self.root / 'delivery_manifest.json').read_text())
        name = p.relative_to(self.root).as_posix()
        self.assertEqual(value['skipped_over_50_MiB_bytes'][name], 51 * 1024 * 1024)
        with tarfile.open(str(self.root / 'core_delivery.tar.gz'), 'r:gz') as tar:
            self.assertNotIn(name, tar.getnames())


if __name__ == '__main__':
    unittest.main()
