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

## Component selection and native version reads

Further inspection of 3.0.7 `Th.v3` maps its selected `Ka` objects to M (`r10`)
and D (`r15`) at the worker calls. In normal mode, `Mh.l(target, installed)`
compares all four version fields using `Ph.c`: major<<20, minor<<16,
patch<<8, build. Both upgrade and downgrade comparisons select a transfer;
equality does not. Forced rewriting and recovery have additional branches.
An installed minor nibble F with a non-F target is a separate recovery case.
The normal path executes selected M before selected D, and an M failure exits
before proceeding to D. This does not yet establish the full recovery flow.

`tools/compare_components.py D.dat M.dat --installed-d A.B.C.D
--installed-m A.B.C.D` models that ordinary comparison with explicit installed
versions. Unknown versions and recovery states produce no proposed order.
It never treats component comparison as installation approval. Three synthetic
tests cover independent selection, ordering, missing/recovery information and
the fourth version field. The candidate pair cannot yet be planned for the
real bike because separate native installed versions have not been observed.

`Th.y3` reads native firmware with `Hn.n0(0, 1, 0x84, [IC], D3(slot), ...)`.
IC=0 is labeled DCAS/D and IC=1 Renesas/M in `Q2`. `D3` maps slot zero to FF,
forcing the ordinary motor transport for that case. `Hn.n0` constructs
`00 01 84 IC` for this route; it is distinct from our existing `00 01 2C 00`
version query. `Wi(18)` accepts normalized replies beginning `01 86` or
`01 87`, with at least five bytes. `Th.Z3` identifies `01 87` as the unit
firmware-error path. `Ph.b` parses the packed major/minor from normalized byte
2, patch from byte 3, and build from byte 4.

These replies do not echo the IC selector in the recognized prefix. A browser
batch must therefore stop on a timeout or transport error before issuing the
other selector; the general claim that every information query has a distinct
prefix would be false for these new reads. No native queries have been added
to the live app yet. Source parsing is not a live observation.

`Q2` normally retries final verification up to three times with a four-second
delay between failed attempts, re-reads both native components and compares
their four-field versions against target metadata. However `v3` has a distinct
post-D branch that bypasses this ordinary `Q2` call. That branch and its reset/
reconnect behavior remain to be reconstructed before defining completion.

## Build .18: native D/M reads in the existing information batch

The batch now ends with `00 01 84 00` and `00 01 84 01` on 2AFE,
matching the ordinary motor route derived from `Th.y3` / `Hn.n0`. It recognizes
`00 01 86` success and `00 01 87` error prefixes on 2AFD and requires six
bytes for a successful transport-prefixed reply. All three version bytes are
retained, yielding major.minor.patch.build. D/M versions are logged separately
from the original drive-unit firmware result.

The reads are serialized without retries. Because the reply lacks an IC echo,
any error, short reply or timeout ends this pair before the next selector is
sent. A thrown write error or disconnect stops the batch as usual. A batch
cannot be repeated on the same connection. This prevents a late timed-out D
reply satisfying the M query. The protocol still assumes one response to each
successful request; arbitrary duplicate successful responses lack enough
information to disambiguate by IC. These requests and decodes require live
validation. No firmware transfer or region write is enabled.

The post-D finalization branch is now partly resolved: `Th.v3` calls `Lh.c`,
which constructs `(verified=false, failed=false, deferred=true)` and labels
verification "diferida". This is explicitly deferred verification, not a
successful version check. `C0041b7.g1` passes reset=true through `x1` to `w1`;
after transfer/finish, `w1` invokes `n1`, which sends command 40 (28 hex) via
its D transport wrapper and throws on transport failure. A fresh connection
and native D/M version readback are therefore required by our completion
criterion even when this source worker returns true. Reset acknowledgement
alone cannot prove application startup, version persistence or region change.

## E5000 M reply correlation

`C0776xk.F0` registers `C0644tk` before sending outer command 0B with payload
`querySequence 03 dataSequence`. Its response deadline is three seconds after
that write completes. The observer examines normalized `Dn` records from
`Hn.K`; these are not the raw GATT payloads.

For a protocol byte satisfying `(protocol & 0B) == 0B`, the observer recognizes:

- normalized byte 1 = 83, byte 2 = query sequence: byte 3 is query status;
  a positive status terminates `F0` as failure;
- byte 1 = 91 or 92, byte 2 = data sequence: a data-status observation,
  recorded separately from acknowledgement;
- byte 1 = C0, byte 2 = data sequence: the matching packet acknowledgement.
  C0 with another sequence is counted but does not acknowledge this packet.

For E5000 checkpoint blocks, `e1` scans the normalized payload for the first
`F2 00` marker. Status 31 is the checksum-success marker and 32 is failure.
This marker has no sequence correlation and the source scan is not gated by
the protocol mask. `F0` requires a matching packet acknowledgement and a
checkpoint result; a missing checkpoint result fails at the shared deadline.
Checksum failure and positive query-error status take precedence over success.
Non-checkpoint blocks do not require a checksum result. The EP-specific extra
checksum-query path (`p1`) is false for E5000 and must not be imported into it.

