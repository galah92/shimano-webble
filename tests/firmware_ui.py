"""Browser check for the local-only pair pickers and top-level workflow gates."""
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
    expect(page.locator('#build')).to_contain_text('2026-09-10.62')
    expect(page.locator('#setUS')).to_be_disabled()
    expect(page.locator('#bootProbe')).to_be_disabled()
    page.locator('#preparationFiles').set_input_files([
        {'name': 'D.dat', 'mimeType': 'application/octet-stream', 'buffer': bytes(256)},
        {'name': 'M.dat', 'mimeType': 'application/octet-stream', 'buffer': bytes(256)}])
    expect(page.locator('#preparationStatus')).to_contain_text('Files not accepted: Unrecognized')
    page.locator('#restorationFiles').set_input_files([])
    expect(page.locator('#restorationStatus')).to_contain_text('Select one reviewed ZIP or exactly two')
    page.locator('#firmwareConsent').check()
    page.locator('#powerCycled').check()
    expect(page.locator('#bootProbeStatus')).to_contain_text('Select and verify both')
    assert page.locator('#preparationFiles').get_attribute('accept') == '.zip,.dat'
    assert page.locator('a[href$="5000_430.zip"]').count() == 1
    assert page.locator('#copyLog').count()==1 and page.locator('#clearLog').count()==1
    assert not errors, errors
    browser.close()
print('Firmware picker browser check passed')
