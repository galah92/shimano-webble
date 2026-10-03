# Firsthand Reddit and related forum evidence for stock BLE region changes

## What does the user's exact EP8 Reddit thread establish?

### Takeaway
The thread contains firsthand Android/Bluetooth region-change success and a separate claim of reaching 32 km/h. It supplies no native firmware pair, display identity, command trace, or confirmed no-downgrade E5000 result, so it cannot explain the observed D4.5 A0 rejection.

### Cited Findings
- The question was posted 2023-05-10 and asks about changing EP8 EU25 to US32. On 2023-06-01 20:31:08 UTC, iPaidFairly says eTuning changed the region using Android; on 2024-03-09 23:06:07 UTC the same account says only the bike's Bluetooth connection was needed. No motor subtype, display, or firmware is supplied. [Android report](https://www.reddit.com/r/ebikes/comments/13djzkb/comment/jmiwk2y/); [Bluetooth-only clarification](https://www.reddit.com/r/ebikes/comments/13djzkb/comment/ku551qz/); exact dates from [Reddit comment API](https://www.reddit.com/api/info.json?id=t1_l5uw06d,t1_lstho7m,t1_jmiwk2y,t1_ku551qz).
- On 2024-05-27 08:27:54 UTC Mastergumble reports US → EU → US changes around maintenance and says it remains easy if the mechanic does not update firmware. On 2024-10-20 09:38:01 UTC they answer yes to whether they reached the US32 limit. This is a user confirmation of experience, not a recorded assistance-cutoff measurement: no GPS method, motor load, wheel size, B4 readback, or actual cutoff trace is provided. [Reversible changes](https://www.reddit.com/r/ebikes/comments/13djzkb/comment/l5uw06d/); [32 km/h answer](https://www.reddit.com/r/ebikes/comments/13djzkb/comment/lstho7m/); [timestamp API](https://www.reddit.com/api/info.json?id=t1_l5uw06d,t1_lstho7m,t1_jmiwk2y,t1_ku551qz).
- A 2024-11-14 nested comment explicitly asks whether anyone tried E5000 and has no success reply in the accessible thread. A 2026-06-06 reply says EP6/EP801/EP5 require PC eTuning plus SM-PCE02. This newer-generation note does not apply to E5000. [E5000 question](https://www.reddit.com/r/ebikes/comments/13djzkb/change_of_region_on_ep8_shimano_steps/lx53fbb/); [June 2026 reply](https://www.reddit.com/r/ebikes/comments/13djzkb/change_of_region_on_ep8_shimano_steps/oq67biz/).
- Two parent comments are deleted or removed, with a surviving question asking how to downgrade. Their content is inaccessible and must not be reconstructed from replies. Live HTML and Reddit JSON were accessible through the web tool; a Wayback retrieval returned an internal error and direct shell Reddit fetch returned no usable body. [Full live thread](https://www.reddit.com/r/ebikes/comments/13djzkb/change_of_region_on_ep8_shimano_steps/); [live JSON](https://www.reddit.com/r/ebikes/comments/13djzkb/change_of_region_on_ep8_shimano_steps/.json?limit=100).

### Inferences
- The reports establish that a Bluetooth region workflow existed for some Shimano systems in this period. They do not establish that the phone's geographical location selects motor destination, nor that native E5000 D4.5 accepts it without a firmware change.
- The mechanic-update caveat is evidence against treating old success as version independent.

### Gaps
- No known-good byte trace, native D/M pair, display identity, lighting transaction, protected-mode sequencing, or independently measured cutoff exists in the accessible thread.

## What do E5000-specific and broader r/ebikes reports add?

### Takeaway
The strongest newly found E5000 no-downgrade claim is outside Reddit and uses EW-WU111, not SC-E7000. It is worth a firmware/ownership comparison, but its missing firmware version prevents calling it a D4.5 counterexample.

### Cited Findings
- On 2024-05-29, Happyride user No01se describes a White E-XC 290 COMP with E5000, a purchased EW-WU111 for Bluetooth, eTuning, US registration, and 32 km/h. They explicitly say downgrade was unnecessary but do not know how they solved it. They also report that changing wheel diameter could produce a much higher speed. No original or current firmware number, display identity, update history, or recovery sequence appears. [Firsthand E5000 report](https://happyride.se/forum/threads/optimala-installningar-for-shimano-steps-e5000.3700908/).
- Shimano's release history dates E5000 4.5.0 to 2024-05-20. Happyride's report is nine days later, but a new bike need not already carry that firmware; temporal proximity is not proof of D4.5. [Shimano release history](https://uat-bike.shimano.com/no-NO/products/apps/e-tube-project-cyclist.html).
- A model/version-specific firsthand report on 2020-07-11 says E5000 4.3.0 worked with STUnlocker after going back into E-TUBE and setting 32 km/h. This supports the already documented destination-versus-configured-maximum distinction; it does not explain present D4.5 A0 rejection. [E5000 4.3 report, post 466](https://www.emtbforums.com/threads/stunlocker-ex-shimano-steps-unlocker-android-windows-app-for-derestriction-market-change-and-etc.4935/page-16).
- A 2024-06-04 E5000 4.5.0 owner asks about US-setting persistence using PCE02. The accessible passage is a question, not a success report. [Version-specific question, post 1174](https://www.emtbforums.com/threads/stunlocker-ex-shimano-steps-unlocker-android-windows-app-for-derestriction-market-change-and-etc.4935/page-40).
- The OP of a separate EP8 thread reports on 2023-03-06 that eTuning US32 improves connecting-road riding and describes reduced motor torque above about 28 km/h. This is stronger riding experience than a region-label screenshot, but still has no firmware/display or native-pair evidence. [EP8 riding experience](https://www.reddit.com/r/ebikes/comments/oamnui/comment/jb76c8n/).
- A 2025 E7000 discussion starts from a claim of no downgrade. One later account reports 35 km/h; another reports changing three bikes but says the process has several steps and blocks firmware upgrading. The OP never tried it. Neither commenter supplies firmware or a byte trace, and 35 km/h does not uniquely identify a correct-speed US32 transaction. [eTuning legitimacy thread](https://www.reddit.com/r/ebikes/comments/1imal19/is_this_etuning_app_legit/).
- An E6100 discussion explicitly recommends following the downgrade guide and says no special hardware is required when Bluetooth exists. This demonstrates phone-only and no-downgrade are different constraints. [E6100 discussion](https://www.reddit.com/r/ebikes/comments/1b73d20/).
- An EP801 user says recreating profile and phone location did not change motor region or speed. Another commenter mixes a remembered E6100 country setting with later PCE wheel editing. This is not a reliable official-app location recipe. [EP801 location attempt](https://www.reddit.com/r/ebikes/comments/1gnnv6i/).
- An SC-E5000 upgrade discussion is about EP8 motor plus non-Bluetooth display, not E5000 motor. The OP reports no solution by March 2025. Display and motor names must not be conflated. [SC-E5000 display discussion](https://www.reddit.com/r/ebikes/comments/1e6es35/shimano_sce5000_upgrade_to_use_etube_and_other/).

### Inferences
- The Happyride EW-WU111 owner is a credible distinct topology lead: compare that endpoint's PC-mode ownership and source-slot behavior offline, looking for a mode lifetime or host identity difference transferable to SC-E7000. Buying the dongle is outside the stated goal, and its behavior cannot be assumed equivalent.
- No searched r/ebikes result supplied a firsthand E5000 D4.5/M4.4.8 + SC-E7000 firmware-unchanged US success. This is bounded negative search evidence, not proof of impossibility.

### Gaps
- Happyride's motor firmware, exact bike update state, Bluetooth unit firmware, display, application version and complete operation order are all missing.
- The reports do not identify a stock-firmware read-only protected-mode query better than AC or provide a missing A0 prerequisite.

## Does this evidence support build95 as the next goal-directed test?

### Takeaway
Yes, conditionally: the early AC probe remains a useful discriminator of the newly found bus queue route, provided the result is described as timing/transport evidence. A successful AC cannot show that protected mode survives at A0 execution or that a region write will be accepted.

### Cited Findings
- STUnlocker currently advertises Bluetooth destination/circumference through E5000 4.3.0 and says Windows/PCE supports latest firmwares. The vendor separates basic Bluetooth connection from advanced-setting compatibility. [STUnlocker compatibility](https://stunlocker.com/).
- eMaxMobileApp 1.74's 2024-05-21 announcement explicitly lists support for E5000 4.5.0 but says maximum-assistance changes cannot be made by Bluetooth. Its miniMax 2.52 2024-06-17 and 2.62 2025-08-05 announcements describe 4.5.0 destination/wheel changes using wired PCE. These are primary vendor capability claims, not traces proving the limitation's cause. [Mobile announcement](https://www.emax-tuning.com/new-version-of-emaxmobileapp-1-74-for-ios-and-android-released); [miniMax 2.52](https://www.emax-tuning.com/new-version-2-52-of-minimax-released); [miniMax 2.62](https://www.emax-tuning.com/new-version-2-62-of-minimax-released).
- The repository documents exact SC-E7000 queue analysis and the AC probe's limitations, including that ordinary AC read success cannot establish protected A0 acceptance. [Repository bridge analysis](https://github.com/galah92/shimano-webble/blob/main/docs/evidence/bridge-analysis.md); [current research correction](https://github.com/galah92/shimano-webble/blob/main/RESEARCH.md).

### Inferences
- Expected useful result: AC admitted before observed mode completion and AE received afterward supports placing a phone-forwarded read immediately behind the display-owned handshake. It advances the queue-admission premise of the early-A0 hypothesis and should be paired with full transition logging.
- Failure or early completion eliminates that particular window for the measured connection; it does not imply a downgrade or patch is needed.
- Even the expected success is insufficient to dispatch A0: AC has a different policy gate, BLE observation timestamps are not bus timestamps, and asynchronous mode loss can still occur. The existing attempt journal should remain terminal until a separately reviewed hypothesis has enough evidence.
- A static comparison of EW-WU111 ownership/source state is the most concrete newly found research branch. A read-only wheel query is a separate fallback discriminator; the forum evidence does not make it a better destination-mode test than AC.

### Gaps
- No actual E5000 D4.5 known-good BLE trace or new protected-mode read-only discriminator was discovered.
- Search covered the linked thread, nested replies, related r/ebikes EP8/E6100/E7000 discussions, E5000/firmware/no-downgrade queries, primary compatibility announcements, and E5000 forum results. It does not claim an exhaustive crawl of every subreddit post.
