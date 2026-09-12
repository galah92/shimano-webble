# Shimano WebBLE

A single-file Web Bluetooth diagnostic page for Shimano STEPS. The current
guided button verifies the tested E5000 motor, D4.5.0/M4.4.8 firmware, and
current destination. It does not enter motor PC mode or attempt a region write.
The earlier command-only US experiment remains in the source for offline
analysis and synthetic regression tests.

**Live site:** https://galah92.github.io/shimano-webble/

## Current result (build .73)

The bike reported the wireless application slot `0D`, D4.5.0/M4.4.8 firmware,
and EU destination. Motor authentication and regulation unlock completed, and
the motor acknowledged normal PC mode 1 and authenticated mode 4. Build .73
then read lighting time 10 and sent Shimano's seven-byte unchanged-lighting
stage, `00 16 A0 0A 00 FF FF`. The motor rejected that stage with `A3 3A`.
The page exited PC mode and disconnected; it never sent the US destination
command `A8`. The user observed a screen reset during the process, but the
compact log does not establish exactly when it happened or whether bike power
was interrupted.

The D4.5.0 A0 handler can reject a command if its PC-mode state is no longer
active or its internal target field is unexpected. The mode-4 acknowledgement
does not prove the mode remained active at the instant A0 ran. We are tracing
that gap before another setting experiment. The US region and assistance speed
are not verified.

## Use build .74

Open the site in Chrome on Android, enable Bluetooth, make the Shimano endpoint
discoverable, enter the six-digit passkey, and tap **Connect and check bike**.
The button authenticates the BLE session and reads motor identity, firmware,
and destination. It does not perform motor unlock, PC-mode entry, a setting
write, or a firmware command. Copy the compact log after it reports the result.

The controls under **Advanced diagnostics** expose earlier read and
session-authentication steps. The destination setter is disabled in the UI.
The previous setting workflow remains only for offline analysis and synthetic
regression tests. The retired firmware preparation implementation is hidden
and inert.

The US-region goal remains incomplete until a future command path yields US
readback on the same motor and that value persists after a physical power
cycle. Assistance cutoff requires a separate physical measurement.

## Develop

Edit `index.html`; there is no build step or runtime dependency installation.

```sh
git clone https://github.com/galah92/shimano-webble.git
cd shimano-webble
python3 -m http.server 8000 --bind 127.0.0.1
```

Open http://localhost:8000 for local UI development. Use the HTTPS site for
phone testing; a plain HTTP LAN address does not provide the required secure
context for Web Bluetooth.

GitHub Pages publishes the repository root from `main`. Push changes to `main`
to deploy; check the repository's Actions tab for the Pages build result.
`.nojekyll` keeps the site as plain static files.

For simulated browser tests, use Python with Playwright and its Chromium browser
installed, then run `python tests/browser.py`. No Bluetooth hardware is needed.

## Source and handoff

See [RESEARCH.md](RESEARCH.md) for verified evidence, protocol details,
firmware limitations, and remaining live checks.

The original HTML and historical handoff notes came from
`shimano_webble_with_handoff.html`. Their original read-only description predates
the explicit authentication experiment in build `2026-09-09.3`.

Keep passkeys, device identifiers, bugreports, and raw captures outside this
public repository. Earlier diagnostic builds logged the passkey via 2AF8;
keep those old exported logs private.

## Copy logs

**Copy log** copies the latest connection and its results, with a character
count and `END SHIMANO LOG` marker. No export mode selection is needed. If
clipboard access fails, select and copy the log text directly.

Build .10 also reports notification headers, counts and timing separately for
each query on all three channels. Startup traffic cannot hide later response
types. No new bike commands were added. Export tests: `python tests/log_export.py`.

Build .11 recognizes the observed destination response `00 16 AF 3A` and stops
further destination reads promptly. An older Shimano library names error 3A
`CMD_NOT_DISPOSE`; the precise rejected state remains unresolved. It is never
decoded as a region or treated as permission to change configuration.

