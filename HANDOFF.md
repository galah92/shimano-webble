# Shimano WebBLE handoff — 2026-09-26

## Objective and current answer

The goal is a reproducible, phone-only HTTPS Web Bluetooth workflow that sets
this bike's OEM destination to US (`1`), confirms the value on the same motor
after a physical power cycle, and separately measures the assistance cutoff.
Destination `1` selects the US profile, whose supported ceiling is 32 km/h
(~20 mph), while keeping the speedometer correct; a separate configured
maximum can nevertheless remain at 25 km/h and must be verified independently
(codes: `0` EU, `1` US, `2` Japan, `3` Taiwan, `4` Korea).

**No validated US-setting workflow exists yet.** The last verified destination
is EU (`0`); no speed increase has been demonstrated. Builds 76/77 established
that the SC-E7000 forwards PC-mode and setting commands correctly but reclaims
the motor's global PC-mode state 59-74 ms after the mode-4 completion. They
conclusively rule out sending a later setting command after a
*phone-originated* mode completion while the display retains ownership.

A new branch closes an important post-destination ambiguity. Shimano
Cyclist 5.0.2 explicitly marks DU-E5000 as supporting a separate configured
maximum-assist-speed value. It reads that value with `00 16 B4 00` / `B6` and
the motor's destination-specific US ceiling with `00 16 BC 01` / `BE`; values
are little-endian hundredths of km/h. Reset copies the current destination's
ceiling into pending settings and Apply uses a distinct `B0` setter. Therefore
US destination readback alone does not prove that the separate ceiling is 32
km/h. A public January 2026 E-TUBE Professional 5.4.4 report independently
shows D4.5.0 with destination Type 1 and a 25 km/h maximum at the same time.
Build 91 keeps both getters in the normal information batch and adds a `B0`
transaction that can arm only after the exact stock
D4.5.0/M4.4.8 pair has persisted US and still reads a lower configured ceiling
than the safe 32.00 km/h target. It journals before one write, requires `B2` and immediate fresh
readback, cannot retry, and separates a later same-device/different-session
power-cycle readback from the write. This is synthetic implementation evidence,
not a bike result. The exact evidence and limits are in
[`docs/evidence/max-assist-speed-analysis.md`](docs/evidence/max-assist-speed-analysis.md).

Exact eTuning 3.0.7 now independently confirms the intended continuation. Its
old-generation region activity sends direct A8; the successful callback derives
32 km/h for US, waits 350 ms, and calls a writer that emits the identical
`00 16 B0 80 0C FF FF`. A firsthand E6100/4.4.0 report likewise describes US
remaining at 24 km/h until E-TUBE Reset moved the maximum to 32. Both support
the destination-then-ceiling model but remain version/model-bounded and do not
prove SC-E7000/D4.5.0 acceptance on the bike.

Exact D4.5.0 decompilation now closes the stock-setter policy gap. Its
cumulative dispatcher has explicit `16 B0`, `16 B4`, and `16 BC` cases. B0
requires only a nonzero ordinary PC mode, parses the requested u16, and calls a
persistent setter that rejects only values above the current destination's
ceiling. Destination 1's internal ceiling is 3218 hundredths, while Shimano's
clients request 3200. Success queues the matching `B2` builder. Thus stock
D4.5.0 directly permits the exact build-91 B0 after US; live transport and
persistence remain unverified. The M4.4.8 image is separately mapped as RX at
`0xFFFC0000`; seeding its real entry `0xFFFC0018` recovers 904 functions, but
its apparent opcode hits remain false. An M-side wire handler is no longer
expected because D contains the acceptance and persistence policy.

The 2026-09-24 review found a stronger untested distinction. The SC-E7000's
BLE/display-local `0C` handler explicitly accepts modes 0, 1, 4 and 5. For
modes 1/4/5 it constructs the motor PC-mode request and queues the five secure
words itself. The supplied official capture already demonstrates this
display-owned route for `00 0C 01`: display acknowledgement `2C 00`, then motor
completion `00 32 12 01 0D ...`. Builds 76/77 instead requested motor mode
directly from the phone while the display still owned its connection; their
rapid mode loss is an ownership collision. `00 0C 04` or `00 0C 05` makes the
display own the protected handshake and avoids the already observed
phone-versus-display ownership collision. A further trace through completion
handler `0x21d2c` shows that the display stores the requested mode in its own
active-mode field before it
emits the motor completion and makes no mode-0 or cleanup call on that path.
The post-request helper also clears the periodic topology-maintenance trigger;
the tick cannot enter the exit state machine unless a fresh lifecycle/topology
event re-arms it. A timer alone therefore cannot reproduce the build-76/77
reclaim. The raw drive-command enqueue and full-copy formatter also have no
direct call into the re-arm, mode-0, or cleanup paths, so receipt of A0 does not
synchronously cancel the display-owned protected mode before forwarding it.
The remaining untested premise of build 91's unchanged visible destination sequence is
narrower: whether the motor
accepts the following bridged A0 before any independent asynchronous topology
event.

