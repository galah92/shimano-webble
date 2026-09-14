# Agent handoff

Read [`HANDOFF.md`](HANDOFF.md) first, then the latest correction at the end of
[`RESEARCH.md`](RESEARCH.md). [`ASSETS.md`](ASSETS.md) lists sources and hashes;
there is no required `~/shimano-analysis` dependency.

Build 76 recovered and reverse-engineered the SC-E7000 4.1.0 display image (the
bridge-mapping evidence the prior handoff lacked). It established that the `A0`
framing was always valid (the motor's offset+4 target byte is the packet's
leading `00`, confirmed against the working `00 16 AC 01` read) and that the
phone's PC-mode commands do reach the motor. So `A3 3A` was never a framing
problem: the motor's PC mode 4/5 is not live when `A0` lands. The build-76 live
test settled why: after a real mode-4 completion, `A0` was rejected ~74 ms later
with the BLE link still up and no display reset, so the SC-E7000 reclaims the
motor's global PC-mode state within ~55 ms of the grant — faster than the first
BLE command can land. Build 77's pipelined `A0`→`A8` burst with per-run retries
was tested (2026-09-14) and **conclusively ruled out phone-only**: `A0` rejected
`A3 3A` at 59–67 ms across four cycles, deterministic, region unchanged. The
~60 ms reclaim is shorter than one BLE round-trip, so no phone-only build can
win — use the wired SM-PCE adapter (writes destination=US directly, no
downgrade) or a firmware downgrade; do not iterate phone-only builds. The
current EU destination and the absence of a *verified* US write still stand, and
synthetic tests do not prove bike acceptance. Keep private passkeys, raw
captures, serials, and vendor binaries (including the display image) out of the
public repository.
