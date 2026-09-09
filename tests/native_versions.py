"""Read-only identity descriptor experiment, including unsupported responses."""
import unittest
from playwright.sync_api import sync_playwright
import browser

class NativeVersionTests(unittest.TestCase):
    open = browser.BrowserTests.open
    auth = browser.BrowserTests.auth
    ready_for_identify = browser.BrowserTests.ready_for_identify
    wait_batch = browser.BrowserTests.wait_batch
    writes = browser.BrowserTests.writes

    @classmethod
    def setUpClass(cls):
        cls.playwright = sync_playwright().start()
        cls.browser = cls.playwright.chromium.launch()

    @classmethod
    def tearDownClass(cls):
        cls.browser.close(); cls.playwright.stop()

    def test_native_versions_and_failure_boundary(self):
        for opts in ({}, {'nativeError': 0}, {'nativeShort': 0}, {'nativeTimeout': 0},
                     {'nativeWriteFailure': 0}, {'nativeDisconnect': 0}, {'nativeError': 1}):
            with self.subTest(opts=opts):
                self.ready_for_identify(motorModel=34, motorFirmware=69, motorPatch=0, **opts)
                self.wait_batch()
                if 'nativeTimeout' in opts: self.page.wait_for_timeout(700)
                log = self.page.locator('#log').inner_text()
                packets = [w[2] for w in self.writes() if w[1] == '2afe' and w[2][2] == 132]
                expected = [[0,1,132,0]] if opts and 0 in opts.values() else [[0,1,132,0],[0,1,132,1]]
                self.assertEqual(packets, expected)
                if not opts:
                    self.assertIn('Native D firmware: 4.5.0.7', log)
                    self.assertIn('Native M firmware: 4.2.1.7', log)
                elif 0 in opts.values():
                    self.assertNotIn('Native M firmware: 4.', log)
                self.assertTrue(self.page.locator('#setUS').is_disabled())
                self.assertFalse(self.errors)
                self.context.close()

if __name__ == '__main__': unittest.main()
