import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from somfy_rpitx.cli import main


class CliTests(unittest.TestCase):
    def test_dry_run_prog_does_not_consume_rolling_code(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            config = root / "config.json"
            state = root / "state.json"
            config.write_text(
                json.dumps(
                    {
                        "rf": {
                            "center_frequency_hz": 447_700_000,
                            "deviation_hz": 2_500,
                        }
                    }
                ),
                encoding="utf-8",
            )
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                first = main(
                    [
                        "--config",
                        str(config),
                        "--state-file",
                        str(state),
                        "dry-run",
                        "prog",
                    ]
                )
                second = main(
                    [
                        "--config",
                        str(config),
                        "--state-file",
                        str(state),
                        "dry-run",
                        "prog",
                    ]
                )
            persisted = json.loads(state.read_text(encoding="utf-8"))

        self.assertEqual((first, second), (0, 0))
        self.assertEqual(persisted["next_rolling_code"], 1)
        self.assertEqual(output.getvalue().count("command: PROG (0x8)"), 2)
        self.assertIn("frame_count: 4", output.getvalue())

    def test_unresolved_actual_command_does_not_create_state(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            state = Path(directory) / "state.json"
            error = io.StringIO()
            with contextlib.redirect_stderr(error):
                result = main(["--state-file", str(state), "up"])
            self.assertEqual(result, 1)
            self.assertFalse(state.exists())
            self.assertIn("unresolved", error.getvalue())


if __name__ == "__main__":
    unittest.main()
