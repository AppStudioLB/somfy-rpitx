import json
import multiprocessing
import os
import tempfile
import unittest
from pathlib import Path

from somfy_rpitx.storage import StateStore


def _reserve_from_process(path: str) -> int:
    return StateStore(Path(path)).reserve_rolling_code()[1]


class StorageTests(unittest.TestCase):
    def test_create_and_reserve_persists_monotonically(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "state.json"
            store = StateStore(path)
            initial = store.peek_or_create()
            address_1, code_1 = store.reserve_rolling_code()
            address_2, code_2 = store.reserve_rolling_code()
            persisted = json.loads(path.read_text(encoding="utf-8"))

            self.assertEqual(address_1, initial.remote_address)
            self.assertEqual(address_2, initial.remote_address)
            self.assertEqual((code_1, code_2), (1, 2))
            self.assertEqual(persisted["next_rolling_code"], 3)
            self.assertEqual(os.stat(path).st_mode & 0o777, 0o600)
            self.assertTrue(path.with_name("state.json.lock").exists())

    def test_peek_does_not_consume_code(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = StateStore(Path(directory) / "state.json")
            first = store.peek_or_create()
            second = store.peek_or_create()
            self.assertEqual(first, second)

    def test_corrupt_state_is_not_overwritten(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "state.json"
            path.write_text("{broken", encoding="utf-8")
            with self.assertRaises(ValueError):
                StateStore(path).peek_or_create()
            self.assertEqual(path.read_text(encoding="utf-8"), "{broken")

    def test_unknown_state_keys_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "state.json"
            path.write_text(
                json.dumps(
                    {
                        "version": 1,
                        "remote_address": 1,
                        "next_rolling_code": 1,
                        "surprise": True,
                    }
                ),
                encoding="utf-8",
            )
            with self.assertRaises(ValueError):
                StateStore(path).peek_or_create()

    def test_file_lock_serializes_multiple_processes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "state.json"
            StateStore(path).peek_or_create()
            with multiprocessing.Pool(processes=4) as pool:
                codes = pool.map(_reserve_from_process, [str(path)] * 12)
            persisted = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(sorted(codes), list(range(1, 13)))
        self.assertEqual(persisted["next_rolling_code"], 13)


if __name__ == "__main__":
    unittest.main()
