import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess

base = Path('/home/s2400012831/Desktop/fullstack_chipdesign/uploads/20261029_171412_postsim_2714f61')
root = base / 'postsim/xzx_method_verified_20261030'
root.mkdir(exist_ok=False)
inputs = base / 'postsim/inputs'
for name, src in {'tb_postsim.sv': inputs/'tb_xzx_method.sv', 'netlist.v': inputs/'netlist.v', 'timing.sdf': inputs/'timing.sdf', 'sram_period_adapter.v': inputs/'sram_period_adapter.v'}.items():
    shutil.copyfile(src, root/name)
manifest = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in root.iterdir() if p.is_file()}
(root/'manifest.json').write_text(json.dumps(manifest, indent=2))

def execute(cmd, cwd, log):
    (cwd/(log+'.command.json')).write_text(json.dumps(cmd, indent=2))
    with (cwd/log).open('w') as f:
        code = subprocess.call(cmd, cwd=cwd, stdout=f, stderr=subprocess.STDOUT)
    (cwd/(log+'.exit.json')).write_text(json.dumps({'exit_code': code}))
    return code

build = root/'build'; build.mkdir()
shutil.copyfile(root/'timing.sdf', build/'timing.sdf')
cmd = ['vcs', '-full64', '-sverilog', '-j4', '-negdelay', '+neg_tchk', '+define+NTC+RECREM', '+sdfverbose', '-timescale=1ns/1ps', '-top', 'tb_postsim', '-o', str(build/'simv'), str(root/'tb_postsim.sv'), str(root/'netlist.v')]
for p in ['/lec/pdk/tsmc180/tcb018gbwp7t_290a/TSMCHOME/digital/Front_End/verilog/tcb018gbwp7t_270a/tcb018gbwp7t.v', '/lec/pdk/tsmc180/tpd018nv_280a/TSMCHOME/digital/Front_End/verilog/tpd018nv_260a/tpd018nv.v', str(root/'sram_period_adapter.v')]:
    cmd += ['-v', p]
assert execute(cmd, build, 'compile.log') == 0
zero = root/'build_zero'; zero.mkdir()
zc = cmd.copy(); zc[zc.index('-o')+1] = str(zero/'simv')
zc += ['+notimingcheck', '+delay_mode_zero', '+define+NO_SDF']
assert execute(zc, zero, 'compile.log') == 0
cases = [('sdf_max', base/'configs/firmware.hex', 2000)]
cases += [('sdf_'+p.stem, p, 250+1400*i) for i,p in enumerate(sorted((base/'configs').glob('firmware_*.hex')))]
cases += [('gate_zero', base/'configs/firmware.hex', 2000)]
results = {}
for name, fw, offset in cases:
    run = root/name; run.mkdir()
    shutil.copyfile(fw, run/'firmware.hex')
    (run/'timing.sdf').symlink_to(root/'timing.sdf')
    executable = zero/'simv' if name=='gate_zero' else build/'simv'
    code = execute([str(executable), '+RESET_OFFSET_PS='+str(offset)], run, 'simulation.log')
    text = (run/'simulation.log').read_text(errors='replace')
    phase='initial'; counts={'initial':0,'active':0,'after_reset':0}
    for line in text.splitlines():
        if line.startswith('ACTIVE_START'): phase='active'
        if line.startswith('RESET_ASSERT'): phase='after_reset'
        if 'Timing violation' in line: counts[phase]+=1
    results[name] = {'exit_code':code,'functional_pass':'FUNCTIONAL_PASS' in text,'done':'POSTSIM_DONE' in text,'timing':counts,'bus_conflicts':len(re.findall('BUS CONFLICT',text)), 'pass_lines':re.findall(r'FUNCTIONAL_PASS[^\n]*',text), 'reset_offset_ps':offset}
    (root/'results.json').write_text(json.dumps(results,indent=2))
    print(name,json.dumps(results[name]),flush=True)
(root/'DONE').write_text('completed\n')
