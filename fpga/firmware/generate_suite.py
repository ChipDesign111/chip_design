"""Generate paired HAR/RAW FPGA packages with per-image GDB result checks.

Requires the PyTorch compiler environment. The original HAR image generator
remains usable without PyTorch. No FPGA project or RTL files are modified.
"""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "test/int8"))

BASE = 0x80000000
TAG = BASE + 0x1fe4
STATUS = BASE + 0x1fe0
RAW_CASES = ("full_b1", "full_b2", "full_b3", "full_b4", "tail_b4",
             "k_split_b4", "multi_b2", "wide_b3")


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8", newline="\n")


def readback_words(tensors, reference):
    """Merge tensor bytes into aligned word checks, masking row padding."""
    checks = {}
    for name, tensor in tensors.items():
        width = 1 if tensor.get("dtype", "int8") == "int8" else 4
        if len(reference[name]) != tensor["shape"][0]:
            raise ValueError("Incorrect reference batch: " + name)
        for row, values in enumerate(reference[name]):
            if len(values) != tensor["shape"][1]:
                raise ValueError("Incorrect reference width: " + name)
            start = tensor["address"] + row * tensor["stride"]
            data = b"".join((v & ((1 << (8*width))-1)).to_bytes(width, "little") for v in values)
            if not BASE <= start < start+len(data) <= BASE+0x1fc0:
                raise ValueError("Tensor outside data SRAM: " + name)
            for i, value in enumerate(data):
                address, shift = (start+i) & -4, ((start+i) & 3)*8
                expected, mask = checks.get(address, (0, 0))
                if mask & (255 << shift) and (expected >> shift) & 255 != value:
                    raise ValueError("Conflicting tensor aliases")
                checks[address] = (expected | (value << shift), mask | (255 << shift))
    return [dict(address=address, expected=value, mask=mask)
            for address, (value, mask) in sorted(checks.items())]


def write_board_files(directory, info, checks):
    image = bytearray((directory / "firmware.bin").read_bytes())
    if len(image) != 8192 or image[TAG-BASE:TAG-BASE+4] != bytes(4):
        raise ValueError("Expected 8 KiB image with unused board tag word")
    # This reserved word distinguishes otherwise numerically identical CPU/NPU
    # packages during board readback. It changes no executable instruction.
    tag = int.from_bytes(hashlib.sha256(image).digest()[:4], "little")
    struct.pack_into("<I", image, TAG-BASE, tag)
    (directory / "firmware.bin").write_bytes(image)
    (directory / "firmware.hex").write_text(
        "".join("%08x\n" % w for w in struct.unpack("<2048I", image)), encoding="ascii", newline="\n")
    info.update(schema=1, image_bytes=8192, status_address=STATUS, pass_value=0xc0dec0de,
                fail_value=0xdeadbeef, tag_address=TAG, tag_value=tag,
                checks=checks, board_tested=False,
                cycle_counter_address=0x10038,
                timing="Hardware first non-debug fetch through PASS/FAIL, including firmware checks; not BEGIN/END cycles")
    lines = ["# Generated; source from the fpga directory after running and halting this image.",
             "define soc-check-result", "  set $soc_check_errors = 0",
             "  if *(unsigned int *)0x%08x != 0x%08x" % (TAG, tag),
             '    printf "FPGA_CHECK_FAIL: wrong image tag for %s\\n"' % info["name"],
             "    set $soc_check_errors = $soc_check_errors + 1", "  else",
             "    if *(unsigned int *)0x%08x != 0xc0dec0de" % STATUS,
             '      printf "FPGA_CHECK_FAIL: firmware status is not PASS\\n"',
             "      set $soc_check_errors = $soc_check_errors + 1", "    else"]
    for check in checks:
        lines += ["      set $soc_actual = *(unsigned int *)0x%08x & 0x%08x" % (check["address"], check["mask"]),
                  "      if $soc_actual != 0x%08x" % check["expected"],
                  '        printf "Mismatch at 0x%08x: got=0x%%08x expected=0x%08x mask=0x%08x\\n", $soc_actual'
                  % (check["address"], check["expected"], check["mask"]),
                  "        set $soc_check_errors = $soc_check_errors + 1", "      end"]
    lines += ["    end", "  end", "  if $soc_check_errors == 0",
              '    printf "FPGA_CHECK_PASS %s checked_words=%d full_soc_cycles=%%u\\n", *(unsigned int *)0x00010038'
              % (info["name"], len(checks)), "  else",
              '    printf "FPGA_CHECK_FAIL errors=%d\\n", $soc_check_errors', "  end", "end", "",
              "document soc-check-result", "Check the image tag, PASS status and all input/intermediate/output tensor words.",
              "Read $soc_check_errors for a machine-readable failure count. CPU must be halted.", "end", ""]
    (directory / "check.gdb").write_text("\n".join(lines), encoding="ascii", newline="\n")
    info["files_sha256"] = {p.name: sha(p) for p in sorted(directory.iterdir()) if p.is_file() and p.name != "board_manifest.json"}
    write_json(directory / "board_manifest.json", info)
    return dict(name=info["name"], family=info["family"], backend=info["backend"],
                path=directory.name, batch=info["batch"], code_bytes=info["code_bytes"],
                firmware_sha256=sha(directory / "firmware.bin"),
                board_manifest_sha256=sha(directory / "board_manifest.json"))


