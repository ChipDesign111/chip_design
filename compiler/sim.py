"""Run an index/ready/data RAW deployment package on the unchanged full SoC."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import struct
import subprocess
import time

from .runtime import BASE, ROOT


def words(path, values):
    path.write_text(''.join('%08x\n' % (v & 0xffffffff) for v in values))


def execute(command, cwd, log, timeout):
    start = time.monotonic()
    result = subprocess.run(command, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=timeout)
    text = result.stdout.decode(errors='replace')
    (cwd/log).write_text(text, encoding='utf-8')
    if result.returncode or re.search(r'FATAL:|# \*\* (?:Fatal|Error):', text):
        raise RuntimeError('%s failed: %s' % (log, text[-4000:]))
    return text, round(time.monotonic()-start, 3)


def simulate(directory, vsim='vsim', timeout=300):
    directory = Path(directory).resolve()
    meta = json.loads((directory/'manifest.json').read_text())
    reference = json.loads((directory/'reference.json').read_text())
    if meta['target'] != 'int22-raw-v1' or meta.get('task_engine'):
        raise ValueError('Package targets a different NPU ABI')
    for name, digest in meta['source_sha256'].items():
        if hashlib.sha256((ROOT/name).read_bytes()).hexdigest() != digest:
            raise ValueError('Source changed after compilation: '+name)
    image = (directory/'firmware.bin').read_bytes()
    if len(image) != 8192 or hashlib.sha256(image[:meta['code_bytes']]).hexdigest() != meta['code_sha256']:
        raise ValueError('Firmware size or code identity mismatch')
    work = directory/('simulation_%d' % time.time_ns())
    work.mkdir()
    (work/'firmware.hex').write_bytes((directory/'firmware.hex').read_bytes())
    expected = bytearray(image)
    layout = []
    read_addresses = set()
    for name, tensor in meta['tensors'].items():
        width = 1 if tensor.get('dtype', 'int8') == 'int8' else 4
        for row, values in enumerate(reference[name]):
            start = tensor['address']+row*tensor['stride']
            data = b''.join((v & ((1 << (width*8))-1)).to_bytes(width, 'little') for v in values)
            expected[start-BASE:start-BASE+len(data)] = data
            read_addresses.update(range(start & -4, (start+len(data)+3) & -4, 4))
            if name != meta['input']:
                layout += [start, start+len(data), 0, 0]
    # Integer compatibility images keep their original post-END self-checks.
    golden = meta.get('golden_ranges', [])
    for i, pair in enumerate(golden):
        layout[i*4+2:i*4+4] = pair
    ranges = len(layout)//4
    if not ranges:
        raise ValueError('No computed outputs to validate')
    limit = max(32, ranges)
    words(work/'bench_layout.hex', [ranges]+layout+[0]*(4*limit-len(layout)))
    words(work/'expected.hex', struct.unpack('<2048I', expected))
    phase_pcs = meta.get('phase_pcs', {})
    phases = ('setup', 'input_pack', 'weight_pack', 'npu_wait', 'read_reduce', 'postprocess', 'cpu_mac')
    words(work/'phase_pcs.hex', [phase_pcs.get(name, 0) for name in phases])
    dma = meta['dma_ranges']
    if len(dma) > 32:
        raise ValueError('Too many weight source ranges for the monitor')
    values = [len(dma)]+[v for pair in dma for v in pair]
    words(work/'dma_ranges.hex', values+[0]*(65-len(values)))
    template = (ROOT/'test/int8/tb_gemv_benchmark.sv').read_text()
    template = template.replace('layout[0:128]', 'layout[0:%d]' % (4*limit))
    template = template.replace('layout[0]>32', 'layout[0]>%d' % limit)
    read_task = '''
    reg [31:0] observed;
    integer result_fd;
    task sba_read(input reg [31:0] address,output reg [31:0] value);
        integer timeout;
        begin
            @(negedge clk);load_req=1;load_we=0;load_addr=address;load_be=15;timeout=0;
            @(posedge clk);
            while(!dut.dm_master_gnt && timeout<1000) begin @(posedge clk);timeout=timeout+1;end
            if(timeout>=1000) $fatal(1,"SBA read grant timeout");
            @(negedge clk);load_req=0;timeout=0;
            while(!dut.dm_master_r_valid && timeout<1000) begin @(posedge clk);timeout=timeout+1;end
            if(timeout>=1000) $fatal(1,"SBA read response timeout");
            value=dut.dm_master_r_rdata;
            @(negedge clk);
        end
    endtask
'''
    template = template.replace('    initial begin', read_task+'\n    initial begin')
    reads = ['        result_fd=$fopen("actual_words.hex","w");',
             '        if(!result_fd) $fatal(1,"Cannot open readback file");']
    for address in sorted(read_addresses):
        reads.append('        sba_read(32\'h%08x,observed);$fdisplay(result_fd,"%%08x",observed);' % address)
    reads += ['        $fclose(result_fd);']
    template = template.replace('        $finish;', '\n'.join(reads)+'\n        $finish;')
    (work/'tb_compiled_raw.sv').write_text(template)
    sources = []
    for line in (ROOT/'rtl/filelist.f').read_text().splitlines():
        line = line.strip()
        if line and not line.startswith('//'):
            sources.append('+incdir+'+(ROOT/line[8:]).as_posix() if line.startswith('+incdir+') else (ROOT/line).as_posix())
    sources.append((work/'tb_compiled_raw.sv').as_posix())
    (work/'soc.f').write_text('\n'.join(sources)+'\n')
    (work/'run.do').write_text('onerror {quit -code 1}\nonbreak {resume}\nvlib work\nvmap work work\nvlog -sv -f soc.f\nvsim -suppress 12110 -novopt -onfinish stop work.tb_gemv_benchmark +TILES=%d +BATCH=%d\nrun -all\nset status [examine -radix hex /tb_gemv_benchmark/magic]\nif {![string equal -nocase $status c0dec0de]} {quit -code 3}\nquit -code 0\n' % (meta['npu_core_starts'], meta.get('npu_batch', 1)))
    text, seconds = execute([vsim, '-c', '-do', 'do run.do'], work, 'soc.log', timeout)
    match = re.search(r'GEMV_BENCH_PASS ([^\r\n]+)', text)
    if not match:
        raise RuntimeError('Missing genuine compiled RAW SoC PASS')
    counters = {k: int(v) for k, v in re.findall(r'(\w+)=(\d+)', match[1])}
    observed = [int(v, 16) for v in (work/'actual_words.hex').read_text().splitlines()]
    if len(observed) != len(read_addresses):
        raise RuntimeError('Incomplete SBA readback')
    readback = dict(zip(sorted(read_addresses), observed))
    actual = {}
    for name, tensor in meta['tensors'].items():
        width = 1 if tensor.get('dtype', 'int8') == 'int8' else 4
        rows = []
        for row in range(tensor['shape'][0]):
            start = tensor['address']+row*tensor['stride']
            data = bytes((readback[at & -4] >> ((at & 3)*8)) & 255
                         for at in range(start, start+tensor['shape'][1]*width))
            rows.append([int.from_bytes(data[i:i+width], 'little', signed=True) for i in range(0, len(data), width)])
        if rows != reference[name]:
            raise RuntimeError('SBA tensor mismatch: '+name)
        actual[name] = rows
    result = dict(passed=True, cycles=counters['cycles'], counters=counters, elapsed_seconds=seconds,
                  firmware_sha256=hashlib.sha256(image).hexdigest(), work=str(work),
                  scope='Unchanged full SoC; accepted BEGIN/END stores; all tensor outputs checked before END and read back by SBA')
    (directory/'actual_output.json').write_text(json.dumps(dict(output=meta['output'], values=actual[meta['output']], tensors=actual), indent=2)+'\n')
    (directory/'simulation.json').write_text(json.dumps(result, indent=2)+'\n')
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('package', type=Path)
    parser.add_argument('--vsim', default='vsim')
    args = parser.parse_args()
    print(json.dumps(simulate(args.package, args.vsim), indent=2))


if __name__ == '__main__':
    main()
