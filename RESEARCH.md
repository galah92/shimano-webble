# Session authentication investigation

Updated 2026-09-09. Target: SC-E7000 + DU-E7000 firmware 4.7.1,
using Android Web Bluetooth. Build `2026-09-09.4` verified session access on
the real bike. Build `2026-09-09.5` received no matching drive-unit model reply in two live
tests. Build `2026-09-09.6` batches four information queries with transport diagnostics.

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
