"""JSON configuration loading for somfy-rpitx."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

from .modulation import FSKSettings
from .pulses import TimingProfile


DEFAULT_CONFIG_PATH = Path("/etc/somfy-rpitx/config.json")
DEFAULT_STATE_PATH = Path("/var/lib/somfy-rpitx/state.json")


@dataclass(frozen=True)
class Settings:
    rf: FSKSettings = FSKSettings()
    timings: TimingProfile = TimingProfile()
    frame_count: int = 3
    prog_frame_count: int = 4
    state_file: Path = DEFAULT_STATE_PATH
    transmitter_executable: str = "somfy-rpitx-tx"
    transmit_enabled: bool = False

    def __post_init__(self) -> None:
        if self.frame_count < 1:
            raise ValueError("frame_count must be at least 1")
        if self.prog_frame_count < 1:
            raise ValueError("prog_frame_count must be at least 1")
        if not self.transmitter_executable:
            raise ValueError("transmitter_executable cannot be empty")

    @classmethod
    def from_mapping(cls, values: Mapping[str, object]) -> "Settings":
        allowed = {
            "rf",
            "timings",
            "frame_count",
            "prog_frame_count",
            "state_file",
            "transmitter_executable",
            "transmit_enabled",
        }
        unknown = set(values) - allowed
        if unknown:
            raise ValueError(f"unknown configuration keys: {', '.join(sorted(unknown))}")
        return cls(
            rf=FSKSettings.from_mapping(_mapping_or_none(values.get("rf"), "rf")),
            timings=TimingProfile.from_mapping(
                _mapping_or_none(values.get("timings"), "timings")
            ),
            frame_count=int(values.get("frame_count", 3)),
            prog_frame_count=int(values.get("prog_frame_count", 4)),
            state_file=Path(str(values.get("state_file", DEFAULT_STATE_PATH))),
            transmitter_executable=str(
                values.get("transmitter_executable", "somfy-rpitx-tx")
            ),
            transmit_enabled=_boolean(values.get("transmit_enabled", False), "transmit_enabled"),
        )


def _mapping_or_none(value: object, name: str) -> Mapping[str, object] | None:
    if value is None:
        return None
    if not isinstance(value, dict):
        raise ValueError(f"{name} must be a JSON object")
    return value


def _boolean(value: object, name: str) -> bool:
    if not isinstance(value, bool):
        raise ValueError(f"{name} must be true or false")
    return value


def load_settings(path: Path | None = None) -> Settings:
    """Load settings, using safe dry-run defaults when the file is absent."""

    configured = path
    if configured is None:
        configured = Path(os.environ.get("SOMFY_RPITX_CONFIG", DEFAULT_CONFIG_PATH))
    try:
        raw = configured.read_text(encoding="utf-8")
    except FileNotFoundError:
        return Settings()
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid JSON in {configured}: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError(f"configuration root in {configured} must be an object")
    return Settings.from_mapping(data)
