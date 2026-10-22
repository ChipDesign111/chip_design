"""Create the desktop workspace entry points and an offline GUI README."""
import argparse
from datetime import datetime, timedelta, timezone
import html
import json
from pathlib import Path
import re
import shlex
import shutil
from urllib.parse import quote


def write(path, value):
    with path.open('w', encoding='utf-8', newline='\n') as stream:
        stream.write(value)


def read_json(path):
    return json.loads(path.read_text(encoding='utf-8')) if path.is_file() else {}


def initialize(root, deploy):
    root = root.expanduser().resolve()
    deploy = deploy.resolve()
    if not re.fullmatch(r'[A-Za-z0-9_./-]+', str(root)) or deploy != root / 'deploy':
        raise ValueError('Unpack the deployment in <workspace>/deploy; use an ASCII path without spaces')
    if not (deploy / 'source.json').is_file() or not (deploy / 'rtl/filelist.f').is_file():
        raise ValueError('Missing deployment source.json or RTL')
    for name in ['incoming', 'configs', 'runs', 'logs', 'results', 'docs', 'lab4', 'history']:
        (root / name).mkdir(parents=True, exist_ok=True)
    if (deploy / 'docs').is_dir():
        shutil.copytree(str(deploy / 'docs'), str(root / 'docs'), dirs_exist_ok=True)
    config_path = root / 'configs/design.json'
    if not config_path.exists():
        shutil.copyfile(str(deploy / 'server/config/design.json'), str(config_path))
    pointer = root / 'current_run.txt'
    if pointer.is_file():
        work = Path(pointer.read_text(encoding='utf-8').strip()).resolve()
        work.relative_to(root / 'runs')
    else:
        stamp = datetime.now(timezone(timedelta(hours=8))).strftime('%Y%m%d_%H%M%S')
        work = root / 'runs' / ('w8a4_' + stamp)
        write(pointer, str(work) + '\n')
    write(root / 'run_env.sh', '\n'.join([
        '# Generated workspace paths; all run products stay under this directory.',
        'export CHIP_WORKSPACE=' + shlex.quote(str(root)),
        'export EDA_DEPLOY=' + shlex.quote(str(deploy)),
        'export EDA_CONFIG=' + shlex.quote(str(config_path)),
        'export EDA_WORK=' + shlex.quote(str(work)), '']))
    collect = '''#!/usr/bin/env bash
set -e
cd -- "$(dirname -- "$0")"
source ./run_env.sh
bash "$EDA_DEPLOY/server/bin/eda.sh" report --work "$EDA_WORK"
bash "$EDA_DEPLOY/server/bin/eda.sh" package --work "$EDA_WORK"
bash "$EDA_DEPLOY/server/bin/review.sh" --work "$EDA_WORK"
bash "$EDA_DEPLOY/server/bin/workspace.sh" --root "$CHIP_WORKSPACE"
'''
    run = '''#!/usr/bin/env bash
set -e
cd -- "$(dirname -- "$0")"
source ./run_env.sh
refresh_readme() {
    eda_exit=$?
    bash "$EDA_DEPLOY/server/bin/workspace.sh" --root "$CHIP_WORKSPACE" || true
    exit "$eda_exit"
}
trap refresh_readme EXIT
eda_args=(all --work "$EDA_WORK")
if [ ! -d "$EDA_WORK" ]; then
    eda_args+=(--config "$EDA_CONFIG")
fi
bash "$EDA_DEPLOY/server/bin/eda.sh" "${eda_args[@]}" "$@"
bash ./collect_results.sh
'''
    for name, body in [('run_all.sh', run), ('collect_results.sh', collect)]:
        write(root / name, body)
        (root / name).chmod(0o755)
    source = read_json(deploy / 'source.json')
    stage = read_json(work / 'evidence/step_33.json').get('automatic_checks', {})
    last = work / 'evidence/last_step.txt'
    progress = last.read_text().strip() if last.is_file() else '0'
    work_rel = work.relative_to(root).as_posix()
    timing = stage.get('timing', {})
    setup = timing.get('Setup', {}).get('wns_ns', '尚未生成')
    hold = timing.get('Hold', {}).get('wns_ns', '尚未生成')
    error = (work / 'evidence/unexpected_tool_errors.json').is_file()
    summary = {'workspace': str(root), 'deployment_commit': source.get('git_commit'),
               'work': str(work), 'last_completed_step': int(progress),
               'unexpected_tool_errors': error, 'setup_wns_ns': setup, 'hold_wns_ns': hold,
               'final_stage_checks': stage,
               'export_checks': read_json(work / 'evidence/step_34.json').get('automatic_checks', {})}
    write(root / 'results/current_run.json', json.dumps(summary, ensure_ascii=False, indent=2) + '\n')
    rows = [
        ('deploy/', '当前正式部署：server脚本、RTL、source.json；不在这里生成实现输出。'),
        ('configs/design.json', '本轮准备前的参数副本：PDK、SRAM来源、周期、CPU与宏位置。'),
        ('runs/', '每轮独立工程：输入快照、综合、布局布线、检查点、最终导出和运行报告。'),
        ('logs/', '从桌面入口启动完整流程的控制台日志，方便查看运行进度和错误。'),
        ('results/current_run.json', '当前运行的阶段与最终指标摘要；原始报告仍在runs中。'),
        ('docs/', '部署操作指南、34步解释、报告分析和基础知识。'),
        ('lab4/', '完整保留的原Lab 4工程、课程资料和辅助材料。'),
        ('history/', '历史有效结果；不作为当前运行输入，旧报告绝对路径仅代表当时来源。'),
        ('incoming/', '上传包接收区；确认部署成功后可清理已解压的包。'),
        ('run_env.sh', '当前工作区全部路径；重新登录后source即可恢复环境变量。'),
        ('run_all.sh', '从RTL开始完整实现并打包；同一工程再次调用时按已通过进度续跑。'),
        ('collect_results.sh', '最终步骤完成后重新生成报告和交付包，不重新实现电路。'),
    ]
    links = [
        ('本轮逐步运行报告', work_rel + '/evidence/运行报告.md'),
        ('最终时序与物理检查', work_rel + '/evidence/step_33.json'),
        ('导出检查', work_rel + '/evidence/step_34.json'),
        ('最终布局截图', work_rel + '/evidence/34_final_layout.gif'),
        ('最终Setup/Hold原始报告目录', work_rel + '/pnr/my_soc_top/reports/postFiller/'),
        ('最终DEF、GDS、网表、SDF、SPEF', work_rel + '/pnr/my_soc_top/outputs/manual_final/'),
        ('检查点目录', work_rel + '/pnr/my_soc_top/backup/'),
    ]
    command = 'cd ' + shlex.quote(str(root)) + '\nsource ./run_env.sh\nbash ./run_all.sh'
    body = '\n'.join('| [%s](%s) | %s |' % (name, quote(name), meaning) for name, meaning in rows)
    md = ('# fullstack_chipdesign 服务器工作区\n\n'
          'GUI中双击README.html查看带链接的说明。本文件也可用文本编辑器阅读。\n\n'
          '当前部署提交：`%s`；当前工程：`%s`。\n\n'
          '后端最后完成步骤：%s/34；未解决工具错误记录：%s；最终Setup/Hold WNS：%s / %s ns。\n\n'
          '未生成的指标不表示通过。完成后请结合原报告和第33/34步检查判断。\n\n'
          '| 路径 | 作用 |\n| --- | --- |\n%s\n\n'
          '## 开始或继续\n\n```bash\n%s\n```\n\n'
          '长任务在tmux内运行，或按操作指南使用nohup；不要同时启动两份写同一工程的任务。'
          '查看状态可运行`bash "$EDA_DEPLOY/server/bin/eda.sh" status --work "$EDA_WORK"`。\n\n'
          '## 结果入口\n\n%s\n\n'
          '## 保留与清理\n\n'
          'Lab 4原始目录完整保留在lab4中；历史工程迁移后，旧记录中的绝对路径不自动改写，避免改变原证据。'
          '当前实验只使用deploy与runs，不从history导入检查点。工艺库读取/lec/pdk/tsmc180，授权SRAM读取/lec/lab4，二者不复制到Git。\n\n'
          '下载校验后，用`bash "$EDA_DEPLOY/server/bin/eda.sh" clean --work "$EDA_WORK" --dry-run`预览，去掉--dry-run清理交付压缩包。'
          '报告、日志、清单、中间文件、检查点及最终GDS/SDF/SPEF保留。\n\n'
          '单TT教学流程不等于独立晶圆厂DRC/LVS、IR/EM/ESD签核或SDF回标仿真。\n') % (
              source.get('git_commit', '未知'), str(work), progress, error, setup, hold, body,
              command, '\n'.join('- [%s](%s)' % (label, quote(path)) for label, path in links))
    write(root / 'README.md', md)
    html_rows = ''.join('<tr><td><a href="%s">%s</a></td><td>%s</td></tr>' %
                        (quote(name), html.escape(name), html.escape(meaning)) for name, meaning in rows)
    html_links = ''.join('<li><a href="%s">%s</a></li>' %
                         (quote(path), html.escape(label)) for label, path in links)
    page = '''<!doctype html><html lang="zh-CN"><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><title>fullstack_chipdesign 使用说明</title>
<style>body{font-family:"Noto Sans CJK SC",sans-serif;max-width:1100px;margin:36px auto;padding:0 24px;line-height:1.8;color:#203044;background:#f5f7fa}h1,h2{color:#123959}table{border-collapse:collapse;background:white;width:100%%}td,th{border:1px solid #d7dfe8;padding:12px;text-align:left;vertical-align:top}a{color:#075ea9}pre{white-space:pre-wrap;background:#152b40;color:white;padding:20px;border-radius:8px}.status{background:#e5effa;padding:18px;border-radius:8px}code{font-family:monospace}</style>
<h1>fullstack_chipdesign 服务器工作区</h1><p>在桌面文件管理器进入本文件夹，双击本README即可查看。所有后续部署、运行与结果都放在这里。</p>
<div class="status">部署提交：%s<br>本轮工程：%s<br>最后完成：%s / 34；未解决工具错误：%s<br>最终Setup / Hold WNS：%s / %s ns<br>尚未生成的指标不表示通过；结论以原始报告及第33/34步为准。</div>
<h2>文件结构与作用</h2><table><tr><th>路径（可点击）</th><th>作用</th></tr>%s</table>
<h2>开始或继续完整流程</h2><p>在服务器终端运行；已有进度会从同一工程继续。长任务使用tmux，运行中不要再启动另一份任务。</p><pre>%s</pre>
<h2>从哪里读结果</h2><ul>%s</ul><p>压缩的时间原文可在终端用gzip -cd 文件 | less查看；JSON和Markdown可用文本编辑器打开。结果尚未生成时，链接对应文件可能不存在。</p>
<h2>Lab 4、历史与清理</h2><p>lab4完整保留原始教学工程和资料。history保留历史有效结果，旧绝对路径代表当时来源，不作为本轮输入。本轮从RTL开始，不导入旧检查点。PDK和授权SRAM继续读取/lec中的课程资料。</p>
<p>下载校验后可在终端使用eda.sh clean --work "$EDA_WORK" --dry-run预览，去掉--dry-run清理重复交付包。报告、日志、清单、中间文件、检查点和最终GDS/SDF/SPEF保留。详细命令见docs中的操作指南。</p>
<p>本流程是单TT教学实现；不代表已完成独立晶圆厂DRC/LVS、IR/EM/ESD签核或SDF回标仿真。</p></html>''' % tuple(
        [html.escape(str(x)) for x in [source.get('git_commit', '未知'), work, progress, error, setup, hold]]
        + [html_rows, html.escape(command), html_links])
    write(root / 'README.html', page)
    print(json.dumps({'workspace': str(root), 'deploy': str(deploy), 'work': str(work), 'readme': str(root / 'README.html')}, ensure_ascii=False))
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path.home() / 'Desktop/fullstack_chipdesign')
    args = parser.parse_args()
    initialize(args.root, Path(__file__).resolve().parents[2])


if __name__ == '__main__':
    main()
