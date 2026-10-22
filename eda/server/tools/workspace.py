"""Initialize entry points and GUI documentation inside one isolated upload."""
import argparse
import html
import json
from pathlib import Path
import re
import shlex
import shutil
from urllib.parse import quote


def write(path, value):
    if path.is_symlink():
        raise ValueError('Refusing to overwrite an upload symlink: ' + str(path))
    with path.open('w', encoding='utf-8', newline='\n') as stream:
        stream.write(value)


def read_json(path):
    return json.loads(path.read_text(encoding='utf-8')) if path.is_file() else {}


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
    collect = '''#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "$0")"
source ./run_env.sh
exec > >(tee -a "$EDA_UPLOAD/logs/collect.log") 2>&1
bash "$EDA_DEPLOY/server/bin/eda.sh" report --work "$EDA_WORK"
bash "$EDA_DEPLOY/server/bin/eda.sh" package --work "$EDA_WORK"
bash "$EDA_DEPLOY/server/bin/review.sh" --work "$EDA_WORK"
bash "$EDA_DEPLOY/server/bin/workspace.sh" --root "$EDA_UPLOAD"
'''
    run = '''#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "$0")"
source ./run_env.sh
for eda_arg in "$@"; do
    case "$eda_arg" in --headless) ;; *) echo "Only --headless is accepted; paths are fixed to this upload" >&2; exit 2;; esac
done
exec > >(tee -a "$EDA_UPLOAD/logs/flow.log") 2>&1
refresh_readme() {
    eda_exit=$?
    bash "$EDA_DEPLOY/server/bin/workspace.sh" --root "$EDA_UPLOAD" || true
    exit "$eda_exit"
}
trap refresh_readme EXIT
eda_args=(all --work "$EDA_WORK")
if [ ! -d "$EDA_WORK" ]; then eda_args+=(--config "$EDA_CONFIG"); fi
bash "$EDA_DEPLOY/server/bin/eda.sh" "${eda_args[@]}" "$@"
bash ./collect_results.sh
'''
    for name, body in [('run_all.sh', run), ('collect_results.sh', collect)]:
        write(root / name, body)
        (root / name).chmod(0o755)
    source, upload = read_json(deploy / 'source.json'), read_json(root / 'upload.json')
    stage = read_json(work / 'evidence/step_33.json').get('automatic_checks', {})
    last = work / 'evidence/last_step.txt'
    progress = int(last.read_text().strip()) if last.is_file() else 0
    timing = stage.get('timing', {})
    setup, hold = [timing.get(k, {}).get('wns_ns', '尚未生成') for k in ['Setup', 'Hold']]
    error = (work / 'evidence/unexpected_tool_errors.json').is_file()
    summary = {'upload': str(root), 'archive_sha256': upload.get('archive_sha256'),
               'deployment_commit': source.get('git_commit'), 'work': str(work),
               'last_completed_step': progress, 'unexpected_tool_errors': error,
               'setup_wns_ns': setup, 'hold_wns_ns': hold,
               'final_stage_checks': stage,
               'export_checks': read_json(work / 'evidence/step_34.json').get('automatic_checks', {})}
    write(root / 'results/summary.json', json.dumps(summary, ensure_ascii=False, indent=2) + '\n')
    rows = [
        ('chip_design_eda.tar.gz', '本次上传的原始包，保留为版本来源；不同上传目录各存自己的包。'),
        ('chip_design_eda.tar.gz.sha256', '上传包内容校验值，公共解压器用它验证传输。'),
        ('upload.json', '本上传目录的包SHA与源码提交；原包变化时拒绝覆盖解压。'),
        ('deploy/', '本版本的server、RTL、docs和source.json，其他版本不引用这里。'),
        ('configs/design.json', '本版本准备前的参数副本：工艺路径、周期、CPU、宏坐标等。'),
        ('work/', '本版本唯一运行工程：输入快照、综合、后端、检查点、原始报告及最终导出。'),
        ('logs/', '本版本完整入口和收集入口的控制台日志。'),
        ('results/summary.json', '本版本的阶段、最终时间和物理/导出检查摘要。'),
        ('docs/', '本版本配套的操作指南、34步解释、基础知识和报告分析。'),
        ('run_env.sh', '只指向本上传目录的路径变量，重新登录后source此文件。'),
        ('run_all.sh', '本版本完整综合、01–34与打包；再次运行仅在本版本work内续跑。'),
        ('collect_results.sh', '本版本完成实现后重新生成报告与交付包。'),
    ]
    links = [
        ('运行入口日志', 'logs/flow.log'), ('综合原始日志', 'work/evidence/genus_synthesis.log'),
        ('逐步运行报告', 'work/evidence/运行报告.md'),
        ('最终时序与物理检查', 'work/evidence/step_33.json'),
        ('导出检查', 'work/evidence/step_34.json'),
        ('布局截图', 'work/evidence/34_final_layout.gif'),
        ('最终Setup/Hold报告目录', 'work/pnr/my_soc_top/reports/postFiller/'),
        ('最终DEF、GDS、网表、SDF、SPEF', 'work/pnr/my_soc_top/outputs/manual_final/'),
        ('检查点', 'work/pnr/my_soc_top/backup/'),
    ]
    command = 'cd ' + shlex.quote(str(root)) + '\nsource ./run_env.sh\nbash ./run_all.sh'
    md = '# 本次上传的独立EDA工程\n\n版本目录：`%s`\n\n源码提交：`%s`；后端完成：%d/34；未解决工具错误：%s；最终Setup/Hold WNS：%s / %s ns。\n\n' % (root, source.get('git_commit'), progress, '有' if error else '未发现', setup, hold)
    md += '公共脚本只负责解压；本目录的脚本、配置、日志和结果不使用其他上传版本，也不写共享current_run。未生成的指标不表示通过。\n\n| 路径 | 作用 |\n| --- | --- |\n'
    md += '\n'.join('| [%s](%s) | %s |' % (n, quote(n), meaning) for n, meaning in rows)
    md += '\n\n## 运行或继续\n\n```bash\n' + command + '\n```\n\n长任务使用tmux或nohup。新版本必须新建上传目录，不在此替换原包或修改已准备输入。\n\n## 结果入口\n\n'
    md += '\n'.join('- [%s](%s)' % (label, quote(path)) for label, path in links)
    md += '\n\n下载校验后可用`bash deploy/server/bin/eda.sh clean --work "$PWD/work" --dry-run`预览，去掉--dry-run清理本版本交付包。原上传包、清单、日志、报告、中间文件、检查点和最终视图保留。\n\n本流程为单TT教学实现；独立晶圆厂DRC/LVS、IR/EM/ESD及SDF回标仿真需另行执行。\n'
    write(root / 'README.md', md)
    table = ''.join('<tr><td><a href="%s">%s</a></td><td>%s</td></tr>' % (quote(n), html.escape(n), html.escape(m)) for n, m in rows)
    items = ''.join('<li><a href="%s">%s</a></li>' % (quote(path), html.escape(label)) for label, path in links)
    page = '''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>独立上传版本的EDA说明</title>
<style>body{font-family:"Noto Sans CJK SC",sans-serif;max-width:1100px;margin:36px auto;padding:0 24px;line-height:1.8;color:#203044;background:#f5f7fa}h1,h2{color:#123959}table{border-collapse:collapse;background:white;width:100%%}td,th{border:1px solid #d7dfe8;padding:12px;text-align:left;vertical-align:top}a{color:#075ea9}pre{white-space:pre-wrap;background:#152b40;color:white;padding:20px;border-radius:8px}.status{background:#e5effa;padding:18px;border-radius:8px}</style>
<h1>本次上传的独立EDA工程</h1><p>每个上传版本有自己的原包、解压文件、脚本、配置和结果。公共解压脚本在顶层；后续操作全部在本目录内。</p>
<div class="status">版本目录：%s<br>源码提交：%s<br>后端完成：%d / 34；未解决工具错误：%s<br>最终Setup / Hold WNS：%s / %s ns<br>尚未生成的指标不表示通过，结论以原报告及第33/34步为准。</div>
<h2>文件结构与作用</h2><table><tr><th>本版本路径</th><th>作用</th></tr>%s</table>
<h2>运行或继续</h2><pre>%s</pre><p>长任务使用tmux或nohup。本版本已有进度会在自己的work内继续；新版本要新建上传目录，不能替换此处原包或改写已准备输入。</p>
<h2>从哪里读结果</h2><ul>%s</ul><p>JSON、Markdown、日志可用文本编辑器打开。压缩时间报告用gzip -cd 文件 | less阅读。尚未生成的文件暂时无法打开。</p>
<h2>清理</h2><p>下载校验后，用本版本的eda.sh clean --work "$PWD/work" --dry-run预览，去掉--dry-run清理交付包。原上传包、清单、日志、报告、中间文件、检查点和最终GDS/SDF/SPEF保留。不清理或修改其他版本。</p>
<p>单TT教学实现不代表独立晶圆厂DRC/LVS、IR/EM/ESD签核或SDF回标仿真已完成。</p></html>''' % (html.escape(str(root)), html.escape(str(source.get('git_commit'))), progress, '有' if error else '未发现', html.escape(str(setup)), html.escape(str(hold)), table, html.escape(command), items)
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
