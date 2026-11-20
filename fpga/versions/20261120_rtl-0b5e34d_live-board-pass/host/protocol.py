"""Version-one single-slot SRAM mailbox used by the live inference firmware.

Only request_seq and response_seq publish a complete request/result. Host and
CPU own different fields, so a multiword memory access need not be atomic.
"""
from __future__ import annotations

from dataclasses import dataclass
import json
import math
from pathlib import Path
import struct
from typing import Iterable

SRAM_BASE = 0x80000000
SRAM_BYTES = 8192
MAILBOX_BASE = SRAM_BASE + SRAM_BYTES - 64
MAGIC = 0x4C495645
VERSION = 1

MAGIC_OFFSET = 0
VERSION_OFFSET = 4
REQUEST_SEQ = 8
RESPONSE_SEQ = 12
COMMAND = 16
INPUT_BYTES = 20
STATUS = 24
ERROR = 28
CYCLES = 32
EXECUTIONS = 36
ARGMAX = 40
OUTPUT_BYTES = 44
INPUT_ADDRESS = 48
OUTPUT_ADDRESS = 52
PACKAGE_TAG_LOW = 56
PACKAGE_TAG_HIGH = 60
INFER = 1
READY = 1
BUSY = 2
DONE = 3
FAILED = 4


def int8_bytes(values: Iterable[int], expected: int) -> bytes:
    """Reject floats, overflow and wrong lengths rather than wrapping inputs."""
    values = list(values)
    if len(values) != expected:
        raise ValueError(f"Expected {expected} INT8 input values, got {len(values)}")
    result = []
    for value in values:
        # NumPy integer scalars expose __index__; float/bool are not inputs.
        if isinstance(value, bool):
            raise ValueError("Input must contain signed integers, not bool")
        try:
            integer = value.__index__()
        except (AttributeError, TypeError) as error:
            raise ValueError("Input must contain signed INT8 integers") from error
        if not -128 <= integer <= 127:
            raise ValueError(f"INT8 input out of range: {integer}")
        result.append(integer & 255)
    return bytes(result)


def signed_bytes(data: bytes) -> list[int]:
    return list(struct.unpack(f"<{len(data)}b", data))


@dataclass(frozen=True)
class Metadata:
    input_address: int
    input_bytes: int
    input_scale: float
    output_address: int
    output_bytes: int
    output_scale: float
    mailbox_address: int = MAILBOX_BASE
    abi: int = VERSION
    package_tag: str = ""

    def __post_init__(self):
        if self.abi != VERSION or self.mailbox_address != MAILBOX_BASE:
            raise ValueError("Unsupported live-demo mailbox address or ABI")
        if len(self.package_tag) != 16 or any(c not in "0123456789abcdef" for c in self.package_tag):
            raise ValueError("Resident package requires a 64-bit lowercase hex package tag")
        if not 1 <= self.input_bytes <= 1024 or not 1 <= self.output_bytes <= 32:
            raise ValueError("Live demo requires 1..1024 input and 1..32 output bytes, batch one")
        regions = []
        for address, size in ((self.input_address, self.input_bytes),
                              (self.output_address, self.output_bytes)):
            if address % 4 or not SRAM_BASE <= address < MAILBOX_BASE or address + ((size+3)//4)*4 > MAILBOX_BASE:
                raise ValueError("Live input/output must be aligned and inside SRAM below the mailbox")
            regions.append((address, address + ((size+3)//4)*4))
        if max(regions[0][0], regions[1][0]) < min(regions[0][1], regions[1][1]):
            raise ValueError("Live input and output regions overlap")
        if any(not math.isfinite(scale) or scale <= 0 for scale in (self.input_scale, self.output_scale)):
            raise ValueError("Quantization scales must be finite and positive")

    @classmethod
    def from_manifest(cls, manifest: str | Path | dict) -> "Metadata":
        if isinstance(manifest, (str, Path)):
            manifest = json.loads(Path(manifest).read_text(encoding="utf-8"))
        data = manifest["live_demo"]
        fields = {name: data[name] for name in (
            "input_address", "input_bytes", "input_scale", "output_address", "output_bytes", "output_scale")}
        fields.update(mailbox_address=data.get("mailbox_address", MAILBOX_BASE), abi=data.get("abi", VERSION),
                      package_tag=data["package_tag"])
        return cls(**fields)


@dataclass(frozen=True)
class Mailbox:
    magic: int
    version: int
    request_seq: int
    response_seq: int
    command: int
    input_bytes: int
    status: int
    error: int
    cycles: int
    executions: int
    argmax: int
    output_bytes: int
    input_address: int
    output_address: int
    package_tag_low: int
    package_tag_high: int

    @classmethod
    def parse(cls, words: Iterable[int]) -> "Mailbox":
        words = list(words)
        if len(words) != 16:
            raise ValueError("Mailbox read must contain all 16 words")
        return cls(*words)

    def validate_identity(self, metadata: Metadata):
        if self.magic != MAGIC or self.version != VERSION:
            raise RuntimeError("Resident live-demo firmware is not running (mailbox magic/ABI mismatch)")
        if (self.output_bytes, self.input_address, self.output_address) != (
                metadata.output_bytes, metadata.input_address, metadata.output_address):
            raise RuntimeError("Running firmware buffers differ from the selected package")
        if self.package_tag_low | (self.package_tag_high << 32) != int(metadata.package_tag, 16):
            raise RuntimeError("Running model/program package tag differs from the selected package")