An exact historical D4.1.0 cross-check closes the firmware-version loophole:
D4.1, D4.3, and D4.5 all use the same mode-4/5, A0-created one-shot gate before
A8, and all cold-start zero ranges cover that gate. The E-TUBE 3.4.5
destination buttons call A8 directly, but their executable has no hidden A0 in
those button handlers. They prove mode context and packet arguments, not a
self-contained transaction. Downgrade compatibility is therefore not explained
by an ungated old handler; its advantage must lie in compatibility or retained
state elsewhere in the older system.

The contemporaneous SC-E7000 4.0.6 display image also has the same local
mode-0/1/4/5 ownership path, the same three secure tables, retained successful
completion, and a trigger-disarmed maintenance path as 4.1.0. Current 4.1.0
actually clears one additional maintenance phase byte. No evidence supports
adding a display downgrade; it would increase flashing risk without satisfying
the motor's separate A0 gate.

The exact SC-E6100 4.0.5 image closes the display-model loophole raised by the
2020 DU-E5000/SC-E6100 success reports. Its local handler accepts the same
0/1/4/5 modes, all three five-word secure tables are byte-identical to both
SC-E7000 images, successful completion retains the requested mode, and its
trigger-disarmed/event-rearmed exit machinery is homologous. This does not
reproduce old runtime timing or client-created state, but it rules out a
different SC-E6100 key table or an obvious permissive display lifecycle. A
display swap, emulation target, or SC-E6100 firmware port is therefore not a
supported next route.

Exact PC-mode handler checks also show that mode 4/5 completion never arms the
destination gate in D4.1, D4.3, or D4.5. The request and fifth-secure-word paths
only update the slot/mode/counter state; the separate gate is still created by
A0. Mode 5 gives build 91 the best-supported ownership and client context, but
does not remove the need for its explicit unchanged A0.

The old wired success report does not reveal a host-side prerequisite. A full
E-TUBE 3.4.5 managed call-chain trace reaches generic `0x48` DCAS serial
framing without inserting A0 or rewriting A8. The public `freeMax` executable
independently writes complete ordinary DCAS frames straight to PCE1/BCR2. In
the patched desktop worker, SetDestination runs inside SetTireCircumference,
before the only later conditional SetLightingTime call, so the shown order
cannot satisfy the motor's verified A0-created gate. This rules out normal
managed-host magic. Exact SM-PCE02 3.0.4 firmware analysis further proves that
its generic `0x48` handler copies `16 A8` unchanged and selects its ordinary bus
packetizer; the adapter neither injects A0 nor rewrites A8. PCE1's public board
identifies a µPD78F1807/78K0R MCU, but its update-package layout remains
undecoded; the published recipe allowed PCE02. Retained state, an omitted
command, a different firmware context, or another omitted workflow step remain
possible.

