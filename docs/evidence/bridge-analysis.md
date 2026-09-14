# SC-E7000 4.1.0 display bridge analysis

Analyst-generated summary of the SC-E7000 4.1.0 display firmware
(`SCE7000.4.1.0.dat`, 126,508 bytes, catalog MD5
`4974d4f471b126be9f9657510e6bef55`, plaintext ARM Cortex-M, load base
`0x8000`). Addresses are analyzer labels. The binary itself is not committed
(see [`ASSETS.md`](../../ASSETS.md)); this note records only the reasoning needed
to resume. It supersedes the "missing bridge-mapping evidence" gap noted in
earlier handoffs.

## Question that mattered

Builds .68–.73 sent `00 16 A0 <lo> <hi> FF FF` after a confirmed PC mode-4
completion and received motor error `A3 3A`, never reaching the `A8` region
write. On D4.5.0 the `A0` handler accepts only when PC mode is 4/5 **and** the
normalized message byte at offset+4 (the motor target address) is `0`. We could
not tell over BLE which gate failed because the bytes the motor actually
received were unknown. The display is a bridge, so its framing is the missing
link.

## Findings

### 1. Drive-unit commands are forwarded verbatim; offset+4 is the leading byte

The display has **no** command-id literals for `A0`/`A8`/`AC` and no per-opcode
filter. It never originates these commands and does not intercept or rewrite
them; they reach the motor through a raw forward path (`0x25bb2` selects the
full-copy formatter `0x257c4` when the staging buffer type byte is `0x10`),
which copies the command content byte-for-byte into the wire slot
(`0x20001bf0`) and prepends exactly two bus-node bytes (dest node from MAC
`0x4000c200`, source = display node id `0x20002ed3`, injected by `fcn.0x243b4`).

Byte map (phone write `b0 b1 b2 b3 …` → motor normalized message):

| motor offset | value | source |
| --- | --- | --- |
| +0 | dest node | bus MAC |
| +1 | source node | display node id `0x20002ed3` |
| +2 | category | phone `b1` |
| +3 | opcode | phone `b2` |
| +4 | target address | phone `b0` (the leading byte) |
| +5.. | parameters | phone `b3, b4, …` |

This reconciles with the known-working region read `00 16 AC 01`: its leading
`00` lands at offset+4 (the `AC` handler requires this to be `0`) and the
selector `01` lands at offset+5. **Therefore every `A0` packet in builds
.68–.73 already had offset+4 == 0; the `A3 3A` was never a target-byte or
framing problem.** (An earlier model placing the first parameter at offset+4 is
falsified by `AC 01`, which would then be rejected but is accepted every
session.)

### 2. Phone cat-0x32 PC-mode commands are forwarded to the motor

The display's own cat-0x32 handlers (table `0x21844`, dispatch `0x1964a`;
builders `0x192ac`/`0x178ce`/`0x19ae4` with literals `0x1032`/`0x3032`/`0x1232`)
belong to its connection/handshake state machine for the display's own DU link
(`0x200001f8`), invoked from the periodic bus loop `0x17c0e` on connection-state
changes. They are "display talks to the motor" handlers, not a phone-inbound
dispatcher, and there is no code that synthesizes a motor secure-word reply or a
slot-routed opcode-0x12 completion locally. The DU→phone path
(`0x131c6`/`0x131e0` → BLE notify `0x10bf4`) tunnels the motor's raw reply words
straight back. So the phone's mode requests reach the motor's secure-word
handler, which sets the active-mode byte and routes the opcode-0x12 completion to
the requesting app-slot — matching the live result that app-slot `00` produced
no completion while slot `0D` did.

### 3. Mode loss is a display reset, not local interception or periodic traffic

A stable connected session sends no periodic cat-0x32 mode traffic to the motor
(steady state is cat-0x16 polling, which does not touch the motor's PC-mode
byte). The active-mode byte is cleared on a (re)connection event. The app image
has no software reset (no `AIRCR 0xE000ED0C` / `0x05FA` VECTKEY) and no runtime
re-init path (the init funcs are called only from entry `0xe000`), so the screen
reset observed in build .73 is a hardware watchdog / brown-out re-entering via
the bootloader. The WDT refresh and SysTick live in the bootloader, not this
app image; there are `bkpt` fault sinks (`0x26a14`, `0xe12e`, `0x148f0`) so any
unhandled fault hangs until the watchdog fires. A reset is abrupt and silent to
the motor, which then times out mode 4/5.

## Bottom line

Phone-only region-set is **architecturally viable**: cat-0x32 reaches the motor,
`A0`/`A8` are forwarded, and the framing was always valid. The rejection is the
motor's PC mode 4/5 being cleared before `A0` by a display reset. Mitigation
(build .76): keep the unchanged `A0` bytes, move the lighting read and record
save out of the privileged window, fire `A0`→`A8` as one fast burst inside a
single stable display up-window, and instrument the timing so a live failure
distinguishes a link drop (reset) from a silent in-session mode loss. Whether
PC-mode entry itself provokes the reset is unresolved from the app image (the
watchdog is in the bootloader) and is the decisive open question for the live
test.
