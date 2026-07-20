"""Human-readable dry-run rendering."""

from __future__ import annotations

from .modulation import FSKSettings, carrier_enabled_for_pulse
from .protocol import RTSFrame
from .pulses import Pulse, total_duration_us


def render_dry_run(
    *,
    frame: RTSFrame,
    pulses: tuple[Pulse, ...],
    rf: FSKSettings,
) -> str:
    resolved = rf.resolve()
    clear = frame.clear_bytes()
    encoded = frame.encoded_bytes()
    bits = "".join(str(bit) for bit in frame.bits_msb_first())

    if resolved is None:
        mark = "UNSET (set deviation_hz or explicit mark/space)"
        space = "UNSET (set deviation_hz or explicit mark/space)"
        source = "unresolved"
    else:
        mark = str(resolved.mark_frequency_hz)
        space = str(resolved.space_frequency_hz)
        source = resolved.source

    lines = [
        "mode: dry-run (no RF transmission; rolling code not consumed)",
        f"command: {frame.command.name} (0x{int(frame.command):X})",
        f"remote_address: 0x{frame.remote_address:06X}",
        f"rolling_code: {frame.rolling_code} (0x{frame.rolling_code:04X})",
        f"clear_frame: {' '.join(f'{byte:02X}' for byte in clear)}",
        f"encoded_frame: {' '.join(f'{byte:02X}' for byte in encoded)}",
        f"on_air_bits_msb_first: {bits}",
        f"center_frequency_hz: {rf.center_frequency_hz}",
        f"deviation_hz: {rf.deviation_hz if rf.deviation_hz is not None else 'UNSET'}",
        f"mark_frequency_hz: {mark}",
        f"space_frequency_hz: {space}",
        f"tone_resolution: {source}",
        f"invert_mark_space: {str(rf.invert_mark_space).lower()}",
        f"rpitx_tick_us: {rf.tick_us}",
        f"frame_count: {max(pulse.frame_index for pulse in pulses) + 1}",
        f"pulse_count: {len(pulses)}",
        f"total_duration_us: {total_duration_us(pulses)}",
        "",
        "index start_us frame phase logical tone frequency_hz duration_us",
    ]

    start_us = 0
    for index, pulse in enumerate(pulses):
        carrier_enabled = carrier_enabled_for_pulse(pulse)
        if carrier_enabled:
            tone = _tone_name(pulse.level, rf.invert_mark_space)
            frequency = (
                str(resolved.frequency_for_level(pulse.level))
                if resolved is not None
                else "UNSET"
            )
        else:
            tone = "OFF"
            frequency = "-"
        lines.append(
            f"{index:04d} {start_us:8d} {pulse.frame_index:02d} "
            f"{pulse.phase:17s} {int(pulse.level)} {tone:5s} "
            f"{frequency:>12s} {pulse.duration_us:8d}"
        )
        start_us += pulse.duration_us
    return "\n".join(lines)


def _tone_name(level: bool, inverted: bool) -> str:
    mark_level = not inverted
    return "MARK" if level == mark_level else "SPACE"
