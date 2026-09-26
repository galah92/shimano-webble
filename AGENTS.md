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

Local build 91 keeps build 82's bounded destination experiment unchanged. It sends `00 0C 05`,
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
unchanged-A0 design
remains the next evidence-backed test.
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
current destination's ceiling; US is internally 3218 hundredths. The local
Advanced-diagnostics path therefore derives `min(fresh BC, 3200)`, which is
3200 and matches Shimano's clients. It is gated by the exact stock pair,
persisted US, a fresh lower B4 value, and motor authentication. It journals
both BC and target before one dispatch, never retries, requires exact B2 plus
immediate fresh readback, and permits only read-only persistence verification
after an explicit power cycle in a different session. It has synthetic tests
but no bike result and remains unpublished.
The M4.4.8 image is RX at `0xFFFC0000`; its real entry is `0xFFFC0018` and a
clean entry-seeded project recovers 904 functions. Its false opcode hits do not
override the D-side policy.
The public Pages site still serves build 77 until a separately authorized
publish.

The last verified destination is EU and no higher-speed result exists. The
paired BLE downgrade remains the riskier fallback; no image has ever been sent
to this bike. Keep private passkeys, raw captures, serials, and vendor binaries
(including display and motor images) out of the public repository.
