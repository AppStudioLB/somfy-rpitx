import subprocess
import unittest

from somfy_rpitx.config import Settings
from somfy_rpitx.modulation import FSKSettings
from somfy_rpitx.pulses import Pulse
from somfy_rpitx.transmitter import RpitxTransmitter


class TransmitterTests(unittest.TestCase):
    def test_disabled_transmission_fails_before_other_checks(self) -> None:
        backend = RpitxTransmitter(Settings(), geteuid=lambda: 0)
        with self.assertRaisesRegex(RuntimeError, "disabled"):
            backend.validate()

    def test_unresolved_tones_are_rejected(self) -> None:
        settings = Settings(transmit_enabled=True)
        backend = RpitxTransmitter(settings, geteuid=lambda: 0)
        with self.assertRaisesRegex(RuntimeError, "unresolved"):
            backend.validate()

    def test_root_is_required(self) -> None:
        settings = Settings(
            rf=FSKSettings(deviation_hz=2_500),
            transmit_enabled=True,
        )
        backend = RpitxTransmitter(settings, geteuid=lambda: 1000)
        with self.assertRaises(PermissionError):
            backend.validate()

    def test_backend_is_invoked_without_a_shell(self) -> None:
        calls = []

        def runner(arguments, **kwargs):
            calls.append((arguments, kwargs))
            return subprocess.CompletedProcess(arguments, 0, "", "native summary")

        settings = Settings(
            rf=FSKSettings(deviation_hz=2_500, invert_mark_space=True),
            transmitter_executable="somfy-rpitx-tx",
            transmit_enabled=True,
        )
        backend = RpitxTransmitter(
            settings,
            runner=runner,
            which=lambda _: "/usr/local/bin/somfy-rpitx-tx",
            geteuid=lambda: 0,
        )
        validated = backend.validate()
        log = backend.transmit(
            [
                Pulse(True, 644, "data", 0),
                Pulse(False, 700, "inter-frame-gap", 0),
            ],
            validated,
        )

        arguments, kwargs = calls[0]
        self.assertEqual(arguments[0], "/usr/local/bin/somfy-rpitx-tx")
        self.assertIn("--invert-mark-space", arguments)
        self.assertEqual(kwargs["input"], "1 644\n-1 700\n")
        self.assertNotIn("shell", kwargs)
        self.assertEqual(log, "native summary")

    def test_backend_failure_is_reported(self) -> None:
        def runner(arguments, **kwargs):
            return subprocess.CompletedProcess(arguments, 7, "", "DMA failed")

        settings = Settings(
            rf=FSKSettings(deviation_hz=2_500),
            transmit_enabled=True,
        )
        backend = RpitxTransmitter(
            settings,
            runner=runner,
            which=lambda _: "/fake/backend",
            geteuid=lambda: 0,
        )
        with self.assertRaisesRegex(RuntimeError, "DMA failed"):
            backend.transmit([Pulse(True, 644, "data", 0)])


if __name__ == "__main__":
    unittest.main()
