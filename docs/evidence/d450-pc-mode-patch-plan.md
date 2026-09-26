# D4.5.0 PC-mode-gate patch feasibility

This note records an unpublished, **unwired** software-only recovery branch.
No modified firmware has been sent to the bike, no vendor image is committed,
and the browser UI cannot invoke this branch. It is a causal design and static
construction result, not a qualified installation procedure.

## Why the ordinary downgrade is not yet a complete explanation

Exact D4.3.0 and D4.5.0 analysis found the same two requirements:

1. `A0` accepts only in active PC mode 4/5 with target byte zero, then creates a
   volatile one-shot destination gate; and
2. `A8` accepts only in active PC mode 4/5 while that gate is one, consumes it,
   and calls the persistent-record helper.

Cold startup clears the gate in both versions. All 27 located instructions that
load the D4.3 active-mode byte have corresponding D4.5 instructions at a fixed
`+0x1734` code relocation, and their local instruction windows are identical.
The request and fifth-secure-word handlers and mode 1/4/5 tables are also
equivalent. This does not disprove every transient created by a commercial
preparation workflow, but it means that “install D4.3, reboot, send direct A8”
does not itself satisfy the verified motor-side state machine.

## Minimal current-firmware patch

The exact unwrapped D4.5.0 image is 138,072 bytes with SHA-256
`44806bd54aedff95a88bb73fafe0f0581297f2f67b2ea35545cea012899d90bb`.
The proposed derived image changes five bytes:

| Purpose | Runtime address | File offset | Original | Replacement |
| --- | ---: | ---: | --- | --- |
| distinguish experimental readback | `0x10012` | `0x12` | `00` | `01` |
| bypass only A0's active-mode rejection | `0x252c8` | `0x152c8` | `2D D1` | `00 BF` |
| bypass only A8's active-mode rejection | `0x25394` | `0x15394` | `24 D1` | `00 BF` |

The first edit changes the native D header from 4.5.0.0 to 4.5.0.1. That gives
reconnect readback a positive marker for the experimental image and lets a later
4.5.0.0 readback distinguish the stock restoration. The other edits replace
the final Thumb `BNE error` after each mode-4/mode-5 comparison with a Thumb
NOP. They do **not** bypass:

- A0's requirement that the target byte is zero;
- A0's copying of the five-byte pending-record half;
- A0's creation of the one-shot gate;
- A8's check and consumption of that gate;
- A8's six-byte destination-half copy; or
- the original persistent-record helper and response construction.

The deterministic result has SHA-256
`0dbbb3d3b634d831d8450d2758d953502bfdc7f16ac8640a4e3ca46fff3fff18`
and finish checksum `0x49` (the source image is `0xBD`).
[`tools/patch_motor_pc_mode.py`](../../tools/patch_motor_pc_mode.py) validates
the exact source fingerprint and instruction bytes, fails closed on any other
input, and defaults to a dry run. The page contains the same exact-hash builder
without a UI caller; its synthetic regression uses no vendor bytes.

## Why modified-image acceptance is plausible, but not proved

The reconstructed D update path accepts an image buffer, checks its raw header
against the queried bootloader family/unit, writes 64-byte blocks with byte-sum
checksums and block indices, then sends command 39 with the original image's
whole-byte sum modulo 256. Equal-version rewriting is explicitly selectable in
the audited Android coordinator; the 4.5.0.1 marker instead makes this candidate
an ordinary upward version comparison. The official D container's AES-CBC and
embedded MD5 are removed and checked by the host before the raw image reaches
this transfer path; they are not fields sent as a separate bootloader signature.

No asymmetric-signature operation or second whole-image authenticator has been
found in the audited client path, and the raw image has no identified signature
trailer. That is bounded positive feasibility—not proof about every check in
the resident bootloader or application startup. A hidden bootloader integrity
check, a startup self-check, an interrupted transfer, or a Web Bluetooth loss
could leave the motor unavailable over BLE.

