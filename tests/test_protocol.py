import unittest

from somfy_rpitx.protocol import Command, RTSFrame, checksum, deobfuscate, obfuscate


class ProtocolTests(unittest.TestCase):
    def test_open_rts_reference_vector(self) -> None:
        frame = RTSFrame(Command.UP, rolling_code=123, remote_address=0xFACADE)
        self.assertEqual(frame.clear_bytes(), bytes.fromhex("AB 2F 00 7B DE CA FA"))
        self.assertEqual(checksum(frame.clear_bytes()), 0)

    def test_obfuscation_reference_vector(self) -> None:
        clear = bytes.fromhex("A3 29 1E 63 EE 1F 42")
        encoded = bytes.fromhex("A3 8A 94 F7 19 06 44")
        self.assertEqual(obfuscate(clear), encoded)
        self.assertEqual(deobfuscate(encoded), clear)

    def test_address_is_little_endian(self) -> None:
        frame = RTSFrame(Command.DOWN, 0x1234, 0xA1B2C3)
        self.assertEqual(frame.clear_bytes()[4:], bytes.fromhex("C3 B2 A1"))

    def test_all_required_commands(self) -> None:
        expected = {"up": 2, "down": 4, "stop": 1, "prog": 8}
        for name, value in expected.items():
            with self.subTest(name=name):
                self.assertEqual(Command.from_cli(name), value)

    def test_bits_are_msb_first(self) -> None:
        frame = RTSFrame(Command.PROG, 1, 0x010203)
        bits = frame.bits_msb_first()
        self.assertEqual(len(bits), 56)
        self.assertEqual(bits[:8], tuple(int(bit) for bit in "10100001"))

    def test_range_validation(self) -> None:
        with self.assertRaises(ValueError):
            RTSFrame(Command.UP, 0x10000, 1)
        with self.assertRaises(ValueError):
            RTSFrame(Command.UP, 1, 0x1000000)


if __name__ == "__main__":
    unittest.main()
