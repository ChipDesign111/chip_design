"""Initialize entry points and GUI documentation inside one isolated upload."""
import argparse
import html
import json
from pathlib import Path
import re
import shlex
import shutil


def write(path, value):
    if path.is_symlink():
        raise ValueError('Refusing to overwrite an upload symlink: ' + str(path))
    with path.open('w', encoding='utf-8', newline='\n') as stream:
        stream.write(value)


def read_json(path):
    return json.loads(path.read_text(encoding='utf-8')) if path.is_file() else {}


def render_markdown(markdown):
    """Render the deliberately small Markdown subset used in server/README.md."""
    def inline(value):
        value = html.escape(value)
        value = re.sub(r'`([^`]+)`', r'<code>\1</code>', value)
        value = re.sub(r'\[([^]\n]+)\]\(([^)\n]+)\)', r'<a href="\2">\1</a>', value)
        return re.sub(r'\*\*([^*]+)\*\*', r'<strong>\1</strong>', value)
    output, code, table, listing = [], None, False, False
    for line in markdown.splitlines() + ['']:
        if line.startswith('```'):
            if code is None:
                code = []
            else:
                output.append('<pre><code>' + html.escape('\n'.join(code)) + '</code></pre>')
                code = None
            continue
        if code is not None:
            code.append(line)
            continue
        if table and not line.startswith('|'):
            output.append('</table>')
            table = False
        if listing and not line.startswith('- '):
            output.append('</ul>')
            listing = False
        if line.startswith('|'):
            cells = [x.strip() for x in line.strip('|').split('|')]
            if all(re.fullmatch(r':?-+:?', x) for x in cells):
                continue
            if not table:
                output.append('<table>')
                table = True
            output.append('<tr>' + ''.join('<td>' + inline(x) + '</td>' for x in cells) + '</tr>')
        elif line.startswith('- '):
            if not listing:
                output.append('<ul>')
                listing = True
            output.append('<li>' + inline(line[2:]) + '</li>')
        elif line.startswith('#'):
            level = len(line) - len(line.lstrip('#'))
            output.append('<h%d>%s</h%d>' % (level, inline(line[level:].strip()), level))
        elif line.strip():
            output.append('<p>' + inline(line) + '</p>')
    return '\n'.join(output)


