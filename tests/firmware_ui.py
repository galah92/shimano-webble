"""Browser check for the local-only firmware picker and invalid-file feedback."""
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
    expect(page.locator('#build')).to_contain_text('2026-09-09.28')
    expect(page.locator('#setUS')).to_be_disabled()
    page.locator('#firmwareFiles').set_input_files([
        {'name': 'D.dat', 'mimeType': 'application/octet-stream', 'buffer': bytes(256)},
        {'name': 'M.dat', 'mimeType': 'application/octet-stream', 'buffer': bytes(256)}])
    expect(page.locator('#firmwareStatus')).to_contain_text('Files not accepted: Unrecognized')
    page.locator('#firmwareFiles').set_input_files([])
    expect(page.locator('#firmwareStatus')).to_contain_text('Select exactly two')
    assert not errors, errors
    browser.close()
print('Firmware picker browser check passed')