The page source is now build `2026-09-26.94`. Build 91 was published; build 92
reduced the normal interface to one contextual
button. **Connect and check bike** remains read-only and reports both
assist-speed ceilings. Only after those reads prove eligibility does that same
button become **Set US region once**. Subsequent states expose only read-only
power-cycle verification, then—if US persisted with a lower ceiling—**Set 32
km/h once**, followed by its read-only power-cycle verification. Each write has
a separate confirmation. The detailed telemetry, sanitized log, and old manual
buttons are collapsed under **Technical details and log** → **Manual protocol
controls**. Build 93 also keeps the connection containing the latest motor
authentication or setting attempt in the compact report even after a later
read-only reconnect. The recovered build-93 physical report stopped at a motor
`DB` challenge rejection, before PC mode, A0, A8, B0, or either attempt
journal. Build 94 retains the DB reason byte and adds Shimano's bounded
authentication-lock branch: only exact `DB 46` sends one E8, requires EA, and
starts one fresh D8 challenge. Any other DB code, unlock failure, or second DB
stops without a loop. This does not retry a setting write. Build 91's retained destination branch
is gated by the exact D4.5.0/M4.4.8 pair, EU readback, motor authentication, and
no prior attempt. It reads the current lighting value, sends display-local
`00 0C 05`, requires `2C 00` and the exact motor mode-5/slot completion, sends
one unchanged A0, and only on A2 requires a second complete display-owned
mode-5 handshake before one US A8. It requires AA and fresh US readback, then
exits through `00 0C 00`. It never sends direct phone category-32 mode traffic
or firmware and never retries A0 or A8. The refresh is safe because mode
request/promotion neither consumes the A0 gate nor changes its pending record,
and the SC-E7000 forwards same-mode requests again. Synthetic tests prove the
intended ordering and guards, not bike acceptance. Mode 5 is selected because
the exact Shimano desktop inspection panel that exposes the destination
buttons uses protected mode 5; builds 79-81 were neither published nor tested
on the bike. Build 91 also writes a salted same-device attempt record to
durable browser storage before privileged mode. Once any command attempt is
recorded, the setter stays disabled across reloads and after either US or
non-US reconnect verification. If A0 may have run without A8, the status also
requires a physical bike power cycle before another setting tool.

Build 91 adds a second, independent stock maximum-assist `B0` setter, exposed
by build 94 only when it is the next eligible guided action. It remains disabled
at EU and therefore cannot run
in the last verified bike state. Its gate requires a verified/authenticated
session, motor authentication, the exact stock pair, US destination, both
speed getters, current below the safe 32.00 km/h target, and—if this page
performed the destination attempt—a prior same-device reconnect proving US.
Immediately before mutation it rereads model, application/native versions,
destination, B4, and BC. The salted durable attempt journal must persist before
the one `00 16 B0 lo hi FF FF` dispatch. Exact B2 and a second full fresh-read
set must show B4 equal to the journaled target while BC remains unchanged. All failure and ambiguity paths block
a repeat. A later explicit physical-power-cycle checkbox and different BLE
session permit only read-only same-device persistence verification. The target
cannot be typed and is capped at 32 km/h. No B0 has been sent to the bike.

If build 91's destination branch fails after exact display acknowledgement and motor completion,
two no-new-hardware firmware branches remain. The existing paired BLE
preparation workflow can install exact D4.3.0/M4.2.1 and later restore
D4.5.0/M4.4.8. Current eTuning 3.0.7's exact MD5 allowlist now proves that its
firmware importer accepts those two public, stock preparation files; transfer
code passes their unwrapped bytes onward without a hidden E5000 patch. This
makes the paired BLE downgrade the strongest no-new-hardware fallback, although
exact static comparison still shows that D4.3 retains the same PC-mode and
one-shot A0/A8 gates and the commercial success path is not yet a complete
causal recipe for this SC-E7000 topology. Build 91 corrects this route's hidden
coordinator: after exact-pair reconnect verification and a durable journal it
reads and preserves the current lighting half, uses display-owned mode 5,
sends one A0, refreshes display-owned mode 5, and sends one A8. Exact A2/AA,
immediate US readback, a separate physical-power-cycle persistence gate, and
exact stock restoration are required. An explicit rejection or ambiguous transport
result cannot retry the mutation. The card remains hidden and unpublished.
A newer, unpublished branch derives
an exact five-byte D4.5.0.1 image that bypasses only A0/A8's active-mode
rejections while preserving their one-shot transaction and persistent helper.
Its fail-closed constructor, exact-stock-pair loader, paired transfer/replay,
D4.5.0.1 reconnect gate, one-write/persistence lineage, and stock-restoration
lineage are implemented and synthetically tested. They have no UI caller and
are not authorized for this bike. Neither branch has sent an image to it.
Wireless flashing has a real interruption risk that can require wired SM-PCE
recovery.

Build 87 adds a distinct wheel-circumference fallback for the exact prepared
D4.3.0/M4.2.1 EU state. Exact eTuning 3.0.7 code establishes getter
`00 35 04 00`, reply `00 35 06 lo hi`, setter `00 35 00 lo hi`, setter-success
opcode `02`, immediate readback, and the 1300–3000 mm range. For a measured
2080 mm wheel, representing 1625 mm targets about 32 km/h from a 25 km/h
baseline, while making speed and distance read about 21.9% low. The local
branch is unwired, journals before one setter, never retries an ambiguous
write, and requires read-only reconnect plus a physical-power-cycle proof. It
does not yet authorize restoration because D4.5.0 getter behavior must first be
proved. This is a separate fallback, not a claim that destination changed.

