# DU-E5000 M4.4.8 maximum-assist reverse-engineering status

## Result

The exact M4.4.8 motor image is a Renesas RX application mapped at
`0xFFFC0000`, not M16C and not a base-zero image. Loading it with the community
[Ghidra RX processor module](https://github.com/redballoonsecurity/rx-proc-ghidra)
produces coherent code and ROM/RAM references. This correction invalidates the
earlier base-zero/M16C scratch interpretations.

The corrected static pass has not identified a category-16 B0 handler in this
secondary motor-control image. That is no longer a missing acceptance-policy
gap: exact D4.5.0 analysis recovered the B0/B4/BC dispatcher and persistent B0
policy in the D application. Apparent direct B0/A0/A8 hits in the first M-image
scalar and byte-sequence sweeps were instruction encodings, low RAM addresses,
or calibration/control tables—not command dispatch entries. They must not be
used as evidence of an M-side protocol handler.

## Exact artifact and mapping

- Artifact: `DUE5000-M.4.4.8.dat`
- Size: 119,824 bytes
- SHA-256:
  `9ea350e988345a9d9fb41c1363562ca190f1a8d5e1cc8a38c6373f69b877f033`
- Architecture: Renesas RX
- Image base used for the corrected project: `0xFFFC0000`
- Header entry pointer at file offset `0x14`: `0xFFFC0018`
- Ghidra processor module revision inspected:
  `redballoonsecurity/rx-proc-ghidra@af8e7ddeb2a4e30cced895fee6bb9ffd1c9ed918`

The first word is the file size (`0x1D410`), not an entry point. Seeding the
real `0xFFFC0018` entry in a clean project produces coherent RX startup code:
it initializes ISP/EXTB/INTB, invokes the initialization chain, copies the
`_UPDATE_` marker, and calls through the pointer at `0xFFFC8A04`. Full analysis
then recovers 904 functions. The base is independently supported by coherent
internal references into the RX internal-ROM range. The vendor image remains
outside Git.

## Bounded findings

Searches covered immediate operands and rendered operands for `0x16`, `0xA0`,
`0xA8`, `0xB0`, `0xB2`, `0xB4`, `0xB6`, `0xBC`, `0xBE`, 2500 (`0x09C4`), and
3200 (`0x0C80`), followed by contextual disassembly/decompilation of the hits.

- The B0/B6/A0/A8 references inside recovered functions near `0xFFFD78F1`
  and `0xFFFD843E` address low RAM locations such as `0xB0`; they are not wire
  opcodes.
- Raw `16 B0` pairs at file offsets `0x62B5`, `0xEECA`, and `0xF389` occur in
  calibration data or RX instruction encodings rather than a command table.
- Recovered `0x0C80` and `0x09C4` comparisons occur in motor-control and
  hardware/configuration initialization contexts. No inspected reference ties
  either constant to category-16 packet parsing or persistent maximum-assist
  state.
- The D4.5.0 application contains explicit cumulative-dispatch cases for B0,
  B4, and BC. Its B0 handler enforces the current destination's ceiling and
  persists record `0x28`; the M image therefore need not contain the wire-
  protocol dispatcher. See `max-assist-speed-analysis.md`.

The absence of a recovered direct immediate is only bounded negative evidence.
The opcode may be decoded through indexed tables, subtraction/range dispatch,
or a packet structure not yet typed by Ghidra.

## Reproducible tooling and next discriminator

`tools/GhidraDumpInstructions.java`, `tools/GhidraFindInstructionScalars.java`,
`tools/GhidraListFunctions.java`, and `tools/GhidraSearchDecompiled.java` are
reusable headless-Ghidra scripts. The scalar finder includes a rendered-
operand fallback for processor modules that do not expose immediates as
Ghidra `Scalar` objects; `--defined-only` keeps a clean entry-seeded program
from being polluted by speculative linear disassembly. The decompiler and
address-reference helpers support focused follow-up.

The next useful M-image step is data-flow work only if a D-side recalculation
or enforcement question remains after a live B0 test. A real B4/BC/B0
notification transcript would still anchor cross-MCU state, but recovering a
second wire dispatcher is no longer a prerequisite. Repeating raw byte or
immediate scans without such an anchor is not informative.
