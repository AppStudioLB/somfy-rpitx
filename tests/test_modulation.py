import unittest

from somfy_rpitx.modulation import (
    FSKSettings,
    carrier_enabled_for_pulse,
    modulate,
)
from somfy_rpitx.pulses import Pulse


class ModulationTests(unittest.TestCase):
    def test_no_deviation_is_deliberately_unresolved(self) -> None:
        self.assertIsNone(FSKSettings().resolve())

    def test_center_and_deviation_resolve_symmetric_tones(self) -> None:
        fsk = FSKSettings(
            center_frequency_hz=447_700_000,
            deviation_hz=12_500,
        ).resolve()
        assert fsk is not None
        self.assertEqual(fsk.mark_frequency_hz, 447_712_500)
        self.assertEqual(fsk.space_frequency_hz, 447_687_500)

    def test_explicit_tones_take_precedence(self) -> None:
        fsk = FSKSettings(
            deviation_hz=9_999,
            mark_frequency_hz=447_703_000,
            space_frequency_hz=447_697_500,
        ).resolve()
        assert fsk is not None
        self.assertEqual(fsk.mark_frequency_hz, 447_703_000)
        self.assertEqual(fsk.space_frequency_hz, 447_697_500)
        self.assertEqual(fsk.source, "explicit mark/space")

    def test_mark_and_space_must_be_a_pair(self) -> None:
        with self.assertRaises(ValueError):
            FSKSettings(mark_frequency_hz=447_701_000)

    def test_invert_setting_requires_a_json_boolean(self) -> None:
        with self.assertRaisesRegex(ValueError, "invert_mark_space"):
            FSKSettings.from_mapping({"invert_mark_space": "false"})

    def test_inversion_changes_logical_mapping_only(self) -> None:
        normal = FSKSettings(deviation_hz=1_000).resolve()
        inverted = FSKSettings(deviation_hz=1_000, invert_mark_space=True).resolve()
        assert normal is not None and inverted is not None
        self.assertEqual(normal.frequency_for_level(True), normal.mark_frequency_hz)
        self.assertEqual(
            inverted.frequency_for_level(True), inverted.space_frequency_hz
        )

    def test_modulation_preserves_timing_and_metadata(self) -> None:
        fsk = FSKSettings(deviation_hz=1_000).resolve()
        assert fsk is not None
        pulses = (Pulse(True, 644, "data[00]=1", 0),)
        event = modulate(pulses, fsk)[0]
        self.assertEqual(event.duration_us, 644)
        self.assertEqual(event.phase, "data[00]=1")
        self.assertEqual(event.frequency_hz, fsk.mark_frequency_hz)
        self.assertTrue(event.carrier_enabled)

    def test_rts_silences_disable_the_carrier(self) -> None:
        wakeup_low = Pulse(False, 7_072, "wakeup", 0)
        inter_frame = Pulse(False, 26_838, "inter-frame-gap", 0)
        data_low = Pulse(False, 644, "data[00]=1", 0)
        self.assertFalse(carrier_enabled_for_pulse(wakeup_low))
        self.assertFalse(carrier_enabled_for_pulse(inter_frame))
        self.assertTrue(carrier_enabled_for_pulse(data_low))

        fsk = FSKSettings(deviation_hz=3_000).resolve()
        assert fsk is not None
        events = modulate((wakeup_low, inter_frame, data_low), fsk)
        self.assertEqual(events[0].frequency_hz, None)
        self.assertEqual(events[1].frequency_hz, None)
        self.assertEqual(events[2].frequency_hz, fsk.space_frequency_hz)


if __name__ == "__main__":
    unittest.main()
