# E5000 D4.3.0 and current Android destination-path analysis

This note records the 2026-09-24 re-check that led from build 78 through build 82. It does not
claim that the bike accepted a destination change. Vendor binaries and complete
decompilations remain outside the public repository.

## Exact firmware comparison

The historical eTuning preparation archive is the published
[`5000_430.zip`](https://etuning-app.com/wp-content/uploads/2024/11/5000_430.zip)
(146,098 bytes, SHA-256
`4dee4d75ee83c22e951114cbf57332709c15be637ec2a8171bd82f9345adb137`).
It contains the exact E5000 preparation pair:

| Image | Bytes | SHA-256 | Internal version |
| --- | ---: | --- | --- |
| `DUE5000-D.5.3.0.dat` unwrapped | 132,072 | `3d3df4dfe3de333062f445b6719fa5033f93dc9d384448134ee6041d216c6af0` | D4.3.0 |
| `DUE5000-M.5.2.1.dat` | 116,320 | `10190fd78e6527908c0e43405184c414b612bc4becce9ca5483612665ced6b56` | M4.2.1 |

The D4.3.0 image is little-endian ARM Thumb at base `0x10000`. Its header gives
entry pointer `0x2e215` (Thumb function `0x2e214`) and image size `0x203e8`.
For comparison, the examined D4.5.0 image enters at `0x2f985` (function
`0x2f984`).

The relevant D4.3.0 handlers are structurally the same as D4.5.0, shifted by
`0x1734`:

| Operation | D4.3.0 | D4.5.0 |
| --- | ---: | ---: |
| `A0` record/staging handler | `0x23b74` | `0x252a8` |
| `A8` destination handler | `0x23c48` | `0x2537c` |
| PC-mode request handler | `0x25ae8` | `0x2721c` |
| Secure-word handler | `0x25cfc` | `0x27430` |

D4.3.0 does **not** remove the mode or one-shot gates: `A0` still requires PC
mode 4/5 and a zero target, then sets the byte at `0x2000295f`; `A8` still
requires PC mode 4/5 and that byte equal to one, clears it, and invokes the
persistent-record helper. The PC-mode and secure-word handlers stage and then
promote mode 4/5 as on D4.5.0. Therefore the historical preparation pair is
useful because it is field-supported for Bluetooth destination changes, not
because it has an ungated destination opcode.

The startup path closes a further ambiguity. Entry `0x2e214` calls the complete
runtime initializer table at `0x2ffcc`. Its first variable-length record invokes
the zeroing routine at `0x2ff90` for `0x2530` bytes starting at `0x20000490`.
The cleared range ends at `0x200029c0` and therefore includes `0x2000295f`.
The table's only other record invokes the decompressor at `0x294aa`, consumes
`0x3f5` bytes of packed data, and writes `0x56c` bytes from `0x2000000c` through
`0x20000577`. It stops `0x23e7` bytes before the gate. The dispatcher reaches
the table end after that record; there is no third initializer.

The writer search was also expanded beyond exact gate literals. The only direct
literal for `0x2000295f` is shared by A0 and A8. Every located reference to
nearby bases from `0x20002940` through `0x2000295e` performs an exact byte load
or store, not indexed access into the gate. Every call site of the identified
generic byte-fill (`0x29230`) and byte-copy (`0x29246`) helpers was checked;
none spans `0x2000295f`. This is bounded static negative evidence rather than a
proof against arbitrary computed pointers, but it rules out the direct,
nearby-base, startup-table, and standard bulk-helper write paths present in the
image. A cold boot does not pre-arm A8, and A0 remains the only identified
setter.

D4.5 has the same complete two-record startup behavior. Its table at `0x3173c`
first invokes zeroing routine `0x31700` for `0x25d0` bytes from `0x20000490`,
ending at `0x20002a60` and covering its corresponding gate at `0x200029fd`.
Its second record invokes the same decompressor logic at `0x2c33a` and again
writes exactly `0x56c` bytes through `0x20000577`, far below that gate.

### D4.1.0 historical cross-check

The exact E-TUBE Professional 3.4.5 installer provides a contemporaneous
DUE5000 D4.1.0 raw image (135,052 bytes, SHA-256
`fdb0f40b94d55ce9d098f803fe0f2f4038a3ce3343fe539bf151a9511dda14ec`).
That matters because the same desktop release exposes direct
`DUUnitDataLink.SetDestination` buttons: if D4.1 had accepted direct A8 without
the volatile gate, the desktop/client-versus-firmware discrepancy could have
been explained as a later firmware change. It does not.

The D4.1 opcode tables point A0 to `0x240e0` and A8 to `0x241b0`. A0 requires
active PC mode 4 or 5 and a zero selector, copies five bytes to
`0x200028d0`, sets the one-shot byte at `0x20002d72`, and replies A2. A8
requires the same mode and that byte equal to one, copies six bytes into the
adjacent tail at `0x200028d5`, clears the byte, calls the record helper at
`0x24356`, and replies AA or 3A. The gate address appears as an exact literal
only once, in the literal pool shared by these handlers.

Cold-start behavior is also parallel. Header entry `0x2ebb9` reaches runtime
initialization at `0x30b20`. The first initializer record at `0x30bc8` resolves
to zero routine `0x30b8c` and clears `0x2520` bytes from `0x200008b0` through
`0x20002dcf`, including the gate. Thus exact D4.1, D4.3, and D4.5 all require
an A0-created one-shot gate and all clear it on startup. The D4.1 comparison
rules out “downgrade to an ungated destination opcode” as the explanation for
the published D4.3 Bluetooth boundary. Compatibility must instead depend on
how an earlier client/display establishes and retains prerequisite state, or
on another version-dependent path not present in the visible destination
button call.

### Protected PC mode does not arm the destination gate

A handler-level comparison closes a separate loophole: successful mode 4 or 5
authentication does not itself set the A8 gate. The relevant RAM layouts are:

| Image | Slot | Active mode | Requested mode | Secure-word count | Destination gate |
| --- | ---: | ---: | ---: | ---: | ---: |
| D4.1.0 | `0x20002d6d` | `0x20002d6e` | `0x20002d6f` | `0x20002d70` | `0x20002d72` |
| D4.3.0 | `0x2000295a` | `0x2000295b` | `0x2000295c` | `0x2000295d` | `0x2000295f` |
| D4.5.0 | `0x200029f8` | `0x200029f9` | `0x200029fa` | `0x200029fb` | `0x200029fd` |

For modes 4 and 5, each request handler records the requested mode and
application slot and resets the secure-word count. Each secure-word handler
checks the same corresponding ten-byte table; after the fifth matching word it
copies requested mode to active mode and resets the count. Those verified
direct state writes do not touch the destination gate two bytes beyond the
counter. The mode-1/4/5 tables are byte-identical across D4.1, D4.3, and D4.5
and match the corresponding SC-E7000 tables, so mode 5 is not a distinct
implicit destination unlock.

This is bounded static evidence, not proof against arbitrary computed-pointer
writes elsewhere. Combined with the unique exact gate literal and expanded
writer audit, however, it rules out protected-mode completion itself as the
missing A0 substitute. An explicit accepted A0 remains necessary before A8 on
all three examined motor versions.

The managed caller audit sharpens the unresolved part. In the complete 3.4.5
desktop executable, `SetDestination` is called only by the factory and OEM
destination buttons; `SetLightingTime` is called by a separate lighting button
and by the drive-unit setup worker. There is no hidden A0 call immediately in
either destination button. Those call sites therefore prove selector and
destination arguments, but not a self-contained wire transaction. Build 82's
display-owned mode 5 plus explicit unchanged A0 remains the only current
candidate that satisfies the motor firmware's verified gate without inventing
a payload.

The surrounding lifecycle does not silently close the gap. The inspection
panel's `DoLoad` and `ResetDisplay` paths enumerate units and populate controls;
they do not invoke a DU setter. The ordinary drive-unit apply worker calls
`SetTireCircumference` at IL offset `0x0182`, while its only
`SetLightingTime` call is much later at `0x0481` and conditional on that value
having changed. This ordering also means the public patch that inserts
`SetDestination` inside `SetTireCircumference` invokes A8 before that later A0,
not after it. A successful wired report is useful outcome evidence, but its
published method does not explain the motor gate by call ordering alone.

`tools/inspect_motor_destination.py` reproduces the exact-image fingerprints,
destination and PC-mode dispatch pointers, request/promotion signatures,
secure tables, RAM-state separation, pending-record adjacency, one-shot gate,
record-helper edge, and startup zero coverage for all three versions. Its
static result does not prove live timing, persistence, or speed behavior.

### SC-E7000 4.0.6 bridge cross-check

E-TUBE Professional 3.4.5 also bundles the exact SC-E7000 4.0.6 display image
(123,100 bytes, SHA-256
`ff934060d5a00e60817a153a557bde384ab2020ccbcd06c30a463549e62a3603`).
Comparing it with the bike's SC-E7000 4.1.0 closes another tempting historical
explanation: the older display does not contain a special destination-mode
bridge absent from the current image.

In 4.0.6, local handler `0x22d74` accepts modes 0, 1, 4, and 5 and uses secure
tables at `0x21474`, `0x21480`, and `0x2148c`. Their ten-byte hashes are
identical to the corresponding 4.1.0 tables. Successful completion handler
`0x213a4` stores the requested mode, completion flag, and application slot
before announcing completion, with no immediate mode-0 or cleanup call. Its
post-request helper `0x1ee1c` clears the periodic topology-maintenance trigger,
and tick `0x1ed68` reaches the exit machine only while that trigger is one.
Whole-image direct-call counts remain structurally parallel to 4.1.0.

The only relevant difference found in this bounded path goes in the opposite
direction from a historical shortcut: 4.1.0's post-request helper additionally
clears phase byte `+0x03`; 4.0.6 clears trigger `+0x06` and phase bytes `+0x04`
and `+0x05` but leaves `+0x03` unchanged. Both disarm the periodic trigger,
while current 4.1.0 resets one more maintenance field. Thus display downgrade
does not explain or remove the motor's separate A0 gate, and it offers no
evidence-backed advantage over build 80's use of current display firmware.

`tools/compare_display_pc_mode.py` verifies both fingerprints, the identical
secure-table hashes, completion state writes, bounded call graphs, maintenance
trigger rule, and whole-image direct references. It does not rule out all
asynchronous events or prove a live write.

## Two independent current Android clients send direct A8

The exact eTuning 3.0.7 APK fingerprint already recorded in
[`source-artifact-hashes.json`](source-artifact-hashes.json) was decompiled with
JADX 1.5.6. Its old-generation destination path constructs
`00 16 A8 01 <destination>` directly in `p000/C1459qj.java` and writes it from
`ActivityC1041w.java`. `C1463qn.m6499J` is the GATT write helper. The app's
`A0` constructor (`C1463qn.m6513X`) belongs to its separate lighting-time path;
it is not called by the destination task.

A second pass through the complete call chain rules out an implicit stage in
that helper: `m6499J` only assigns the caller's byte array to `2AFE` and invokes
Android's `BluetoothGatt.writeCharacteristic`, with bounded retries only when
the local API refuses to queue the write. The quick-action dispatcher also
processes its optional region task before its optional wheel, assist, and other
setting tasks. Its optional lighting-time action is separate. Thus neither the
destination call nor its immediate transport helper hides an `A0` write.

The independently published eMaxMobileApp 1.89 Android client was also
inspected (APKPure-served APK, 1,046,473 bytes, SHA-256
`1a55a436bbf15706bc8ee6476a0a181283342de2170303ed01504b01ffeb6968`).
The APKPure landing page advertised a different package hash, so this artifact
is corroborating implementation evidence rather than a vendor-authenticated
release. `DestinationSettingsActivity.java` constructs these direct writes:

| Selection | Packet |
| --- | --- |
| EU | `00 16 A8 01 00` |
| US | `00 16 A8 01 01` |
| Japan/Taiwan/Korea | the corresponding value in the final byte |

It writes the packet to `2AFE` and treats `AA` as success. It contains no `A0`
in this destination action; the APK's `A0` packet constructors occur in its
lighting activity. This is independent corroboration of the direct-A8 packet
shape, not of a self-contained transaction. It does not reveal how those apps
arm the volatile motor flag; connection initialization, version-specific
system behavior, or another indirect write must account for successful field
use.

Both vendors' published compatibility information draws the same boundary:
E5000 D4.2.1-D4.3.0 can change destination over Bluetooth, while D4.4.2-D4.5.0
cannot. See the [eMax compatibility table](https://www.emax-tuning.com/eMax-possibilities.pdf),
[eTuning comparison](https://etuning-app.com/compare/etuning-vs-emax-vs-stunlocker/),
and [STUnlocker compatibility page](https://www.stunlocker.com/).

## Historical client and display-local command audit

Historical eTuning 1.0.32 uses the same direct destination action as the
current client: it sends `00 16 A8 01 <destination>`, without A0 in that button
path. A second JADX pass in raw/fallback mode confirms that the complete
`RegionActivity.writeClick` bytecode constructs exactly that five-byte array
and performs one `2AFE` write. The activity's only `onCreate` helper is a
firmware-version warning; it does not write to BLE. Its setup uses display
command `00 0C 01`; a complete source-tree literal audit found no `0C 04` or
`0C 05` call site in that APK. eMaxMobileApp 1.89 is parallel: its inventory
flow contains `00 0C 01`, while its destination activity writes direct A8 and
has no local mode-4/5 command. These results bound the historical-client
negative evidence more tightly than inspecting the destination button alone.
The historical eTuning connection flow also contains `00 32 B4 00`,
but this is not a hidden mode or gate setter. The matching D4.3 handler at
`0x215b4` calls getter
`0x2453a`, which only reads the dword at `0x2000276c` and returns a B6 response;
D4.5 is parallel at `0x22c40`/`0x25c6e`, reading `0x200027e8`. The display-local
`00 0D 00` command is likewise a read-only status query (`0x23746`).

A 2026-09-24 comparison of eTuning 2.0.7 and 2.0.8 also rules out the latter's
advertised E5000 assistance-save fix as a hidden destination mechanism. Both
versions use the same ordinary `00 16 98 <mode> ...` assistance writes and
contain local `0C 01`, but neither contains local `0C 04`/`0C 05`.

STUnlocker Android 1.21.157 supplies a separate negative control. After decoding
the package's obfuscated literals, its market worker selects slot 0, performs
model-dependent authentication, writes direct `00 16 A8 01 <destination>`, and
reads `00 16 AC 01`. Its lighting worker separately constructs `00 16 A0`.
Across the complete decoded literal inventory there is one `000C01` and no
`000C04` or `000C05`. An authentic 1.20.153 package, independently matched by
published SHA-1 and the same signing certificate, has the same market call
chain and local-mode inventory. These packages therefore corroborate the
packet meanings without revealing another privilege grant on D4.5.0. The
unavailable pre-1.20 packages remain a bounded evidence gap.

The missing state transition was instead in the SC-E7000 display image. Its
local `0C` handler at `0x236fc` explicitly accepts modes 0, 1, 4 and 5. For
modes 1/4/5 it calls `0x17cc8`, then `0x212ac(mode)`, and replies `2C 00`.
`0x212ac` constructs the motor PC-mode request and queues five secure words
from built-in tables (`0x21dfc`, `0x21e08`, `0x21e14`). Mode 0 runs the same
builder with zero and then cleanup. The supplied official capture confirms the
path for mode 1: `00 0C 01` was followed by `2C 00` and the motor completion
`00 32 12 01 0D ...`.

Builds 76/77 sent category-32 mode requests directly to the motor while the
SC-E7000 retained ownership of its display-created session. Their 59-74 ms mode
loss therefore demonstrates an ownership collision, not a limitation of the
display's own mode path. Sending local `00 0C 04` makes the SC-E7000 establish
mode 4 itself and avoids the already observed phone-versus-display race.

The completion path was then traced through handler `0x21d2c`. After all five
mode-4 table words match, it stores mode 4 in the display's own active-mode
field (`0x200001f8 + 0x0e`), stores the application slot at offset `+0x12`,
sets its completed-session flag at `+0x1e`, and only then constructs the
category-32 opcode-`12` completion. It does not call the local `0C` handler with
mode 0, the PC-mode builder, or cleanup helpers `0x17cfa`/`0x1f76c`. The mode-0
calls at `0x1f810` and `0x1f85a` belong to connection/topology maintenance
reached through `0x1f7b8`/`0x1f836`, not the secure-word completion path. This
proves that the display does not deliberately discard its own mode 4 while
reporting success. Moreover, helper `0x1f7a4`, called after a local nonzero-mode
request, clears the topology-maintenance trigger at state byte `+0x06`. The
periodic tick at `0x1f6f0` invokes the exit machine only while that byte is one.
Thus an already-running timer cannot silently reclaim display-owned mode 4; a
fresh topology/lifecycle event must first re-arm the state machine.

A whole-image direct-call scan finds only four references to the re-arm handler
(`0x17820`, `0x178a6`, `0x17b6c`, and `0x18352`), only two references to the
exit machine (`0x1f704` and `0x1f7f0`), and only three references to the local
mode handler (`0x16210`, `0x1f810`, and `0x1f85a`). None is in the completion
or raw-forwarding path. This removes a hidden direct caller as an explanation,
but does not exclude a real asynchronous connection event through a known
caller.

This cannot prove that such an event will not occur before the next BLE write,
or that the motor will accept the following bridged A0, so A0 remains the exact
live gate in build 79.

The raw drive-command path does not itself introduce that event. Enqueue
`0x2bf74` reaches selector `0x2dbb2`, whose staging-type-`0x10` branch invokes
the full-copy formatter at `0x2d7c4`. Across those bounded call graphs there is
no direct call to `0x1f7b8`, `0x1f836`, `0x236fc`, the mode builder, or either
cleanup helper. Thus processing `A0` cannot synchronously cancel mode 4 before
the command is queued; only an independent asynchronous state transition is
left as a display-side race.

Within the category-32 state cluster, direct-store inspection found only the
explicit mode-0 clear at `0x21cc6` and the successful secure-completion store at
`0x21d78`. `tools/inspect_display_pc_mode.py` reproduces the fingerprint,
secure tables, bounded call graphs, topology-maintenance gate, and state-write
ordering without printing or committing the vendor image.

## Exact A0/A8 pending-record boundary

A further D4.5.0 pass resolves what the two category-16 setters do before the
record helper. Handler `0x252a8` (`00 16 A0 ...`) first requires active PC mode
4 or 5 and selector zero. It copies the five bytes following that selector to
RAM at `0x20002548`, sets the one-shot byte at `0x200029fd`, and constructs the
`A2` response. It does not call the persistent-record helper on that success
path.

Handler `0x2537c` (`00 16 A8 ...`) independently requires mode 4/5 and the
one-shot byte equal to one. It copies six bytes into the immediately adjacent
RAM at `0x2000254d`, clears the one-shot byte, then calls `0x25516`.
`0x25516` compares the resulting 11-byte pending buffer at `0x20002548` with
the current 11-byte record at `0x2000253c`; its changed-record path copies the
pending buffer into the record buffer before the downstream record operation.
Thus A0 and A8 are two halves of one assembled settings record, rather than two
independent persistent writes. Reading and replaying the current A0/lighting
half before placing destination US in the A8 half is the firmware-backed way to
avoid changing unrelated bytes.

The search for a mode-4-specific read-only probe did not produce one. The only
other directly located handler that tests specifically for mode 4 or 5 is
category-32 opcode A0 at `0x24d50`, a different command from `00 16 A0`. Its
success path dispatches the supplied byte through `0x1c434`/`0x246ec` and a
separate record/update path before producing category-32 `A2`; it is not a
status read. The category-32 B4 command and display-local 0D command remain
read-only but do not distinguish mode 4/5 from the reclaimed normal mode.
Consequently the unchanged category-16 A0 used by builds 79-81 is the
narrowest available live gate before A8; adding an unknown category-32 write as
a probe would increase risk without adding a necessary guarantee.

## Superseded build 79 display-owned transaction

On the exact verified D4.5.0/M4.4.8 EU baseline, build 79:

1. reads the current lighting value and saves the salted restart expectation;
2. sends display-local `00 0C 04` on `2AFA`;
3. requires display reply `2C 00` and exact motor completion
   `00 32 12 04 <wireless-slot>` before proceeding;
4. sends one unchanged `00 16 A0 <low> <high> FF FF` and requires `A2`;
5. sends one `00 16 A8 01 01`, requires `AA`, and freshly reads destination 1;
6. exits through display-local `00 0C 00`, again requiring its acknowledgement
   and the exact motor mode-0 completion.

It never sends a phone-originated category-32 mode request, never retries A0 or
A8, and never sends A8 after an A0 rejection. Synthetic tests verify those
properties, not bike acceptance. It records the exact interval from the
mode-4 completion notification to A0 enqueue and to A2 acceptance, so a single
run preserves the remaining timing evidence without authorizing a retry. A
successful immediate read still requires a physical power cycle, a new-session
readback, and a safe cutoff-speed test.

Build 79 was not published or bike-tested. Its ownership change remains valid,
but its mode choice is superseded by build 80. The exact E-TUBE 3.4.5 desktop
inspection panel contains both destination buttons and places their
`DUUnitDataLink.SetDestination` calls inside protected mode 5. Since the motor
gates accept 4 or 5 and the SC-E7000 local handler owns both through the same
control path, local mode 5 is the closer known Shimano destination context.

Build 80 changed only steps 2 and 3 above to `00 0C 05` and exact
completion `00 32 12 05 <wireless-slot>`. All remaining packet, identity,
at-most-once, no-retry, readback, persistence, and exit constraints are
unchanged. It was never published or bike-tested.

Build 81 adds a second exact display-owned mode-5 handshake after A0 returns A2
and before the single A8. This is safe because the motor's mode-request and
fifth-word-promotion handlers do not clear the separate A0 gate or pending
record, while the SC-E7000 local handler forwards the same accepted mode again
instead of short-circuiting it. A second-handshake failure withholds A8 and
requires a physical power cycle because the A0 gate may remain armed. Build 81
was never published or bike-tested. Build 82 retains that packet ordering and
adds a durable, phase-aware same-device attempt journal. It blocks another
command write across reloads and after either US or non-US reconnect readback,
while leaving the read-only bike check available. Build 82 has synthetic
coverage but no bike result.

## Superseded build 78 timing hypothesis

Builds 76/77 waited for the exact mode-4 completion notification before sending
their first drive-setting command. The live motor rejected that first command
59-74 ms later because the SC-E7000 had already reclaimed the motor's global
mode. Those results rule out commands sent *after* the completion round trip.
They did not test this ordering:

1. subscribe to both PC-mode and destination replies;
2. send the fifth secure word;
3. when its local ATT write completes, immediately queue the unchanged current
   lighting value as `00 16 A0 <low> <high> FF FF` and then queue the one
   `00 16 A8 01 01`, without awaiting either A0's motor reply or the mode
   completion;
4. require the exact mode-4/slot completion, A0 `A2`, and A8 `AA`; and
5. require a fresh destination-1 readback, then a separate post-power-cycle
   readback.

The secure handler promotes the active mode before emitting completion, so this
ordering can reach the motor earlier than builds 76/77 while satisfying the
statically proven gate. It is still only a hypothesis: either ATT response may
arrive too late or the display may reclaim the mode first. Build 78 sends A0
and A8 at most once and never retries. `A3 3A`, `AB 3A`, EU readback, or a
missing exact completion is a negative result, not permission to repeat.

Build 78 remains useful historical reasoning but is no longer the preferred
live experiment. The display-owned protected-mode route is causally stronger
because it removes the ownership collision instead of trying to outrun it. If
build 82 is rejected despite both exact display acknowledgements and motor
completions,
the evidence-backed no-new-hardware fallback is the existing paired BLE
firmware workflow: prepare to D4.3.0/M4.2.1, verify that exact pair, then use
the same explicit display-owned mode-5/A0/mode-5/A8 transaction rather than
depending on the commercial clients' unexplained retained state. Build 91
requires A2, AA, immediate and power-cycle US readback before restoring
D4.5.0/M4.4.8. No image has yet
been sent to this bike, and an interrupted wireless firmware operation can
still require a wired recovery tool.

The later exact PCE02 3.0.4 decode also rules out an adapter-side A8 rewrite or
hidden A0 in that adapter's generic `0x48` path. The public wired report remains
outcome evidence with an omitted prerequisite, not a complete causal sequence;
see [`pce-transport-analysis.md`](pce-transport-analysis.md).
