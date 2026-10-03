# Agent handoff

Read [`HANDOFF.md`](HANDOFF.md) first, then the latest correction at the end of
[`RESEARCH.md`](RESEARCH.md). [`ASSETS.md`](ASSETS.md) lists sources and hashes;
there is no required `~/shimano-analysis` dependency.

Builds 76/77 proved that a phone-owned motor mode 4 is reclaimed by the
SC-E7000 within 59-74 ms, before a post-completion BLE command can land. The
2026-09-24 display-firmware review found the missing ownership path: the
display-local command `00 0C <mode>` accepts modes 0, 1, 4 and 5. For mode 4/5
the SC-E7000 itself sends the motor request and its five built-in secure words.
This is the same display-owned mechanism used by the captured official setup
command `00 0C 01`; it avoids competing with the display for the motor's single
global mode byte.

Build 94 keeps build 93's UI/reporting, build 91's setting protocol, and build 82's bounded destination
experiment unchanged. It sends `00 0C 05`,
requires both display reply `2C 00` and exact motor completion
`00 32 12 05 <slot>`, then sends one unchanged-lighting A0. Only after A2 does
it require a second full display-owned mode-5 handshake before one US A8. It
requires AA and a fresh US readback, exits through `00 0C 00`, and never sends
direct phone category-32 mode traffic or firmware. A0 and A8 are never retried;
the second mode handshake is safe because it does not consume the separate A0
gate or pending record. Mode 5 matches Shimano's desktop destination panel.
Builds 79/80 were never published or bike-tested. Synthetic tests prove the
guards and ordering, not bike acceptance. Its salted same-device attempt
journal is durable and blocks a repeat across reloads, including after a
verified non-US reconnect result.
Exact D4.1.0 comparison now proves that the A0-created one-shot A8 gate and
cold-start clearing predate D4.3; downgrade compatibility is not explained by
an ungated old destination handler. Build 91's refreshed-mode-5 plus
unchanged-A0 design was physically tested in build 94 and rejected at A0;
see the latest correction at the end of `RESEARCH.md`.
Exact D4.1/D4.3/D4.5 PC-mode handlers also prove that request and fifth-word
promotion update separate slot/mode/counter state without arming the
destination gate; mode 5 cannot substitute for A0.
Exact SC-E7000 4.0.6 comparison also shows the same owned modes and identical
secure tables as 4.1.0; do not add a display downgrade.
Exact E-TUBE 3.4.5 transport tracing now also rules out a hidden host-side A0
or A8 rewrite. The public `freeMax` client sends normal DCAS frames directly to
PCE1/BCR2, while the published wired patch sends A8 before the worker's later
conditional A0. Exact SM-PCE02 3.0.4 firmware analysis now also proves that its
`0x48` path forwards `16 A8` unchanged through the ordinary packetizer: it does
not inject A0 or rewrite A8. PCE1 is identified as µPD78F1807/78K0R, but its
update-package layout and running image remain undecoded; see
`docs/evidence/pce-transport-analysis.md`.
Exact D4.3.0/D4.5.0 comparison now also maps every located active-mode
reference across the fixed code relocation. A commercial-style rebooted D4.3
plus direct A8 is therefore not a complete causal recipe for this topology.
Build 91 therefore corrects the hidden D4.3 fallback to read and retain the
lighting half, use display-owned mode 5, send one A0, refresh display-owned
mode 5, and only then send one A8. As a separate, unpublished recovery branch,
build 91 contains a fail-closed,
unwired constructor for an exact five-byte D4.5.0.1 derivative that NOPs only
the A0/A8 active-mode rejections and adds a readback marker. It preserves A0's
one-shot gate and A8's persistent write. A non-installable loader now derives
that D image in memory only from the exact stock D4.5.0/M4.4.8 pair. Its
offline coordinator now persists patch-specific paired-transfer/replay,
D4.5.0.1 reconnect, one-write/persistence, and stock-restoration lineage, but
has no UI caller and no modified image has been sent to the bike. Exact E-TUBE
3.4.5 IL enumerates no flash-read command and sends host binary data through
address/data/additive-checksum/finish/reset without a separate signature
operation. This strengthens acceptance plausibility but cannot inspect the
resident loader; an unbootable image can still remove BLE recovery. See
`docs/evidence/d450-pc-mode-patch-plan.md` and
`docs/evidence/d-loader-acceptance-analysis.md`.
Build 91 retains the B4 and BC getters for the configured maximum-assist speed
and motor's US-profile ceiling. Shimano Cyclist 5.0.2 proves those getters and
a separate B0 setter; a public 2026 E-TUBE Professional report independently
shows D4.5.0 with destination Type 1 and a 25 km/h maximum simultaneously.
Exact D4.5.0 decompilation now proves explicit B0/B4/BC handlers. B0 requires
only nonzero ordinary PC mode and accepts any request no higher than the
current destination's ceiling; US is internally 3218 hundredths. The guided
path therefore derives `min(fresh BC, 3200)`, which is
3200 and matches Shimano's clients. It is gated by the exact stock pair,
persisted US, a fresh lower B4 value, and motor authentication. It journals
both BC and target before one dispatch, never retries, requires exact B2 plus
immediate fresh readback, and permits only read-only persistence verification
after an explicit power cycle in a different session. It has synthetic tests
but no bike result and has never been sent to the bike.
The M4.4.8 image is RX at `0xFFFC0000`; its real entry is `0xFFFC0018` and a
clean entry-seeded project recovers 904 functions. Its false opcode hits do not
override the D-side policy.
Build 91 was published on 2026-09-26. Build 92 changes only the UI and guided
orchestration: one contextual button performs the read-only check, exposes the
separately confirmed at-most-once US write when eligible, then read-only
power-cycle verification, the separately confirmed at-most-once 32 km/h write
when eligible, and final read-only verification. Detailed telemetry, log, and
manual protocol controls are collapsed. Build 93 changes only compact-report
selection so the latest motor-authentication or setting failure is retained
across a later read-only reconnect. The recovered physical build-93 report
stopped at a motor `DB` challenge rejection before any PC mode, A0, A8, B0, or
attempt journal. Build 94 records the non-secret DB reason byte. Only exact
`DB 46` may send one E8, require EA, and start one fresh D8 challenge, matching
the inspected Shimano desktop caller; every other code and a second rejection
stop without a loop. No setting command is retried. The firmware card remains
hidden.