The exact D4.1/D4.3/D4.5 application startup paths now provide bounded positive
feasibility evidence for the patch. Each entry reaches only the ordinary
RAM-zero/ROM-copy runtime initializer before `main`; each declared image-size
value occurs only in its header, while the corresponding computed image-end and
size-field pointer are absent. The structured tail has no identified opaque
signature trailer. This reduces the application-self-check concern but does
not inspect the resident bootloader, exclude a computed/external integrity
record, or guarantee BLE recovery. The final image checksum supplied to the
loader remains necessary but is not bootability proof. Exact E-TUBE 3.4.5 IL
also exposes no flash-read request and no separate signature operation in the
host-binary/address/data/additive-checksum/finish/reset path. That makes the
patch more plausible and simultaneously confirms that the reviewed BLE clients
cannot first dump a recovery copy of the resident loader. It still does not
reveal the loader's internal acceptance policy.

The same 3.4.5 desktop assemblies define a genuine DU-E5000 boot-patch spec:
substrate 1, base `UPDATEX`, bootloader 5.0.0 revision 01, yielding filename
stem `1UPDATEX-01`. The updater validates a BootPatch file, compares its version
to the reported bootloader, and reuses the ordinary update sender. No matching
payload was found in the reviewed public catalogs, archived installers, or
source indexes, so this is not currently an actionable recovery or unlock
route. See `docs/evidence/d5000-boot-patch-analysis.md`.

## Verified bike baseline

| Item | Observed result | Evidence |
| --- | --- | --- |
| Wireless/display endpoint | SC-E7000 (`SCE7000`) after two session-auth acknowledgements and `2AFF: FF 00` | User logs, `RESEARCH.md` |
| Drive-unit identity | E50X0 family (exact casing variant not established) | Model read `00 01 1E 22 00` |
| Native motor firmware | D `4.5.0.0`, M `4.4.8.0` | `84 00/01` reads and `86` replies |
| OEM/current destination | EU, value `0` | `AC 01` → `AE 01 00`; independently repeated after reconnection |
| BLE session authentication | Both 2AF3 stages acknowledged | `10 01 01`, `10 02 01` |
| Motor challenge-response | Completion marker observed | `00 16 E2 FF FF` |
| Regulation unlock | `E8` received `EA` | Live builds .65 onward |
| Wireless application slot | `0D` | 2AFD mode announcement; accepted mode completions echo `0D` |
| PC-link modes | Mode 1, then modes 4 or 5 accepted in different trials | `00 32 12 <mode> 0D` |

These are protocol observations, not evidence that the motor granted a
destination-write permission. `ATT write completed` only means the Bluetooth
write completed. The user's reported display reset during build .73 has no
timestamped cause in the compact log; do not call it a physical power cycle.

## Decisive experiments and decisions

1. **Session transport, builds .3–.8:** both auth stages alone did not make
   `2AF7` readable. Sending the captured `2AFF: FF 00` did. Subsequent setup
   commands enabled motor replies on `2AFD`; display replies use `2AF9`.
2. **Region baseline, builds .13–.18:** `AC 00` and `AC 01` replied `AE 00 00`
   and `AE 01 00`. D/M native reads were 4.5.0/4.4.8. Model family is E50X0.
3. **Direct setter, builds .15–.16:** after motor authentication, one
   `00 16 A8 01 01` returned `00 16 AB 3A 00`. Reconnection read EU. This is
   a command rejection, not a successful region change.
4. **Firmware route, builds .41–.63:** offline eTuning policy routed D4.5.0
   through preparation; exact original and historical images were identified.
   Bootloader entry/exit probes and readbacks did not change the original
   firmware or region. The live D-recovery stage returned FIRMUP `12` or
   timed out, including bounded retries. No firmware image was sent. The user
   prefers avoiding a firmware change. Build .64 corrected the first-use path
   to ordinary bootloader entry, which build .45 had already verified live, but
   .64 itself was never live-tested.
