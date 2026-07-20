"""Pure Somfy RTS payload generation.

This module deliberately knows nothing about GPIO, RF frequencies, storage, or
the command line.  It implements the established 56-bit Somfy RTS payload used
by 433.42 MHz libraries so it can be reused by the Korean FSK output layer.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum


FRAME_BYTES = 7


class Command(IntEnum):
    """Four-bit Somfy RTS control codes."""

    MY_STOP = 0x1
    UP = 0x2
    DOWN = 0x4
    PROG = 0x8

    @classmethod
    def from_cli(cls, value: str) -> "Command":
        aliases = {
            "up": cls.UP,
            "down": cls.DOWN,
            "stop": cls.MY_STOP,
            "my": cls.MY_STOP,
            "prog": cls.PROG,
        }
        try:
            return aliases[value.lower()]
        except KeyError as exc:
            raise ValueError(f"unsupported RTS command: {value}") from exc


def checksum(frame: bytes | bytearray) -> int:
    """Return the RTS nibble-XOR checksum.

    A valid clear frame containing its checksum returns zero.  When generating
    a frame, byte 1's low nibble must initially be zero; this function then
    returns the checksum nibble to insert there.
    """

    if len(frame) != FRAME_BYTES:
        raise ValueError(f"RTS frame must be {FRAME_BYTES} bytes")
    value = 0
    for byte in frame:
        value ^= byte ^ (byte >> 4)
    return value & 0x0F


def obfuscate(frame: bytes | bytearray) -> bytes:
    """Apply the RTS cumulative XOR obfuscation."""

    if len(frame) != FRAME_BYTES:
        raise ValueError(f"RTS frame must be {FRAME_BYTES} bytes")
    result = bytearray(frame)
    for index in range(1, FRAME_BYTES):
        result[index] ^= result[index - 1]
    return bytes(result)


def deobfuscate(frame: bytes | bytearray) -> bytes:
    """Reverse the RTS cumulative XOR obfuscation."""

    if len(frame) != FRAME_BYTES:
        raise ValueError(f"RTS frame must be {FRAME_BYTES} bytes")
    return bytes(
        frame[index] if index == 0 else frame[index] ^ frame[index - 1]
        for index in range(FRAME_BYTES)
    )


@dataclass(frozen=True)
class RTSFrame:
    """One logical Somfy RTS command payload."""

    command: Command
    rolling_code: int
    remote_address: int
    encryption_key: int | None = None

    def __post_init__(self) -> None:
        if not 0 <= self.rolling_code <= 0xFFFF:
            raise ValueError("rolling_code must fit in 16 bits")
        if not 0 <= self.remote_address <= 0xFFFFFF:
            raise ValueError("remote_address must fit in 24 bits")
        if self.encryption_key is not None and not 0 <= self.encryption_key <= 0xFF:
            raise ValueError("encryption_key must fit in 8 bits")
        try:
            Command(self.command)
        except ValueError as exc:
            raise ValueError("unsupported RTS command") from exc

    @property
    def key(self) -> int:
        """Return a physical-remote-like key unless explicitly overridden."""

        if self.encryption_key is not None:
            return self.encryption_key
        return 0xA0 | (self.rolling_code & 0x0F)

    def clear_bytes(self) -> bytes:
        """Serialize the checksum-bearing, non-obfuscated 56-bit frame."""

        frame = bytearray(
            (
                self.key,
                int(self.command) << 4,
                self.rolling_code >> 8,
                self.rolling_code & 0xFF,
                self.remote_address & 0xFF,
                (self.remote_address >> 8) & 0xFF,
                (self.remote_address >> 16) & 0xFF,
            )
        )
        frame[1] |= checksum(frame)
        return bytes(frame)

    def encoded_bytes(self) -> bytes:
        """Serialize the on-air, obfuscated 56-bit frame."""

        return obfuscate(self.clear_bytes())

    def bits_msb_first(self) -> tuple[int, ...]:
        """Return the 56 on-air bits, MSB first."""

        return tuple(
            (byte >> bit_index) & 1
            for byte in self.encoded_bytes()
            for bit_index in range(7, -1, -1)
        )
