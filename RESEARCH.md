# Session authentication investigation

Updated 2026-09-09. Target: SC-E7000 + DU-E7000 firmware 4.7.1,
using Android Web Bluetooth. Build `2026-09-09.4` verified session access on
the real bike. Build `2026-09-09.5` received no matching drive-unit model reply in two live
tests. Build .6 verified display commands but recorded a silent motor-response
channel. Build .7 verified motor communication and reported E50X0 / 4.5.0.
Build `2026-09-09.8` adds destination reads and a US-region readiness summary.

## Confirmed from the supplied artifacts

Both eTuning XAPKs (1.0.32 and 3.0.7), ShimanoBleProbe.zip, and the Android
bugreport pass archive integrity checks. The bugreport includes
`FS/data/misc/bluetooth/logs/btsnoop_hci.log`: 115,513 bytes and 1,084 ATT packets.
There is one captured connection, one 2AF4 challenge read, and one successful
two-stage authentication exchange. The probe ZIP contains a read-only Android
project, not an authentication implementation.

Service discovery establishes these characteristic value handles **for this
capture only**:

| Characteristic | Handle | Role observed |
| --- | --- | --- |
| 2AF3 | 0x0015 | Authentication writes and result indications |
| 2AF4 | 0x0018 | 16-byte challenge |
| 2AF6 | 0x001c | Later reads, after additional client operations |
| 2AF7 | 0x001e | Display identification |
| 2AF8 | 0x0020 | Six-digit passkey, not region |
| 2AFF | 0x0031 | Additional post-authentication setup |

Captured ordering (frame numbers refer to the original snoop file):

1. Frame 621: read the 16-byte challenge from 2AF4.
2. Frames 623–624: enable 2AF3 indications through its CCCD.
3. Frame 626: write a 17-byte stage-1 message to 2AF3.
4. Frame 629: receive `10 01 01` (stage-1 success).
5. Frame 631: write a 17-byte stage-2 message to 2AF3.
6. Frame 635: receive `10 02 01` (stage-2 success).
7. Frame 637: additional `FF 00` write to 2AFF, followed by subscriptions to
   other characteristics.
8. Frames 654–655: read 2AF7 successfully; it identifies `SCE7000` plus a NUL.
9. Frames 656–658: read 2AF8; its value is the passkey used in stage 1.

The capture does **not** include a failed pre-authentication 2AF7 read in that
same connection. The blocked-read baseline is user-reported from earlier
WebBLE/nRF tests. It also does not prove that step 7 is unnecessary for 2AF7.
Build .3 checked 2AF7 immediately after both acknowledgements; the live result
and next experiment are recorded below.

## Reconstructed handshake

Both APK versions construct the same AES-128 challenge responses:

- Stage 1 key: fixed ten-byte prefix `00 01 11 47 A5 3F A2 79 52 48`, followed
  by the six **ASCII digits** of the user-configured passkey.
- Stage 2 key: protocol constant
  `00 02 D3 9C A4 26 C6 94 E3 0B C9 22 E8 7B B5 8D`.
- Encrypt the original 16-byte challenge with AES-ECB, without padding, for
  each stage. Do not reorder the challenge bytes.
- Write `01 || ciphertext1`, wait for `10 01 01`, then write
  `02 || ciphertext2` and wait for `10 02 01`.

The passkey participates in application authentication as well as the phone's
bonding workflow. Bonding alone does not send these application messages.
This remains separate from any motor-level configuration authorization.

Private decompilation pointers:

- 1.0.32: `d/a/a/a/c.java`, cases -18, -17 and -16: key construction and two
  message stages; `f` performs encryption; `d/a/a/a/g.java::h` sends the message.
- 3.0.7: `defpackage/Q5.java`, cases -18, -17 and -16, and `q1`:
  matching key/message construction and explicit AES/ECB/NoPadding.
- 3.0.7: `defpackage/AbstractC0544qi.java::j`: challenge byte storage and
  recognition of both success indications.

JADX reported errors elsewhere in both APK decompilations. The relevant
handshake paths are readable and independently checked against actual traffic;
this is not a claim that the entire decompiled program is correct.

## Validation and implementation limits

The actual browser `authResponses` implementation reproduced **both captured
writes byte-for-byte** using the passkey read from the private capture. The user subsequently tested build .3 against a new live challenge: both
stages were acknowledged, independently confirming the response calculation.