5. **Original-firmware command path, builds .65–.73:** D4.5.0 static analysis
   found an `A8` handler gated by PC mode 4/5 and an internal one-shot flag.
   Motor auth, `E8/EA`, wireless slot `0D`, and exact mode-1/mode-4 or mode-5
   completions were achieved. Guessed staging variants failed with `A3 3A`.
   Build .73 sent Shimano's seven-byte unchanged lighting-time packet
   `00 16 A0 0A 00 FF FF` after accepted mode 4; it also returned `A3 3A`.
   Mode exit completed. **No `A8` was sent in these later trials.**
6. **Offline correction, 2026-09-12:** desktop `SetDestination` and
   `SetLightingTime` are separate UI actions; the Android region task sends
   `A8` directly. There is no known-good client trace that stages unchanged
   lighting time first. The A0 prerequisite was an inference from the motor
   handler, and repeating A0 variants is not justified. Build .74 parks the
   setter and restores a guided read-only bike check.
7. **Bridge and timing, builds .76–.77:** the recovered display image proved
   forwarding and framing correct. Live A0 rejection at 74 ms, then 59-67 ms
   across four pipelined cycles with the link up, proved that any command sent
   after the mode-completion notification is too late.
8. **Cross-check, 2026-09-24:** D4.3.0 retains the same A0/A8 mode and one-shot
   gates. Its complete startup table first zeroes the RAM range containing the
   gate; its only other record decompresses data only through `0x20000577`, far
   below the gate. An expanded direct-, nearby-base-, and standard bulk-writer
   audit still finds A0 as the only gate setter. D4.5 has the same two-record
   structure. Current eTuning and eMax nevertheless issue direct A8 from their
   destination actions, so those call sites establish packet shape but leave
   prior state unexplained. Vendor compatibility tables agree that the exact
   D4.3.0/M4.2.1 pair supports the Bluetooth operation.
9. **Build .78:** sends unchanged A0 then direct A8 after the fifth secure ATT
   completion but before waiting for mode completion. This ordering has
   synthetic coverage but no bike result and is superseded by the ownership
   finding below.
10. **Display-owned mode and build .79:** SC-E7000 handler `0x236fc` accepts
    local modes 0/1/4/5; builder `0x212ac` emits the motor request and five
    mode-specific secure words. Historical eTuning's `32 B4` and display `0D`
    commands were separately traced and are read-only, so they are not hidden
    gate setters. The category-16 A0/A8 handlers were further traced: A0 fills
    the first five bytes of an 11-byte pending settings record and sets the
    volatile one-shot flag; A8 fills the adjacent six bytes, clears the flag,
    and reaches the record helper. Replaying the freshly read A0 half therefore
    preserves the unrelated fields. No mode-4/5-specific read-only probe was
    found; the similarly named category-32 A0 follows a separate update path.
    Build 79 uses local `0C 04`, then bounded A0/A8, and exits with local
    `0C 00`. The secure completion handler records mode 4 before emitting
    opcode `12` and has no immediate exit call. The post-request helper clears
    the periodic topology-maintenance trigger, so its separate mode-0 paths
    require a fresh lifecycle/topology event before they can run; an existing
    timer alone cannot recreate the build-76/77 reclaim. Build 79 has synthetic
    coverage and no bike result.
11. **Current-client cross-check:** eTuning 2.0.7 versus 2.0.8 shows the
    advertised E5000 assistance-save fix is the same ordinary category-16
    opcode-`98` write path, not a destination or PC-mode change. A complete
    decoded-literal and call-chain audit of STUnlocker Android 1.21.157 likewise
    finds direct A8 for market, A0 for lighting time, and display-local `0C 01`,
    but no local `0C 04`/`0C 05`. The authentic, same-signer 1.20.153 package has
    the same market path and local-mode inventory. These public clients confirm
    the packet roles but expose no second D4.5 privilege path; unavailable
    pre-1.20 packages remain an explicit evidence gap.
12. **Mode selection and build .80:** the older E-TUBE 3.4.5 inspection panel
    contains the actual factory/OEM destination buttons and establishes
    protected mode 5 around those controls. Because the D4.5 handlers accept
    both 4 and 5 and the display-local handler owns both identically, mode 5 is
    the closer known-good destination-setting context. Build 80 changes build
    79's local request and exact completion requirement from 4 to 5; all
    at-most-once, readback, exit, identity, and no-firmware guards remain. Build
    79 was never published or bike-tested.
