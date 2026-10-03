# Shimano US-region workflow investigation

For the current takeover summary and asset policy, start with [HANDOFF.md](HANDOFF.md)
and [ASSETS.md](ASSETS.md). This document is a chronological notebook; older
plans and interpretations below are retained as history, not current advice.

Current status (2026-09-24, local build .82): SC-E7000 display; motor reports
E50X0, native D 4.5.0.0 / M 4.4.8.0, and last verified destination EU. The
display firmware exposes local command `00 0C <mode>` for modes 4 and 5, which
makes the SC-E7000 itself establish and own that protected motor mode using its
built-in secure-word table.
This avoids the ownership collision that defeated phone-originated mode
requests in builds .76/.77. Local build .82 selects display-owned mode 5 because
Shimano's desktop inspection panel exposes its destination controls in that
protected mode. It sends one unchanged A0, then freshly establishes
display-owned mode 5 again before at most one US A8, with exact reply gates and
a local mode exit. It has synthetic coverage but no bike result.
The public Pages site still serves build .77. US readback, persistence, and
assistance speed remain unverified.
The dated entries below retain earlier hypotheses and superseded limitations.


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

## Analysis artifacts and privacy

The selected protocol analysis outputs and source-artifact hashes needed for
this handoff are committed under [`docs/evidence/`](docs/evidence/). Retrieval
sources, exact hashes, and excluded large/private artifacts are listed in
[`ASSETS.md`](ASSETS.md). This repository does not require the former private
analysis folder. No raw capture, user passkey, device address, or captured
authentication ciphertext is committed.

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
`Gh.k` contribute the other conditions. A standalone Java harness executing
the extracted methods confirmed: DUE50X0/430 -> direct gate true;
DUE50X0/450 -> false. Its historical result is recorded here; the harness is
not a current handoff dependency.

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
  71-byte logical message, distinct from the short 2AFE motor command transport.
  Hn.t0 then splits it into four ATT writes of at most 20 bytes (see outgoing
  GATT transport correction below). Live firmware transfer remains untested.
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
and 71-byte logical messages, fragmented by Hn.t0 before ATT writes. The final checksum is the original image byte sum
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
writes establishes a firmware data transfer. The modeled 68/71-byte messages
are logical messages, not individual ATT writes; absence of long ATT writes
alone is not evidence that firmware transfer is absent. The short
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

## M bootloader query, mode and session integration

The private Java oracle executed C0776xk.b(): the bootloader-version request
is [00,F0,00,41,00,00,00], sent by y0 via Hn.g0 with a 6000-ms timeout.
Wi(5)/d1 look for F2 at an offset and status at offset+2; unlike C0/e1,
they do not require the intervening byte to be zero. y0 rejects an observed
32 marker before parsing 51. Its next byte contains major/minor nibbles,
followed by patch and build. A short 51 result is an error, not version zero.

C0677uk.a selects the newer mode only above 2.0.2.0, strictly. E5000 B0
sends outer 0B with [00,04,01] above that boundary and [00,04,02] otherwise.
Wi(6) tests bytes 1/2 for 84/00; its timeout is 2000 ms. The app now models
these predicates and joins version/start/mode/address/clear, 150-ms delay,
data and finish without reset. Synthetic integration tests cover both sides
of the threshold and failing ATT at each of the ten writes for a 65-byte
image. Existing full-image tests separately cover image geometry/checkpoints.

This operation requires prior bootloader entry and target-slot selection.
Source G0 calls Hn.s0(0) before y0; it is not implicitly performed by the
new operation. The target selector still has to come from verified routing.
Neither the version predicate nor a finish acknowledgement proves compatibility
or persistence on this bike. Live update and recovery remain unvalidated.

## D finish and reset semantics

Rechecked C0041b7.h1 (lines 2822-2870): FINISH uses K1(39 decimal,
original image checksum, 0), y1 timeout 3000 ms, then Thread.sleep(1000).
The browser joins this to the full D data phase and reports D-transfer-finished
only after the accepted finish and delay. An abort during the delay fails the
operation, and no reset follows automatically. Existing setup reply matching
is reused for finish; its uncorrelated response limitation still applies.

C0041b7.n1 uses k0(88 hex, X1(K1(40 decimal,0,0))). It only inspects
the write outcome, without waiting for a protocol result. The separate browser
reset primitive therefore reports reset-write-completed, with rebootVerified
and firmwareVerified both false. It has no automatic caller. The paired
coordinator must first prove both transfers finished, then verify reconnect
and component versions; ATT completion alone cannot satisfy those checks.

The D operation still assumes prior j1/k1 identity checks and A1 setup.
Synthetic integration tests validate setup/data/finish order, original-byte
checksum despite FF padding, the one-second delay, failures at each write,
finish rejection, abort and separate reset semantics. They do not establish
that firmware preparation, recovery or US destination works on the bike.

## D bootloader identity exchange and field validation

C0041b7.j1 issues commands 2E,2F,30,29,2A (hex), expecting 3A,3B,3C,35,36.
I1 sends protocol 88 with four-byte command and a 3000-ms timeout. j1
does not decode the first two version replies; they are retained as opaque
responses in the browser. The unit response requires at least three bytes
(opcode/family/unit); J1 requires four bytes per serial half and assembles
bytes 1-3 from each into a six-byte field for A1. No serial is logged.

For E5000 Ih.n, Ih.M accepts family 34 (22 hex) only. k1 compares embedded
image family against the intended family, image unit against bootloader unit,
and bootloader family against Ih.M. The browser's raw-header checker already
limits the reviewed D layout to family34/unit0; checkDBootloaderImage now
requires matching identity fields and a six-byte serial. This check alone
does not authorize flashing or validate bootloader entry/recovery.

Z6/I1 search for an expected opcode anywhere in the supplied response. The
browser intentionally tightens this to a response prefix: raw, optional
leading zero, or a recognized protocol-88 envelope. It never scans serial
or unrelated payload bytes for a matching opcode. This is a deliberate
bounded parsing policy, not exact reproduction of the loose source matcher;
live bootloader framing still needs validation before use. Synthetic tests
cover packet ordering, matching/nonmatching prefixes, truncated identity/serial
fields, ATT failure stops, and compatible/incompatible image fields.

## D serial setup and component workflow

C0041b7.A1 first sends K1(06,family,unit), then K1(07,serial0,serial1),
K1(08,serial2,serial3), K1(09,serial4,serial5). Each K1 yields four bytes
with a zero final byte. A1 uses H1, which sends protocol88 via i0, waits
3000 ms with X6/F1, then checks R1 for31 success/32 rejection. H1 does
not contain a retry loop. X6's branches both delegate to F1, so the existing
raw-instruction-corrected matcher applies to these commands as well.

Ih.L rechecked for E5000: family34 and unit0 are required. The joined
browser component operation validates/snapshots the D image, reads the
bootloader identity, checks those fields, performs all four acknowledged
setup commands, and invokes the reviewed setup/data/finish path. It returns
no serial in its summary and never resets. Tests use a synthetic D header
and cover mismatch stops before setup, short/invalid files before any writes,
source command ordering, input mutation and failure at every one of the
21 writes in a 256-byte scenario. Command tests cover the four new bounds
and 3000-ms deadlines. No live setup or transfer has occurred. Bootloader
entry, paired asset authorization/validation, handover and recovery remain
preconditions for an eventual user-facing updater.

## Outgoing GATT transport correction — build .34

The prior encoders and component tests operate on logical Hn.I messages.
They did not include the Hn.i0 -> d0(z2=true) -> t0 transport step. This
corrects the earlier description of 68/71-byte blocks as BLE writes.
For the normal i0 path, t0 prepends 00 to logical messages of at most 18 bytes.
For longer messages it repeats the protocol byte after a fragment header and
carries at most 18 message bytes per fragment. Nonfinal headers are
(index * 32 - 128) modulo 256; the final header is index * 32.
A 71-byte message therefore produces ATT values of lengths 20/20/20/18,
with headers 80/A0/C0/60. A 68-byte message ends with a 15-byte fragment.
C0 chooses Android write type 1 (without response) for every long-message
fragment; short messages use type 2 (with response). Short direct 2AFE
messages take D0 and are unchanged. Long 2AFE framing is outside this adapter.

Ten synthetic fixtures execute the original Java t0 for logical lengths
1, 2, 5, 18, 19, 20, 37, 55, 68 and 71. The browser fragmenter matches every
byte and write mode. The known live display query also provides a short-frame
cross-check: logical 13 01 1C 00 becomes ATT 00 13 01 1C 00.
No vendor source or firmware data is included in those fixtures.

createFirmwareGattWriter snapshots all fragments before writing, serializes
one logical message at a time and stops permanently after failure or abort.
Its seven-second total deadline precedes the component workers' eight-second
write deadline. Native GATT promises cannot be cancelled, but their late
completion cannot send remaining fragments. Tests cover failure at every
fragment, timeout, abort, close, concurrency rejection and input mutation.
There is no retry after uncertain delivery. This adapter remains unwired;
future component orchestration must use it, not pass logical messages directly
to a characteristic. Bootloader entry, paired handover, recovery and actual
firmware traffic validation remain unfinished. No bike test is requested.

## Update-mode entry and M slot selection — build .35

Th.k3/p3's ordinary non-EP path is now modeled as an unwired operation.
k3 reads bridge command04 and requires bit80 in Hn.Z/M's status. p3 preserves
bit20, requests command03 with that bit as its argument, waits1000ms and
reads04 again. Cn requires bit80, bit40 cleared, and bit20 unchanged. The
low five status bits become the target selector; they must not be inferred
from the motor model. Bridge replies use Hn.H's raw/leading-zero prefix
layouts; Hn.Z also permits a raw status byte with bit80 set.

Hn.p0 then sends logical 00 32 20 01 through n0. Selector0 routes it through
2AFA as logical 13 32 20 01; other selectors use direct2AFE. Hn.R/p0 requires
32 22 followed by value01. A 32 23 reply rejects the request; a success opcode
without value01 is also failure. Supported prefix layouts are raw32,
48/32, 48/one-byte/32 and 00/48/one-byte/32. No arbitrary payload scan is
used. Successful p3 waits2000ms before returning. The browser result is
update-entry-acknowledged, not bootloader identity verified. The source's
special recovery and EP branches are outside this implementation.

C0776xk.G0 separately calls Hn.s0(0) before the M bootloader-version query.
That is logical2AFA 06 00. Wi12 accepts Hn.H(26) only if its next byte is
absent or zero. selectMFirmwareSlot models this separately; transferMFirmware
still requires it as a precondition. The entry helper deliberately performs
one attempt per command, rather than the source's multiple retries after
uncorrelated replies. Missing replies stop after3s (PCA request6s).

Integration tests drive these operations through createFirmwareGattWriter
and check physical ATT values, routes for selectors0/13/31, mode0/20,
source delays, PCA success-value validation, slot rejection, timeout and
native failure at every write, plus cancellation. Synthetic tests establish
implementation behavior, not permission to flash or successful boot entry
on this bike. No entry operation is connected to a UI control.

The Th.v3 instruction dump at L1bb7 calls e3, disposes Sh resources, then
calls p3 again before constructing the D worker. This is evidence that M
completion alone does not establish the D entry state. e3 branches through
Sh.f (e && !d); its applicability and transport cleanup still need tracing
before assembling paired handover. No automatic M reset or mixed-pair boot
is assumed.

## D entry prerequisite and ordinary handover — build .36

Rechecking C0041b7.g1 -> x1 -> w1 uncovered an additional entry layer before
j1's identity reads. A newly constructed worker has b=false. For E5000,
d2 is false (it only selects an EP/N9 path), so w1 calls t1(true,mode,selector)
and o1 before reading identity. t1 calls Hn.r0(40,mode,selector): set03,
wait1000ms, read04 with ready/40/mode bits checked. With mode0 the selector
occupies the low five request bits; with mode20 it is omitted.

The ordinary o1 sequence is now modeled by enterDBootloader:
- Select target31 using06, accepting Wi12's26 status rule.
- Send FIRMUP stage1 four times using i1's write-only path, waiting1000ms
  after each. These four sends are the source's fixed priming sequence.
- Select target0, then send stages1..4 through B1, requiring each stage ACK.
- Send stage5 through i1's write-only path, wait150ms for E5000/Hh.a.
- c2 sets mode60 through r0(40,20,0), including the1000ms delay and04 check.
- Select target31 and send acknowledged stage5 through B1.

l1 supplies four inner bytes: one-based stage and three credential bytes.
i1/B1 prepend protocol88 through Hn, then the GATT adapter adds framing.
The five private credential rows must be supplied as a15-byte Uint8Array;
no vendor credential constants are embedded in the repository or logs. The
helper snapshots them before writing and clears its private key copy on exit.
JavaScript does not guarantee erasure of all engine-created copies.

AbstractC0567r9.g/f and C0665u8 case11 identify ACK11 and NAK12 after an
optional00 and optional88 prefix. ACK must contain the expected stage byte;
a missing/wrong stage is not success. The browser stops on any rejection,
uncertain write, timeout or abort, without source B1/o1 retries. Stage reply
deadlines are2000ms; bridge exchanges3000ms. Source retry/recovery behavior
has not been established as safe on this bike.

Tests cover the complete17-write physical ATT sequence for both modes and
selectors0/13/31,6150ms of source delays, credential snapshot, all17 native
failure and abort positions, each acknowledged-stage timeout, and reply
prefix/stage validation. No real credentials are in fixtures. Successful
simulation yields D-entry-acknowledged with bootloaderVerified=false; identity
queries still must validate the actual bootloader before data transfer.

Th.p3's ordinary E5000 result constructs Sh with d=false/e=false and no N9/C9
resources; only its EP branch replaces it through Sh.g. For that ordinary
result, e3's sole sh.f() block is skipped because f=e&&!d. Sh.d also has no
resources to dispose. Thus the ordinary M->D path's material transition is
another p3 negotiation followed by the D t1/o1 sequence above. This conclusion
is scoped to the ordinary p3 path, not special recovery/W2/EP branches.
The paired coordinator must select that path explicitly and cannot treat
M completion or motor authentication as D bootloader entry. No entry or
firmware transfer is exposed in the UI yet.

## Paired coordinator — build .37

transferFirmwarePair now joins the ordinary path: validate both files,
M update negotiation, M slot0, M version/setup/data/finish, fresh D update
negotiation, D FIRMUP entry, and D identity/setup/data/finish. It suppresses
reset and never calls the US setter. The fresh D selector is used instead of
reusing the M selector. Th.p3's ordinary non-EP path is the only modeled path.

loadFirmwarePair is shared by the picker and coordinator. It snapshots each
actual file buffer before hashing, checks the reviewed SHA-256 allowlist,
requires one D and one M from the same source pair, validates raw headers and
peer minima, and bounds component geometry. Both files pass before any entry
write. Picker results cannot authorize a transfer or substitute for these
checks. Actual preparation and restoration pairs both pass the shared loader;
synthetic images are rejected by the deployed allowlist.

The coordinator requires an externally supplied fresh E5000 family34/unit0
baseline with either reviewed pair of native component versions, private stage
credentials, and the required GATT write methods. These checks do not prove
freshness by themselves: a future UI must obtain the baseline from the active
authenticated bike session. No UI caller is enabled. The coordinator takes an
exclusive per-characteristic lease before asynchronous file loading; another
coordinator cannot interleave on that transport. Its writer closes on either
success or failure. Private credentials are snapshotted and its key copy is
cleared in finally; no complete JavaScript memory-erasure guarantee is made.

Progress exposes stage names only. Errors expose the failed stage and whether
M or D has finished, not arbitrary native error text or packet contents.
There is no automatic retry, reset, resume or rollback. A completed transfer
returns firmwareVerified=false, regionVerified=false and recoveryVerified=false.
Native version and region checks after a separately justified reset are still
required. No claim is made about an interrupted pair being bootable.

Orchestration tests use controlled component workers to verify ordering,
new-selector handover, immutable inputs, validation before writes, concurrency
rejection, cancellation before entry and partial-completion reporting at every
phase. They do not simulate the entire wire exchange: entry, component and
GATT suites test those layers separately. An integrated physical-protocol
simulation and live recovery/entry evidence remain necessary before enabling
an updater. The real private assets pass the shared loader without changing
the public allowlist or adding firmware binaries to git.

## Full paired wire simulation — build .38

The new firmware_pair_wire.cjs runs the real coordinator, all entry and transfer
workers, reply matchers, and GATT adapter together. Only the device, clock and
synthetic-image trust entries are substituted. The simulated device validates
physical write modes/lengths and reassembles fragments, checks image bytes,
M zero padding/checkpoints, D FF padding/checksum/block indices, and finish
checksums, and emits the modeled reply shapes. It never accepts a reset.
Synthetic images are trusted only in the test VM; deployed hashes are unchanged.

The256-byte pair uses85 physical ATT writes. Tests inject failure before
processing and after processing at every one of those writes, and cancellation
at every write. Every acknowledged workflow phase is also tested with dropped
replies. Wrong D identity after M completion stops before D data. Larger cases
cover a D bank boundary and M checkpoint/final partial window, plus synthetic
images matching both actual pair lengths (132072/116320 and138072/119824).
All complete the coordinator with correct block counts and finish checksums.
The fake clock drains native Promise microtasks before advancing deadlines;
advancing after a fixed microtask count incorrectly timed out long synchronous
simulation chains and was corrected in the harness.

A material reporting ambiguity was exposed by failure-after-processing tests:
the simulated device can accept M or D finish and emit its reply, while the
native write promise subsequently fails. In that case the worker correctly
rejects, but mFinished/dFinished=false does not establish unchanged firmware.
Coordinator errors now include deviceStateUnknown=true after file validation;
the finish flags mean confirmed worker completion only. Tests explicitly
exercise accepted-but-unconfirmed finishes for both components. No reset,
rollback, success claim or continued write follows those failures.

This integration evidence catches software-layer mismatches but is not a
capture of real firmware traffic. The simulated reply model comes from the
source analysis and still requires live validation. Native component/region
verification after restart, recovery after interrupted paired changes and
controlled entry on this bike remain incomplete. No firmware control is enabled.

## Reconnected application readback — build .39

readFirmwareBaseline uses five existing application reads after a fresh session
has completed authentication and information-transport setup: model001C,
serial003C, native0084 IC0, native0084 IC1, and destination16AC slot1. It
checks family34/unit0, valid six-byte serial, supported native version fields,
and destination range. No configuration, authentication or firmware command is
sent by this reader. Each read has a3s reply deadline and stops on incomplete
or failed delivery; the remaining reads are not sent after a timeout. Native
D/M replies still lack IC echo, so attribution relies on the ordered response
window and does not establish correlation against arbitrary delayed duplicates.

Motor identity is SHA-256(private16-byte salt || six-byte serial). The same
salt must be used for before/after comparison; it is not a passkey or an
application-authentication credential. Raw serials and the fingerprint are
not included in the public verification summary. The reader's internal serial
and salt copies are cleared in finally, with the usual JS-copy limitation.

verifyFirmwareAfterReconnect snapshots the expected fingerprint, reviewed
native pair and EU/US destination, requires distinct previous/current session
tokens, and compares a fresh readback. Tokens must come from actual connection
lifecycle objects; caller-supplied token inequality alone cannot prove a BLE
reconnect. The helper remains unwired. A different motor suppresses both
firmware and region match flags even if it reports the expected values.
Version/region mismatches are explicit results; malformed/failed reads throw.
No reset, region write, repair, rollback or retry follows a mismatch.

Tests drive the reader through the actual GATT adapter, checking all five
physical read requests, identity mismatch, D/M/region mismatch, unchanged
expectation despite caller mutation, same-session rejection, and ATT failure,
truncation and timeout at each read. A native read timeout stops before the
next IC read. Matching readback is not a power-cycle test: both
powerCycleVerified and persistenceVerified remain false. The eventual UX
must acquire fresh sessions and separately establish restart/persistence.
This implements comparison logic without claiming a live installation result.


### Build .40: bounded live entry/exit probe

The next live boundary is bootloader entry and exit without any image transfer.
The probe composes the existing source-derived ordinary E5000 update entry,
M slot selection/version read, fresh D entry, FIRMUP exchange and loader identity
reads. It requests the existing n1 RESET only after loader family 34/unit 0.
This use of reset without an image transfer is an experiment, not previously
observed live behavior. Failure does not trigger speculative cleanup packets.

Before entry, five fresh reads require the original native D4.5.0.0/M4.4.8.0,
EU0 and family34/unit0 and save a salted application-serial fingerprint. A
strict logical-packet allowlist excludes all protocol0B commands, D erase,
start, address, finish, serial programming, and destination writes. Loader
serial representation is not assumed equivalent to application serial; the
post-reconnect check compares application serial fingerprints only.

Simulation covers 38 physical writes, failure before/after each native write,
abort at each write, missing replies at each phase, wrong identity/baseline,
reset gating, and forbidden commands. Browser tests cover profile validation
and pending verification across reload. Existing paired-wire and readback
regressions also pass. These results establish software behavior, not live
bootloader entry, reset, recovery, firmware compatibility, or US persistence.


### Build .41: embedded profile and guided UI

