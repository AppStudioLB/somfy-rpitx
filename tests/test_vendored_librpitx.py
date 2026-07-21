import hashlib
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class VendoredLibrpitxTests(unittest.TestCase):
    EXPECTED_SHA256 = {
        "fskburst.cpp": "b8ef315794d02223717f93849e5dd4a94f70e9ebfec4cabc85a5f629b93b6ab8",
        "fskburst.h": "43be6c6b9a8502675f94bf102f200035d44a3a916c2f4cb8cf4e7b196125ecc1",
        "dma.cpp": "524800e3d08e8c3cb9a3c8dd3fb8ee8fab9cdffcc36803ce5efb8ae784b2501a",
        "dma.h": "b05820668b54c594658397832bb30f165dff4e039e27910dee0e2d6a98069389",
        "gpio.cpp": "d6c4d19308fb6a3184b42aaab166a0d026cf88bf8ac0ed1bc550fc8c9533ce98",
        "gpio.h": "a7aa0a3a850b3b040ec76876ca149f00ff98816f073ac02a18bf24d861a87f9e",
        "util.cpp": "114e363378763a1b0c22606ef27d8580dec5089d43d7628dc1be61ab60f2202e",
        "util.h": "edc6f3f58ef972dae71ea632a65d4cb814d51509d2c57d004a50460ede3219f2",
        "mailbox.c": "71eb55da72cf0f385729faa79a0f2b2cda43deb379c253b4546ebeaad040e9b6",
        "mailbox.h": "024f61224df45eadd9489bf853526c9fc6b598ed3a8ece29b2d7c1d7843d219f",
        "raspberry_pi_revision.c": "65b71499eb5ce0edd652bf222c536131163b331c26b79f10edc4803aa1611f6d",
        "raspberry_pi_revision.h": "6c89b64ea8a53d82f473aa740728a9b0b222d57668a6b7fd5b0c1e2ee9327f4e",
        "rpi.c": "4e0512b6544c61686516a5b0b61773e893ee6e3fbc257844d6b49e2335bc03fa",
        "rpi.h": "b392157ef5ceef640f348ea15292cbdd836d80b9bdc70f5e74dfe231bbe9cef4",
    }

    def test_selected_sources_match_pinned_vendor_snapshot(self):
        source_dir = ROOT / "third_party" / "librpitx" / "src"
        for name, expected in self.EXPECTED_SHA256.items():
            with self.subTest(name=name):
                digest = hashlib.sha256((source_dir / name).read_bytes()).hexdigest()
                self.assertEqual(digest, expected)

        license_digest = hashlib.sha256(
            (ROOT / "third_party" / "librpitx" / "LICENCE.txt").read_bytes()
        ).hexdigest()
        self.assertEqual(
            license_digest,
            "0ae0485a5bd37a63e63603596417e4eb0e653334fa6c7f932ca3a0e85d4af227",
        )

        provenance = (
            ROOT / "third_party" / "librpitx" / "UPSTREAM.md"
        ).read_text(encoding="utf-8")
        self.assertIn("f01bdb64bcdb6207f448379193bc0a8accb9aa22", provenance)

    def test_build_has_no_legacy_videocore_link_dependency(self):
        makefile = (ROOT / "Makefile").read_text(encoding="utf-8")
        self.assertNotIn("/opt/vc", makefile)
        self.assertNotIn("-lbcm_host", makefile)
        self.assertNotIn("-lrpitx", makefile)
        self.assertIn("librpitx-somfy.a", makefile)

    def test_native_backend_uses_the_minimal_header(self):
        source = (ROOT / "native" / "somfy_rpitx_tx.cpp").read_text(
            encoding="utf-8"
        )
        self.assertIn('#include "fskburst.h"', source)
        self.assertNotIn("librpitx/librpitx.h", source)


if __name__ == "__main__":
    unittest.main()
