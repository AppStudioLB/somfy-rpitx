import contextlib
import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from somfy_rpitx import homebridge_helper


class HomebridgeHelperTests(unittest.TestCase):
    def test_valid_request_is_forwarded_to_cli(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            config = root / "config.json"
            config.write_text("{}\n", encoding="utf-8")
            state_directory = root / "state"
            state_directory.mkdir()
            state = state_directory / "blind-1.json"
            calls = []

            with (
                patch.object(homebridge_helper, "DEFAULT_CONFIG_PATH", config),
                patch.object(
                    homebridge_helper,
                    "DEFAULT_STATE_DIRECTORY",
                    state_directory,
                ),
            ):
                result = homebridge_helper.main(
                    ["--config", str(config), "--state-file", str(state), "up"],
                    run_cli=lambda argv: calls.append(list(argv)) or 0,
                    geteuid=lambda: 0,
                )

        self.assertEqual(result, 0)
        self.assertEqual(
            calls,
            [["--config", str(config), "--state-file", str(state), "up"]],
        )

    def test_non_root_and_paths_outside_fixed_directories_are_rejected(self) -> None:
        error = io.StringIO()
        with contextlib.redirect_stderr(error):
            non_root = homebridge_helper.main(
                [
                    "--config",
                    "/etc/somfy-rpitx/config.json",
                    "--state-file",
                    "/var/lib/somfy-rpitx/blind-1.json",
                    "down",
                ],
                geteuid=lambda: 1000,
            )
        self.assertEqual(non_root, 1)
        self.assertIn("must run as root", error.getvalue())

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            config = root / "config.json"
            config.write_text("{}\n", encoding="utf-8")
            state_directory = root / "state"
            state_directory.mkdir()
            error = io.StringIO()
            with (
                patch.object(homebridge_helper, "DEFAULT_CONFIG_PATH", config),
                patch.object(
                    homebridge_helper,
                    "DEFAULT_STATE_DIRECTORY",
                    state_directory,
                ),
                contextlib.redirect_stderr(error),
            ):
                outside = homebridge_helper.main(
                    [
                        "--config",
                        str(config),
                        "--state-file",
                        str(root / "outside.json"),
                        "stop",
                    ],
                    geteuid=lambda: 0,
                )
        self.assertEqual(outside, 1)
        self.assertIn("directly inside", error.getvalue())

    def test_prog_is_not_an_allowed_helper_action(self) -> None:
        with contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit):
                homebridge_helper.main(
                    [
                        "--config",
                        "/etc/somfy-rpitx/config.json",
                        "--state-file",
                        "/var/lib/somfy-rpitx/blind-1.json",
                        "prog",
                    ]
                )


if __name__ == "__main__":
    unittest.main()
