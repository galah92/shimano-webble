# Shimano WebBLE handoff — 2026-09-14

## Objective and current answer

The goal is a reproducible, phone-only HTTPS Web Bluetooth workflow that sets
this bike's OEM destination to US (`1`), confirms the value on the same motor
after a physical power cycle, and separately measures the assistance cutoff.
**No validated US-setting workflow exists yet.** The last verified destination
is EU (`0`); no speed increase has been demonstrated. The investigation is
blocked by missing evidence about the SC-E7000-to-motor command path, not by a
pending user click. Do offline analysis before asking for another bike test.

The public page at <https://galah92.github.io/shimano-webble/> (source
[`index.html`](index.html), build `2026-09-14.75`) offers a guided **Connect and
check bike** action. It authenticates the BLE session and reads identity,
firmware and region. It does not perform motor unlock, PC-mode entry, setting
writes, or firmware operations. The old setter and firmware code still exists
inside the single HTML file for synthetic regression tests, but its UI actions
are disabled/hidden; do not mistake this code for a verified or reachable live
workflow. After any page edit, verify this invariant in code and browser tests.

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
   prefers avoiding a firmware change; do not revive that route from the
   existence of prepared assets alone.
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

## What could move the goal forward

The strongest next work is **offline**: reconstruct the SC-E7000 bridge's
translation and routing of category-`16` `A0`/`A8` requests and the lifetime
of PC mode 4, or obtain a known-good destination-write trace for this firmware
path. In D4.5.0, `A3 3A` can arise from more than one condition; the current
BLE log does not reveal which internal branch rejected A0. The display bridge
image used on this exact endpoint is not in the repo; the recorded catalog URL
returned HTTP 403 on 2026-09-12. A demonstrably equivalent image or an
observed write trace would change the evidence. Asset sources and hashes are
in [`ASSETS.md`](ASSETS.md).

Only after a candidate is tied to new evidence should a new live test be
prepared. It must identify the exact same motor/firmware, send at most the
bounded intended setting command, distinguish ATT completion from motor reply,
read destination immediately, exit privileged mode, then check persistence in
a separate session after an actual physical power cycle. A region readback
still does not measure assistance cutoff. The display's Adjust, Shift timing,
and RD protection reset menu items concern electronic shifting; they are not
evidence of a region-setting menu (`RESEARCH.md`, latest section).

## Repository map and reproducibility

- [`index.html`](index.html): public single-file application. Active guided
  action is read-only; old write/firmware code is dormant. No build step.
- [`tests/`](tests): synthetic browser/BLE and firmware protocol regression
  tests. They verify software guards and parsing, not acceptance by the bike.
- [`tools/`](tools): offline firmware inspection/planning utilities.
- [`RESEARCH.md`](RESEARCH.md): detailed dated chronology and packet evidence.
- [`ASSETS.md`](ASSETS.md): all source artifacts, download links, hashes,
  exclusions, and the no-local-dependency policy.
- [`docs/evidence/`](docs/evidence/): curated, small analysis outputs and
  source-artifact fingerprints needed to resume reasoning on a fresh clone.
- [`docs/README-history.md`](docs/README-history.md): old build-by-build README.

For a smoke check, run `python3 tests/browser.py`,
`python3 tests/region_write.py`, `python3 tests/log_export.py`, and
`node tests/region_compatibility.cjs`. The Python browser tests require the
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
