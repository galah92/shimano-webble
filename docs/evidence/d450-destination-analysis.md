# E5000 D4.5.0 destination command analysis

**Historical analysis with a corrected conclusion.** The proposed A0 staging
sequence below was not observed in a real destination-write workflow and was
rejected by the bike. Read “2026-09-12 correction” and
[`HANDOFF.md`](../../HANDOFF.md) before using any packet described here.

## Scope

This note records the static evidence used to replace the proposed firmware
downgrade with a command-only candidate for the tested E5000 motor. The primary
image is `due5000_d.4.5.0.unwrapped.dat`, loaded as little-endian ARM Thumb at
`0x10000`.

| Image | Bytes | SHA-256 |
| --- | ---: | --- |
| E5000 D4.5.0 unwrapped | 138072 | `44806bd54aedff95a88bb73fafe0f0581297f2f67b2ea35545cea012899d90bb` |
| E5000 D4.3.0 reference | 132072 | `3d3df4dfe3de333062f445b6719fa5033f93dc9d384448134ee6041d216c6af0` |

The command shapes were cross-checked against Shimano's desktop
`EtubeDataLinks` managed assemblies. Static analysis can establish implemented
branches and packet construction. It cannot establish that this exact bike will
accept or persist the transaction; that requires readback from the bike.

## Confirmed in D4.5.0

The destination setter remains implemented in D4.5.0. The category `0x16`,
opcode `0xA8` dispatches to `FUN_0002537c` at `0x2537c`. That function contains
no firmware-version comparison and no destination-value rejection branch.

The setter checks two pieces of volatile state before copying the candidate
destination and calling the persistent-record helper at `FUN_00025516`:

1. the current PC mode is `4` or `5`; and
2. the one-shot staging flag is `1`.

If either check fails, or if the persistent-record helper fails, the handler
constructs error `0x3A`. This is the exact error observed on the bike as
`00 16 AB 3A 00`. The observed error therefore does not demonstrate that D4.5.0
removed the setter or rejected US value `1`.

The category `0x16`, opcode `0xA0` handler is `FUN_000252a8` at `0x252a8`.
While PC mode is `4` or `5`, it copies the first part of the same candidate
record and sets the one-shot flag used by `A8`. The corresponding getter is
opcode `0xA4`, handled by `FUN_0002541c` at `0x2541c`.

The internal record is 11 bytes. The persisted copy starts at RAM `0x2000253c`
and the candidate starts at `0x20002548`; the helper compares or persists all
11 bytes. `FUN_0002e57c` reassembles three-byte bus fragments into a normalized
buffer with command category/opcode at offsets 2/3. A cross-check against the
working raw `00 16 AC 01` query establishes the next fields: offset 4 is the
zero motor target address, and public command parameters begin at offset 5.
`FUN_000252a8` checks that target address, then copies five normalized bytes.
Shimano's four public lighting parameters supply the first four; the bridge
supplies the fifth. Earlier builds incorrectly treated all five normalized
bytes as public BLE parameters.

The PC-mode request handler is `FUN_0002721c` at `0x2721c`. A mode-4 or mode-5
request stages that mode and the requesting application slot. The secure-code
handler is `FUN_00027430` at `0x27430`. Once all five 16-bit values match, it
promotes the staged mode to the active byte at RAM `0x200029f9` before sending
the completion response to that slot. The `A0` and `A8` handlers read that same
active byte. A mode-0 request clears the privileged state and performs the
normal exit work.

The D4.5.0 image contains distinct secure tables for modes 1, 4, and 5. The
mode-4 table is at file offset `0x19f8` (loaded address `0x119f8`) and yields the
wire pairs `19 B2`, `73 D8`, `A4 73`, `B1 72`, and `01 10`. The already tested
mode-5 table is at file offset `0x1a04`. Mode 4 is therefore a separately keyed
firmware state, and both destination-related handlers explicitly accept it.

## Confirmed across firmware, capture, and Shimano applications

