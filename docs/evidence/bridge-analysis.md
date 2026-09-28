# SC-E7000 bridge analysis and SC-E6100 historical control

**2026-09-27 update:** Build 94 physically completed display-owned mode 5 but
its first A0 returned `A3 3A`; no A8 was sent and EU remained on reconnect.
The earlier proposed post-completion sequence below is therefore not a next
live action. A new, untested queue-ordering hypothesis is recorded at the end.

Analyst-generated summary of the SC-E7000 4.1.0 display firmware
(`SCE7000.4.1.0.dat`, 126,508 bytes, catalog MD5
`4974d4f471b126be9f9657510e6bef55`, plaintext ARM Cortex-M, load base
`0x10000`). The embedded entry pointer `0x2c6f1` maps to file offset
`0x1c6f1`, and the secure-table pointers independently confirm the base.
Addresses below are analyzer labels. The binary itself is not committed
(see [`ASSETS.md`](../../ASSETS.md)); this note records only the reasoning needed
to resume. It supersedes the "missing bridge-mapping evidence" gap noted in
earlier handoffs. An earlier draft used base `0x8000`; those display function
labels were `0x8000` too low and are corrected here. The decoded bytes and
control-flow conclusions did not change.

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
them; they reach the motor through a raw forward path (`0x2dbb2` selects the
full-copy formatter `0x2d7c4` when the staging buffer type byte is `0x10`),
which copies the command content byte-for-byte into the wire slot
(`0x20001bf0`) and prepends exactly two bus-node bytes (dest node from MAC
`0x4000c200`, source = display node id `0x20002ed3`, injected at `0x2c3b4`).

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

The display's own cat-0x32 handlers (table `0x21844`, dispatch `0x2164a`;
builders `0x212ac`/`0x1f8ce`/`0x21ae4` with literals `0x1032`/`0x3032`/`0x1232`)
belong to its connection/handshake state machine for the display's own DU link
(`0x200001f8`), invoked from the periodic bus loop `0x1fc0e` on connection-state
changes. They are "display talks to the motor" handlers, not a phone-inbound
dispatcher, and there is no code that synthesizes a motor secure-word reply or a
slot-routed opcode-0x12 completion locally. The DU→phone path
(`0x1b1c6`/`0x1b1e0` → BLE notify `0x18bf4`) tunnels the motor's raw reply words
straight back. So the phone's mode requests reach the motor's secure-word
handler, which sets the active-mode byte and routes the opcode-0x12 completion to
the requesting app-slot — matching the live result that app-slot `00` produced
no completion while slot `0D` did.

### 3. The display exposes its own PC-mode command to BLE

The BLE/display-local handler at `0x236fc` accepts exactly modes `0`, `1`, `4`,
and `5`. Modes 1/4/5 call setup helper `0x17cc8`, then `0x212ac(mode)`, and reply
`2C 00`; other nonzero values reply `2C 01`. Mode 0 calls `0x212ac(0)`, performs
cleanup through `0x17cfa`, and also replies `2C 00`. The command presented to
that handler is `00 0C <mode>` on the display characteristic, and the reply is
observed on the display-notification characteristic.

`0x212ac` is not merely a state toggle. It constructs the display-to-motor
category-32 request and, for modes 1, 4, and 5, queues the corresponding five
secure words from tables at `0x21dfc`, `0x21e08`, and `0x21e14`. The official
capture already exercised this path for mode 1: `00 0C 01` received display
acknowledgement `2C 00`, followed by motor completion
`00 32 12 01 0D ...` about 61 ms later.

This changes the ownership model. Builds 76/77 requested motor mode directly
from the phone while the display remained the owner of its existing mode-1
session, so the display promptly reclaimed the global motor mode. A local
`00 0C 04` or `00 0C 05` asks the SC-E7000 itself to originate the protected
transaction. That avoids the known phone-versus-display ownership collision.
The secure-word completion handler at `0x21d2c` stores the requested mode in
the display's active-mode field
before it constructs opcode `12`, and it contains no mode-0 or cleanup call.
The separately located mode-0 calls are connection/topology maintenance paths,
not normal mode completion. The post-request helper also clears the trigger
that lets the periodic tick enter that maintenance machine; a new
topology/lifecycle event must re-arm it before a delayed mode-0 path can run.
Static analysis therefore rules out both an immediate completion-path exit and
a timer-only exit while the trigger remains clear. Whether the motor accepts
the following bridged A0 remains the live gate.