## Required staged experiment

Build 85 keeps build 82's current-firmware command sequence unchanged. It adds
an unwired patch coordinator around build 84's exact constructor and
non-installable in-memory pair loader. The coordinator accepts only the stock
D4.5.0/M4.4.8 restoration pair, derives D4.5.0.1, retains M4.4.8 unchanged,
rechecks peer requirements, persists a patch-specific recovery lineage, and can
replay the complete pair after a stopped transfer. The safe order remains:

1. Run the existing current-firmware display-owned mode-5/A0/mode-5/A8
   experiment once. If it succeeds, no firmware experiment is needed.
2. Before any flash, require the exact original D4.5.0/M4.4.8 restoration pair,
   exact live EU baseline, application identity, D-loader fingerprint, durable
   recovery journal, charged bike/phone, and explicit live authorization.
3. Transfer a complete compatible pair containing stock M4.4.8 and the derived
   D4.5.0.1 image; do not expose a D-only shortcut until its recovery semantics
   are separately proved.
4. Reset and require a different BLE session to read the same motor with native
   D4.5.0.1/M4.4.8. A version mismatch or an unavailable application stops the
   experiment; no setting command follows.
5. Send the unchanged A0 half once, require A2, send A8 once, require AA and a
   fresh US readback. Neither setting mutation is retried after an uncertain
   result.
6. Restore the exact stock D4.5.0/M4.4.8 pair, reset, and require same-motor
   native 4.5.0.0/4.4.8 plus US readback after another power cycle.
7. Measure the physical assistance cutoff separately. A US byte alone is not a
   measured speed result.

The coordinator, D4.5.0.1 reconnect gate, one-write/persistence lineage, and
stock-restoration authorization are now implemented and synthetically tested.
They have no UI caller and are not authorized for the bike, so the generated
pair remains **not installable**. The inability to guarantee BLE recovery after
an unbootable image is the main no-new-hardware risk and must remain visible
rather than being softened into a generic firmware warning.

## Application-startup integrity audit

The exact D4.1.0, D4.3.0, and D4.5.0 application images were also traced from
their header entry pointers. Each entry sets the stack and calls a runtime
initializer. That initializer executes two table records—RAM zeroing and one
12-byte ROM-to-RAM copy—then calls `main`. In all three images, the declared
image-size value occurs only at header offset `0x18`; neither the computed image
end nor a pointer to the size field occurs anywhere in the raw image. The tail
is structured executable/data material and has no identified appended opaque
signature block. A fresh Ghidra D4.5 import found version-header reads but zero
references to the entry, size, or family header fields.

[`tools/inspect_motor_image_integrity.py`](../../tools/inspect_motor_image_integrity.py)
checks the exact fingerprints, startup calls, initializer records, whole-image
literal searches, and structured tails without dumping vendor bytes. This
substantially reduces the risk of an application-level whole-image self-check.
It does not inspect the resident bootloader, exclude computed addresses or an
external checksum record, or establish modified-image acceptance and BLE
recovery.

## Resident-loader client audit

The exact E-TUBE 3.4.5 managed assembly exposes the complete loader request set
used by its Renesas update worker: start, firmware version, erase count, set
address, checksum, clear checksum, finish, reset, serial low/high, and loader
version. There is no flash-read command in the enum or helper set. The write
worker passes `get_BinaryData` through address, data, additive-checksum, finish,
and reset operations; no separate signature operation appears in that bounded
call chain. eTuning 2.0.7, 2.0.8, and 3.0.7 likewise construct no memory-read
request.

[`tools/inspect_etube_d_loader.py`](../../tools/inspect_etube_d_loader.py)
machine-checks the exact assembly and IL facts, and
[`d-loader-acceptance-analysis.md`](d-loader-acceptance-analysis.md) records the
evidence and limitations. This strengthens modified-image plausibility but also
means there is no reviewed BLE backup primitive before the experiment. It does
not inspect or prove the resident loader's internal acceptance policy.
