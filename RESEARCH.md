# Session authentication investigation

Updated 2026-09-09. Target: SC-E7000 + DU-E7000 firmware 4.7.1, using an
Android phone over Bluetooth. The objective is a reproducible US-destination
configuration workflow, implemented in the single `index.html` where feasible.

## Evidence boundaries

User-reported live results: WebBLE connects, 2AF4 returns a changing 16-byte
value, and 2AF6/7/8 reads fail despite Android bonding and link encryption.
The user reports that successful Shimano-app session setup makes 2AF7 readable
and returns display identification. The underlying captures have not yet been
examined in this checkout.

This supports investigating application session setup. A 16-byte changing
value alone does not establish its cryptographic construction, key derivation,
or required response. Readability of 2AF7 is the operational success criterion;
it does not establish authorization to change motor configuration.

## Firmware evidence checked against primary sources

1. [eTuning's firmware guide](https://etuning-app.com/downgrade.pdf), pages
   2 and 4, retains historical E7000 guidance: 4.5.0 for preparation from
   4.6+, and region/wheel changes listed through 4.5.0. Its new first page says
   the preparation procedure is now integrated into the Android/iPhone apps.
2. [The live eTuning compatibility checker](https://etuning-app.com/en/), with
   **E7000** selected, advertises mobile Bluetooth configuration regardless of
   installed firmware and an internally handled preparation workflow. Verified
   both in the page source and by selecting the model in Chromium.

Interpretation: the historical direct-configuration restrictions and current
phone-only capability can coexist if the modern app performs preparation.
Neither source establishes the actual sequence, whether firmware is changed
for this bike, or whether version 3.0.7 already implements today's advertised
workflow. The alleged 4.7.7 boundary remains unverified. Do not encode a
firmware cutoff or initiate preparation based on these claims alone.

## Required artifacts

Retrieve the original HCI-containing Android bugreport and eTuning 3.0.7,
then 1.0.32 and ShimanoBleProbe.zip. They are not present in the current
checkout or the searched local paths. The Drive root listing contained the
HTML but none of these artifacts. Drive text search returned no artifact
matches; its MIME filtering means this does not establish absence of archives
elsewhere in Drive. Attachments from the originating conversation are not
available in this thread.

Keep original binaries/captures in a private analysis directory outside this
public repository. Record hashes and app package/version metadata locally.

## Next analysis sequence

1. Extract the Bluetooth snoop log. Identify the target connection and ATT
   service discovery, mapping handles to UUIDs from that capture rather than
   assuming stable handles across sessions.
2. Reconstruct the complete ordered exchange from connection through the
   first successful 2AF7 read. Include notification subscriptions, ATT writes
   and responses, indications and confirmations, errors, and timing. Separate
   connections and verify capture completeness before treating missing packets
   as evidence.
3. Follow the APK's 18FF/2AF4/2AF3 call chain. Establish the triggering state,
   challenge transformation, key inputs, message framing, and success/failure
   transitions. Crypto imports alone are insufficient evidence of usage here.
4. Validate the recovered algorithm offline against complete captured sessions.
   Prefer at least two distinct challenges to exclude a hard-coded replay.
   Keep private test vectors out of the public repo.
5. Implement only the explained session exchange in `index.html`; verify it
   using simulated GATT responses before a live test. Then check 2AF7 on the
   bike and compare the result with the known-good app capture.
6. Investigate motor-level configuration authorization and firmware preparation
   separately after session access is established.

No authentication or configuration writes have been added in this research
step. The existing deployed diagnostic remains the hardware baseline.