13. **D4.1 historical control, 2026-09-24:** exact D4.1.0 has the same A0-set,
    A8-consumed one-shot gate as D4.3/D4.5, and its startup zero record covers
    that gate. The 3.4.5 desktop executable has only the two visible
    `SetDestination` button callers and no nested lighting-time call. This
    rules out an ungated-old-firmware explanation but leaves earlier setup or
    retained state unresolved. Build 82 remains the narrowest original-
    firmware experiment.
14. **SC-E7000 4.0.6 historical control:** exact 4.0.6 and current 4.1.0 have
    identical mode-1/4/5 secure tables and parallel owned-mode completion and
    maintenance call graphs. Version 4.1.0 clears one extra maintenance phase
    byte after a request. Display downgrade supplies no missing gate and is not
    part of the next experiment.
15. **SC-E6100 4.0.5 historical control:** the exact image named by old
    DU-E5000 success reports accepts local modes 0/1/4/5 and uses byte-identical
    mode-1/4/5 secure tables to both SC-E7000 controls. Its successful
    completion and event-driven maintenance/exit call graphs are homologous;
    no different display secret or obvious permissive lifecycle was found.
16. **PC-mode/gate isolation:** in exact D4.1/D4.3/D4.5 images, request mode,
    application slot, active mode, and the five-word counter occupy a separate
    state cluster from the destination gate. Request and fifth-word promotion
    signatures do not write the gate, and all three versions use identical
    mode-1/4/5 tables. Successful mode 5 therefore cannot explain or replace
    A0. The exact-image verifier checks this invariant; build 82 remains the
    narrowest original-firmware experiment.
17. **Mode refresh and build .81:** the display-local handler does not
    short-circuit a repeated accepted mode, and its builder emits a fresh motor
    request and secure sequence. Because the accepted A0 gate is independent
    of mode state, build 81 re-establishes display-owned mode 5 after A2 and
    requires a second exact completion before its single A8. A refresh failure
    sends no A8 and requires a physical power cycle because the A0 gate may
    remain armed. Builds 79/80 were never published or bike-tested.
18. **Durable one-attempt guard and build .82:** build 81's ordering is
    unchanged, but its salted same-device command journal now survives page
    reloads and is terminal for both US and non-US reconnect outcomes. The
    phase is persisted before A0 and A8 enqueue. An A0-only interruption blocks
    A8, requires a physical bike power cycle, and cannot be retried by reloading
    the page. No raw Bluetooth identifier, passkey, serial, or capture is
    stored. Build 81 was never published or bike-tested.
19. **PCE transport and wired-report audit:** E-TUBE 3.4.5 constructors feed
    their exact unit command into generic DCAS and `0x48` serial framing; the
    host does not insert A0. Independent `freeMax` code sends ordinary complete
    frames directly to PCE1/BCR2. The published patch injects A8 before the
    worker's later optional A0, so its shown call order does not explain the
    D4.1/D4.3/D4.5 gate. Exact PCE02 3.0.4 ARM analysis proves its `0x48`
    handler copies the unit command unchanged and that neither `16 A0` nor
    `16 A8` is in its only opcode-aware table, excluding a narrow PCE02 A8
    special case. PCE1 is µPD78F1807/78K0R, but its packaged running image
    remains undecoded.

The short, corrected analysis is in
[`docs/evidence/d450-destination-analysis.md`](docs/evidence/d450-destination-analysis.md).
Selected D4.5.0 handler and E-TUBE IL excerpts are beside it, including the
command gates. The decisive separate desktop button call sites are in
[`etube-inspection-buttons.il`](docs/evidence/etube-inspection-buttons.il),
and the Android `A8` constructor is summarized in
[`android-region-call.txt`](docs/evidence/android-region-call.txt). These are
analyst-generated excerpts, not executable
protocol specifications. [`RESEARCH.md`](RESEARCH.md) is a chronological lab
notebook with superseded hypotheses. Its latest correction is authoritative
over earlier build diary entries. Old HTML handoff prose is preserved in
[`docs/legacy-html-handoff.md`](docs/legacy-html-handoff.md), explicitly
superseded.

The D4.3.0 comparison, client audit, and display-owned rationale are in
[`docs/evidence/d430-direct-a8-analysis.md`](docs/evidence/d430-direct-a8-analysis.md).
The desktop/PCE transport and wired-patch contradiction are in
[`docs/evidence/pce-transport-analysis.md`](docs/evidence/pce-transport-analysis.md).