At the user's request, the fixed 15-byte source-derived profile is embedded in
the page. No phone file download or input remains. This changes distribution
of those constants, not the bike passkey/serial logging rules. A guided click
executes the existing session, information, motor-auth and bounded probe
functions, checking each prerequisite's resulting state. Manual controls are
under Advanced diagnostics. A pending baseline changes the guided click to
verification-only; clearing that pending state cannot fall through into a
second probe. Physical probe packets and its allowlist are unchanged.


### Build .41 live probe result; .42 diagnostics

The 2026-09-09 17:04 UTC user log confirms the guided setup, original native
D4.5.0.0/M4.4.8.0/EU reads, and motor E2FFFF marker. Probe baseline completed,
then M-update-entry began at 17:04:50.948 and stopped at 17:04:58.299. No reset
was requested and the allowlisted probe has no image-transfer commands.
Entry/exit is not established and post-probe readback was not included.

The 7.35-second phase is consistent with the one-second mode delay, several
ATT writes and six-second PCA reply timeout, but the old log cannot prove the
failed substep. Hn.R source prefix matching was rechecked without identifying
a justified packet change. Build .42 preserves the sequence and matchers and
logs initial-status/set-mode/configured-status/pca-request, ATT completion,
accepted bridge status and at most 12 distinct three-byte RX headers per step.
No serial or authentication payload is exposed. The test now simulates a
missing PCA reply and checks exact diagnostic attribution.

Copy log now retains the latest probe's connection and subsequent reconnects
when a probe start marker is present; previously latest-session slicing lost
the first half of an entry/exit test. The browser test covers both halves.


### Build .43: compact clipboard report

The user reports truncation when copying/pasting a 36,131-character test log.
The exact clipboard-versus-paste boundary is unconfirmed. Copy log now exports
a report below 8,000 characters: routine packet/setup lines are omitted,
entry diagnostics and failures are retained, and the newest whole lines take
priority if necessary. Omitted-line counts and the END marker make this
explicit. Full displayed/stored logs are not modified. Tests cover a large
log, entry failure plus restart separated by thousands of routine lines,
latest-session outcomes, and clipboard failure. No bike protocol changes.


### Build .43 report: restart verification incomplete; .44 stops duplicate reads

The compact user report includes the .42 17:12/17:13 reconnect: EU0 and native
D4.5.0.0 are readable, ordinary drive firmware has no matching reply, and M
returns 00 01 87 39 00. Physical power-cycle and normal bike operation have
been asked about; not yet confirmed. Error39 semantics are not inferred.
No new entry probe occurred. The old verification reader ignored negative
replies and the UI ran it even after failed native reads.

Build .44 requires successful model, ordinary firmware, region and native D/M
batch results before additional identity verification. A failed batch stops
with named missing reads. The verification reader now recognizes the matching
negative reply opcode, names each read on failure, and stops immediately on
device rejection. Tests cover rejection on all five reads and the full browser
batch stopping at M with no follow-on reads. Probe command sequence unchanged.


### Build .44 live reply framing; .45 correction

The 17:24:02 readback matched the original motor fingerprint, native
D4.5.0.0/M4.4.8.0 and EU0. A subsequent .44 probe obtained bridge status8D,
set-mode acknowledgement23, and configured status8D. The PCA request
00 32 20 01 received a ten-byte notification beginning00 32 22 roughly7ms
after ATT completion. The parser ignored this leading-zero GATT envelope and
timed out six seconds later. No reset or image commands were sent.

Build .45 adds exactly offset1 for a00 32 prefix. It still requires response
22 followed by value1; the old header-only log did not reveal that value, so
acceptance remains unverified. Rejection/missing-value diagnostics now retain
the parser's explicit reason. Tests cover the envelope on both routes and
all selectors/modes, rejection/truncation, and the full bounded probe using
ten-byte zero-prefixed PCA replies. Commands and write allowlist unchanged.

### Build .45 live entry/exit and reconnect milestone

The user report at 17:28 confirms both PCA exchanges were accepted, the M
loader version was read as 2.0.7.1, D bootloader identity was family34/unit0,
and the reset write completed. The probe allowlist excludes firmware erase,
image data and region writes. At 17:30:01.662, a subsequent connection verified
the same application motor fingerprint, native D4.5.0.0/M4.4.8.0 and EU0.
This establishes the bounded entry/exit plus reconnect-readback milestone.
The log does not independently establish a physical power cycle or prove that
the reset command caused recovery. No repeat of this probe is needed for the
same milestone. Region change and firmware transfer remain unverified.

The next preparation prerequisite is interrupted-transfer recovery. The current
transferFirmwarePair baseline accepts only complete original or preparation
pairs; it rejects mixed component versions. Its D identity check also occurs
after the M transfer. Those properties do not support recovery after a lost
connection during a paired update. A firmware version readback alone is not
a byte-for-byte firmware integrity check.

Source review: Th.W2 returns an in-memory cached Sh after checking the stored
model, rather than reconstructing a recovery session after process loss.
Th.p3 has a conditional PCA bypass when h is true, mode bit32 is set and the
selector is zero. The flag is passed through C0012ab.b and Th.n4; its meaning
is not established here, so this branch is not a justified recovery recipe.

Before exposing preparation in the page, establish same-motor identification
without relying on a running application, persist intended image hashes and
transaction state before mutation, and define source-supported behavior for
disconnects during M, between components and during D. Test these failure
paths offline. Do not treat cached session state or a successful entry-only
probe as evidence that an interrupted image transfer can be recovered.

### Build .46: source recovery entry condition

Resolved the previously unknown flag: f64d9.onCreate reads the intent boolean
recovery_install into Q; RunnableC0753wu passes Q to V; V constructs
C0012ab with that flag; f9c41 passes its b field to Th.n4, setting h.
Thus the Th.p3 mode32/selector0 PCA bypass is explicitly a recovery-install
branch, not a generic alternate entry sequence.

enterFirmwareUpdateSession now accepts a strictly boolean recoveryInstall
option, default false. Only true plus mode32 plus selector0 bypasses PCA;
status negotiation and the two-second settling delay remain. No page caller
enables this option. Tests exercise both modes and selectors0/13/31, exact
physical writes and timing, and reject nonboolean flags before any write.
The existing full entry/exit probe tests still pass. This implements one
source-supported recovery primitive, not an interrupted-transfer recovery
workflow or permission to flash.

### Build .47: dedicated D recovery entry, not paired restart

Further source tracing changes the recovery design: Th.v3's recovery flag
branches to static Th.d3 for non-EP models and returns before the ordinary
M/D worker selection. d3 sets C0041b7.b=true and calls x1 with the D file,
mode32, selector0, and no special session resource. Thus the p3 flag modeled
in .46 is not itself the complete recovery-install route.

C0041b7.w1 invokes t1 then o1; o1 selects v1 when b is true. v1 waits100ms,
selects slot0, acknowledges FIRMUP stages1-4, sends stage5 without a result
wait, waits150ms, then acknowledges stage5. It does not use the ordinary
four priming writes or second mode change. Recovery slot0 accepts status1
as well as0/absent (r1 -> Z6 variant2). The original source retries up to
three times; our primitive deliberately makes one bounded attempt and stops
on uncertain delivery.

enterDBootloader now models this explicit recoveryInstall branch only for
mode32/selector0. Nine physical writes and1250ms fixed delays are tested,
including failure and abort at every write, missing replies, invalid modes,
invalid flags and slot rejection. Existing ordinary entry and full probe
tests pass. No live caller selects recovery; no erase/image/region command
was added to the probe. The source D-only path does not establish recovery
from an interrupted M transfer or compatibility of a mixed native pair.
Those cases, same-motor identity and durable transaction tracking remain
requirements before exposing firmware preparation.

### Build .48: retain a bootloader identity reference

The entry-only probe already reads the D loader's six serial bytes but used
only family/unit in its result. It now hashes a snapshot of those bytes with
the probe's random16-byte salt, domain DBL1, family and unit. The resulting
versioned fingerprint is stored alongside the application baseline in the
existing sessionStorage probe record before requesting reset. Application and
bootloader serial formats are not assumed equivalent. Raw loader serial bytes
are cleared after hashing and excluded from results and saved records.

This adds no BLE commands: the probe still uses38 physical writes. Tests
cover repeatability, different identity/salt, input snapshots, invalid serial
fields, callback isolation/failure, all existing probe failures and UI record
retention through reload and reconnect verification. No recovery or transfer
caller consumes this reference yet. Older records lack it; they must not be
treated as having a verified bootloader reference. Session storage is not a
durable cross-tab or browser-loss recovery journal. No additional live probe
is requested merely to populate this field; a future preparation preflight
will need a fresh identity reference once the full procedure is established.

### Build .49: enforce the recorded motor before D programming

The unwired paired coordinator now requires a version1 probe identity
reference with completed reconnect verification, a bootloader fingerprint,
a valid salt, and an application identity equal to the supplied fresh
baseline. Missing/old/unverified references fail before any BLE writes.
The caller must obtain that fresh authenticated baseline using the reference
salt; the record itself does not prove current connection identity.

The D component worker snapshots the expected fingerprint and salt, queries
the live bootloader identity, and compares the salted fingerprint before
serial setup, erase or image writes. Family/unit checks still apply. The
coordinator snapshots the reference before awaiting file loading, so later
changes cannot redirect the comparison. Tests include a different serial
with the same family/unit, invalid references before any paired writes,
reference mutation, all worker failures, and both full-size paired wire
simulations. A mismatch during D stops with M completion retained and no
automatic reset; it does not undo the preceding M transfer.

No UI caller enables transfers or recovery. This closes the D same-motor
guard gap; it does not implement a fresh baseline reader in the coordinator,
a durable transaction journal, or recovery of a partly written M image.

### Build .50: bounded recovery handshake in the guided bike test

The existing normal entry/read/reset probe now includes the source-derived
D recovery-entry sequence after first reading and fingerprinting D identity.
It then repeats the five identity reads and requires the same fingerprint
before its reset request. Fixed recovery substeps have request/accepted/stop
diagnostics without credential or serial payloads. The probe command
allowlist is unchanged: erase, serial programming, image data and region
writes remain blocked. The physical sequence grows from38 to52 writes.

Tests cover failure-before/after and abort at every write, phase timeouts,
different recovery serial on the same family/unit, reset gating, identity
reference capture and UI result logging. The new handshake is not yet live
validated. Request one guided bike test on .50 followed by off/on and the
existing Verify after restart action. A successful result would establish
re-entry from the intact D bootloader plus original native readback, not
recovery of erased firmware or an interrupted M image. No image transfer
is enabled by this test or by a successful result.

### Build .51: fresh baseline enforced by the paired coordinator

After validating both image snapshots and before update entry, the unwired
paired coordinator now reads model, salted application identity, native D/M
versions and current destination from the current connection. All six
baseline fields must match the snapshotted plan. Caller mutation after the
operation starts cannot alter the expected values. Missing destination is
rejected before writes; mismatched live values stop before update entry.
The existing reference salt is used so the fresh identity is comparable.

Tests cover each mismatching baseline field, early input rejection, plan
mutation, and the full physical pipeline including five baseline reads.
Full-size preparation/restoration simulations and all-write failure/abort
checks pass. Authentication and recovery readiness remain external
preconditions; the page still does not call the transfer coordinator.
The guided52-write .50 recovery probe and requested bike test are unchanged.

### Build .52: distinguish the live recovery-stage failure

The .51 bike run accepted recovery mode and slot, then stopped stage 1 in
66 ms. This is shorter than the two-second reply deadline and therefore
is not evidence of a reply timeout. The compact diagnostic previously
collapsed rejection, wrong-stage reply and transport failure together.
Source AbstractC0567r9.f/g and C0665u8 case 11 agree with our normalized
FIRMUP 11 + stage / 12 rejection matcher; no acceptance rule is relaxed.

The next build reports device rejection, expected/received stage mismatch,
reply timeout, ATT timeout, disconnection or transport/local failure
separately. Arbitrary native error messages and credentials stay private.
Local tests cover rejection, mismatch, silence, native failure and abort;
all stop at stage 1 with no follow-up writes. The probe sequence is unchanged.

At 18:21:26.914 the subsequent .51 readback matched the same motor,
D 4.5.0.0, M 4.4.8.0 and EU. Recovery re-entry from the intact loader has
not passed; recovery after erased/interrupted firmware is still unproven.
No firmware transfer or US configuration was achieved by this run.

### Build .53: recovery handoff from the application baseline

The .52 live report explicitly received FIRMUP 12 at recovery stage 1,
90 ms after the request. Subsequent readback at 2026-09-10 04:31:01.152
matched the original motor, D 4.5.0.0, M 4.4.8.0 and EU. No images were sent.
This establishes rejection in the tested already-in-loader state; it does
not establish that the same handoff fails from the running application.

Source Th.d3 directly invokes the recovery worker; C0041b7.v1 labels its
stage-5 transition "working-du handoff". The previous combined probe inserted
normal M and D loader entry before this path. A starting-state mismatch is
a hypothesis, not a decoded explanation of FIRMUP 12.

The guided probe now performs baseline -> direct recovery entry -> D loader
identity -> reset. It has 20 physical writes rather than 52. The restricted
writer no longer permits PCA requests, M loader queries, ordinary mode
selection or slot31. Full identity read and private fingerprint storage must
finish before reset is allowed. The next reconnect still verifies original
application identity, both versions and destination. Loader identity capture
alone is not a comparison to the application's differently encoded serial.

Local tests cover every physical write failing before/after acknowledgement,
abort, phase timeouts, FIRMUP rejection, identity and record failures, and
blocked commands. Success on hardware would establish the direct handoff
from an intact application, not recovery after erase or interrupted M data.
Firmware transfer remains unwired, and the US-region goal remains unmet.

### Build .54: bounded unanswered stage-1 replay

The .53 application-start probe reached recovery mode and slot but stage 1
hit its two-second reply deadline. No recognized acknowledgement or rejection
was observed; this does not prove the bike sent no other traffic. At
2026-09-10 04:36:04.834, readback matched the same original motor, D 4.5.0.0,
M 4.4.8.0 and EU. Neither tested starting state has completed recovery.

Rechecked Th.v3/d3, C0041b7.x1/w1/o1/v1 and B1: the recovery worker directly
uses its handoff, while B1 permits four attempts when no successful transport
result arrives (lines 1609-1720). Our single-attempt experiment was stricter.
The next probe repeats only the identical stage-1 packet, at most four times,
and only after ATT completed followed by the reply timeout. Explicit FIRMUP
rejection, wrong stage, disconnection, ATT errors and later-stage timeouts
still stop. No extra mode changes or downstream commands run during replay.
A delayed stage-1 acknowledgement is evidence of that stage, not attribution
to a particular attempt; the remaining handshake and loader identity are
still required. Success path remains 20 writes; maximum with replay is 23.

Local tests cover success after 1/2/3 silent attempts, four-attempt exhaustion,
identical packet bytes and timing, explicit rejection without replay, native
failure/abort during replay, and full-probe failure/abort boundaries. The
firmware transfer coordinator is still unwired. This test cannot establish
recovery after erased firmware or completion of the US-region objective.

## Build .55: reconnect preparation to the actual US setter

Revalidated the primary published guide on 2026-09-10:
https://etuning-app.com/downgrade.pdf (pages 1, 3 and 4, zero-based).
It explicitly lists E5000/E5080 4.3.0 for downgrade from 4.4+, calls the
included firmware original/unmodified, and assigns E5000 4.3.0 capability B
(region USA), whereas 4.4+ has only capability C. This is vendor documentation
supporting the candidate, not a live compatibility test of this bike. Its
historical Android installation instructions are not our phone-only WebBLE
implementation. Its claim of settings surviving a later firmware update
also does not replace our required destination persistence check.

Fresh source audit: w.z checks Gh.w and opens f91a2 when false. Gh.w/D
permits this family at 430; executing the extracted VerifyPolicy.java again
returned false at 450 and true at 430. The direct branch then sends
00 16 A8 01 <destination>. The intervening ae.d0 is a UI dialog helper,
not a BLE recovery/authorization command. In's AA handler invokes the region
success callback; it does not establish independent readback or persistence.
Thus there is a source/documented path from older stock firmware to the same
setter already implemented. There is no source claim that our recovery probe
itself enables region writes. The exact reason for device AB/3A remains
undecoded; these findings do not prove downgrade is the only possible route.

A concrete integration gap was fixed: identifyDrive previously hardcoded
motor authentication to 4.5.0 and directWriteEligible=false for every version.
It would therefore block the intended post-preparation step. The page now
requires successful exact model/unit, ordinary 4.3.0, native D 4.3.0.0 and
native M 4.2.1.0 responses plus a valid slot-1 region before marking the
reviewed preparation pair eligible for the manual US experiment. The existing
canSetUS additionally requires verified connection, motor authentication,
EU value 0 and no prior attempt. The original 4.5.0 pair stays ineligible.
Missing, truncated, device-error and mismatched responses fail the new gate.
Eligibility is not a claim that the subsequent write will succeed.

No firmware transfer is enabled. The guided recovery card says it is on hold;
no new physical test is requested for this build. Next implementation work
must address completing the verified preparation -> US setter -> restart
readback workflow, rather than treating recovery diagnostics as the outcome.

## Build .56: same-motor US readback after reconnect

The US setter now obtains a fresh five-query application baseline after its
EU preflight, requires the reviewed prepared pair, and saves a salted motor
identity plus expected US destination in the existing session-storage restart
record before sending A8. Storage failure or baseline mismatch prevents the
setter. Only the salted hash is saved, not raw serial or passkey. The record
also remains pending after a rejected or uncertain write, so the next action
is verification rather than another setter. Pending restart verification
blocks new US attempts.

The existing Verify after restart button reads the same motor identity,
native D/M versions and US destination in a distinct connection. It never
falls through into motor authentication or the recovery probe during that
verification click. An EU or identity/firmware mismatch remains unverified;
no retry or repair writes follow. Logs distinguish post-region evidence from
post-probe restoration. Immediate US readback does not mark the restart
record verified. Page reload in the same tab preserves the expectation;
sessionStorage does not promise retention after closing the tab/browser.

Eight setter browser tests pass, including baseline/storage failures,
pre-write record creation and reload, rejection/uncertain delivery and
unchanged destination. Guided UI tests cover matching and mismatching US
verification with read-only dispatch. The existing physical baseline tests
cover identity/version/region mismatches, all read errors and the distinct
connection requirement. Reconnect is not independent proof of a power cycle:
physical restart persistence and a real US change remain unverified. No
firmware transfer was enabled and no new bike test is requested.


## Build .57: enforce the recovery-test hold in the guided action

The .55 card said recovery diagnostics were on hold, but runGuidedBikeTest
still called motor authentication and runBootloaderProbe after compatibility
reads. This contradicted the stated next step. The main action now says Check
region and stops after session authentication and the information batch.
Pending same-motor restart verification retains its existing read-only branch.
The recovery primitive remains available for offline work but has no guided
button caller. Firmware transfer remains unwired; no new bike test is requested.

The browser test asserts that a normal click and a repeated click cannot invoke
motor authentication or recovery, retains earlier-build restart records, and
checks US matching/mismatching readback without further writes. This change
implements the investigation hold; it does not advance firmware compatibility
or establish a successful US write.

## Preparation blocker audit — 2026-09-10

The previous guided-action correction is deployed as .57. The next unresolved
requirement is the actual preparation transfer and its interrupted-M recovery
path; another D-loader entry success would not establish either.

Targeted reinspection of eTuning 3.0.7 Th.q4 (8093-8104) shows an Ih.k family
check before its alternative M worker callers (8261, 8531). This is not an
E5000 recovery route. C0776xk.z0 (4776-4778) delegates to x0(false), rather than
implementing independent reconnect recovery. Th.W2 (6832-6842) returns an
in-memory cached Sh only for a matching family; it does not demonstrate
restoration after process loss. These are bounded findings about these callers,
not proof that no other recovery implementation exists.

Primary documentation checked through indexed official source excerpts:
- https://si.shimano.com/en/pdfs/um/7J4WA/UM-7J4WA-008-ENG.pdf,
  page 21, Restoring the firmware: the general Professional procedure uses
  SM-PCE02 connected to a PC and the affected unit.
- https://bike.shimano.com/en-UK/support-and-service/faq/EPC0A.html,
  NM-6060 and NM-4030: wireless-failure recovery guidance includes restarting
  the system and checking restoration; unresolved wireless update failures
  are directed to wired restoration. The linked recovery categories in
  NM-6060 concern system information displays/wireless units and power meters.
  This does not specify interrupted E5000 M-component recovery over WebBLE.

Full PDF downloads attempted in this audit were unavailable (web size limit
and direct HTTP 403). The claims above are limited to the returned official
indexed sections, not an exhaustive review of those manuals. The documentation
neither establishes our phone-only recovery implementation nor proves such a
route impossible. No purchase is proposed and no additional motor test or
firmware write is enabled. Required new evidence is a source-backed E5000 M
interruption/reconnect restoration sequence or a known-working corresponding
trace; repeating intact D-entry diagnostics does not supply that evidence.

## Build .58: retain M rejection codes needed for window recovery