`tools/m_reply.py` records these distinct observations from an already-normalized
envelope. Four synthetic tests exercise wrong sequences, protocol masks,
truncated messages, first-marker behavior and the lack of checksum correlation.
It deliberately exposes `uncorrelated_checksum_status`; it does not decide that
an image block can be committed or retried. Raw `Hn.K` framing, notification
fragmentation and late checkpoint results remain to be validated before this
can drive an updater. No new bike command or deployed HTML change was needed.

## Raw notification candidates for the M observer

`Hn.K` calls `C` on the original bytes, optionally on bytes after a leading
zero, and optionally on the output of `J(raw, false)`. `C` normally takes byte
0 as protocol and the remaining bytes as payload; protocol 48 hex skips two
bytes, while a payload starting F2 is assigned protocol 48 and retained whole.
These are candidate interpretations, not a unique framing decision.

`J` optionally removes a leading zero, requires a trailing BB delimiter, skips
an optional initial BB, and unescapes BD followed by a byte using XOR 20. It
requires the checksum byte to equal (sum of decoded content + 1) modulo 256,
then removes checksum and terminator. The original/raw candidates are retained
by `K` even if `J` rejects the checksum. No cross-notification buffering exists
in this layer, and duplicated candidate interpretations are not deduplicated.

`tools/m_reply.py:envelopes` models these rules. Fourteen synthetic input vectors
were generated by running the extracted Java `Hn.C/J/K` and `Dn` methods in an
isolated harness. They cover empty/short input, zero prefix, raw checksum
markers, BB framing, escaped BB/BD, missing delimiters and bad checksum.
The Python translation matches all vectors. A separate end-to-end test passes
raw, zero-prefixed and escaped acknowledgements through normalization and M
reply classification. All six reply/envelope tests pass.

These are synthetic parser checks, not captured firmware-transfer acceptance
or proof that each notification is a complete frame. A future live updater
must establish characteristic routing, fragmentation behavior and stale-message
boundaries before using these candidate interpretations to advance or retry.

## Preparation selection and M retry policy clarified

`Jh.f` selects E5000 generation zero, using `Ka.g` independently for each
component base name. `Ka.g` chooses the highest version among matching names
and generation values in the provided file list (`Ka.l` enumerates the local
FW directory). The preparation UI's 4.3.0 label does not itself constrain both
installed files to that version. Therefore the archived D 4.3.0 / M 4.2.1 pair
remains a candidate, not proven contents of the downloaded preparation archive.

`C0776xk.f1` has at most two local data attempts. Each attempt waits 400 ms,
consumes a fresh data sequence, constructs/sends the data block, then on ATT
success waits 15 ms and consumes a separate query sequence for `H0`. A failed
ATT data write proceeds to the second attempt. A successful `H0` returns the
data sequence. A failed `H0` is retried only when `R0(errorMessage)` matches;
otherwise it throws `C0743wk`, leaving handling to the surrounding window logic.
This is data retransmission, not merely polling an earlier packet again.

The normal JADX output incorrectly represents part of `R0` with empty branches.
A separate fallback instruction dump resolves its actual boolean expression:
contains `TRANSFER_START 83 error status=0x01`, OR contains both
`TRANSFER_START_83_ERROR` and `status=0x01`. The strings were independently
decoded from the local class. Timeouts and generic checksum failures do not
satisfy this predicate. `tools/m_reply.py:source_query_retryable` records this
source behavior for offline analysis, with positive and negative tests. It
must not be used as standalone authorization to replay a firmware block.

The enclosing window recovery path, stale checksum observations, sequence wrap
and disconnect recovery still need validation. There is no evidence here that
arbitrary failed writes are idempotent or that a browser may resume after power
loss. The live application continues to perform diagnostic reads only for
firmware; its US setter remains disabled after the observed AB/3A rejections.

## Capture coverage and remaining live evidence

Re-audited the supplied ATT export: 1,084 rows, SHA-256
`e70413207f78886e05278df0d24dce65279c852c12875c2acc98c0401afa06a4`.
For this capture's characteristic mapping, value handle 0025 (2AFA) has 60
write requests, maximum 10 bytes; handle 002F (2AFE) has 241, maximum 7 bytes.
There are no ATT prepare/execute-write operations in the export. None of these
writes contains the modeled 68/71-byte M or 71-byte D data payloads. The short
0088 setup writes are not evidence of a completed firmware transfer. This
capture cannot validate our firmware-data reply classification, checkpoint
correlation, retransmission or recovery behavior. This is bounded to the
supplied export, not a conclusion about what the bike supports.

The goal remains incomplete against the actual acceptance criteria:

