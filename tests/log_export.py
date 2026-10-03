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
        self.page.locator('summary').filter(has_text='Technical details and log').click()

    def tearDown(self):
        self.browser.close()
        self.p.stop()

    def set_log(self, text):
        self.page.evaluate("text => document.getElementById('log').textContent = text", text)

    def test_full_copy_preserves_large_log_and_compact_export_stays_bounded(self):
        source = '[old] Connected; test\n' + ('Diagnostic line — 0123456789\n' * 15000) + 'LAST RESULT\n'
        self.set_log(source)
        compact = self.page.evaluate('exportLog()')
        expected = self.page.evaluate('exportFullLog()')
        self.page.locator('#copyLog').click()
        self.assertEqual(self.page.evaluate('window.copied'), expected)
        self.assertLess(len(compact), 8000)
        self.assertIn("LAST RESULT", expected)
        self.assertIn("omitted", compact)
        self.assertIn(source, expected)
        self.assertEqual(self.page.locator("#log").inner_text(), source)
        self.assertTrue(expected.rstrip().endswith('JavaScript characters)'))

    def test_latest_session_keeps_last_connection_outcome(self):
        latest = '[new] Connected; test\nCurrent destination: EU\nDisconnected\n'
        self.set_log('[old] Connected; test\nOLD RESULT\n' + latest)
        self.page.locator('#copyLog').click()
        copied = self.page.evaluate('window.copied')
        self.assertIn(latest, copied)
        self.assertNotIn('OLD RESULT', copied)
        self.assertIn('END SHIMANO LOG', copied)

    def test_setting_failure_survives_later_read_only_reconnect(self):
        failed='[one] Connected; setting session\n'
        failed+='[one] --- motor authentication start; region and firmware unchanged ---\n'
        failed+='[one] MILESTONE: motor authentication completed and E8 regulation unlock returned EA.\n'
        failed+='[one] --- US-region attempt start; target OEM slot 1 = US (1) ---\n'
        failed+='[one] US-region attempt stopped: protected PC mode 5 rejected 3A.\n'
        latest='[two] Connected; read-only recovery\n[two] Current destination: EU\n'
        self.set_log(failed+latest)
        self.page.locator('#copyLog').click()
        copied=self.page.evaluate('window.copied')
        self.assertIn('motor authentication completed',copied)
        self.assertIn('US-region attempt stopped',copied)
        self.assertIn('Current destination: EU',copied)

    def test_report_preserves_entry_failure_and_restart(self):
        source='[one] Connected; test\n[one] Bootloader entry/exit probe started.\n'
        source+='[one] QUERY TRAFFIC setup / 2AFD: noise\n'*1000
        source+='[one] Entry pca-request: stopped reply-timeout\n[two] Connected; test\n'
        source+='[two] TX 2AFA setup: 00 04\n'*1000
        source+='[two] Post-probe readback: original configuration matches\n'
        self.set_log(source)
        copied=self.page.evaluate('exportLog()')
        self.assertLess(len(copied),8000)
        self.assertIn('Entry pca-request: stopped reply-timeout',copied)
        self.assertIn('Post-probe readback',copied)
        self.assertNotIn('QUERY TRAFFIC',copied)
        self.assertIn('END SHIMANO LOG',copied)

    def test_full_copy_keeps_exit_details_after_reload_without_a_bike_run(self):
        source='[one] Connected; test\n[one] Ready. Build 2026-10-03.96.\n'
        source+='[one] --- early display-queue timing probe start; AC read only ---\n'
        source+='[one] TX 2AFA SC-E7000-owned PC mode exit: 00 0C 00\n'
        source+='[one] ATT write completed: SC-E7000-owned PC mode exit\n'
        source+='[one] RX SC-E7000-owned PC mode exit display acknowledgement via 2AF9: 2C 00\n'
        source+='[one] Disconnected\n'
        self.page.evaluate('text => { document.getElementById("log").textContent=text; log("Retained result"); }',source)
        self.page.reload()
        self.page.locator('summary').filter(has_text='Technical details and log').click()
        self.page.locator('#copyLog').click()
        copied=self.page.evaluate('window.copied')
        self.assertIn(source,copied)
        self.assertIn('full session report',copied)
        self.assertIn('exported by build 2026-10-03.97',copied)
        self.assertIn('Copied full session report',self.page.locator('#exportStatus').inner_text())

    def test_report_preserves_pc_mode_route_and_echo_evidence(self):
        source='[one] Connected; test\n'
        source+='[one] PC-mode application slot observed via 2AFD: 0D\n'
        source+='[one] RX normal PC-link mode 1 secure echo 1 via 2AFB: 00 32 30 A2 2B\n'
        source+='[one] RX normal PC-link mode 1 completion via 2AFB: 00 32 12 01\n'
        source+='[one] MILESTONE: normal PC-link mode 1 accepted; entering protected inspection mode next.\n'
        source+='[one] US-region attempt stopped: protected PC mode 5: completion reply timed out; 0 secure echoes observed.\n'
        self.set_log(source)
        self.page.locator('#copyLog').click()
        copied=self.page.evaluate('window.copied')
        self.assertIn('PC-mode application slot observed via 2AFD: 0D',copied)
        self.assertIn('secure echo 1 via 2AFB',copied)
        self.assertIn('completion via 2AFB',copied)
        self.assertIn('protected PC mode 5: completion reply timed out',copied)

    def test_queue_probe_report_keeps_read_only_result(self):
        source='[one] Connected; test\n'
        source+='[one] --- early display-queue timing probe start; AC read only, no A0/A8/B0 or firmware ---\n'
        source+='[one] Queue probe context: previous US attempt remains recorded as non-US.\n'
        source+='[one] Queue probe timing: AC ATT acknowledgement to completion 17.2 ms.\n'
        source+='[one] MILESTONE: the read-only AC ATT write completed before motor mode-5 completion.\n'
        source+='[one] --- early display-queue timing probe end; no setting write or journal change ---\n'
        self.set_log(source)
        self.page.locator('#copyLog').click()
        copied=self.page.evaluate('window.copied')
        self.assertIn('Queue probe timing: AC ATT acknowledgement',copied)
        self.assertIn('no setting write or journal change',copied)

    def test_copy_failure_offers_manual_copy(self):
        self.page.evaluate('window.failCopy = true')
        self.page.locator('#copyLog').click()
        self.assertIn('Copy failed', self.page.locator('#exportStatus').inner_text())

if __name__ == '__main__':
    unittest.main()
