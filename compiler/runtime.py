"""Reuse the tested RAW/CPU emitters without changing their script entry points."""
from pathlib import Path
import hashlib
import sys

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / 'test/int8'
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from generic_firmware import (BENCHMARK_ADDRESS, BENCHMARK_PHASES, RuntimeAssembler,
                              _cpu_kernel, _marker, build as build_dynamic)
from generic_runtime import BASE, CODE_BYTES, Layer, plan, reference
from optimized_firmware import _full_blocks, build as build_optimized, pack_layer


def source_hashes():
    paths = list((ROOT/'compiler').glob('*.py'))
    paths += [p for p in (ROOT/'rtl').rglob('*') if p.suffix in ('.sv', '.svh', '.v', '.f')]
    paths += [SCRIPTS/name for name in ('assembler.py', 'generic_runtime.py',
               'generic_firmware.py', 'optimized_firmware.py', 'tb_gemv_benchmark.sv')]
    return {p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(paths)}
