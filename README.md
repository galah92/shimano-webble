# Shimano WebBLE

A single-file Web Bluetooth bike-status page for the tested Shimano SC-E7000
endpoint and E50X0 motor family. [Open the HTTPS page](https://galah92.github.io/shimano-webble/).
The guided action authenticates the BLE session and reads motor identity,
firmware, and current destination. It does **not** change region or firmware.

**Current result:** the bike reports native D `4.5.0.0`, M `4.4.8.0`, and EU
destination (`0`). A direct US (`1`) command was rejected; later protected-mode
staging commands were also rejected. No validated US-region or higher-speed
outcome exists. The previous setting code is dormant and unreachable from the
page's active controls.

Start with [HANDOFF.md](HANDOFF.md) for the exact goal, verified results,
failed experiments, decisions, and next evidence needed. [ASSETS.md](ASSETS.md)
lists sources and hashes for material excluded from public Git.
[RESEARCH.md](RESEARCH.md) is the detailed chronological lab notebook; its
older hypotheses must be read with the latest correction. The former
build-by-build README is archived in [docs/README-history.md](docs/README-history.md).

## Develop and verify

There is no build step. Serve `index.html` locally for UI development:

```sh
python3 -m http.server 8000 --bind 127.0.0.1
```

Use HTTPS on a phone for Web Bluetooth. Synthetic browser tests require
Python Playwright and its Chromium browser; they use simulated GATT responses,
not the bike:

```sh
python3 -m pip install playwright
python3 -m playwright install chromium
python3 tests/browser.py
python3 tests/region_write.py
python3 tests/log_export.py
node tests/region_compatibility.cjs
```

GitHub Pages serves the repository root from `main`. Verify the Pages workflow
and the live page after publishing a change. No private files or external
analysis directory are required to run the page or these tests.
