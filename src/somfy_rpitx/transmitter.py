"""Validated subprocess bridge to the native librpitx FSK backend."""

from __future__ import annotations

import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Sequence

from .config import Settings
from .modulation import ResolvedFSK, carrier_enabled_for_pulse
from .pulses import Pulse


RunFunction = Callable[..., subprocess.CompletedProcess[str]]


@dataclass(frozen=True)
class ValidatedTransmitter:
    executable: str
    fsk: ResolvedFSK


class RpitxTransmitter:
    def __init__(
        self,
        settings: Settings,
        *,
        runner: RunFunction = subprocess.run,
        which: Callable[[str], str | None] = shutil.which,
        geteuid: Callable[[], int] = os.geteuid,
    ) -> None:
        self.settings = settings
        self._runner = runner
        self._which = which
        self._geteuid = geteuid

    def validate(self) -> ValidatedTransmitter:
        """Validate everything that can fail before consuming a rolling code."""

        if not self.settings.transmit_enabled:
            raise RuntimeError(
                "actual RF transmission is disabled; set transmit_enabled=true "
                "after measuring FSK tones and confirming regulatory compliance"
            )
        fsk = self.settings.rf.resolve()
        if fsk is None:
            raise RuntimeError(
                "FSK tones are unresolved; configure deviation_hz or both "
                "mark_frequency_hz and space_frequency_hz"
            )
        if self._geteuid() != 0:
            raise PermissionError("actual rpitx transmission must run as root")
        executable = self._which(self.settings.transmitter_executable)
        if executable is None:
            raise FileNotFoundError(
                f"rpitx backend not found: {self.settings.transmitter_executable}"
            )
        return ValidatedTransmitter(executable=executable, fsk=fsk)

    def transmit(
        self,
        pulses: Sequence[Pulse],
        validated: ValidatedTransmitter | None = None,
    ) -> str:
        checked = validated or self.validate()
        arguments = [
            checked.executable,
            "--mark-hz",
            str(checked.fsk.mark_frequency_hz),
            "--space-hz",
            str(checked.fsk.space_frequency_hz),
            "--tick-us",
            str(checked.fsk.tick_us),
        ]
        if checked.fsk.invert_mark_space:
            arguments.append("--invert-mark-space")
        pulse_input = "".join(
            (
                f"{int(pulse.level)} {pulse.duration_us}\n"
                if carrier_enabled_for_pulse(pulse)
                else f"-1 {pulse.duration_us}\n"
            )
            for pulse in pulses
        )
        completed = self._runner(
            arguments,
            input=pulse_input,
            text=True,
            capture_output=True,
            check=False,
        )
        if completed.returncode != 0:
            detail = completed.stderr.strip() or completed.stdout.strip()
            raise RuntimeError(
                f"rpitx backend failed with exit code {completed.returncode}: {detail}"
            )
        return completed.stderr.strip()