def initialize(root, deploy):
    original = root.expanduser()
    if original.is_symlink():
        raise ValueError('Use a real upload directory')
    root, deploy = original.resolve(), deploy.resolve()
    if (not re.fullmatch(r'[A-Za-z0-9_./-]+', str(root))
            or root.parent.name != 'uploads' or deploy != root / 'deploy'
            or not (root / 'upload.json').is_file()):
        raise ValueError('Use the public unpack.sh to initialize <workspace>/uploads/<version>')
    if not (deploy / 'source.json').is_file() or not (deploy / 'rtl/filelist.f').is_file():
        raise ValueError('Missing deployment source.json or RTL')
    for name in ['configs', 'logs', 'results', 'docs', 'work']:
        path = root / name
        if path.is_symlink():
            raise ValueError('Upload directories cannot be symlinks: ' + str(path))
        path.resolve().relative_to(root)
        if name != 'work':
            path.mkdir(parents=True, exist_ok=True)
    if (deploy / 'docs').is_dir():
        shutil.copytree(str(deploy / 'docs'), str(root / 'docs'), dirs_exist_ok=True)
    config = root / 'configs/design.json'
    if config.is_symlink():
        raise ValueError('Configuration must belong to this upload')
    if not config.exists():
        shutil.copyfile(str(deploy / 'server/config/design.json'), str(config))
    work = root / 'work'
    write(root / 'run_env.sh', '\n'.join([
        '# Paths belong exclusively to this upload. No global current-run state.',
        'export EDA_UPLOAD=' + shlex.quote(str(root)),
        'export EDA_DEPLOY=' + shlex.quote(str(deploy)),
        'export EDA_CONFIG=' + shlex.quote(str(config)),
        'export EDA_WORK=' + shlex.quote(str(work)), '']))
    for name in ['check_env.sh', 'run_eda.sh', 'collect_results.sh', 'run_all.sh']:
        body = (deploy / 'server/entry' / name).read_text(encoding='utf-8')
        write(root / name, body)
        (root / name).chmod(0o755)
    source, upload = read_json(deploy / 'source.json'), read_json(root / 'upload.json')
    stage = read_json(work / 'evidence/step_33.json').get('automatic_checks', {})
    last = work / 'evidence/last_step.txt'
    progress = int(last.read_text().strip()) if last.is_file() else 0
    timing = stage.get('timing', {})
    setup, hold = [timing.get(k, {}).get('wns_ns', '尚未生成') for k in ['Setup', 'Hold']]
    error = (work / 'evidence/unexpected_tool_errors.json').is_file()
    geometry=read_json(work/'evidence/geometry.json')
    whole_area=geometry.get('whole_die_area_mm2')
    limit=read_json(work/'config/design.json').get('max_die_area_mm2',4.0)
    summary = {'acceptance_profile':read_json(root/'configs/design.json').get('acceptance_profile'),
               'minimum_setup_and_hold_wns_ns':0.0,
               'whole_die_area_mm2':whole_area,'max_whole_die_area_mm2':limit,
               'whole_die_area_within_limit':None if whole_area is None else whole_area<=limit, 'upload': str(root), 'archive_sha256': upload.get('archive_sha256'),
               'deployment_commit': source.get('git_commit'), 'work': str(work),
               'last_completed_step': progress, 'unexpected_tool_errors': error,
               'setup_wns_ns': setup, 'hold_wns_ns': hold,
               'final_stage_checks': stage,
               'export_checks': read_json(work / 'evidence/step_34.json').get('automatic_checks', {})}
    exit_file = root / 'logs/run_exit_code.txt'
    exit_code = int(exit_file.read_text().strip()) if exit_file.is_file() else None
    ready = (work / 'review_delivery.tar.gz').is_file()
    summary.update(pipeline_exit_code=exit_code, review_archive_ready=ready)
    write(root / 'results/summary.json', json.dumps(summary, ensure_ascii=False, indent=2) + '\n')
    status = '尚未完成；请查看logs和work/evidence中的当前日志'
    if exit_code is not None and exit_code != 0:
        status = '入口退出码%d；检查对应阶段日志后再继续' % exit_code
    elif progress == 34 and ready and not error:
        status = '34步及结果整理已完成'
    template = (deploy / 'server/README.md').read_text(encoding='utf-8').replace('(../docs/', '(docs/')
    replacements = {'UPLOAD': str(root), 'COMMIT': str(source.get('git_commit')), 'STATUS': status,
                    'STEP': str(progress), 'SETUP': str(setup), 'HOLD': str(hold), 'AREA':str(whole_area) if whole_area is not None else '尚未生成', 'AREA_LIMIT':str(limit)}
    md = template
    for key, value in replacements.items():
        md = md.replace('{{' + key + '}}', value)
    write(root / 'README.md', md)
    page = '<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>本上传版本的EDA操作指南</title><style>body{font-family:"Noto Sans CJK SC",sans-serif;max-width:1100px;margin:36px auto;padding:0 24px;line-height:1.8;color:#203044;background:#f5f7fa}h1,h2,h3{color:#123959}table{border-collapse:collapse;background:white;width:100%}td,th{border:1px solid #d7dfe8;padding:10px;text-align:left;vertical-align:top}a{color:#075ea9}pre{white-space:pre-wrap;overflow-wrap:anywhere;background:#152b40;color:white;padding:20px;border-radius:8px}code{overflow-wrap:anywhere}p{overflow-wrap:anywhere}</style>' + render_markdown(md) + '</html>'
    write(root / 'README.html', page)
    print(json.dumps({'upload': str(root), 'deploy': str(deploy), 'work': str(work), 'readme': str(root / 'README.html')}, ensure_ascii=False))
    return summary


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root', type=Path, required=True, help='The individual uploads/<version> directory')
    args = p.parse_args()
    initialize(args.root, Path(__file__).resolve().parents[2])


if __name__ == '__main__':
    main()