def generate(output):
    # Heavy dependencies are needed only for generation, not image/dump checking.
    from compiler import compile_model
    from compiler.runtime import source_hashes
    from har_benchmark import build as build_har
    from raw_batch_cases import fixtures

    output.mkdir(parents=True, exist_ok=True)
    images = []
    for batch in range(1, 5):
        for backend in ("cpu", "npu"):
            name = "har_b%d_%s" % (batch, backend)
            directory = output / name
            meta = build_har(directory, seed=10000, batch=batch, backend=backend)
            image = (directory / "firmware.bin").read_bytes()
            checks = [dict(address=BASE+0x1d00+sample*64+offset,
                           expected=struct.unpack_from("<I", image, 0x1c00+sample*64+offset)[0], mask=0xffffffff)
                      for sample in range(batch) for offset in range(0, 60, 4)]
            info = dict(name=name, family="har", backend=backend, batch=batch, seed=10000,
                        code_bytes=meta["code_bytes"], input_shape=[batch, 64], output_shape=[batch, 6],
                        firmware_selfcheck=True, npu_core_starts=int(backend == "npu"), npu_batch=batch,
                        description="Original HAR 64->32->6; INT22 wrap and all hidden/scores/classes checked on CPU")
            images.append(write_board_files(directory, info, checks))
    selected = {name: (model, x, calibration) for name, model, x, calibration in fixtures() if name in RAW_CASES}
    for case in RAW_CASES:
        model, x, calibration = selected[case]
        reference = None
        for backend in ("cpu", "raw"):
            name = "raw_%s_%s" % (case, backend)
            directory = output / name
            package = compile_model(model, x, calibration, force_cpu=backend == "cpu")
            values = package.write(directory, x)
            expected = {key: value.tolist() for key, value in values.items()}
            if reference is not None and reference != expected:
                raise ValueError("CPU/RAW reference differs: " + case)
            reference = expected
            meta = package.metadata
            info = dict(name=name, family="raw", backend=backend, case=case,
                        batch=meta["input_shape"][0], input_shape=meta["input_shape"],
                        output_shape=meta["tensors"][meta["output"]]["shape"],
                        code_bytes=meta["code_bytes"], halt_pc=package.program.labels["halt"],
                        firmware_selfcheck=False, npu_core_starts=meta["npu_core_starts"],
                        npu_batch=meta["npu_batch"], batch_weight_reuse=meta["batch_weight_reuse"],
                        description="Calibrated PyTorch INT8 graph; all tensors checked externally by check.gdb")
            images.append(write_board_files(directory, info, readback_words(meta["tensors"], expected)))
    sources = source_hashes()
    sources.update({p.relative_to(ROOT).as_posix(): sha(p) for p in
                    [HERE / "generate_suite.py", ROOT / "test/int8/raw_batch_cases.py",
                     ROOT / "test/int8/har_benchmark.py", ROOT / "test/int8/firmware.py",
                     ROOT / "test/int8/run.py", ROOT / "test/int8/har_uci24.json",
                     ROOT / "model/reference/tile_layout.py", ROOT / "model/export/weights_int8.npz",
                     ROOT / "model/export/quant_params.json"]})
    write_json(output / "suite_manifest.json", dict(schema=1, generated_for="current INT22/16-MAC RTL",
                board_tested=False, image_count=len(images), source_sha256=sources, images=images,
                board_timing="Read 0x00010038 after PASS. CPU/NPU use the same arithmetic and outputs.",
                raw_pass_meaning="Completion only until check.gdb validates all tensors"))
    print("Generated %d paired FPGA packages in %s" % (len(images), output), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=HERE / "suite")
    args = parser.parse_args()
    generate(args.output_dir.resolve())


if __name__ == "__main__":
    main()
