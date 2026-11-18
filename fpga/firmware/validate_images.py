"""Check FPGA image identities, optionally validate an SRAM dump or run full SoC.

Image/dump checks use only the Python standard library. Simulation uses the
existing CPU/AXI/SRAM testbenches and ModelSim, without changing any RTL.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import struct
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(HERE))
from generate_suite import BASE, readback_words


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def save(path, value):
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8", newline="\n")


def check_image(hex_path, bin_path):
    lines = hex_path.read_text(encoding="ascii").splitlines()
    if len(lines) != 2048 or any(not re.fullmatch(r"[0-9a-fA-F]{8}", line) for line in lines):
        raise ValueError("Expected 2048 complete 32-bit words: " + str(hex_path))
    image = struct.pack("<2048I", *(int(line, 16) for line in lines))
    if bin_path.read_bytes() != image:
        raise ValueError("Hex/binary mismatch: " + str(bin_path))
    return image


def check_sources(sources):
    for name, digest in sources.items():
        if sha(ROOT / name) != digest:
            raise ValueError("Source changed since generation: " + name)


def check_dump(directory, dump):
    meta = read_json(directory / "board_manifest.json")
    if len(dump) != 8192:
        raise ValueError("SRAM dump must be exactly 8192 bytes")
    checks = [dict(address=meta["tag_address"], expected=meta["tag_value"], mask=0xffffffff),
              dict(address=meta["status_address"], expected=meta["pass_value"], mask=0xffffffff)] + meta["checks"]
    for check in checks:
        actual = struct.unpack_from("<I", dump, check["address"]-BASE)[0] & check["mask"]
        if actual != check["expected"]:
            raise ValueError("%s: SRAM 0x%08x got 0x%08x expected 0x%08x (mask 0x%08x)" %
                             (meta["name"], check["address"], actual, check["expected"], check["mask"]))
    return dict(name=meta["name"], passed=True, checked_words=len(meta["checks"]))


def check_suite(suite):
    manifest = read_json(suite / "suite_manifest.json")
    check_sources(manifest["source_sha256"])
    pairs = {}
    for item in manifest["images"]:
        directory = suite / item["path"]
        if sha(directory / "board_manifest.json") != item["board_manifest_sha256"]:
            raise ValueError("Board manifest identity mismatch: " + item["name"])
        meta = read_json(directory / "board_manifest.json")
        for name, digest in meta["files_sha256"].items():
            if sha(directory / name) != digest:
                raise ValueError("Package file changed: " + str(directory / name))
        image = check_image(directory / "firmware.hex", directory / "firmware.bin")
        if sha(directory / "firmware.bin") != item["firmware_sha256"]:
            raise ValueError("Image identity mismatch: " + item["name"])
        if struct.unpack_from("<I", image, meta["tag_address"]-BASE)[0] != meta["tag_value"]:
            raise ValueError("Invalid board image tag")
        if meta["family"] == "raw":
            compiled = read_json(directory / "manifest.json")
            if hashlib.sha256(image[:compiled["code_bytes"]]).hexdigest() != compiled["code_sha256"]:
                raise ValueError("Compiled instructions changed")
            reference = read_json(directory / "reference.json")
            checks = readback_words(compiled["tensors"], reference)
            key = meta["case"]
            if key in pairs and pairs[key] != reference:
                raise ValueError("CPU/RAW tensors differ: " + key)
            pairs[key] = reference
        else:
            checks = [dict(address=BASE+0x1d00+s*64+at,
                           expected=struct.unpack_from("<I", image, 0x1c00+s*64+at)[0], mask=0xffffffff)
                      for s in range(meta["batch"]) for at in range(0, 60, 4)]
        if checks != meta["checks"]:
            raise ValueError("Readback checks do not match reference: " + meta["name"])
        if not meta["code_bytes"] or meta["code_bytes"] >= 0x1fc0:
            raise ValueError("Invalid code size")
    if len(manifest["images"]) != manifest["image_count"]:
        raise ValueError("Incorrect suite count")
    return manifest


def check_legacy():
    manifest = read_json(HERE / "image_manifest.json")
    check_sources(manifest["generator"]["source_sha256"])
    check_sources(manifest["rtl_source_sha256"])
    for item in manifest["images"]:
        check_image(HERE / item["file"], HERE / item["binary_file"])
        if sha(HERE / item["file"]) != item["sha256"] or sha(HERE / item["binary_file"]) != item["binary_sha256"]:
            raise ValueError("HAR image hash mismatch: " + item["file"])
    if (HERE / manifest["canonical"]).read_bytes() != (HERE / manifest["canonical_alias"]).read_bytes():
        raise ValueError("Canonical HAR image differs from UCI 00")
    check_image(HERE / manifest["canonical"], HERE / manifest["canonical_binary"])
    if sha(HERE / manifest["canonical_binary"]) != manifest["canonical_binary_sha256"]:
        raise ValueError("Canonical binary identity mismatch")
    return manifest


def execute(command, directory, log):
    result = subprocess.run(command, cwd=directory, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=300)
    output = result.stdout.decode(errors="replace")
    (directory / log).write_text(output, encoding="utf-8")
    if result.returncode or re.search(r"FATAL:|# \*\* (?:Fatal|Error):|TIMEOUT", output):
        raise RuntimeError("%s failed: %s" % (log, output[-4000:]))
    return output


def simulate_all(suite, suite_meta, legacy, out, vsim):
    from compiler.sim import simulate
    out.mkdir(parents=True, exist_ok=False)
    report = dict(status="RUNNING", board_tested=False, cases=[],
                  scope="Actual emitted FPGA images on unchanged full CPU/AXI/SRAM RTL; not FPGA timing or board validation",
                  source_sha256=suite_meta["source_sha256"],
                  legacy_manifest_sha256=sha(HERE / "image_manifest.json"),
                  suite_manifest_sha256=sha(suite / "suite_manifest.json"))
    build = out / "build"
    build.mkdir()
    sources = []
    for line in (ROOT / "rtl/filelist.f").read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("//"):
            sources.append("+incdir+"+(ROOT/line[8:]).as_posix() if line.startswith("+incdir+") else (ROOT/line).as_posix())
    for name in ("tb_soc", "tb_har_benchmark"):
        template = (ROOT / ("test/int8/"+name+".sv")).read_text()
        marker = '        $display("INT8_SOC PASS' if name == "tb_soc" else "        $finish;"
        template = template.replace(marker, '        $display("FPGA_FULL_CYCLES hw_soc_cycles=%0d",dut.i_bootram.soc_cycles);\n'+marker)
        target = build / (name+".sv")
        target.write_text(template)
        sources.append(target.as_posix())
    (build / "soc.f").write_text("\n".join(sources)+"\n")
    (build / "compile.do").write_text("onerror {quit -code 1}\nvlib work\nvmap work work\nvlog -sv -f soc.f\nquit -code 0\n")
    try:
        execute([vsim, "-c", "-do", "do compile.do"], build, "compile.log")
        todo = [(item["file"], HERE / item["file"], "tb_soc", "", "INT8_SOC PASS", item["sha256"])
                for item in legacy["images"]]
        for item in suite_meta["images"]:
            if item["family"] == "har":
                directory = suite / item["path"]
                meta = read_json(directory / "board_manifest.json")
                todo.append((item["name"], directory / "firmware.hex", "tb_har_benchmark",
                             " +TILES=%d +BATCH=%d" % (meta["npu_core_starts"], meta["batch"]),
                             "HAR_BENCH_PASS", sha(directory / "firmware.hex")))
        for name, firmware, top, args, expected, digest in todo:
            directory = out / Path(name).stem
            directory.mkdir()
            shutil.copyfile(firmware, directory / "firmware.hex")
            if top == "tb_har_benchmark":
                for filename in ("bench_layout.hex", "expected.hex", "phase_pcs.hex", "dma_ranges.hex"):
                    shutil.copyfile(firmware.parent / filename, directory / filename)
            (directory / "run.do").write_text(
                "onerror {quit -code 1}\nonbreak {resume}\nvmap work {%s}\nvsim -suppress 12110 -novopt -onfinish stop work.%s%s\nrun -all\nset status [examine -radix hex /%s/magic]\nif {![string equal -nocase $status c0dec0de]} {quit -code 3}\nquit -code 0\n"
                % ((build / "work").as_posix(), top, args, top))
            output = execute([vsim, "-c", "-do", "do run.do"], directory, "soc.log")
            match = re.search(re.escape(expected)+r" ([^\r\n]+)", output)
            full = re.search(r"FPGA_FULL_CYCLES hw_soc_cycles=(\d+)", output)
            if not match or not full or sha(directory / "firmware.hex") != digest:
                raise RuntimeError("Missing PASS/cycles or changed image: " + name)
            entry = dict(name=name, passed=True, firmware_hex_sha256=digest,
                         hw_soc_cycles=int(full[1]), counters={k: int(v) for k, v in re.findall(r"(\w+)=(\d+)", match[1])},
                         log_sha256=sha(directory / "soc.log"))
            report["cases"].append(entry)
            save(out / "validation.json", report)
            print("FPGA firmware %s: PASS full_cycles=%d" % (name, entry["hw_soc_cycles"]), flush=True)
        for item in suite_meta["images"]:
            if item["family"] == "raw":
                directory = out / item["name"]
                shutil.copytree(suite / item["path"], directory)
                result = simulate(directory, vsim)
                report["cases"].append(dict(name=item["name"], passed=True,
                          firmware_sha256=item["firmware_sha256"], benchmark_cycles=result["cycles"],
                          counters=result["counters"], simulation_sha256=sha(directory / "simulation.json")))
                save(out / "validation.json", report)
                print("FPGA firmware %s: PASS benchmark_cycles=%d; all tensors read back" % (item["name"], result["cycles"]), flush=True)
        check_sources(suite_meta["source_sha256"])
        report["status"] = "PASS"
    except Exception as error:
        report.update(status="FAIL", error=str(error))
        raise
    finally:
        save(out / "validation.json", report)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--suite", type=Path, default=HERE / "suite")
    parser.add_argument("--package", type=Path, help="Package to check against --dump")
    parser.add_argument("--dump", type=Path, help="8 KiB binary SRAM capture, starting at 0x80000000")
    parser.add_argument("--simulate", action="store_true")
    parser.add_argument("--out", type=Path, help="Fresh simulation output directory (use test/int8/runs/)")
    parser.add_argument("--vsim", default="vsim")
    args = parser.parse_args()
    if args.dump:
        if not args.package:
            parser.error("--dump requires --package")
        # Verify package identities before trusting its readback expectations.
        check_suite(args.package.resolve().parent)
        print(json.dumps(check_dump(args.package, args.dump.read_bytes()), indent=2))
        return
    legacy, suite = check_legacy(), check_suite(args.suite)
    print("FPGA_IMAGE_CHECK_PASS legacy=%d paired=%d; all hex/bin/source/reference hashes match" %
          (legacy["count"], suite["image_count"]), flush=True)
    if args.simulate:
        if not args.out:
            parser.error("--simulate requires --out")
        report = simulate_all(args.suite.resolve(), suite, legacy, args.out.resolve(), args.vsim)
        print("FPGA_SOC_CHECK_PASS images=%d" % len(report["cases"]), flush=True)


if __name__ == "__main__":
    main()
