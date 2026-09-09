# Shimano WebBLE

A single-file Web Bluetooth diagnostic and experimental session-authentication
console for Shimano STEPS. The experimental US-destination setter is currently disabled.
No firmware changes are implemented.

**Live site:** https://galah92.github.io/shimano-webble/

## Use

Open the site in Chrome on Android, enable Bluetooth, make the Shimano endpoint
discoverable, and tap **Connect Shimano**. The page subscribes to 2AF3 indications
and probes 2AF4, 2AF6, and 2AF7 without application writes.

To test session access, enter the six-digit passkey configured in E-TUBE and tap
**Authenticate session**. This sends the two reconstructed authentication
messages, waits for their acknowledgements, then waits 500 ms and checks whether
2AF7 identifies the SC-E7000. If the read fails, it sends the captured `FF 00`
setup command to 2AFF once, waits another 500 ms, and checks again. The passkey is used locally, cleared after the attempt, and never
saved or logged. **Copy log** exports the diagnostic results for analysis.

Build .4 verified both authentication stages and SC-E7000 identification on the
real bike after the captured setup command. If authentication fails, reconnect
before retrying.

Tap **Read region and compatibility** after session verification.
It runs the verified connection setup plus an experimental seven-step setup
sequence found in both supplied eTuning versions. It then reads motor information
and destination slots against the US target (value 1). Replies are required at
every setup step; AF/3A stops destination checks with the region unknown.
Keep Chrome foregrounded until **information batch end**, then copy the log.
Allow up to 80 seconds if queries go unanswered.

Build .7 confirmed motor communication and reported E50X0 / 4.5.0. The newer
APK's direct-region gate routes that combination through preparation; 4.3.0
is the concrete preparation lead under investigation. Builds .15 and .16 both
received AB/3A rejection after motor authentication. The .15 reconnect confirmed EU;
the .16 pre-write read also reported EU. Build .17 disables direct writes,
including after successful authentication. No firmware transfer is implemented.
The US-region goal remains incomplete.

Build .16 returned seven zero model-descriptor bytes. Together with series 22
and unit 00, this matches the base DU-E5000 entry in the older desktop model
table. It does not certify a particular firmware image's compatibility.

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

## Motor authentication experiment

After a successful information batch reporting E50X0 / 4.5.0 and a valid
destination, tap **Authenticate motor** once. It privately reads the serial,
requests the motor challenge, validates all three fragments, computes the AES
response and waits for the APK completion marker `00 16 E2 FF FF`.
Copy the log after **motor authentication end**. This is an experiment; the
marker does not establish permission to change region. DB replies stop the run; the APK's E8
fallback is not implemented. An older Shimano library identifies E8 as an
authentication-lock release request; its applicability to this bike still
needs verification.

The user's build .14 log verified motor authentication on the real bike, with
the three DA challenge fragments and E2 FF FF completion after the third E0.

## US destination experiment (build .15)

**Live result:** this exact experiment was rejected with `AB 3A` after
successful motor authentication. A separate connection read EU (0) again.
Do not repeat the same write sequence; the next investigation is the app's
preparation workflow. Firmware 4.3.0 is a candidate from its source, not a
verified downgrade prescription.

As of build .17, **Set region to US** remains disabled after authentication.
No production path currently grants direct-write eligibility. The retained
experimental implementation is tested using synthetic eligible sessions:
It first reads the current destination again; only EU (0) permits the write.
It sends `00 16 A8 01 01` once, watches for AA or AB, and reads back the
current destination after AA or an acknowledgement timeout with completed ATT.
US (1) readback is the value check. An acknowledgement alone is never success.
Rejections, write failures and unverified readback stop the attempt. There is
no automatic retry, downgrade, factory-slot write or separate speed setter.

For a future validated write workflow, if US is read back, disconnect,
turn the bike fully off and on, reconnect, authenticate the session, and run
**Read region and compatibility** again. Copy that second log and report that
the bike was power-cycled. The app cannot detect a physical power cycle; a US
value in one session does not prove persistence or an assistance-speed outcome.

The shared goal is a verified phone-only US-destination workflow with readback
and persistence checks. Current baseline: session setup, EU readback and motor
authentication work. Region-write compatibility, persistence and actual speed
behavior remain unverified. Firmware preparation is a separate open task.

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
Use `--force-equal` to model the installer's equal-version rewrite flag;
without it, equal versions are omitted. The observed `f9c41` installer caller
passes this flag as true. Neither mode models failed-read/recovery selection
or proves that a component will be retained in the actual preparation workflow.
The build .18 live batch independently read D **4.5.0.0** and M **4.4.8.0**;
destination remained EU (0). The sanitized baseline is in
`tests/bike_baseline.json`. Use `--installed-d 4.5.0.0 --installed-m 4.4.8.0`
to compare candidate files with this observation. The archived D 4.3.0 / M 4.2.1
pair selects two downgrades, M then D. This does not establish that both are
required, that the pair matches eTuning's preparation package, or that it is
installable. Exact-version restoration assets were subsequently recovered from
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
