"""Browser check for the single local bundle picker and top-level workflow gates."""
from pathlib import Path
from playwright.sync_api import sync_playwright, expect
html = (Path(__file__).resolve().parents[1] / 'index.html').read_text()
with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page()
    errors = []
    page.on('pageerror', lambda error: errors.append(str(error)))
    page.route('https://shimano.test/', lambda route: route.fulfill(body=html, content_type='text/html'))
    page.goto('https://shimano.test/')
    expect(page.locator('#build')).to_contain_text('2026-09-10.65')
    expect(page.locator('#guidedUS')).to_be_visible()
    expect(page.locator('#guidedUSStatus')).to_contain_text('six-digit Shimano passkey')
    expect(page.locator('#firmwareFiles')).to_be_hidden()
    expect(page.locator('#setUS')).to_be_disabled()
    expect(page.locator('#bootProbe')).to_be_disabled()
    page.locator('#firmwareFiles').set_input_files([
        {'name': 'D.dat', 'mimeType': 'application/octet-stream', 'buffer': bytes(256)},
        {'name': 'M.dat', 'mimeType': 'application/octet-stream', 'buffer': bytes(256)},
        {'name': 'restore.dat', 'mimeType': 'application/octet-stream', 'buffer': bytes(256)}])
    expect(page.locator('#firmwareStatus')).to_contain_text('Files not accepted: A selected file does not match')
    page.evaluate("document.getElementById('firmwareConsent').checked=true;controls()")
    expect(page.locator('#bootProbeStatus')).to_contain_text('Choose the preparation ZIP')
    assert page.locator('#firmwareFiles').get_attribute('accept') == '.zip,.dat'
    assert page.locator('#firmwareFiles').count() == 1
    assert page.locator('#powerCycled').count() == 0
    assert page.locator('a[href$="5000_430.zip"]').count() == 1
    assert page.locator('a[href$="DUE5000-D.4.5.0.dat"]').count() == 1
    assert page.locator('a[href$="DUE5000-M.4.4.8.dat"]').count() == 1
    assert page.locator('details #connect').count() == 1
    assert page.locator('#copyLog').count()==1 and page.locator('#clearLog').count()==1
    cached = page.evaluate('''async () => {
      await cacheFirmwareBundle([
        new File([Uint8Array.of(1,2,3)],'one.dat'),
        new File([Uint8Array.of(4,5)],'two.dat'),
        new File([Uint8Array.of(6)],'three.zip')]);
      const files=await readCachedFirmwareBundle();
      const result=files.map(file=>[file.name,file.size]);
      await clearCachedFirmwareBundle();
      return [result,await readCachedFirmwareBundle()];
    }''')
    assert cached == [[['one.dat',3],['two.dat',2],['three.zip',1]],None]
    assert not errors, errors
    browser.close()
print('Firmware picker browser check passed')
