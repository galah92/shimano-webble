# PCE transport and old wired-client analysis

This note records the 2026-09-24 audit of E-TUBE Professional 3.4.5's
SM-PCE transport, its bundled adapter firmware, the public `freeMax` client,
and the published wired destination patch. It is deliberately bounded: no
vendor binary, complete decompilation, private capture, passkey, or serial is
committed here.

## Examined artifacts

| Artifact | Bytes | SHA-256 |
| --- | ---: | --- |
| E-TUBE Professional 3.4.5 archive | 60,529,291 | `62266eedf48e9a8f6ec25dd68c9c899f405bf41d9bf9fe3931786877644d4787` |
| `etubedatalinks.dll` | 851,456 | `814d8096d9f6e5552d8131ff840d3bf407b0f0b089c9a0a821cbb34f141e5ab5` |
| `smpce1com.dll` | 82,944 | `c34eab626b4d31bb5dd1084569902fe43f0db205ea4572d16ec472e4c7c61e2b` |
| SM-PCE1 3.1.3 adapter image | 28,867 | `ae1ac59063db670b684063a2738f5dd91e6801e049f6bdf5ca5a6a708a875fac` |
| SM-PCE1 3.0.2 adapter image | 28,867 | `be92d5bb2542f0cba61123203e7b5d44b6b3244c4abbf2f1649d1c9312dbc152` |
| SM-PCE02 3.0.4 adapter image | 64,360 | `93e7889d678ec943cd99b32ba193777df1dacff86558b666d37147f72298d777` |
| public SM-PCE1 top-board photograph | 1,065,052 | `7f040130ac6cffc572e9af2cd08f29766551ff71e1955aa3ad96a39d0feab4a3` |
| public `freeMax.exe` | 128,000 | `fbe73c0ad4644fcad2607fc7ce3d164676ae42044dd49eed7848b8bb65643042` |

