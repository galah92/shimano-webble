# Exact stock BLE timing probe audit

## Does the proposed read-only experiment advance the goal?

### Takeaway
The early AC experiment can test whether a phone read is admitted before the display-owned mode handshake completes. It cannot establish that the motor still has protected mode 5 when the read executes, or that A0 would pass. The next diagnostic is more informative after matching build 94's motor authentication and recording every surfaced mode header throughout its window.

### Cited Findings
- Build 94 completed motor authentication including the bounded DB46 recovery, established display-owned mode 5, then received A3 3A for the unchanged-lighting A0; no A8/B0 followed, and later EU/25 km/h persisted — [latest physical correction](../../RESEARCH.md#2026-09-27-twenty-seventh-correction-build-94-physical-a0-rejection).
- Build 95's probe path required motor eligibility but never invoked motor authentication; the guided mutation path did invoke it. Build 96 now calls the existing bounded authenticateMotor once if needed and verifies the same session and successful motorAuthenticated flag before mode 5 or AC — [implementation](../../index.html), functions probeEarlyDisplayQueue, authenticateMotor, runGuidedMutation.
- The exact display path queues the request and five secure words before its local 2C00 acknowledgement; AC and A0 use the same ordinary bus queue, and none is in the initialized priority table — [queue evidence](../../docs/evidence/bridge-analysis.md#2026-09-27-correction-enqueue-before-motor-completion), [exact-hash verifier](../../tools/inspect_display_pc_mode.py).
- AC/AE reads the destination; its handler does not test protected motor mode. The probe compares AC send-call and ATT acknowledgement times with the first exact mode5/slot completion, and AE arrival afterward — [destination handlers](../../docs/evidence/d450-destination-handlers.c), [probe implementation](../../index.html).
- Build 96 adds passive observation of known category32 request/completion mode+slot fields and rejection reasons on 2AF9/B/D from before mode entry through mode exit. It excludes secure-word and authentication opcodes, records localACK-to-send delay, and gives an explicit timing/transition/failure verdict. All A0/A8/B0 and firmware command paths and durable journals remain unchanged — [implementation](../../index.html), [focused synthetic tests](../../tests/region_write.py).

### Inferences
- A successful timing result supports preparing the early-queue hypothesis for review; it is insufficient by itself to justify a new setting attempt.
- Matching successful authentication removes a real comparison confound even though the committed PC request/secure handlers show no explicit authentication test — [PC handlers](../../docs/evidence/d450-pca-mode-handlers.c).
- Phone timestamps order received BLE events, not actual motor processing. Different characteristics can deliver notifications at different times; ATT completion is not bus processing acknowledgement — [implementation and bounded milestone wording](../../index.html).

### Gaps
- No runtime bus capture or read-only getter has been identified that directly exposes motor active mode4/5, source relation, or the A0-created gate — [handoff decisions](../../HANDOFF.md), [destination analysis](../../docs/evidence/d450-destination-analysis.md).
- The user's memory of a build94 screen restart is unknown; it must not be converted into positive or negative reset evidence — [physical correction records this missing observation](../../RESEARCH.md#2026-09-27-twenty-seventh-correction-build-94-physical-a0-rejection).
- If no mode transition reaches BLE, the observer cannot conclude that the motor retained mode5. Bus requests/replies routed elsewhere may never appear on these characteristics — [bridge routing analysis](../../docs/evidence/bridge-analysis.md).

## Is mode loss established, and could target/source explain the rejection?

### Takeaway
Mode loss remains the leading interpretation, not a captured transition. The exact A0 handler checks active mode4/5 and zero normalized target; its source argument is used for reply routing, not a separate local authorization test. Common forwarding and successful AC support the zero-target map but do not substitute for observing A0's actual normalized buffer.

### Cited Findings
- Exact A0 at0x252a8 has only the active4/5 and target+4==0 checks before copying five bytes and arming the gate; its source argument goes to reply construction — [A0 decompilation](../../docs/evidence/d450-a0-a8-neighborhood.c).
- Static full-copy mapping places phone b0 at motor normalized+4, category/opcode at+2/+3, and injects the display's bus-node ID separately at+1 — [bridge byte map](../../docs/evidence/bridge-analysis.md#1-drive-unit-commands-are-forwarded-verbatim-offset4-is-the-leading-byte).
- Builds76/77 inferred reclaim from A3 3A and did not directly observe a mode1 overwrite. The exact display maintenance exit paths call mode0; normal setup uses mode1 — [historical observations and later ownership correction](../../RESEARCH.md), sections Build76 live result, Build77 live result, and2026-09-24 display-owned correction.
- Display completion state and motor active mode are separate RAM state; the successful display handler stores its requested mode before reporting completion, and motor promotion writes its own active byte before its completion — [display verifier](../../tools/inspect_display_pc_mode.py), [motor PC handlers](../../docs/evidence/d450-pca-mode-handlers.c).
- Read-only category32 B4 returns a separate stored dword and display0D is a status query; neither is demonstrated to expose active protected motor mode. Motor modes2/3 request cases merely emit hardcoded completions2/3 without reading the active mode — [negative historical command audit](../../RESEARCH.md), [motor mode request handler](../../docs/evidence/d450-destination-handlers.c).
- BC's nonzero-PC-mode gate can distinguish zero from nonzero, but cannot distinguish mode1 from5 — [maximum-assist policy](../../docs/evidence/max-assist-speed-analysis.md#exact-d450-acceptance-path), [verifier](../../tools/inspect_motor_max_assist.py).

### Inferences
- Adding BC solely as a mode-state diagnostic would introduce extra traffic without resolving the important mode1-vs5 ambiguity; no BC probe was added.
- A WU111 topology could change ownership and bus source versus an SC-E7000 BLE endpoint, but a firmware-unidentified community success cannot establish D4.5.0/M4.4.8 acceptance. Source authorization is not proven by the A0 handler; any additional restriction would need an upstream/runtime explanation — [local handler and routing evidence](../../docs/evidence/d450-a0-a8-neighborhood.c), [bridge source mapping](../../docs/evidence/bridge-analysis.md).
- AC is shorter than A0 and can differ in segmentation; static shared-queue proof reduces but does not eliminate runtime packet/target ambiguity — [packet shapes](../../docs/evidence/d450-destination-analysis.md), [queue analysis](../../docs/evidence/bridge-analysis.md).

### Gaps
- No known-good exact stock E50X0/D4.5.0 SC-E7000 destination trace was available in the repository; no motor-mode getter was invented or sent — [handoff](../../HANDOFF.md).
- No local private firmware artifacts remained under the previous temporary paths in this environment; this audit uses committed exact-hash verifier logic and selected decompilation excerpts, rather than claiming a new full binary decompilation — [asset retrieval inventory](../../ASSETS.md).

## What result changes the next decision?

### Takeaway
One diagnostic should produce a clear bounded result. A late send, wrong event order, rejected/failed handshake, authentication failure, or observed different mode should stop this candidate rather than lead to repetitive setting attempts.

### Cited Findings
- Probe execution remains once per connection and requires freshly checked exact stock firmware, EU destination, and a verified prior non-US attempt record; it preserves the durable setting journal — [probe gates](../../index.html), [synthetic tests](../../tests/region_write.py).
- Failed authentication sends neither mode5 nor AC. Early motor completion prevents AC dispatch. Duplicate completion retains the first timing boundary. Wrong-order timing is explicitly inconclusive — [implementation](../../index.html), [tests](../../tests/region_write.py).
- Compact report selection retains Queue probe lines, ignored mode headers, latest consequential session, and end markers, while leaving the full displayed/session-stored log available for manual copy — [exportLog](../../index.html), [log export tests](../../tests/log_export.py).
- The normal flow still uses one contextual button. No additional full-log-copy control was added because the existing full log can already be selected within Technical details, and copying arbitrary historical logs automatically would need a separate privacy review — [UI](../../index.html).
- The page has no setInterval or periodic mode1 sender. Its sole ordinary local0C01 is an item in the awaited sequential information batch; batchDone and the busy guard prevent the probe from overlapping that batch. Other timers are exchange deadlines or finite delays, and mode0 is explicitly requested only for exit — [INFO_QUERIES, identifyDrive, probeEarlyDisplayQueue and timer call sites](../../index.html).
- Verification completed in this audit: 27 region/probe tests pass, including a delayed real authenticateMotor serial/D8/E0/E8 integration before mode5 and the failed-auth no-command branch; all 11 existing motor-authentication tests pass, including bounded DB46 recovery and failure/privacy cases; 7 compact-report tests pass; the firmware picker browser check passes — [region/probe tests](../../tests/region_write.py), [log tests](../../tests/log_export.py), [firmware UI check](../../tests/firmware_ui.py), [motor tests](../../tests/motor.py).

### Inferences
- Authentication failure: resolve the bounded auth result; it provides no queue/mode evidence.
- Motor completion before localACK callback/send: the localACK hook has insufficient lead time on this phone/session; another post-completion A0 is not justified.
- AC ATT acknowledged before exact completion and AE afterward, no surfaced transition: early phone read admission is supported, protected-mode persistence and A0 acceptance remain open.
- Different mode observed after mode5 and before requested exit: capture the mode/slot/time header, then compare that transition with the display lifecycle and motor writer paths before considering any setting.
- No surfaced transition: no claim of mode retained. A new setting candidate would still need a separately reviewed one-shot sequence and distinct journal decision; clearing build94's journal is not an acceptable shortcut.

### Gaps
- Synthetic tests establish code ordering/guards/redaction only; no build95/96 physical result or higher-speed result exists — [handoff](../../HANDOFF.md).