The whole-image direct-call scan finds exactly four references to re-arm
handler `0x1f7b8` (`0x17820`, `0x178a6`, `0x17b6c`, and `0x18352`), two to the
exit machine (`0x1f704` and `0x1f7f0`), and three to the local mode handler
(`0x16210`, `0x1f810`, and `0x1f85a`). This rules out another hidden direct
caller in the exact image, although it cannot rule out a genuine asynchronous
connection event taking one of the four known paths.

The subsequent drive-command enqueue path was checked separately. Generic
enqueue `0x2bf74` selects formatter `0x2dbb2`; for staging type `0x10`, that
selector calls the byte-for-byte formatter `0x2d7c4`. The bounded call graphs
contain no direct call to topology re-arm `0x1f7b8`, maintenance exit
`0x1f836`, local mode handler `0x236fc`, mode builder `0x212ac`, or cleanup
`0x17cfa`/`0x1f76c`. Receiving `A0` therefore does not synchronously exit mode
4 or 5 before enqueueing the motor command. This does not exclude an independent
asynchronous topology event after enqueue.

### 4. Later live timing disproved the display-reset explanation

The app image contains no obvious periodic cat-0x32 mode traffic and the reset
observed in build .73 could have cleared the motor's active mode. Build .76,
however, received a real mode-4 completion and then an `A3 3A` reply to `A0`
about 74 ms later while the BLE link remained up and the display did not reset.
Build .77 repeated the cycle four times and received `A3 3A` at 59, 67, 63,
and 59 ms, again without a link loss. The reset theory is therefore falsified
for these failures. The observed behavior is consistent with the SC-E7000
reclaiming the motor's single global PC-mode state during its own bus traffic,
within roughly one poll cycle.

### 5. SC-E6100 4.0.5 does not expose a different protected-mode secret

Contemporaneous reports of successful DU-E5000 market changes used an
SC-E6100, so its exact public 4.0.5 image was checked as a possible display-
specific explanation. It is not a loose name match: the 164,488-byte image has
SHA-256 `9a3d9575af48eac883a2369af08bd00d819547c49c78d313d7aadc18269eeb77`
and catalog MD5 `90ea6133e21bf5d59b40f999e5ea9a11`.

The SC-E6100 local handler at `0x2b88c` accepts the same modes 0, 1, 4, and 5.
Its mode builder is `0x29460`; successful secure completion at `0x29ee0`
stores the requested mode, completion flag, and application slot before
constructing opcode `12`, with no immediate mode-0 or cleanup call. Most
decisively, the five-word tables at `0x29fb0`, `0x29fbc`, and `0x29fc8` have
the same SHA-256 values as the SC-E7000 mode-1/4/5 tables:

| Mode | Secure-table SHA-256 |
| --- | --- |
| 1 | `b34a08754c4e367c574499c73ce89919f3c1ed20165c5063cd139ac562a99c4e` |
| 4 | `be1f5a4366bfd7b3c7f77dd585554e1201f38e86e56a1789522ff6af4cd47fa1` |
| 5 | `52cf8e1fbc56803e6ede87262de5df10e0165e948d7ebf992c29ace6541ee2b6` |

Its maintenance topology is also homologous. Post-request helper `0x27950`
clears the periodic trigger and phase bytes +4/+5; periodic tick `0x2789c`
can enter exit machine `0x279e0` only while trigger byte +6 is one. The only
direct local-mode references are `0x1da58`, `0x279ba`, and `0x27a04`; the
latter two are the same event-driven mode-0 sites seen in SC-E7000. As in
SC-E7000 4.0.6, the post helper does not clear phase byte +3; current SC-E7000
4.1.0 is the image that adds that extra clear.

This rules out a different secure-word table or an obvious permissive local-
mode lifecycle as the reason old DU-E5000/SC-E6100 reports succeeded. It does
not reproduce runtime bus timing and cannot exclude state created by the old
client or a preceding firmware/update workflow. It therefore strengthens the
search for a historical client/state transition; it does not justify swapping
or reflashing the display.