**Clear log** clears the visible and saved log history. It leaves the Bluetooth
connection and bike state unchanged; subsequent messages continue logging normally.

## Protected motor authorization

The guided workflow privately reads the motor serial, requests the challenge,
validates all three fragments, computes the AES response, and requires the
`00 16 E2 FF FF` completion marker. It then sends Shimano's separate `E8`
regulation-unlock request using the same serial-derived request and requires a
normal `EA` reply. Only then can the destination transaction continue. Serial,
challenge, keys, ciphertext, secure PC words, and passkey are omitted from logs.

The user's build .14 log verified motor authentication on the real bike, with
the three DA challenge fragments and E2 FF FF completion after the third E0.

## Command-only US destination candidate (build .73)

The D4.5.0 `A8` handler at `0x2537c` accepts the write only while PC mode is 4
or 5 and a one-shot flag set by the `A0` handler is active. There is no version
check in that handler. Its persistence helper compares and writes an internal
11-byte record. Those internal buffer widths are not BLE parameter lengths.
The official capture contains 241 writes to the motor characteristic and none
exceeds seven bytes, while both Shimano applications construct the lighting
setter as `00 16 A0 <low> <high> FF FF`. Fixed-size replies include bridge data
beyond a setting's declared fields, so those bytes are not copied into a setter.

Build .73 first reads the current OEM destination again; only selector 1 and EU
value 0 permit progress. It establishes ordinary PC-link mode 1, then enters
the firmware's separately keyed authenticated mode 4 and requires a matching
completion reply after each five-word sequence. Unlike the desktop adapter,
the wireless path uses application slot `0D`; the page learns it from the bike's
setup announcement or falls back to the exact value in the supplied official
capture. It reads the declared 16-bit lighting value and sends exactly one
same-value `00 16 A0 <low> <high> FF FF` stage. It saves a durable reconnect
expectation only after that form returns `A2`, then sends the Android eTuning destination
frame `00 16 A8 01 01` once. It accepts only `AA` as the setter's normal reply
and immediately reads destination slot 1. It always requests PC-mode exit. An
acknowledgement alone is never success, and a later connection performs readback
only. There is no automatic retry, downgrade, factory-slot write, or separate
speed setter.

If US is read back, disconnect, turn the bike fully off and on, reconnect,
authenticate the session, and run **Read region and compatibility** again. Copy
that second log and report that the bike was power-cycled. The app cannot detect
a physical power cycle; a US value in one session does not prove persistence or
an assistance-speed outcome.

The shared goal is a verified phone-only US-destination workflow with readback
and persistence checks. Session setup, exact D4.5.0/M4.4.8 identity, EU
readback, motor authentication, `E8` regulation unlock, wireless slot `0D`, and
authenticated mode 4 work on the bike. The corrected same-value lighting stage,
destination commit, persistence, and actual speed behavior remain to be
verified live.

Synthetic write/readback tests: `python tests/region_write.py`.

## Firmware preparation research

Build .16 adds a read-only **Motor model descriptor** query to the existing
information batch. Connect, authenticate the session, then choose **Read region
and compatibility** and copy the log. Motor authentication and the US setter
are not needed for this check. A missing descriptor is not interpreted as a
particular model. The casing label is helpful but not a prerequisite for
continuing electronic identification.

The source distinguishes D and M motor firmware components. The offline tool
`python3 tools/inspect_firmware.py path/to/file.dat` classifies the known raw
E5000 header layouts and prints version, size and SHA-256. It does not write
to the bike or approve an image for installation. Wrapped/encrypted assets
are unsupported. Tests: `python3 tests/firmware_header.py`.

Archived E5000 4.1.0 files were used only as parser reference samples. They
are not preparation candidates. An archived E-TUBE 4.0.2 installer supplied
E5000 D 4.3.0 and M 4.2.1 files with matching binary headers. Their hashes and
offline analysis are recorded in RESEARCH.md; vendor binaries stay outside
this repository. This establishes a bundled pair, not that eTuning uses that
pair for preparation. Compatibility, transfer completion and recovery remain open.

