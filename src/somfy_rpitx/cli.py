"""Command-line entry point."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Sequence

from .config import Settings, load_settings
from .dryrun import render_dry_run
from .protocol import Command, RTSFrame
from .pulses import generate_pulses
from .storage import StateStore
from .transmitter import RpitxTransmitter


COMMAND_NAMES = ("up", "down", "stop", "prog")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="somfy-rpitx",
        description="Control a paired virtual Somfy RTS remote using 447.7 MHz FSK",
    )
    parser.add_argument("--config", type=Path, help="JSON configuration path")
    parser.add_argument("--state-file", type=Path, help="override state JSON path")
    parser.add_argument(
        "action",
        choices=(*COMMAND_NAMES, "dry-run"),
        help="RTS command, or dry-run followed by a command",
    )
    parser.add_argument(
        "dry_run_command",
        nargs="?",
        choices=COMMAND_NAMES,
        help="command to inspect when action is dry-run",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.action == "dry-run" and args.dry_run_command is None:
        parser.error("dry-run requires one of: up, down, stop, prog")
    if args.action != "dry-run" and args.dry_run_command is not None:
        parser.error("a second command is only valid after dry-run")

    try:
        settings = load_settings(args.config)
        state_file = args.state_file or settings.state_file
        store = StateStore(state_file)

        if args.action == "dry-run":
            command = Command.from_cli(args.dry_run_command)
            state = store.peek_or_create()
            frame = RTSFrame(
                command,
                state.next_rolling_code,
                state.remote_address,
            )
            pulses = generate_pulses(
                frame,
                frame_count=_frame_count(settings, command),
                timings=settings.timings,
            )
            print(render_dry_run(frame=frame, pulses=pulses, rf=settings.rf))
            return 0

        command = Command.from_cli(args.action)
        backend = RpitxTransmitter(settings)
        validated = backend.validate()
        address, rolling_code = store.reserve_rolling_code()
        frame = RTSFrame(command, rolling_code, address)
        pulses = generate_pulses(
            frame,
            frame_count=_frame_count(settings, command),
            timings=settings.timings,
        )
        backend_log = backend.transmit(pulses, validated)
        print(
            f"sent {command.name}: address=0x{address:06X} "
            f"rolling_code={rolling_code} frames={_frame_count(settings, command)}"
        )
        if backend_log:
            print(backend_log, file=sys.stderr)
        return 0
    except (OSError, OverflowError, PermissionError, RuntimeError, ValueError) as exc:
        print(f"somfy-rpitx: error: {exc}", file=sys.stderr)
        return 1


def _frame_count(settings: Settings, command: Command) -> int:
    return (
        settings.prog_frame_count
        if command == Command.PROG
        else settings.frame_count
    )


if __name__ == "__main__":
    raise SystemExit(main())