The managed desktop library constructs the protected-mode sequence and generic
setter payloads. The supplied official capture contains 241 writes to the motor
characteristic and none exceeds seven bytes. This is not a hard protocol limit:
Android eTuning 3.0.7 contains direct nine-byte writes to the same characteristic
in `G5`. The captured `A4` reply is
`00 16 A6 0A 00 FF FF A4 01 FF`; the managed getter declares only `0A 00` as
the lighting-time parameters. The later bytes are bridge envelope data.

| Operation | Packet sent through the drive-unit channel |
| --- | --- |
| Enter PC mode 5 through desktop adapter slot 0 | `00 32 10 05 00 00 00` |
| Secure word 1 | `00 32 30 27 0F 00 00` |
| Secure word 2 | `00 32 30 11 55 00 00` |
| Secure word 3 | `00 32 30 35 B0 00 00` |
| Secure word 4 | `00 32 30 03 F3 00 00` |
| Secure word 5 | `00 32 30 09 03 00 00` |
| Read lighting time | `00 16 A4 00`; decode the first two `A6` parameters as little-endian `UInt16` |
| Generic Android/desktop lighting setter | `00 16 A0 <low> <high> FF FF` |
| Read OEM destination | `00 16 AC 01`; take the value byte from `AE 01` |
| Android eTuning 3.0.7 region setter | `00 16 A8 01 01` |
| Exit PC mode | `00 32 10 00 00 00 00` |

The library waits 1000 ms after requesting mode 5 when a battery is present,
sends the five secure words with 100 ms spacing, and waits for category `0x32`,
opcode `0x12` completion. Its embedded 5x2 table stores each word as high byte
then low byte, but the transmit loop explicitly takes column 1 before column 0.
The D4.5.0 parser at `FUN_0002c25a` reads the received pair as little-endian.
Build .65 incorrectly transmitted the table's stored order, so the firmware's
secure counter never advanced; build .66 transmits the required low byte first.

`DUUnitDataLink.SetLightingTime` creates four parameters from a static
initializer, copies the little-endian 16-bit lighting value into indices 0 and
1, and sends opcode `A0`. `SetDestination` creates the same four parameters,
then overwrites index 0 with destination selector and index 1 with destination
value. The shared FieldRVA initializer was extracted directly from
`etubedatalinks.dll` at RVA `0xD1560`; its first four bytes are
`FF FF FF FF`. Selector `1` is current/OEM and value `1` is US. These managed
constructors establish the D4.5 staging command's public BLE fields. Build .70
tested it in mode 5; build .73 is the first test pairing it with authenticated
mode 4. Android's actual region call sites in
`eTuning/.../ea/w.java`, `C0545qj`, and `AbstractC0210gc` independently send
`00 16 A8 01 <destination>` without the legacy desktop padding.

## Wireless application slot

The desktop packets above use application slot `00` because its directly
attached data link initializes `PCAppliSlotNo` to zero. That slot is not
portable to the SC-E7000 BLE bridge. In the supplied official eTuning ATT
capture, display setup `00 0C 01` receives its `2C` acknowledgement and is
immediately followed on 2AFD by:

`00 32 12 01 0D FF FF 00 FF FF`

This is a category-32 opcode-12 mode-1 announcement carrying application slot
`0D`.
The managed PC-mode methods place `PCAppliSlotNo` in request parameter 1, and
the D4.5.0 handler saves that parameter before checking the secure words and
sends completion to the saved slot. This supports the hypothesis that a WebBLE
request needs the live wireless application slot (`0D` in this capture), rather
than desktop slot `00`, for its completion to return through SC-E7000. The .68
bike run validated it with exact mode-1 and mode-5 completions carrying slot
`0D`.

The desktop authorization sequence also calls
`DuAuthHelper.UnlockRegulationSetAuth` after the existing challenge-response.
It regenerates the seven-byte serial-derived request and sends category `0x16`,
opcode `0xE8`. The normal reply opcode is `0xEA`; error is `0xEB`. This unlock
is retained as a conservative prerequisite even though the final `A8` handler's
local rejection branch directly tests PC mode and the `A0` staging flag.