Physical build 94 on 2026-09-27 recovered exact `DB 46` with one E8/EA and a
fresh D8, then completed the display-owned mode-5 handshake. It sent one
unchanged-lighting A0 15.5 ms after completion; the motor explicitly returned
`A3 3A`. No A8 or B0 was sent. A read-only reconnect reported EU/25 km/h.
The same-device journal blocks another US attempt. Exact D4.5.0 A0 code rejects
for non-4/5 active mode or a nonzero normalized target; the known bridge and
packet support zero target, making mode loss the leading but unmeasured cause.
Do not repeat A0 or clear the journal. Request the full on-page log and screen
restart observation before inferring the transition or preparing any new live
test. D4.3 retains the same checks, so a paired BLE downgrade is not yet a
causal fix and carries wired-recovery risk; the patched-D branch remains hidden.
New exact SC-E7000 queue analysis finds that local `0C 05` enqueues the motor
request and five secure words before `2C 00`; phone A0 reaches the same normal
bus FIFO and none of those opcodes is in its initialized priority table.
Placing A0 after local acknowledgement but before motor completion is a
distinct untested stock-BLE hypothesis. The verifier and limitations are in
`tools/inspect_display_pc_mode.py` and `docs/evidence/bridge-analysis.md`.
No early A0 write or journal bypass is enabled. Build 95
adds a read-only AC timing probe after the verified non-US attempt record;
synthetic tests do not establish bike behavior.
Build 96 matches build 94's bounded motor authentication before that probe and
passively records redacted category-32 request/completion/rejection headers
from entry through exit. It adds local-acknowledgement timing and explicit
verdicts. Silence is not proof that mode 5 was retained; AC timing is not A0
permission. The owner's screen-restart recollection is unknown. October 3
Reddit/GitHub/vendor research found no exact known-good stock D4.5.0/M4.4.8 +
SC-E7000 destination trace; see `reports/Shimano stock BLE next step.md`.
Build 96's publication must be verified before a live instruction. No US-setting
result, journal clear, new setting write, or firmware transfer exists.
The owner's physical build-96 report confirms that
authentication and mode 5 completed, AC's ATT acknowledgement arrived 54.7 ms
after motor completion, and its EU reply followed by 54.9 ms. Early admission
is inconclusive; no different mode was surfaced. Disconnect occurred during
the requested mode-0 exit and is not evidence of a preceding unsolicited
transition. No setting/firmware write or journal clear occurred. Do not repeat
the same probe; preserve the full on-page exit tail and screen observation.
Build 97 changes only report export: the existing Copy full report button
includes the retained selected session's routine exit lines. The storage key
is unchanged; a same-tab reload can retrieve build 96 without a new bike run.
Build 98 replaces that same button with Copy diagnostic report: latest queue
probe lines plus baseline, keeping routine exit TX/ATT/RX within a chat-sized
export. The full log and journal are untouched. No new bike run is required.
The exact stock D4.5.0 image retains the category-35 wheel getter and a
nonzero-PC-mode, source-gated persistent setter. This corrects the assumption
that the handler was removed after D4.3; it does not establish BLE acceptance
or an accurate-speed workaround. No wheel write is wired; inspect the exact
hash with `tools/inspect_d450_wheel.py`.

The last verified destination is EU and no higher-speed result exists. The
paired BLE downgrade remains the riskier fallback; no image has ever been sent
to this bike. Keep private passkeys, raw captures, serials, and vendor binaries
(including display and motor images) out of the public repository.
