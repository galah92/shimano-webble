# Agent handoff

Read [`HANDOFF.md`](HANDOFF.md) first, then the latest correction at the end of
[`RESEARCH.md`](RESEARCH.md). [`ASSETS.md`](ASSETS.md) lists sources and hashes;
there is no required `~/shimano-analysis` dependency.

Build 76 recovered and reverse-engineered the SC-E7000 4.1.0 display image (the
bridge-mapping evidence the prior handoff lacked). It established that the `A0`
framing was always valid (the motor's offset+4 target byte is the packet's
leading `00`, confirmed against the working `00 16 AC 01` read) and that the
phone's PC-mode commands do reach the motor. So `A3 3A` was never a framing
problem: the motor's PC mode 4/5 is not live when `A0` lands, dominated by the
SC-E7000's own hardware watchdog reset. The page re-enables a tightened,
instrumented mode-4 burst attempt (`A0`→`A8` back-to-back) under Advanced
diagnostics; the current EU destination and the absence of a *verified* US write
still stand, and synthetic tests do not prove bike acceptance. The next step is
one instrumented bike test, not more offline framing analysis. Keep private
passkeys, raw captures, serials, and vendor binaries (including the display
image) out of the public repository.
