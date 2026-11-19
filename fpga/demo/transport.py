"""OpenOCD Tcl RPC memory transport; no UART or per-frame CPU halt required.

Official protocol: https://openocd.org/doc/html/Tcl-Scripting-API.html
Memory commands: https://openocd.org/doc/html/General-Commands.html
"""
from __future__ import annotations

import re
import socket
import struct
import threading
import time
from pathlib import Path
from typing import Protocol, Sequence

from .protocol import SRAM_BASE, SRAM_BYTES

BOOT_STATUS = 0x0001003C
BOOT_KEY = 0xB007C0DE


class MemoryTransport(Protocol):
    backend: str

    def read_words(self, address: int, count: int) -> list[int]: ...
    def write_words(self, address: int, values: Sequence[int]) -> None: ...


class TransportError(RuntimeError):
    pass


def _word_access(address: int, count: int):
    if type(address) is not int or type(count) is not int or address % 4 or count < 1:
        raise ValueError("Memory access needs an aligned uint32 address and positive word count")
    if address < 0 or address + 4*count > (1 << 32):
        raise ValueError("Memory access exceeds 32-bit address space")


def read_bytes(transport: MemoryTransport, address: int, count: int) -> bytes:
    if count < 1:
        raise ValueError("Positive byte count required")
    first = address & ~3
    words = transport.read_words(first, (address-first+count+3)//4)
    return struct.pack(f"<{len(words)}I", *words)[address-first:address-first+count]


def write_bytes(transport: MemoryTransport, address: int, data: bytes):
    """Word writes with preserved padding, for host-owned idle input buffers."""
    data = bytes(data)
    if not data:
        raise ValueError("Nonempty input required")
    first = address & ~3
    size = (address-first+len(data)+3)//4*4
    if first == address and len(data) == size:
        raw = data
    else:
        # Never use this read/modify/write helper on volatile mailbox fields.
        raw = bytearray(read_bytes(transport, first, size))
        raw[address-first:address-first+len(data)] = data
    transport.write_words(first, struct.unpack(f"<{size//4}I", raw))


class OpenOCDTransport:
    backend = "openocd-jtag"

    def __init__(self, host: str = "127.0.0.1", port: int = 6666, *, timeout: float = 10.0,
                 target: str | None = None, chunk_words: int = 64):
        if timeout <= 0 or not 1 <= chunk_words <= 256 or not 1 <= port <= 65535:
            raise ValueError("Invalid OpenOCD timeout, TCP port or transfer chunk")
        if target is not None and not re.fullmatch(r"[A-Za-z0-9_.:-]+", target):
            raise ValueError("Invalid OpenOCD target name")
        self.host, self.port, self.timeout = host, port, timeout
        self.target, self.chunk_words = target, chunk_words
        self._socket = None
        self._receive = bytearray()
        self._lock = threading.Lock()

    def connect(self):
        if self._socket is not None:
            return self
        try:
            self._socket = socket.create_connection((self.host, self.port), self.timeout)
            self._socket.settimeout(self.timeout)
            self.command("tcl notifications off")
            self.command("tcl trace off")
            if self.target:
                self.command("targets " + self.target)
            # SBA can access the AXI bus while CPU firmware runs. Program-buffer
            # fallback is deliberately forbidden because it halts/disturbs CPU.
            try:
                self.command("riscv mem_access sysbus")
            except TransportError:
                self.command("riscv set_mem_access sysbus")
        except Exception:
            self.close()
            raise
        return self

    def __enter__(self):
        return self.connect()

    def __exit__(self, *_):
        self.close()

    def close(self):
        if self._socket is not None:
            self._socket.close()
            self._socket = None
        self._receive.clear()

    def command(self, script: str) -> str:
        """Checked Tcl response; errors never masquerade as memory values."""
        if self._socket is None:
            raise TransportError("Connect to OpenOCD before issuing commands")
        if "\x1a" in script or "\x00" in script:
            raise ValueError("Forbidden Tcl framing byte")
        # The wrapper is generated only from this module's fixed/numeric Tcl.
        wrapped = "set __live_rc [catch {" + script + "} __live_result]; format {%d %s} $__live_rc $__live_result"
        with self._lock:
            try:
                self._socket.sendall(wrapped.encode("utf-8") + b"\x1a")
                while b"\x1a" not in self._receive:
                    data = self._socket.recv(65536)
                    if not data:
                        raise TransportError("OpenOCD closed the Tcl connection")
                    self._receive.extend(data)
                    if len(self._receive) > 1024*1024:
                        raise TransportError("OpenOCD Tcl response exceeds 1 MiB")
                end = self._receive.index(0x1A)
                response = bytes(self._receive[:end]).decode("utf-8", errors="replace")
                del self._receive[:end+1]
            except (OSError, TimeoutError, TransportError) as error:
                self.close()
                raise TransportError(f"OpenOCD Tcl I/O failed: {error}") from error
        code, separator, result = response.partition(" ")
        if not separator or not code.isdecimal():
            raise TransportError(f"Malformed OpenOCD response: {response!r}")
        if int(code):
            raise TransportError(f"OpenOCD command failed ({script}): {result}")
        return result.strip()

    def read_words(self, address: int, count: int) -> list[int]:
        _word_access(address, count)
        result = []
        for offset in range(0, count, self.chunk_words):
            size = min(count-offset, self.chunk_words)
            raw = self.command(f"read_memory 0x{address+offset*4:08x} 32 {size}")
            try:
                words = [int(value, 0) for value in raw.split()]
            except ValueError as error:
                raise TransportError(f"Noninteger OpenOCD memory result: {raw!r}") from error
            if len(words) != size or any(not 0 <= value < 1 << 32 for value in words):
                raise TransportError("OpenOCD returned an incomplete/invalid memory read")
            result.extend(words)
        return result

    def write_words(self, address: int, values: Sequence[int]):
        values = list(values)
        _word_access(address, len(values))
        if any(type(value) is not int or not 0 <= value < 1 << 32 for value in values):
            raise ValueError("Memory write values must be uint32")
        for offset in range(0, len(values), self.chunk_words):
            chunk = " ".join(f"0x{value:08x}" for value in values[offset:offset+self.chunk_words])
            self.command(f"write_memory 0x{address+offset*4:08x} 32 {{{chunk}}}")

    def boot_image(self, image: str | Path | bytes, *, verify: bool = True):
        """Load one uninitialized SoC; a reset/reprogram is required to reload."""
        raw = Path(image).read_bytes() if isinstance(image, (str, Path)) else bytes(image)
        if len(raw) != SRAM_BYTES:
            raise ValueError("The SoC boot loader requires exactly 8192 bytes")
        status = self.read_words(BOOT_STATUS, 1)[0]
        if status & 0x2FFF:
            raise TransportError(f"Boot controller is not empty (0x{status:08x}); reset/reprogram before load, or use --attach")
        self.command("halt 5000")
        status = self.read_words(BOOT_STATUS, 1)[0]
        if status & 0x2FFF:
            raise TransportError("Boot controller changed while halting; refusing to overwrite a loaded image")
        words = list(struct.unpack("<2048I", raw))
        # Strictly ascending and one write per word: boot tracks all 2048 words.
        self.write_words(SRAM_BASE, words)
        status = self.read_words(BOOT_STATUS, 1)[0]
        if status & 0x2FFF != 2048:
            raise TransportError(f"Ordered image loading was not accepted: 0x{status:08x}")
        if verify and self.read_words(SRAM_BASE, 2048) != words:
            raise TransportError("Image readback differs; refusing to commit")
        self.write_words(BOOT_STATUS, [BOOT_KEY])
        deadline = time.monotonic() + self.timeout
        while not self.read_words(BOOT_STATUS, 1)[0] & 0x2000:
            if time.monotonic() >= deadline:
                raise TimeoutError("Boot commit did not assert ready")
            time.sleep(0.01)
        self.command("resume")
