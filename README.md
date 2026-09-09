# Shimano WebBLE

A single-file, read-only Web Bluetooth diagnostic console for Shimano STEPS.

**Live site:** https://galah92.github.io/shimano-webble/

## Use

Open the live site in Chrome/Chromium on Android, enable Bluetooth, make the
Shimano endpoint discoverable, and tap **Connect Shimano**. The page subscribes
to 2AF3 indications and reads the 2AF4 challenge. **Try protected reads** probes
2AF6, 2AF7, and 2AF8; permission failures are logged for investigation.

The app does not perform configuration writes or implement Shimano session
authentication. Actual BLE behavior must be verified with the target hardware.

## Develop

Edit `index.html`; there is no build step or dependency installation.

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

## Source and handoff

`index.html` was imported from `shimano_webble_with_handoff.html` on
2026-09-09, preserving its embedded research and engineering handoff notes.
Those historical observations and provisional protocol models are source
context, not newly verified findings. The deployment limitations described in
the original notes predate this repository setup.

Keep passkeys, device identifiers, bugreports, and raw captures out of this
public repository. Continue with hardware validation of the existing read-only
flow before implementing authenticated-session support.
