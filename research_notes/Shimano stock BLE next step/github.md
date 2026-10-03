# GitHub implementations and current vendor firmware gates

## Is there a public stock-BLE E50X0 D4.5.0 region transaction or trace?

### Takeaway
Fresh GitHub repository, issue and indexed-code searches on 2026-10-03 found no independently demonstrated destination transaction or known-good BLE trace for the exact E50X0 D4.5.0/M4.4.8 + SC-E7000 topology. Relevant repositories provide firmware analysis, component hardware exploration or telemetry rather than the missing protected-setting prerequisite.

### Cited Findings
- `reven-plugin-etube` exposes firmware-header, encryption/decryption and ImHex pattern commands; its source tree contains `crypto.py`, `fwinfo.py` and `hexpat.py`, rather than a BLE setting client. — [Repository](https://github.com/reven-project/reven-plugin-etube)
- `etubeapi` scrapes and retrieves firmware from Shimano's web API. It is not a motor command implementation. — [Repository](https://github.com/reven-project/etubeapi)
- `rolandvs/shimano` documents display/PCE hardware exploration and unproductive initial connection experiments. It was archived in August 2022; all five listed forks retain upstream-era last pushes (2021 or 2018), and its issues endpoint returned no issues. — [Repository](https://github.com/rolandvs/shimano); [fork inventory](https://api.github.com/repos/rolandvs/shimano/forks?per_page=100); [issues](https://api.github.com/repos/rolandvs/shimano/issues?state=all&per_page=100)
- The EP8 CAN analysis repository presently describes charger/battery captures and hardware sniffer tooling, not an E5000 destination transaction. — [Repository](https://github.com/CapnDeCode/shimano-steps-ep8-canbus-messages-analysis-data)
- `ottelo9/Shimano-Steps-Simulator-BT-E6000` contains battery UART protocol analysis and ESP32 simulation. Its category-independent `A0`/`A8` byte hits relate to battery registers, so they are not evidence of the motor category-16 setting path. — [Protocol notes](https://github.com/ottelo9/Shimano-Steps-Simulator-BT-E6000/blob/main/protocol_analysis/README.md)
- `Andrewpk/unlockSLbike` was a fresh repository-search hit for Shimano/region, but its README explicitly identifies Specialized SL motors and says the Shimano part is the drivetrain. It cannot be used as Shimano setting evidence. — [Repository](https://github.com/Andrewpk/unlockSLbike)
- `donnm/etubedb-mock-server` concerns the Professional application's web login flow. It supplies no BLE motor-setting implementation or acceptance trace. — [Repository](https://github.com/donnm/etubedb-mock-server)

### Inferences
- These sources offer no evidence that would justify repeating A0, removing its existing journal, or skipping authentication/source-state checks. Firmware-analysis helpers may be useful offline, but do not resolve runtime mode loss.

### Gaps
- No known-good category-16 destination trace was found in the searched public repositories, their visible issues or forks. Search coverage is bounded: GitHub anonymous repository/issue API plus indexed web code queries, not exhaustive authenticated global code search.
- Reproducible search scopes: repository queries `shimano steps`, `freeMax`, `shimano in:name,description,readme region`, `shimano bluetooth`, `etube shimano`, and `shimano unlock`; issue query `shimano region`; indexed queries with `Shimano` plus `0xA8`, `DCAS`, `2AFE`, `eMax`, `STUnlocker`, `DUE5000`, and `E50X0`.

## Do current commercial primary sources support untouched D4.5.0 BLE region changes?

### Takeaway
Current E5000-specific primary documentation still draws the same boundary: Bluetooth destination and wheel changes on older D4.3 firmware, latest D4.5 support through a wired PCE interface. In-app automatic preparation eliminates external manual steps, but the vendor explicitly describes it as downgrade/preparation; it does not establish an untouched-stock solution.

### Cited Findings
- The current eMax capabilities PDF, revision 3.2 dated 17 May 2026, page 20 / section 11.1, names eMaxMobileApp 1.89 and has green checks for destination and wheel circumference on D4.2.1–4.3.0 and red crosses for both on D4.4.2–4.5.0. This was verified visually because text extraction omits the icons. — [Primary PDF, page 20](https://www.emax-tuning.com/eMax-possibilities.pdf#page=20)
- The same eMax PDF page 21 / section 11.2 permits destination/circumference with miniMax 2.68 and states PCE1/PCE02 plus Windows are required. Its Bluetooth page separately notes downgrade to D4.2.1. — [Primary PDF, pages 20–21](https://www.emax-tuning.com/eMax-possibilities.pdf#page=21)
- STUnlocker's current website permits Bluetooth destination and circumference only through E5000 D4.3.0 while separately saying its Windows version supports current firmware via PCE. The global all-firmware support wording includes other settings and must not override the feature-specific gate. — [STUnlocker](https://stunlocker.com/)
- eTuning's current comparison, with sources reviewed 8 September 2026, says latest-firmware region changes on older motors without downgrade require Windows/Mac plus SM-PCE1 or SM-PCE02. It marks automatic in-app downgrade as eTuning's advantage for older motors. — [Primary comparison](https://etuning-app.com/compare/etuning-vs-emax-vs-stunlocker/)
- eTuning's live downgrade PDF now says the procedure is built into its Android/iPhone apps. Its E5000/E5080 table still specifies D4.3.0 for downgrade from D4.4 or higher. — [Primary PDF](https://etuning-app.com/downgrade.pdf)
- eMax's August 2025 miniMax release note explicitly lists E50X0 D4.5.0 optimization in combination with a cable-bound PCE interface. — [Release note](https://www.emax-tuning.com/new-version-2-62-of-minimax-released)

### Inferences
- Marketing phrases such as all firmware, phone-only, or no external process do not prove stock-D4.5 destination acceptance. The exact model + function + transport + preparation clauses remain decisive.
- This fresh verification does not disprove a creative stock-BLE route, but supplies no new causal prerequisite that would make another write evidence-based.

### Gaps
- Vendors do not publish the packet sequence, bus timing or source/target state that distinguishes their wired latest-firmware route from Bluetooth rejection. No source found proves an E5000 D4.5 BLE region write without preparation.

## Do newer Bluetooth claims or alternate speed features transfer to this bike?

### Takeaway
New EP801/EP6 Pro claims are a useful sign that firmware preparation can enable Bluetooth features, but they are explicitly generation-specific and require a firmware adjustment. Speedometer calibration and wheel edits are separate features and cannot be treated as an accurate E5000 US-region solution.

### Cited Findings
- eTuning currently advertises Bluetooth region/circumference on compatible EP801/EP6 with Pro. Its dedicated guide requires following an app-directed firmware adjustment before configuring region. It excludes EP5/EP500 from that Pro route. — [Primary guide](https://etuning-app.com/deslimitar-shimano-ep801-ep6-ep500/)
- eTuning distinguishes region, which preserves real speed indication, from circumference changes, which alter the speed/distance calculation. — [Primary FAQ](https://etuning-app.com/en/faq/)
- STUnlocker's iOS manual lists speedometer calibration on E5000 D4.5, but market and wheel circumference only on D4.3. The calibration section describes displayed-speed correction, not increasing assistance cutoff. — [Primary iOS manual](https://stunlocker.com/doc/ST_Manual_iOS.pdf)

### Inferences
- The next stock-BLE experiment should answer the actual missing state question. A basic success with a read-only getter establishes forwarding/order only; none of these public sources makes getter success equivalent to A0 acceptance.
- A future commercial fallback can fit no-new-hardware if in-app preparation is accepted, but that remains a change of firmware and is outside the user's presently preferred untouched-stock route.

### Gaps
- No EP801/EP6 preparation details or accepted modified-image mechanism were publicly documented that could be transferred to E5000.
- No current primary source found supplies an accurate-speed, unchanged-D4.5 BLE workaround other than the unvalidated stock-protocol research already underway.
