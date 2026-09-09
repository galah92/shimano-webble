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
