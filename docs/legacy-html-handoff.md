# Legacy HTML handoff (superseded)

This comment was moved verbatim from the page. Its early DU-E7000/4.7.1 target and milestones were hypotheses and are superseded by [HANDOFF.md](../HANDOFF.md).

```text
<!--
===============================================================================
SHIMANO WEBBLE REVERSE-ENGINEERING HANDOFF NOTES

Historical import. For current verified findings, see RESEARCH.md.
Build 2026-09-09.8 adds both destination reads and a US-region readiness summary.
The original read-only behavior and pending milestones below are historical.
===============================================================================

PURPOSE / END GOAL
------------------
This file is the beginning of a phone-only Web Bluetooth tool for a Shimano
STEPS system. The practical end goal is to understand enough of Shimano's BLE
configuration protocol to support legitimate configuration workflows without
requiring SM-PCE hardware.

The historical page described below was intentionally read-only. The current
guided workflow uses the authenticated BLE channel to read the exact motor,
firmware pair, and region after the failed build .73 setting stage. It sends
no motor unlock, PC-mode, destination, or firmware command. Preserve a staged
approach:
1) establish BLE access,
2) identify / validate Shimano session authentication,
3) map authenticated configuration transport,
4) only then consider supported configuration operations.

TARGET HARDWARE / SOFTWARE OBSERVED
-----------------------------------
Observed target system:
- Display / wireless endpoint: SC-E7000, advertising with an "SCE7000" name
- Drive unit: DU-E7000
- Drive unit firmware observed: 4.7.1.0
- Android phone: Pixel, Android build family "caiman"

The user configured a six-digit Shimano BLE passkey in E-TUBE. Do NOT commit
that passkey, device MAC address, or other private identifiers to this repo.
Retrieve secrets only from the live test context when needed.

DO NOT ASSUME the six-digit BLE passkey is identical to any regulation/auth
key used by Shimano's proprietary command protocol. Evidence points to multiple
security layers.

USER-SUPPLIED ARTIFACTS / FILES
-------------------------------
Highly relevant artifacts supplied in the originating ChatGPT conversation:
- Android bugreport ZIP containing Bluetooth HCI snoop traffic
- eTuning+ for Shimano Steps v1.0.32 XAPK
- eTuning+ for Shimano Steps v3.0.7 XAPK
- ShimanoBleProbe.zip
- nRF Connect logs / screenshots from a live connection to SC-E7000

If working in the same ChatGPT environment, search conversation/library for:
  bugreport-caiman-CP2A.260805.005-2026-09-08-20-36-59.zip
  eTuning+-+For+Shimano+Steps_1.0.32_apkcombo.com.xapk
  eTuning+-+For+Shimano+Steps_3.0.7_apkcombo.com.xapk
  ShimanoBleProbe.zip

KNOWN BLE SERVICES / CHARACTERISTICS
------------------------------------
Shimano proprietary UUID suffix is ASCII "SHIMANO_BLE\0":
  5348-494d-414e-4f5f424c4500

Primary proprietary service observed:
  000018ff-5348-494d-414e-4f5f424c4500

Characteristics observed on the target:
  2AF3  [INDICATE, SIGNED WRITE, WRITE]
  2AF4  [READ]
  2AF5  [WRITE]
  2AF6  [READ]
  2AF7  [READ, WRITE]
  2AF8  [READ, WRITE]
  2AF9  [NOTIFY]
  2AFA  [WRITE, WRITE WITHOUT RESPONSE]
  2AFB  [NOTIFY]
  2AFC  [WRITE, WRITE WITHOUT RESPONSE]
  2AFD  [NOTIFY]
  2AFE  [WRITE]
  2AFF  [WRITE]

Other Shimano proprietary service observed:
  000018ef-5348-494d-414e-4f5f424c4500
with:
  2AC0, 2AC1, 2AC2, 2AC3, 2AC4

Also observed:
  000018fe-1212-efde-1523-785feabcd123
with:
  2AE2, 2AE3

nRF CONNECT LIVE RESULTS
------------------------
Connection succeeded as CONNECTED + BONDED.
Android BLE encryption was enabled at link layer.

Reading 2AF4 succeeded and returned a fresh 16-byte value.
Reading 2AF6, 2AF7, and 2AF8 in that session returned:
  GATT READ NOT PERMIT (error 0x02)

This strongly indicates Android-level bonding is not sufficient for all
proprietary configuration access.

A prior successful E-TUBE / app capture showed a different 2AF4 challenge and
application-layer traffic on 2AF3. Reconstruct exact packet values from the HCI
snoop artifact rather than relying on prose notes.

WORKING PROTOCOL MODEL (PROVISIONAL)
------------------------------------
Current best model:
  Android BLE bond / encryption
      ->
  Shimano application/session auth over 18FF, involving 2AF4 + 2AF3
      ->
  protected characteristics become accessible
      ->
  configuration command transport using one or more 2AFx characteristics
      ->
  application-level configuration operations

Important correction from early exploration:
"Region" is NOT a dedicated GATT characteristic. It appears to be an
application-level Shimano command transported inside the proprietary 18FF
protocol.

OLD eTUNING APP FINDINGS
------------------------
From prior manual/decompilation work on eTuning 1.0.32:
- There is a RegionActivity.
- A five-byte destination-market command structure was identified in the app.
- Treat any inferred raw packet format as reverse-engineering evidence only
  until its exact call chain, wrapping, authenticated context, and response
  behavior are validated against captured traffic.

From broader inspection:
- App uses local crypto primitives including:
    javax.crypto.Cipher
    javax.crypto.spec.SecretKeySpec
    SHA-256
- This suggests at least part of the BLE/session crypto is implemented locally,
  not fetched from a server.

The later 3.0.7 app should be decompiled and compared with 1.0.32 because the
modern app reportedly integrates "legacy" preparation / downgrade workflows
for older STEPS motors.

PUBLIC REVERSE-ENGINEERING LEADS
--------------------------------
Repos / references already identified:

1) https://github.com/markdotai/emtb
   Useful for Shimano BLE service/telemetry mapping.
   Confirms Shimano proprietary BLE UUID families but does not implement
   region configuration.

2) https://github.com/rolandvs/shimano
   Hardware / E-Tube bus / PCE reverse engineering.
   Useful context for Shimano service architecture.

3) https://github.com/jarod46/GoProBleRemote
   Uses Shimano Di2/D-Fly BLE notifications, especially 18EF/2AC2.
   Helps separate telemetry/button BLE from protected configuration BLE.

4) https://github.com/rpad300/KROMI_BIKECONTROL
   Mainly Giant-oriented; contains BLE/e-bike crypto patterns and some Shimano
   accessory support.

5) https://github.com/abramovychmax-cpu/bell-call
   Helpful for UUID naming / SHIMANO_BLE mapping and D-Fly services.

6) GitHub code search starting point:
   https://github.com/search?q=SHIMANO_BLE&type=code

7) Shimano firmware / E-Tube reverse engineering:
   https://github.com/reven-project/etubeapi
   https://github.com/reven-project/reven-plugin-etube

Public forum / documentation leads previously identified:
- EMTB Forums Shimano STEPS unlock / service reverse-engineering threads
- ElectricBikeReview thread: "Derestricting a Shimano STEPS e-bike"
  Relevant names reported there include:
    ProcessRegulationSetAuth
    UnlockRegulationSetAuth
    EncryptRandVal
- BetterShifting E-TUBE Project archive
- eTuning documentation / FAQ / downgrade PDFs
- ST Unlocker compatibility documentation
- eMax compatibility documentation

Search terms worth continuing:
  "00002af3-5348-494d-414e-4f5f424c4500"
  "00002af4-5348-494d-414e-4f5f424c4500"
  "2AF3 Shimano"
  "2AF4 Shimano"
  "18ff 2af3"
  "18ff 2af4"
  "ProcessRegulationSetAuth"
  "UnlockRegulationSetAuth"
  "EncryptRandVal"
  "AuthKeyGenerator Shimano"
  "Common AES Key Shimano"
  "DUUnitDataLink SetDestination"
  "SetDestination Shimano E-Tube"

FIRMWARE / COMPATIBILITY CONTEXT
--------------------------------
There is conflicting public documentation around DU-E7000 firmware thresholds.

Evidence encountered during research:
- Historical app docs saying E7000 4.4.0 / 4.5.0 supported destination changes,
  while later versions had reduced BLE capabilities.
- Another reverse-engineering source suggested a significant lockout/downgrade
  threshold around 4.7.7 for E7000.
- Target motor is on 4.7.1, which is below 4.7.7 but above 4.5.0.

Do NOT hard-code an assumption that 4.7.1 definitely accepts or definitely
rejects a BLE destination command. Establish this from app code, authenticated
protocol traces, and/or historical firmware behavior.

A plausible historical workflow is:
  temporary downgrade to a compatible firmware
  -> perform configuration
  -> upgrade firmware while persistent settings remain

The modern eTuning app reportedly integrates preparation/downgrade workflows,
which makes v3.0.7 especially valuable to reverse engineer.

WEB BLUETOOTH DEPLOYMENT NOTES
------------------------------
Goal: keep this as a single self-contained HTML file for rapid iteration.

Web Bluetooth:
- Chrome/Chromium on Android is the intended environment.
- Requires HTTPS / secure context and explicit user gesture.
- Android OS handles BLE pairing/bonding underneath browser GATT.
- Web Crypto API is available, so future crypto experiments can remain
  dependency-free in one HTML file.

GitHub repo:
  https://github.com/galah92/shimano-webble

At the time these notes were added:
- Repo existed and was empty.
- Repo metadata showed it was PUBLIC.
- GitHub plugin could read repo metadata but write attempts returned:
    403 Resource not accessible by integration
- Needed permission: Contents: Read and write
- Optional for deployment automation: Actions: Read and write

Likely GitHub Pages URL after Pages is enabled:
  https://galah92.github.io/shimano-webble/

CURRENT HTML BEHAVIOR
---------------------
See README.md and RESEARCH.md. This imported section predates the authenticated
application transport, observed E5000 identity, recovery journal and guarded
firmware/region workflow now implemented below.

NEXT TECHNICAL MILESTONE
------------------------
Run the controlled command-only transaction on the verified E5000 bike. Require
an immediate US readback and a same-device readback after a physical power cycle
before claiming that the destination change persisted.

ENGINEERING PRACTICE
--------------------
- Do not fuzz unknown 2AFx write characteristics on the motor controller.
- Do not interrupt power during any future firmware operation.
- Prefer read-only validation and packet correlation before writes.
- Preserve logs for every experiment.
- Compare against known-good E-TUBE / eTuning captures whenever possible.
- Keep BLE link-layer bonding, Shimano app/session auth, and any separate
  regulation-setting auth conceptually distinct.
- Treat every inferred packet format as provisional until matched against real
  successful traffic.

===============================================================================
END HANDOFF NOTES
===============================================================================
-->
```
