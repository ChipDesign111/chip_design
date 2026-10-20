"""Simulation execution, diagnostic markers and tool lookup."""
import re,shutil,subprocess,time
from pathlib import Path
from tools.workspace import WORK,ROOT
RESULTS=[]

def execute(name, command, cwd=ROOT, marker=None, timeout=300, env=None):
    start = time.monotonic()
    result = subprocess.run([str(v) for v in command], cwd=cwd, env=env, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=timeout)
    log = WORK / 'logs' / (name + '.log')
    log.parent.mkdir(parents=True, exist_ok=True)
    log.write_text(result.stdout, encoding='utf-8')
    ok = result.returncode == 0 and (marker is None or marker in result.stdout)
    if re.search('(?m)^.*(?:FATAL:|FAIL case=|TIMEOUT after|# \\*\\* Error:)', result.stdout):
        ok = False
    cycles = re.search('self-check OK after (\\d+) cycles', result.stdout)
    record = dict(test=name, pass_=ok, seconds=round(time.monotonic() - start, 3), log=str(log.relative_to(ROOT)), exit_code=result.returncode)
    if cycles:
        record['soc_cycles'] = int(cycles.group(1))
    RESULTS.append(record)
    print(f"{name}: {('PASS' if ok else 'FAIL')} ({record['seconds']}s)", flush=True)
    if not ok:
        print(result.stdout[-12000:])
        raise RuntimeError(f'{name} failed; see {log}')
    return result.stdout

def tool(name, override=None):
    found = override or shutil.which(name)
    if not found:
        raise RuntimeError(f'{name} not found; add it to PATH or use the explicit CLI option')
    return str(Path(found).resolve())
