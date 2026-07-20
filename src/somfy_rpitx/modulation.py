"""Map logical RTS pulse levels to configurable binary FSK tones."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from .pulses import Pulse


@dataclass(frozen=True)
class FSKSettings:
    """RF settings without an assumed deviation for the Korean transmitter."""

    center_frequency_hz: int = 447_700_000
    deviation_hz: int | None = None
    mark_frequency_hz: int | None = None
    space_frequency_hz: int | None = None
    invert_mark_space: bool = False
    tick_us: int = 4

    def __post_init__(self) -> None:
        if not 50_000 <= self.center_frequency_hz <= 1_500_000_000:
            raise ValueError("center_frequency_hz is outside rpitx's supported range")
        if self.deviation_hz is not None and self.deviation_hz <= 0:
            raise ValueError("deviation_hz must be positive when set")
        if (self.mark_frequency_hz is None) != (self.space_frequency_hz is None):
            raise ValueError(
                "mark_frequency_hz and space_frequency_hz must be set together"
            )
        for name, frequency in (
            ("mark_frequency_hz", self.mark_frequency_hz),
            ("space_frequency_hz", self.space_frequency_hz),
        ):
            if frequency is not None and not 50_000 <= frequency <= 1_500_000_000:
                raise ValueError(f"{name} is outside rpitx's supported range")
        if self.tick_us <= 0:
            raise ValueError("tick_us must be positive")

    @classmethod
    def from_mapping(cls, values: Mapping[str, object] | None) -> "FSKSettings":
        if not values:
            return cls()
        allowed = {
            "center_frequency_hz",
            "deviation_hz",
            "mark_frequency_hz",
            "space_frequency_hz",
            "invert_mark_space",
            "tick_us",
        }
        unknown = set(values) - allowed
        if unknown:
            raise ValueError(f"unknown RF settings: {', '.join(sorted(unknown))}")
        normalized = dict(values)
        for key in (
            "center_frequency_hz",
            "deviation_hz",
            "mark_frequency_hz",
            "space_frequency_hz",
            "tick_us",
        ):
            if key in normalized and normalized[key] is not None:
                normalized[key] = int(normalized[key])
        if "invert_mark_space" in normalized:
            value = normalized["invert_mark_space"]
            if not isinstance(value, bool):
                raise ValueError("invert_mark_space must be true or false")
        return cls(**normalized)

    def resolve(self) -> "ResolvedFSK | None":
        """Resolve the exact tones, or return ``None`` if calibration is absent."""

        if self.mark_frequency_hz is not None:
            mark = self.mark_frequency_hz
            space = self.space_frequency_hz
            assert space is not None
            source = "explicit mark/space"
        elif self.deviation_hz is not None:
            mark = self.center_frequency_hz + self.deviation_hz
            space = self.center_frequency_hz - self.deviation_hz
            source = "center ± deviation"
        else:
            return None

        if mark == space:
            raise ValueError("mark and space frequencies must differ")
        return ResolvedFSK(
            center_frequency_hz=self.center_frequency_hz,
            mark_frequency_hz=mark,
            space_frequency_hz=space,
            invert_mark_space=self.invert_mark_space,
            tick_us=self.tick_us,
            source=source,
        )


@dataclass(frozen=True)
class ResolvedFSK:
    center_frequency_hz: int
    mark_frequency_hz: int
    space_frequency_hz: int
    invert_mark_space: bool
    tick_us: int
    source: str

    def frequency_for_level(self, level: bool) -> int:
        """Map logical high to MARK unless inversion is requested."""

        mark_level = not self.invert_mark_space
        return self.mark_frequency_hz if level == mark_level else self.space_frequency_hz


@dataclass(frozen=True)
class ToneEvent:
    logical_level: bool
    frequency_hz: int | None
    carrier_enabled: bool
    duration_us: int
    phase: str
    frame_index: int


def carrier_enabled_for_pulse(pulse: Pulse) -> bool:
    """Return whether an RTS interval contains RF energy.

    Manchester, software-sync, and hardware-sync lows become the SPACE tone
    under FSK.  The wake-up separator and inter-frame gap remain true RF
    silence, as required by the RTS framing description.
    """

    return pulse.phase != "inter-frame-gap" and not (
        pulse.phase == "wakeup" and not pulse.level
    )


def modulate(pulses: tuple[Pulse, ...], fsk: ResolvedFSK) -> tuple[ToneEvent, ...]:
    events = []
    for pulse in pulses:
        carrier_enabled = carrier_enabled_for_pulse(pulse)
        events.append(
            ToneEvent(
                logical_level=pulse.level,
                frequency_hz=(
                    fsk.frequency_for_level(pulse.level)
                    if carrier_enabled
                    else None
                ),
                carrier_enabled=carrier_enabled,
                duration_us=pulse.duration_us,
                phase=pulse.phase,
                frame_index=pulse.frame_index,
            )
        )
    return tuple(events)
