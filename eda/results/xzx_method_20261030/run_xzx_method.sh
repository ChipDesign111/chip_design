#!/usr/bin/env bash
set -u
set -o pipefail
source /etc/profile.d/eda.sh
BASE=/home/s2400012831/Desktop/fullstack_chipdesign/uploads/20261029_171412_postsim_2714f61/postsim
ROOT=$BASE/xzx_method_20261030
IN=$BASE/inputs
rm -rf "$ROOT"
mkdir -p "$ROOT/build" "$ROOT/build_zero"
cp "$IN/tb_xzx_method.sv" "$ROOT/tb_postsim.sv"
cp "$IN/netlist.v" "$ROOT/netlist.v"
cp "$IN/timing.sdf" "$ROOT/timing.sdf"
cp "$IN/sram_period_adapter.v" "$ROOT/sram_period_adapter.v"
COMMON=(vcs -full64 -sverilog -j4 -negdelay +neg_tchk +define+NTC+RECREM +sdfverbose -timescale=1ns/1ps -top tb_postsim -o "$ROOT/build/simv" "$ROOT/tb_postsim.sv" "$ROOT/netlist.v" -v /lec/pdk/tsmc180/tcb018gbwp7t_290a/TSMCHOME/digital/Front_End/verilog/tcb018gbwp7t_270a/tcb018gbwp7t.v -v /lec/pdk/tsmc180/tpd018nv_280a/TSMCHOME/digital/Front_End/verilog/tpd018nv_260a/tpd018nv.v -v "$ROOT/sram_period_adapter.v")
"${COMMON[@]}" >"$ROOT/build/compile.log" 2>&1
code=$?
printf '%s\n' "$code" >"$ROOT/build/compile.exit"
if [ "$code" -ne 0 ]; then exit "$code"; fi
ZERO=(vcs -full64 -sverilog -j4 -negdelay +neg_tchk +define+NTC+RECREM +sdfverbose -timescale=1ns/1ps -top tb_postsim -o "$ROOT/build_zero/simv" "$ROOT/tb_postsim.sv" "$ROOT/netlist.v" -v /lec/pdk/tsmc180/tcb018gbwp7t_290a/TSMCHOME/digital/Front_End/verilog/tcb018gbwp7t_270a/tcb018gbwp7t.v -v /lec/pdk/tsmc180/tpd018nv_280a/TSMCHOME/digital/Front_End/verilog/tpd018nv_260a/tpd018nv.v -v "$ROOT/sram_period_adapter.v" +notimingcheck +delay_mode_zero +define+NO_SDF)
"${ZERO[@]}" >"$ROOT/build_zero/compile.log" 2>&1
code=$?
printf '%s\n' "$code" >"$ROOT/build_zero/compile.exit"
if [ "$code" -ne 0 ]; then exit "$code"; fi
printf '%s\n' 'sdf_max 2000' 'sdf_firmware_1 250' 'sdf_firmware_10001 1650' 'sdf_firmware_10002 3050' 'sdf_firmware_10003 4450' 'sdf_firmware_10004 5850' 'sdf_firmware_10005 7250' 'sdf_firmware_10006 8650' 'sdf_firmware_10007 10050' 'sdf_firmware_10008 11450' 'sdf_firmware_10009 12850' 'sdf_firmware_10010 14250' 'sdf_firmware_10011 15650' 'sdf_firmware_3 17050' 'sdf_firmware_5 18450' 'sdf_firmware_7 19850' >"$ROOT/cases.txt"
while read -r mode offset; do
  mkdir -p "$ROOT/$mode"
  fw=firmware.hex
  if [ "$mode" != sdf_max ]; then fw="${mode#sdf_}.hex"; fi
  cp "$BASE/configs/$fw" "$ROOT/$mode/firmware.hex"
  ln -sf "$ROOT/timing.sdf" "$ROOT/$mode/timing.sdf"
  (cd "$ROOT/$mode" && "$ROOT/build/simv" +RESET_OFFSET_PS="$offset" -l "$ROOT/$mode/simulation.log") >"$ROOT/$mode/stdout.log" 2>&1
  printf '%s\n' "$?" >"$ROOT/$mode/exit.code"
done <"$ROOT/cases.txt"
mkdir -p "$ROOT/gate_zero"
cp "$BASE/configs/firmware.hex" "$ROOT/gate_zero/firmware.hex"
ln -sf "$ROOT/timing.sdf" "$ROOT/gate_zero/timing.sdf"
(cd "$ROOT/gate_zero" && "$ROOT/build_zero/simv" +RESET_OFFSET_PS=2000 -l "$ROOT/gate_zero/simulation.log") >"$ROOT/gate_zero/stdout.log" 2>&1
printf '%s\n' "$?" >"$ROOT/gate_zero/exit.code"
python3 - "$ROOT" >"$ROOT/summary.txt" <<'PY'
import sys,pathlib,re,json
root=pathlib.Path(sys.argv[1]); out={}
for p in sorted(root.glob('sdf_*/simulation.log'))+[root/'gate_zero/simulation.log']:
 t=p.read_text(errors='replace'); out[p.parent.name]={"exit_code":int((p.parent/'exit.code').read_text()),"functional_pass":'FUNCTIONAL_PASS' in t,"postsim_done":'POSTSIM_DONE' in t,"timing_violations":len(re.findall(r'Timing violation',t,re.I)),"errors":len(re.findall(r'ERROR',t)),"bus_conflicts":len(re.findall(r'BUS CONFLICT',t)),"annotation_errors":len(re.findall(r'SDF.*error|annotation.*error|SDFCOM',t,re.I)),"pass_line":re.findall(r'FUNCTIONAL_PASS[^\n]*',t)[-1:]}
print(json.dumps(out,indent=2))
PY
cat "$ROOT/summary.txt"
