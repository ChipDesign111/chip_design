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

from firmware import build  # noqa: E402
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
    if canonical.exists():
        if canonical.read_text(encoding="ascii").splitlines() != uci_zero.read_text(
            encoding="ascii"
        ).splitlines():
            raise RuntimeError("int8_selftest.hex does not match UCI group 00")
    else:
        canonical.write_bytes(uci_zero.read_bytes())

    manifest = {
        "format": "2048 x 32-bit hexadecimal words, one word per line",
        "canonical": "int8_selftest.hex",
        "canonical_alias": "int8_uci_00_batch4.hex",
        "canonical_sha256": hashlib.sha256(canonical.read_bytes()).hexdigest(),
        "count": len(images),
        "images": images,
    }
    (output_dir / "image_manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )
    print(f"Generated {len(images)} FPGA images in {output_dir}")
    print(f"Canonical image: {canonical}")


if __name__ == "__main__":
    main()
