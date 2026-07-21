"""Small, strictly validated sudo boundary for the Homebridge plugin."""

from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path
from typing import Callable, Sequence

from .cli import main as cli_main
from .config import DEFAULT_CONFIG_PATH


DEFAULT_STATE_DIRECTORY = Path("/var/lib/somfy-rpitx")
ALLOWED_ACTIONS = ("up", "down", "stop")
STATE_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*\.json$")
MainFunction = Callable[[Sequence[str] | None], int]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="somfy-rpitx-homebridge",
        description="Validated privileged helper for homebridge-somfy-rpitx",
    )
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--state-file", type=Path, required=True)
    parser.add_argument("action", choices=ALLOWED_ACTIONS)
    return parser


def main(
    argv: Sequence[str] | None = None,
    *,
    run_cli: MainFunction = cli_main,
    geteuid: Callable[[], int] = os.geteuid,
) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        if geteuid() != 0:
            raise PermissionError("Homebridge helper must run as root")
        config = _validated_config(args.config)
        state_file = _validated_state_file(args.state_file)
    except (OSError, PermissionError, ValueError) as exc:
        print(f"somfy-rpitx-homebridge: error: {exc}", file=sys.stderr)
        return 1

    return run_cli(
        [
            "--config",
            str(config),
            "--state-file",
            str(state_file),
            args.action,
        ]
    )


def _validated_config(path: Path) -> Path:
    expected = DEFAULT_CONFIG_PATH.resolve(strict=False)
    resolved = path.resolve(strict=False)
    if resolved != expected:
        raise ValueError(f"config must be {DEFAULT_CONFIG_PATH}")
    if path.is_symlink() or not path.is_file():
        raise ValueError(f"config must be a regular file: {DEFAULT_CONFIG_PATH}")
    return path


def _validated_state_file(path: Path) -> Path:
    if not path.is_absolute():
        raise ValueError("state file must be an absolute path")
    if not STATE_NAME.fullmatch(path.name):
        raise ValueError("state filename must be a safe '<remote-id>.json' name")
    expected_parent = DEFAULT_STATE_DIRECTORY.resolve(strict=False)
    if path.parent.resolve(strict=False) != expected_parent:
        raise ValueError(f"state file must be directly inside {DEFAULT_STATE_DIRECTORY}")
    if path.is_symlink():
        raise ValueError("state file must not be a symbolic link")
    return path


if __name__ == "__main__":
    raise SystemExit(main())