The E-TUBE archive came from the
[BetterShifting archive](https://bettershifting.com/e-tube-project-archive/).
`freeMax.exe` is the executable published with
[`rolandvs/shimano`](https://github.com/rolandvs/shimano). The hashes identify
the exact bytes examined; neither source is a Shimano authenticity guarantee.

## The managed host sends generic frames

Managed IL from `etubedatalinks.dll` exposes the entire normal unit-command
path:

1. `UnitCommandSetting.Make` records the application slot, command group,
   opcode, and parameters. It has no opcode-specific transport hook.
2. `EtubeDataLinksUnitCommand.SendUnitCommandData` builds the unit-command
   payload and calls `DataLinksMain.SendDCASRawPacketCommand`.
3. `SendReceiveUnitCommand` obtains the same setting's `SendData` and calls
   `DataLinksMain.WriteData` with control byte `0x48`.
4. `SendDCASRawPacketCommand` prepends the target address and delegates to the
   same generic `WriteData` method.
5. `WriteData` calls `CreateWriteData`, logs the frame, applies only the known
   PCE02 packet padding when required, and writes the resulting bytes to the
   serial transport.
6. `CreateWriteData` prepends the control byte and appends the FCS.
   `Common.CreateFCS` is the two's-complement byte sum, while
   `Common.CreateFrame` performs framing and byte escaping.

The protected-mode path is equally direct. `SendSetPCLinkModeStart` sends the
ordinary category-`32`, opcode-`10` request, then the five selected secure
words, and waits for opcode `12`. The regulation-unlock helper sends category
`16`, opcode `E8` after its challenge calculation. These are protocol
commands, not adapter-control side channels.

There is therefore no host-library location in this call chain that can
silently insert an `A0` before destination opcode `A8`, rewrite A8, or turn a
direct destination call into a compound transaction. This is stronger than a
search for byte literals: it follows the constructors through the serial
write boundary.

## Independent `freeMax` serial evidence

The 2018 `freeMax.exe` is a mixed managed/native .NET program that opens an
SM-PCE1 or SM-BCR2 serial port directly. Its transmit helper writes logical
bytes to `SerialPort.BaseStream.WriteByte`; it changes only framing escapes:
logical `BB` becomes `BD 9B`, and logical `BD` becomes `BD 9D`. Its receive
helper reverses those mappings.

The program's assistance workflow contains ordinary complete logical frames,
including:

```text
48 00 01 14 00 A3 BB
48 00 32 10 01 0B 00 00 6A BB
48 00 32 B4 00 D2 BB
48 00 16 9C 03 03 BB
48 00 16 9C 02 04 BB
48 00 16 9C 01 05 BB
```

The first byte is the `0x48` control byte, the middle bytes are the direct
DCAS unit command, the penultimate byte is the FCS, and `BB` terminates the
logical frame. The client hands those frames straight to the adapter; it does
not invoke an E-TUBE host library that could synthesize extra unit commands.
This independently argues against a *general* PCE command-expansion layer.

## Adapter-update files do not reveal a host transform

The managed adapter-update path treats both bundled `.dat` files as raw byte
arrays:

- `FirmwareFile.BinaryData` is populated by `ReadAllBytes`;
- `PcInterfaceUnit.SendUpdateData` passes that array to
  `DataLinksFirmware.SendUpdateData`;
- `GetDivisionData` chunks it and pads only the portion beyond end-of-file
  with `FF` while updating packet checksums;
- optional `CompressionData` performs packet-level run-length compression and
  falls back to the original chunk when compression would exceed the packet
  limit; and
- `convertIfNeed` maps boot commands for PCE02 but does not transform firmware
  payload bytes.

For PCE1, the update startup sends write address `00 40 00`. A
[public board photograph](https://github.com/rolandvs/shimano/blob/master/pictures/SM-PCE1-PCB-TOP.jpg)
shows a 32-pin Renesas part whose marking is consistent with `D78F1807`, the
64-KiB µPD78F1807 member of the 78K0R/FB3 family. Renesas' official
[78K0R instruction manual](https://www.renesas.com/en/document/mas/78k0r-microcontrollers-users-manual-instructions)
and [supported-device list](https://www.renesas.com/en/document/mat/list-mcus-supported-renesas-flash-programmer-v2)
corroborate that family and part number. The `0x4000` write start is therefore
consistent with a resident 16-KiB bootloader below the application region.

The update file itself is not yet a decoded flat application image. Both exact
3.0.2 and 3.1.3 files begin with a structured offset-like table and contain a
version record (`05 30 02 00` or `05 31 03 00`), while their apparent offsets
do not decode as plausible 78K0R entry points. The managed host passes those
bytes directly to the PCE1 update protocol, apart from optional per-packet RLE,
so any image-layout or package transformation must occur in the adapter's
bootloader or be inherent in the stored format. The absence of plaintext
`16 A0` or `16 A8` in these package bytes is consequently not evidence that
the running firmware lacks such handling. PCE1's CPU family is identified;
its update-package layout and opcode behavior remain undecoded.

## Exact PCE02 firmware rules out destination-command magic

The SM-PCE02 3.0.4 file is a coherent little-endian ARM Thumb image at load
base `0x10000`. At file offset `0x5e4`, its vector-like pair is stack pointer
`0x20000868` and Thumb reset handler `0x1aba1`. The startup records copy a
28-byte group/opcode table from file offset `0xf7f4` to RAM `0x2000000c`.

The receive parser at `0x11128` reverses `BD` escaping, bounds a logical frame,
and terminates it at `BB`. Dispatcher `0x11240` routes control `0x48` to
function `0x166e2`. That handler accepts a short logical frame, strips its
control and slot bytes, prepends its internal length/type fields, and copies
every remaining group/opcode/parameter byte unchanged into the bus-send path:

```text
0x166e2 -> 0x1873c -> 0x19206 -> 0x1b8a4 -> 0x1beec -> 0x1e15c
```

The only opcode-aware decision in that chain is function `0x1bc42`. It checks
the copied command against this exact 14-pair table:

```text
30 2A   01 18   01 1A   01 2C   01 2E   01 0C   01 0E
01 24   01 26   01 5C   01 5E   02 08   01 00   01 02
```

Neither `16 A0` nor `16 A8` is present. Function `0x1e15c` consequently sends
`16 A8` through its ordinary one-, two-, or three-cell packetizer based on
length. It neither synthesizes A0 nor rewrites A8. The exact bounded function
fingerprints are:

| Function | Address | Bytes | SHA-256 |
| --- | ---: | ---: | --- |
| control dispatcher | `0x11240` | 596 | `9495460b265189a6b67510fb9c45ec309f64b95d61d33fda68b0f55ad70ab857` |
| generic `0x48` handler | `0x166e2` | 56 | `781591b9893e7af20d24354d629694ca7fe7a444e2d9d96b0e63a4091c07f948` |
| special-pair checker | `0x1bc42` | 72 | `6603c41ff4e563a2bbd700bb1db6d61dfcfe33da0fe5328e98c8f22c7c752ec1` |
| bus packetizer | `0x1e15c` | 320 | `e5d21ee99eb958ce609fa2ba53712d81c1ab2aae56a24610f61d183aa66a4fe4` |

[`tools/inspect_pce02_transport.py`](../../tools/inspect_pce02_transport.py)
checks the exact image fingerprint, vector, initializer record, 14-pair table,
and these function slices without committing or printing vendor bytes. This is
exact-image static evidence, not a live adapter trace. It does, however,
exclude the previously open narrow-A8 special case for PCE02 3.0.4.

## The published wired patch does not satisfy the motor gate in shown order

The public
[wired E5000 guide](https://forums.electricbikereview.com/threads/derestricting-a-shimano-steps-e-bike.54485/)
patches E-TUBE's `SetTireCircumference` path to call
`DUUnitDataLink.SetDestination(slotNo, 1, 1)` first. Selector `1`, value `1`
is the OEM US destination. The same guide forces
`ProcessRegulationSetAuth`, which explains the regulation challenge/unlock but
not the motor's separate A0-created destination gate.

Exact IL ordering matters. `DriveUnitSetProgressPanel.setWorker_DoWork` calls
`SetTireCircumference` at offset `0x0182`. Its only `SetLightingTime` call is
much later at `0x0481`, conditional on lighting-time support and a changed
value. The inspection panel also exposes destination and lighting as separate
button handlers. Consequently, the published injection sends A8 before any
possible later A0; it cannot arm the verified D4.1/D4.3/D4.5 one-shot gate by
that call order.

The report is still relevant outcome evidence for a wired system. It is not a
complete causal trace. At least one prerequisite is missing from the public
description: retained motor state, an earlier unobserved command, a different
firmware context, or another omitted workflow step are still possible. The
exact PCE02 path shows that adapter does not supply the missing A0 or transform
A8. PCE1's running image remains undecoded, but the published guide explicitly allowed PCE02,
so PCE1-specific behavior cannot explain the reported PCE02-capable recipe.

## Current conclusion

The evidence now rules out a hidden A0 or destination rewrite in the normal
E-TUBE 3.4.5 managed-host transport and in the exact PCE02 3.0.4 `0x48` unit-
command path. An independent direct-serial client also sends ordinary DCAS
frames through this class of hardware. PCE1 is identified as 78K0R/FB3 but its
packaged running firmware remains undecoded; nevertheless,
there is no known adapter-side mechanism that explains the published wired
result.

Nothing here changes the live bike result: destination remains verified EU,
and no higher cutoff has been measured. The best-supported no-new-hardware
experiment remains build 82's display-owned mode 5, explicit unchanged A0,
fresh display-owned mode 5, one A8, readback, and exit sequence. It is local,
unpublished, and untested on the bike. The established BLE fallback remains a
paired D4.3.0/M4.2.1 preparation and restoration, with real wireless-flashing
and wired-recovery risk.
