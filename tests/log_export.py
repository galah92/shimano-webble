"""Export regression checks, without Bluetooth hardware."""
from pathlib import Path
import unittest
from playwright.sync_api import sync_playwright
HTML = (Path(__file__).resolve().parents[1] / 'index.html').read_text()

class LogExportTests(unittest.TestCase):
    def setUp(self):
        self.p = sync_playwright().start()
        self.browser = self.p.chromium.launch()
        self.context = self.browser.new_context(accept_downloads=True)
        self.page = self.context.new_page()
        self.page.add_init_script("""Object.defineProperty(navigator, 'clipboard', {value: {
          writeText: async text => { window.copied = text; if(window.failCopy) throw Error('denied'); }
        }});""")
        self.page.route('https://shimano.test/', lambda r: r.fulfill(body=HTML, content_type='text/html'))
        self.page.goto('https://shimano.test/')

    def tearDown(self):
        self.browser.close()
        self.p.stop()

    def set_log(self, text):
        self.page.evaluate("text => document.getElementById('log').textContent = text", text)

    def test_copy_preserves_large_latest_session(self):
        source = '[old] Connected; test\n' + ('Diagnostic line — 0123456789\n' * 15000) + 'LAST RESULT\n'
        self.set_log(source)
        expected = self.page.evaluate('exportLog()')
        self.page.locator('#copyLog').click()
        self.assertEqual(self.page.evaluate('window.copied'), expected)
        self.assertIn(source, expected)
        self.assertTrue(expected.rstrip().endswith('JavaScript characters)'))

    def test_latest_session_keeps_complete_last_connection(self):
        latest = '[new] Connected; test\nRESULT EU\nDisconnected\n'
        self.set_log('[old] Connected; test\nOLD RESULT\n' + latest)
        self.page.locator('#copyLog').click()
        copied = self.page.evaluate('window.copied')
        self.assertIn(latest, copied)
        self.assertNotIn('OLD RESULT', copied)
        self.assertIn('END SHIMANO LOG', copied)

    def test_copy_failure_offers_manual_copy(self):
        self.page.evaluate('window.failCopy = true')
        self.page.locator('#copyLog').click()
        self.assertIn('Copy failed', self.page.locator('#exportStatus').inner_text())

if __name__ == '__main__':
    unittest.main()