| Requirement | Current evidence |
| --- | --- |
| HTTPS phone connection and session authentication | Repeated successful Pixel logs including .18 |
| Motor identification | Repeated electronic family code 22/00; descriptor all zero; .18 native D 4.5.0.0 and M 4.4.8.0 |
| Motor authentication | E2 FF FF observed repeatedly; does not establish region-write permission |
| US destination change | Two direct writes rejected AB/3A; later read remained EU |
| Preparation assets | D 4.3.0 / M 4.2.1 matches the freely published historical eTuning E5000 package byte for byte; current server response and bike installation remain unverified |
| Baseline restoration assets | Desktop 5.3.4 contains catalog-matched D 4.5.0 / M 4.4.8; D unwrapped with embedded digest/length verification; installation and recovery unverified |
| Firmware update/recovery | Source-derived offline models and synthetic tests; no real transfer trace or controlled update validation |
| Fresh US readback and power-cycle persistence | Not achieved |
| Assistance-speed behavior | Not measured; no claim made |

The .18 information batch has now supplied both native versions. Another direct
US write would repeat a known failure and would not fill the remaining gaps.
Source analysis can continue, but synthetic codec tests cannot substitute for
evidence from a supported firmware update/recovery path. No flash operation is ready.

## Build .18 live native baseline: 2026-09-09 10:46 UTC

The user's complete 18,045-character export contains independent selector
reads: D `00 01 84 00` returned prefix `00 01 86 45 00 00`, and M
`00 01 84 01` returned prefix `00 01 86 44 08 00`. Each arrived in 65 ms.
These decode to D 4.5.0.0 and M 4.4.8.0. The actual notifications were ten
bytes; the remaining four bytes were omitted by the logger and are unknown.
Both destination slots read EU (0); motor authentication again completed with
E2 FF FF. This session contains no destination setter or firmware transfer.

The sanitized fixture `tests/bike_baseline.json` retains only the observed
identity/version/region fields. A browser replay checks these exact six-byte
prefixes and retains the disabled US setter. It verifies application decoding,
not physical compatibility or update behavior.

Running `compare_components.py` against the private archived 4.0.2 images with
this baseline yields M 4.4.8.0 -> 4.2.1.0, then D 4.5.0.0 -> 4.3.0.0;
`installable` remains false. This is conditional on choosing that candidate
pair. `Jh.f`/`Ka.g` select files from the application's local FW inventory;
the preparation UI label alone still does not prove which M image accompanies
D 4.3.0. No conclusion that M must be downgraded follows from this comparison.

The local raw-file inventory contains the reference 4.1.0 pair and archived
D 4.3.0 / M 4.2.1 candidate, but no exact D 4.5.0 / M 4.4.8 restoration pair.
The remaining concrete preparation work is to establish the actual selected
package and obtain/validate restoration assets, followed by transfer,
finalization and recovery validation. Repeating this information batch is not
needed to resolve package contents. US readback, power-cycle persistence and
assistance-speed behavior remain unachieved.

## Exact-version restoration assets recovered from desktop 5.3.4

