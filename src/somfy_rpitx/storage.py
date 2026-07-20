"""Locked, crash-resistant JSON storage for the virtual RTS remote."""

from __future__ import annotations

import fcntl
import json
import os
import secrets
import tempfile
from contextlib import contextmanager
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterator


STATE_VERSION = 1


@dataclass(frozen=True)
class RemoteState:
    version: int
    remote_address: int
    next_rolling_code: int

    def __post_init__(self) -> None:
        if self.version != STATE_VERSION:
            raise ValueError(f"unsupported state version: {self.version}")
        if not 1 <= self.remote_address <= 0xFFFFFE:
            raise ValueError("remote_address must be between 0x000001 and 0xFFFFFE")
        if not 0 <= self.next_rolling_code <= 0xFFFF:
            raise ValueError("next_rolling_code must fit in 16 bits")


class StateStore:
    """Persist one newly-created virtual remote address and rolling counter."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self.lock_path = path.with_name(path.name + ".lock")

    def peek_or_create(self) -> RemoteState:
        """Read state, creating a new virtual remote if this is first use."""

        with self._locked():
            state = self._read_unlocked()
            if state is None:
                state = RemoteState(
                    version=STATE_VERSION,
                    remote_address=secrets.randbelow(0xFFFFFE) + 1,
                    next_rolling_code=1,
                )
                self._write_unlocked(state)
            return state

    def reserve_rolling_code(self) -> tuple[int, int]:
        """Atomically reserve one code and persist the increment before RF use.

        Returns ``(remote_address, rolling_code)``.  A failed transmission may
        therefore skip a code, but a process crash can never reuse one.
        """

        with self._locked():
            state = self._read_unlocked()
            if state is None:
                state = RemoteState(
                    version=STATE_VERSION,
                    remote_address=secrets.randbelow(0xFFFFFE) + 1,
                    next_rolling_code=1,
                )
            if state.next_rolling_code == 0xFFFF:
                raise OverflowError(
                    "rolling code reached the 0xFFFF exhaustion guard; create "
                    "and pair a new virtual remote before transmitting again"
                )
            reserved = state.next_rolling_code
            updated = RemoteState(
                version=state.version,
                remote_address=state.remote_address,
                next_rolling_code=reserved + 1,
            )
            self._write_unlocked(updated)
            return state.remote_address, reserved

    @contextmanager
    def _locked(self) -> Iterator[None]:
        self.path.parent.mkdir(parents=True, exist_ok=True, mode=0o750)
        descriptor = os.open(self.lock_path, os.O_RDWR | os.O_CREAT, 0o600)
        try:
            os.fchmod(descriptor, 0o600)
            fcntl.flock(descriptor, fcntl.LOCK_EX)
            yield
        finally:
            fcntl.flock(descriptor, fcntl.LOCK_UN)
            os.close(descriptor)

    def _read_unlocked(self) -> RemoteState | None:
        try:
            raw = self.path.read_text(encoding="utf-8")
        except FileNotFoundError:
            return None
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ValueError(f"invalid JSON state file {self.path}: {exc}") from exc
        if not isinstance(data, dict):
            raise ValueError(f"state file {self.path} must contain a JSON object")
        expected = {"version", "remote_address", "next_rolling_code"}
        if set(data) != expected:
            raise ValueError(
                f"state file {self.path} must contain exactly: "
                + ", ".join(sorted(expected))
            )
        return RemoteState(
            version=int(data["version"]),
            remote_address=int(data["remote_address"]),
            next_rolling_code=int(data["next_rolling_code"]),
        )

    def _write_unlocked(self, state: RemoteState) -> None:
        descriptor, temporary_name = tempfile.mkstemp(
            prefix=f".{self.path.name}.",
            suffix=".tmp",
            dir=self.path.parent,
        )
        temporary_path = Path(temporary_name)
        try:
            os.fchmod(descriptor, 0o600)
            with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
                json.dump(asdict(state), handle, indent=2, sort_keys=True)
                handle.write("\n")
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary_path, self.path)
            os.chmod(self.path, 0o600)
            directory_descriptor = os.open(self.path.parent, os.O_RDONLY)
            try:
                os.fsync(directory_descriptor)
            finally:
                os.close(directory_descriptor)
        except BaseException:
            try:
                temporary_path.unlink()
            except FileNotFoundError:
                pass
            raise