## Bottom line

Cat-0x32 reaches the motor, `A0`/`A8` are forwarded, and their framing is valid.
Builds .76/.77 nevertheless prove that a phone-requested mode is lost before a
first setting command sent after completion can arrive. The display-local 0C
handler supplies a stronger, previously unused BLE path: make the SC-E7000 own
the protected mode rather than racing its existing ownership. Unpublished
build .82 selects local mode 5 because Shimano's desktop destination buttons
run in that inspection mode. It sends `00 0C 05`, requires both `2C 00` and the
exact motor mode-5/slot completion, then sends one unchanged-lighting `A0`.
Only on `A2` does it require a second complete local mode-5 handshake before
one destination `A8`. The SC-E7000 forwards a repeated accepted mode request,
while the motor's separate A0 gate survives the refresh. It requires `AA`,
fresh US readback, and a display-owned mode-0 exit. A durable salted-device
journal prevents another command attempt across page reloads. Until a bike run
succeeds and a separate power-cycle read confirms persistence, this is an
evidence-backed experiment, not a working procedure.

## 2026-09-27 correction: enqueue before motor completion

Build 94's A0 was placed only after the motor's mode-5 completion reached BLE.
The display firmware exposes an earlier, causally different point. Local `0C`
handler `0x236fc` calls mode builder `0x212ac` before sending its `2C 00` BLE
acknowledgement. For mode 5, the builder calls `0x210c6` six times: once for
the motor mode request, five times for its secure words. Each call reaches
generic bus enqueue `0x2bf74`. The phone's forwarded A0 path at `0x200bc`
reaches the **same** enqueue function. The ordinary type-`0x10` formatter
`0x2d7c4` copies each message into a ring buffer; `0x2d61e` removes entries
from its head. Thus, an A0 received immediately after `2C 00` can enter the
display queue behind the already-enqueued six handshake frames, instead of
waiting for the motor completion to travel back over BLE.
The phone-forward guard at `0x200bc` and the local mode builder both read the
same connection state at `0x200001f8`; the motor-completion handler does not
write the guard field at `+0x1f`. This makes an early write plausibly admissible,
but only a live read-only probe can verify that state during the handshake.

The exact image's startup record at `0x2ea64` decompresses 1764 bytes into
RAM beginning at `0x2000000c`. The 14-entry priority table at RAM offset
`+0x0c` contains neither mode request `32/10`, secure word `32/30`, nor
lighting A0 `16/A0`. On the ordinary bus path they therefore use the same
normal ring. `tools/inspect_display_pc_mode.py` now verifies the exact image,
call graph, startup-table digest, and those exclusions without exporting the
vendor image or its table bytes.

This is an offline queue-ordering inference, **not** proof of actual bus order,
mode lifetime, A0 acceptance, or destination persistence on this bike. Runtime
state can select a different queue, and an independent topology event can still
intervene. A lower-risk first discriminator is to enqueue the existing
read-only destination getter `00 16 AC 01` immediately after `2C 00`, record
whether its ATT write completes before motor mode-5 completion and its exact
`AE 01` reply follows that completion, then exit through local `0C 00`.
`AC` is also absent from the priority table and uses the
same phone-forwarding path as A0. This would test live queue admission and
relative reply order without another setting write, though it would not prove
that A0's protected-mode gate is open. Build 95 wires
that diagnostic behind the existing contextual button only after the exact
stock pair and verified non-US attempt record are freshly checked. It runs at
most once per connection, does not alter the attempt journal, and requires a
mode-0 exit or disconnect. Synthetic browser tests cover its packet ordering,
early-completion fail-closed branch, and late-ATT-acknowledgement ambiguity;
no bike result exists.

A future bounded setting implementation would have to stage only one
unchanged A0 after `2C 00`, require both exact motor mode-5 completion and A2,
then separately evaluate how to queue a single A8 after another complete
mode-5 handshake. It must retain the existing journal; build 94's rejected A0
must not be silently retried or the record erased. No such live code is wired.
