from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class InstallLayoutTests(unittest.TestCase):
    def test_bookworm_install_uses_a_dedicated_virtual_environment(self):
        makefile = (ROOT / "Makefile").read_text(encoding="utf-8")
        self.assertIn("VENV_DIR ?= /opt/somfy-rpitx", makefile)
        self.assertIn("-m venv --system-site-packages", makefile)
        self.assertIn("pip install --no-deps --no-build-isolation", makefile)
        self.assertNotIn('pip install . --prefix=', makefile)

    def test_cli_links_are_installed_on_path(self):
        makefile = (ROOT / "Makefile").read_text(encoding="utf-8")
        self.assertIn('$(PREFIX)/bin/somfy-rpitx"', makefile)
        self.assertIn('$(PREFIX)/bin/somfy-rpitx-homebridge"', makefile)


if __name__ == "__main__":
    unittest.main()
