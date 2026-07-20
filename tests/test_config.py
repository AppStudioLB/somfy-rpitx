import json
import tempfile
import unittest
from pathlib import Path

from somfy_rpitx.config import Settings, load_settings


class ConfigTests(unittest.TestCase):
    def test_missing_file_uses_unresolved_safe_defaults(self) -> None:
        settings = load_settings(Path("/definitely/missing/somfy.json"))
        self.assertFalse(settings.transmit_enabled)
        self.assertIsNone(settings.rf.resolve())

    def test_load_explicit_frequencies(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config.json"
            path.write_text(
                json.dumps(
                    {
                        "rf": {
                            "center_frequency_hz": 447_700_000,
                            "mark_frequency_hz": 447_703_000,
                            "space_frequency_hz": 447_697_000,
                            "invert_mark_space": True,
                        },
                        "transmit_enabled": True,
                    }
                ),
                encoding="utf-8",
            )
            settings = load_settings(path)
        self.assertTrue(settings.transmit_enabled)
        self.assertTrue(settings.rf.invert_mark_space)

    def test_unknown_key_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            Settings.from_mapping({"frequency": 447_700_000})

    def test_string_false_cannot_accidentally_enable_transmission(self) -> None:
        with self.assertRaisesRegex(ValueError, "transmit_enabled"):
            Settings.from_mapping({"transmit_enabled": "false"})


if __name__ == "__main__":
    unittest.main()