Offline D-transfer analysis: `python3 tools/plan_d_transfer.py path/to/D.dat`
reports block counts, padding, checksums and bank boundaries. It cannot connect
to or update a bike. `python3 tests/d_transfer.py` checks synthetic vectors from
the supplied app's Java routines and boundary cases. M transfer and the correct
D/M preparation pair remain under investigation; equal version numbers must
not be assumed. No new motor test is needed for these offline changes.

Offline M-transfer analysis: `python3 tools/plan_m_transfer.py path/to/M.dat`
reports the separate M payload sizes and checksum windows. Tests:
`python3 tests/m_transfer.py`. The tool does not schedule retries or implement
recovery; its window calculations are for further protocol validation.

Offline component selection: `python3 tools/compare_components.py D.dat M.dat`
accepts optional `--installed-d` and `--installed-m` four-field versions. It
compares each component separately and leaves the order unresolved if either
installed version is unknown. Tests: `python3 tests/component_selection.py`.
It also checks the images' minimum peer versions. A failed or unreadable peer
requirement suppresses the transfer order, including under `--force-equal`.
The old D 4.3.0 / current M 4.4.8 combination fails M's minimum D 4.4.6
requirement. Passing this file-level check does not prove device compatibility.
Use `--force-equal` to model the installer's equal-version rewrite flag;
without it, equal versions are omitted. The observed `f9c41` installer caller
passes this flag as true. Neither mode models failed-read/recovery selection
or proves that a component will be retained in the actual preparation workflow.
The build .18 live batch independently read D **4.5.0.0** and M **4.4.8.0**;
destination remained EU (0). The sanitized baseline is in
`tests/bike_baseline.json`. Use `--installed-d 4.5.0.0 --installed-m 4.4.8.0`
to compare candidate files with this observation. The archived D 4.3.0 / M 4.2.1
pair selects two downgrades, M then D. This does not establish that both are
required or that it is installable. The pair now matches eTuning's freely
downloadable historical E5000 preparation ZIP byte for byte; this does not
establish the current app server's response. No paid account is required to
obtain these published files. Exact-version restoration assets were recovered from
the archived desktop 5.3.4 package: raw M 4.4.8.0 and wrapped D 4.5.0.0.
Offline D unwrapping passed its embedded digest/length checks and header
inspection. Transfer and recovery compatibility remain unverified; see
`RESEARCH.md` for provenance and hashes. Vendor images remain outside this repo.

Build .18 adds native D and M version reads to **Read region and compatibility**.
They run automatically at the end of that batch; no extra button is needed.
Copy the log after the batch ends. An incomplete native D read stops the pair
before M, requiring a reconnect. Firmware preparation remains unavailable.

`tools/m_reply.py` models candidate notification envelopes and classifies
M-transfer replies offline; `python3 tests/m_reply.py` checks Java reference
vectors, sequence matching and checksum distinctions. It does not reassemble
notifications or authorize progress to another firmware block.

Build .19 adds **Check preparation files**, a local-only check for a pair of
extracted DAT files. It recognizes reviewed preparation/restoration contents,
uses internal versions rather than file names, and rejects mixed pairs. It
requires raw files (the restoration D wrapper is not supported). Passing this
check does not enable installation; firmware transfer and recovery remain in
development. No additional bike test is needed for this build.

Build .20 adds the D/M packet encoders and reports transfer block counts when
local files pass validation. Their full output matches the offline codecs for
both preparation and restoration images. Transfer remains unavailable until
reply handling, bootloader handover and recovery are validated.

Build .21 adds M reply classification and per-attempt evidence handling for the
future updater, tested against Java envelope fixtures and notification-order
cases. It does not send firmware. Checkpoint freshness, the timed transport,
D reply handling and paired handover/recovery still require implementation.

