"""Convert an encoded Somfy RTS frame into timed logical pulses."""

from __future__ import annotations

from dataclasses import dataclass, fields
from typing import Mapping

from .protocol import RTSFrame


@dataclass(frozen=True)
class TimingProfile:
    """RTS timings in microseconds.

    Defaults are the measured ``RTS_TIMINGS_SITUO5`` values from Open RTS.
    They remain configurable because regional transmitters and receivers may
    differ slightly.
    """

    wakeup_high_us: int = 10_568
    wakeup_low_us: int = 7_072
    preamble_high_us: int = 2_585
    preamble_low_us: int = 2_436
    software_sync_high_us: int = 4_898
    software_sync_low_us: int = 644
    half_symbol_us: int = 644
    inter_frame_gap_us: int = 26_838

    def __post_init__(self) -> None:
        for field in fields(self):
            if getattr(self, field.name) <= 0:
                raise ValueError(f"{field.name} must be positive")

    @classmethod
    def from_mapping(cls, values: Mapping[str, object] | None) -> "TimingProfile":
        if not values:
            return cls()
        allowed = {field.name for field in fields(cls)}
        unknown = set(values) - allowed
        if unknown:
            raise ValueError(f"unknown timing settings: {', '.join(sorted(unknown))}")
        return cls(**{key: int(value) for key, value in values.items()})


SITUO5_TIMINGS = TimingProfile()


@dataclass(frozen=True)
class Pulse:
    """A logical RTS level held for ``duration_us``."""

    level: bool
    duration_us: int
    phase: str
    frame_index: int


def _frame_pulses(
    frame: RTSFrame,
    *,
    frame_index: int,
    repeated: bool,
    timings: TimingProfile,
) -> list[Pulse]:
    pulses: list[Pulse] = []

    def add(level: bool, duration_us: int, phase: str) -> None:
        pulses.append(Pulse(level, duration_us, phase, frame_index))

    if not repeated:
        add(True, timings.wakeup_high_us, "wakeup")
        add(False, timings.wakeup_low_us, "wakeup")

    preamble_count = 7 if repeated else 2
    for _ in range(preamble_count):
        add(True, timings.preamble_high_us, "hardware-sync")
        add(False, timings.preamble_low_us, "hardware-sync")

    add(True, timings.software_sync_high_us, "software-sync")
    add(False, timings.software_sync_low_us, "software-sync")

    for bit_offset, bit in enumerate(frame.bits_msb_first()):
        phase = f"data[{bit_offset:02d}]={bit}"
        # Somfy Manchester: a logical 1 is a rising edge and 0 is falling.
        add(not bool(bit), timings.half_symbol_us, phase)
        add(bool(bit), timings.half_symbol_us, phase)

    add(False, timings.inter_frame_gap_us, "inter-frame-gap")
    return pulses


def generate_pulses(
    frame: RTSFrame,
    *,
    frame_count: int = 3,
    timings: TimingProfile = SITUO5_TIMINGS,
) -> tuple[Pulse, ...]:
    """Generate one initial RTS frame and ``frame_count - 1`` repeats."""

    if frame_count < 1:
        raise ValueError("frame_count must be at least 1")

    result: list[Pulse] = []
    for frame_index in range(frame_count):
        result.extend(
            _frame_pulses(
                frame,
                frame_index=frame_index,
                repeated=frame_index > 0,
                timings=timings,
            )
        )
    return tuple(result)


def total_duration_us(pulses: tuple[Pulse, ...] | list[Pulse]) -> int:
    return sum(pulse.duration_us for pulse in pulses)
