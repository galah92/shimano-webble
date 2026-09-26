# DU-E5000 maximum-assist-speed protocol

## Result

Shimano stores the configured maximum assist speed separately from the motor's
destination. Destination remains the preferred 32 km/h route because it keeps
speed and distance correct, but a successful US destination read is not by
itself proof that the separate maximum has been raised to the US ceiling.

The exact read protocol is part of build 91's normal information batch. It
reads both the configured value and the motor's destination-specific US
ceiling. Build 91 also exposes a narrowly gated, bike-untested implementation of
Shimano's stock setter behind the guided workflow. It cannot arm until fresh
reads prove the exact stock D4.5.0/M4.4.8 pair, destination US, and a configured
ceiling below 32 km/h. Exact D4.5.0 decompilation now proves that the stock B0
handler exists and accepts a requested value no higher than the current
destination's internal ceiling. It has still not been exercised on the bike;
no live B0 result exists.

## Primary client evidence

The historical Android client inspected was E-TUBE PROJECT Cyclist 5.0.2,
package `com.shimano.etubeprojectmobile.droid.phone`, version code `20211125`.
It was obtained from the [APKCombo version page](https://apkcombo.com/e-tube-project-cyclist/com.shimano.etubeprojectmobile.droid.phone/download/phone-5.0.2-apk)
and kept outside the repository.

- Size: 115,738,926 bytes
- SHA-256: `b9b0ccb924f0dd1931beaada10501791b77268e4364bdb871010cd36ca606db2`
- Embedded signing-certificate SHA-256:
  `4670436569eabd6ea8392b9f844fc23a574c35bffe463a537620452495d3c6bb`
- Certificate subject: `CN=Yoshiyuki Kasai, OU=Bicycle Components Division,
  O=SHIMANO INC., L=Sakai, ST=Osaka, C=JP`

The mirror is not a Shimano distribution endpoint. The manifest identity,
embedded certificate, and signed-entry verification materially improve
provenance, but this remains a historical mirrored artifact rather than a
fresh vendor download. No APK or whole decompilation is committed.

The fail-closed `tools/inspect_etube_max_assist.py` checker can reproduce the
source-level findings from JADX output and, when `--apk` is supplied, first
requires this exact APK size and SHA-256. It prints no vendor source.

The relevant decompiled classes are:

- `DUE5000Unit`: sets `canSetMaxAssistSpeed = true`.
- `DUUnitDataLink`: constructs the exact category-`16` getter, setter, and
  per-destination getter commands.
- `DUUnitReadWriter`: converts between the wire's hundredths of km/h and the
  UI's integer km/h.
- `DUCustomizeOptions`: reads current destination, then asks the motor for the
  maximum allowed for that destination and uses it as the default.
- `CustomizeDUPresenter`: Reset copies that destination-specific default into
  the pending settings; confirmation alone does not write. Apply invokes the
  maximum-speed writer.
- `DestinationType`: maps EU to `0` and US to `1`.

This agrees with Shimano's public Cyclist manual, which documents a separate
**Maximum assist speed** control followed by **APPLY**, and with Shimano's
DU-E5000 product data, which lists 25 km/h and 20 mph support. See the
[Cyclist manual](https://si.shimano.com/en/pdfs/um/7J4MA/UM-7J4MA-008-ENG.pdf)
and [DU-E5000 product specification](https://productinfo.shimano.com/en/product/DU-E5000).

## Public live-configuration cross-check

A public E-TUBE PROJECT Professional 5.4.4 service report generated in January
2026 shows one DU-E5000 on firmware 4.5.0 with **Destination Type 1** and
**Maximum assist speed 25 km/h** in the same configuration. Cyclist's enum maps
Type 1 to US. This independently confirms that a US destination and a lower
configured maximum can coexist on current firmware; it does not establish how
that bike reached the state or whether a BLE B0 write is accepted. The report
contains device identifiers, so none are reproduced here. See the
[public E-TUBE service report](https://media-cdn-frz.alltricks.com/manuels/OCCTEST0011O2FEEL.pdf?1770975382=).

## Wire protocol

All values below are logical application packets sent through the existing
`2AFE` drive-unit route. Multi-byte speeds are little-endian hundredths of
km/h.

| Operation | Request | Normal reply | Parsed value |
| --- | --- | --- | --- |
| Read configured maximum | `00 16 B4 00` | `00 16 B6 lo hi` | `lo + hi*256` |
| Read maximum for destination | `00 16 BC destination` | `00 16 BE destination lo hi` | `lo + hi*256` |
| Set configured maximum | `00 16 B0 lo hi FF FF` | normal setter completion (`B2`) | requested hundredths |

For example, 32 km/h is `3200 = 0x0C80`, so its setter payload would be
`00 16 B0 80 0C FF FF`. Build 91 constructs exactly that payload. It does not
accept a typed target: the target is the lower of the freshly returned `BC 01`
value and Shimano's documented/client-selected 32.00 km/h US value.

The app's fallback range table uses 19–32 km/h for US and 15–25 km/h for the
ordinary non-US metric case. The motor's D4.5.0 implementation returns an
internal US ceiling of 3218 hundredths for `BC 01`; that is an acceptance
bound, not the UI target. Shimano clients request 3200, so the page deliberately
sends 3200 while retaining the fresh 3218 observation in the durable journal.

## Independent corroboration and boundary

The exact eTuning 3.0.7 base APK provides a stronger independent workflow
cross-check. In its old-generation region activity, it writes
`00 16 A8 01 destination`. The successful completion path invokes a maximum-
speed continuation, derives 32 km/h for destination US, waits 350 ms, and calls
the old-generation writer. That writer multiplies the speed by 100 and emits
`00 16 B0 lo hi FF FF`; for US this is the same
`00 16 B0 80 0C FF FF` packet used by build 91. The read-only checker can now
verify this chain from the exact external JADX output as well as verify the
Cyclist sources:

```sh
python3 tools/inspect_etube_max_assist.py /path/to/cyclist-jadx/sources \
  --apk /path/to/etube-cyclist-5.0.2.apk \
  --etuning-sources /path/to/etuning-3.0.7-jadx/sources \
  --etuning-apk /path/to/etuning-3.0.7-base.apk
```

This establishes the commercial client's intended A8-success -> 350 ms -> B0
ordering and independently confirms the exact stock payload. It does not prove
that either write is accepted through SC-E7000 on D4.5.0/M4.4.8; eTuning's
documented E5000 Bluetooth region path is bounded to the older preparation
firmware.

The separately inspected eMaxMobileApp 1.89 implements the same old-generation
`B0 lo hi FF FF` write and parses `B6` as a little-endian current value. That
independently corroborates the packet family. However, its current UI disables
the reduced-maximum-speed button for the E5000 family even while enabling
destination and circumference on supported older firmware. Therefore generic
packet support is not evidence that a live E5000 write is accepted in the
current state.

## Exact D4.5.0 acceptance path

The exact D4.5.0 image contains direct handlers for all three commands. The
dispatcher at `0x1D4A0` encodes comparisons as cumulative subtractions, which
is why a literal/immediate search initially missed them. Replaying that chain
recovers these combined little-endian category/opcode keys:

| Key | Compare site | Handler | Behavior |
| --- | --- | --- | --- |
| `0xB016` (`16 B0`) | `0x1D74E` | `0x1EE3C` | parse requested u16 and call the persistent setter |
| `0xB416` (`16 B4`) | `0x1D766` | `0x1EE80` | emit the configured-maximum response |
| `0xBC16` (`16 BC`) | `0x1D778` | `0x1EE8C` | stage the destination selector and emit its ceiling |

The B0 handler first requires the global PC-mode byte to be nonzero. It does
not require protected mode 4 or 5. That matters for BLE: the normal display-
owned mode 1 is sufficient, and the fresh BC read immediately before B0 has
the same nonzero-mode gate. The setter at `0x19264` then:

1. obtains the current destination;
2. calls `0x193EE` for that destination's internal ceiling;
3. rejects only if the requested value exceeds that ceiling;
4. accepts equality without rewriting; otherwise persists record `0x28`,
   confirms the write, updates the configured value, and runs the dependent
   recalculation hooks;
5. queues response event `0x2E`, whose matching builder uses key `16 B2`.

`0x193EE` returns 2500 for destination 0, 3218 (`0x0C92`) for destination 1,
2400 for destination 2, and 2500 for destinations 3/4 and the fallback. The BC
response builder at `0x22F1C` echoes the selector and calls this same function;
the B4 builder at `0x22ED8` uses key `16 B6` and reports the configured value.
Therefore a US destination plus B0=3200 is directly accepted by the exact
D4.5.0 policy, assuming the ordinary nonzero session mode remains live. This
is much stronger than client-only packet evidence, but static control flow is
still not a physical-bike result.

The read-only verifier reproduces these bounded facts without printing vendor
bytes:

```sh
python3 tools/inspect_motor_max_assist.py /path/to/DUE5000-D.4.5.0.raw.dat
```

A historical firsthand E6100 report supplies a live, but model-bounded,
cross-check: the bike showed US destination while still limited to 24 km/h;
using E-TUBE's Reset-to-default operation after the region change moved the
maximum to 32 km/h, and the rider reported assistance to that speed after a
power cycle. See the
[2019 E-MTB Forums thread](https://www.emtbforums.com/threads/steps-unlocker-issue.7518/).
That E6100/4.4.0 result supports the separate destination-then-ceiling model;
it is not evidence that this E5000/D4.5.0 bike accepts B0.

## Build 91 at-most-once transaction

The normal authenticated batch retains the two build-88 getters:

1. `B4 00` reads the configured ceiling.
2. `BC 01` reads this motor's US-profile ceiling.

Both require exact reply headers, lengths, destination echo for `BE`, and a
bounded 10–50 km/h decoded value. A device error, timeout, short reply, or
out-of-range value stays undecoded.

The live decision gate is:

- EU plus an ordinary ceiling: continue pursuing a verified US destination.
- US plus a ceiling below `min(BC 01, 3200)`: the destination succeeded but the
  separate maximum still needs a Reset/Apply-equivalent operation.
- US plus a ceiling at that safe target: power-cycle persistence and an actual
  assistance-cutoff ride remain independent checks.

Build 91 implements the second state's transaction without claiming that the
bike accepts it:

1. The ordinary information batch must identify the exact stock
   D4.5.0/M4.4.8 E5000 pair, US destination, and a configured ceiling below
   the safe target. The internal `BC 01` value may be 32.18 km/h.
2. If US came from this page's destination experiment, its same-device
   reconnect record must already say that US persisted. The BLE session and
   motor authentication must both be complete.
3. Immediately before mutation, the page rereads model, application and native
   firmware, destination, `B4`, and `BC 01`. It derives the target as
   `min(BC 01, 3200)`, matching the exact D4.5.0 acceptance bound and Shimano's
   own 32.00 km/h client write.
4. A salted same-device journal containing only hashes and the expected public
   component state is written and read back before `B0` is dispatched once.
5. Exact `B2` is required, followed by the same seven fresh reads and equality
   of `B4` to the target. Rejection, timeout, disconnection, malformed reply,
   or mismatched readback leaves a terminal no-repeat journal.
6. Persistence is a separate, read-only operation. It requires an explicit
   physical-power-cycle checkbox, a different BLE session, the same salted
   Web Bluetooth device, the same exact component pair and US destination, and
   unchanged journaled `BC 01` observation and `B4 ==` the journaled safe
   target. It has no write callback.

`tests/max_assist_write.cjs` covers the exact 32 km/h packet, journal-before-
write order, one-write ceiling, context failures, known rejection, ambiguous
transport, storage failure before mutation, same-device/session gates, and
persistence match/mismatch. The browser test exercises one synthetic B0 and a
second-session power-cycle readback while proving B0 occurs exactly once.
These tests validate software behavior, not BLE acceptance, stored bike state,
or the real assistance cutoff. Build 91 remains local and unpublished; the last
verified physical-bike state is still stock D4.5.0/M4.4.8 at EU.
