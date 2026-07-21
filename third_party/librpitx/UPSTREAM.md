# Vendored librpitx subset

This directory contains the unmodified `fskburst` implementation and its
transitive DMA, GPIO, mailbox, Raspberry Pi revision, and utility dependencies
from [F5OEO/librpitx](https://github.com/F5OEO/librpitx).

- Upstream commit: `f01bdb64bcdb6207f448379193bc0a8accb9aa22`
- Upstream commit date: 2024-03-11
- License: GPL-3.0; see `LICENCE.txt`
- Imported files: `src/fskburst.*`, `src/dma.*`, `src/gpio.*`, `src/util.*`,
  `src/mailbox.*`, `src/raspberry_pi_revision.*`, and `src/rpi.*`

The upstream source files are unchanged apart from normalizing the missing
final newline in `src/util.h`. The project-level Makefile builds only these
files into a private static archive. It deliberately does not use upstream's
legacy `/opt/vc/include`, `/opt/vc/lib`, or `-lbcm_host` flags: the selected
source already implements the two required `bcm_host_*` address lookups in
`src/rpi.c` using the Linux device tree.

The resulting `somfy-rpitx-tx` executable is linked with GPL-3.0 code and must
be distributed under GPL-3.0-compatible terms. The rest of this project's
separately usable source remains under its top-level MIT license.
