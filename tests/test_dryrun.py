import unittest

from somfy_rpitx.dryrun import render_dry_run
from somfy_rpitx.modulation import FSKSettings
from somfy_rpitx.protocol import Command, RTSFrame
from somfy_rpitx.pulses import generate_pulses


class DryRunTests(unittest.TestCase):
    def test_unresolved_output_is_explicit(self) -> None:
        frame = RTSFrame(Command.PROG, 1, 0x123456)
        output = render_dry_run(
            frame=frame,
            pulses=generate_pulses(frame, frame_count=1),
            rf=FSKSettings(),
        )
        self.assertIn("command: PROG (0x8)", output)
        self.assertIn("mark_frequency_hz: UNSET", output)
        self.assertIn("space_frequency_hz: UNSET", output)
        self.assertIn("rolling code not consumed", output)

    def test_resolved_output_contains_each_tone(self) -> None:
        frame = RTSFrame(Command.UP, 2, 0x123456)
        output = render_dry_run(
            frame=frame,
            pulses=generate_pulses(frame, frame_count=1),
            rf=FSKSettings(deviation_hz=2_500),
        )
        self.assertIn("mark_frequency_hz: 447702500", output)
        self.assertIn("space_frequency_hz: 447697500", output)
        self.assertIn("MARK", output)
        self.assertIn("SPACE", output)
        self.assertIn("OFF", output)


if __name__ == "__main__":
    unittest.main()
