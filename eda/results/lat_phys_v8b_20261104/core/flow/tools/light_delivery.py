"""Collect a small local review bundle; keep large physical/parasitic views remote."""
import argparse
import gzip
import importlib.util
import json
import os
from pathlib import Path
import shutil
import sys
import tarfile
from cleanup import generated_path, remove_generated, STAGING


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--work', type=Path, required=True)
    args = p.parse_args()
    work = args.work.expanduser().resolve()
    spec = importlib.util.spec_from_file_location('frozen_eda_flow', str(work / 'flow/bin/flow.py'))
    flow = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(flow)
    with flow.project_lock(work):
        flow.verify_inputs(work)
        flow.verify_libraries(work)
        if int((work / 'evidence/last_step.txt').read_text()) != 34 or (work / 'evidence/unexpected_tool_errors.json').exists():
            raise ValueError('Review bundle requires completed step34 without unexpected errors')
        complete = json.loads((work / 'delivery_manifest.json').read_text())
        stage34 = work / 'evidence/step_34.json'
        if flow.sha(stage34) != complete['files']['evidence/step_34.json']['sha256']:
            raise ValueError('Final evidence changed; regenerate the complete package first')
        selected = {}
        prefixes = ['config/', 'flow/', 'src/chip_design/rtl/', 'evidence/', 'syn/my_soc_top/reports/', 'pnr/my_soc_top/reports/']
        for name, value in complete['files'].items():
            root_report = name.startswith('pnr/my_soc_top/') and name.count('/') == 2 and name.endswith('.rpt')
            if (any(name.startswith(x) for x in prefixes) or root_report or name == 'src/filelist_syn.f') and value['bytes'] <= 2 * 1024 * 1024:
                path = (work / name).resolve()
                path.relative_to(work)
                if flow.sha(path) != value['sha256']:
                    raise ValueError('Delivery content changed: ' + name)
                selected[name] = path
        output = work / 'pnr/my_soc_top/outputs/manual_final'
        for name in ['my_soc_top.sdc', 'my_soc_top_path_adjust.tcl', 'my_soc_top.lef']:
            relative = (output / name).relative_to(work).as_posix()
            if flow.sha(output / name) != complete['files'][relative]['sha256']:
                raise ValueError('Small final output changed: ' + relative)
            selected[relative] = output / name
        source = output / 'my_soc_top_hier_postpnr.v'
        source_name = source.relative_to(work).as_posix()
        if flow.sha(source) != complete['files'][source_name]['sha256']:
            raise ValueError('Hierarchical netlist changed')
        compressed = generated_path(work, STAGING[0])
        compressed.parent.mkdir(exist_ok=True)
        archive = generated_path(work, 'review_delivery.tar.gz')
        partial = generated_path(work, 'review_delivery.tar.gz.part')
        checksum = generated_path(work, 'review_delivery.tar.gz.sha256')
        checksum_partial = generated_path(work, 'review_delivery.tar.gz.sha256.part')
        try:
            with source.open('rb') as src, gzip.open(str(compressed), 'wb') as dst:
                shutil.copyfileobj(src, dst, 1048576)
            selected[source_name + '.gz'] = compressed
            retained = {}
            for path in sorted(output.iterdir()):
                if path.is_file() and path.name not in ['my_soc_top.sdc', 'my_soc_top_path_adjust.tcl', 'my_soc_top.lef', 'my_soc_top_hier_postpnr.v']:
                    retained[path.relative_to(work).as_posix()] = {'bytes': path.stat().st_size, 'sha256': flow.sha(path)}
            metadata = {'scope': 'Small review copy, not the complete physical handoff. Full outputs and core_delivery.tar.gz remain remote.', 'remote_work': str(work), 'input_manifest_sha256': flow.sha(work / 'evidence/input_manifest.json'), 'collector_sha256': flow.sha(Path(__file__)), 'collector_python': sys.version.split()[0], 'files': {n: {'bytes': x.stat().st_size, 'sha256': flow.sha(x)} for n, x in selected.items()}, 'compressed_hierarchy_source': {'file': source_name, 'bytes': source.stat().st_size, 'sha256': flow.sha(source)}, 'large_final_views_retained_remote': retained, 'full_manifest_sha256': flow.sha(work / 'delivery_manifest.json')}
            flow.write_json(work / 'review_manifest.json', metadata)
            with tarfile.open(str(partial), 'w:gz') as tar:
                for name, path in sorted(selected.items()):
                    tar.add(str(path), arcname=name, recursive=False)
                for name in ['review_manifest.json', 'delivery_manifest.json']:
                    tar.add(str(work / name), arcname=name, recursive=False)
            with checksum_partial.open('w', encoding='utf-8', newline='\n') as f:
                f.write(flow.sha(partial) + '  ' + archive.name + '\n')
            os.replace(str(partial), str(archive))
            os.replace(str(checksum_partial), str(checksum))
            print(json.dumps({'archive': str(archive), 'bytes': archive.stat().st_size, 'sha256': flow.sha(archive), 'large_final_views_kept_remote': len(retained)}, indent=2))
        finally:
            remove_generated(work, STAGING + ('review_delivery.tar.gz.part', 'review_delivery.tar.gz.sha256.part'))


if __name__ == '__main__':
    main()
