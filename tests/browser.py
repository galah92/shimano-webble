"""Run with Python + Playwright Chromium: python tests/browser.py."""
from pathlib import Path
import unittest
from playwright.sync_api import sync_playwright

HTML = (Path(__file__).resolve().parents[1] / 'index.html').read_text()
MOCK = r"""
window.options = OPTIONS;
window.operations = [];
window.characteristics = {};
const value = array => new DataView(Uint8Array.from(array).buffer);
class Characteristic extends EventTarget {
  constructor(short) { super(); this.short = short; }
  async readValue() {
    operations.push(['read', this.short]);
    if (this.short === '2af4') return value(options.shortChallenge ? [0] : [...Array(16).keys()]);
    if (this.short === '2af6') throw new DOMException('GATT operation not permitted', 'NotAllowedError');
    if (this.short === '2af7' && window.stage === 2 && !options.blockIdentity && (!options.requireSetup || window.setupDone))
      return value([...new TextEncoder().encode('SCE7000'), 0]);
    throw new DOMException('GATT operation not permitted', 'NotAllowedError');
  }
  async startNotifications() { operations.push(['subscribe', this.short]); }
  async writeValueWithResponse(packet) {
    packet = [...packet];
    operations.push(['write', this.short, packet]);
    if (this.short === '2afa') {
      const rx = characteristics['2af9'];
      if ([3, 4, 6].includes(packet[1])) {
        if (options.initDisconnect === packet[1]) { bike.gatt.disconnect(); return; }
        if (options.initTimeout === packet[1]) return;
        rx.value = value([packet[1] + 32, options.initReject === packet[1] ? 1 : packet[1] === 4 ? 141 : 0, 0, 0, 0, 0, 0, 0, 0, 0]);
        rx.dispatchEvent(new Event('characteristicvaluechanged'));
        if (packet[1] === 3) {
          characteristics['2afd'].value = value([0, 22, 128, 0, 0, 0, 0, 0, 0, 0]);
          characteristics['2afd'].dispatchEvent(new Event('characteristicvaluechanged'));
        }
        return;
      }
      const send = () => {
        rx.value = value([51, 1, packet[3] + 2, packet[3] === 28 ? 33 : 65, packet[3] === 28 ? 2 : 0, 255, 255, 255, 255, 255]);
        rx.dispatchEvent(new Event('characteristicvaluechanged'));
      };
      if (options.batchTimeout) return;
      if (options.lateDisplay && packet[3] === 28) { setTimeout(send, 8500); return; }
      if (options.lateDisplay && packet[3] === 44) return;
      if (options.motorDelayed) setTimeout(send, 20); else send();
      if (options.stalledWrite) return new Promise(() => {});
      return;
    }
    if (this.short === '2afe') {
      if (packet[1] === 22 && packet[2] === 172) {
        const rx = characteristics['2afd'];
        const slot = packet[3];
        if (options.batchTimeout || options.regionTimeout) return;
        // The other slot must not satisfy this query.
        rx.value = value([0, 22, 174, 1 - slot, 1, 0, 0, 0, 0, 0]);
        rx.dispatchEvent(new Event('characteristicvaluechanged'));
        rx.value = value(options.regionShort ? [0, 22, 174, slot] : [0, 22, 174, slot, options.regionValue ?? 0, 0, 0, 0, 0, 0]);
        rx.dispatchEvent(new Event('characteristicvaluechanged'));
        return;
      }
      if (options.motorFailure) throw new DOMException('Information write failed', 'NetworkError');
      if (options.motorDisconnect) { bike.gatt.disconnect(); return; }
      const rx = characteristics['2afd'];
      const send = () => {
        // Unrelated notification must not satisfy this request.
        rx.value = value([0, 22, 30, 33, 0, 0, 0, 0, 0, 0]);
        rx.dispatchEvent(new Event('characteristicvaluechanged'));
        if (options.motorTimeout || options.batchTimeout) return;
        rx.value = value(options.motorMalformed ? [0, 1, packet[2] + 2] :
          [0, 1, packet[2] + 2, packet[2] === 28 ? 33 : 71, packet[2] === 28 ? 0 : 1, 0, 0, 0, 0, 0]);
        rx.dispatchEvent(new Event('characteristicvaluechanged'));
      };
      if (options.motorDelayed) setTimeout(send, 20); else send();
      return;
    }
    if (this.short === '2aff') {
      if (options.setupFailure) throw new DOMException('Setup write failed', 'NetworkError');
      if (options.setupDisconnect) { window.bike.gatt.disconnect(); return; }
      if (options.setupTimeout) return new Promise(() => {});
      window.setupDone = true;
      return;
    }
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
    return {getCharacteristic: async uuid => {
      const short = uuid.slice(4, 8);
      return characteristics[short] ||= new Characteristic(short);
    }};
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
        self.assertEqual(self.writes()[-1], ['write', '2aff', [255, 0]])
        self.assertEqual(len(self.writes()), 3)

    def test_setup_unlocks_identity_after_delayed_read(self):
        self.open(requireSetup=True)
        self.auth()
        self.page.wait_for_function("document.getElementById('protected').textContent.startsWith('Session verified')")
        self.assertEqual([x[1] for x in self.writes()], ['2af3', '2af3', '2aff'])
        self.assertEqual(self.writes()[-1][2], [255, 0])
        operations = self.page.evaluate('operations')
        stage2 = next(i for i, x in enumerate(operations) if x[0] == 'write' and x[2][0] == 2)
        self.assertEqual(operations[stage2 + 1:], [['read', '2af7'], ['write', '2aff', [255, 0]], ['read', '2af7']])
        self.assertFalse(self.errors)

    def test_setup_failure_disconnect_and_timeout_stop(self):
        for option in ('setupFailure', 'setupDisconnect', 'setupTimeout'):
            with self.subTest(option=option):
                self.open(requireSetup=True, **{option: True})
                self.auth()
                self.page.wait_for_function("document.getElementById('status').textContent === 'Disconnected'", timeout=12000)
                self.assertEqual(len(self.writes()), 3)
                self.assertNotIn('MILESTONE', self.page.locator('#log').inner_text())
                self.assertFalse(self.errors)
                self.context.close()

    def test_disconnect_during_post_auth_delay_prevents_setup(self):
        self.open(requireSetup=True)
        self.auth()
        self.page.wait_for_function('window.stage === 2')
        self.page.locator('#disconnect').click()
        self.page.wait_for_timeout(600)
        self.assertEqual(len(self.writes()), 2)
        self.assertFalse(self.errors)

    def ready_for_identify(self, **options):
        self.open(requireSetup=True, **options)
        self.assertTrue(self.page.locator('#identify').is_disabled())
        self.auth()
        self.page.wait_for_function("!document.getElementById('identify').disabled")
        self.assertEqual(len(self.writes()), 3)  # No automatic information queries.
        self.page.locator('#identify').click()

    def test_drive_identity_both_response_orders(self):
        for delayed in (False, True):
            with self.subTest(delayed=delayed):
                self.ready_for_identify(motorDelayed=delayed)
                self.wait_batch()
                self.assertEqual(self.page.locator('#drive').inner_text(), 'DU-E7000; firmware 4.7.1')
                self.assertEqual(self.writes()[3:], [['write', '2afa', [0, 19, 1, 28, 0]], ['write', '2afa', [0, 19, 1, 44, 0]], ['write', '2afa', [0, 3, 0]], ['write', '2afa', [0, 4]], ['write', '2afa', [0, 6, 0]], ['write', '2afe', [0, 1, 28, 0]], ['write', '2afe', [0, 1, 44, 0]], ['write', '2afe', [0, 22, 172, 0]], ['write', '2afe', [0, 22, 172, 1]]])
                ops = self.page.evaluate('operations')
                self.assertLess(ops.index(['subscribe', '2afd']), ops.index(self.writes()[3]))
                self.assertFalse(self.errors)
                self.context.close()

    def test_drive_query_failure_stops_sequence(self):
        for option in ('motorFailure', 'motorDisconnect'):
            with self.subTest(option=option):
                self.ready_for_identify(**{option: True})
                self.page.wait_for_function("document.getElementById('status').textContent === 'Disconnected'", timeout=12000)
                self.assertEqual(self.writes()[8:], [['write', '2afe', [0, 1, 28, 0]]])
                self.assertNotIn('Drive-unit information:', self.page.locator('#log').inner_text())
                self.assertTrue(self.page.locator('#identify').is_disabled())
                self.assertFalse(self.errors)
                self.context.close()

    def wait_batch(self, timeout=65000):
        self.page.wait_for_function("document.getElementById('log').textContent.includes('information batch end')", timeout=timeout)

    def test_batch_continues_after_completed_writes_without_replies(self):
        self.ready_for_identify(batchTimeout=True)
        self.wait_batch()
        self.assertEqual(len(self.writes()), 12)
        self.assertEqual(self.page.locator('#status').inner_text(), 'Connected')
        self.assertTrue(self.page.locator('#identify').is_disabled())
        self.assertIn('Drive-unit firmware: no matching reply', self.page.locator('#log').inner_text())
        self.assertFalse(self.errors)

    def test_late_display_reply_cannot_satisfy_firmware_query(self):
        self.ready_for_identify(lateDisplay=True)
        self.wait_batch()
        log = self.page.locator('#log').inner_text()
        self.assertIn('Display model: no matching reply', log)
        self.assertIn('Display firmware: no matching reply', log)
        self.assertIn('DU-E7000; firmware 4.7.1', log)
        self.assertIn('2AF9 traffic: 4 notifications', log)

    def test_stalled_write_stops_even_with_matching_notification(self):
        self.ready_for_identify(stalledWrite=True)
        self.wait_batch()
        self.assertEqual(len(self.writes()), 4)
        self.assertIn('ATT write did not complete', self.page.locator('#log').inner_text())
        self.assertEqual(self.page.locator('#status').inner_text(), 'Disconnected')

    def test_short_replies_do_not_decode_but_batch_continues(self):
        self.ready_for_identify(motorMalformed=True)
        self.wait_batch()
        self.assertEqual(len(self.writes()), 12)
        self.assertIn('Drive-unit model: short reply', self.page.locator('#log').inner_text())
        self.assertNotIn('Drive-unit information:', self.page.locator('#log').inner_text())
        self.assertFalse(self.errors)

    def test_setup_reply_required_before_later_commands(self):
        for options in ({'initTimeout': 3}, {'initReject': 6}, {'initDisconnect': 4}):
            with self.subTest(options=options):
                self.ready_for_identify(**options)
                self.wait_batch()
                self.assertFalse(any(x[1] == '2afe' for x in self.writes()))
                self.assertEqual(self.page.locator('#status').inner_text(), 'Disconnected')
                self.assertIn('Drive-unit model: not completed', self.page.locator('#log').inner_text())
                self.assertFalse(self.errors)
                self.context.close()

    def test_region_reads_match_slot_and_never_write_destination(self):
        self.ready_for_identify()
        self.wait_batch()
        self.assertEqual(self.page.locator('#region').inner_text(), 'EU')
        self.assertFalse(any(x[1] == '2afe' and x[2][2] == 168 for x in self.writes()))
        self.assertIn('target US = 1', self.page.locator('#log').inner_text())

    def test_unknown_and_short_region_are_not_eu_or_ready(self):
        for options in ({'regionValue': 255}, {'regionShort': True}):
            self.ready_for_identify(**options)
            self.wait_batch()
            self.assertNotEqual(self.page.locator('#region').inner_text(), 'EU')
            self.assertIn('not verified', self.page.locator('#regionStatus').inner_text())
            self.context.close()

    def test_reported_motor_firmware_requires_preparation_in_app_policy(self):
        self.open()
        result = self.page.evaluate('regionReadiness([0,1,30,34,0], [0,1,46,69,0], [0,22,174,1,0])')
        self.assertIn('through preparation', result)
        already = self.page.evaluate('regionReadiness([0,1,30,34,0], [0,1,46,69,0], [0,22,174,1,1])')
        self.assertIn('US already reported', already)

    def test_captured_drive_fields_decode_without_assuming_target(self):
        self.open()
        result = self.page.evaluate('decodeDriveInfo([0,1,30,34,0], [0,1,46,69,0])')
        self.assertEqual(result, 'DU-E50X0 family; firmware 4.5.0')
        unknown = self.page.evaluate('decodeDriveInfo([0,1,30,255,0], [0,1,46,71,1])')
        self.assertEqual(unknown, 'Unknown model code 0xff; firmware 4.7.1')

    def test_aes_known_answer(self):
        self.open()
        result = self.page.evaluate("""async () => [...await encryptBlock(
          Uint8Array.from({length:16}, (_,i)=>i),
          Uint8Array.from({length:16}, (_,i)=>i*17))]
        """)
        self.assertEqual(bytes(result).hex(), '69c4e0d86a7b0430d8cdb78070b4c55a')

if __name__ == '__main__':
    unittest.main()