C0776xk.X0 scans for F2 00 32 followed by an unsigned error byte. Y0 parses
that error from a diagnostic string. Q0 selects codes 02, 05 and 0A; P0
recognizes 05. An extracted Java harness confirmed those predicates, including
unknown/malformed input. These codes are distinct from transfer query status 01.
The M reply accumulator previously discarded the error byte and retained only
checksum-rejected. It now preserves observed codes through the failed query
exception. A missing byte remains unknown, not zero; distinct observations are
retained rather than silently choosing one. Checksum markers remain uncorrelated.
No retry selection is enabled by this evidence and existing failure stops remain.

Further raw E0 control-flow inspection locates an at-most-three partial-window
loop (M-transfer-debug.java 2790-2813, 3148, 3830-3862), selected by Q0, and a
subsequent at-most-five full-window loop (3899-3910, 4827, 4929-4961,
5780-5805). The full-window path sets the address, clears checksum, and invokes
j1 in 64-byte steps. Complete success/exit and error escalation still need
validation before translating that state machine. Both are same-session logic;
this is not evidence of reconnect or power-loss recovery.

Query tests cover zero/02/05/0A/FF, missing error bytes, conflicting observations
before ATT completion, and no extra writes. M reply, block/image and shared D
query tests pass. Firmware transfer remains disconnected from page controls.
No new physical test is requested.

## Build .59: partial-window M packet encoding

Raw j1 (M-transfer-debug.java 12229 onward) copies up to 64 real bytes into a
zero-initialized block. A checkpoint occurs when offset+64 reaches image end
or a 1024-byte boundary; its checksum starts at the caller's retained window
start. T0's clamp can make the final retry unaligned: for 116320 bytes and
failure offset116288, restart is116256, address FDC620, checksum start115712.
The restoration M image's 16-byte final window instead clamps to its start.
Extracted Java helpers a()/d() both produced 000000 for window/initial checksum
clear payloads. This does not establish their effect on an interrupted motor.

firmwareMRewriteBlock encodes only offsets in that explicit partial-window
sequence. It leaves ordinary firmwareBlock alignment checks intact and has no
transport caller. Six synthetic fixtures use extracted M0/Q9 Java methods;
the harness supplies the chunk/checksum following the inspected raw j1 rules,
so these are payload/geometry checks, not execution of the entire Java worker.
They cover the reviewed image lengths, an unaligned 65-byte case, a complete
window, final zero padding and full-window checksum. Tests also reject offsets
outside the derived sequence. No retry state machine, reconnect recovery or
firmware writes were enabled. No new bike test is requested.

## M checksum freshness: timeout and explicit rejection are different cases

Inspected 3.0.7 C0644tk.a (52-145): query/data acknowledgements compare
sequence fields, while the checkpoint branch (117-141) records F2 00 31/32
without comparing a sequence or window address. F0 registers that listener
before issuing its query and waits for the acknowledgement/checksum
(M-transfer-debug.java 7004-7100). AbstractC0812yn.b/e add/remove listeners;
its c method forwards newly received bytes to current listeners. Registration
does not replay its history, but neither registration nor removal establishes
a device queue flush. These inspected paths provide no freshness barrier.

A hypothetical checksum arriving after a timeout and a subsequent attempt's
data acknowledgement could therefore be mistaken for that subsequent attempt's
checksum. This is a protocol-correlation limit, not an observed bike failure.
It does not establish ambiguity for every explicit-rejection retry: in that
case a terminal rejection was already observed, rather than still outstanding.
The inspected source selects rejection codes 02/05/0A for partial recovery;
its same-session rewrite logic and device ordering assumptions remain distinct
from recovery after timeout, disconnect or power loss. An arbitrary delay is
not evidence that outstanding device replies have been drained.

The current block worker stops on a checkpoint timeout. The worker regression
now exercises a checkpoint data ACK with no checksum, verifies no retransmission,
then invokes a saved callback with a late checksum to model an already queued
notification. The settled failure stays failed, with no writes or timers added.
This validates host cleanup only; it does not qualify firmware installation.
Next implementation work should keep explicit-rejection recovery separate from
uncertain transport outcomes, rather than enable a general retry-on-failure path.

## Build .60: source-backed reconnect recovery journal and full M replay

Further eTuning 3.0.7 tracing resolves the paired reconnect behavior. The
recovery UI launches `f64d9` with `recovery_install=true` plus the cached family
and baseline. `f64d9.V` carries the flag in `C0012ab`; `f9c41.Y` passes it to
`Th.n4`, which assigns `Th.h`. `Th.o3` is only a wrapper around `p3`. In the
paired `Th.q4` path, the relevant calls occur in this order: `o3`,
`C0776xk.z0(M image)`, `p3`, and `C0041b7.g2(D image)`. Both decompiler copies
have the same order. `C0776xk.z0` delegates to `x0(..., false)` with the complete
image object; no persisted byte offset is supplied. `Th.p3` uses `h` only to
bypass the PCA request when bridge mode32 and selector0 are already active.

This supports a reconnect recovery that replays M from its beginning and then
continues the paired D path. It does not support resuming M at an arbitrary
saved byte. The source's same-session partial-window rewrites remain separate
from reconnect recovery and are not enabled after timeouts or disconnects.

The unwired coordinator now writes a versioned journal before its first
update-mode command. The journal contains only whitelisted baseline fields,
the exact reviewed D/M SHA-256 hashes, versions and sizes, a salted binding to
the origin-scoped Web Bluetooth device ID, the salted D-loader fingerprint,
completed-component flags, and the last stage. It never stores the passkey,
motor-authentication credentials, raw device ID, raw serial or firmware bytes.
Every stage transition must round-trip through durable storage.

`recoverFirmwarePair` requires the same Bluetooth device binding, user-reselected
files with the exact recorded hashes, and the recorded bootloader fingerprint.
It invokes both session negotiations with `recoveryInstall=true`, replays all of
M, runs the ordinary paired D entry, verifies the D-loader fingerprint before
D setup/data, and stops without reset. An already completed journal does not
replay. Failure records the stage for another explicit reconnect attempt.

`node tests/firmware_recovery.cjs` covers full M replay even when the old attempt
reported M complete, paired ordering, every worker failure, impossible journal
states, different device/file rejection before writes, field whitelisting and
the completed no-op. The ordinary coordinator now refuses to mutate the bike
unless its journal was durably saved; its controlled and full-wire tests pass.
The Web Bluetooth device ID identifies the SC-E7000 endpoint rather than proving
the attached motor on its own. The D-loader fingerprint supplies the motor check
before D data, while the fresh application fingerprint remains the pre-mutation
check. This limitation matches the source workflow and must remain explicit.

No UI caller, reset, firmware image write or region write is enabled by build
.60. Remaining offline work is a reset/reconnect transaction that accepts only
the exact prepared D4.3.0.0/M4.2.1.0 readback, retains recovery state until that
verification succeeds, and then gates the already modeled US write and a later
power-cycle persistence read. Only after those failure paths pass simulation is
a controlled preparation test justified.

## Builds .61-.63: complete guarded transaction and simplified local input

The guided transaction now separates paired transfer, reset, reconnect readback,
the one destination mutation, physical-power-cycle persistence, restoration and
final readback. Preparation begins only from the same E5000 family 34/unit 0,
D4.5.0.0/M4.4.8.0 and EU value 0. Restoration begins only after the same motor
has reported D4.3.0.0/M4.2.1.0 and US value 1 in a different BLE session after
explicit physical-power-cycle confirmation. Completion requires a later session
to report the original D4.5.0.0/M4.4.8.0 pair and US value 1. The journal remains
until that final match.

The direct setter packet remains `00 16 A8 01 01`. Reinspection of the desktop
setter establishes byte 3 as destination_rewrite and byte 4 as destination, so
the rejected original-firmware attempt did not use a reversed selector. The
newer app's connection state machine deliberately enters `03 4B / 06 1F` and
then restores `03 00 / 06 00` before normal operation. Keeping its temporary
connection mode active is therefore not a supported alternative explanation for
AB/3A. Its compatibility predicate routes E5000 firmware 4.3.0 through the
destination-setting path and routes tested 4.5.0 through preparation.

The public `5000_430.zip` has SHA-256
`4dee4d75ee83c22e951114cbf57332709c15be637ec2a8171bd82f9345adb137`.
Its two extracted files are byte-identical to the archived Shimano desktop
D4.3.0/M4.2.1 files already reviewed. Build .63 accepts only that complete
archive hash, its exact two local-entry layouts, decompressed sizes and raw
SHA-256 hashes. It also continues accepting the two exact extracted DAT files.
The archive is parsed and decompressed locally; neither file contents nor user
credentials leave the browser.

Build .63 combines the preparation archive and both restoration images into one
file selection, classifies them by the reviewed hashes regardless of selection
order, and caches the verified bundle in local browser storage for interrupted
workflow recovery. The cache is cleared after final success. The six-digit
passkey and authorized Bluetooth device object remain memory-only in the open
tab, allowing one passkey entry and best-effort direct reconnects. Each required
physical restart is confirmed by pressing an explicitly worded **I
power-cycled** workflow action; the separate checkbox was removed.

Journal validation now binds a preparation journal to the original EU baseline
and a restoration journal to the prepared US baseline. Every post-reset stage
requires the recorded reset-connection binding. A stopped journal must retain a
non-stopped last stage, while an active journal cannot carry stale failure state.
After preparation preflight, the transfer button requires a physical power-cycle
confirmation before the first firmware byte.

The exact original restoration images remain mandatory before preparation.
The reviewed D4.5.0 wrapper and M4.4.8 raw file validate locally. Shimano's
catalog names and sizes match, but direct public URLs returned HTTP 403 from the
development environment. No public mirror of that exact pair was found. The UI
links to Shimano and refuses to start when either file is unavailable or fails
its exact hash. No firmware bytes have yet been sent by this guided workflow.

Offline validation covers the complete physical packet streams at both reviewed
image sizes, failure before and after every simulated write, timeouts, aborts,
same-device and loader-identity gates, full-M reconnect replay, reset separation,
uncertain one-shot US readback, physical-power-cycle persistence, restoration,
final goal readback, reviewed wrapper normalization, and exact ZIP extraction.
The remaining evidence is a controlled bike run. It must first establish that
the preparation pair transfers, resets and reads back exactly; only then may the
same transaction attempt US. The final readback is the region result. Higher
assistance speed is a separate physical observation.

## Build .64: first-use preflight returns to the bike-validated entry path

The build .63 live run verified the complete preparation/restoration bundle,
the original D4.5.0.0/M4.4.8.0 EU baseline and motor authentication. Its direct
D-recovery preflight accepted recovery mode and slot, then received no reply to
recovery stage 1 in four bounded attempts. It stopped before creating a recovery
journal, sending a firmware image, or writing the destination. Firmware and
region therefore remained unchanged by that run.

Using direct recovery as the first-use gate was inconsistent with the bike
evidence. Build .45 already completed the ordinary M entry, M loader-version
read, ordinary D entry, D loader identity and reset sequence on this exact bike.
Build .64 restores that sequence for the preparation preflight. The restricted
writer permits only the application baseline reads, ordinary entry commands,
loader version/identity reads and the final reset; it continues to block image
data, erase commands and destination writes.

Direct recovery entry remains available only after the durable journal proves
that a firmware transfer started and was interrupted. A successful .64 preflight
records the application and D-loader identities, requests reset and stops. The
page then requires an explicit physical power cycle before it enables the first
firmware transfer. Offline simulation covers all 38 preflight writes, failures
before and after each write, aborts, phase timeouts, identity and baseline gates,
the reset gate and command allowlist. Preparation transfer and the resulting
region change remain unverified on the bike.

## Build .65: D4.5.0 decompilation replaces firmware preparation

The unwrapped E5000 D4.5.0 image was loaded as little-endian ARM Thumb at
`0x10000`. Its category-16 command table dispatches `A0` to `FUN_000252a8` at
`0x252a8`, `A4` to `FUN_0002541c` at `0x2541c`, and `A8` to
`FUN_0002537c` at `0x2537c`. The `A8` handler contains no firmware-version
comparison. It accepts the record only when current PC mode is 4 or 5 and the
one-shot flag written by `A0` is 1; otherwise it constructs error `3A`. On the
accepted branch it copies the destination fields, clears the flag and invokes
the persistent-record helper at `0x25516`.

The PC-mode handler `FUN_0002721c` at `0x2721c` stages modes 4/5. Secure-code
handler `FUN_00027430` at `0x27430` promotes the staged mode after five matching
16-bit values and routes the category-32 opcode-12 completion to the requesting
application slot. Mode 0 clears the privileged state. These branches explain a
specific missing-state result and do not depend on the newer app's policy of
routing D4.5.0 through firmware preparation.

The protected-mode sequence and D4.5.0 record handlers establish this wire
sequence:

1. `00 32 10 05 00 00 00`, wait 1000 ms with the battery present;
2. five little-endian category-32 opcode-30 secure words, 100 ms apart, then require
   category-32 opcode-12 completion;
3. read the first five record bytes with `00 16 A4 00` / `A6`;
4. stage those five bytes unchanged with
   `00 16 A0 00 <five bytes from A6>`;
5. read the current six-byte OEM record tail with `00 16 AC 01` / `AE`,
   change only its destination byte from 0 to 1, and send all six bytes with
   `00 16 A8 <six-byte candidate>`; and
6. exit with `00 32 10 00 00 00 00`.

The desktop authorization caller also invokes `UnlockRegulationSetAuth` after
the already reconstructed challenge-response. It regenerates the seven-byte
serial-derived request and sends category 16 opcode `E8`; build .65 requires
its normal `EA` reply before entering PC mode. This is a conservative upstream
authorization gate. The `A8` handler's local `3A` branch directly checks PC mode
and the `A0` flag.

Build .69 performs a fresh full-record EU read, the complete authorization and
mode sequence, one full-record destination write, immediate readback, and a
mode-0 exit on success or failure. A salted same-device record is durably saved
immediately before `A8`. After a physical power cycle, the same button verifies
the same D4.5.0/M4.4.8 pair and destination in a different BLE session; it does
not repeat `A8`. The firmware preparation UI is hidden and its cache is no longer
loaded at startup.

Synthetic browser tests cover exact packet order, preservation of both record
halves, early and delayed replies, ATT failures that race replies, every
prerequisite gate, at-most-once `A8`, mandatory PC-mode exit, durable record
reload, same-device pairing, and terminal persistence outcomes. Live validation
still has to establish `E8/EA`, PC-mode completion, `A8/AA`, US readback and
post-power-cycle persistence on the bike. No speed outcome is inferred from a
region reply.

## Build .66: correct mode-5 secure-word byte order

The build .65 bike test completed motor authentication and received the normal
`EA` response to the `E8` regulation unlock. It then timed out waiting for the
mode-5 completion response, before any lighting or destination command ran.

Reviewing the exact desktop transmit loop exposed a byte-order error in .65.
The embedded 5x2 table is stored as high byte followed by low byte, while the
loop sends column 1 and then column 0. D4.5.0's `FUN_0002c25a` parser constructs
the 16-bit value from the received pair as little-endian. Build .66 therefore
sends `27 0F`, `11 55`, `35 B0`, `03 F3`, and `09 03`. These values also match
the mode-5 table extracted directly from the exact D4.5.0 image. The mode,
application slot, spacing, prerequisite, and no-write-on-failure boundaries are
unchanged. The corrected mode completion and destination transaction still
require live validation.

## Build .67: reproduce the desktop PC-link lifecycle

The production desktop method `SendSetPCLinkModeStart` establishes ordinary
mode 1 before connected-unit operations; its inspection method later enters
mode 5. Build .67 reproduces both transitions. It sends mode-1 words `A2 2B`,
`30 0E`, `7A 4D`, `62 2B`, and `85 B4`, requires category-32 opcode-12
completion, and only then sends the corrected mode-5 sequence. The destination
path stays closed unless both completions arrive.

Mode 1 broadcasts a secure echo for each received word, which provides a
framing checkpoint before the completion gate. The page listens for these
responses on 2AF9, 2AFB, and 2AFD and logs the characteristic that carried
them. A mode-status response received before the fifth word cannot satisfy the
gate. Any failure requests mode 0 and disconnects without sending `A0` or `A8`.

The real .67 run sent both mode-1 setup and all five words but observed zero
echoes and no completion. No setting opcode ran. This bounded result ruled out
the secure-word values as the immediate failure point and exposed the remaining
difference from a wireless session: the return application slot.

## Build .68: route PC-mode completion to the wireless application

The supplied eTuning ATT capture writes display setup `00 0C 01`; 61 ms later
2AFD reports `00 32 12 01 0D FF FF 00 FF FF`. D4.5.0's mode request handler
reads the request's second parameter as the application slot, retains it during
the five-word check, and sends completion to that slot. Shimano's managed
library likewise fills parameter 1 from `PCAppliSlotNo`. Slot `00` is therefore
specific to the directly attached desktop adapter, while this SC-E7000 BLE
route announces slot `0D`.

Build .68 records an unicast slot below `3F` from a mode-1 opcode-12 setup
announcement. If the bridge does not relay that announcement, it uses `0D` from
the exact supplied capture. Mode 1, mode 5, and mode 0 requests all carry the
selected slot. An opcode-12 notification counts as completion only after the
fifth secure word and only when both its reported mode and application slot
equal the request.
The `A0` and `A8` commands remain unreachable on any missing or mismatched mode
completion.

## Build .69: preserve the complete regulation record

**Superseded by build .70.** This section records the hypothesis tested by .69;
the live rejection and wire-level evidence below show that its internal-buffer
widths were incorrectly treated as BLE parameter lengths.

The .68 bike run validated the wireless route. The information batch observed
application slot `0D`; normal mode 1 completed as `00 32 12 01 0D`; protected
mode 5 completed as `00 32 12 05 0D`. The subsequent `A4` read reported a
lighting value of 10, but .68 sent `00 16 A0 0A 00 00 00`. The motor immediately
returned `A3 3A`, the page exited mode 5, and no `A8` command was sent.

The rejection matches the exact D4.5.0 handler. `FUN_000252a8` requires the
first parameter after `A0` to be zero, copies the following five bytes into a
candidate buffer, and only then sets the one-shot flag. `FUN_0002541c`, reached
by `A4`, returns the corresponding five-byte live record. The persistent-record
helper at `FUN_00025516` compares and writes 11 bytes. `A8` supplies the remaining
six bytes, and the adjacent `AC` getter returns those six bytes. The persistent
record lives at RAM `0x2000253c`; the candidate lives at `0x20002548`.

Build .69 therefore performs a full-record read-modify-write. It requires the
fresh `AC 01` response to contain all six OEM bytes and EU at byte 1. After exact
mode completions, it reads all five `A4/A6` bytes and sends
`00 16 A0 00 <the same five bytes>`. Only an `A2` response unlocks the final
step. It then clones the six OEM bytes, changes byte 1 from EU (`00`) to US
(`01`), and sends `00 16 A8 <the six-byte clone>`. Short replies and any error
stop before the destination commit; `A8` remains at most once.

This correction also avoids relying on legacy managed-library padding. The
older `SetDestination` helper initializes a four-byte parameter array to
`FF FF FF FF` before replacing its first two bytes. D4.5.0 itself copies six
destination-tail bytes. Reusing the live `AC` result preserves the exact values
for this motor and is stronger than choosing zero or `FF` for fields whose
meaning is not established.

## Build .70: restore Shimano's seven-byte setter frames

The .69 bike run completed session authentication, motor authentication,
`E8`/`EA`, normal PC-link mode 1, and protected mode 5. Its `A4` response was
logged as `0A 00 FF FF 93`; the nine-byte `A0` stage was then rejected with
`A3 3A`, and `A8` remained unreachable. Mode exit completed and the bike was
left at EU.

The supplied official HCI capture resolves the boundary between command data
and the BLE bridge envelope. Handle `0x002f`, mapped to `2AFE`, has 241 writes
and a maximum value length of seven bytes. The captured `A4` request is the
four-byte `00 16 A4 00`; its ten-byte reply is
`00 16 A6 0A 00 FF FF A4 01 FF`. The managed getter declares only the first two
reply parameters as lighting time. The remaining bytes are fixed-envelope
padding or trailer data and cannot be copied back as setting fields. The same
applies to bytes after selector/value in the ten-byte `AC` reply.

The desktop `etubedatalinks.dll` supplies the missing setter serialization.
`DUUnitDataLink.SetLightingTime` creates a four-byte parameter array, copies the
little-endian `UInt16` into indices 0 and 1, and sends category `16`, opcode
`A0`. `SetDestination` creates the same four-byte array, overwrites indices 0
and 1 with selector/value, and sends opcode `A8`. The FieldRVA initializer used
by both methods is confirmed directly at DLL RVA `0xD1560` as
`FF FF FF FF`. Thus the exact candidate frames are:

- `00 16 A0 <lighting low> <lighting high> FF FF`;
- require normal `00 16 A2` before continuing;
- `00 16 A8 01 01 FF FF` for OEM selector 1 and US value 1.

Build .68 used the correct seven-byte length for `A0` but filled the final two
parameters with `00 00`; build .69 used invalid nine-byte record framing.
Build .70 changes only this bounded wire-level issue. It retains exact motor
and firmware gates, the verified slot-`0D` mode lifecycle, at-most-once `A8`,
immediate destination readback, protected-mode exit, and distinct-session
persistence verification. No firmware, erase, bootloader, retry, or separate
speed-limit command is used.

