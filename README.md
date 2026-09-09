# Shimano WebBLE

A single-file Web Bluetooth diagnostic and experimental session-authentication
console for Shimano STEPS. No configuration or firmware changes are implemented.

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

In build .7, tap **Run transport setup batch** after session verification.
It reads display information, sends three captured connection-setup commands,
then queries motor model and firmware. Keep Chrome foregrounded until
**information batch end** appears (allow up to one minute), then copy the log.
The summary includes ATT completion, replies, and notification traffic.

Missing or unexpected setup replies stop the run. Motor queries may continue
past unanswered completed writes. Reconnect for another batch. The setup
commands occur in both APK connection paths, but their internal semantics are
not fully decoded. No destination setter or firmware transfer is implemented.
Build .6 verified the display command path while the motor response channel
remained silent; this new sequence still needs a live test.

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