The next offline inventory pass found both measured baseline versions in the
archived Shimano desktop installer. Download source:
https://assets.bettershifting.com/archive/E-tube_Proj_V_5_3_4.zip
(linked by https://bettershifting.com/e-tube-project-archive/).
ZIP size 309,035,074; SHA-256
`004883e032a6f343e5c11d9b8b45b7f7c77e47ca5dd7259f488f913f6aaede4f`.
Static extraction: ZIP -> PE overlay ISSetupStream -> embedded
`E-TUBE PROJECT Professional V5.msi` -> Data1.cab. No installer was executed.

| Bundled file | Bytes | MD5 matching the saved reven firmware catalog | SHA-256 |
| --- | --- | --- | --- |
| due5000_d.4.5.0.dat | 138132 | 1e72967e756ad36f096a9ccf9fd43498 | 363a43fc6997d384e0d723fa241b034146365e7c48f1fc8cfda027a948c5a6a7 |
| due5000_m.4.4.8.dat | 119824 | 77ac236e16662211ed186bdf36b5cc63 | 9ea350e988345a9d9fb41c1363562ca190f1a8d5e1cc8a38c6373f69b877f033 |

Catalog reference: https://github.com/reven-project/etubeapi/blob/master/fw-scraped.yml.
Matching this catalog is corroboration, not publisher signature verification.
The files remain in the private analysis directory, not the public repository.

M passes the existing raw-header inspector as E5000/E50X0, M 4.4.8.0.
D does not have the raw header. A private reconstruction of the supplied
eTuning 3.0.7 `Ha.d` AES-CBC asset-unwrapping path produced 138,072 plaintext
bytes. Both embedded plaintext MD5 and declared length matched before saving
the result. Its header identifies E5000/E50X0, D 4.5.0.0; plaintext SHA-256:
`44806bd54aedff95a88bb73fafe0f0581297f2f67b2ea35545cea012899d90bb`.
This was a bounded one-file reconstruction, not a general-purpose validated
wrapper parser; the public raw inspector still rejects wrapped inputs.

`compare_components.py` with the unwrapped D, raw M and measured baseline
returns `equal` for both, normal order `[]`, and `installable: false`.
Thus the prior missing-restoration-files gap is resolved at the asset/version
level. The package does not establish the actual eTuning preparation pair,
whether M must be downgraded, or whether browser transfer, reset and recovery
will work. Those remain required before any firmware operation; US destination
and persistence have still not been achieved.

## Equal-version rewriting in the installer caller

Tracing the worker caller resolves a limitation of ordinary version comparison:
`f9c41` calls `this.g.u3(c0549qn, this, true)` (decompiled source line 1188).
`Th.u3` passes that boolean unchanged to `Th.v3`. In the instruction-level
`Th.v3` dump, labels L919-L939 construct separate M and D force flags when the
argument is true, the relevant native-read exceptional flag is false, and
the version comparison equals `Mh.f`. `Mh.l` returns `Mh.f` for equal versions.
Labels L939-L95b include those force flags in the component-selection booleans.
Thus equality does not, by itself, establish that this installer skips a
component. This is a caller/worker finding; it does not establish package
contents or every entry route into the activity.

The special alternative-pair search `Th.f3` immediately returns null unless
the family is `Ih.k` (EP800), its flag is enabled, and native information is
available. It is not evidence of an E5000 path that retains the current M.

`compare_components.py --force-equal` now models equal-version rewriting for
the case with valid independent native reads. With the recovered restoration
pair and the measured D/M baseline, both comparisons remain `equal`, but
the selected order becomes M then D. Without the flag the order remains empty.
Unknown or recovery-state versions still yield no modeled order, and both
modes retain `installable: false`. Four selection tests pass, covering mixed
equal/downgrade cases and unresolved reads under the force flag.

Consequently, neither the older candidate pair nor a mixed D 4.3.0 / M 4.4.8
pair establishes a D-only preparation procedure. Preserving M would be a
distinct workflow requiring evidence, not a faithful consequence of the
observed installer call. No additional live probe or repeated US setter
is needed to answer this source-level question.

## E5000 file-level D/M minimum-version checks

`Ka.i` explicitly recognizes DUE5000-D (the obfuscated name in its third D
branch decodes to that string). It reads current version at offset 16,
minimum peer version at offset 47, and a separate three-byte field at 44.
The E5000 M branch reads current version at offset 8 and minimum peer at 16.
`Th.j3` compares M current (`ia2.f`) against D minimum (`ia.g`), and D current
(`ia.f`) against M minimum (`ia2.g`), rejecting either shortfall. These are
the standard E5000 branches, not its separate NATIVE_SPEC early-return branch.
`Ja.a` parses the three-byte packed versions; `Ja.c` uses decimal weights
major*1000000 + minor*10000 + patch*100 + build. This differs from `Mh.l`'s
packed comparison and is preserved in the offline pair check.

Measured on the private, classified raw images:

| Image | Minimum peer version |
| --- | --- |
| D 4.3.0.0 | M 4.2.0.0 |
| M 4.2.1.0 | D 4.2.0.0 |
| D 4.5.0.0 (unwrapped restoration) | M 4.4.8.0 |
| M 4.4.8.0 (restoration) | D 4.4.6.0 |

Both complete archived pairs satisfy those two comparisons. Both mixed pairs
fail: D 4.3.0 with M 4.4.8 fails M's D minimum, while D 4.5.0 with M 4.2.1
fails D's M minimum. This rules out treating retention of the current M with
the candidate D as satisfying eTuning's file-level compatibility check.
It does not establish the actual downloaded preparation contents or prove
that either complete pair can be flashed safely on this bike.

`inspect_firmware.py` now reports `minimum_peer_version` for these known raw
layouts. `compare_components.py` reports both directional checks and suppresses
the modeled order on failure or an unrecognized minimum, even when forced.
Five component-selection tests and ten existing header/transfer tests pass.
Actual candidate/restoration and both mixed pairs were also checked offline.

This is a check of the intended final pair, not an assertion that a transient
state between M and D writes is bootable. The original worker's ordering,
reset suppression and recovery still require validation as a complete
operation. No live commands were added or firmware files published.

## Paired transfer reset and bootloader checks

Rechecked the worker chain against the instruction dump after discovering
the incompatible intermediate pairs:

- `Th.v3` invokes M `A0`; `C0776xk.A0` unwraps the file and calls
  `x0(..., false)`, suppressing that worker's final reset.
- If M returns false, the caller reports the failure and returns before the
  D-worker branch (dump immediately before L1849). That branch does not restore
  the original M image. This is bounded to the examined branch, not a claim
  that no other recovery screen exists.
- After M success, the caller performs the D handover path and invokes
  `C0041b7.g1`. That method passes reset=true through `x1` into `w1`.
- D `w1` obtains bootloader information with `j1`, checks the file against
  that information with `k1`, performs `A1` and `C1`, transfers data, sends
  finish, and finally calls `n1` when reset=true.

The D bootloader `j1` exchange is a separate protocol from the live application
version reads. Through its `K1`/`I1` wrappers it queries command/response pairs
2E/3A, 2F/3B, 30/3C, 29/35 and 2A/36 (hex). `k1` checks parsed image series
against the intended family and bootloader identity, and requires matching
unit fields. `A1` requires a six-byte field for its subsequent setup. These
operations have not been observed against this bike's bootloader; the existing
application-mode 22/00 reply does not validate them.

This means the final-pair minimum-version test must not be used as an
intermediate reboot test. Neither restarting between M and D nor treating
M failure as a completed rollback is justified. A browser implementation
needs a validated handover, bootloader identity/setup, and failure-recovery
path in addition to the existing offline block codecs. Those gaps remain;
no bootloader entry or firmware command was added to the live page.

## Public historical preparation package resolves the asset-source gap

The user has no paid eTuning access. Inspecting the embedded links in the
public https://etuning-app.com/downgrade.pdf revealed an unauthenticated E5000
download: https://etuning-app.com/wp-content/uploads/2024/11/5000_430.zip.
The guide is marked historical because preparation is now integrated into the
app. It identifies E5000/E5080 4.3.0 for downgrading from 4.4 or higher and
describes installing renamed files through an older E-TUBE mobile version.
This source supports an independently obtained historical asset pair; paid
access is not a prerequisite for acquiring it.

ZIP size: 146,098 bytes. SHA-256:
`4dee4d75ee83c22e951114cbf57332709c15be637ec2a8171bd82f9345adb137`.

| Public filename | Internal version | Bytes | SHA-256 |
| --- | --- | --- | --- |
| DUE5000-D.5.3.0.dat | 4.3.0.0 | 132072 | 3d3df4dfe3de333062f445b6719fa5033f93dc9d384448134ee6041d216c6af0 |
| DUE5000-M.5.2.1.dat | 4.2.1.0 | 116320 | 10190fd78e6527908c0e43405184c414b612bc4becce9ca5483612665ced6b56 |

Direct byte-array comparisons against the privately extracted desktop 4.0.2
files returned equal for both images. The higher filename versions differ
from the internal versions, as expected for the documented older updater
workflow. Our inspector correctly uses the header, not the filename.
The underlying payloads are unchanged; this finding supersedes the earlier
requirement for paid access to establish *a published preparation package*.
It does not prove what the modern app server currently supplies, but that
response is no longer the sole possible source for the independent project.

The public binaries remain outside the repository. No firmware was sent to
the bike. Next work is implementation and validation of the paired BLE update,
bootloader handover and recovery using this source-identified pair and the
matching restoration assets. The guide is supporting evidence, not a live
test of WebBLE on this Pixel/bike; US configuration remains unachieved.

## Build .19: local firmware pair checks in the single-file app

The page now accepts two local raw DAT files in a collapsed file-check section.
It identifies D/M and versions from headers, checks both peer minima with the
source's decimal version ranking, and requires exact SHA-256 matches to the
reviewed public preparation or extracted restoration images. File names and
selection order are ignored. Mixed pairs, duplicate components, modified bytes,
wrapped files and unsupported sizes are rejected. No binaries are committed.
The restoration D input must already be unwrapped; browser decryption is not
implemented. This is file validation, not a compatibility certification.

The checker retains no firmware bytes or permission token, and makes no BLE
calls. A later installer must validate its actual inputs again. UI results are
protected against a previous asynchronous selection overwriting a newer one.
Transfer and region controls remain unavailable. The next implementation gap
is the paired transfer state machine, bootloader handover and recovery.

Validation: Node tests exercise the exact page functions, including both mixed
pair failures and unknown-file rejection. Private integration checks use all
four actual images, reversed file order, duplicates and one-byte corruption.
A Chromium check covers page startup and invalid-file/cleared-picker feedback.

## Build .20: browser D/M packet encoders

Ported the separately Java-oracle-validated Python encoders into the single
HTML page. Both take an explicit sequence byte; neither allocates sequence
numbers nor sends BLE operations. D pads with FF, includes a padded block
checksum and little-endian block index. M pads with zero and includes the
1024-byte window checksum at checkpoints, including a zero-valued checksum.
The final image checksum excludes padding. Modeled address ranges are enforced,
not claimed as verified device flash capacities.

The local pair checker now reports block/checkpoint counts after file hashes
and headers pass. It retains no packets or firmware bytes. Packet generation
is available for the future scheduler but not connected to BLE writes.

`tests/firmware_packets.py` compares whole JS packet streams to the Python
codecs (whose byte layouts were checked against the decompiled Java), using
24 synthetic cases plus four optional private real images. All 28 matched,
including non-aligned image ends, window/bank transitions, maximum modeled
sizes, sequence wraparound and all-zero checksum windows. This validates
encoding parity, not successful transfer on SC-E7000. Local file-check tests
and the Chromium picker test also pass. Next: correlated reply handling and
worker state transitions, followed by paired handover/recovery validation.

## Build .21: M reply interpretation and attempt evidence

Ported Hn.K/C/J envelope candidates and C0644tk/C0776xk reply classification
into the app. Candidate framing is retained explicitly: raw and leading-zero
interpretations are not checksum-validated. Only the escaped interpretation
checks its checksum. The source protocol mask is preserved. The reply window
uses distinct query and data sequences: 83 correlates to the query; C0 to the
data; 91/92 are statuses, never acknowledgements. The whole notification is
processed before reporting accumulated evidence, and a positive query failure
or checksum rejection dominates success evidence. Closed windows ignore late
notifications. A caller can close on timeout/disconnect/write failure.

This accumulator has no timers, writes, retry authority or sequence allocator.
It reports `evidence-complete`, not update success. Checkpoint F2 00 31/32
remains explicitly uncorrelated and must be scoped by a future transport;
sequence wrap and delayed checkpoint freshness are not solved by classification.
Neither raw candidate parsing nor a checkpoint marker alone authorizes progress.
The region and firmware controls remain disabled as before.

Re-read C0776xk.F0: listener registration precedes the 0B query containing
[query sequence, 03, data sequence]; the source waits up to 3000ms after a
successful query write, with matching query errors taking precedence. The
browser accumulator is only the evidence part of that worker, not its timing
or recovery implementation.

Tests: all 14 Java-generated envelope vectors match. Additional cases cover
raw/escaped acknowledgements, both ACK/checkpoint orders, status-only traffic,
wrong sequence, checksum failure with ACK in the same notification, failure
remaining sticky, timeout/close behavior, and stale ACK from another attempt.
Packet-codec, file-check and Chromium startup/picker regression checks pass.

## Build .22: timed M query exchange

Added an unwired `queryMFirmwareBlock` for the source F0 query phase. It accepts
an exclusive transport's write/subscribe functions and an abort signal; it
registers before sending 0B [query-sequence, 03, data-sequence]. Immediate RX is
buffered by the reply accumulator until ATT succeeds. ATT failure overrides
that buffered evidence. The source's three-second reply deadline starts after
ATT completion. An additional application eight-second bound handles an ATT
promise that never settles; it requires reconnect, never automatic retry.

All paths remove listeners and timers, including synchronous write errors,
abort, query rejection, checksum failure and timeout. A late ATT completion
cannot restart a closed attempt. The function sends only the query when called;
no application control calls it, and no data writes or bootloader entry were
added. Success reports reply evidence, including the unresolved checksum
correlation flag, not permission to advance a flash.

Fake-clock tests cover immediate notification, notification followed by ATT
failure, slow ATT followed by a full three-second reply window, stalled ATT,
late completion, ACK/checkpoint ordering, checksum rejection, buffered query
error precedence, wrong sequences/status traffic, abort and synchronous failure.
Existing envelope, file-check and Chromium startup tests pass. Next work is
the M data/retry worker and D protocol handling, then paired handover/recovery.

## Build .23: M normal data attempt plus bounded protocol retry

Re-reading j1's caller corrected an important scope issue: f1's two attempts
are retries after j1's initial attempt, not a two-attempt total. j1 invokes f1
only when R0 accepts the failed query diagnostic. Debug source j1 around
13520-13560 shows the initial k0 write, 15ms sleep, fresh query sequence, H0,
R0 filter and f1 call. f1 around 8800-8840 bounds retry counters 1..2;
9085 delays 400ms before allocating a fresh data sequence; 10695 allocates
another query sequence after 15ms; 11342 applies R0 before another retry.

Added an unwired browser M block worker: snapshot image bytes before awaits,
initial data write/query, then at most two delayed rewrites on query status 01.
The transport and sequence allocator must be exclusive for the paired update.
The worker does not allocate bootloader state, stream an image, reset a unit,
or authorize installation. It returns accumulated reply evidence only.

Intentional boundary: source f1 may continue after its k0 reports failure;
we do not equate an arbitrary WebBLE rejection with a definitely unprocessed
write. Browser data-write rejection, abort, eight-second stalled ATT bound,
and reply timeout stop this worker without a rewrite. Recovery or repeat
permission after an uncertain ATT result remains unimplemented. No UI calls
this worker, and the app's live region/firmware gates are unchanged.

Fake-clock tests verify all three attempts, exact 15/400ms timing, fresh
sequence allocation through FF->00, unchanged retry bytes after caller
mutation, retry exhaustion, query status 02, missing reply, rejected/hung
ATT and abort before a retry. All passed, alongside query/envelope/file
checks and Chromium startup. Next implementation gaps: D response/transfer,
M image/window recovery, paired bootloader handover and final verification.

## Build .24: D reply semantics checked against original Java listener

The D m1 query cannot reuse M's success condition. It registers Y6, sends
0B [query sequence, 03, data sequence], and waits for both C0 acknowledgement
and a block result. Its reply deadline is 25 seconds for block indexes 0..2,
then 3 seconds, starting after ATT completion. E5000 sets d=true in w1
(ih != Ih.k, the EP800 branch), selecting Y6's first result-handling branch.

Ported that branch's evidence accumulator. C0 requires protocol mask 0B and
matching data sequence. Results require protocol mask 88: 31 needs at least
three payload bytes, with a one-based little-endian block index; 32 accepts
shorter payloads. A zero or absent index is accepted by the source as
uncorrelated. Other indexed blocks are ignored, with 32 counted separately.
Once 31 has arrived, a later matching 32 increments a counter without
replacing success. A 31 can replace an earlier 32. This differs from the M
error precedence rule and is preserved explicitly, not generalized away.

`tests/d_reply_vectors.json` contains 72 synthetic normalized-packet cases.
Expected results were generated by the unmodified decompiled Y6 listener
executed with private minimal Java dependencies. Hn was stubbed to provide a
single normalized candidate; framing itself is covered by the prior separate
Hn Java vectors. Cases span early blocks, the deadline boundary, bank boundary,
last modeled block, both arrival orders, wrong sequences/indexes, missing
index, short result and late errors. All browser results match the Java oracle.
Vendor code and binaries remain private. Existing M worker/query/envelope,
file-check and Chromium startup tests also pass.

This code records source evidence; no updater calls it. The source's accepted
uncorrelated result is not proof of freshness or hardware compatibility. Next
work is the D timed query/data worker with address/bank setup, then image-level
handover and recovery. The live app still cannot flash firmware or change US
region; the bike's last observed destination remains EU.

## Build .25: D timed query and address/bank setup plan

D now uses the tested common query lifecycle with its own Y6 evidence window
and m1 reply deadline (25 seconds for block indexes 0..2, 3 seconds thereafter).
Both M and D register before writing and wait for successful ATT completion
before accepting immediate buffered RX; timers/listeners are removed on all
terminal paths. D still needs both data-sequence C0 and a qualifying 31 result.
No D retries or data writes have been wired.

Re-read C1/f1/z1/K1/X1 and the E5000 Ih.n protocol assignment (family 34,
Hh.a). The declarative initial plan is protocol 88 with four-byte payloads:
21 00 page 00 (page=floor((length-1)/2048), 40s), 0A 00 00 00
(bank zero, 1.2s), then 24 00 40 00 (24-bit little-endian address 4000,
1.2s). u1's later bank transition reverses the latter two operations: address
then bank. Bank changes occur at indexes 1024 and 2048, to addresses 14000
and 24000. Reposition commands are recorded without retry authority.
The source y1 callers permit five retries for address/bank and zero for start;
that command worker/retry policy and 88 transport mapping are not implemented.

Added fake-clock D query tests for both RX orders, immediate buffered reply,
slow ATT with full subsequent 25s/3s window, wrong block, rejection, stalled
ATT and abort. Address-plan tests verify initialization ordering, both bank
crossings, no spurious crossing, last modeled address and bounds. They pass
alongside 72 Java D reply vectors, M query/worker regression tests, file checks
and Chromium startup. The app remains unable to flash or change region.

## Protocol 88 transport and command-filter correction from raw instructions

Hn.i0 uses C0483on.U and Hn.I, which prepends exactly one protocol byte.
Decoded C0483on's UUID assignment for U is
00002afa-5348-494d-414e-4f5f424c4500. Therefore the observed source path for
protocol 88 is 2AFA [88, four-byte command], not an application query on 2AFE.
X1 pads command payloads shorter than four bytes; these setup commands already
have four bytes. No actual bootloader write was performed.

An important decompiler discrepancy appeared while examining X6/F1/Hn.E.
Readable JADX F1 inverted the raw-payload condition for E5000. Recompiling
that text initially accepted indexed 31/32 payloads and rejected 31 00 00.
This was NOT faithful to the APK's raw instructions. Generated a fresh
fallback decompilation of C0041b7 and checked F1 labels L10..L66: a raw
31/32 result requires length >=3 and bytes 1 and 2 both zero. The prefixed
88 and leading-zero/88 forms likewise require their two result bytes zero.
L67 records a rejected general result; L66 returns true. Do not treat a
recompiled readable decompilation as an independent ground-truth oracle
without checking suspicious conditions against raw instructions.

The offline command matcher now follows that raw-instruction predicate and
Hn.E's candidate order: raw; optional leading-zero removal; each Hn.K
payload, optionally zero-stripped payload, protocol+payload; then Hn.J
payload/full-frame candidates. It accepts the first qualified candidate.
The 108 synthetic fixtures were regenerated using copied Hn methods and the
F1 predicate normalized from those raw instructions. They cover raw/prefixed,
escaped, short and indexed cases. Python matches all fixtures, and explicit
regressions reject 88 31 01 00 and 88 32 01 00. These fixtures are source-model
checks, not captured bootloader traffic. No vendor code is committed.

A zero-index result still has no transaction identifier. Exclusive command
windows, delayed same-shape replies, retry handling and long-write behavior
remain integration concerns. This evidence removes the suspected indexed-
block aliasing problem and establishes the command filter needed next.
App build remains .25; no extra bike test or deploy is required for this
offline source correction. The next change can implement the protocol-88
command exchange using the corrected predicate and the tested query lifecycle.

## Build .26: protocol-88 setup command exchange

Ported the corrected F1 predicate and Hn.E candidate ordering to the app,
sharing the Hn.J decoder with the existing envelope parser. Browser matching
agrees with all 108 offline raw-instruction-corrected fixtures. Indexed block
results are rejected as setup-command replies.

The unwired `sendDFirmwareCommand` accepts only the reviewed four-byte start,
bank and address commands, with modeled page/bank/alignment bounds. It sends
2AFA-style bytes [88, command payload] through a caller-supplied transport,
registering its listener first. The reply deadline begins after ATT succeeds:
40 seconds for start, 1.2 seconds for bank/address. As with data queries,
an eight-second application ATT bound prevents an unresolved write from
hanging indefinitely. It is not a source retry signal.

A received 31 00 00 is first-match success evidence; 32 00 00 rejects. Neither
contains a command identifier, and the returned evidence explicitly reports
commandCorrelated=false and installable=false. Automatic command retries are
not enabled; the source's retry behavior is not sufficient to establish
freshness after an uncertain WebBLE operation. The page UI never calls this
exchange and does not enter the bootloader or send firmware.

Tests cover the 108 matcher cases, command bounds, immediate buffered RX,
ATT failure after RX, both reply deadlines starting after a slow ATT, rejection,
ignored indexed results, stalled ATT, late completion, abort and no retries.
M/D query, M worker, envelope, file-check and Chromium startup regressions pass.
Next: D setup/data orchestration, then paired M/D handover and recovery.

## Full-image data phases and remaining M setup

Builds .27/.28 join D setup/bank/data/query operations and M data/query
operations respectively. Full-image tests use deterministic synthetic bytes,
including the reviewed image lengths, not a live bootloader or firmware update.
M owns one snapshot for all blocks and retries. Its sequence allocator remains
caller-supplied; this is not a claim of identical diagnostic-only sequence
consumption in the APK. Both workers return data-phase completion only.
Neither finishes, resets, enters a bootloader nor recovers from disconnect.

Re-reading C0776xk.x0 lines 4291-4330 shows START (33 decimal), then B0,
WRITE_ADDRESS_SET (36), CLEAR_CHECKSUM (38), 150 ms, E0 data, FINISH (39)
with the original image checksum and conditional RESET (40). B0 constructs
[00,04,mode], choosing mode 1 when the EP flag or its supplied boolean is
true, otherwise mode 2. It uses a separate exchange from C0, so implementing
only start/address/checksum commands would omit setup. C0 constructs
[00,F0,00,command,arg0,arg1,arg2] and sends through Hn.g0 using its
constructor-supplied transport selector. The selector, B0 input boolean and
reply predicates still need validation before that setup is wired.

## M command transport and arguments resolved

C0776xk.C0 constructs [00,F0,00,command,arg0,arg1,arg2]. Hn.g0 relays
through i0(13 hex) on C0483on.U only when the leading 00 equals the
constructor selector; otherwise it sends the original packet through W.
Executing C0483on's private UUID decoder confirmed W is 2AFE; U was
previously confirmed as 2AFA. A private Java source oracle executed the
original f()/d() argument decoders: START arguments are [00,0E,00],
CLEAR_CHECKSUM [00,00,00]. J0 addresses are three-byte little-endian.

C0 deadlines: START 6000 ms, address 10000 ms (constructor d), clear 2000 ms
(constructor e), finish 21000 ms. Wi(7) delegates to e1, which returns the
status following the first F2/00 marker. A first unknown status is not skipped
in favor of a later success marker. Status 31 completes, 32 rejects; X0
extracts the optional following error byte. These markers have no command ID.

The browser command exchange is bounded and does not automatically perform
the APK's five attempts: uncorrelated late replies and uncertain browser writes
are not sufficient grounds for replay. It requires an explicit target selector
and an adapter accepting characteristic plus packet. No current UI caller uses
it. B0 remains to be integrated: its boolean comes from y0's C0677uk version
comparison (strictly greater than packed 2.0.2.0), not the application-mode
native M firmware version. B0 uses i0(0B) and Wi(6), which tests reply bytes
1/2 for 84/00. Bootloader version/identity and handover remain unverified live.
