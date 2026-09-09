"""Run with Python + Playwright Chromium: python tests/browser.py."""
from pathlib import Path
import unittest
from playwright.sync_api import sync_playwright

HTML = (Path(__file__).resolve().parents[1] / 'index.html').read_text()
MOCK = r"""
window.options = OPTIONS;
window.operations = [];
const value = array => new DataView(Uint8Array.from(array).buffer);
class Characteristic extends EventTarget {
  constructor(short) { super(); this.short = short; }
  async readValue() {
    operations.push(['read', this.short]);
    if (this.short === '2af4') return value(options.shortChallenge ? [0] : [...Array(16).keys()]);
    if (this.short === '2af6') throw new DOMException('GATT operation not permitted', 'NotAllowedError');
    if (this.short === '2af7' && window.stage === 2 && !options.blockIdentity)
      return value([...new TextEncoder().encode('SCE7000'), 0]);
    throw new DOMException('GATT operation not permitted', 'NotAllowedError');
  }
  async startNotifications() { operations.push(['subscribe', this.short]); }
  async writeValueWithResponse(packet) {
    packet = [...packet];
    operations.push(['write', this.short, packet]);
    if (options.writeFailure) throw new DOMException('Write failed', 'NetworkError');
    if (options.disconnect) { window.bike.gatt.disconnect(); return; }
    if (options.timeout) return;
    const send = () => {
      this.value = value(options.malformed ? [16, packet[0]] :
        [16, packet[0], options.rejectStage === packet[0] ? 0 : 1]);
      window.stage = packet[0];
      this.dispatchEvent(new Event('characteristicvaluechanged'));
    };
    if (options.delayed) setTimeout(send, 20); else send();
  }
}
window.stage = 0;
window.bike = new EventTarget();
bike.name = 'SCE7000 test';
bike.gatt = {
  connected: false,
  async connect() { this.connected = true; return this; },
  disconnect() { this.connected = false; bike.dispatchEvent(new Event('gattserverdisconnected')); },
  async getPrimaryService() {
    return {getCharacteristic: async uuid => new Characteristic(uuid.slice(4, 8))};
  }
};
Object.defineProperty(navigator, 'bluetooth', {value: {requestDevice: async () => bike}});
"""

class BrowserTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.playwright = sync_playwright().start()
        cls.browser = cls.playwright.chromium.launch()

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.playwright.stop()

    def open(self, **options):
        import json
        self.context = self.browser.new_context(viewport={'width': 393, 'height': 851})
        self.addCleanup(self.context.close)
        self.page = self.context.new_page()
        self.errors = []
        self.page.on('pageerror', lambda error: self.errors.append(str(error)))
        self.page.add_init_script(MOCK.replace('OPTIONS', json.dumps(options)))
        self.page.route('https://shimano.test/', lambda route: route.fulfill(body=HTML, content_type='text/html'))
        self.page.goto('https://shimano.test/')
        self.page.locator('#connect').click()
        self.page.wait_for_function("!document.getElementById('probe').disabled")
        return self.page

    def auth(self):
        self.page.locator('#passkey').fill('123456')  # Synthetic fixture, not a captured secret.
        self.page.locator('#authenticate').click()

    def writes(self):
        return self.page.evaluate("operations.filter(x => x[0] === 'write')")

    def test_probe_never_writes_or_reads_passkey(self):
        self.open()
        self.assertEqual(self.writes(), [])
        self.assertNotIn(['read', '2af8'], self.page.evaluate('operations'))
        self.assertIn('not readable', self.page.locator('#protected').inner_text())

    def test_handshake_and_sensitive_log_omission(self):
        self.open()
        self.auth()
        self.page.wait_for_function("document.getElementById('protected').textContent.startsWith('Session verified')")
        writes = self.writes()
        self.assertEqual([x[1] for x in writes], ['2af3', '2af3'])
        self.assertEqual([len(x[2]) for x in writes], [17, 17])
        self.assertEqual([x[2][0] for x in writes], [1, 2])
        self.assertEqual(self.page.locator('#passkey').input_value(), '')
        self.assertTrue(self.page.locator('#authenticate').is_disabled())
        saved = self.page.evaluate("JSON.stringify(sessionStorage)")
        self.assertNotIn('123456', saved)
        for packet in writes:
            self.assertNotIn(' '.join(f'{n:02X}' for n in packet[2]), saved)
        self.assertFalse(self.errors)

    def test_acknowledgement_after_write_resolves(self):
        self.open(delayed=True)
        self.auth()
        self.page.wait_for_function("document.getElementById('protected').textContent.startsWith('Session verified')")
        self.assertEqual(len(self.writes()), 2)

    def test_rejected_first_stage_never_sends_second(self):
        self.open(rejectStage=1)
        self.auth()
        self.page.wait_for_function("document.getElementById('status').textContent === 'Disconnected'")
        self.assertEqual(len(self.writes()), 1)
        self.assertIn('rejected', self.page.locator('#log').inner_text())
        self.assertFalse(self.errors)

    def test_second_stage_rejected(self):
        self.open(rejectStage=2)
        self.auth()
        self.page.wait_for_function("document.getElementById('status').textContent === 'Disconnected'")
        self.assertEqual(len(self.writes()), 2)
        self.assertNotIn('MILESTONE', self.page.locator('#log').inner_text())

    def test_disconnect_during_auth(self):
        self.open(disconnect=True)
        self.auth()
        self.page.wait_for_function("!document.getElementById('connect').disabled")
        self.assertEqual(len(self.writes()), 1)
        self.assertEqual(self.page.locator('#challenge').inner_text(), '—')
        self.assertFalse(self.errors)

    def test_write_failure(self):
        self.open(writeFailure=True)
        self.auth()
        self.page.wait_for_function("document.getElementById('status').textContent === 'Disconnected'")
        self.assertEqual(len(self.writes()), 1)
        self.assertFalse(self.errors)

    def test_malformed_response(self):
        self.open(malformed=True)
        self.auth()
        self.page.wait_for_function("document.getElementById('status').textContent === 'Disconnected'")
        self.assertEqual(len(self.writes()), 1)

    def test_timeout(self):
        self.open(timeout=True)
        self.auth()
        self.page.wait_for_function("document.getElementById('status').textContent === 'Disconnected'", timeout=12000)
        self.assertEqual(len(self.writes()), 1)
        self.assertIn('timed out', self.page.locator('#log').inner_text())
        self.assertFalse(self.errors)

    def test_invalid_challenge_never_writes(self):
        self.open(shortChallenge=True)
        self.auth()
        self.page.wait_for_function("document.getElementById('status').textContent === 'Disconnected'")
        self.assertEqual(self.writes(), [])

    def test_acknowledged_but_read_blocked_is_not_success(self):
        self.open(blockIdentity=True)
        self.auth()
        self.page.wait_for_function("!document.getElementById('probe').disabled")
        self.assertIn('identification not verified', self.page.locator('#protected').inner_text())
        self.assertNotIn('MILESTONE', self.page.locator('#log').inner_text())
        self.assertEqual(len(self.writes()), 2)

    def test_aes_known_answer(self):
        self.open()
        result = self.page.evaluate("""async () => [...await encryptBlock(
          Uint8Array.from({length:16}, (_,i)=>i),
          Uint8Array.from({length:16}, (_,i)=>i*17))]
        """)
        self.assertEqual(bytes(result).hex(), '69c4e0d86a7b0430d8cdb78070b4c55a')

if __name__ == '__main__':
    unittest.main()
