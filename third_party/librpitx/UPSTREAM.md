# Vendored librpitx subset

This directory contains the `fskburst` implementation and its transitive DMA,
GPIO, mailbox, Raspberry Pi revision, and utility dependencies from
[F5OEO/librpitx](https://github.com/F5OEO/librpitx).

- Upstream commit: `f01bdb64bcdb6207f448379193bc0a8accb9aa22`
- Upstream commit date: 2024-03-11
- License: GPL-3.0; see `LICENCE.txt`
- Imported files: `src/fskburst.*`, `src/dma.*`, `src/gpio.*`, `src/util.*`,
  `src/mailbox.*`, `src/raspberry_pi_revision.*`, and `src/rpi.*`

Local changes are limited to normalizing the missing final newline in
`src/util.h` and adding a bounded DMA-completion wait plus explicit GPIO 4
clock shutdown in `src/fskburst.*`. The wait follows the calculated PCM burst
duration with a 20 ms scheduling margin before resetting a sticky DMA ACTIVE
bit. This prevents a completed RF transmission from leaving the CLI blocked
forever without adding a long delay after every frame. The project-level
Makefile builds only these files into a private static archive. It deliberately
does not use upstream's legacy
`/opt/vc/include`, `/opt/vc/lib`, or `-lbcm_host` flags: the selected source
already implements the two required `bcm_host_*` address lookups in `src/rpi.c`
using the Linux device tree.

The resulting `somfy-rpitx-tx` executable is linked with GPL-3.0 code and must
be distributed under GPL-3.0-compatible terms. The rest of this project's
separately usable source remains under its top-level MIT license.