The .70 bike result rejected `00 16 A0 0A 00 FF FF` with `A3 3A` after exact
mode-1 and mode-5 completions. The motor then accepted mode 0 and disconnected;
`A8` was not sent. This rejects that packet in mode 5. It did not test the
separately keyed mode 4 later accepted in build .72.

## Build .71: isolate the zero-selector staging boundary

**Superseded by build .73.** The normalized-offset interpretation in this
section omitted the motor target address inserted between opcode and setting
parameters. The section remains as the record of the experiment that led to
build .72.

Rechecking the D4.5 receive path establishes the handler field mapping. The
internal bus reassembler places the command category and opcode at normalized
offsets 2 and 3; the first raw setting parameter is therefore normalized offset
4. `FUN_000252a8` requires that byte to be zero, copies the following five bytes
to the transient candidate, and sets the only flag consumed by `A8`. Builds .68
and .70 put lighting value `0A` in that position. Build .69 used the correct
zero-selector form and all five fresh bytes, yet still received `A3 3A` after
the exact protected completion. The remaining failure is therefore bounded to
the motor's live mode state or the wireless delivery shape.

The Android 3.0.7 source supplies two further controls. Its generic
`C0549qn.X(int)` method emits the seven-byte lighting packet tested by .70, so
that helper is not evidence for D4.5's destination prerequisite. Its actual
region call sites in `eTuning/.../ea/w.java`, `C0545qj`, and `AbstractC0210gc`
all emit exactly `00 16 A8 01 <destination>` with no explicit padding. The same
2AFE characteristic also receives nine-byte setting writes in `G5`, so the
seven-byte maximum observed in one HCI capture is bounded negative evidence,
not a protocol ceiling.

Build .71 performs one automated, nonpersistent diagnostic after all existing
identity, authentication, `E8/EA`, mode-1 and mode-5 gates pass. It freshly reads
the five-byte `A4/A6` record, then sends these `A0` forms in order:

1. `00 16 A0 00`;
2. the same packet followed by the first one, two, three and four live bytes;
3. `00 16 A0 00 <all five live bytes>`.

Every accepted prefix is logged. The first `A3` or transport failure stops,
requests mode 0 and disconnects without `A8`. Prefix stages only overwrite the
RAM candidate; no persistent helper runs until `A8`. Even if an early prefix
sets the one-shot flag, a later failure cannot cause a write because the page
never sends `A8` on that path and ends the privileged session.

If and only if the complete nine-byte form returns `A2`, the last candidate is
an exact copy of the fresh live record. The page then saves its same-device
restart expectation and sends `00 16 A8 01 01` at most once, matching Shimano's
Android region call sites. It requires immediate selector-1 readback, exits PC
mode on all paths and requires a separate power-cycle readback for persistence.
No firmware, bootloader, erase, retry, factory-selector, or speed-setting command
is reachable from this workflow.

## Build .72: exercise the firmware's authenticated mode 4

The .71 bike run completed motor authentication, `E8`/`EA`, ordinary mode 1,
and mode 5 on wireless application slot `0D`. It freshly read the regulation
record as `0A 00 FF FF 84`, then sent the first diagnostic frame
`00 16 A0 00`. The motor immediately returned `A3 3A`, the page exited mode 5,
and `A8` remained unsent. Since the first prefix failed, .71 provided no
evidence about longer prefix acceptance and further prefix looping would only
repeat the same rejected state.

Static analysis supplies a distinct next authorization state. The D4.5.0 image
contains three adjacent five-word secure tables: the already verified mode-1
and mode-5 tables, plus a mode-4 table at image offset `0x19f8` with wire pairs
`19 B2`, `73 D8`, `A4 73`, `B1 72`, and `01 10`. The `A0` and `A8` handlers both
read the same current-mode byte at RAM `0x200029f9` and explicitly accept values
4 or 5. The secure-word handler promotes the requested mode into that byte
before emitting opcode-12 completion. Mode 4 is therefore a firmware-defined,
authenticated setting candidate rather than an invented state.

Build .72 retains every proven gate and changes only the second PC-mode
selection. It requires exact mode-1 and mode-4 completions for live slot `0D`,
freshly reads all five `A4/A6` bytes, and sends one complete
`00 16 A0 00 <five live bytes>` stage. No short-prefix loop remains. A normal
`A2` is mandatory before the at-most-once destination write. The write stays
the exact five-byte Android region call `00 16 A8 01 01`; bytes following the
public fields in fixed ten-byte replies are not copied into a setter. Any mode,
stage, storage, write, or readback failure requests mode 0 and prevents a retry.
The .72 bike run established exact mode-4 acceptance on slot `0D`, then read
`A4/A6` as `0A 00 FF FF 93`. Its nine-byte stage returned `A3 3A`, so `A8` was
not sent; mode exit completed and the bike remained EU.

## Build .73: combine authenticated mode 4 with Shimano's A0 frame

The working destination query `00 16 AC 01` resolves an ambiguity left by the
decompiler. `FUN_000254a4` accepts the live query although it requires byte
`+4` in its normalized message to be zero. That byte therefore cannot be raw
selector `01`; it is the motor target address from raw byte 0. Category and
opcode occupy normalized offsets `+2/+3`, target address occupies `+4`, and
public setting parameters start at `+5`. This mapping also explains why the
firmware copies five bytes for a four-parameter BLE setter: the wireless bridge
supplies the final internal byte.

Both Shimano implementations independently construct the public `A0` command
as a 16-bit lighting value followed by `FF FF`. Android
`C0549qn.X(int)` emits `00 16 A0 <low> <high> FF FF`; the desktop
`DUUnitDataLink.SetLightingTime` emits the same fields. Only the declared first
two `A6` parameters are the lighting value. The later fixed-notification bytes
belong to the normalized bridge record and must not be copied into a BLE setter.

No previous run tested this official seven-byte packet while authenticated
mode 4 was active: build .70 paired it with mode 5, while build .72 paired mode
4 with a nine-byte packet. Build .73 retains build .72's accepted mode-1 and
mode-4 lifecycle and changes only the transient stage. It reads the 16-bit
lighting time and sends one unchanged `00 16 A0 <low> <high> FF FF`. Only `A2`
creates the pending restart record and permits the at-most-once Android region
write `00 16 A8 01 01`. Every failure exits mode and disconnects without `A8`.
Immediate selector-1 US readback and a separate reconnect remain mandatory;
assistance cutoff still requires a separate physical measurement.

## Build .73 live result and .74 verification-only UI

The 2026-09-12 bike run confirmed the D4.5.0/M4.4.8 pair, EU destination,
wireless slot `0D`, motor challenge-response and `E8/EA` unlock. It received
exact mode-1 and mode-4 completion responses. The page read lighting time 10,
then sent the single seven-byte unchanged stage
`00 16 A0 0A 00 FF FF`. The motor replied `A3 3A`; mode 0 exit completed and
the page disconnected. No `A8` destination command or firmware command was
sent. The user also observed a screen reset during the process, without a
timestamp relative to the command stages. The compact log does not establish
whether this was a display UI reset or a bike power cycle.

The A0 handler at D4.5.0 address `0x252a8` has two immediate gates: active PC
mode 4/5 and a zero target field at normalized offset `+4`. The observed
mode-4 completion does not prove that the mode remained active when A0 was
handled. The working `AC 01` query supports a zero target field in this BLE
route, but the bridge's exact internal A0 record is not observed. Consequently
`A3 3A` does not identify which gate failed. Repeating A0 with another guessed
packet would add no evidence.

Build .74 changes the primary button to a verification-only status check. It
does the established BLE authentication and information batch, then reports
motor firmware and region. It never calls motor authentication, PC mode entry,
A0 or A8 from that button. The historical setter code remains available to
synthetic tests but is disabled in the page UI. The next live action, if
needed, is only a readback of the original firmware and EU region.

The SC-E7000 setting-menu items the user observed are not region controls.
Shimano's user manual describes Adjust as electronic-shifting adjustment,
Shift timing as gear-shift timing, and RD protection reset as recovery for an
electronic rear derailleur after an impact. The first two depend on electronic
shifting; RD protection reset requires an electronic rear derailleur. Their
presence in the menu does not imply a region configuration path.
Source: https://si.shimano.com/en/pdfs/um/79H0B/UM-79H0B-000-ENG.pdf

Offline review after the .73 result corrected the proposed A0 prerequisite.
Shimano's desktop inspection UI calls `SetDestination` directly from its OEM
destination button; its lighting button separately calls `SetLightingTime`.
The Android region task in `C0545qj.java` also sends `00 16 A8 01 <value>`
directly. No observed client call site stages unchanged lighting time before
changing destination. We inferred the A0 stage from D4.5's A8 one-shot flag,
but have not established how Shimano's region workflow sets that flag through
the SC-E7000 bridge. The A3/3A reply after mode-4 completion narrows the
failure to a mode/target gate only if the response came from the D handler;
the exact bridge mapping remains unknown. No more A0 payload variations or
bike mutation tests are justified by the current evidence.

The local E-TUBE metadata lists Shimano's SC-E7000 4.1.0 display image as
`SCE7000.4.1.0.dat` (126,508 bytes, catalog MD5
`4974d4f471b126be9f9657510e6bef55`). A read-only download from its
published Shimano URL returned HTTP 403 on 2026-09-12, so display bridge
firmware could not yet be compared with the live A0 response. No alternative
image was assumed equivalent.

## Build .75→.76: SC-E7000 bridge image recovered; A0 framing cleared; mode-loss is the real blocker

### The missing display image was obtained and reverse-engineered

The SC-E7000 4.1.0 display bridge image (`SCE7000.4.1.0.dat`, 126,508 bytes,
catalog MD5 `4974d4f471b126be9f9657510e6bef55`) was downloaded on 2026-09-14.
The Akamai edge returns HTTP 403 to a plain GET, but sending the E-TUBE app
User-Agent (`E-TUBE PROJECT Cyclist/4.1.0 (Android)`) reaches the AmazonS3
origin and returns the full image; the MD5 matches the catalog exactly. It is
plaintext ARM Cortex-M (entropy 6.77), loaded at base `0x10000`. It is kept
private and is not committed (see `ASSETS.md`).

### What the bridge does with drive-unit commands

- **No per-opcode filtering.** The display has no command-id literals for
  `A0`/`A8`/`AC`; it never originates them and has no code to intercept or
  rewrite them. They reach the motor through a raw, verbatim forward path
  (`0x2dbb2`→`0x2d7c4`), which copies the command content byte-for-byte and
  prepends only two bus-node bytes.
- **Motor offset+4 is the packet's leading byte, not the first parameter.**
  Verified byte map: motor offset +2/+3 = phone bytes b1/b2 (category/opcode),
  offset +4 = phone b0 (the leading slot/target byte), offset +5.. = phone
  b3, b4, …  This reconciles with the known-working region read `00 16 AC 01`:
  its leading `00` lands at offset+4 (the value the `AC` handler requires to be
  0) and the selector `01` lands at offset+5. **Consequence: every `A0` packet
  sent in builds .68–.73 already had offset+4 == 0. The `A3 3A` rejection was
  never a target-byte or framing problem.** An earlier analyst model that put
  the first parameter at offset+4 was falsified by the `AC 01` read, which would
  then have been rejected but is accepted every session.
- **PC-mode commands are forwarded to the motor, not answered locally.** The
  display's own cat-0x32 handler table (`0x21844`, dispatch `0x2164a`) belongs
  to its connection/handshake state machine for the display's own DU link; it is
  not the phone-inbound handler and contains no code to synthesize a motor
  secure-word reply or a slot-routed opcode-0x12 completion. The DU→phone path
  (`0x1b1c6`/`0x1b1e0`→BLE notify `0x18bf4`) tunnels the motor's raw reply words
  straight back. This matches the live evidence that app-slot `00` produced no
  completion while slot `0D` did: that is the motor's secure-handler slot
  routing. So the motor genuinely enters PC mode 4 when the phone drives it.

### Therefore the blocker is PC mode 4/5 not being live when A0 lands

Because offset+4 was always 0, an `A3 3A` from the `A0` handler means only its
other gate failed: PC mode was not 4 or 5 at the instant `A0` was processed,
even though a mode-4 completion had just been received. A stable connected
session does not clobber the motor's active-mode byte — the display sends no
periodic cat-0x32 mode traffic during steady state (steady state is cat-0x16
polling). The active-mode byte is knocked out on a (re)connection event,
dominantly the display's own reset: the app image contains no software-reset
(no `AIRCR`/`VECTKEY`) and no runtime re-init path, so the screen reset the user
observed in build .73 is a hardware watchdog/brown-out re-entering via the
bootloader (the WDT refresh lives in the bootloader, not this app image). A
reset is abrupt and silent to the motor, which then times out mode 4/5 on its
own. Whether PC-mode entry itself provokes the reset is unresolved from the app
image alone (the watchdog behavior is in the bootloader) and is the key open
question for the live test.

### Market/speed premise confirmed from community sources

Destination `1` (US) unlocks the 32 km/h (~20 mph) cap and keeps the
speedometer/odometer correct; codes are `0` EU, `1` US, `2` Japan, `3` Taiwan,
`4` Korea, and all but US are capped at 25 km/h. The current commercial tools
(eMax bulletin March 2025, STUnlocker, eTuning) report that the latest E5000
firmware cannot change region over Bluetooth and route it through a wired SM-PCE
adapter or a firmware downgrade. Build .76 tests whether a tight-window BLE
burst can nonetheless land the write before the display resets.

### Build .76 changes

The region setter is re-enabled under Advanced diagnostics, gated by the same
`canSetUS` prerequisites (verified session, exact D4.5.0/M4.4.8 pair, motor
authenticated, EU destination, no prior attempt). The transaction is
restructured so the authenticated mode-4 window holds only the `A0`→`A8` pair:
the `A4` lighting read and the salted restart-record save are moved before PC
mode entry (both are valid outside privileged mode). After the mode-4
completion the page fires the unchanged `00 16 A0 <lo> <hi> FF FF` and, on its
`A2`, the single `00 16 A8 01 01`, with no reads or delays between. It logs the
elapsed time from mode-4 completion to `A0` and to `A0` acceptance, and on
rejection it distinguishes a BLE link drop (watchdog reset) from a silent
in-session mode loss. At-most-once `A8`, immediate readback, mandatory mode
exit, and the separate power-cycle persistence check are unchanged. No firmware,
erase, bootloader, or downgrade command is reachable.

Still unverified on the bike: whether the tightened window beats the reset;
whether PC-mode entry deterministically triggers the display reset (if it does,
the burst may still lose, which itself is the decisive next data point); and
persistence plus the actual assistance-speed change after a physical power cycle.

## Build .76 live result and .77 pipelined burst

The 2026-09-14 bike run on build .76 completed session authentication, SC-E7000
identification, the EU baseline, motor authentication with the `E8`/`EA` unlock,
PC mode 1 completion on wireless slot `0D`, and PC mode 4 completion. `A0` was
then rejected `A3 3A` about 74 ms after the mode-4 completion, **with the BLE
link still up** — no disconnect and no display reset this run.

Because the framing is verified correct (offset+4 = the leading `0`), the `A0`
handler's only other gate — active PC mode 4/5 — was not satisfied: the motor's
PC mode was cleared within roughly 55 ms of the grant while still connected.
This **refutes the build-76 hypothesis** that the display's watchdog reset is
what drops the mode; there was no reset here. The evidence instead points to the
SC-E7000 continuously owning the motor's single global PC-mode byte over the
shared internal bus and reclaiming it within one of its own poll cycles (tens of
ms), fast enough that the first BLE command after the grant is already too late.
This matches the commercial tools' position that the latest E5000 firmware
cannot change region over BLE, and it contradicts the earlier analyst claim that
a stable session does not clobber the mode.

Build .77 makes the best remaining phone-only attempt:

1. **Pipeline `A0` then `A8`** back-to-back, waiting only for `A0`'s ATT
   write-response, not the motor's `A0` notification, so both land within one
   BLE round-trip. Sending `A8` without a confirmed `A0` accept is harmless: with
   no staged flag the motor returns `3A` and nothing changes.
2. **Retry the mode-4 → burst cycle** up to four times per run (`usBurstAttempts`)
   to sample the display's poll phase, stopping on a US readback. Each attempt
   logs the `A0`/`A8` reply and its timing relative to the mode-4 completion.

If .77 also fails across its samples, the live PC-mode window is provably shorter
than a single BLE command round-trip and phone-only region-set is not achievable
on D4.5.0. The reliable paths are then the wired SM-PCE adapter (writes
destination=US directly, no downgrade) or a firmware downgrade.

## Build .77 live result: phone-only conclusively ruled out

The 2026-09-14 run drove four grant-and-burst cycles, all identical: PC mode 1
and PC mode 4 completed each time, then `A0` was rejected `A3 3A` at **59, 67,
63, and 59 ms** after the mode-4 completion (the pipelined `A8` returned `AB` at
134–212 ms, moot). Region stayed EU on every cycle.

The PC-mode window is therefore consistently shorter than the first BLE
command's round-trip (~60 ms) and is **deterministic across samples, not
phase-dependent**. Pipelining and retries cannot help, because `A0` itself
cannot land before the SC-E7000 reclaims the motor's global PC-mode state. This
**conclusively rules out phone-only region-set on D4.5.0** over the SC-E7000
bridge. The reliable paths are the wired SM-PCE adapter (E-TUBE Professional
writes destination=US directly, no firmware downgrade) or a firmware downgrade.
Do not iterate further phone-only builds; the ~60 ms reclaim is a bus-ownership
property of the display, not something a Web Bluetooth client can outrun.

## 2026-09-24 correction and build .78: the completion wait, not BLE itself, was ruled out

The build-.77 conclusion was too broad. Its four live failures conclusively
rule out sending the first drive-setting command **after receiving** the
mode-4 completion notification. They do not rule out queuing a setting command
after the fifth secure word's ATT write completes locally but **before waiting
for** that notification. That removes one complete BLE notification scheduling
leg from the critical path.

### Cross-version firmware findings

The public eTuning preparation archive was fetched again and verified as
SHA-256 `4dee4d75ee83c22e951114cbf57332709c15be637ec2a8171bd82f9345adb137`.
It contains the exact D4.3.0/M4.2.1 pair. Reverse engineering D4.3.0 found the
same structure as D4.5.0:

- `A0` handler `0x23b74` requires mode 4/5 and zero target, and sets the
  one-shot byte at `0x2000295f`;
- `A8` handler `0x23c48` requires mode 4/5 plus that byte, clears it, and
  persists the candidate record;
- PC-mode request `0x25ae8` and secure-word handler `0x25cfc` stage and promote
  mode 4/5 in the same way as D4.5.0.

Therefore the older supported firmware does not simply remove the gates. Its
different field behavior must come from state/timing elsewhere in the complete
system. Preparation remains a credible path because multiple commercial tools
support this exact pair, not because the `A8` handler is unconditional.

The D4.3 startup path resolves the fresh-boot question. Entry `0x2e214` calls
the complete two-record initializer table at `0x2ffcc`. Record one invokes
zeroing routine `0x2ff90` for `0x2530` bytes beginning at `0x20000490`. That
range ends at `0x200029c0`, so it explicitly clears the A8 gate at
`0x2000295f`. Record two invokes decompressor `0x294aa`; decoding its complete
`0x3f5`-byte input produces `0x56c` bytes at `0x2000000c..0x20000577`, ending
`0x23e7` bytes before the gate. The table dispatcher then reaches its end.

The static writer audit was widened beyond exact literals. The only direct
literal for `0x2000295f` remains the A0/A8 shared literal. Every located
reference based from `0x20002940` through `0x2000295e` accesses an exact byte,
and no call site of the image's generic byte-fill or byte-copy helper spans the
gate. This does not mathematically exclude an arbitrary computed pointer, but
it rules out the direct, nearby-base, startup-table, and identified standard
bulk-write paths. No other gate setter was found. Thus a cold boot does not
pre-arm direct A8; the commercial call sites prove packet shape but leave some
prior state or version-specific behavior unstated.

D4.5 is parallel: initializer table `0x3173c` first calls zeroing routine
`0x31700` for `0x25d0` bytes from `0x20000490`, covering its gate at
`0x200029fd`. Its second record calls the structurally identical decompressor
at `0x2c33a` and also ends at `0x20000578` exclusive. Neither initializer can
arm the gate.

### Two independent clients use direct A8

Current eTuning 3.0.7 was decompiled again. Its old-generation region action
constructs `00 16 A8 01 <destination>` directly in `p000/C1459qj.java`; its
`A0` method is used by the separate lighting-time UI. The independent
eMaxMobileApp 1.89 implementation does the same in
`DestinationSettingsActivity.java`, including `00 16 A8 01 01` for US, and
treats `AA` as success. Neither region path stages A0.

The current published compatibility evidence is also consistent:

- eMax's table lists E50X0 D4.2.1-D4.3.0 as Bluetooth-capable for destination
  changes and D4.4.2-D4.5.0 as not capable, with Bluetooth downgrade support:
  https://www.emax-tuning.com/eMax-possibilities.pdf