Build .22 implements the timed M query exchange with immediate-reply handling,
separate write/reply deadlines, abort and listener cleanup. Fake-clock tests
cover failure and race cases. It remains disconnected from the bike controls;
firmware data transfer and automatic retries are not enabled.

Build .23 adds an unwired M data-block worker: an initial attempt and up to two
protocol-directed retries, with fresh sequences and source-derived delays.
Uncertain ATT outcomes stop without automatic rewriting. The worker is tested
offline; whole-image transfer, D handling and paired recovery remain incomplete.

Build .24 adds D reply handling, checked against 72 cases executed through the
original Java listener. D requires both a data acknowledgement and a block
result, with longer deadlines for its first three blocks. This remains offline
updater infrastructure; no firmware controls or new bike test are enabled.

Build .25 adds the timed D query and a source-derived address/bank command plan.
M and D share listener/timeout cleanup while retaining different reply rules.
Offline timing, correlation and bank-boundary tests pass. Actual bootloader
command transport, D data transfer and paired recovery remain unfinished.

Protocol-88 research now establishes the 2AFA command mapping and a command
reply filter checked against raw APK instructions. The readable decompiler
inverted one condition; offline fixtures now cover the corrected behavior.
This is preparation for the command worker, not live firmware validation.

Build .26 adds the protocol-88 setup command exchange with corrected reply
matching, parameter bounds and command-specific deadlines. It passes the
108 matcher fixtures and timing/failure tests. It remains disconnected from
bike controls; paired transfer and recovery are not yet ready for a motor test.

Build .27 joins the D setup commands, bank changes and data/query exchanges
into an unwired full-image data-phase worker. Synthetic images cover both
reviewed D image lengths, the maximum modeled range, padding and sequence
wraparound. Failures stop without resending or advancing; input bytes are
snapshotted before the first write. Run `node tests/d_firmware_image.cjs`.
The worker returns a checksum for later finish handling; it does not finish,
reset, enter a bootloader or validate hardware compatibility. Paired image
installation and recovery remain incomplete. No new bike test is needed.

Build .28 adds the unwired M image data-phase worker. It snapshots an image
once, advances only after each block/checkpoint passes, and retains the bounded
protocol-directed block retries. `node tests/m_firmware_image.cjs` exercises
synthetic images at both reviewed M lengths and the maximum modeled range,
sequence wrap, zero padding, checkpoint loss/rejection and uncertain writes.
M setup, finish, paired handover and recovery remain separate unfinished work;
no firmware operation is available from the bike controls.

Build .29 implements the unwired M start/address/clear-checksum/finish command
exchange, with explicit routing, argument bounds and source-specific deadlines.
Tests cover relay/direct routes, early replies, rejection, timeout and abort.
Run `node tests/m_firmware_command.cjs`. It does not enter update mode, reset
the motor, or connect these commands to the data worker or user controls.

Build .30 joins the M bootloader-version query, start, configuration mode,
address/checksum setup, data phase and finish. It suppresses reset for later
paired handover. Integration tests exercise the version threshold, both routes
and ATT failure at every stage: `node tests/m_firmware_session.cjs`.
Bootloader entry and target selection remain preconditions, not implemented
by this operation. Paired identity validation and recovery are still needed;
the operation has no bike-control caller.

Build .31 joins D data transfer and finish with the source's one-second
post-finish delay. Reset remains a separate bounded write whose result does
not claim reboot or firmware verification. `node tests/d_firmware_session.cjs`
checks ordering, checksum, failure stops and reset semantics; command tests
cover the 3-second finish deadline. No firmware controls are enabled.

Build .32 adds unwired D bootloader identity queries and image-field checks.
Replies must start with the expected opcode after recognized framing, rather
than contain it anywhere. Tests cover the five-query order, six-byte serial
assembly, truncated replies and incompatible family/unit fields. Run
`node tests/d_bootloader_identity.cjs`. Bootloader entry, serial-dependent
setup and paired recovery are still required before a firmware test.

