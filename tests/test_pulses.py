import unittest

from somfy_rpitx.protocol import Command, RTSFrame
from somfy_rpitx.pulses import SITUO5_TIMINGS, TimingProfile, generate_pulses


class PulseTests(unittest.TestCase):
    def setUp(self) -> None:
        self.frame = RTSFrame(Command.UP, 0, 0xC0FFEE)

    def test_initial_frame_shape_matches_open_rts(self) -> None:
        pulses = generate_pulses(self.frame, frame_count=1)
        self.assertEqual(len(pulses), 121)
        self.assertEqual(
            [(pulse.level, pulse.duration_us) for pulse in pulses[:8]],
            [
                (True, 10_568),
                (False, 7_072),
                (True, 2_585),
                (False, 2_436),
                (True, 2_585),
                (False, 2_436),
                (True, 4_898),
                (False, 644),
            ],
        )
        self.assertEqual(pulses[-1].duration_us, 26_838)

    def test_repeat_has_seven_sync_pairs_and_no_wakeup(self) -> None:
        pulses = generate_pulses(self.frame, frame_count=2)
        repeat = [pulse for pulse in pulses if pulse.frame_index == 1]
        self.assertEqual(len(repeat), 129)
        self.assertEqual(repeat[0].phase, "hardware-sync")
        self.assertEqual(
            sum(pulse.phase == "hardware-sync" for pulse in repeat),
            14,
        )

    def test_three_frames_reuse_same_payload(self) -> None:
        pulses = generate_pulses(self.frame, frame_count=3)
        self.assertEqual(len(pulses), 121 + 129 + 129)
        data_by_frame = [
            [(p.level, p.duration_us) for p in pulses if p.frame_index == index and p.phase.startswith("data")]
            for index in range(3)
        ]
        self.assertEqual(data_by_frame[0], data_by_frame[1])
        self.assertEqual(data_by_frame[1], data_by_frame[2])

    def test_manchester_edges(self) -> None:
        pulses = generate_pulses(self.frame, frame_count=1)
        data = [pulse for pulse in pulses if pulse.phase.startswith("data")]
        first_bit = self.frame.bits_msb_first()[0]
        expected = [(True, False), (False, True)][first_bit]
        self.assertEqual((data[0].level, data[1].level), expected)
        self.assertEqual(data[0].duration_us, SITUO5_TIMINGS.half_symbol_us)

    def test_timing_profile_is_configurable(self) -> None:
        timing = TimingProfile.from_mapping({"half_symbol_us": 604})
        self.assertEqual(timing.half_symbol_us, 604)
        self.assertEqual(timing.wakeup_high_us, 10_568)

    def test_invalid_frame_count(self) -> None:
        with self.assertRaises(ValueError):
            generate_pulses(self.frame, frame_count=0)


if __name__ == "__main__":
    unittest.main()
