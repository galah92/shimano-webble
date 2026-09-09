"""Read-only identity descriptor experiment, including unsupported responses."""
import unittest
from playwright.sync_api import sync_playwright
import browser

class DescriptorTests(unittest.TestCase):
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

    def test_full_descriptor_and_unavailable_cases(self):
        for opts, expected in [({}, 'Motor model descriptor ASCII:'),
                               ({'descriptorError': True}, 'device error: 00 16 7F 3A 00'),
                               ({'descriptorShort': True}, 'RESULT Motor model descriptor: short reply'),
                               ({'descriptorTimeout': True}, 'RESULT Motor model descriptor: no matching reply')]:
            with self.subTest(opts=opts):
                self.ready_for_identify(motorModel=34, motorFirmware=69, motorPatch=0, **opts)
                self.wait_batch()
                log = self.page.locator('#log').inner_text()
                self.assertIn(expected, log)
                self.assertEqual(self.page.locator('#region').inner_text(), 'EU')
                packets = [w[2] for w in self.writes() if w[1] == '2afe']
                self.assertEqual(packets, [[0,1,28,0],[0,1,44,0],[0,22,172,0],[0,22,172,1],[0,22,124,0]])
                if opts: self.assertIn('no variant inferred', log)
                else: self.assertIn('00 16 7E 00 00 00 00 00 00 00 (10 bytes total)', log)
                self.assertFalse(self.errors)
                self.context.close()

if __name__ == '__main__': unittest.main()