Web Crypto provides AES-CBC rather than ECB. For exactly one input block,
zero-IV CBC produces the required AES block as its first output block; the
implementation discards the appended padding block. This is also checked
against the standard AES-128 known-answer vector. See the
[Web Crypto AES-CBC specification](https://www.w3.org/TR/webcrypto/#aes-cbc).

Browser tests exercise both indication/write completion orders, both stages'
rejections, malformed responses, timeout, write failure, disconnect, invalid
challenge length, blocked identity reads, and omission of sensitive log values.
No real bike writes were performed by this agent.

The page performs authentication only after the user enters their passkey and
presses **Authenticate session**. It waits for the matching stage result and
stops on failure, disconnecting before a retry. It declares the milestone only
when both acknowledgements succeed and 2AF7 returns the expected display
identity. Build .4 conditionally sends one captured 2AFF setup command as
described below. No destination or firmware operations are implemented.

2AF8 is no longer read. Passkeys and outgoing authentication payloads are not
logged or saved. The old session-storage log is discarded because previous
builds logged 2AF8 values. Keep earlier exported logs private too.

## Firmware and destination remain unresolved

[eTuning's firmware guide](https://etuning-app.com/downgrade.pdf), pages 2 and
4, retains historical E7000 guidance: 4.5.0 for preparation from 4.6+, with
region/wheel changes listed through 4.5.0. The new first page says preparation
is integrated into the Android/iPhone apps.

[The live compatibility checker](https://etuning-app.com/en/), with E7000
selected, advertises mobile Bluetooth configuration regardless of installed
firmware and internally handled preparation (checked 2026-09-09).

These sources do not identify what preparation this specific bike needs. The
alleged 4.7.7 cutoff remains unverified. No destination command or firmware
preparation is implemented. Next: verify the drive-unit identity and firmware
on the actual bike, then trace configuration authorization and the modern
app's preparation decision separately.

## Private analysis location

Original files remain in the user's home directory. Extracted APKs, decompiled
code, capture data, hashes, and an offline browser/capture verifier are in
`~/shimano-analysis/`, outside this public repository. No raw capture,
user passkey, device address, or captured authentication ciphertext is committed.

## Live result and build 2026-09-09.4

The user's September 9 build .3 test received `10 01 01` and `10 02 01`,
but 2AF7 still returned GATT operation not permitted about 73 ms after the
second acknowledgement. This proves live acceptance of both stages; it does
not distinguish delayed availability from additional required setup.

The successful capture writes `FF 00` to 2AFF at frame 637, immediately after
stage 2, and receives the ATT write response at frame 639. It also enables
2AF9, 2AFB and 2AFD notifications before reading 2AF7 successfully roughly
575 ms after stage 2. Those additional subscriptions remain untested here.

Both APKs corroborate the setup command: old `d/a/a/a/c.java` case -15 calls
`g.k([-1, 0])`; new `Q5.java` case -15 calls `C0549qn.g0([-1, 0])`, which
writes `C0483on.X`. Decoding its UUID mapping confirms X is 2AFF. These paths
also schedule a 500 ms state-machine delay. This establishes the command's
placement in session initialization, not its complete internal semantics.

Build .4 first waits 500 ms and attempts 2AF7 without extra writes. If that
read fails, it sends `FF 00` to 2AFF exactly once, waits for the ATT write
response, waits another 500 ms and reads 2AF7 again. Successful identification
before setup avoids the write. Failed setup or timeout stops and disconnects;
failed identification after setup stops without additional commands. Browser
simulation covers setup success, failure, timeout, disconnect and continued
blocked access. The subsequent live test succeeded, as recorded below.

## Build .4 live session milestone

At 06:07 UTC on September 9, both authentication stages were acknowledged.
2AF7 remained blocked after the 500 ms wait. A single `2AFF ← FF 00` received
an ATT write response, and the subsequent read after another 500 ms returned
`53 43 45 37 30 30 30 00` (`SCE7000\0`). No other application writes or
notification subscriptions were needed in that test. The minimum required
delay has not been measured; the observation supports the setup command's
role but does not isolate it from all elapsed-time effects.

## Build .5: drive-unit information experiment

The capture and both APKs agree on these requests and response prefixes:

| Query | Write characteristic | Request | Notification characteristic | Matching prefix |
| --- | --- | --- | --- | --- |
| Drive-unit model | 2AFE | `00 01 1C 00` | 2AFD | `00 01 1E` |
| Drive-unit firmware | 2AFE | `00 01 2C 00` | 2AFD | `00 01 2E` |

Old `d/a/a/a/c.java` cases 20 and 22 send these requests via `g.j`.
New `Q5.java` cases 20 and 22 send them via `C0549qn.f0`, which writes
`C0483on.W`. The capture maps the write handle 0x002f to 2AFE and notification
handle 0x002c to 2AFD. Frames 748/751 contain the model query/reply;
frames 777/779 contain the firmware query/reply.

Old `d/a/a/a/h.java` cases 30 and 46 and new `In.java` cases 30 and 46
handle these replies. `In.x7` maps model byte 0x21 to DUE7000 and 0x22 to
DUE50X0. Firmware is decoded from the high/low nibbles of response byte 3
and response byte 4 as major.minor.patch (zero-based offsets).

**Artifact discrepancy:** frame 751's model fields are `00 01 1E 22 00`,
and frame 779's firmware fields are `00 01 2E 45 00`. With the APK decoder,
these mean DU-E50X0 family / 4.5.0, not the handoff's DU-E7000 / 4.7.1.
The display identity is still SC-E7000. This discrepancy is unresolved;
do not treat captured motor-dependent operations or firmware decisions as
validated for the target bike. Live information reads will establish the
current unit. No assumption is made about why the capture differs.

Build .5 keeps the verified authentication sequence and enables **Identify
drive unit** only after SC-E7000 session verification. On that explicit action
it subscribes to 2AFD and sends the model query, then the firmware query after
a matching ten-byte reply. Each request waits for both ATT write completion
and the matching notification, with an eight-second timeout. Other response
prefixes are ignored. Failure stops and disconnects, without retry or fallback
commands. Only the five information fields are logged; trailing bytes and
unrelated notifications are omitted.

This is deliberately a minimal transport experiment. The capture performed
additional 2AFA commands, subscriptions, and 2AF5/2AF6 operations before these
queries. Their necessity has not been established, so they are not replayed.
A timeout would leave transport initialization unresolved, not establish that
the motor is inaccessible through Bluetooth. No destination, configuration
write, or firmware preparation command is added.

Browser simulation covers both notification/write completion orders, unrelated
notifications, write failure, malformed reply, disconnect, timeout, no automatic
query after authentication, and decoding the captured fields separately from
a synthetic DU-E7000 / 4.7.1 fixture.

## Build .5 live result and .6 batch

Two September 9 live runs verified the SC-E7000 session, subscribed to 2AFD,
and sent `00 01 1C 00` to 2AFE. Both timed out without a matching reply.
Build .5 did not log ATT write completion or unrelated notification traffic,
so those logs cannot distinguish an incomplete write from a completed write
with no matching reply. They do not prove that 2AFD was entirely silent.

At the user's request to reduce phone-testing iterations, build .6 runs one
bounded batch after session verification. It enables 2AF9, 2AFB and 2AFD
notifications, matching the capture's subscriptions, and then sends:

| Order | Information query | Write | Matching notification prefix |
| --- | --- | --- | --- |
| 1 | Display model | 2AFA `00 13 01 1C 00` | 2AF9 `33 01 1E` |
| 2 | Display firmware | 2AFA `00 13 01 2C 00` | 2AF9 `33 01 2E` |
| 3 | Drive-unit model | 2AFE `00 01 1C 00` | 2AFD `00 01 1E` |
| 4 | Drive-unit firmware | 2AFE `00 01 2C 00` | 2AFD `00 01 2E` |

The display queries appear in old `c.java` and new `Q5.java` cases -5 and 2;
capture frames 669/672 and 694/697 show each write/reply. Old `h.java` and
new `In.java` cases 30 and 46 distinguish display replies (`33 01 ...`)
from drive-unit replies (`00 01 ...`). These are information queries, not
configuration setters. The captured initialization also includes other 2AFA
commands; their necessity and full semantics remain unresolved and they are
not added to this batch.

Each query has an eight-second deadline, logs ATT completion independently,
and accepts the first matching reply's five information bytes. A short
matching reply is reported without decoding. Extra bytes are omitted. If
ATT completes but no matching reply arrives, the batch continues to the next
distinct prefix. A failed or uncompleted write stops and disconnects; there
are no retries. Batch execution is limited to once per connection to avoid
ambiguous late replies from an earlier run.

The final summary lists all four outcomes and notification counts plus up to
eight distinct three-byte prefixes/lengths per channel. Unrelated payloads
are omitted. A successful run may be quick; four unanswered queries take
about 32 seconds plus discovery/subscription time. Keep Chrome foregrounded.
The added subscriptions and query ordering change the experiment: success
would establish this batch works, not isolate which added step is necessary.

Browser tests cover continuing after completed writes with no replies,
rejecting a late model reply as a firmware response, stopping on a stalled
write even if a reply arrives, short replies, both notification/write orders,
and the existing authentication and capture-response checks.

## Build .6 live result and .7 connection-setup batch

The September 9 .6 run returned display model fields `33 01 1E 21 02`
and display firmware fields `33 01 2E 41 00` (SC-E7000 / 4.1.0 using the
APK decoder). Both motor-query ATT writes completed. Neither motor query
received a matching response, and 2AFD and 2AFB recorded zero notifications.
This establishes a working display-command path and a silent downstream
response channel for that batch; it does not establish why that path is silent.

Build .7 inserts these captured connection steps between the display and
motor queries, with all three notification subscriptions already enabled:

| Step | 2AFA write | 2AF9 reply in capture | Capture frames |
| --- | --- | --- | --- |
| Setup 03 | `00 03 00` | starts `23 00` | 698 / 702 |
| Setup 04 | `00 04` | starts `24 8D` | 733 / 735 |
| Setup 06 | `00 06 00` | starts `26 00` | 744 / 747 |

The first captured 2AFD burst begins at frame 703, after setup 03. The first
successful direct motor model query is at frames 748/751, after setup 06.
Both APK connection state machines contain these commands in cases 5, 6,
and 8: old `d/a/a/a/c.java`, new `Q5.java`. The new `Q5.S0` reconnect path
also sends these same steps. They are connection-initialization commands;
their exact internal semantics and status-byte meanings remain unresolved.
Do not label them as proven scan/start/stop/select operations yet.

The experiment waits for both the ATT completion and a matching control
reply. It stops on a missing or short setup reply, or a setup 03/06 second
byte differing from the captured zero. Setup 04's second byte is logged but
not interpreted. A matching reply is evidence of receipt, not proof that
initialization succeeded. The page waits 1000 ms after setup 03 and 04 and
200 ms after 06 before proceeding. No automatic retries occur. The final
summary includes setup results and all observed notification traffic.

This is a subset of the captured setup, not a claim of a fully reconstructed
initialization protocol. In particular `00 13 32 50 07`, `00 0D 00`, and
2AF5/2AF6 operations are still omitted. No destination setter, firmware
transfer or arbitrary command interface is added. A successful batch would
validate the combined sequence on this bike, not isolate each step's effect.
A stopped or silent batch narrows which additional initialization to trace.

## Build .7 live result

The September 9 .7 test received all three captured setup replies, then both
motor replies. 2AFD delivered 27 notifications. Live motor fields were
`00 01 1E 22 00` and `00 01 2E 45 00`, matching the original capture and the
APK decoder's E50X0 family / 4.5.0. The initial E7000 / 4.7.1 handoff is not
supported by these live responses. The combined connection sequence is now
verified; individual setup-step necessity remains unisolated.

## Destination reads and US write path

Both APK connection paths query destination slots through 2AFE:

| Query | Request | Matching 2AFD response prefix | Value offset |
| --- | --- | --- | --- |
| Destination slot 0 | `00 16 AC 00` | `00 16 AE 00` | 4 |
| Current destination (slot 1) | `00 16 AC 01` | `00 16 AE 01` | 4 |

These requests/replies occur at capture frames 1033/1036 and 1037/1040,
and repeatedly later. Both captured values are zero. New `Q5.java` sends
them via `f0` (locate the `-84, 0` and `-84, 1` byte literals); old `h.java` case -82
and new `In.java` case -82 decode them. The region screen consumes the
slot-1 value. Slot 0's exact factory/default/persistent semantics remain
unresolved and are not assumed by the WebBLE UI.

New region activity `eTuning/shimano/steps/ui/ea/w.java::H` maps 0 to EU,
1 to US, 2 to Japan, 3 to Taiwan, 4 to Korea and 5 to US Class 3. The user's
target is **US value 1**, not value 5. Unknown/255 values are displayed as
unavailable rather than silently treated as EU.

The old `RegionActivity.writeClick` and new `w.z` direct BLE path both send
`00 16 A8 01 <destination>` through 2AFE. Thus the reconstructed direct US
setter is `00 16 A8 01 01`. Old/new response handlers recognize `00 16 AA`.
**This setter is documented, not implemented or live-validated.** The capture
contains destination reads but no instance of this setter, and firmware gates
must be resolved before relying on it. A result indication alone would not
prove persistence; a fresh-session destination read would be required.

## Firmware gate: concrete preparation lead

In eTuning 3.0.7, `w.z` checks `Gh.w` before taking its direct BLE region-write
path; failing this check routes to firmware/preparation activity `f91a2`.
`Gh.a` maps DUE50X0 into `Fh.k` (E5000 family, ordinal 10). `Gh.D` allows
that family's direct path only at firmware integer 430. `Gh.x`, `Gh.g` and
`Gh.k` contribute the other conditions. A private standalone Java harness
executing the extracted methods (`~/shimano-analysis/VerifyPolicy.java`)
confirmed: DUE50X0/430 -> direct gate true; DUE50X0/450 -> false.

This is the app's policy, not proof that the bike would reject an unsupported
write or that a downgrade is safe. The policy establishes 4.3.0 as a concrete
preparation candidate for the live-reported model. A second decompilation of
`f91a2` with debug/bad-code output exposes a 4.3.0 preparation option, but
JADX still flags that selection method as inconsistent. Its complete decision
path and the firmware transfer/recovery procedure are not yet verified.
No firmware transfer or downgrade is implemented.

## Build .8 validation and next live batch

Build .8 preserves the verified connection/setup sequence, reads display and
motor model/firmware, then reads both destination slots. Matching includes the
slot byte, so a slot-0 reply cannot satisfy slot 1. Missing, short and unknown
values do not produce a ready-to-change state. The summary names current
region, US target value 1, and the known preparation gate for E50X0/4.5.0.
It reports an already-US value without claiming persistence or speed behavior.

Browser tests cover the full sequence, wrong-slot notifications, unknown/short
region values, absence of destination setters, and the known firmware policy.
Next live result needed: current destination from this bike. Remaining offline
work: validate the preparation selection and transfer protocol, then implement
an appropriately verified region write and fresh-session readback.

## Build .8 live destination result and .9 export fix

The completed September 9 .8 run again verified E50X0 / 4.5.0 and both
motor information replies. Both destination ATT writes completed, but neither
received a matching slot reply within eight seconds. 2AFD delivered 77
notifications overall. Its first-eight-prefix summary does not establish which
other response types arrived during the destination queries. Destination remains
unverified; this is not evidence of EU or of a required downgrade by itself.

Build .9 changes log export only. The old copy handler passed the complete
visible text to the clipboard without slicing; the point of earlier truncation
is unknown. New exports have an explicit end marker/count, optional latest-
connection scope, and a full UTF-8 text download. Browser tests compare large
copied and downloaded snapshots exactly, plus scope selection and copy failure.

## Build .9 live result and .10 per-query diagnostics

The user's latest-session export contained its end marker and matching counts.
The .9 bike run again returned motor model/firmware while both destination
queries timed out after completed ATT writes. 2AFD delivered 84 notifications,
but the batch's first-eight-prefix summary could not characterize traffic
within each destination request window.

Build .10 adds query-local observers on 2AF9, 2AFB and 2AFD before each write.
Each summary reports notification counts, four-byte headers (including slot or
subcommand), total packet lengths, and first/last arrival time relative to the
query. Up to 64 distinct header/length pairs are retained per channel per query;
any excess is explicitly counted with its last header. Observers are removed
on completion, timeout, failure or disconnect. These windows show temporal
association, not proof that every notification is a response to the request.
Unrelated full payloads remain omitted.

A capture review found additional controller steps before the first destination
reads: frames 801–839 include control operations, several repeated 2AFA writes
at frames 818–828, and a return through the 03/04/06 sequence. Other intervening
unit queries follow before frames 1033/1037. These operations are not yet fully
mapped to the APK path or shown necessary, and are not added to build .10.
The observed destination timeout does not itself establish a firmware restriction.

At the user's request, log export is simplified to one Copy log button using
the latest connection. Full-log download, export mode selection, and Clear log
buttons are removed. The end marker/count remain; clipboard failure tells the
user to select and copy the visible text. Bluetooth commands are unchanged.

## Build .10 live AF/3A result and .11 handling

Both destination reads produced a 10-byte 2AFD notification beginning
`00 16 AF 3A`, at 98 ms and 87 ms respectively. The previous AE/slot-only
matcher ignored these and waited eight seconds per query. Temporal association
is strong, but the exact meaning of AF/3A remains unresolved.

The examined old `d/a/a/a/h.java::a` and new `In.java::F6` receive switches
handle AE destination data and AA write responses; no explicit AF case or
reliable mapping of 3A was found. This bounded source inspection does not prove
that no such mapping exists elsewhere. Do not import meanings from ATT or UDS
error tables, or infer a firmware restriction from this response alone.

Build .11 recognizes only the exact observed AF/3A header during destination
reads. It waits for ATT write completion, reports an alternate response with
unknown semantics, and stops the remaining destination checks because the
header has no verified slot identifier. Alternate payloads never enter region
decoding. Verified model and firmware results remain visible. No new BLE
commands or configuration writes are introduced; Copy log remains one button.

## Build .13: compare the missing connection setup

Build .11's live run confirmed `00 16 AF 3A 00` at 75 ms, with no other
notification in that destination query window. It is reproducible, but still
not a decoded region or an established authorization error.

Both eTuning versions include the following controller writes at connection
states 34–40, before their destination-read states 59/60:

| State | 2AFA write | Expected reply prefix |
| --- | --- | --- |
| 34 | `00 0C 01` | `2C` |
| 35 | `00 03 4B` | `23` |
| 36 | `00 04` | `24` |
| 37 | `00 06 1F` | `26` |
| 38 | `00 03 00` | `23` |
| 39 | `00 04` | `24` |
| 40 | `00 06 00` | `26` |

Source locations: old `d/a/a/a/c.java`, cases 34–40 (lines 1818–2017);
new `Q5.java`, cases 34–40 (3996–4322), also repeated in `S0`
(8338–8405). This establishes an ordinary connection-path sequence in both
APKs, not its individual commands' internal semantics or sufficiency.

The supplied capture's corresponding frames are 801, 806, 811, 814,
831, 836 and 839. Frame 806 uses **4D**, whereas both APKs use **4B**.
Frames 818/822/825/828 contain four additional controller writes beginning
`00 88`; no matching literal was found in the examined APK Java sources.
These differences mean the capture cannot be treated as an exact transcript
of either supplied APK. The emitting app/version remains unverified.
There are also intervening unit reads and controller operations before the
first destination read at frame 1033; necessity is unresolved.

Build .13 adds the seven APK steps after the already verified initial setup,
then repeats model/firmware and destination reads. Each controller operation
requires its matching response before continuing, with conservative pauses.
The 4B request's `23 00` response is an expectation based on the existing
03 response shape; it has not yet been observed live. Setup reply bytes are
not interpreted as proof of configuration authorization. The unmatched 88
writes are omitted. No destination setter or firmware transfer is added.

Experiment interpretation: an AE destination reply would show this added
sequence is sufficient with our preceding steps. AF/3A would show this
sequence is insufficient; it would not establish that a downgrade is required.
The motor identification discrepancy also remains open: repeated live results
and the original capture agree with the APK decoder's E50X0 / 4.5.0, rather
than the original handoff's E7000 / 4.7.1. No firmware image is selected.

## Build .13 live success and preparation/authorization trace

The live test at 08:04:42 UTC returned `00 16 AE 00 00` and
`00 16 AE 01 00`: both destination reads now work, and current destination
is EU (0). The seven added setup steps are sufficient with our preceding
sequence to enable these reads. Their individual necessity is not established.
No unmatched capture 88 writes were needed.

### The firmware gate is an application decision

In eTuning 3.0.7, region activity `w.z` (lines 454–485) calls `Gh.w`.
For the model decoded as DUE50X0, `Gh.a` yields family `Fh.k` (ordinal 10);
`Gh.D` accepts only version 430. `Gh.w = Gh.x && !Gh.g && Gh.D`.
Consequently 4.5.0 fails the direct-write gate and 4.3.0 passes it. This is
not a device rejection or proof that a direct write would fail on 4.5.0.

The preparation activity `f91a2.e0` contains a DUE50X0/E5000 choice
`Ju(Ih.n, 0, "4.3.0")`. JADX warns about this method's reconstructed
control flow, so the selection is a strong lead, not a verified full workflow.
Independent decoding of `Ih.n` identifies family E5000, display label
E5000 / E5080 / E5080-H, model identifiers DUE5000-D and DUE5000-M,
and model code 34. Its separate `h` field contains 4.5.0; do not confuse
that family metadata with the choice's explicit 4.3.0 target.

The choice handler `f91a2.v0` dispatches `C0791y2.D`, which checks
`Gh.c` and `X2.a`, obtains a file via `W2.a(choice.b, context, identifier)`,
and passes it to `Oa.s(file, choice.a)`. `Oa` parses archive contents,
constructs firmware candidate records and uses a digest routine. Preparation
then leads to `f64d9`, which binds foreground service `f9c41`; its worker
invokes `f9c41.U`, with `Th` implementing Bluetooth-related update logic.
This establishes a firmware-package and installation path, not merely more
session setup. Package selection, integrity/authenticity checks, bootloader
entry, transfer acknowledgements and interruption recovery are not yet
reconstructed sufficiently for a WebBLE firmware implementation. No package
was downloaded or selected for flashing in this investigation.

### A separate motor challenge/response path is still missing

The new APK's `In.F6` model-code-34 branch calls `AbstractC0640tg.Q0`,
setting flag L. The firmware handler enables Y when `f0()` (flag L) is true
and version >=410. A motor serial reply (`00 01 3E`, at least ten bytes
needed for all accesses) sets X through `b1()`. Thus E50X0 / 4.5.0 is
eligible for this branch once the serial is read; this is also true at 4.3.0.

`Q5` states 68–74 conditionally perform the following exchange on 2AFE:

- Generate seven challenge bytes and a sixteen-byte key from the serial via
  `J0` and its PRNG helper.
- Send D8, with conditional E8 and D8 follow-ups based on response flags.
- Assemble returned challenge data and encrypt it when the required flags
  are present.
- Send the sixteen-byte result in three E0 fragments, tagged 16, 26 and 34
  (hexadecimal tags), conditional on the crypto-ready flag.

The older APK has a corresponding branch at states 67–73. This is a
motor-level challenge/response sequence distinct from 2AF3 session auth and
from the setup that enabled destination reads. Its precise authorization
scope and the necessary terminal-success criterion are not yet established.
The current WebBLE app neither reads the motor serial nor runs this exchange.
A scan of the supplied ATT trace found no 2AFE/2AFD packets with D8, E8,
E0, DA, EA or E2 opcodes under `00 16`, so it supplies no ground-truth
example for validating this branch. Serial and generated payloads must remain
private and must not be included in public logs or fixtures.

The direct destination setter remains `00 16 A8 01 <value>`; US is 1.
The activity sends it after its gates; the receive parser has an AA callback.
An ATT acknowledgement or that callback alone would not demonstrate durable
configuration: a verified implementation needs current-destination readback
and a reconnect/power-cycle persistence check. Nothing here establishes that
this command alone is sufficient on 4.5.0, or that motor auth bypasses the
firmware requirement. No destination setter, motor auth exchange, or firmware
transfer has been sent by the WebBLE app.

Next implementation boundary: reconstruct and test the motor exchange and its
success criterion before attempting a persistent region change. Firmware
preparation remains a separate, substantially larger implementation task.

## Build .14 motor authentication experiment

The serial read is `00 01 3C 00`, with `00 01 3E` plus six serial bytes
in little-endian order (bytes 3–8; minimum length nine). The previous note's
ten-byte minimum for serial data was overly strict; ten bytes are required
for the motor challenge fragments, not the serial field.

Reconstruction: `Q5.J0` seeds the four 32-bit xorshift words from the serial,
warms up by serial byte 1, emits seven request bytes (discarding the eighth
byte of the second word), then emits sixteen key bytes starting at a fresh
word. `Q5.q1` explicitly uses AES/ECB/NoPadding. `In.F6` assembles DA tags
16/26/34 into six, six and four bytes, requiring FF FF padding on tag 34.
The `AbstractC0640tg` getter/setter mapping confirms that concatenating those
parts in tag order is the sixteen-byte plaintext used in state 71.

The E0 response has tags 16/26/34, carries six/six/four ciphertext bytes, and
pads the last fragment with FF FF. `In.F6` case E2 with FF FF in bytes 3/4
sets both the APK's completion flag (`e1`) and atomic flag `a`. Build .14
reports that marker, without claiming its permission scope. A marker before
the third response write is treated as premature; ATT completion is required.

The experiment is gated to the observed E50X0 / 4.5.0 with destination
readback, one attempt per connection. DB, E3, malformed/incomplete/conflicting
challenge fragments, unexpected completion fields, write failures and timeout
stop the exchange and disconnect. It does not automatically execute the APK's
conditional E8/D8 fallback or any persistent configuration operation. Sensitive
serial, derived key, challenge and ciphertext values are omitted from all app
logs and exports. Synthetic fixtures use invented serials and a fixed
00..0F challenge; Python integer arithmetic and cryptography AES/ECB provide
an independent reference for the browser computations. No captured motor
authentication exchange exists, so actual bike validation is still required.

## Independent desktop-library cross-check after build .14

Statically inspected the assemblies distributed in E-TUBE Project 3.4.5,
retrieved from the [installer archive mirror](https://assets.bettershifting.com/archive/E-tube_Proj_V_3_4_5.zip).
The installer was unpacked without execution. This is an archived distribution,
not a freshly authenticated download from Shimano; hashes identify the exact
evidence inspected, rather than proving publisher authenticity. Binaries and
disassembly remain outside this public repository.

- ZIP SHA-256: `62266eedf48e9a8f6ec25dd68c9c899f405bf41d9bf9fe3931786877644d4787`
- etubedata.dll SHA-256: `e67f2a12a678628521095dfef9cc27d5588abda8988606206b03ad43382e1dbe`
- etubedatalinks.dll SHA-256: `814d8096d9f6e5552d8131ff840d3bf407b0f0b089c9a0a821cbb34f141e5ab5`

`AuthKeyGenerator.GenerateKeys` independently agrees with the APK reconstruction:
the same serial-derived seeds, byte-1 warmup, seven request bytes, discarded
eighth byte, and fresh-word start for the sixteen AES-key bytes.
`DuAuthHelper.ProcessRegulationSetAuth` performs key generation, the D8 challenge
request, encryption and the E0 response. This corroborates the algorithm, but
does not replace a live test of the WebBLE framing and completion handling.

The library provides useful distinctions absent from our earlier log labels:

| Item | Library interpretation | Remaining limit |
| --- | --- | --- |
| Error 3A | `DCC_PRM_ERR_CMD_NOT_DISPOSE` | Does not identify which setup prerequisite was missing. |
| Error 3B | `DCC_PRM_ERR_CMD_INVALID` | The D8 handler returns authentication `Unnecessary`; this is not proof that a destination write is allowed. |
| Error 46 | `DCC_PRM_ERR_AUTH_LOCK` | The D8 handler returns authentication `Locked`. |
| E8 / EA | Authentication-lock release request / reply | `UnlockRegulationSetAuth` uses the serial-derived seven bytes; caller policy and live behavior need verification before adding a retry. |
| Destination selector 0 / 1 | Factory / OEM rewrite selectors | Consistent with the two observed reads; do not assume both values are changed together. |

`ProcessRandomValueAuth` sends the three E0 fragments through the desktop
send/receive helper, with 100 ms spacing, and checks the last communication
result. The mobile APK supplies our E2 FF FF completion criterion. Their
different transports do not establish that intermediate desktop replies have
the same shape on BLE; build .14's early-completion rejection still requires
live validation.

A further read-only lead is `DUUnitDataLink.GetMaxAssistSpeedForEachDestination`:
group 16, command BC, one destination parameter, reply BE. It extracts a
two-byte unsigned value from response parameters 1 and 2. Units and BLE
response layout are not yet validated, so this query has not been added to
the app or used to predict the bike's assistance cutoff.

Next evidence needed: the build .14 motor-authentication result. EU readback is
established by the user's build .13 test. US configuration, persistence and
speed behavior remain unverified; no firmware or destination write is enabled.

### Desktop caller policy for authentication locks

Static inspection of `e_tube_project.exe` from the same installer confirms
how the authentication results are used. SHA-256:
`e0f16523dcaef90aedd8f271161f7f8747bb7109414ce55950ce7bffdb3979fb`.
`DriveUnitLoadPanel.loadWorker_DoWork` (RVA C6AA4, IL 016F–0221)
calls `ProcessRegulationSetAuth`: Success (0) and Unnecessary (3) continue;
Fail (1) stops; the remaining defined result, Locked (2), calls
`UnlockRegulationSetAuth`. An unlock failure stops and marks both authentication
and unlock failure. An unlock success loops back to authentication.
`UnitWriteCheckPanel.RightButtonClickedHandler` has the corresponding flow.

This narrows the future BLE fallback: an explicit DB error 46 is evidence for
trying E8 and then a fresh D8 exchange after a verified unlock acknowledgement.
A generic DB, timeout or malformed challenge is not equivalent to that lock
result. The desktop loop itself is not a reason to add unbounded WebBLE retries.
The live EA response shape remains unverified; build .14 deliberately retains
its single-attempt behavior while awaiting the first motor-authentication log.
This finding does not resolve the separate eTuning firmware-preparation gate.

## Live build .14 motor authentication and build .15 setter experiment

The user's 2026-09-09 08:41 UTC test independently reproduced E50X0 / 4.5.0,
factory and OEM destination 0, then completed the motor exchange:
serial read, DA tags 16/26/34, three E0 fragments, and E2 FF FF after the
third fragment. No E8 fallback was required. Sensitive values were omitted
from the log. This validates the implemented exchange on this bike; it does
not prove destination-write permission or remove the APK preparation gate.

The next bounded experiment uses the exact mobile setter from eTuning 3.0.7
`w.z` (lines 483–489): `00 16 A8 01 01`. `In.F6` case -86 recognizes the
`00 16 AA` header and invokes the region activity callback; it does not inspect
further response fields. The desktop setter agrees on group 16, opcode A8,
OEM selector 1 and destination value 1, though its transport has additional
parameter padding. The mobile five-byte packet is used for BLE.

Build .15 offers a separate explicit button, restricted to the observed
model/firmware, successful motor authentication and EU readback. A fresh OEM
read must still return EU before the one permitted setter invocation.
AA is logged as an acknowledgement, AB as an error with its code. After AA,
or no acknowledgement within 20 seconds with completed ATT, a new AC 01
request must return AE 01 01 to report US readback. A write failure, malformed
error, disconnect or missing/invalid readback never produces that milestone.
Unknown write outcomes require reconnect/readback rather than retrying.

This is explicitly an experiment outside the newer APK's direct-change policy
for 4.5.0. It tests whether motor authentication is sufficient for the known
setter; rejection or unchanged readback leaves preparation unresolved. No
firmware operation, other destination value, factory-slot setter or speed
setter is available. Persistence requires a later read after a user-confirmed
bike power cycle. No software-only test can establish the actual speed outcome.

## Build .15 live result: authenticated destination write rejected

The user's first 2026-09-09 session completed motor authentication at
08:54:13.067 UTC. A fresh AC 01 read at 08:54:15.660 still returned
`00 16 AE 01 00`. The app then sent exactly one `00 16 A8 01 01`.
ATT completed, followed by `00 16 AB 3A 00` at 08:54:15.731; the app
reported rejection and disconnected. There was no AA acknowledgement and no
US readback.

The user then reconnected and ran the information batch without a destination
setter. At 08:54:58.974, AC 01 again returned `00 16 AE 01 00`. Factory
slot 0 also remained 0. This independently confirms EU after reconnect.
A physical power cycle was not stated and is not inferred from the log.
This is a rejected-change result, not evidence that a successful US change
was lost during a restart.

Conclusion: the exact build .15 sequence, including successful motor auth,
is insufficient to set US on the reported E50X0 / 4.5.0. Error 3A alone
does not distinguish a firmware restriction from another missing protocol
state. It is not the 46 authentication-lock error, so the E8 lock-recovery
path has no supporting trigger here. Repeating the unchanged setter would
not test a new hypothesis. No downgrade has occurred.

Preparation follow-up: the explicit `Ju(Ih.n, 0, "4.3.0")` candidate remains
the source-grounded lead. A debug instruction dump of `W2.a` confirms a POST
through `Ik.w`, an output cache file, and acceptance only for a 2xx response
with a nonempty file. `C0791y2.D` then supplies that file and selected family
to `Oa.s`. This is a downloaded asset workflow, not evidence of one additional
BLE unlock command. The downloaded contents, whether stock or modified, exact
hardware compatibility, transfer protocol and recovery path remain unverified.
No request using extracted app credentials, asset download or flash was made.

## Preparation research: component headers and update entry

`Oa.B` first calls `Ha.d` (an optional asset-unwrapping path), then recognizes
two relevant raw motor component layouts. For E5000-family code 22:

| Component | Version offset | Family bytes | Additional classifier |
| --- | --- | --- | --- |
| D / DCAS_X | 16 | 40–41 = 22 00 | byte 42 = 04 |
| M / RENESAS | 8 | 14–15 = 22 00 | separate raw layout |

`Ja.a` decodes three bytes as major/minor nibbles in the first byte, patch
in the second, build in the third. A matching version string alone does not
identify the component. `tools/inspect_firmware.py` implements only these raw
4.x header classifiers, with additional reference-sample header checks. It
does not implement `Ha.d`, trust a filename, or certify completeness, publisher
authenticity or bike compatibility. SHA-256 is an identifier, not a signature.

Validation used two actual files statically extracted from the already
identified E-TUBE 3.4.5 installer archive; binaries remain outside the repo:

- `due5000_d.4.1.0.dat`: 135052 bytes, decoded 4.1.0.0, SHA-256
  `fdb0f40b94d55ce9d098f803fe0f2f4038a3ce3343fe539bf151a9511dda14ec`.
- `due5000_m.4.1.0.dat`: 116128 bytes, decoded 4.1.0.0, SHA-256
  `ed5593f61b58509ab5f1b7c7bcd82415abb3d1dbf57283dfc5ffb90219be6224`.

These are parser samples, not selected firmware. Synthetic tests cover the
different offsets, wrong-family rejection, short input, invalid version
fields and the distinction between metadata recognition and content integrity.

The generic updater is `Th.u3 -> v3`; `v3` required a debug instruction dump
because JADX failed type inference. It selects a `Jh` plan with component
references and reaches `Th.p3` before the `C0041b7` transfer worker. The
separate `Th.q4` entry contains an Ih.k-specific check and must not be mistaken
for the generic E5000 path. `C0041b7.x1` loads/unpacks the file and forwards
it to `w1`; the complete E5000 transfer/finalization path is not yet mapped.

`Th.p3` reads setup state through `Hn.r0`, then the non-Ih.k path can call
`Hn.p0`. The latter explicitly names `PCA_UPDATE_SET`: command group 32,
opcode 20, payload 01 (hex), requiring reply opcode 22 with value 01 and
handling opcode 23 as rejection. `Hn.r0` composes the familiar setup 03/04
exchange; `Hn.s0` sends 06. This establishes a distinct update-entry step,
not permission to invoke it without a verified image and recovery workflow.
None of these update commands was added to WebBLE or sent to the bike.

Before image selection, the physical motor model needs reconciliation with
the original E7000 handoff and the repeated E50X0 / 4.5.0 BLE replies. The
user was asked for the casing model. No stock/modified 4.3.0 image has been
selected, and the US-region goal remains incomplete.

## Electronic identity cross-check and build .16

The user cannot identify the model from the casing. This is not a prerequisite
for continuing research: the desktop library independently corroborates the
existing numeric reply interpretation. In the previously hashed
etubedatalinks.dll, `DuE5000Unit..cctor` (RVA 5A310) sets series number 34
(hex 22), unit number 0 and model name DU-E5000. `DuE7000Unit..cctor`
(RVA 5B73C) instead sets series number 33 (hex 21), unit number 0 and
DU-E7000. Both include seven model-discrimination bytes. This supports the
E5000-family interpretation of our repeated 22 00 replies, independently of
eTuning's newer E50X0 family label. It does not identify every later variant.

The desktop constant `DCC_CMD_PU_MD_MODEL_GET_C` is 7C. eTuning `Q5`
connection state 43 (also state 21 in another path) sends the exact BLE query
`00 16 7C 00`. `In.F6` case 126 consumes `00 16 7E` with at least ten
bytes, passing the seven descriptor bytes starting at offset 3 to `y7`.
That parser uses known variant strings rather than assuming the entire reply
is a full model name. Some decompiled string-match helpers have missing
mismatch branches; their reconstructed control flow is not used for inference.

Build .16 appends this one read to the existing batch, retains the ten-byte
descriptor response, and displays its raw bytes and ASCII without assigning a
variant. The 7F error prefix is reported promptly; short replies, errors and
timeouts do not replace the numeric identity or enable a firmware operation.
Tests cover those four outcomes and verify the exact read-only 2AFE sequence.
The descriptor's utility on this motor remains a live-test question.

## Build .16 live result and .17 write gate

The 2026-09-09 09:34 session returned `00 16 7E 00 00 00 00 00 00 00`.
Seven zero descriptor bytes, together with series 22 and unit 00, match the
older desktop DuE5000Unit master entry (its seven-byte array is zero initialized).
This strengthens the electronic E5000 identification despite the original E7000
handoff; it does not establish compatibility of any preparation image.

Motor authentication again completed with E2 FF FF. The US setter again
returned `00 16 AB 3A 00`, repeating the .15 rejection. The fresh pre-write
read reported EU. This session did not include a post-rejection readback;
the previous .15 reconnect had independently confirmed EU after its rejection.
No successful US write or speed change has been established.

Build .17 requires explicit direct-write eligibility independently of motor
authentication. No current production path grants it. The retained setter is
covered by synthetic eligible-session tests; the real information-batch path
is tested to remain disabled even when motor authentication is marked complete.
UI instructions no longer invite the rejected experiment. Next research remains
the exact E5000 preparation asset, transfer/finalization sequence and recovery
requirements. No firmware candidate has been selected or transferred.

## Offline preparation analysis: D transfer arithmetic and component pairing

To reduce motor iterations, the next work is validated offline. The supplied
3.0.7 `C0041b7` D worker now provides a concrete encoding model:

- `w1` performs update entry, bootloader identity/serial handling, preparation,
  data transfer, finish and conditional reset. These stages are not interchangeable
  with ordinary motor authentication or the region setter.
- `Q1` reads 64-byte blocks, padding the final block with FF. Its block checksum
  includes padding; its separate contribution to the finish checksum excludes it.
- `M1` produces 70 inner bytes: sequence, 02, 00, 64 data bytes, block checksum,
  and little-endian block index. In the E5000 branch the index starts at zero.
- `Hn.k0/i0/I` prepend command 0B; `C0483on.U` decodes to 2AFA. This implies a
  71-byte data write at that layer, not the short 2AFE motor command transport.
  Actual Chrome/SC-E7000 handling of this long write remains untested.
- `u1/m1` consume separate sequence values for data and query; the no-retry path
  starts with data sequence 0 and wraps after 255. The query refers to the data
  sequence. Source timeouts are 25 seconds for the first three blocks and 3 seconds
  thereafter. Reply correlation and retry/recovery are not ported.
- E5000 addresses in `S1` simplify to 4000 hex plus block offset. `u1` changes
  banks at blocks 1024 and 2048, with addresses 14000 and 24000 hex. The offline
  model deliberately rejects images beyond the three modeled 64-KiB banks.
- `C1` uses floor((length - 1)/2048) in START, then bank/address setup. `h1` uses
  the unpadded byte sum modulo 256 in FINISH. Neither command is sent by our tools.

`tools/plan_d_transfer.py` implements only the arithmetic and payload encoding.
Its CLI emits a summary and fingerprint, not executable transfer commands. It
rejects M files and unknown headers, always reports `installable: false`, and
lists the outstanding protocol and asset requirements. It is not imported by
`index.html` and has no Bluetooth or network operations.

Seven synthetic vectors were generated by compiling the extracted, stateless
Java `Q1`, `M1`, and `S1` methods with minimal local data-source stubs. No APK or
native vendor binary was executed. The resulting vectors exercise partial/full
blocks, sequence bytes 0/254/255 and both bank boundaries. Only synthetic input
outputs are committed, not vendor source or firmware. `tests/d_transfer.py`
compares the independent Python implementation to those vectors, reassembles
images across boundaries and verifies both checksum definitions and rejections.
Together with the existing header tests, all six tests pass.

The archived 4.1.0 D reference sample produces 2,111 blocks, 52 padding bytes,
finish checksum 02, padded checksum CE and three banks. This is a parser/codec
reference only, not an installation candidate.

The current [reven firmware catalog](https://github.com/reven-project/etubeapi/blob/master/fw-scraped.yml)
lists DUE5000-D.4.3.0.dat (one record says 132,072 bytes). Its published Shimano
URL returned HTTP 403 during this run. The catalog has no E5000 M 4.3.0 entry;
listed M versions include 4.1.0 and 4.2.1, then 4.4.x. A guessed M 4.3.0 URL
also returned 403 and is not evidence that such a file exists. D and M version
numbers must not be assumed equal. Catalog metadata is not a verified image hash
or proof of the component pair used by eTuning's preparation archive.

The generic `Th.v3` instruction dump has a conditional M stage using
`C0776xk.A0` before the conditional D stage using `C0041b7.g1`. The M worker
unwraps its file, uses its own START/address/checksum/transfer/FINISH flow and
separate 11/12 data payload types. Its `E0` and recovery routines require
instruction-level analysis because normal JADX output omits them. The debug
dump is retained privately for that next step. No complete M transfer, paired
finalization, recoverable update procedure or validated preparation asset is
available yet. The phone-only US configuration goal remains open.

## Offline M payload and checksum-window model

The 3.0.7 `C0776xk` constructor sets its EP-specific flag only for `Ih.k`;
E5000 is `Ih.n`. Its `E0` instruction dump selects a 1024-byte checksum window
for the non-EP path. `j1` allocates a zero-initialized 64-byte block and copies
only the remaining file bytes. At a window boundary or image end it computes
the byte sum from the window start through the last real byte.

`M0` emits sequence / 11 / 00 / 64 data bytes for ordinary E5000 blocks.
At a checkpoint it uses type 12 and appends checksum / 00 / 00, including when
the checksum itself equals zero. With the outer Hn command 0B, those are 68-byte
and 71-byte data writes. The final checksum is the original image byte sum
modulo 256. It is not the D codec and must not reuse its FF padding or footer.

`Q9.d` computes recovery-window geometry, including partial final windows.
`T0` clamps a reported failure offset within that window, sets the write address
relative to FC0000 hex, and invokes block handling from that point. The checksum
start remains the window start. This is partial evidence for window recovery,
not a validated rule to resume after disconnect or power loss. Retry selection,
reply classification, progress semantics and paired finalization remain open.

Sequence handling also needs its own implementation: `j1` calls the sequence
counter while constructing a diagnostic payload, and `f1` consumes another
counter value for the actual write, followed by the query. The offline M codec
therefore takes an explicit sequence byte and does not invent a complete
transfer schedule. `f1` has a 400-ms delay before a data attempt and a 15-ms delay
before querying; a live updater cannot assume maximum-throughput streaming.

`tools/plan_m_transfer.py` now reports checksum windows, payload lengths,
zero padding and image checksum without sending commands or scheduling retries.
It accepts only M-classified input and bounds addresses to the modeled 24-bit
space above FC0000; this limit is not a certified flash-capacity statement.
All outputs retain `installable: false`.

Seven additional synthetic vectors were generated with the extracted Java
`M0` and `Q9.d` routines, with the surrounding block/checksum calculation
reconstructed from `j1`. Tests cover those vectors, zero-valued checkpoints,
window boundaries, reassembly and invalid inputs. Combined header/D/M tests:
ten tests pass. The archived M 4.1.0 reference has 1,815 blocks, 32 zero padding
bytes, 114 checksum windows and finish checksum AA. It is not an update candidate.

Neither supplied APK contains firmware under assets or res/raw: 1.0.32 has no
such entries; 3.0.7 has only two dex optimization profile assets. The downloaded
preparation package remains a separate artifact; `Jh.d` checks the presence of
both components and does not establish that their version numbers must match.

## Archived E5000 D 4.3.0 / M 4.2.1 pair found

The [Shimano firmware history](https://bike.shimano.com/products/apps/firmware-update.html)
places E5000 4.2.1 on November 18, 2019, 4.3.0 on May 18, 2020, and 4.4.2 on
November 4, 2020. The [desktop release history](https://bike.shimano.com/products/apps/e-tube-project-professional.html)
dates E-TUBE 4.0.2 to October 13, 2020. That timeline suggested inspecting its
bundled files. The installer was retrieved from the
[E-TUBE archive mirror](https://bettershifting.com/e-tube-project-archive/)
and unpacked statically; no installer or vendor code was executed.

Archive `E-tube_Proj_V_4_0_2.zip`: 180,864,996 bytes, SHA-256
`903a343e2fde116b36846045267c9953d64535a9ed49a9adde864f18c9b56960`.
The embedded MSI's Data1.cab contains both files below, each with a June 5,
2020 archive timestamp. Header classification agrees with their filenames:

| Component | File | Bytes | SHA-256 |
| --- | --- | ---: | --- |
| D | due5000_d.4.3.0.dat | 132072 | `3d3df4dfe3de333062f445b6719fa5033f93dc9d384448134ee6041d216c6af0` |
| M | due5000_m.4.2.1.dat | 116320 | `10190fd78e6527908c0e43405184c414b612bc4becce9ca5483612665ced6b56` |

The offline D planner yields 2,064 blocks, 24 FF padding bytes, three banks,
finish checksum A1 and padded checksum 89. Its no-retry data-frame fingerprint
is `80a9c5a498cba7ac25acf5ab150311b29f03af17352fbbc0ba870bf3adbfabf3`.
The M planner yields 1,818 blocks, 32 zero padding bytes, 114 checksum windows
and finish checksum 06. Both tools continue to report `installable: false`.

This is evidence that the desktop distribution bundled D 4.3.0 with M 4.2.1.
It does not establish publisher authenticity, the contents of eTuning's remote
preparation package, compatibility with this bike, or a working downgrade and
recovery procedure. The 4.0.4 archive was also inspected and instead contains
D/M 4.4.3. All extracted binaries remain private and outside this repository.

Next implementation gates are the M reply/sequence state machine, conditional
D/M selection and finalization in `Th.v3`, and recovery behavior. The existing
AB/3A rejection remains the live result; no new region or firmware write was
introduced by this offline work and no additional motor test is needed yet.
