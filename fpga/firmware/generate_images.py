"""Generate complete 8 KiB self-checking FPGA images."""
import argparse
import hashlib
import json
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
TEST_DIR = ROOT / "test" / "int8"
sys.path.insert(0, str(TEST_DIR))

from firmware import DEFAULT_MODE, build  # noqa: E402
from run import make_case  # noqa: E402


RANDOM_SEEDS = tuple(range(32))
UCI_SEEDS = tuple(range(10000, 10006))


def single_image(output_dir, seed, name, kind):
    memory = make_case(seed)
    batch = memory[0x1F08 // 4]
    with tempfile.TemporaryDirectory(prefix="int8_fpga_image_") as temporary:
        generated = Path(temporary)
        build(generated, seed)
        text = (generated / "firmware.hex").read_text(encoding="ascii")
        metadata = json.loads((generated / "firmware_meta.json").read_text())

    lines = text.splitlines()
    if len(lines) != 2048 or any(len(line) != 8 for line in lines):
        raise RuntimeError(f"{name}: expected 2048 eight-digit hex words")

    target = output_dir / name
    target.write_text(text, encoding="ascii", newline="\n")
    digest = hashlib.sha256(target.read_bytes()).hexdigest()
    return {
        "file": name,
        "kind": kind,
        "seed": seed,
        "batch": batch,
        "firmware_mode": metadata["mode"],
        "code_bytes": metadata["code_bytes"],
        "sha256": digest,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, default=HERE)
    args = parser.parse_args()
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    images = []

    for seed in RANDOM_SEEDS:
        batch = make_case(seed)[0x1F08 // 4]
        images.append(
            single_image(
                output_dir,
                seed,
                f"int8_random_{seed:02d}_batch{batch}.hex",
                "random",
            )
        )

    uci_images = []
    for group, seed in enumerate(UCI_SEEDS):
        item = single_image(
            output_dir,
            seed,
            f"int8_uci_{group:02d}_batch4.hex",
            "uci",
        )
        images.append(item)
        uci_images.append(item)

    canonical = output_dir / "int8_selftest.hex"
    uci_zero = output_dir / "int8_uci_00_batch4.hex"
    # The canonical image is the active firmware input, so it must follow the
    # current RTL even when an older self-test image already exists.
    if canonical.exists():
        if canonical.read_text(encoding="ascii").splitlines() != uci_zero.read_text(
            encoding="ascii"
        ).splitlines():
            print("Refreshing int8_selftest.hex from current UCI group 00")
        else:
            print("int8_selftest.hex already matches current UCI group 00")
    canonical.write_bytes(uci_zero.read_bytes())

    manifest = {
        "format": "2048 x 32-bit hexadecimal words, one word per line",
        "generator": {
            "entrypoint": "fpga/firmware/generate_images.py",
            "firmware_mode": DEFAULT_MODE,
            "source_sha256": {
                name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
                for name in (
                    "fpga/firmware/generate_images.py",
                    "test/int8/firmware.py",
                    "test/int8/assembler.py",
                    "test/int8/run.py",
                    "test/int8/har_uci24.json",
                    "model/reference/tile_layout.py",
                    "model/export/weights_int8.npz",
                    "model/export/quant_params.json",
                )
            },
        },
        "canonical": "int8_selftest.hex",
        "canonical_alias": "int8_uci_00_batch4.hex",
        "canonical_firmware_mode": uci_images[0]["firmware_mode"],
        "canonical_code_bytes": uci_images[0]["code_bytes"],
        "canonical_sha256": hashlib.sha256(canonical.read_bytes()).hexdigest(),
        "count": len(images),
        "images": images,
    }
    partial_fixture = output_dir / "int8_partial_4k.bin"
    if partial_fixture.exists():
        manifest["retained_fixtures"] = [{
            "file": partial_fixture.name,
            "bytes": partial_fixture.stat().st_size,
            "sha256": hashlib.sha256(partial_fixture.read_bytes()).hexdigest(),
            "status": "historical partial image; not regenerated or validated with current firmware",
        }]
    (output_dir / "image_manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )
    print(f"Generated {len(images)} FPGA images in {output_dir}")
    print(f"Canonical image: {canonical}")


if __name__ == "__main__":
    main()