- eTuning advertises automatic downgrade for older E5000 systems and region
  changes without a physical device:
  https://etuning-app.com/compare/etuning-vs-emax-vs-stunlocker/
- STUnlocker lists Bluetooth destination change through E5000 D4.3.0 and a
  wired path for the latest firmware: https://www.stunlocker.com/
- Shimano's own recovery documentation warns that an interrupted wireless
  update may require E-TUBE Professional and SM-PCE recovery:
  https://bike.shimano.com/en-NA/support-and-service/faq/EPP0A.html

Community reports corroborate the outcome but are not protocol proof. E5000
owners report a US/32 km/h selection through eTuning over Bluetooth:
https://www.appwereld.nl/app/etuning-for-shimano-ebikes/1578877322 and
https://happyride.se/forum/threads/optimala-installningar-for-shimano-steps-e5000.3700908/

### Build .78 transaction

Build .78 keeps one A0 and one A8, with no retries. On the exact verified
D4.5.0/M4.4.8 EU baseline, after motor authentication and mode 1 it:

1. reads the current two-byte lighting time before privileged mode;
2. subscribes to the exact mode-4 completion routes and A0/A8 replies;
3. sends the mode-4 request and five secure words;
4. after the fifth secure write's ATT completion, immediately queues unchanged
   `00 16 A0 <low> <high> FF FF`, then queues one `00 16 A8 01 01` after only
   A0's local ATT completion, without awaiting A0's motor reply or mode-4
   completion;
5. requires exact mode-4/slot completion, A0 `A2`, and A8 `AA`;
6. freshly reads selector 1 and requires US; and
7. exits protected mode. A separate physical power cycle and new session are
   still required to establish persistence, and a ride is required to establish
   the assistance cutoff.

The secure handler promotes the active mode before it emits completion, so the
ordering is internally coherent and A0 supplies the statically required gate.
It may still fail if either ATT response is already too late. There is one
attempt only: no A0 or A8 retry, no inferred success from ATT completion, and
an uncertain transport outcome triggers a readback. Synthetic tests
deliberately withhold the mode-4 completion until both commands are observed,
proving the page does not wait for the losing notification round trip.
Synthetic acceptance does not prove bike acceptance.

A deeper eTuning call-chain audit found no hidden A0 inside the direct region
operation. `C1463qn.m6499J` is only a bare `2AFE` GATT write helper, and the
quick-action dispatcher schedules its optional region task before its other
optional setting tasks; its lighting-time action is separate. In the eMax APK,
the A0 packet constructors likewise occur in `LightActivity`, not in
`DestinationSettingsActivity`. This strengthens the direct-A8 observation but
does not explain the cold-zeroed gate: connection initialization,
version-specific system behavior, or an indirect memory write remains missing.

The current public field evidence also sharpens the downgrade tradeoff. On
2026-05-29 the eTuning author stated that the guided mobile app now integrates
the downgrade for older E5000/E5080 systems and supports 32 km/h over Bluetooth:
https://foro.e-mtb.es/index.php?topic=5382.375 . The same thread contains user
reports of wireless updates stopping at 98% or around 60% and requiring dealer
or SM-PCE02 restoration. Those anecdotes do not quantify the failure rate, but
they corroborate Shimano's official recovery warning and justify keeping the
firmware path behind a separate risk decision.

If a .78 run returns `A3 3A` or `AB 3A` and EU, the remaining
evidence-backed no-new-hardware path is the already implemented paired BLE
firmware workflow: install D4.3.0/M4.2.1, verify that exact pair, write and
persist US, then restore D4.5.0/M4.4.8. Build .45 already verified ordinary
bootloader entry and clean return on this bike; build .64 corrected the
first-use preflight to that path but has never been live-tested, and no firmware
image has ever been sent. Wireless flashing is materially riskier than build
.78: interruption can leave a unit needing the wired recovery hardware the user
wants to avoid. The hidden firmware UI must not be exposed until the .78 result
is known and the recovery/restore sequence is reviewed again.

## 2026-09-24 second correction and build .79: let the display own mode 4

The build-.78 timing hypothesis is superseded by a stronger finding in the
SC-E7000 4.1.0 display image. The prior phone-only experiments asked the motor
for mode 4 directly while the display still owned and maintained its normal
motor session. Their repeatable 59-74 ms loss demonstrates that ownership
collision. It does not establish that a mode requested and owned by the display
itself is equally short-lived.

### The local 0C handler supports protected modes

An independent address check corrected the earlier display-image base. Header
entry pointer `0x2c6f1` maps to file offset `0x1c6f1`, and literal table pointer
`0x21dfc` maps to the known mode-1 words at file offset `0x11dfc`; both require
load base `0x10000`, not the previously recorded `0x8000`. Earlier display
function labels were therefore `0x8000` too low. The bytes and control flow were
the same, but all display function addresses below use the corrected base.

The BLE/display-local handler at `0x236fc` accepts exactly input modes 0, 1, 4,
and 5:

- mode 0 calls `0x212ac(0)`, then cleanup helper `0x17cfa`, and replies
  `2C 00`;
- modes 1/4/5 call setup helper `0x17cc8`, then `0x212ac(mode)`, then helper
  `0x1f7a4`, and reply `2C 00`;
- any other mode replies `2C 01`.

`0x212ac` builds the display-to-motor category-32 mode request and, for nonzero
accepted modes, queues all five secure words. Its built-in tables are at
`0x21dfc` for mode 1, `0x21e08` for mode 4, and `0x21e14` for mode 5. This is
not speculative transport mapping: the supplied official eTuning capture sends
display command `00 0C 01`, receives `2C 00` on the display reply route, and
then receives motor completion `00 32 12 01 0D ...` about 61 ms later.

Thus `00 0C 04` is the missing BLE primitive: it asks the SC-E7000 itself to
establish mode 4 with the motor. Builds .76/.77 instead sent the corresponding
category-32 request and secure words from the phone, causing the display's own
state machine to overwrite their grant. Static analysis proves the changed
ownership path.

### Completion does not immediately exit the display-owned mode

The follow-up trace located the five-word response handler at `0x21d2c`.
After the fifth comparison succeeds it stores the requested mode from
`0x20003101` in the display connection state's active-mode byte at
`0x200001f8 + 0x0e`, clears the word counter, sets the completion flag at
offset `+0x1e`, stores the application slot at `+0x12`, and constructs the
observed category-32 opcode-`12` completion. These state writes occur before
the completion is queued. There is no call to `0x236fc(0)`, cleanup helper
`0x17cfa`/`0x1f76c`, or the mode-0 builder on this path. Within this
category-32 state cluster, the only direct writes to the active-mode byte are
the explicit mode-0 clear at `0x21cc6` and the successful five-word completion
store at `0x21d78`.

The two internal calls to `0x236fc(0)` are at `0x1f810` and `0x1f85a`. Both
are reached through the separate `0x1f7b8`/`0x1f836` connection/topology
maintenance state machine; the four call sites of `0x1f7b8` are connection
event handlers, not the secure-word completion handler. The local nonzero-mode
path also calls `0x1f7a4`, which clears bytes `+0x06`, `+0x04`, `+0x05`, and
`+0x03` in topology state at `0x20002fc8`. The periodic tick at `0x1f6f0`
decrements the timer but calls exit state machine `0x1f836` only if byte
`+0x06` equals one. It is therefore disarmed after the display-owned request;
a timer alone cannot produce the 59--74 ms reclaim observed when the phone
owned mode 4. A fresh connection/topology event through `0x1f7b8` can set the
trigger again, so this does not prove an unlimited mode-4 lifetime.

A whole-image direct-`BL` scan narrows that remaining event caveat. The only
references to re-arm handler `0x1f7b8` are `0x17820`, `0x178a6`, `0x17b6c`,
and `0x18352`; the only references to exit machine `0x1f836` are the periodic
gate at `0x1f704` and the re-arm handler at `0x1f7f0`. The only direct
references to local mode handler `0x236fc` are the normal local-command
dispatcher at `0x16210` and the two maintenance mode-0 calls. None is in the
mode-completion or raw drive-command forwarding path. This does not prove that
an independent connection event cannot occur, but it rules out another hidden
direct caller elsewhere in this exact image.

This rules out the specific concern that the SC-E7000 reports success and
immediately or periodically exits its own requested mode without a new event.
It does not prove that a later topology event cannot end the mode before the
next BLE command, nor that D4.5.0 will accept A0. Build .79 identified the
motor-side A0 gate after an internally recorded display-owned completion, not
whether the completion handler or an already-running timer revokes the grant;
build .80 below retains that question while selecting the stronger mode-5
client precedent.

The next BLE drive command does not synchronously re-arm or exit this state
machine. The generic enqueue at `0x2bf74` reaches selector `0x2dbb2`; staging
type `0x10` takes its full-copy branch to `0x2d7c4`. None of those bounded call
graphs calls `0x1f7b8`, `0x1f836`, `0x236fc`, `0x212ac`, `0x17cfa`, or
`0x1f76c`. Consequently receipt of the build-.79 A0 cannot cancel mode 4 before
the packet is enqueued. This is still bounded static evidence: an independent
asynchronous topology event could occur after enqueue, and motor acceptance is
unverified.

The read-only `tools/inspect_display_pc_mode.py` verifier pins the exact private
image fingerprint and reproduces the mode tables, bounded local/completion and
drive-forward call graphs, topology-maintenance gate, and state-write ordering
without emitting vendor bytes.

### Negative audit of other historical setup commands

Historical eTuning 1.0.32 was decompiled to test whether its connection flow
contained another hidden gate setter. Its destination button still sends
direct `00 16 A8 01 <destination>` and no A0. It uses display-local `0C 01`,
but no `0C 04`/`0C 05` call site was found. Raw/fallback decompilation confirms
the complete `RegionActivity.writeClick` bytecode constructs that one five-byte
A8 packet and performs one `2AFE` write; its `onCreate` helper only checks the
firmware version and can show a warning. A complete eMaxMobileApp 1.89 source
audit is parallel: inventory sends local `0C 01`, destination writes direct A8,
and no local mode-4/5 command was found. Its connection command
`00 32 B4 00` is read-only: D4.3 handler `0x215b4` calls `0x2453a`, which loads
the dword at `0x2000276c` and returns a B6 response. D4.5 is parallel at
`0x22c40`/`0x25c6e`, loading `0x200027e8`. The display-local `00 0D 00`
command is also a read-only status query at `0x23746`. Neither explains or arms
the A8 one-shot gate.

These negative findings preserve the static motor conclusion: A0 remains the
only identified setter of the cold-zeroed A8 gate. The new result changes how
mode 4 should be established, not the required A0/A8 semantics.

### Current commercial-client diffs expose no second privilege path

Two additional current/historical release comparisons were performed on
2026-09-24, with all third-party packages kept outside the repository.

The eTuning 2.0.8 release note says it fixed a firmware-specific E5000 problem
that prevented assistance parameters from being saved. A direct comparison
with 2.0.7 shows that this is not a destination or PC-mode change. Both versions'
assistance worker writes the same ordinary category-16 opcode-`98` records,
`00 16 98 <mode> <assist-le16> <torque> <power-le16>`, with 750 ms between
changed modes. Both source trees contain display-local `00 0C 01`, but neither
contains `00 0C 04` or `00 0C 05`; their category-32 literal inventories are
also unchanged. Therefore the public 2.0.8 E5000 fix does not provide a second
way to enter privileged destination-write mode. The inspected 3.0.7 manifest
is version code 97, matching the current public release listing as of this
check. Release history:
https://apkpure.net/tw/etuning-for-shimano-steps/eTuning.for.shimnao.steps/versions .

STUnlocker Android 1.21.157 provides a second independent implementation. Its
obfuscated strings were decoded from the package's own native string routine
and the complete decoded literal inventory was searched. The connection flow
performs the normal BLE authentication and display access sequence, including
display-local `00 0C 01`. The market worker then selects motor slot 0, performs
the model-dependent motor authentication when required, writes exactly
`00 16 A8 01 <destination>`, and reads `00 16 AC 01`. Its lighting worker labels
`00 16 A0 <low> <high> FF FF` as the lighting-time setter. The complete decoded
inventory contains one `000C01`, one `0016A801`, the `0016A0` constructor, and
no `000C04` or `000C05`. Thus STUnlocker independently confirms both category-16
packet roles but exposes no alternate D4.5 mode grant. This is consistent with
its published boundary of Bluetooth destination changes through E5000 D4.3.0
and a wired route for the latest firmware: https://www.stunlocker.com/ .

An authentic intermediate package, STUnlocker 1.20.153, was then recovered.
Its SHA-256 is
`0965e31e6db74f9d19b410bcba9bb04ad5b3a710638f6bdad6ab6d9935c71af9`;
its SHA-1 matches APKFab's version page, and its signing certificate is
byte-for-byte the same certificate used by 1.21.157. Decoding all 3,333 unique
literal values and tracing its market worker produces the same result: select
slot 0, run D8/AES/E8 security access when required, send direct
`00 16 A8 01 <destination>`, optionally update assistance speed, and read
`00 16 AC 01`. Its inventory also contains local `000C01`, but no `000C04` or
`000C05`. This shows the visible direct-A8 design was already present in the
January 2025 package; it still does not establish what the unavailable
1.15.120-era client did.

Together these audits rule out another visible sequence in the public packages
examined. They do not explain reported success on older supported firmware,
which could depend on transient state created during preparation/update or on
an unexamined historical/private workflow. Build .79's display-owned
`00 0C 04` step remains the only identified software-only way to supply
D4.5.0's required mode 4/5 before the unchanged A0 and A8 halves of the
settings record.

The current STUnlocker package's embedded v1.20 manual independently gives the
same E5000 boundary: Market Setting is supported through D4.3.0, while standard
features extend through D4.5.0. Its decoded "Use Security Access" path is not a
second PC-mode mechanism; it performs the already tested D8 challenge/AES
response and E8 release sequence before direct A8. Public archive metadata
lists historical Android releases back to 1.7.38, but the checked APKPure,
Uptodown, APKCombo, APKTurbo and Aptoide routes did not yield an authentic
pre-1.20 artifact. Uptodown's current client API was also reconstructed from
its native HMAC routine, but the public API host returned `410 Gone` before an
authenticated archive lookup could complete. In particular, versioned APKTurbo
URLs displayed the requested old version only in the page title while their
structured data and download target still pointed to 1.20.153. This is a
bounded artifact-availability result, not evidence that an old client lacked
another sequence.

### The category-16 setters assemble one 11-byte record

The exact D4.5.0 handlers also sharpen the mutation boundary. Category-16 A0
at `0x252a8` requires mode 4/5 and selector zero, copies five bytes to the
pending buffer at `0x20002548`, sets the volatile one-shot byte
`0x200029fd`, and emits A2. Category-16 A8 at `0x2537c` requires the same mode
and that flag equal to one, copies the next six bytes to adjacent address
`0x2000254d`, clears the flag, and calls `0x25516`. That helper compares the
assembled 11-byte pending buffer against the current record at `0x2000253c`
and copies it into the record buffer only on its changed-record path. This
explains why preserving the freshly read A0/lighting bytes is important: A0
and A8 form two halves of a single settings record, and only the destination
half should differ.

An exact mode-4/5-only read-only probe was sought before A0. The other direct
mode-4/5 check is category-32 A0 at `0x24d50`, not the category-16 A0 above;
its path dispatches the supplied byte through `0x1c434`/`0x246ec` and a
separate record/update operation. It is therefore not safe as a status probe.
Category-32 B4 and display-local 0D are read-only, but neither proves that the
motor remains specifically in mode 4/5. The unchanged category-16 A0 is still
the narrowest available gate before the destination commit.

### Build .79 transaction and safety boundaries

On the exact verified D4.5.0/M4.4.8 EU baseline, build .79:

1. reads selector 1 and the current two-byte lighting value before privileged
   mode;
2. stores the salted same-device restart expectation;
3. sends `00 0C 04` on display characteristic 2AFA;
4. requires both display acknowledgement `2C 00` and exact motor completion
   `00 32 12 04 <wireless-slot>` on an observed notification route;
5. sends unchanged `00 16 A0 <low> <high> FF FF` once and requires A2;
6. only then sends `00 16 A8 01 01` once and requires AA;
7. freshly reads destination selector 1 and requires US; and
8. exits via display-local `00 0C 00`, requiring its acknowledgement and exact
   motor mode-0 completion.

It sends no phone-originated category-32 mode request or secure words, no
firmware data, no A8 after an A0 rejection, and no A0/A8 retry. An uncertain
destination-write transport result triggers readback rather than another
write. The page records mode-4 completion-to-A0-enqueue and
completion-to-A2-acceptance intervals for the one allowed run. Synthetic tests
cover the exact packet order, reply routing, timing-log presence, wrong
mode/slot filtering, rejection paths, exit attempts, and at-most-once
properties. They do not prove bike acceptance.

The next meaningful live evidence is therefore a single build-.79 run, not a
build-.78 timing run. Success requires `2C 00`, exact mode-4/slot completion,
A2, AA, and fresh US readback; persistence still requires a physical power
cycle and a new session, and higher assistance speed still requires a safe ride
test. If the motor returns `A3 3A` or `AB 3A` despite exact display-owned mode
completion, do not repeat the command. The paired BLE D4.3.0/M4.2.1 preparation
workflow remains the higher-risk no-new-hardware fallback.

### Fresh public-code sweep does not expose another destination path

A 2026-09-24 search of current public repositories and exact command strings
found no independent implementation of the E50X0 destination transaction or
the SC-E7000 local mode-4/5 operation. This is bounded negative evidence, not a
claim that unpublished code does not exist.

