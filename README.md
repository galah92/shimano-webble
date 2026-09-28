# Shimano WebBLE

A single-file Web Bluetooth bike-status page for the tested Shimano SC-E7000
endpoint and E50X0 motor family. [Open the HTTPS page](https://galah92.github.io/shimano-webble/).
The first guided action authenticates the BLE session and reads motor identity,
firmware, current destination, configured assist-speed ceiling, and the motor's
US-profile ceiling without changing anything. The guided control exposes a
confirmed, journaled write only when its gates allow one. This bike's build-94
US attempt is now durably recorded, so another setting attempt is disabled;
read-only checks remain available. It never enables a setting retry or firmware
transfer. Raw controls and the sanitized log are collapsed under
**Technical details and log**.

**Current result:** the bike reports native D `4.5.0.0`, M `4.4.8.0`, and EU
destination (`0`) with a configured 25 km/h maximum. In the physical build-94
run, `DB 46` authentication-lock recovery and the SC-E7000-owned mode-5
handshake both completed, but the unchanged-lighting A0 returned `A3 3A`.
No A8 destination command or B0 speed write was sent; reconnect still read EU
and 25 km/h. The durable journal blocks another attempt. Do not press Set US
again or clear that journal. No validated US-region or higher-speed outcome
exists. Builds 76/77 proved that a mode requested directly by the phone
is reclaimed by the SC-E7000 before a later BLE setting command can land.
Display-firmware analysis then found the missing route: local command
`00 0C <mode>` makes the SC-E7000 establish and own protected motor mode 4 or 5
with its built-in secure sequence. Its completion handler records the requested
mode before emitting the completion and does not immediately exit it. The
post-request helper also
disarms the periodic topology-maintenance exit; a fresh event must re-arm that
state machine, so a timer alone cannot recreate the build-76/77 reclaim. The
raw drive-command forwarder likewise has no synchronous re-arm or exit call.
Exact D4.1.0, D4.3.0, and D4.5.0 motor-image checks also show the same
mode-4/5, A0-created one-shot gate before A8; cold boot clears it in all three.
This rules out the tempting theory that old firmware accepted an ungated A8.
Their PC-mode request and fifth-secure-word handlers update separate
slot/mode/counter state and do not arm that destination gate, so successful
mode 5 cannot substitute for A0.

Build 91 retains the read-only discriminator recovered from Shimano's own
historical Cyclist 5.0.2 app. DU-E5000 is explicitly marked as supporting a
separate maximum-assist-speed setting: `00 16 B4 00` reads the configured value,
while `00 16 BC 01` reads this motor's US-profile maximum. Speeds are returned
little-endian in hundredths of km/h. Shimano's Reset action copies the current
destination's maximum into the pending setting and Apply performs a distinct
`B0` write. Consequently a US destination can coexist with a lower configured
ceiling until that second setting is applied. A public 2026 E-TUBE Professional
report independently shows D4.5.0 with destination Type 1 and a 25 km/h
maximum together. The browser reads both values normally. Build 94 exposes the
separate at-most-once stock `B0` step only through the guided button
only after fresh reads prove the exact stock D4.5.0/M4.4.8 pair, persisted US,
and a configured ceiling below the safe 32.00 km/h target. Exact D4.5.0
decompilation now proves direct B0/B4/BC handlers: B0 requires only a nonzero
ordinary PC mode and rejects a request only above the current destination's
internal ceiling. US is internally 3218 hundredths, so the page derives
`min(fresh BC, 3200)` and sends Shimano's exact 3200 client value. It journals
before dispatch, never retries, requires immediate readback, and can claim
persistence only after an explicit physical power cycle in a different BLE
session. This path is synthetically tested but has never been accepted by or
sent to the bike. See
[`max-assist-speed-analysis.md`](docs/evidence/max-assist-speed-analysis.md).

Exact eTuning 3.0.7 code independently confirms the intended sequence. Its
old-generation region flow sends A8; on success it derives 32 km/h for US,
waits 350 ms, and sends the same `00 16 B0 80 0C FF FF` ceiling packet. A
[historical E6100 report](https://www.emtbforums.com/threads/steps-unlocker-issue.7518/)
also describes US destination remaining at 24 km/h until E-TUBE Reset moved it
to 32 km/h. These strengthen the destination-then-ceiling model, but neither
proves that this E5000 on D4.5.0 accepts either write through SC-E7000.

The exact M4.4.8 motor image was also reloaded correctly as Renesas RX at
`0xFFFC0000`. Its real entry is `0xFFFC0018`, and a clean entry-seeded project
recovers 904 functions. The first opcode/constant hits remain rejected as low-
RAM references, instruction encodings, or motor-control tables. An M-side wire
handler is no longer a prerequisite because the D image contains the exact B0
acceptance and persistence policy. That bounded result and the reusable Ghidra
scripts are recorded in
[`m448-max-assist-analysis.md`](docs/evidence/m448-max-assist-analysis.md).

Current eTuning 3.0.7 nevertheless provides a materially stronger stock-BLE
fallback than the static handler alone suggested. Its exact decompiled import
policy allowlists the two files in the public E5000 preparation archive by MD5:
stock D4.3.0 and stock M4.2.1. The app then transfers the accepted unmodified
files; no secret E5000 patch is required by that client path. This makes the
complete paired downgrade, separate-session verification, one bounded region
write, power-cycle proof, and stock restoration a commercially evidenced
no-hardware research candidate. Build 94's A0 rejection and the identical
old-firmware mode/gate checks weaken its causal case for this SC-E7000 bike;
it still needs bike validation and does not explain the direct-A8 gate paradox.
See [`etuning-firmware-policy-analysis.md`](docs/evidence/etuning-firmware-policy-analysis.md).
The paired SC-E7000 4.0.6 comparison likewise has the same display-owned
mode path and identical secure tables as current 4.1.0. Exact SC-E6100 4.0.5,
the display named in contemporaneous DU-E5000 success reports, also has the
same accepted modes, byte-identical mode-1/4/5 tables, retained completion,
and homologous event-driven exit machinery. A display swap or downgrade
therefore adds risk without exposing the missing gate.
Build 91 keeps build 87's visible destination sequence (originally build 82) and uses local mode 5 because Shimano's desktop destination buttons run
inside its protected inspection mode. It requires the display acknowledgement
and exact motor completion, sends one unchanged `A0`, then requires a fresh
display-owned mode-5 handshake before at most one US `A8`. Repeating mode 5 is
safe because mode state is separate from the accepted A0 gate and pending
record; A0 and A8 themselves are never retried. It reads the destination back
and exits via `00 0C 00`. Its salted same-device attempt record is kept in
durable browser storage and blocks another write across reloads, including a
verified non-US result. Synthetic tests validate the ordering and guards, not
acceptance by the bike. Build 91 was published without a bike write; builds
92/93 changed only presentation, guided orchestration, and failure-report
retention around the same guards. The physical build-93 setting action stopped
at a motor `DB` challenge reply, before PC mode or any A0/A8/B0 setting command.
Build 94 retains that reply's non-secret reason byte and follows Shimano's
inspected bounded lock policy: only exact `DB 46` sends one E8, requires EA,
and starts one fresh D8 challenge. The physical test confirmed this recovery
but rejected A0 after mode-5 completion. The exact motor A0 handler accepts
only active mode 4/5 with zero target; the packet/bridge support a zero target,
so mode loss is the leading hypothesis, not a directly observed transition.
The compact log does not show what happened between completion and rejection.
All other DB codes and a second rejection stop; no setting write is retried.

A new offline SC-E7000 queue analysis identifies a different stock-BLE
candidate: its mode-5 request and five secure words are enqueued before local
`2C 00`, and phone-forwarded A0 uses the same normal bus queue. An A0 placed
after that local acknowledgement could follow the handshake before the later
motor completion reaches BLE. This is not bike-tested and no new setting write
is wired. Build 95 adds only a read-only `AC 01` timing
diagnostic after a verified non-US reconnect; it leaves the prior attempt
journal intact. See
[`bridge-analysis.md`](docs/evidence/bridge-analysis.md).

The stock D4.5.0 image also retains the old wheel getter and a gated,
persistent wheel setter. That does not establish BLE acceptance or correct
speed reporting; no wheel write is enabled. See
[`d430-wheel-circumference-analysis.md`](docs/evidence/d430-wheel-circumference-analysis.md).

A separate build-86 research branch constructs, but cannot install, an exact
five-byte D4.5.0.1 derivative. It adds a native version marker and bypasses
only A0's and A8's active-PC-mode rejection branches while retaining the
target check, one-shot gate, pending record, gate consumption, and persistent
write helper. The constructor requires the exact reviewed D4.5.0 source hash,
checks every original byte and the exact derived hash, has no UI caller, and
has never produced a bike-tested image. Its non-installable pair loader accepts
only the exact stock D4.5.0/M4.4.8 restoration pair, derives D4.5.0.1 in memory,
and retains M4.4.8 unchanged. An unwired coordinator now covers durable paired
transfer/replay, a different-session D4.5.0.1 marker gate, one US write,
power-cycle persistence, and same-motor stock restoration. It has no UI caller
and remains unqualified. Exact E-TUBE 3.4.5 IL exposes no flash-read command
and no separate signature operation in its raw address/data/checksum/finish
path, which improves feasibility but cannot prove the resident loader accepts
or boots the image. An unbootable wireless update may require wired recovery.
See [`d450-pc-mode-patch-plan.md`](docs/evidence/d450-pc-mode-patch-plan.md)
and [`d-loader-acceptance-analysis.md`](docs/evidence/d-loader-acceptance-analysis.md).
The same desktop release also defines an E5000 `1UPDATEX-01` boot-patch path,
but no patch payload was found in the reviewed public catalogs, installers, or
archives. It is recovery-architecture evidence, not an available BLE bypass;
see [`d5000-boot-patch-analysis.md`](docs/evidence/d5000-boot-patch-analysis.md).

Build 91 corrects build 87's hidden stock preparation coordinator: only after a
different-session read proves exact D4.3.0/M4.2.1 at EU does it persist an
at-most-once journal, read and preserve the current lighting half, establish
display-owned mode 5, send one `A0`, refresh display-owned mode 5, then send one
US `A8`. It requires exact A2/AA and immediate US
readback, requires another physical-power-cycle proof, and then permits stock
D4.5.0/M4.4.8 restoration. Explicit `AB` rejection, timeout, or an ambiguous
transport result becomes read-only recovery state; the write is never retried.
The entire firmware card remains hidden and unpublished pending explicit live
authorization because an interrupted wireless transfer can require wired
recovery. Synthetic tests do not prove bike acceptance.

Build 87 added a separate, unwired D4.3.0 wheel-circumference fallback, which
build 91 retains unchanged.
Exact eTuning 3.0.7 code reads with `00 35 04 00`, receives
`00 35 06 lo hi`, writes `00 35 00 lo hi`, and recognizes opcode `02` as the
setter success. Shimano specifies a 1300–3000 mm range. Representing a real
2080 mm wheel as 1625 mm should move a nominal 25 km/h cutoff to about 32 km/h,
but makes displayed speed and distance about 21.9% low. The hidden coordinator
journals before its one write, blocks retries, resolves ambiguous outcomes by
read-only reconnect, and requires a physical-power-cycle readback. It has no UI
caller, has not touched the bike, and does not yet authorize firmware
restoration. See
[`d430-wheel-circumference-analysis.md`](docs/evidence/d430-wheel-circumference-analysis.md).

The old wired path does not supply the missing phone recipe. Exact 3.4.5
managed-host tracing shows that E-TUBE sends the caller's ordinary DCAS command
through its generic `0x48` serial framing; it does not secretly insert A0 or
rewrite A8. The independent public `freeMax` client likewise sends complete
ordinary frames directly to PCE1/BCR2. The published E5000 desktop patch calls
A8 during tire-circumference handling, before the worker's later conditional
lighting write, so its shown order cannot satisfy the verified one-shot gate.
Exact SM-PCE02 3.0.4 firmware analysis also shows that its `0x48` handler
forwards `16 A8` unchanged through the ordinary packetizer; there is no narrow
PCE02 A8 special case. PCE1 is identified as a µPD78F1807/78K0R adapter, but
its update-package layout remains undecoded; the published recipe allowed
PCE02, so PCE1-only rewriting cannot explain that recipe. See
[`pce-transport-analysis.md`](docs/evidence/pce-transport-analysis.md).

Start with [HANDOFF.md](HANDOFF.md) for the exact goal, verified results,
failed experiments, decisions, and next evidence needed. [ASSETS.md](ASSETS.md)
lists sources and hashes for material excluded from public Git.
[RESEARCH.md](RESEARCH.md) is the detailed chronological lab notebook; its
older hypotheses must be read with the latest correction. The former
build-by-build README is archived in [docs/README-history.md](docs/README-history.md).

If the private plaintext SC-E7000 4.1.0 image is available, the bounded
display-owned mode analysis can be reproduced without copying it into the
repository:

```sh
python3 tools/inspect_display_pc_mode.py /path/to/SCE7000.4.1.0.dat
```

If the three exact private motor images listed in `ASSETS.md` are available,
the cross-version destination gate can be checked in one read-only run:

```sh
python3 tools/inspect_motor_destination.py /path/to/D4.1.raw.dat \
  /path/to/D4.3.raw.dat /path/to/D4.5.raw.dat
```

The historical display comparison is likewise read-only and accepts the
SC-E6100 control as an optional third input:

```sh
python3 tools/compare_display_pc_mode.py /path/to/SCE6100.4.0.5.dat \
  /path/to/SCE7000.4.0.6.dat /path/to/SCE7000.4.1.0.dat
```

The unpublished motor-patch constructor defaults to a read-only dry run and
will accept only the exact unwrapped D4.5.0 image listed in `ASSETS.md`:

```sh
python3 tools/patch_motor_pc_mode.py /path/to/D4.5.raw.dat
python3 tools/patch_motor_pc_mode.py --self-test
```

The bounded application-startup/integrity checks can be reproduced against the
same three exact private D images used by the destination analysis:

```sh
python3 tools/inspect_motor_image_integrity.py /path/to/D4.1.raw.dat \
  /path/to/D4.3.raw.dat /path/to/D4.5.raw.dat
```

The exact E-TUBE 3.4.5 managed loader audit needs `dnfile` and `dncil` in an
isolated environment and emits only metadata/IL facts:

```sh
python3 -m venv /tmp/shimano-loader-audit
/tmp/shimano-loader-audit/bin/pip install dnfile dncil
/tmp/shimano-loader-audit/bin/python tools/inspect_etube_d_loader.py \
  /path/to/etubedatalinks.dll
```

The current eTuning allowlist can be decoded from the exact JADX output without
committing the APK or firmware:

```sh
python3 tools/inspect_etuning_firmware_policy.py /path/to/C0473Oa.java \
  --xapk /path/to/eTuning-3.0.7.xapk \
  --firmware /path/to/DUE5000-D.5.3.0.dat \
  --firmware /path/to/DUE5000-M.5.2.1.dat
```

The exact historical Cyclist 5.0.2 decompilation can be checked without
printing vendor code:

```sh
python3 tools/inspect_etube_max_assist.py /path/to/jadx-output/sources \
  --apk /path/to/etube-cyclist-5.0.2.apk \
  --etuning-sources /path/to/etuning-3.0.7-jadx/sources \
  --etuning-apk /path/to/etuning-3.0.7-base.apk
```

The desktop boot-patch framework audit uses the same isolated `dnfile`/`dncil`
environment as the loader checker:

```sh
/tmp/shimano-loader-audit/bin/python tools/inspect_etube_boot_patch.py \
  /path/to/etubedatalinks.dll /path/to/etubecommons.dll /path/to/etubedata.dll
```

## Develop and verify

There is no build step. Serve `index.html` locally for UI development:

```sh
python3 -m http.server 8000 --bind 127.0.0.1
```

Use HTTPS on a phone for Web Bluetooth. Synthetic browser tests require
Python Playwright and its Chromium browser; they use simulated GATT responses,
not the bike:

```sh
python3 -m pip install playwright
python3 -m playwright install chromium
python3 tests/browser.py
python3 tests/region_write.py
python3 tests/log_export.py
node tests/region_compatibility.cjs
```

GitHub Pages serves the repository root from `main`. Verify the Pages workflow
and the live page after publishing a change. No private files or external
analysis directory are required to run the page or these tests.