## What could move the goal forward

The offline bridge mapping now identifies a display-owned protected-mode path
that no previous bike run exercised. Build 94 retains build 91's destination setter as the next
lower-risk live experiment: it
changes ownership rather than timing a phone-owned mode, selects mode 5 to
match Shimano's known desktop destination-setting context, and freshly
re-establishes that mode after A2 without consuming the A0 gate.

1. Open build 94 with the bike
   stationary, keep the phone close to the display,
   enter the passkey, and press **Connect and check bike**. Record current
   `B4/B6` plus US-profile `BC/BE`. If the guarded action becomes available,
   press **Set US region once** and confirm it. The page performs the required
   session and motor authentication automatically.
2. Preserve the complete sanitized log. A valid transaction needs display
   `2C 00`, exact motor `00 32 12 05 <slot>`, A0 `A2`, a second complete
   mode-5 handshake, A8 `AA`, immediate US readback, and verified `0C 00` exit.
   `ATT write completed` alone is not success.
3. On success, power cycle and read again in a different session; only then
   measure assistance cutoff on a safe ride.
4. After a successful US destination readback and its physical-power-cycle
   verification, run the read-only check again. If B4 is below BC 01,
   press the guided **Set 32 km/h once** action and confirm it.
   Build 91 rereads the complete exact context, derives `min(BC 01, 3200)`,
   requires B2 plus immediate B4 equality, and records the attempt before
   dispatch. On every outcome, do not repeat B0. Fully power-cycle, then press
   **I power-cycled — verify 32 km/h**; only that
   separate same-device result can establish persistence.
5. On `A3 3A` or `AB 3A` plus EU, do not repeat build 94's action. The next
   no-new-hardware candidate is the hidden exact-stock D4.3.0/M4.2.1 paired
   workflow, not the modified-D4.5.0.1 route. Its transfer/recovery coordinator,
   one explicit display-owned A0→A8 transaction, immediate readback, power-cycle persistence gate,
   and stock restoration are complete and synthetically tested. It still needs
   separate explicit live authorization because an interrupted BLE firmware
   transfer can require wired recovery. Keep the exact restoration pair cached.
6. If the prepared A0→A8 transaction is rejected, retain that verified D4.3.0/M4.2.1
   state. The next bounded software fallback is one circumference write with
   an original-value read and durable journal—not another A8 or A0 retry. Do
   not expose it in the UI until restoration-era wheel reads are proven.

Do not pursue further A0 payload variants or repeat timing attempts. Asset
sources and hashes are in [`ASSETS.md`](ASSETS.md).

Only after a candidate is tied to new evidence should a new live test be
prepared. It must identify the exact same motor/firmware, send at most the
bounded intended setting command, distinguish ATT completion from motor reply,
read destination immediately, exit privileged mode, then check persistence in
a separate session after an actual physical power cycle. A region readback
still does not measure assistance cutoff. The display's Adjust, Shift timing,
and RD protection reset menu items concern electronic shifting; they are not
evidence of a region-setting menu (`RESEARCH.md`, latest section).

## Repository map and reproducibility

- [`index.html`](index.html): public single-file application source. Build 94's
  first guided action is read-only; the same button exposes the display-owned
  destination setter and separately gated stock B0 setter only when each is the
  next verified step. Technical controls are collapsed and the firmware
  workflow remains hidden. No build step.
- [`tests/`](tests): synthetic browser/BLE and firmware protocol regression
  tests. They verify software guards and parsing, not acceptance by the bike.