- Reven's [`etubeapi`](https://github.com/reven-project/etubeapi) provides the
  firmware catalog, and
  [`reven-plugin-etube`](https://github.com/reven-project/reven-plugin-etube)
  provides firmware header/decrypt/encrypt helpers. Neither contains a BLE
  settings client or destination transaction.
- [`BikeBridge`](https://github.com/Shiho-Patch/BikeBridge) independently names
  the Shimano `2AFA` command and `2AF9` response characteristics and implements
  ordinary display settings. Its Shimano constants leave `DUUnitDataLink` and
  `DestinationType` as comments; there is no destination setter or local
  `0C 04`/`0C 05` sequence in the current tree.
- The
  [`Shimano-Steps-Simulator-BT-E6000`](https://github.com/ottelo9/Shimano-Steps-Simulator-BT-E6000)
  project documents battery UART authentication and simulation. It is a
  different transport/subsystem and provides no E-Tube BLE destination path.
- The public
  [E-Tube desktop patching guide](https://forums.electricbikereview.com/threads/derestricting-a-shimano-steps-e-bike.54485/)
  still describes the wired `DUUnitDataLink.SetDestination(slot, 1, 1)` route
  and serial-derived regulation authentication. Its command details agree with
  the already inspected E-TUBE 3.4.5 assemblies, but it requires SM-PCE01/02
  and adds no phone-only initialization step.

The sweep therefore found corroboration for the known command surface, not a
safer shortcut.

## 2026-09-24 third correction and build .80: match Shimano's destination mode

Build .79 correctly changed ownership, but its choice of protected mode 4 was
not the closest available client precedent. Rechecking the E-TUBE 3.4.5 desktop
control flow shows that `SetInspectionModeOtherPanel` contains the actual
factory and OEM destination buttons, both calling
`DUUnitDataLink.SetDestination`. The surrounding inspection workflow enters
protected PC-link mode 5. That is direct evidence for the mode in which Shimano
exposes destination writes, whereas mode 4 is only known to be accepted by the
same D4.5 motor gates.

This does not undo the display-firmware result. The SC-E7000 local handler
accepts both 4 and 5, calls the same setup and post-request helpers for either,
and selects the corresponding built-in secure table. The completion handler
stores the requested mode generically before announcing success. The D4.5 A0
and A8 handlers also accept either 4 or 5. Therefore display-owned mode 5 keeps
the ownership fix while matching Shimano's known destination-setting context
more closely.

Local build .80 changes only that selection and its exact completion gate:

1. send display-local `00 0C 05`;
2. require `2C 00` and exact motor completion
   `00 32 12 05 <wireless-slot>`;
3. send one unchanged category-16 A0 and require A2;
4. send at most one OEM-selector US A8 and require AA plus fresh US readback;
5. exit through display-local `00 0C 00`; and
6. require a separate post-power-cycle readback before calling the value
   persistent.

All identity, EU-baseline, motor-authentication, durable restart-record,
at-most-once, no-retry, readback, and exit guards are unchanged. Build .79 was
never published or tested on the bike. Build .80 has synthetic coverage only;
the last verified destination remains EU, and no higher assistance cutoff has
been measured.

## 2026-09-24 fourth correction: the A0 gate predates D4.3

The remaining client/firmware contradiction was tested against the exact
DUE5000 D4.1.0 image distributed with E-TUBE Professional 3.4.5. That pairing
is historically important because the same desktop release contains the
inspection panel whose factory and OEM destination buttons call
`DUUnitDataLink.SetDestination` directly.

D4.1.0 is not an ungated predecessor. Its category-16 A0 handler at `0x240e0`
requires active PC mode 4 or 5 and selector zero, copies the five-byte first
half of the pending record to `0x200028d0`, sets the byte at `0x20002d72`, and
returns A2. Its A8 handler at `0x241b0` requires mode 4/5 and that byte equal to
one, copies the adjacent six-byte second half to `0x200028d5`, clears the gate,
and reaches record helper `0x24356`. This is the same state machine already
verified in D4.3.0 and D4.5.0.

Cold boot does not supply the missing state. D4.1 header entry `0x2ebb9` calls
runtime initialization at `0x30b20`; the first record in table `0x30bc8`
resolves to zero routine `0x30b8c` and clears `0x2520` bytes from
`0x200008b0`, covering the gate. The exact gate address occurs as a literal
only once, in the pool shared by A0 and A8. This is bounded static negative
evidence, not proof against arbitrary computed pointers, but it rules out an
already-armed cold-start gate and a firmware-version explanation based on A8
becoming gated only after D4.1.

A complete managed caller pass found only two `SetDestination` callers in the
3.4.5 executable: the factory and OEM destination buttons. The only
`SetLightingTime` callers are its separate button and the drive-unit setup
worker. No hidden A0 call sits immediately inside either destination button.
The old desktop UI therefore remains evidence for mode 5 and A8 arguments, not
for a complete self-contained wire sequence. Some earlier setup state,
operator sequence, display behavior, or an unobserved indirect path must
explain the direct call.

The panel lifecycle and general apply worker were then checked. `DoLoad` and
`ResetDisplay` only build the inspection controls and unit lists. In the
ordinary drive-unit settings worker, `SetTireCircumference` occurs at IL
offset `0x0182`; the only `SetLightingTime` call is later at `0x0481` and only
when the lighting value changed. Therefore the public desktop patch that adds
`SetDestination` inside `SetTireCircumference` executes A8 before this possible
A0. Its reported wired success cannot be explained by a hidden preceding
lighting setter in the published call chain.

This correction strengthens rather than changes build .80. Display-owned mode
5 matches Shimano's destination context, while replaying the freshly read,
unchanged A0 half explicitly satisfies the one-shot gate present in all three
verified motor versions. The build number and live-test plan remain unchanged.
`tools/inspect_motor_destination.py` makes the three-version result
reproducible from exact private images without dumping or committing them.

## 2026-09-24 fifth correction: old display firmware has the same owned mode

The exact SC-E7000 4.0.6 image bundled with E-TUBE Professional 3.4.5 was
compared against the bike's 4.1.0 image to test whether historical BLE success
depended on an older bridge lifecycle. It does not expose such a shortcut.

SC-E7000 4.0.6 local handler `0x22d74` accepts modes 0, 1, 4, and 5. Its three
five-word secure tables at `0x21474`, `0x21480`, and `0x2148c` are byte-for-byte
identical to the corresponding 4.1.0 tables. Completion handler `0x213a4`
stores the requested mode, completed-session flag, and application slot before
announcing completion and has no immediate mode-0 or cleanup call. Its
post-request helper clears the periodic maintenance trigger, while the periodic
tick invokes the exit machine only when a later event has set that trigger.
Whole-image direct references to the local handler, event-rearm handler, and
exit machine have the same bounded topology as 4.1.0.

The one relevant implementation difference makes current 4.1.0 more fully
reset, not less capable: its post-request helper additionally clears topology
phase byte `+0x03`; 4.0.6 clears the same trigger and phase `+0x04/+0x05` fields
but not `+0x03`. There is therefore no static reason to add a display downgrade
to the candidate workflow. It would add wireless-update risk without arming
the motor's separate destination gate.

`tools/compare_display_pc_mode.py` verifies the two exact fingerprints, secure
table hashes, state-write signatures, call graphs, and whole-image direct-call
sets. This historical negative result leaves build .80 unchanged and further
concentrates the next experiment on current display-owned mode 5 plus A0/A8.

## 2026-09-24 sixth correction: PC-mode completion cannot substitute for A0

The apparent direct-A8 desktop path left one narrow alternative: perhaps the
fifth secure word that promotes protected mode 4 or 5 also arms the nearby
destination gate. Exact-image handler checks now rule that out for D4.1.0,
D4.3.0, and D4.5.0.

Each version keeps the application slot, active mode, requested mode, and
secure-word count in four consecutive bytes. The destination gate is a
separate byte two positions beyond the count. The PC-mode request handlers at
`0x26098`, `0x25ae8`, and `0x2721c` stage requested mode and slot and reset the
counter. The secure-word handlers at `0x262ac`, `0x25cfc`, and `0x27430`
promote requested mode after the fifth matching word and reset the counter.
Their verified direct state writes do not set the destination gate. The three
mode-1/4/5 secure tables are also byte-identical across all motor versions and
match the paired display tables; mode 5 therefore supplies context and
ownership, not an implicit region-write grant.

`tools/inspect_motor_destination.py` now machine-checks those handler
dispatches, request and promotion signatures, tables, state layout, and the
already verified A0/A8 and cold-start invariants against exact fingerprints.
All three private images pass; a modified sample is rejected. This remains
bounded static evidence and does not prove bike acceptance. It does show that
build .80's unchanged A0 is required rather than merely defensive, and leaves
the unexplained old direct-A8 client behavior attributable to prior or retained
staging, an unobserved indirect path, or adapter-specific state—not mode-5
completion alone.

## 2026-09-24 seventh correction and build .81: refresh mode after A0

The separated PC-mode and destination-gate state makes a safer transaction
possible. Once A0 returns A2, its candidate record and one-shot gate survive
ordinary PC-mode changes; only A8 consumes the gate, while cold startup clears
it. The SC-E7000 local `0C` handler also does not short-circuit a request for
the already active mode. Each accepted mode-5 request stages mode 5 again and
queues a fresh motor request plus all five secure words.

Build .81 therefore keeps both setting writes once-only but requires two
display-owned handshakes:

1. require local `00 0C 05` acknowledgement and exact motor mode-5 completion;
2. send the unchanged A0 once and require A2;
3. send local `00 0C 05` again and require a second exact display and motor
   completion; and
4. only then send one OEM US A8, require AA and fresh US readback, and exit
   through local mode 0.

This removes a remaining avoidable race between A2 and A8: even if an
independent topology event reclaimed motor mode after A0, the second handshake
restores it without clearing the accepted A0 gate. The exact display image
shows that same-mode requests are forwarded again, and the exact motor images
show that mode request/promotion does not touch either the gate or pending
record. If the second handshake fails, build .81 withholds A8, disconnects,
and tells the operator to power-cycle before using another setting tool because
the A0 gate may remain armed. Synthetic fault tests cover all three second-
handshake failures and prove one A0, zero A8, verified exit attempt, and the
power-cycle warning. No bike acceptance, persistence, or higher cutoff has yet
been demonstrated.

## 2026-09-24 eighth correction and build .82: no-retry survives reload

Build .81's protocol ordering was sound, but its no-retry guarantee was only
held in the live JavaScript session. The command verification record used
`sessionStorage`, and `canSetUS` blocked only an unverified record. After a
non-US reconnect result became verified, a page reload and new connection could
therefore make the setter eligible again. An A0-only interruption also needed
stronger persistence because its gate can remain armed until bike power-off.

Build .82 keeps the exact build-.81 packet sequence and changes the attempt
journal. Before privileged mode it durably stores only a random salt, a salted
hash binding the browser-selected Bluetooth device, the exact expected motor
pair and destination, and a phase marker. It persists `a0-started` before A0
enqueue and `a8-started` before A8 enqueue. Any command-attempt record is now
terminal for the setter across reloads, including verified `us` and `not-us`
outcomes. The read-only bike check remains available. A record that reached A0
without A8 produces an explicit physical-power-cycle warning before any other
setting tool is used.

No passkey, raw device identifier, serial number, packet capture, or firmware
content is stored. Synthetic tests reload the page after A0-only failures and
after a verified non-US result and prove that `canSetUS` remains false. Build
.82 remains unpublished and has no bike result.

## 2026-09-24 ninth correction: the desktop host does not hide the A0 gate

The remaining wired-client ambiguity was followed through E-TUBE Professional
3.4.5's managed serial boundary. `UnitCommandSetting.Make` only stores the
slot, group, opcode, and parameters. `SendUnitCommandData` and
`SendReceiveUnitCommand` pass that payload through
`SendDCASRawPacketCommand`/`WriteData` with control byte `0x48`.
`CreateWriteData` adds the control byte and two's-complement FCS, and
`Common.CreateFrame` performs framing and escaping. The protected-mode start
and five secure words are ordinary category-32 commands through the same path.
There is no opcode-specific hook that inserts A0 before A8 or rewrites the
destination call.

The independent 2018 `freeMax.exe` client provides a second control. It opens
PCE1/BCR2 serial directly and writes complete logical DCAS frames byte by byte,
escaping only logical `BB` and `BD`. Its assistance workflow includes ordinary
frames such as `48 00 32 10 01 0B 00 00 6A BB`,
`48 00 32 B4 00 D2 BB`, and direct category-16 `9C` setting writes. It does not
invoke E-TUBE's managed transport or a host-side command expander. This makes
a general adapter command-synthesis layer unlikely, although it cannot exclude
a narrow firmware special case for A8.

The bundled PCE1 3.1.3 and PCE02 3.0.4 update files were also traced through
the updater. The host reads each file as raw bytes, chunks it, optionally
run-length-compresses an individual transport packet, pads only beyond EOF,
and sends it; PCE1 startup supplies write address `00 40 00`. No decrypt or
relocation transform precedes the device. Raw scans and bounded M16C, RL78,
8051, MSP430, H8, CR16, and V850 attempts did not produce a coherent program,
so the adapter CPU and any opcode-specific path remain unresolved rather than
negatively proved.

Finally, exact UI worker order strengthens the contradiction. The published
wired patch injects `SetDestination(slot, 1, 1)` inside
`SetTireCircumference`, reached at IL `0x0182`. The worker's only
`SetLightingTime` call is later at `0x0481` and conditional on a changed value.
Thus its shown call order sends A8 before any possible A0; it cannot itself
explain the one-shot gate verified in D4.1, D4.3, and D4.5. The published
outcome may depend on retained state, omitted initialization, a different
context, or narrow adapter behavior, but it is not a complete causal trace.

This correction does not change build .82. Display-owned mode 5, one unchanged
A0, a fresh display-owned mode-5 completion, one A8, readback, and local mode-0
exit remain the narrowest no-new-hardware experiment. Build .82 is still local,
unpublished, and untested on the bike; the last verified destination remains
EU and no higher assistance cutoff has been measured. The complete bounded
transport evidence and exact fingerprints are in
`docs/evidence/pce-transport-analysis.md` and `ASSETS.md`.

## 2026-09-24 tenth correction: exact PCE02 does not transform A8

The ninth correction left one adapter-sized uncertainty. The exact bundled
SM-PCE02 3.0.4 update file is now decoded as a coherent little-endian ARM Thumb
image at base `0x10000`, with vector-like stack/reset values `0x20000868` and
`0x1aba1`. Its logical serial parser reverses `BD` escaping and dispatches
control `0x48` to function `0x166e2`.

That handler strips only the serial control and application-slot bytes, then
copies all group/opcode/parameter bytes unchanged into this send chain:

```text
0x166e2 -> 0x1873c -> 0x19206 -> 0x1b8a4 -> 0x1beec -> 0x1e15c
```

The chain's only opcode-aware branch, `0x1bc42`, checks 14 group/opcode pairs
from a startup-initialized table at RAM `0x2000000c`. The exact table is
`30/2A`, `01/18`, `01/1A`, `01/2C`, `01/2E`, `01/0C`, `01/0E`, `01/24`,
`01/26`, `01/5C`, `01/5E`, `02/08`, `01/00`, and `01/02`. Neither `16/A0`
nor `16/A8` is present. The A8 command therefore takes `0x1e15c`'s ordinary
length-based bus packetizer. This exact PCE02 firmware does not inject A0 or
rewrite A8.

`tools/inspect_pce02_transport.py` verifies the whole-image fingerprint,
vector, initializer record, 14-pair table, and exact function-slice hashes; its
in-memory modified-sample test fails closed. PCE1's running image remains
undecoded, and this
is static evidence rather than a live PCE trace. However, the public wired
guide explicitly allowed PCE02, so a PCE1-only special case cannot explain its
claimed general recipe. The wired outcome must depend on retained state, an
omitted command, a different motor/firmware context, or some other unreported
workflow condition—not a PCE02 A8 transform.

This correction leaves build .82 as the narrowest no-new-hardware experiment:
display-owned mode 5, one unchanged A0, a fresh complete display-owned mode-5
handshake, one A8, readback, and mode-0 exit. It remains local, unpublished,
and untested on the bike; the last verified destination remains EU and no
higher assistance cutoff has been measured.

## 2026-09-24 eleventh correction: PCE1 MCU identified, package still undecoded

The public SM-PCE1 top-board photograph shows a 32-pin Renesas device whose
marking is consistent with `D78F1807`. Renesas' instruction manual and device
list identify µPD78F1807 as a 64-KiB 78K0R/FB3 part. E-TUBE starts PCE1 update
writes at `0x4000`, which is consistent with a resident 16-KiB bootloader and
an application region above it. The earlier bounded attempts to decode the
file as M16C, RL78, 8051, MSP430, H8, CR16, or V850 are therefore discarded;
78K0R is distinct from both RL78 and the older 78K0 ISA.

That identification does not turn the exact PCE1 update file into a flat
program. The 3.0.2 and 3.1.3 files are equal-sized structured packages with an
offset-like leading table and explicit version records (`05 30 02 00` and
`05 31 03 00`). Apparent entry offsets do not decode as plausible 78K0R code.
The managed updater passes file bytes directly, apart from optional per-packet
RLE, so the resident PCE1 bootloader must interpret the package layout or
perform the remaining transformation. Plaintext searches for `16 A0` or
`16 A8` in those package bytes are not probative. The correct bounded statement
is: the PCE1 CPU family is identified, while its package layout, running image,
and opcode behavior remain undecoded.

This does not reopen adapter magic as the explanation for the published wired
recipe. The guide explicitly allowed PCE02, and the exact PCE02 3.0.4 running
image demonstrably forwards `16 A8` unchanged without synthesizing A0. A
PCE1-only implementation therefore cannot explain a recipe claimed for both
adapters. Build .82 and the paired BLE preparation fallback remain unchanged;
neither has a new live-bike result.

## 2026-09-24 twelfth correction and build .83: exact current-firmware patch branch

The commercial paired-downgrade route was rechecked as a causal mechanism,
rather than accepted from the client policy alone. All 27 located instructions
that load the active PC-mode byte in exact D4.3.0 have corresponding D4.5.0
references at a fixed `+0x1734` code relocation, with identical local
instruction windows. The mode-request handler, fifth-secure-word promotion,
mode 1/4/5 tables, A0-created one-shot gate, A8 gate consumption, and cold-boot
clearing are also equivalent. A preparation workflow may create some other
transient, but “reboot D4.3 and send direct A8” is not by itself a complete
motor-side recipe for this topology.

A bounded current-firmware derivative is now more causally direct. In the exact
unwrapped D4.5.0 image, the final `BNE error` after A0's active-mode comparisons
is at runtime `0x252c8` (file `0x152c8`), and the corresponding A8 branch is at
runtime `0x25394` (file `0x15394`). Replacing only those two Thumb branches with
`00 BF` NOPs lets the existing handlers proceed independently of the contested
global PC-mode byte. It does not bypass A0's zero target, candidate copy, or
one-shot gate, nor A8's gate check/consumption or persistent-record helper. A
fifth changed byte marks the native D header 4.5.0.1, allowing reconnect
readback to distinguish the experiment from restored stock 4.5.0.0.

The exact source image is 138,072 bytes with SHA-256
`44806bd54aedff95a88bb73fafe0f0581297f2f67b2ea35545cea012899d90bb`.
The deterministic five-byte derivative has SHA-256
`0dbbb3d3b634d831d8450d2758d953502bfdc7f16ac8640a4e3ca46fff3fff18`
and whole-image byte-sum `0x49`, versus source `0xBD`.
`tools/patch_motor_pc_mode.py` and the unwired page helper both require the
exact source fingerprint and original bytes and validate the exact output.
Synthetic tests use generated bytes, not a committed vendor image.

The audited update path's raw family/header checks, 64-byte block sums, block
indices, and final whole-image sum make modified-image acceptance plausible.
The official container AES-CBC/MD5 checks are host-side wrapper checks, and no
asymmetric signature or second raw-image authenticator was found. This is not
bootability proof: a resident-bootloader or application-startup integrity check,
an interruption, or a bad image could remove BLE recovery and require wired
hardware.

Build .83 therefore leaves build .82's live command sequence unchanged and
adds only the fail-closed, unwired patch constructor. There is no UI caller,
paired-transfer coordinator, or patched-image recovery journal, and no image
has been sent to the bike. Before any exposure, the implementation must require
the exact stock D4.5.0/M4.4.8 restoration pair, derive D4.5.0.1 in memory,
transfer a complete compatible pair, reset into a different BLE session, prove
native 4.5.0.1/M4.4.8 readback before one A0/A8 transaction, then restore and
prove native 4.5.0.0/M4.4.8 plus persistent US. The current verified state
remains stock D4.5.0/M4.4.8 at EU, with no measured higher cutoff.

## 2026-09-24 thirteenth correction and build .84: exact pair derivation and startup audit

Build .84 leaves build .82's live A0/A8 transaction unchanged and advances only
the offline firmware branch. `loadPatchedD450FirmwarePair` accepts the exact
reviewed stock D4.5.0/M4.4.8 restoration files, applies the five-byte D patch in
memory, keeps M4.4.8 byte-for-byte unchanged, rechecks the D4.5.0.1/M4.4.8 peer
requirements, and returns `source: pc-mode-patch, installable: false`. A
synthetic exact-hash test covers the pair boundary. There is still no UI caller,
transfer authorization, patch-specific recovery journal, or live image write.

The exact application startup was then audited to narrow the modified-image
risk. The D4.1, D4.3, and D4.5 header entries each set the stack and call their
runtime initializer. That initializer executes exactly two table records—a RAM
zero routine and a 12-byte ROM-to-RAM copy—then calls `main`. For each exact
image, the declared image-size value occurs only at header offset `0x18`; the
computed image-end address and a direct pointer to the size field do not occur
anywhere in the raw image. The image tail is structured executable/data content
and contains no identified appended opaque signature block. A fresh D4.5
Ghidra import independently found nine reads of the version header and zero
references to the entry pointer, image-size field, or family field.

`tools/inspect_motor_image_integrity.py` machine-checks the three exact hashes,
header/entry/runtime/main calls, initializer records, whole-image size/end
literal absence, and structured tails. This materially reduces the likelihood
of an application-level whole-image self-check. It does not inspect the
resident motor bootloader, exclude computed addresses or an external checksum
record, or prove modified-image acceptance, successful boot, and BLE recovery.
The bootloader remains the decisive no-new-hardware risk. Build .84 is local,
unpublished, and untested on the bike; the last verified state remains stock
D4.5.0/M4.4.8 at EU with no measured higher cutoff.

## 2026-09-24 fourteenth correction and build .85: loader inventory and patch recovery lineage

The resident-loader uncertainty was narrowed using the exact E-TUBE Project
3.4.5 `etubedatalinks.dll` already fingerprinted in `ASSETS.md`. Its nested
`RenesasMicomCommandDefine.BootloaderCommandCodes` enum is a complete named
client inventory: START `21`, firmware version `22`, erase count `23`, write
address `24`, checksum `25`, clear checksum `26`, FINISH `27`, RESET `28`,
serial low/high `29`/`2A`, and bootloader version `41`, with normal/error and
query response codes `31`-`36`/`51`. There is no flash-read, range-read, dump,
signature, key, or authentication request in that exact enum or its one-helper-
per-command implementation.

The IL call chain independently confirms the raw write contract.
`Unit.UpdateRenesasFirmware` obtains `RenesasFirmwareFile.get_BinaryData` and
passes it to `EtubeDataLinksMain.UpdateRenesasFirmware`. That worker calls
START, then `SendRenesasFWData`, FINISH, and RESET. `SendRenesasFWData` sets the
write address, clears the partial sum, streams data packets, checks additive
byte-sums, and clears between windows. No separate signature or cryptographic
verification operation appears in this reviewed raw-write chain. The DAT
wrapper checks happen on the host before `get_BinaryData`; they are not a
second authenticator sent to the loader.

The eTuning 2.0.7, 2.0.8, and 3.0.7 decompilations were also enumerated for
every loader command constructor. They add current-generation setup `06`-`09`,
bank `0A`, identity/version queries `2E`-`30`, and data command `60`, but no
memory-read request. This is bounded negative evidence for the clients, not a
proof that the resident loader has no undocumented opcode. It does establish
that the reviewed BLE/software paths cannot first dump the resident loader or
make a recovery backup. `tools/inspect_etube_d_loader.py` now verifies the exact
assembly fingerprint, enum, command/reply helpers, and update call chain;
`docs/evidence/d-loader-acceptance-analysis.md` records the limits.

Build .85 uses that result to finish only the offline D4.5.0.1 workflow. It
keeps build .82's live display-owned mode-5/A0/mode-5/A8 transaction unchanged.
`transferPatchedD450Pair` accepts the exact stock restoration files, derives
the five-byte D image in memory through the exact-hash builder, retains M4.4.8
byte-for-byte, and invokes the existing complete M-then-D workers. The durable
journal now admits only the exact `pc-mode-patch` D4.5.0.1/M4.4.8 pair from a
stock D4.5.0/M4.4.8 EU baseline, and recovery reloads the stock files and
re-derives the same patch before replaying the complete pair.

After reset, `verifyPatchedD450FirmwareAfterReconnect` requires another BLE
session to report the same motor at D4.5.0.1/M4.4.8 and destination 0 before
the one-write transaction is eligible. The existing uncertain-write and
physical-power-cycle persistence gates now accept either the historical
preparation pair or the exact patch pair. Stock restoration from a patched
route is authorized only after the same journal proves D4.5.0.1/M4.4.8 at US
through a separate power-cycle readback; final restoration still requires
stock D4.5.0/M4.4.8 plus US. The generic UI planner treats a patch journal as
inspection-only, so no browser action can accidentally expose the branch.

`tests/motor_firmware_patch_workflow.cjs` uses generated bytes to prove exact
derivation, unchanged M, paired transfer ordering, complete-pair recovery
replay, the explicit version-marker gate, one destination mutation, persistence
lineage, and stock-restoration authorization. It also proves that the generic
restoration loader cannot start this route from the stock EU baseline. No
firmware or destination command was sent to the bike, no UI caller was added,
and the public Pages site remains build .77. The last verified bike state is
still stock D4.5.0/M4.4.8 at EU with no measured higher assistance cutoff.

This raises modified-image feasibility but does not close the decisive risk:
the resident loader may apply an implicit/external integrity policy, and an
accepted transfer whose application fails to boot may eliminate BLE recovery.
No software-only experiment is authorized until that risk is explicitly
accepted with the exact stock pair available and the possibility of later
wired recovery understood. The corrected M4.2.1 raw-image SHA-256 is
`10190fd78e6527908c0e43405184c414b612bc4becce9ca5483612665ced6b56`;
the prior `ASSETS.md` value was a transcription error, while the allowlist and
actual extracted file already used the correct digest.

## 2026-09-24 fifteenth correction: current eTuning stock-pair proof and dormant boot-patch path

The exact eTuning 3.0.7 base APK was traced from ZIP import through firmware
transfer to settle whether its modern preparation workflow depends on an
undisclosed patched E5000 image. `C0473Oa.m2065A` computes MD5; `m2079l`
constructs an obfuscated 18-member file allowlist; `m2086u` and the ZIP import
path require membership before an accepted DAT is placed in the private
firmware directory. The update workers unwrap those accepted files and pass
their binary results onward without an identified E5000 application patch.

The first two decoded allowlist entries exactly match the files in eTuning's
public `5000_430.zip`: `DUE5000-D.5.3.0.dat` is MD5
`6daee3c8de5ae0d4b77443e28c7bb758`, and
`DUE5000-M.5.2.1.dat` is MD5 `492d14c37c8ee2fd4a636ab416eea143`.
Their parsed headers and sizes remain D4.3.0.0 at 132,072 bytes and M4.2.1.0 at
116,320 bytes. Thus current eTuning 3.0.7 explicitly accepts the exact public,
stock preparation pair already modeled by the local workflow. The earlier
bounded statement that current client/server pairing remained unproved is
superseded at the client-import and file-identity layers; a server-only or
modified E5000 image is not required to pass this client check.

This does not prove wireless transfer on this bike, destination success,
persistence, or a higher cutoff. It also does not resolve the static paradox:
exact D4.3 still cold-clears the one-shot gate and requires A0 before A8, while
the commercial clients' visible destination action sends direct A8. Some
transient/system state or omitted live step remains. Nevertheless, the exact
stock pair plus current-client acceptance moves the complete paired BLE
downgrade above the modified-D4.5.0.1 route on the no-hardware experiment
ladder. `tools/inspect_etuning_firmware_policy.py` reproduces the allowlist
decode and file matches; `docs/evidence/etuning-firmware-policy-analysis.md`
records the boundary.

A separate official desktop lead was also exhausted. E-TUBE Project 3.4.5's
exact `DuE5000Unit` static constructor assigns family 34/unit 0 a BootPatchSpec
with substrate 1, `Firmware.BootLoaderDcasXBaseName` (`UPDATEX`), and
bootloader 5.0.0 revision 01. `GetBootPatchFileName` constructs substrate plus
base plus `-{revision:X2}`, yielding stem `1UPDATEX-01`. The BootPatch file type
is 3, requires bootloader 4.0.0.0, and exposes checksum, code-size, DCAS,
generation, and version fields at offsets 0, 1, 2, 4, 5, 6, 7, and 8.

`Unit.UpdateBootPatch` starts update mode 2, obtains bootloader identity and
version, validates the newest BootPatch file set, compares its version to the
reported bootloader, and sends newer bytes through `SendUpdateData(..., true)`
and `EndUpdate(true)`. This is a genuine architecture path, not a mislabeled
application update. However, no `UPDATEX`/`UPDATE2I` payload was present in the
installed application or in the inspected public 2.2.3-3.4.5 catalogs,
debug catalog, archived installer contents, likely 5.x static filenames,
Wayback/Common Crawl indexes, GitHub/Sourcegraph results, or the Reven corpus.
Positive-control DUE5000 URLs continued to resolve during the filename sweep.
This bounded negative evidence makes the boot-patch path dealer/recovery-only
or dormant unless a payload is recovered elsewhere; it is not presently a BLE
bypass or recovery backup. `tools/inspect_etube_boot_patch.py` machine-checks
the exact assemblies and IL facts, and
`docs/evidence/d5000-boot-patch-analysis.md` records the search boundary.

Build .85's live and offline behavior is unchanged by this correction. No
firmware or destination command was sent, the public Pages site remains build
.77, and the last verified bike state remains stock D4.5.0/M4.4.8 at EU with
no measured higher assistance cutoff.

## 2026-09-24 sixteenth correction and build .86: hidden stock-pair workflow completed

The current-client allowlist proof makes the exact stock D4.3.0/M4.2.1 route
the best-supported firmware fallback, so build .86 closes the one deliberate
gap in its local coordinator. After a different BLE session has proved the
same motor at exact D4.3.0/M4.2.1 and EU, `writeAndVerifyUs` now delegates to
the existing durable `runPreparedUsWriteTransaction`. The transaction performs
a fresh salted baseline read, persists `US-write-attempt` before mutation,
sends exactly one current-eTuning packet `00 16 A8 01 01`, requires `AA`, and
then re-reads the full same-motor/version/destination baseline. Only an exact US
readback advances to the separate physical-power-cycle persistence gate.

An explicit `AB <status>`, timeout, disconnect, malformed reply, or non-US
readback cannot repeat A8. The durable journal instead requires read-only
resolution in another session or remains stopped. Stock D4.5.0/M4.4.8
restoration is still authorized only after exact D4.3.0/M4.2.1 plus US is
proved across a physical power cycle; the final gate remains exact stock
versions plus US on another reconnect. The transfer/recovery path still
replays a complete M-then-D pair from byte zero rather than resuming a fragment.

The preparation card remains `hidden`/`aria-hidden`, the public page still
serves build .77, and no bike command was sent. Build .86's visible current-
firmware mode-5/A0/mode-5/A8 sequence is unchanged from build .85. The hidden
stock workflow is implemented for synthetic review and is not authorized for
live use because interrupted BLE flashing may require wired recovery. The
modified D4.5.0.1 branch remains a later, higher-risk fallback rather than the
next firmware experiment. The last verified bike state is unchanged: stock
D4.5.0/M4.4.8, EU, with no measured higher assistance cutoff.

## 2026-09-24 seventeenth correction: SC-E6100 historical display control

The contemporaneous STUnlocker success reports specifically pair DU-E5000
with SC-E6100 4.0.5, so that exact display image was recovered from Shimano's
public catalog and checked rather than treating SC-E7000 behavior as universal.
The image is 164,488 bytes, SHA-256
`9a3d9575af48eac883a2369af08bd00d819547c49c78d313d7aadc18269eeb77`,
catalog MD5 `90ea6133e21bf5d59b40f999e5ea9a11`.

The apparent display-specific lead does not survive exact comparison.
SC-E6100 local handler `0x2b88c` accepts modes 0, 1, 4, and 5 with the same
selector semantics as SC-E7000. Its builder is `0x29460`; secure completion
handler `0x29ee0` stores requested mode, completion flag, and application slot
before constructing opcode `12`, and has no immediate mode-0 or cleanup call.
The mode tables at `0x29fb0`, `0x29fbc`, and `0x29fc8` are byte-identical to
the three tables in both exact SC-E7000 images. Their respective SHA-256 values
are `b34a08754c4e367c574499c73ce89919f3c1ed20165c5063cd139ac562a99c4e`,
`be1f5a4366bfd7b3c7f77dd585554e1201f38e86e56a1789522ff6af4cd47fa1`,
and `52cf8e1fbc56803e6ede87262de5df10e0165e948d7ebf992c29ace6541ee2b6`.

The lifecycle machinery is homologous too. Post-request helper `0x27950`
clears the periodic trigger and phase bytes +4/+5; tick `0x2789c` reaches exit
machine `0x279e0` only when trigger byte +6 is one. Whole-image direct-call
references locate exactly four event-rearm callers, two exit-machine callers,
and three local-mode callers. The two maintenance callers at `0x279ba` and
`0x27a04` issue mode 0 under the same event-driven conditions as SC-E7000.
Like SC-E7000 4.0.6, SC-E6100 4.0.5 does not clear phase byte +3 in the post
helper; current SC-E7000 4.1.0 adds that clear.

This rules out a different SC-E6100 secure key/table or an obvious permissive
owned-mode lifecycle as the explanation for the old success reports. It does
not reproduce live scheduling and cannot exclude a transient created by the
2020 client or its preceding firmware/update workflow. The historical-client
artifact and transient-state questions remain, but a display swap, SC-E6100
firmware port, or emulation detour is not supported by this evidence.
`tools/compare_display_pc_mode.py` now verifies SC-E6100 4.0.5 alongside
SC-E7000 4.0.6/4.1.0 without emitting vendor bytes.

No command was sent to the bike, build .86 and the public build .77 remain
unchanged, and the verified bike state remains stock D4.5.0/M4.4.8 at EU with
no measured higher cutoff.

## 2026-09-24 eighteenth correction and build .87: independent wheel-circumference fallback

The exact eTuning 3.0.7 client exposes a second D4.3.0 BLE speed route that does
not depend on the unresolved A0/A8 destination gate. Its old-generation getter
is `00 35 04 00`; notification parsing requires `00 35 06 lo hi`. Both the
single-setting path and backup-restore worker write `00 35 00 lo hi`, and the
notification dispatcher treats opcode `02` as the setter completion. The newer
GATT path independently reads first, writes only when different, waits 150 ms,
then requires an equal readback. Its UI bounds the value to 1300–3000 mm.

Independent public evidence agrees on the boundary. Shimano's DU-E5000
specification lists 1300–3000 mm and both 25 km/h and 20 mph support. eTuning's
downgrade guide marks E5000 4.3.0 as wheel/region capable, explains that the
wheel method makes the speedometer wrong while US gives accurate 32 km/h, and
says region/wheel values survive a later firmware update. STUnlocker lists
4.3.0 as the last E5000 Bluetooth version for both values; its older manual's
warning that E5000 settings may reset at power-off justifies retaining a
separate physical-power-cycle gate. eMax independently lists Bluetooth
destination and circumference changes for DU-E50X0 4.2.1–4.3.0.

For actual circumference `C`, nominal cutoff `Vn`, and target `Vt`, representing
`round(C*Vn/Vt)` makes the motor calculate the target cutoff. A 2080 mm wheel at
25→32 km/h gives 1625 mm, so displayed speed and distance become 0.78125 of
reality. This is a reversible fallback with inaccurate telemetry, not a US
destination change and not a measured cutoff result.

Build .87 leaves build .86's visible display-owned mode-5/A0/mode-5/A8 path
unchanged. It adds only an unwired wheel branch: exact packet builders/parser,
same-device durable journal before one mutation, no retry after any ambiguous
outcome, read-only resolution in another BLE session, and a separate explicit
power-cycle persistence check on the exact same salted motor and prepared pair.
`tests/wheel_fallback_transaction.cjs` uses generated bytes to prove the exact
packets, 2080→1625 calculation, single-write guard, uncertainty resolution,
and persistence gates. `docs/evidence/d430-wheel-circumference-analysis.md`
records the evidence and limits.

The branch has no UI caller and does not authorize D4.5.0 restoration yet. A
live staged experiment must first prove preparation, original value, one setter,
and power-cycle persistence, then prove that the wheel getter remains available
after restoration before the final state machine can be safely extended. No
bike command or firmware transfer occurred; the public page remains build .77,
and the last verified state remains D4.5.0/M4.4.8 at EU with no measured higher
assistance cutoff.

## 2026-09-25 nineteenth correction and build .88: destination is not the only speed field

The exact historical Shimano E-TUBE PROJECT Cyclist 5.0.2 Android client closes
a post-destination ambiguity that the previous work treated only as a forum
anecdote. The inspected package identifies itself as
`com.shimano.etubeprojectmobile.droid.phone`, version `5.0.2`, version code
`20211125`; it is 115,738,926 bytes with SHA-256
`b9b0ccb924f0dd1931beaada10501791b77268e4364bdb871010cd36ca606db2`.
Its embedded signing certificate names SHIMANO INC.'s Bicycle Components
Division and has SHA-256
`4670436569eabd6ea8392b9f844fc23a574c35bffe463a537620452495d3c6bb`.
The APK came from a historical mirror rather than a live Shimano endpoint, so
the manifest, certificate, and signed entries improve provenance without being
treated as a current vendor download. The APK and full decompilation stay
outside Git.

`DUE5000Unit` explicitly sets `canSetMaxAssistSpeed = true`. The exact
`DUUnitDataLink` commands are:

- current configured maximum getter `00 16 B4 00`, reply `00 16 B6 lo hi`;
- destination-specific maximum getter `00 16 BC destination`, reply
  `00 16 BE destination lo hi`;
- configured maximum setter `00 16 B0 lo hi FF FF`, with normal setter
  completion B2.

The two-byte values are little-endian hundredths of km/h.
`DUCustomizeOptions` first reads destination and then invokes the BC getter for
that destination; it divides the returned value by 100 and stores it as the
default maximum. `CustomizeDUPresenter.makeDefaultSettings` copies that default
into the pending DU settings. Confirming Reset updates the pending model only;
the Apply coroutine calls `writeMaxAssistSpeedKM`, which multiplies the selected
integer speed by 100 before B0. The fallback range table gives US 19–32 km/h
and ordinary non-US metric operation 15–25 km/h. Thus Reset/Apply after a
successful destination change has a concrete mechanism: it is a separate B0
write, not a hidden destination command.

A public E-TUBE PROJECT Professional 5.4.4 service report generated in January
2026 independently shows a live DU-E5000 on D4.5.0 with destination Type 1 and
maximum assist speed 25 km/h at the same time. Cyclist maps Type 1 to US. The
report therefore confirms that the separate lower-ceiling state exists on
current firmware; it does not show how the destination was written or prove
BLE setter acceptance. Its device identifiers are intentionally not copied.

Independent eMaxMobileApp 1.89 code corroborates the old-generation B0 packet,
B2 success, B4 getter, and B6 little-endian parser. It does not settle live
E5000 setter availability: the current eMax UI disables the reduced-maximum
button for the E5000 family while allowing supported older-firmware destination
and circumference actions. Static D4.1/D4.3/D4.5 dispatch tables likewise put
B0/B4/BC on the generic category-16 forwarder, not the local A0/A8 handlers;
D4.3's generic handler reaches the secondary-component forwarding path. This
supports, but does not prove, a live BLE response from the exact bike.

Build .88 retains build .87's write and firmware branches unchanged. The normal
authenticated information batch now adds only two reads: B4 for the configured
ceiling and BC 01 for the motor's US-profile ceiling. Exact reply header,
length, destination echo, and 10–50 km/h bounds are required before display.
No B0 setter is exposed. Synthetic tests prove packet construction, parsing,
formatting, batch order, absence of B0, and the diagnostic distinction between
US with a lower configured ceiling and US with its destination maximum.

The next live evidence gate is therefore safer and more informative. A
read-only build-.88 run can establish the current EU-side B4 and US BC values.
If a later destination transaction reads back US but B4 remains below BC 01,
the destination is not the failure; the separate maximum setting becomes the
next narrowly scoped candidate. Only that observed state could justify an
at-most-once B0 coordinator with a durable journal before write, exact B2,
immediate B4, no retry after ambiguity, and a separate physical-power-cycle
readback. No bike command, setting write, or firmware transfer occurred during
this correction. The public page remains build .77 and the last verified bike
state remains D4.5.0/M4.4.8 at EU with no measured higher cutoff.

## 2026-09-25 twentieth correction and build .89: stock B0 continuation after persisted US

The build-.88 decision gate is now implemented as a separate local,
unpublished transaction rather than left as a design note. This does not alter
the prerequisite: the last physical-bike state is still EU, so the new button
cannot arm and no B0 was sent. It becomes eligible only if a normal information
batch first proves the exact stock D4.5.0/M4.4.8 E5000 pair, destination US,
configured B4 below the motor's BC 01 ceiling, verified session, and motor
authentication. When US came from this page's destination transaction, that
transaction's salted same-device reconnect record must already say US
persisted. A typed speed is never accepted; the target is the freshly returned
BC 01 value and is capped at 32 km/h.

Immediately before any mutation, build .89 repeats seven reads: drive model,
application firmware, current destination, B4, BC 01, native D firmware, and
native M firmware. All must reproduce the exact stock pair and US/lower-ceiling
state. It then creates a new versioned journal with a random salt, salted hash
of the browser-selected device ID, salted hash of the BLE connection token,
public expected component versions/destination/target, and original B4. The
journal must serialize, persist, and read back byte-for-byte before the only
`00 16 B0 lo hi FF FF` dispatch. Raw device ID, serial, passkey, and credentials
are not stored.

The write adapter accepts only normal B2 or matching B3 rejection. After B2,
the same seven-read snapshot must still identify D4.5.0/M4.4.8 at US and show
`B4 == BC 01 == journal target`. A B3 rejection, mismatched readback, malformed
result, ATT failure, timeout, or disconnect records a terminal stopped state;
the transaction has no loop or retry entry. Even an ambiguous outcome can only
advance through the separate persistence verifier. That verifier has no write
callback and requires an explicit physical-power-cycle checkbox, another BLE
connection token, the same salted Web Bluetooth device, the exact stock pair,
US, and target equality. A transport failure during persistence remains
retryable only as another read-only verification.

`tests/max_assist_write.cjs` proves the exact 32 km/h wire bytes
`00 16 B0 80 0C FF FF`, journal-before-write order, one-write invariant,
same-device and different-session gates, rejection and ambiguity behavior,
fail-before-write storage errors, context rejection, immediate mismatch, and
power-cycle match/mismatch. The Playwright browser test drives the exact stock
US/lower-ceiling synthetic fixture, confirms one B0, reconnects, performs a
second full information batch with the explicit checkbox, reaches
`persistence-verified`, and confirms the B0 count remains one. The entire CJS
suite and the targeted two-session browser scenario pass. These are software
invariants only: they do not prove the real motor accepts B0, that a stored
value changes assistance, or that 32 km/h is reached while riding.

Build .89 keeps the display-owned mode-5/A0/mode-5/A8 destination experiment,
hidden stock downgrade/restoration coordinator, hidden D4.5.0.1 patch branch,
and hidden D4.3.0 circumference fallback otherwise unchanged. The public site
remains build .77. The bounded live order is still destination first; only
after US itself persists and B4 remains below BC 01 does the new one-attempt B0
button become relevant. A later safe ride remains the independent final proof
of the real assistance cutoff.

## 2026-09-25 twenty-first correction: eTuning confirms A8-to-B0 continuation; M4.4.8 RX trace remains open

The exact eTuning 3.0.7 base APK supplies an independent implementation of the
post-destination step recovered from Shimano Cyclist. Its old-generation region
activity writes `00 16 A8 01 destination`. When the operation's completion
callback reports success, `ActivityC1041w.m5514C` invokes `m5522K`, which
derives the maximum for the newly selected destination. The helper returns 32
km/h for US. The resulting `RunnableC0168F2` sleeps 350 ms and invokes
`C1463qn.m6515Z`; its old-generation branch multiplies by 100 and sends
`00 16 B0 lo hi FF FF`. The concrete US packet is therefore
`00 16 B0 80 0C FF FF`, byte-for-byte identical to build 89's target.

`tools/inspect_etube_max_assist.py` now has an optional exact-eTuning source
pass. It can also require the recorded 7,060,465-byte base APK SHA-256
`d4d545150f025760a13bf3bcade148f278731a1d49bf59d1e9da338723c90e22`.
The combined checker passed against both external decompilations and both exact
APKs without printing source. This proves the current commercial client's
intended A8-success -> 350 ms -> B0 ordering; it does not prove live A8 or B0
acceptance by the stock D4.5.0/M4.4.8 pair. eTuning's documented E5000 BLE
region support remains bounded to its older preparation firmware.

A separate 2019 E-MTB Forums report supplies bounded live corroboration on an
E6100 running 4.4.0. The rider reported that destination already read US while
the maximum remained 24 km/h; using E-TUBE Reset after the region change moved
the maximum to 32 km/h and a later ride reached that assistance speed. This is
consistent with the recovered separate fields and write order, but the motor,
firmware, display path, and client differ from the present E5000 system. Source:
https://www.emtbforums.com/threads/steps-unlocker-issue.7518/ .

The exact official M4.4.8 artifact was reacquired as 119,824 bytes with SHA-256
`9ea350e988345a9d9fb41c1363562ca190f1a8d5e1cc8a38c6373f69b877f033`.
It is Renesas RX code. Loading at `0xFFFC0000` with the Ghidra RX processor
module produces coherent functions and internal-ROM references; earlier M16C
and base-zero scratch projects were invalid. Immediate and rendered-operand
sweeps for the category byte, B0/B4/B6/BC/BE family, A0/A8, and 2500/3200 were
manually checked in context. Candidate B0/A0/A8 hits near recovered functions
were low-RAM addresses, raw `16 B0` pairs were data or instruction encodings,
and the located 2500/3200 constants belonged to motor-control/configuration
logic. No inspected result identifies the packet dispatcher or B0 policy.

The new `tools/GhidraDumpInstructions.java` and
`tools/GhidraFindInstructionScalars.java` scripts make that bounded search
reproducible; the latter now handles RX rendered immediates and non-instruction
range starts. The corrected status is in
`docs/evidence/m448-max-assist-analysis.md`. The next useful motor step is to
recover the table-driven receive dispatcher or anchor it with a real B4/BC/B0
notification transcript, not to treat more unanchored byte hits as commands.
No bike command, setting write, or firmware transfer occurred. Build 89 and the
public build 77 are unchanged; the last verified bike state remains stock
D4.5.0/M4.4.8 at EU with no measured higher cutoff.

## 2026-09-25 twenty-second correction and build .90: exact D4.5 B0 policy recovered

The prior conclusion that D4.5.0 put B0/B4/BC only on a generic forwarder was
wrong. Its large dispatcher at `0x1D4A0` compares combined little-endian
category/opcode keys through a cumulative subtraction chain, so searching for
standalone `0xB016`, `0xB416`, or `0xBC16` literals cannot find the cases.
Replaying every subtraction recovers explicit `16 B0` at `0x1D74E`, `16 B4`
at `0x1D766`, and `16 BC` at `0x1D778`. Their handlers are respectively
`0x1EE3C`, `0x1EE80`, and `0x1EE8C`.

The B0 path is now concrete. `0x1EE3C` requires the global PC-mode byte to be
nonzero, reads the requested little-endian u16, and calls `0x19264`. It does
not require protected mode 4/5. `0x19264` obtains the current destination,
calls ceiling helper `0x193EE`, rejects only when the request exceeds that
ceiling, accepts an already-equal value, and otherwise persists record `0x28`
through the ordinary settings store before updating the live configured value
and recalculating dependent state. Success queues event `0x2E`; its builder at
`0x22E9C` uses response key `16 B2`. The error path still uses B3.

The same helper makes the numerical policy exact: destination 0 returns 2500,
destination 1 returns 3218 (`0x0C92`), destination 2 returns 2400, and
destinations 3/4 or fallback return 2500. The BC handler stores the requested
destination and queues event `0x2F`; builder `0x22F1C` emits `16 BE`, echoes
the selector, and calls `0x193EE`. The B4 callback builder at `0x22ED8` emits
`16 B6` and reads the configured value. Therefore stock D4.5.0 directly
permits B0=3200 after destination 1 while rejecting it under destination 0.
The ordinary display-owned mode 1 is sufficient, and a successful fresh BC
read immediately before B0 proves the same nonzero-mode gate was live.

This also corrects the transaction target. BC 01 can legitimately report the
internal bound 32.18 km/h, while Shimano Cyclist/eTuning choose the user-facing
32.00 km/h. Build .90 now derives `min(fresh BC 01, 3200)`, journals both the
fresh internal ceiling and the derived target, dispatches exactly
`00 16 B0 80 0C FF FF`, and requires later B4=3200 while BC remains unchanged.
The one-write, durable-journal, uncertainty, different-session, and physical-
power-cycle rules remain unchanged. Tests now exercise a synthetic BC=3218
and prove that only B0=3200 is sent.

The M4.4.8 project was also corrected again: the first u32 is image size
`0x1D410`, while the header pointer at file offset `0x14` gives the real entry
`0xFFFC0018`. A clean RX project seeded there produces coherent startup and
904 recovered functions. Its earlier direct opcode hits remain false, but an
M-side wire handler is no longer expected because the exact D application
contains the acceptance and persistence policy. New reusable function-list and
decompiled-search scripts plus `--defined-only` scalar scanning preserve the
clean project.

No bike command, setting write, or firmware transfer occurred. Build 90 remains
local and unpublished; the public site remains build 77 and the last verified
bike state remains stock D4.5.0/M4.4.8 at EU with no measured higher cutoff.

## 2026-09-25 twenty-third correction and build .91: D4.3 fallback now satisfies the verified gate

The hidden stock-preparation coordinator inherited an unresolved contradiction:
after verifying D4.3.0/M4.2.1 it sent the commercial clients' direct A8 packet,
even though exact D4.1, D4.3, and D4.5 firmware all require the volatile gate
created only by an accepted A0. Current eTuning, eMax, and STUnlocker clients
prove the A8 packet and field compatibility but their visible destination call
chains do not explain how the gate becomes armed. Relying on that unexplained
retained state made the repository's fallback less causal than its stock path.

Build .91 corrects the hidden D4.3 transaction without exposing the firmware
card. After the existing same-device, exact-pair, different-session verification
and durable journal, it now reads the current lighting value, asks the SC-E7000
to establish and own mode 5, sends one unchanged-lighting A0, requires A2,
freshly establishes display-owned mode 5 again, and sends one US A8. It requires
AA and immediate US readback, exits through display-local mode 0, never retries
A0 or A8, and retains the separate physical-power-cycle persistence and stock-
restoration gates. A failure after A0 remains terminal journal state resolved
only through read-only reconnect.

The prepared-pair browser adapter test now proves the exact A4 read,
`00 16 A0 lo hi FF FF`, two display-owned mode-5 calls, `00 16 A8 01 01`,
mode exit, rejection mapping, and timeout propagation. The durable transaction
and patched-pair lineage suites remain green. This is synthetic evidence only:
no firmware or setting command was sent, build .91 remains local and unpublished,
and the physical bike remains verified only at stock D4.5.0/M4.4.8 with EU.

## 2026-09-26 twenty-fourth correction and build .92: one guided control

Build .91 was committed, published to GitHub Pages, and verified byte-for-byte
against the local `index.html`. Publication did not connect to the bike or send
any BLE command. The last physical result remains exact stock D4.5.0/M4.4.8 at
EU, with no verified higher assistance cutoff.

Build .92 changes presentation and orchestration only; the protocol packets,
eligibility gates, durable journals, exact replies, and no-retry rules are
unchanged. The normal screen now shows the passkey, one contextual workflow
button, connection, region, and current assist ceiling. Its first action is the
same read-only authenticated information batch. Only after that batch proves EU
and the exact stock pair does the button become **Set US region once**. That
action has a separate confirmation, performs motor authentication automatically,
and invokes the existing at-most-once build-.91 transaction. A pending region
record changes the same control to read-only power-cycle verification rather
than exposing another write.

After same-device reconnect proves persisted US, a freshly lower B4 and higher
BC make the same button become the separately confirmed **Set 32 km/h once**
action. A pending B0 journal again changes it to read-only physical-power-cycle
verification. A verified target disables the control as complete. Invalid,
ineligible, non-US, and recorded non-US states fail closed. Detailed telemetry,
the sanitized log, and legacy manual controls remain available under two
collapsed disclosure sections for troubleshooting; the firmware card remains
hidden and unwired. Synthetic browser coverage proves the initial screen has
one visible button and that the guided control advances from the read-only EU
check to only the US action, pending verification, and the ceiling action. No
bike command, setting write, or firmware transfer occurred during this UI work.

## 2026-09-26 twenty-fifth correction and build .93: retain failed-attempt reports

A build-.92 compact report from the physical bike freshly verifies the exact
stock D4.5.0.0/M4.4.8.0 pair, application slot 0D, EU destination, configured
25.00 km/h maximum, and destination-1 ceiling 32.18 km/h. Its final line proves
that represented connection was read-only. The user reports that a setting
action had errored, but the compact report contains no motor-authentication,
A0, A8, rejection, or setting-attempt line. The outcome of that reported action
therefore cannot be inferred and it must not be repeated from this evidence.

The mismatch exposed a report-selection defect: after any disconnect and
read-only reconnect, `exportLog()` began at the newest `Connected` line and
could omit the entire preceding failed setting session even though the full log
remained in session storage. Build .93 makes no command or gate change. It
anchors the compact report at the connection preceding the latest bootloader
probe, motor-authentication start, US-region attempt, maximum-assist attempt,
or guided-setting failure, preserving that failure together with later
read-only recovery. A regression test covers a mode-5 rejection followed by an
EU reconnect. No bike command or setting write occurred during this code fix.

## 2026-09-26 twenty-sixth correction and build .94: exact DB-46 authentication-lock recovery

The recovered build-.93 physical report establishes the missing boundary. The
same bike again returned the exact stock D4.5.0.0/M4.4.8.0 pair, application
slot 0D, EU destination, configured maximum 25.00 km/h, and destination-1
ceiling 32.18 km/h. The confirmed setting action then stopped when the first
motor D8 challenge received opcode DB. It disconnected before PC mode, A0, A8,
B0, or either durable setting journal. The last verified physical state is
therefore still EU/25 km/h, and the failed action did not consume the page's
at-most-once destination attempt.

Build .93 discarded the byte following DB, so that report cannot distinguish
the desktop library's `3A` command-not-disposed, `3B` authentication-unnecessary,
or `46` authentication-lock results. Build .94 now retains only that non-secret
reason byte in the sanitized log. Every code except exact `46` remains a hard
stop. A short DB, timeout, malformed DA, failed E8, EB, or another DB after
recovery also stops and disconnects.

For exact `DB 46`, build .94 implements the bounded caller policy already
recovered from E-TUBE Project 3.4.5: send one serial-derived E8, require a
normal EA, clear any collected challenge fragments, and start one fresh D8
exchange. There is no loop. If the fresh D8 succeeds, the normal three E0
fragments and exact E2 completion continue; because the lock-release E8 has
already succeeded, no second E8 is sent. The destination workflow can only
begin after that complete authentication result. A0, A8, and B0 behavior,
journals, confirmation, and no-retry rules are unchanged.

The motor regression suite proves the unchanged normal path, retained DB-3A
diagnostic with no E8, exact DB46 wire order (`D8, E8, D8, E0 x3`), one-E8
invariant, second-DB stop, and unlock-failure stop. These are synthetic
transport results. Build .94 has not yet received a physical DB reason or sent
a setting command; the next live run must be treated as a new explicitly
confirmed action, and its compact report must be preserved whatever the DB
code or later outcome.

## 2026-09-27 twenty-seventh correction: build .94 physical A0 rejection

The build-.94 compact physical report supersedes the untested-status paragraph
above. On exact stock D4.5.0.0/M4.4.8.0 with EU destination, B4=25.00 km/h and
BC(US)=32.18 km/h, the first D8 returned `DB 46`. One E8/EA exchange followed
by one fresh D8 challenge completed motor authentication. The page retained
lighting `0A 00`, durably recorded the same-device US attempt, and received
both the SC-E7000's mode-5 acknowledgement and exact motor completion. It
enqueued `00 16 A0 0A 00 FF FF` 15.5 ms after that completion. ATT accepted the
write, but the motor explicitly replied `A3 3A`; the page stopped without
sending A8 or B0. The connection then ended while mode-0 exit was being
attempted, so the exit was not verified. A later read-only reconnect reported
the same stock pair, EU and 25 km/h, and the durable journal blocked a repeat.
The report does not establish whether the screen restarted or which event
caused the disconnection.

Exact D4.5.0 A0-handler decompilation at `0x252a8` has only two acceptance
checks before it sets the A8 gate: active motor PC mode equals 4 or 5, and the
normalized target byte equals zero. Failure produces `3A`. The validated
SC-E7000 forwarder and this packet support a zero target, so loss of active
mode by the time A0 was handled is the leading hypothesis, not directly
measured fact. A read-only review of all references to active-mode RAM
`0x200029f9` found the known mode-request and fifth-secure-word writers, not
a newly discovered timer or hidden A0-specific clear. The full on-page log is
needed to check for a mode-0/1 transition or unsolicited bridge traffic between
the completion and A0 reply. Merely shortening the interval or repeating A0
is not justified by this evidence.

The same D4.1/D4.3/D4.5 mode and A0 gate checks mean a stock D4.3/M4.2.1 BLE
downgrade is not a causal fix for this observed rejection on its own. Vendor
compatibility documentation still identifies D4.3 as the Bluetooth-supported
E5000 range, but the missing state transition and the older clients' direct-A8
gate paradox remain unresolved. Treat flashing as a separate riskier candidate,
not the next automatic action; an interrupted or unbootable BLE update may
require a wired recovery interface. The hidden modified-D4.5.0.1 image remains
uninstalled and unwired. No validated US-setting or higher-speed result exists.

Primary vendor references checked again on 2026-09-27:
[`STUnlocker compatibility`](https://www.stunlocker.com/),
[`eMax DU-E50X0 matrix`](https://www.emax-tuning.com/eMax-possibilities.pdf),
[`eTuning downgrade instructions`](https://etuning-app.com/downgrade.pdf), and
[`Shimano Professional recovery FAQ`](https://bike.shimano.com/en-NA/support-and-service/faq/EPP0A.html).
The now-updated eTuning guide says its old manual downgrade steps are
superseded by an in-app iPhone/Android action; its E5000 table still names
D4.3.0 and says US region has a correct speedometer. The vendor's
[`comparison`](https://etuning-app.com/compare/etuning-vs-emax-vs-stunlocker/)
also claims automatic downgrade for older E5000 motors. These are commercial
capability claims, not proof that the current bike's display/battery topology
will accept the downgrade or destination write. Shimano's FAQ describes
SM-PCE02 single-unit wired restoration if a firmware update fails, so the
in-app convenience does not remove the recovery risk.

## 2026-09-27 twenty-eighth correction: a stock-BLE queue-ordering candidate

The user prefers a route without a firmware downgrade. A fresh read-only
SC-E7000 4.1.0 decompilation found a materially different timing relationship
from the failed build-94 experiment. Display-local `00 0C 05` queues its motor
mode request and five secure words through `0x210c6` → `0x2bf74` **before**
`0x236fc` sends the local `2C 00` reply. Phone-originated drive commands also
use `0x2bf74` through `0x200bc`. The generic type-`0x10` formatter adds full
packets to a ring at `0x2d7c4`, and `0x2d61e` removes them FIFO. The image's
compressed startup data was decoded in memory; its 14-entry priority table
does not include the `32/10` request, `32/30` secure words, or `16/A0`.
The exact-hash read-only verifier in `tools/inspect_display_pc_mode.py` now
checks the startup-table digest, call graphs, and exclusions.

Therefore an unchanged A0 enqueued immediately on local `2C 00`, *before*
motor completion, could sit directly behind the six protected-mode frames and
reach the motor much sooner after mode promotion than build 94's
post-completion A0. This is a new mechanism, not another payload variant or
attempt to shave a few milliseconds off the same post-completion path.
However, static FIFO structure does not prove runtime bus order or exclude a
topology event, an alternate queue state, a write failure, or A0 rejection.
The build-94 salted journal remains terminal; no new bike write, bypass, or
firmware download is enabled. See `docs/evidence/bridge-analysis.md` for the
bounded path and limitations. A live experiment would need a separately
reviewed one-shot protocol, exact motor completion plus A2 gating, and a
distinct journal decision rather than silently clearing the existing record.
A safer first physical discriminator would enqueue only the known read-only
`AC 01` destination getter at local `2C 00`, require its ATT acknowledgement
before motor mode-5 completion and exact `AE 01` afterward, then exit. `AC`
shares A0's phone-forwarding path and is
also absent from the priority table. This tests whether the bike admits and
orders an early queued command without another setting write; it does not
prove protected A0 acceptance. Build .95 connects only this
read-only timing probe to the existing guided button after the verified non-US
attempt record. It does not clear that record or wire the early A0 hypothesis.
Synthetic tests cover ordering, one run per connection, and an early-completion
abort; the probe itself has not been run on the bike.
The [STUnlocker iOS manual](https://stunlocker.com/doc/ST_Manual_iOS.pdf)
also clarifies that its D4.5-compatible speedometer calibration changes only
displayed speed, not the motor's actual assist cutoff, so it is not a route to
the requested higher assistance speed.

## 2026-09-27 twenty-ninth correction: retained D4.5 wheel handlers

Exact D4.5.0 decompilation also found `35 00` and `35 04` dispatch entries at
`0x1d4ce` and `0x1d506`. The setter at `0x1e13c` requires nonzero PC mode,
a nonzero 16-bit value, and a source-state relation at RAM `0x20002168`
offsets `+0x1e` and `+0x18`; only then does `0x18e38` persist record `0x1f`.
The getter route schedules a response. The exact-hash verifier is
`tools/inspect_d450_wheel.py`; see the updated
`docs/evidence/d430-wheel-circumference-analysis.md`.

This is evidence that the native wheel handler remains in D4.5, **not** that
the vendor's D4.3 Bluetooth compatibility matrix is wrong in practice. The
SC-E7000 source-state gate and live BLE reply are untested, and a wheel edit
would misstate speed/distance. A stock-firmware, read-only `35 04` query is a
separate low-risk discriminator; no wheel setter is exposed or sent to the bike.

## 2026-10-03 thirtieth correction: match authentication and observe surfaced modes

A fresh review of build 95 found a real comparison confound: its AC queue
probe did not invoke motor authentication, while the physical build-94 A0
attempt had completed the motor D8/E0 exchange and bounded E8/EA recovery.
Build `2026-10-03.96` now completes the existing bounded authentication path
before display-owned mode 5 and verifies success in the same connection.
Failed authentication sends neither mode 5 nor AC. This does not prove that
authentication caused the earlier rejection; it makes the diagnostic compare
the same established preconditions.

The probe also passively records only redacted category-32 mode/slot and
rejection-reason headers surfaced on 2AF9/B/D from before entry through exit.
Secure words and authentication bytes are excluded. It records the local
`2C 00`-to-AC-send interval and an explicit timing/transition/failure verdict.
The existing one-read early-AC sequence, exact completion/readback checks,
once-per-connection rule, mode-0 exit, and durable setting journal remain.
No A0, A8, B0, wheel setter, journal bypass, or firmware transfer was added.
AC has no protected-mode gate: success tests phone read admission and observed
event order only. BLE arrival times are not motor processing timestamps, and
silence from the passive observer does not establish retained motor mode 5.

The owner does not remember whether the screen restarted during build 94;
that observation remains unknown. Fresh research in the supplied
[EP8 Reddit thread](https://www.reddit.com/r/ebikes/comments/13djzkb/change_of_region_on_ep8_shimano_steps/)
found Android/Bluetooth success reports but no native firmware pair, display
identity, or known-good byte trace. A
[May 29, 2024 E5000 report](https://happyride.se/forum/threads/optimala-installningar-for-shimano-steps-e5000.3700908/)
explicitly describes no downgrade with EW-WU111, but supplies no firmware
version and uses a different BLE owner topology. It is a lead for ownership
comparison, not an exact D4.5 counterexample or an instruction to buy hardware.

Current primary sources remain model/function/transport specific. The
[eMax matrix, revision 3.2](https://www.emax-tuning.com/eMax-possibilities.pdf#page=20)
marks E5000 D4.4.2–4.5.0 Bluetooth destination/wheel changes unsupported;
[STUnlocker](https://stunlocker.com/) places those BLE features through D4.3;
and [eTuning's comparison](https://etuning-app.com/compare/etuning-vs-emax-vs-stunlocker/)
assigns latest-firmware changes without downgrade to desktop/PCE. Its
[in-app downgrade guide](https://etuning-app.com/downgrade.pdf) still names
D4.3 for E5000. Public GitHub repository/issue and indexed-code searches found
firmware inspection, download, hardware exploration, and telemetry projects,
but no independently demonstrated exact-stock destination trace. These are
bounded search results, not proof that a creative stock BLE route is impossible.
Sources, transfer limits, and next decisions are collected in
[`the research report`](reports/Shimano%20stock%20BLE%20next%20step.md).

The synthetic checks passed 27 region/probe tests, 11 motor-authentication
tests, seven compact-report tests, and the firmware-picker browser check. These checks
establish code ordering, guards, and redaction only. Build 96 has no bike result;
the last physical result remains stock D4.5.0/M4.4.8, EU, and 25 km/h.
