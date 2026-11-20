"""Repeated input/result exchange with resident CPU firmware over JTAG SBA.

This module never computes the displayed FPGA result on the PC. Its replay CLI
accepts real INT8 vectors or quantizes float features with the compiled scale.
"""
from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
import json
import math
from pathlib import Path
import threading
import time
from typing import Iterable

from . import protocol as p
from .transport import MemoryTransport, OpenOCDTransport, read_bytes, write_bytes


class DeviceError(RuntimeError):
    def __init__(self, sequence: int, code: int):
        self.sequence, self.code = sequence, code
        super().__init__(f"FPGA request {sequence} failed with firmware error {code}; no output accepted")


@dataclass(frozen=True)
class InferenceResult:
    sequence: int
    values: list[int]
    class_id: int
    cycles: int
    executions: int
    backend: str
    roundtrip_ms: float

    @property
    def scores(self):
        return self.values


class DemoClient:
    """Exclusive one-request-in-flight mailbox owner.

    A timeout keeps the slot reserved. Call recover() to wait for that exact
    request; overwriting its input with the next camera frame is forbidden.
    """
    def __init__(self, transport: MemoryTransport, metadata: p.Metadata, *, timeout: float = 10.0,
                 poll_interval: float = 0.01, package_dir: str | Path | None = None):
        if not math.isfinite(timeout) or timeout <= 0 or not math.isfinite(poll_interval) or poll_interval < 0:
            raise ValueError("Finite positive timeout and nonnegative poll interval required")
        self.transport, self.metadata = transport, metadata
        self.timeout, self.poll_interval = timeout, poll_interval
        self.package_dir = Path(package_dir) if package_dir is not None else None
        self._pending = None
        self._ready = False
        self._lock = threading.Lock()

    @classmethod
    def from_package(cls, transport: MemoryTransport, package_dir: str | Path, **kwargs):
        package_dir = Path(package_dir)
        return cls(transport, p.Metadata.from_manifest(package_dir / "manifest.json"),
                   package_dir=package_dir, **kwargs)

    def mailbox(self) -> p.Mailbox:
        box = p.Mailbox.parse(self.transport.read_words(self.metadata.mailbox_address, 16))
        box.validate_identity(self.metadata)
        return box

    def load(self, image: str | Path | bytes | None = None):
        with self._lock:
            if image is None:
                if self.package_dir is None:
                    raise ValueError("Provide image bytes/path or construct client from_package")
                image = self.package_dir / "firmware.bin"
            boot = getattr(self.transport, "boot_image", None)
            if boot is None:
                raise TypeError("Transport does not implement the physical boot-image loader")
            self._ready = False
            boot(image)
            self._attach_unlocked()
        return self

    def attach(self):
        """Attach to idle resident firmware; do not reset or reload its model."""
        with self._lock:
            if self._pending is not None:
                raise RuntimeError("A timed-out request is pending; call recover() first")
            self._attach_unlocked()
        return self

    def _attach_unlocked(self):
        deadline = time.monotonic() + self.timeout
        while True:
            # At cold start CPU may not have initialized its identity yet.
            box = p.Mailbox.parse(self.transport.read_words(self.metadata.mailbox_address, 16))
            if box.magic == p.MAGIC and box.status != 0:
                box.validate_identity(self.metadata)
                if box.request_seq != box.response_seq or box.status == p.BUSY:
                    raise RuntimeError("FPGA has an outstanding request; await its response before attaching")
                if box.status not in (p.READY, p.DONE, p.FAILED):
                    raise RuntimeError(f"Unexpected resident status {box.status}")
                if box.status == p.FAILED and box.error == 3:
                    raise RuntimeError("NPU failure requires SoC reset/reload before attaching")
                self._ready = True
                return
            if time.monotonic() >= deadline:
                raise TimeoutError("Resident live-demo firmware did not publish READY; check bitstream and image")
            time.sleep(self.poll_interval)

    def quantize(self, features: Iterable[float]) -> list[int]:
        """Same ties-to-even rounding/clipping as compiler.quantize, zero point 0."""
        import numpy as np
        values = np.asarray(list(features), dtype=np.float32)
        if len(values) != self.metadata.input_bytes:
            raise ValueError(f"Expected {self.metadata.input_bytes} floating features")
        if values.ndim != 1 or not np.isfinite(values).all():
            raise ValueError("Nonfinite camera feature")
        return np.clip(np.rint(values/self.metadata.input_scale), -128, 127).astype(np.int8).tolist()

    def infer(self, input_int8: Iterable[int]) -> InferenceResult:
        data = p.int8_bytes(input_int8, self.metadata.input_bytes)
        with self._lock:
            if not self._ready:
                raise RuntimeError("Call load() or attach() before inference")
            if self._pending is not None:
                raise RuntimeError("Previous request is pending; call recover() before submitting another frame")
            box = self.mailbox()
            if box.request_seq != box.response_seq or box.status == p.BUSY:
                raise RuntimeError("Mailbox already has a request; only one host may own it")
            if box.status not in (p.READY, p.DONE, p.FAILED):
                raise RuntimeError(f"Invalid idle firmware status {box.status}")
            if box.status == p.FAILED and box.error == 3:
                self._ready = False
                raise RuntimeError("NPU failure requires SoC reset/reload")
            sequence = (box.request_seq + 1) & 0xFFFFFFFF
            if sequence == 0:
                sequence = 1
            started = time.monotonic()
            write_bytes(self.transport, self.metadata.input_address, data)
            # Host fields first; sequence is the commit word and is sent last.
            self.transport.write_words(self.metadata.mailbox_address + p.COMMAND,
                                       [p.INFER, self.metadata.input_bytes])
            self._pending = (sequence, started)
            try:
                self.transport.write_words(self.metadata.mailbox_address + p.REQUEST_SEQ, [sequence])
            except Exception:
                # The write might have reached the device before TCP failed.
                # Keep the slot pending rather than reusing live input memory.
                raise
            return self._await_unlocked()

    def recover(self) -> InferenceResult:
        """Wait for exactly the last submitted sequence after a timeout."""
        with self._lock:
            if self._pending is None:
                raise RuntimeError("There is no pending request to recover")
            return self._await_unlocked()

    def _await_unlocked(self) -> InferenceResult:
        sequence, started = self._pending
        deadline = time.monotonic() + self.timeout
        while True:
            box = self.mailbox()
            if box.request_seq != sequence:
                raise RuntimeError("Request sequence changed unexpectedly; another host or board reset interfered")
            if box.response_seq == sequence:
                # CPU publishes response_seq only after all outputs/status.
                if box.status == p.FAILED:
                    self._pending = None
                    if box.error == 3:
                        self._ready = False
                    raise DeviceError(sequence, box.error)
                if box.status != p.DONE or box.error:
                    raise RuntimeError("Committed response has invalid status/error")
                values = p.signed_bytes(read_bytes(self.transport, self.metadata.output_address,
                                                  self.metadata.output_bytes))
                final = self.mailbox()
                if (final.request_seq, final.response_seq, final.status) != (sequence, sequence, p.DONE):
                    raise RuntimeError("Response changed during readback")
                category = max(range(len(values)), key=values.__getitem__)
                if box.argmax != category:
                    raise RuntimeError("Firmware argmax differs from read-back result; output rejected")
                self._pending = None
                return InferenceResult(sequence, values, category, box.cycles, box.executions,
                                       self.transport.backend, (time.monotonic()-started)*1000)
            if time.monotonic() >= deadline:
                raise TimeoutError(f"FPGA did not complete sequence {sequence}; slot remains reserved, call recover()")
            time.sleep(self.poll_interval)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("package", type=Path, help="Resident package emitted by fpga.demo.firmware")
    parser.add_argument("--inputs", required=True, type=Path, help="JSON list of feature vectors or JSONL, one vector per line")
    parser.add_argument("--int8", action="store_true", help="Inputs are already quantized signed INT8")
    parser.add_argument("--attach", action="store_true", help="Reuse already loaded idle resident firmware")
    parser.add_argument("--host", default="127.0.0.1", help="OpenOCD Tcl host; Windows→WSL uses localhost forwarding")
    parser.add_argument("--port", type=int, default=6666)
    parser.add_argument("--target", help="Optional OpenOCD target name")
    parser.add_argument("--timeout", type=float, default=10.0)
    parser.add_argument("--output", type=Path, help="Write actual result JSONL including backend and sequence")
    parser.add_argument("--expected", type=Path, help="Optional independent integer-reference JSON rows, checked against actual FPGA readback")
    args = parser.parse_args(argv)
    text = args.inputs.read_text(encoding="utf-8")
    try:
        vectors = json.loads(text)
    except json.JSONDecodeError:
        vectors = [json.loads(line) for line in text.splitlines() if line.strip()]
    if not isinstance(vectors, list) or not vectors or not all(isinstance(v, list) for v in vectors):
        parser.error("--inputs must contain a nonempty list of vectors")
    expected = None
    if args.expected:
        expected = json.loads(args.expected.read_text(encoding="utf-8"))
        if not isinstance(expected, list) or len(expected) != len(vectors):
            parser.error("--expected must contain one quantized output row per input")
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
    output = args.output.open("w", encoding="utf-8") if args.output else None
    try:
        with OpenOCDTransport(args.host, args.port, timeout=args.timeout, target=args.target) as transport:
            client = DemoClient.from_package(transport, args.package, timeout=args.timeout)
            client.attach() if args.attach else client.load()
            for index, vector in enumerate(vectors):
                result = client.infer(vector if args.int8 else client.quantize(vector))
                record = asdict(result)
                if expected is not None:
                    record["matches_integer_reference"] = result.values == expected[index]
                line = json.dumps(record, ensure_ascii=False)
                print(line, flush=True)
                if output:
                    output.write(line + "\n")
                    output.flush()
                if expected is not None and not record["matches_integer_reference"]:
                    raise RuntimeError(f"Actual FPGA result for input {index} differs from independent integer reference")
    finally:
        if output:
            output.close()


if __name__ == "__main__":
    main()