- [`tools/`](tools): offline firmware inspection/planning utilities.
  `inspect_motor_destination.py` verifies the exact D4.1/D4.3/D4.5 A0/A8 gate
  and PC-mode separation and cold-start-zero invariants without storing vendor
  images. `inspect_display_pc_mode.py` verifies the current display's owned-mode
  lifecycle and repeated same-mode forwarding.
  `compare_display_pc_mode.py` verifies the exact SC-E6100 4.0.5 and SC-E7000
  4.0.6/4.1.0 historical owned-mode comparison.
  `inspect_pce02_transport.py` verifies the exact PCE02 3.0.4 vector,
  initializer, opcode table, and transport function slices.
  `patch_motor_pc_mode.py` constructs only the exact reviewed five-byte
  D4.5.0.1 derivative, defaults to dry-run, and checks source, original bytes,
  and derived hash. It is not an installer.
  `inspect_motor_image_integrity.py` checks the three exact D application
  startup paths, initializer records, size/end literals, and structured tails;
  it does not inspect the resident bootloader.
  `inspect_etube_d_loader.py` checks the exact desktop loader command enum and
  raw-binary/address/data/checksum/finish/reset IL path; it requires `dnfile`
  and `dncil` and cannot inspect the resident loader.
  `inspect_etuning_firmware_policy.py` decodes the exact current Android
  firmware allowlists and matches local candidates without dumping bytes.
  `inspect_etube_max_assist.py` verifies the exact historical Cyclist
  DU-E5000 maximum-speed capability, B0/B4/BC packet construction, unit
  conversion, and Reset/Apply path without committing or printing vendor code.
  Its optional exact-eTuning pass verifies the independent A8-success ->
  350 ms -> B0 chain.
  `inspect_motor_max_assist.py` verifies the exact D4.5.0 cumulative dispatch,
  B0 persistence/range policy, destination ceilings, and B2/B6/BE builders
  without dumping firmware.
  `inspect_etube_boot_patch.py` checks the exact historical desktop E5000
  boot-patch specification and updater path; it does not provide a payload.
- [`docs/evidence/d450-pc-mode-patch-plan.md`](docs/evidence/d450-pc-mode-patch-plan.md):
  exact patch rationale, integrity checks, staged experiment, and unresolved
  boot/recovery boundary.
- [`docs/evidence/d-loader-acceptance-analysis.md`](docs/evidence/d-loader-acceptance-analysis.md):
  complete reviewed client command inventory, write call chain, and the bounded
  modified-image acceptance inference.
- [`docs/evidence/etuning-firmware-policy-analysis.md`](docs/evidence/etuning-firmware-policy-analysis.md):
  current Android allowlist proof for the exact public stock preparation pair.
- [`docs/evidence/d430-wheel-circumference-analysis.md`](docs/evidence/d430-wheel-circumference-analysis.md):
  exact D4.3 wheel protocol, speed tradeoff, and hidden one-write coordinator.
- [`docs/evidence/max-assist-speed-analysis.md`](docs/evidence/max-assist-speed-analysis.md):
  Shimano's exact E5000 `B4/B6`, `BC/BE`, and `B0/B2` protocol, historical
  Reset/Apply flow, exact D4.5.0 B0 policy, and build-91 at-most-once
  transaction gate.
- [`docs/evidence/m448-max-assist-analysis.md`](docs/evidence/m448-max-assist-analysis.md):
  corrected Renesas RX mapping, rejected false opcode hits, and the remaining
  motor-side dispatcher question.
- [`docs/evidence/d5000-boot-patch-analysis.md`](docs/evidence/d5000-boot-patch-analysis.md):
  E5000 boot-patch specification, public artifact search, and limits.
- [`RESEARCH.md`](RESEARCH.md): detailed dated chronology and packet evidence.
- [`ASSETS.md`](ASSETS.md): all source artifacts, download links, hashes,
  exclusions, and the no-local-dependency policy.
- [`docs/evidence/`](docs/evidence/): curated, small analysis outputs and
  source-artifact fingerprints needed to resume reasoning on a fresh clone,
  including the bounded PCE transport audit.
- [`docs/README-history.md`](docs/README-history.md): old build-by-build README.

For a smoke check, run `python3 tests/browser.py`,
`python3 tests/region_write.py`, `python3 tests/log_export.py`, and
`node tests/region_compatibility.cjs`; the hidden wheel fallback also has
`node tests/wheel_fallback_transaction.cjs`. The Python browser tests require the
Playwright Python package and its Chromium browser. Run from the repo root.
For a new live deployment, a tested commit on `main` is published by GitHub
Pages; verify the Pages workflow and the actual HTTPS page before directing a
user to it. No phone, bike, secret, or local analysis folder is needed to
inspect this repo or run the synthetic tests.

## Privacy and handoff boundaries

This is a public repository. Do not commit passkeys, MAC addresses, motor
serials, raw Bluetooth bugreports/snoops, authentication ciphertext, APKs,
installers, or firmware images. Sanitized protocol observations and precise
hashes are committed. The private raw capture supplied for earlier work is
not a required local path for the next agent; if raw evidence becomes necessary,
obtain it privately from the owner rather than publishing it. Nothing in this
handoff assumes access to the former `~/shimano-analysis` work directory.