## Command-only candidate

The evidence supports this bounded transaction on the exact tested baseline:

1. verify E5000 D4.5.0/M4.4.8 and current destination EU;
2. complete motor challenge-response and require an `E8`/`EA` unlock;
3. obtain the wireless application slot, establish mode 1, then enter PC mode
   4 and require a matching completion response for both stages;
4. read the declared 16-bit `A4/A6` lighting value and require acceptance of
   the same-value stage `A0 <low> <high> FF FF`;
5. save a same-device reconnect expectation;
6. send Android's `A8 01 01` once for OEM selector 1 and US value 1;
7. read destination immediately;
8. exit PC mode on success or failure; and
9. after a physical power cycle, verify the same firmware pair and US value in
   a different BLE session.

No firmware erase, image-data, update-mode, or bootloader command is part of
this candidate.

## Still unresolved

### 2026-09-12 correction: the lighting stage was an inference, not a captured region workflow

The desktop inspection panel has separate `btnDestinationOem_Click` and
`btnLightingTime_Click` handlers. The former calls `SetDestination` directly;
the latter calls `SetLightingTime`. The Android region task in
`C0545qj.java` likewise sends `00 16 A8 01 <destination>` directly. Neither
observed call site pairs a same-value lighting `A0` with a destination `A8`.
The earlier proposed A0 step came solely from the D4.5.0 `A8` handler's
one-shot staging-flag check. It is not an established prerequisite in Shimano's
client-side region sequence.

This matters because the live motor returned `A3 3A` for Shimano's generic
seven-byte lighting packet `00 16 A0 0A 00 FF FF` even after a mode-4 completion.
The D handler uses `3A` for either inactive mode 4/5 or a nonzero normalized
target byte. The observed response does not identify which branch ran or prove
the display forwarded the packet to that handler unchanged. The display reset
reported during the test also leaves mode lifetime uncertain. Repeating A0
with more guessed payloads would not resolve this ambiguity.

Therefore the command-only candidate above remains a historical experiment,
not a validated procedure. Further work should reconstruct the SC-E7000 bridge
translation or obtain a real destination-write capture for this firmware path
before another bike mutation attempt. The deployed verification-only page is
appropriate until that evidence exists.

- The real D4.5.0 bike returned `EA` to the regulation unlock in build .65.
- Builds .65-.66 used the wrong secure-word byte order or the desktop
  application slot. Build .67 corrected the words and added mode 1 but still
  used slot `00`; it received neither completion. Build .68 used wireless slot
  `0D` and received exact mode-1 and mode-5 completions.
- Builds .68 and .70 sent lighting-style `A0` commands in mode 5 and returned
  `A3 3A`. Build .69 sent an invalid nine-byte frame and also returned `A3 3A`.
  None sent `A8`.
- Build .71 sent the first zero-selector prefix after exact mode-1 and mode-5
  completions; it received `A3 3A`, exited mode 5, and never sent `A8`. The
  first rejection prevented its longer prefix probes, so they yielded no new
  evidence.
- Build .72 verified the firmware's distinct mode 4 and exact slot-`0D`
  completion, then rejected the invalid nine-byte `A0` frame with `A3 3A`.
- Build .73 paired verified mode 4 with Shimano's exact seven-byte same-value
  lighting stage. The bike returned `A3 3A`, accepted mode exit, and
  disconnected. It never sent `A8`. The user reported a display reset during
  the process; its timing and whether bike power changed are unknown. Build
  .74 exposes only a guided firmware/region readback while the A0 gate is
  investigated offline.
- Persistence after a physical power cycle remains unverified.
- A US destination readback does not by itself measure the assistance cutoff.

These validation gaps do not by themselves justify installing different
firmware. The unchanged A0 stage remains rejected on the live D4.5.0 bike.
