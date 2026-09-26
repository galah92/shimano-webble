# eTuning 3.0.7 firmware-import policy

Date: 2026-09-24. This is an offline client audit. No subscription endpoint was
bypassed, no firmware was sent to the bike, and no destination command was
issued.

## Result

The exact eTuning 3.0.7 Android client accepts the public, stock E5000
D4.3.0/M4.2.1 preparation pair by exact MD5. The pair is not a secret modified
firmware build:

| File in [`5000_430.zip`](https://etuning-app.com/wp-content/uploads/2024/11/5000_430.zip) | Header version | Size | MD5 in eTuning 3.0.7 allowlist |
| --- | --- | ---: | --- |
| `DUE5000-D.5.3.0.dat` | D 4.3.0.0 | 132,072 | `6daee3c8de5ae0d4b77443e28c7bb758` |
| `DUE5000-M.5.2.1.dat` | M 4.2.1.0 | 116,320 | `492d14c37c8ee2fd4a636ab416eea143` |

The package itself is the historical preparation archive linked from
[eTuning's downgrade guide](https://etuning-app.com/downgrade.pdf). The exact
raw-image SHA-256 values and the ZIP fingerprint remain in `ASSETS.md`.

This closes one important ambiguity in the earlier research: the current app's
local import policy really does recognize the same two stock public files that
the repository's preparation workflow models. No server-only or patched E5000
image is required to pass this client-side allowlist.

## Exact client evidence

The audited XAPK is 7,228,364 bytes with SHA-256
`9964a346b708eb0c42e13dc08f71073e2dd1673b158b21491d57ac4f714b4eb9`.
Its base APK is 7,060,465 bytes with SHA-256
`d4d545150f025760a13bf3bcade148f278731a1d49bf59d1e9da338723c90e22`.

In JADX's `C0473Oa`:

- `m2065A(File)` calculates MD5.
- `m2079l()` constructs an obfuscated 18-member MD5 allowlist. Its first two
  decoded members are the exact D and M hashes above.
- `m2086u(File)` computes the file MD5 and checks membership in that allowlist.
- the ZIP import path extracts `.dat` entries, parses their firmware headers,
  rejects hashes outside the allowlist, applies compatibility checks, and then
  copies the accepted files into the app's private firmware directory.
- the actual update routines unwrap the accepted DAT container and pass its
  binary result into the transfer path; no E5000 application-byte patch was
  found between import and transfer.

The separate four-member `f1922c` set is a subset of the general allowlist and
does not contain the E5000 pair. It is used by a distinct special-case policy;
it does not alter the E5000 finding.

`tools/inspect_etuning_firmware_policy.py` independently decodes the obfuscated
sets, requires all exact members, fingerprints the optional XAPK/base APK, and
matches optional local firmware files by MD5 without printing their contents.
`tests/etuning_firmware_policy.py` covers the decoder and fail-closed allowlist
comparison with generated source.

## What this changes—and what it does not

The best-supported no-new-hardware route is now the stock BLE preparation
route: transfer the complete D4.3.0/M4.2.1 pair, reconnect and prove that exact
pair, perform one bounded destination transaction, prove US in a separate
power-cycle session, then restore the exact stock D4.5.0/M4.4.8 pair and prove
US again before measuring the assistance cutoff.

This client audit does **not** prove that wireless downgrade succeeds on this
bike, explain why commercial clients' direct `A8` works despite the D4.3
one-shot gate found in static analysis, prove the region write, or prove a
32 km/h assistance cutoff. Interruption during a wireless firmware transfer can
still require SM-PCE recovery. Those remain separate live gates.
