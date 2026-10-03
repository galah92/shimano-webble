# Asset inventory and retrieval

All files needed to understand the current conclusion and run synthetic tests
are in this repository. The old external analysis folder is **not** a build,
test, or handoff dependency. Large/proprietary binaries and private captures
are intentionally excluded from public Git; no file currently requires Git
LFS. The links below are historical acquisition sources, not a recommendation
to install firmware. Check availability and hash any fresh download before
using it. The hashes describe bytes examined during this investigation.

| Asset | Source / access | Size | SHA-256 | Purpose |
| --- | --- | ---: | --- | --- |
| E-TUBE Professional 5.3.4 ZIP | [archive download](https://assets.bettershifting.com/archive/E-tube_Proj_V_5_3_4.zip), [archive index](https://bettershifting.com/e-tube-project-archive/) | 309,035,074 | `004883e032a6f343e5c11d9b8b45b7f7c77e47ca5dd7259f488f913f6aaede4f` | Desktop IL and original-version D/M image source; mirror authenticity is not a vendor signature |
| E-TUBE Professional 4.0.2 ZIP | [archive index](https://bettershifting.com/e-tube-project-archive/) | 180,864,996 | `903a343e2fde116b36846045267c9953d64535a9ed49a9adde864f18c9b56960` | Historical D4.3.0/M4.2.1 comparison; not a validated path for this bike |
| E-TUBE Professional 3.4.5 ZIP | [archive index](https://bettershifting.com/e-tube-project-archive/) | 60,529,291 | `62266eedf48e9a8f6ec25dd68c9c899f405bf41d9bf9fe3931786877644d4787` | Historical images, managed transport assemblies, and adapter-update files; kept outside Git |
| E-TUBE PROJECT Cyclist 5.0.2 APK | [APKCombo historical version page](https://apkcombo.com/e-tube-project-cyclist/com.shimano.etubeprojectmobile.droid.phone/download/phone-5.0.2-apk) | 115,738,926 | `b9b0ccb924f0dd1931beaada10501791b77268e4364bdb871010cd36ca606db2` | Historical Shimano-signed Android client used to recover the exact E5000 maximum-assist-speed getters, setter, and Reset/Apply flow; mirrored package and decompilation kept outside Git |
| Public E-TUBE Professional 5.4.4 service report | [public PDF](https://media-cdn-frz.alltricks.com/manuels/OCCTEST0011O2FEEL.pdf?1770975382=) | 75,228 | `b2429f926bd98f7e16e52a57b1b0462e1b30b1582d7aefe5903b12c3961495e7` | January 2026 live configuration cross-check showing D4.5.0, destination Type 1, and a separate 25 km/h maximum together; report contains identifiers and remains outside Git |
| E-TUBE 3.4.5 managed transport assemblies | Extracted `etubedatalinks.dll` / `smpce1com.dll` from the exact archive above | 851,456 / 82,944 | `814d8096d9f6e5552d8131ff840d3bf407b0f0b089c9a0a821cbb34f141e5ab5` / `c34eab626b4d31bb5dd1084569902fe43f0db205ea4572d16ec472e4c7c61e2b` | Generic DCAS-to-serial transport and loader-command/write-path audits; no hidden A0/A8 rewrite or client flash-read command found |
| SM-PCE1 3.1.3 / SM-PCE02 3.0.4 update files | Extracted from the exact 3.4.5 archive above | 28,867 / 64,360 | `ae1ac59063db670b684063a2738f5dd91e6801e049f6bdf5ca5a6a708a875fac` / `93e7889d678ec943cd99b32ba193777df1dacff86558b666d37147f72298d777` | Exact PCE02 ARM/transport audit rules out hidden A0 or A8 rewrite in its generic `0x48` path; PCE1 is µPD78F1807/78K0R but its update-package layout remains undecoded |
| SM-PCE1 3.0.2 update file | Extracted from E-TUBE 3.3.1 in the same archive collection | 28,867 | `be92d5bb2542f0cba61123203e7b5d44b6b3244c4abbf2f1649d1c9312dbc152` | Historical package-structure comparison; never installed |
| SM-PCE1 top-board photograph | [`rolandvs/shimano`](https://github.com/rolandvs/shimano/blob/master/pictures/SM-PCE1-PCB-TOP.jpg) | 1,065,052 | `7f040130ac6cffc572e9af2cd08f29766551ff71e1955aa3ad96a39d0feab4a3` | Public visual evidence for the µPD78F1807/78K0R/FB3 MCU identification |
| `freeMax.exe` | [`rolandvs/shimano`](https://github.com/rolandvs/shimano) | 128,000 | `fbe73c0ad4644fcad2607fc7ce3d164676ae42044dd49eed7848b8bb65643042` | Independent direct PCE1/BCR2 serial-client evidence; public repository is not a vendor authenticity guarantee |
| D4.1.0 raw image from E-TUBE Professional 3.4.5 | Extracted from the archived installer listed in the [archive index](https://bettershifting.com/e-tube-project-archive/) | 135,052 | `fdb0f40b94d55ce9d098f803fe0f2f4038a3ce3343fe539bf151a9511dda14ec` | Historical destination-gate cross-check; never sent to bike |
| M4.1.0 raw image from E-TUBE Professional 3.4.5 | Same extracted installer | 116,128 | `ed5593f61b58509ab5f1b7c7bcd82415abb3d1dbf57283dfc5ffb90219be6224` | Paired historical parser sample; never sent to bike |
| eTuning E5000 historical preparation ZIP | [download](https://etuning-app.com/wp-content/uploads/2024/11/5000_430.zip), [guide](https://etuning-app.com/downgrade.pdf) | 146,098 | `4dee4d75ee83c22e951114cbf57332709c15be637ec2a8171bd82f9345adb137` | Historical preparation comparison, not installed |
| D4.3.0 unwrapped preparation image | Derive from `DUE5000-D.5.3.0.dat` in the exact preparation ZIP above | 132,072 | `3d3df4dfe3de333062f445b6719fa5033f93dc9d384448134ee6041d216c6af0` | Cross-version destination-handler analysis; never sent to bike |
| M4.2.1 preparation image | `DUE5000-M.5.2.1.dat` in the exact preparation ZIP above | 116,320 | `10190fd78e6527908c0e43405184c414b612bc4becce9ca5483612665ced6b56` | Exact paired preparation image; never sent to bike |
| D4.5.0 original DAT from 5.3.4 | Extract from exact archive above | 138,132 | `363a43fc6997d384e0d723fa241b034146365e7c48f1fc8cfda027a948c5a6a7` | Native baseline image; never sent to bike |
| M4.4.8 original DAT from 5.3.4 | Extract from exact archive above | 119,824 | `9ea350e988345a9d9fb41c1363562ca190f1a8d5e1cc8a38c6373f69b877f033` | Native baseline image; never sent to bike |
| D4.5.0 unwrapped analysis image | Derive from the original D DAT using the eTuning asset wrapper; see `RESEARCH.md` | 138,072 | `44806bd54aedff95a88bb73fafe0f0581297f2f67b2ea35545cea012899d90bb` | D handler analysis; selected excerpts committed in `docs/evidence/` |
| eTuning 1.0.32 and 3.0.7 XAPKs | User-supplied APKCombo packages; exact filenames/sizes/hashes in [`docs/evidence/source-artifact-hashes.json`](docs/evidence/source-artifact-hashes.json) | 2,215,339 / 7,228,364 | See manifest | Client policy, direct `A8`, and current import allowlist. The 3.0.7 base APK is 7,060,465 bytes, SHA-256 `d4d545150f025760a13bf3bcade148f278731a1d49bf59d1e9da338723c90e22`; its allowlist accepts the exact public stock D4.3.0/M4.2.1 files |
| E-TUBE 3.4.5 boot-patch managed assemblies | `etubedatalinks.dll` / `etubecommons.dll` / `etubedata.dll` from the exact 3.4.5 archive above | 851,456 / 215,040 / 2,128,384 | `814d8096d9f6e5552d8131ff840d3bf407b0f0b089c9a0a821cbb34f141e5ab5` / `90d57684bd06caa6071d143357a61432c5f8225b72694271f5da18ce7bb7131c` / `e67f2a12a678628521095dfef9cc27d5588abda8988606206b03ad43382e1dbe` | Exact E5000 `1UPDATEX-01` boot-patch specification, header, and update-path audit. No corresponding payload was found in the public client catalogs/installers reviewed |
| eTuning 2.0.7 and 2.0.8 XAPKs | [APKPure release history](https://apkpure.net/tw/etuning-for-shimano-steps/eTuning.for.shimnao.steps/versions); inspected 2026-09-24 | 3,269,456 / 4,449,124 | `2cc423559bd920f8003d3b6e5e8346ecfc9a33c4cb313a776ec5bd4f4a82d231` / `d74d65ed41e550c43ef5f5857c6cdd0786429ac712ab2486f9f9ea28998235ef` | Release-diff check of the advertised E5000 assistance-save fix; no destination/PC-mode change found |
| eMaxMobileApp 1.89 APK | [APKPure landing page](https://apkpure.net/emaxmobileapp/com.emaxtuning.emaxmobileapp); served APK inspected 2026-09-24 | 1,046,473 | `1a55a436bbf15706bc8ee6476a0a181283342de2170303ed01504b01ffeb6968` | Independent direct-`A8` implementation evidence. The landing page advertised a different hash, so this is not treated as vendor-authenticated |
| STUnlocker Android 1.21.157 APK | [Uptodown release page](https://st-unlocker.en.uptodown.com/android/download); Google Play-matching package retrieved through APKPure on 2026-09-24 | 3,409,980 | `1bedd98101fcbbbaa6964e821bdd846a14a86b4d661a706b27ce18975b13e183` | Independent direct-`A8`, `A0`, and connection-flow audit; package kept outside Git |
| STUnlocker Android 1.20.153 APK | [APKFab version history](https://apkfab.com/stunlocker/com.stunlocker.app.su/versions); package retrieved through APKPure on 2026-09-24 | 3,606,457 | `0965e31e6db74f9d19b410bcba9bb04ad5b3a710638f6bdad6ab6d9935c71af9` | Intermediate historical cross-check; SHA-1 `64f6d5b41aedfe19b3a88d6f481e99195cda9a6c` matches APKFab and its signing certificate matches 1.21.157; package kept outside Git |
| `ShimanoBleProbe.zip` | User-supplied; exact fingerprint in the same manifest | 6,940 | See manifest | Earlier read-only probe source |
| Android bugreport ZIP / `btsnoop_hci.log` | Private user-supplied capture; bugreport fingerprint in the same manifest | 39,638,877 / 115,513 | Bugreport: manifest; snoop: `144a3bece6e0f8a6546cc641311ce619d21751dc7a31a4a8278078970e21c45b` | Session-auth and transport observations; contains identifiers and authentication material, so excluded |
| SC-E7000 4.0.6 display image | Extracted from the archived E-TUBE Professional 3.4.5 installer listed above | 123,100 | `ff934060d5a00e60817a153a557bde384ab2020ccbcd06c30a463549e62a3603` | Historical bridge-lifecycle comparison; never sent to bike and kept outside Git |
| SC-E6100 4.0.5 display image | [catalog URL](https://api.shimano.com/etube/public/data/upload/published/SCE6100.4.0.5.dat) | 164,488 | `9a3d9575af48eac883a2369af08bd00d819547c49c78d313d7aadc18269eeb77` | Exact display control for the contemporaneous DU-E5000/SC-E6100 success reports; MD5 `90ea6133e21bf5d59b40f999e5ea9a11`; never sent to bike and kept outside Git |
| SC-E7000 4.1.0 display image | [catalog URL](https://api.shimano.com/etube/public/data/upload/published/SCE7000.4.1.0.dat) | 126,508 | MD5 `4974d4f471b126be9f9657510e6bef55` (verified); plaintext SHA-256 `1f3c42ad0cc3e46d2e9affd5f023245f645acbc1c8ee3d68569bfcb25c9c3e79` | Bridge-mapping evidence, **obtained 2026-09-14**. The Akamai edge 403s a plain GET; sending the E-TUBE app User-Agent (`E-TUBE PROJECT Cyclist/4.1.0 (Android)`) reaches the AmazonS3 origin and returns the full image. Plaintext ARM Cortex-M (entropy 6.77), not encrypted. Kept private; not committed. |
| STEPS2 radio application 4.7.1 candidate | [vendor URL](https://api.shimano.com/etube/public/data/upload/published/UPDATENRF-STEPS2-ap.4.7.1.hex), [public catalog](https://github.com/reven-project/etubeapi/blob/master/fw-scraped.yml) | 125,032 | SHA-256 `0a52a9240febce92e2a033122c02aeaa23eadbaf1c8648628974dc257e3b9fa1`; catalog MD5 `0dc1d825cab2392460e56c7162dfe2bc` verified | Retrieved 2026-10-03 for offline serial-event analysis. Valid plaintext Intel HEX; range 0x1d000–0x27d8a, Thumb entry 0x27bd5. Exact-bike radio binding unverified; never installed; kept outside Git. |
| NRF2-STEPS radio application 4.3.0 candidate | [vendor URL](https://api.shimano.com/etube/public/data/upload/published/UPDATENRF2-STEPS-ap.4.3.0.hex), [public catalog](https://github.com/reven-project/etubeapi/blob/master/fw-scraped.yml) | 325,076 | SHA-256 `13987bc9b6fac8d872da1acc507a4808d4be17593e414da37fc38b080268e8a0`; catalog MD5 `157e7578e5bf3190a7ac6eeb605a83fd` verified | Retrieved 2026-10-03. Not plaintext Intel HEX despite extension; container remains undecoded. Different candidate family, not assumed compatible; never installed; kept outside Git. |

`tools/inspect_display_pc_mode.py` can verify the last image's fingerprint and
the bounded display-owned mode, repeated same-mode forwarding, and
topology-maintenance call graphs without dumping the image or making it a
repository dependency.
`tools/inspect_motor_destination.py` similarly verifies the exact D4.1.0,
D4.3.0, and D4.5.0 raw-image fingerprints, their A0/A8 gate invariants, PC-mode
request/promotion separation, secure tables, and startup zero ranges without
committing or dumping those images.
`tools/compare_display_pc_mode.py` verifies the SC-E6100 4.0.5 and SC-E7000
4.0.6/4.1.0 display-owned PC-mode comparison under the same exclusion policy.
`tools/inspect_pce02_transport.py` verifies the exact PCE02 3.0.4 vector,
initializer, opcode table, and transport function slices without committing or
dumping its image.
`tools/patch_motor_pc_mode.py` is a fail-closed, dry-run-by-default constructor
for the reviewed five-byte D4.5.0.1 derivative. It requires the exact source
fingerprint and original instruction bytes and checks the exact derived hash;
neither the source nor derived image is committed. Its rationale and the
unresolved wireless-recovery risk are documented in
[`docs/evidence/d450-pc-mode-patch-plan.md`](docs/evidence/d450-pc-mode-patch-plan.md).
`tools/inspect_motor_image_integrity.py` verifies the exact D4.1/D4.3/D4.5
header, entry/runtime/main calls, two initializer records, declared-size/end
literal invariants, and structured image tails. It finds no direct
application-level whole-image range or opaque signature trailer; it cannot
inspect the resident bootloader or prove a modified image boots.
`tools/inspect_etube_d_loader.py` verifies the exact E-TUBE 3.4.5 managed
assembly, complete Renesas-loader command enum, request/reply helper constants,
and host-binary/address/data/checksum/finish/reset call chain. No flash-read or
separate signature operation appears in that exact client path; this is not an
inspection of the resident motor loader. The detailed boundary is in
[`docs/evidence/d-loader-acceptance-analysis.md`](docs/evidence/d-loader-acceptance-analysis.md).
`tools/inspect_etuning_firmware_policy.py` decodes the exact eTuning 3.0.7
firmware MD5 allowlists and confirms that the public stock D4.3.0/M4.2.1 pair
is accepted by the current client. The bounded finding and live limits are in
[`docs/evidence/etuning-firmware-policy-analysis.md`](docs/evidence/etuning-firmware-policy-analysis.md).
`tools/inspect_etube_max_assist.py` verifies the exact Cyclist 5.0.2
DU-E5000 capability flag, command constants, packet construction,
hundredths-of-km/h conversion, and Reset/Apply call flow from JADX output. With
`--apk`, it also requires the recorded APK fingerprint. Its optional eTuning
3.0.7 pass verifies the independent destination-success -> 350 ms -> B0 chain
and can pin that base APK too; neither APK nor either decompilation is committed.
The corrected Renesas RX analysis status for the exact M4.4.8 image is recorded
in [`m448-max-assist-analysis.md`](docs/evidence/m448-max-assist-analysis.md).
The exact D4.5.0 cumulative-dispatch cases and B0 acceptance/persistence policy
are recorded separately in
[`max-assist-speed-analysis.md`](docs/evidence/max-assist-speed-analysis.md);
`tools/inspect_motor_max_assist.py` verifies them against the exact raw image
without dumping bytes. The vendor image and whole decompilation remain outside
Git.
`tools/inspect_etube_boot_patch.py` verifies the exact desktop E5000 boot-patch
specification, filename construction, file header, and update call chain. No
payload was recovered; [`docs/evidence/d5000-boot-patch-analysis.md`](docs/evidence/d5000-boot-patch-analysis.md)
records the artifact-search boundary.
The managed PCE transport, adapter update path, independent `freeMax` frames,
and old wired-patch ordering are documented in
[`docs/evidence/pce-transport-analysis.md`](docs/evidence/pce-transport-analysis.md).
That audit rules out a hidden A0 in both the normal desktop host and the exact
PCE02 path. PCE1's MCU family is identified, but its update-package layout and
running image remain undecoded.

The official [SC-E7000 user manual](https://si.shimano.com/en/pdfs/um/79H0B/UM-79H0B-000-ENG.pdf)
is the source for the display's Adjust, Shift timing, and RD protection reset
menu meanings. The [eTUBE API firmware catalog](https://github.com/reven-project/etubeapi/blob/master/fw-scraped.yml)
corroborates historical hashes but is not an authenticity guarantee. The
vendor's [eMaxMobileApp 1.89 release note](https://www.emax-tuning.com/new-version-of-emaxmobileapp-1-89-for-ios-and-android-released)
explicitly lists DU-E50X0 D4.5.0 as partially supported while saying that
speed-increasing settings cannot be changed through Bluetooth on the latest
firmware; it independently supports keeping the paired downgrade route as the
known BLE fallback rather than treating generic D4.5.0 connectivity as proof
of destination-write support.

The curated textual evidence is deliberately small. `d450-*.c` are selected
Ghidra decompilation outputs for the D4.5.0 image, and `etube-*.il` are selected
managed IL excerpts. Their function names/addresses are analyzer labels, and
the candidate sequence in `d450-destination-analysis.md` is historical and
explicitly superseded by its final correction. No binary package, whole
decompilation, or secret-bearing raw trace must be present to reproduce the
handoff's current bounded conclusions. Further bridge reconstruction may
require acquiring new private evidence.