Build .33 joins D identity reads, image checks, serial-dependent setup, data
transfer and finish. Mismatches stop before setup; any failed exchange stops
the sequence. `node tests/d_component_workflow.cjs` covers the combined
operation and failure at every write. The operation does not enter the
bootloader, reset or recover a failed paired update, and has no UI caller.

Build .34 corrects the outgoing firmware transport: existing encoders produce
logical messages, which need short-command framing or fragmentation before
BLE writes. The new unwired adapter matches ten original-Java synthetic
vectors and stops after any uncertain fragment delivery. Run
`node tests/firmware_gatt.cjs`. Earlier component simulations cover logical
exchanges; they do not establish a working live firmware transfer. The updater
still requires bootloader entry, paired handover and recovery validation.

Build .35 models ordinary update-mode entry and M slot selection. Integration
checks now pass through the physical GATT framing adapter, including routes,
mode checks, acknowledgement values, delays and failure at each exchange:
`node tests/firmware_entry.cjs`. These helpers have no UI caller. Entry on the
real bike, paired handover and recovery still need validation before flashing.

Build .36 models the missing D bootloader-entry FIRMUP sequence. Its17 physical
writes and source delays are tested across routes, reply errors, cancellation
and failure at every step: `node tests/d_bootloader_entry.cjs`. It takes private
stage credentials as input and contains none in the repository. This is still
unwired: paired orchestration, actual entry/identity checks and recovery must
be validated before a bike firmware test.

Build .37 joins validation, M transfer, fresh handover, D entry and D transfer
in an unwired paired coordinator. It owns the transport, validates both actual
file snapshots before writes, and reports partial completion without resetting
or retrying. `node tests/firmware_pair.cjs` checks orchestration with controlled
workers; the component suites cover their protocols separately. Full integrated
wire simulation, fresh live baseline acquisition and recovery remain required
before exposing an updater or requesting a firmware test.

Build .38 adds a full paired BLE-device simulation using all real app workers:
`node tests/firmware_pair_wire.cjs`. It covers both reviewed image sizes,
fragmentation, checkpoints, bank boundaries and failure before/after every
write in the small pair. Failures now explicitly mark device state unknown:
an unconfirmed finish does not prove the component stayed unchanged. Live
entry, recovery and post-restart verification remain unfinished.

Build .39 adds unwired read-only verification after reconnect: motor identity,
both native versions and region. `node tests/firmware_readback.cjs` checks
mismatches and every read failure through the GATT adapter. The caller must
supply actual connection lifecycle tokens and the same private identity salt.
Matching readback does not establish power-cycle persistence; that remains
an explicit live verification requirement.

## Historical guided bike test (build .41; replaced by .57)

This earlier procedure is on hold. The main button now performs the region
check described above; it no longer runs this probe.

No profile download, file selection, or paid account was required.

1. Connect and enter the six-digit Shimano passkey.
2. Tap **Run bike test**. Session authentication, compatibility reads, motor authentication and the entry/read/reset probe run automatically. Keep Chrome foregrounded.
3. When prompted, turn the bike off and on, connect again and enter the passkey.
4. Tap **Verify after restart**, then **Copy log**.

The verification click only reads the original motor identity, native D4.5.0.0 /
M4.4.8.0 and EU destination; it never starts a second probe. Manual controls and
the optional firmware-file checker are under **Advanced diagnostics**.

The entry profile is now embedded at the user's request. It contains fixed
source-derived entry parameters, not the user's passkey or motor serial. The
passkey is still used locally, cleared after authentication, and not saved or
logged. The same tab retains a salted motor fingerprint and configuration for
reconnect comparison.

Entry and reset remain unverified on the bike. This probe cannot send erase,
firmware-data or region-write commands. Reset delivery does not prove reboot,
interrupted-update recovery, or US-region persistence.

Tests: `node tests/bootloader_probe.cjs` checks the physical sequence and failure
handling. `python tests/bootloader_probe_ui.py` checks automatic sequencing,
failed prerequisites and verification without a second probe.
