"""Run with Python + Playwright Chromium: python tests/browser.py."""
from pathlib import Path
import unittest
from playwright.sync_api import sync_playwright

HTML = (Path(__file__).resolve().parents[1] / 'index.html').read_text()
MOCK = r"""
window.options = OPTIONS;
window.operations = [];
window.characteristics = {};
window.currentMaxAssistSpeed = options.maxAssistSpeed ?? 2500;
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
      if ([3, 4, 6, 12].includes(packet[1])) {
        if (options.initDisconnect === packet[1]) { bike.gatt.disconnect(); return; }
        if (options.initTimeout === packet[1]) return;
        rx.value = value([packet[1] + 32, options.initReject === packet[1] ? 1 : packet[1] === 4 ? 141 : 0, 0, 0, 0, 0, 0, 0, 0, 0]);
        rx.dispatchEvent(new Event('characteristicvaluechanged'));
        if (packet[1] === 12 && !options.omitPcSlotAnnouncement) {
          const pcRx = characteristics['2afd'];
          pcRx.value = value([0, 0x32, 0x12, 1, options.pcApplicationSlot ?? 0x0d, 0xff, 0xff, 0, 0xff, 0xff]);
          pcRx.dispatchEvent(new Event('characteristicvaluechanged'));
        }
        if (packet[1] === 3) {
          characteristics['2afd'].value = value([0, 22, 128, 0, 0, 0, 0, 0, 0, 0]);
          characteristics['2afd'].dispatchEvent(new Event('characteristicvaluechanged'));
        }
        return;
      }
      const send = () => {
        if (packet[3] === 132) {
          rx.value=value(options.radioVersionError ? [51,1,135,57,0,0] :
            options.radioVersionShort ? [51,1,134,71,1] : [51,1,134,71,1,0,255,255,255,255]);
          rx.dispatchEvent(new Event('characteristicvaluechanged'));
          return;
        }
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
      if (packet[1] === 1 && packet[2] === 132) {
        const rx = characteristics['2afd'];
        if (options.nativeWriteFailure === packet[3]) throw new DOMException('Native write failed', 'NetworkError');
        if (options.nativeDisconnect === packet[3]) { bike.gatt.disconnect(); return; }
        const send = () => {
          rx.value = value(options.nativeError === packet[3] ? [0,1,135,58,0,0] :
            options.nativeShort === packet[3] ? [0,1,134,69,0] :
            options.nativeReplies ? options.nativeReplies[packet[3]] : [0,1,134,packet[3] ? 66 : 69,packet[3] ? 1 : 0,7,0,0,0,0]);
          rx.dispatchEvent(new Event('characteristicvaluechanged'));
        };
        if (options.nativeTimeout === packet[3]) { setTimeout(send, 8500); return; }
        send(); return;
      }

      if (packet[1] === 22 && packet[2] === 124) {
        const rx = characteristics['2afd'];
        if (options.descriptorTimeout) return;
        rx.value = value(options.descriptorError ? [0,22,127,58,0] : options.descriptorShort ? [0,22,126,0] : [0,22,126,0,0,0,0,0,0,0]);
        rx.dispatchEvent(new Event('characteristicvaluechanged'));
        return;
      }
      if (packet[1] === 22 && packet[2] === 172) {
        const rx = characteristics['2afd'];
        const slot = packet[3];
        if (options.batchTimeout || options.regionTimeout) return;
        if (options.regionAlternate) {
          const send = () => {
            rx.value = value([0, 22, 175, 58, 1, 0, 0, 0, 0, 0]);
            rx.dispatchEvent(new Event('characteristicvaluechanged'));
          };
          if (options.regionAlternateDelayed) setTimeout(send, 20); else send();
          if (options.regionAlternateWriteFailure) throw new DOMException('Destination write failed', 'NetworkError');
          return;
        }
        // The other slot must not satisfy this query.
        rx.value = value([0, 22, 174, 1 - slot, 1, 0, 0, 0, 0, 0]);
        rx.dispatchEvent(new Event('characteristicvaluechanged'));
        rx.value = value(options.regionShort ? [0, 22, 174, slot] : [0, 22, 174, slot, options.regionValue ?? 0, 0, 0, 0, 0, 0]);
        rx.dispatchEvent(new Event('characteristicvaluechanged'));
        return;
      }
      if (packet[1] === 22 && packet[2] === 180) {
        const rx = characteristics['2afd'];
        if (options.batchTimeout || options.maxAssistTimeout) return;
        const speed = window.currentMaxAssistSpeed;
        rx.value = value(options.maxAssistError ? [0,22,183,options.maxAssistError] :
          options.maxAssistShort ? [0,22,182,speed & 255] : [0,22,182,speed & 255,speed >> 8,0,0,0,0,0]);
        rx.dispatchEvent(new Event('characteristicvaluechanged'));
        return;
      }
      if (packet[1] === 22 && packet[2] === 176) {
        const rx = characteristics['2afd'];
        if (options.maxAssistWriteTimeout) return;
        if (options.maxAssistWriteReject !== undefined) {
          rx.value = value([0,22,179,options.maxAssistWriteReject,0,0,0,0,0,0]);
        } else {
          window.currentMaxAssistSpeed = packet[3] | packet[4] << 8;
          rx.value = value([0,22,178,0,0,0,0,0,0,0]);
        }
        rx.dispatchEvent(new Event('characteristicvaluechanged'));
        return;
      }
      if (packet[1] === 22 && packet[2] === 188) {
        const rx = characteristics['2afd'];
        if (options.batchTimeout || options.usMaxAssistTimeout) return;
        const speed = options.usMaxAssistSpeed ?? 3200;
        rx.value = value(options.usMaxAssistShort ? [0,22,190,packet[3],speed & 255] :
          [0,22,190,packet[3],speed & 255,speed >> 8,0,0,0,0]);
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
          [0, 1, packet[2] + 2, packet[2] === 28 ? (options.motorModel ?? 33) : (options.motorFirmware ?? 71), packet[2] === 28 ? 0 : (options.motorPatch ?? 1), 0, 0, 0, 0, 0]);
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
bike.id = 'synthetic-bike-id';
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
window.deviceChooserCalls = 0;
Object.defineProperty(navigator, 'bluetooth', {value: {requestDevice: async () => {deviceChooserCalls++; return bike;}}});
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
        self.page.locator('summary').filter(has_text='Technical details and log').click()
        self.page.locator('summary').filter(has_text='Manual protocol controls').click()
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

    def test_open_tab_reconnect_reuses_authorized_bike(self):
        self.open()
        self.assertEqual(self.page.evaluate('deviceChooserCalls'), 1)
        self.page.locator('#disconnect').click()
        self.page.wait_for_function("document.getElementById('status').textContent === 'Disconnected'")
        self.page.evaluate('connect(workflowDevice)')
        self.page.wait_for_function("!document.getElementById('probe').disabled")
        self.assertEqual(self.page.evaluate('deviceChooserCalls'), 1)
        self.assertTrue(self.page.evaluate('session.device === bike'))
        self.assertFalse(self.errors)

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

    def test_pending_restart_stops_after_native_error(self):
        self.ready_for_identify(nativeError=1)
        self.page.evaluate("""() => {
          probeRecord={verified:false};window.extraVerification=0;
          verifyPendingBootloaderProbe=async()=>{window.extraVerification++;};
        }""")
        self.wait_batch()
        self.assertEqual(self.page.evaluate('window.extraVerification'),0)
        self.assertIn('Restart verification incomplete: Native M firmware',self.page.locator('#log').inner_text())
        self.assertEqual(self.writes()[-1],['write','2afe',[0,1,132,1]])
        self.assertFalse(self.errors)

    def test_drive_identity_both_response_orders(self):
        for delayed in (False, True):
            with self.subTest(delayed=delayed):
                self.ready_for_identify(motorDelayed=delayed)
                self.wait_batch()
                self.assertEqual(self.page.locator('#drive').inner_text(), 'DU-E7000; firmware 4.7.1')
                self.assertEqual(self.writes()[3:], [['write', '2afa', [0, 19, 1, 28, 0]], ['write', '2afa', [0, 19, 1, 44, 0]], ['write', '2afa', [0, 3, 0]], ['write', '2afa', [0, 4]], ['write', '2afa', [0, 6, 0]], ['write', '2afa', [0, 12, 1]], ['write', '2afa', [0, 3, 75]], ['write', '2afa', [0, 4]], ['write', '2afa', [0, 6, 31]], ['write', '2afa', [0, 3, 0]], ['write', '2afa', [0, 4]], ['write', '2afa', [0, 6, 0]], ['write', '2afe', [0, 1, 28, 0]], ['write', '2afe', [0, 1, 44, 0]], ['write', '2afe', [0, 22, 172, 0]], ['write', '2afe', [0, 22, 172, 1]], ['write', '2afe', [0, 22, 180, 0]], ['write', '2afe', [0, 22, 188, 1]], ['write', '2afe', [0, 22, 124, 0]], ['write', '2afe', [0, 1, 132, 0]], ['write', '2afe', [0, 1, 132, 1]]])
                ops = self.page.evaluate('operations')
                self.assertLess(ops.index(['subscribe', '2afd']), ops.index(self.writes()[3]))
                self.assertFalse(self.errors)
                self.context.close()

    def test_drive_query_failure_stops_sequence(self):
        for option in ('motorFailure', 'motorDisconnect'):
            with self.subTest(option=option):
                self.ready_for_identify(**{option: True})
                self.page.wait_for_function("document.getElementById('status').textContent === 'Disconnected'", timeout=12000)
                self.assertEqual(self.writes()[15:], [['write', '2afe', [0, 1, 28, 0]]])
                self.assertNotIn('Drive-unit information:', self.page.locator('#log').inner_text())
                self.assertTrue(self.page.locator('#identify').is_disabled())
                self.assertFalse(self.errors)
                self.context.close()

    def wait_batch(self, timeout=110000):
        self.page.wait_for_function("document.getElementById('log').textContent.includes('information batch end')", timeout=timeout)

    def test_radio_version_is_one_cached_component_read_after_motor_reads(self):
        self.ready_for_identify()
        self.wait_batch()
        writes=self.writes()
        self.assertEqual(writes[-1],['write','2afa',[0,19,1,132,1]])
        self.assertEqual(sum(x[1]=='2afa' and x[2]==[0,19,1,132,1] for x in writes),1)
        self.assertIn('Display radio firmware: 4.7.1.0 (cached radio component read;',self.page.locator('#log').inner_text())
        self.assertFalse(any(x[1]=='2afe' and len(x[2])>2 and x[2][2] in [0xa0,0xa8,0xb0] for x in writes))
        self.assertFalse(self.errors)

    def test_radio_version_rejection_does_not_decode_or_retry(self):
        for option in ['radioVersionError','radioVersionShort']:
            with self.subTest(option=option):
                self.ready_for_identify(**{option:True})
                self.wait_batch()
                self.assertEqual(self.writes()[-1],['write','2afa',[0,19,1,132,1]])
                self.assertNotIn('Display radio firmware: 4.7.1.0',self.page.locator('#log').inner_text())
                self.assertEqual(sum(x[1]=='2afa' and x[2]==[0,19,1,132,1] for x in self.writes()),1)
                self.assertFalse(self.errors)
                self.context.close()

    def test_batch_continues_after_completed_writes_without_replies(self):
        self.ready_for_identify(batchTimeout=True)
        self.wait_batch()
        self.assertEqual(len(self.writes()), 25)
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
        self.assertIn('2AF9 traffic: 12 notifications', log)

    def test_stalled_write_stops_even_with_matching_notification(self):
        self.ready_for_identify(stalledWrite=True)
        self.wait_batch()
        self.assertEqual(len(self.writes()), 4)
        self.assertIn('ATT write did not complete', self.page.locator('#log').inner_text())
        self.assertEqual(self.page.locator('#status').inner_text(), 'Disconnected')

    def test_short_replies_do_not_decode_but_batch_continues(self):
        self.ready_for_identify(motorMalformed=True)
        self.wait_batch()
        self.assertEqual(len(self.writes()), 25)
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

    def test_read_only_assist_speed_diagnostics(self):
        self.ready_for_identify(maxAssistSpeed=2450, usMaxAssistSpeed=3200)
        self.wait_batch()
        self.assertEqual(self.page.locator('#assistLimit').inner_text(), '24.50 km/h')
        self.assertEqual(self.page.locator('#usAssistLimit').inner_text(), '32 km/h')
        packets=[x[2] for x in self.writes() if x[1]=='2afe' and x[2][2] in (0xb0,0xb4,0xbc)]
        self.assertEqual(packets,[[0,0x16,0xb4,0],[0,0x16,0xbc,1]])
        self.assertNotIn([0,0x16,0xb0,0x80,0x0c,0xff,0xff],packets)
        self.assertIn('read-only B4/B6',self.page.locator('#log').inner_text())
        self.assertFalse(self.errors)

    def test_us_with_lower_separate_ceiling_is_reported(self):
        self.ready_for_identify(regionValue=1,maxAssistSpeed=2400,usMaxAssistSpeed=3200)
        self.wait_batch()
        self.assertIn('US is reported, but the configured ceiling 24 km/h is below',
                      self.page.locator('#regionStatus').inner_text())
        self.assertIn('no setter was sent',self.page.locator('#regionStatus').inner_text())
        self.assertFalse(self.errors)

    def test_stock_us_ceiling_write_is_one_shot_and_power_cycle_verified(self):
        # Exact D4.5.0 firmware reports the US internal ceiling as 32.18 km/h;
        # Shimano's clients still request the user-facing 32.00 km/h.
        exact = dict(regionValue=1,maxAssistSpeed=2400,usMaxAssistSpeed=3218,
            motorModel=34,motorFirmware=69,motorPatch=0,
            nativeReplies={0:[0,1,134,69,0,0],1:[0,1,134,68,8,0]})
        self.ready_for_identify(**exact)
        self.wait_batch()
        self.assertTrue(self.page.locator('#setUSMax').is_disabled())
        self.page.evaluate('session.motorAuthenticated=true; controls();')
        self.assertTrue(self.page.evaluate('canSetUSMax(session)'))
        self.assertFalse(self.page.locator('#setUSMax').is_disabled())
        self.page.locator('#setUSMax').click()
        self.page.wait_for_function("document.getElementById('log').textContent.includes('one-attempt stock maximum-assist transaction end')",timeout=35000)
        b0=[x[2] for x in self.writes() if x[1]=='2afe' and x[2][2]==0xb0]
        self.assertEqual(b0,[[0,0x16,0xb0,0x80,0x0c,0xff,0xff]])
        self.assertEqual(self.page.locator('#assistLimit').inner_text(),'32 km/h')
        journal=self.page.evaluate("JSON.parse(localStorage.getItem('shimano-max-assist-us-v1'))")
        self.assertEqual(journal['stage'],'readback-verified')
        self.assertEqual(journal['expected']['usProfileHundredths'],3218)
        self.assertEqual(journal['expected']['targetHundredths'],3200)
        self.assertNotIn('synthetic-bike-id',str(journal))
        self.assertTrue(self.page.locator('#setUSMax').is_disabled())
        self.assertFalse(self.page.locator('#maxAssistPowerCycle').is_disabled())
        self.page.locator('#maxAssistPowerCycle').check()
        self.page.locator('#disconnect').click()
        self.page.wait_for_function("document.getElementById('status').textContent === 'Disconnected'")
        self.page.locator('#connect').click()
        self.page.wait_for_function("!document.getElementById('probe').disabled")
        self.auth()
        self.page.wait_for_function("!document.getElementById('identify').disabled")
        self.page.locator('#identify').click()
        self.page.wait_for_function("JSON.parse(localStorage.getItem('shimano-max-assist-us-v1')).stage === 'persistence-verified'",timeout=110000)
        b0_after=[x[2] for x in self.writes() if x[1]=='2afe' and x[2][2]==0xb0]
        self.assertEqual(b0_after,b0)
        self.assertIn('persisted on the same stock E5000',self.page.locator('#log').inner_text())
        self.assertIn('Verified after a physical power cycle',self.page.locator('#maxAssistWriteStatus').inner_text())
        self.assertFalse(self.errors)

    def test_extended_setup_follows_apk_order_before_destination(self):
        self.ready_for_identify()
        self.wait_batch()
        packets = [x[2] for x in self.writes() if x[1] == '2afa' and x[2][1] in (3, 4, 6, 12)]
        self.assertEqual(packets, [[0,3,0], [0,4], [0,6,0],
            [0,12,1], [0,3,75], [0,4], [0,6,31], [0,3,0], [0,4], [0,6,0]])
        self.assertEqual(self.page.locator('#region').inner_text(), 'EU')
        self.assertEqual(self.page.evaluate('session.pcApplicationSlot'), 0x0d)
        self.assertIn('PC-mode application slot observed via 2AFD: 0D', self.page.locator('#log').inner_text())
        self.assertFalse(any(x[2][1] == 136 for x in self.writes()))
        self.assertFalse(self.errors)

    def test_extended_setup_failure_stops_before_destination(self):
        self.ready_for_identify(initReject=12)
        self.wait_batch()
        self.assertIn('eTuning setup 0C: response byte 1 differs', self.page.locator('#log').inner_text())
        self.assertFalse(any(x[1] == '2afe' for x in self.writes()))
        self.assertFalse(self.errors)

    def test_destination_alternate_stops_without_decoding_or_second_read(self):
        for delayed in (False, True):
            self.ready_for_identify(regionAlternate=True, regionAlternateDelayed=delayed)
            self.page.wait_for_function("document.getElementById('log').textContent.includes('--- information batch end;')", timeout=12000)
            log = self.page.locator('#log').inner_text()
            self.assertIn('alternate response 00 16 AF 3A; meaning unresolved', log)
            self.assertIn('Current destination: not completed', log)
            self.assertNotIn('no matching reply', log)
            self.assertNotIn('Current destination: US', log)
            self.assertIn('unknown', self.page.locator('#regionStatus').inner_text())
            self.assertIn('DU-E7000', self.page.locator('#drive').inner_text())
            region_writes = [x for x in self.writes() if x[1] == '2afe' and x[2][1] == 22]
            self.assertEqual([x[2] for x in region_writes], [[0, 22, 172, 0]])
            self.assertFalse(self.errors)
            self.context.close()

    def test_destination_alternate_does_not_hide_att_write_failure(self):
        self.ready_for_identify(regionAlternate=True, regionAlternateWriteFailure=True)
        self.wait_batch()
        log = self.page.locator('#log').inner_text()
        self.assertIn('Information batch stopped: Destination write failed', log)
        self.assertNotIn('RESULT Destination slot 0: alternate', log)
        self.assertFalse(self.errors)

    def test_unknown_and_short_region_are_not_eu_or_ready(self):
        for options in ({'regionValue': 255}, {'regionShort': True}):
            self.ready_for_identify(**options)
            self.wait_batch()
            self.assertNotEqual(self.page.locator('#region').inner_text(), 'EU')
            self.assertIn('not verified', self.page.locator('#regionStatus').inner_text())
            self.context.close()

    def test_exact_original_pair_enables_display_owned_mode_us_attempt(self):
        self.ready_for_identify(motorModel=34, motorFirmware=69, motorPatch=0,
            nativeReplies={0:[0,1,134,69,0,0],1:[0,1,134,68,8,0]})
        self.wait_batch()
        self.page.evaluate('session.motorAuthenticated=true; controls();')
        self.assertTrue(self.page.evaluate('canSetUS(session)'))
        self.assertFalse(self.page.locator('#setUS').is_disabled())
        self.assertTrue(self.page.evaluate('session.commandWriteEligible'))
        self.assertIn('build-94 A0 path failed on the tested bike', self.page.locator('#regionStatus').inner_text())

    def test_reported_motor_firmware_describes_the_unverified_command_path(self):
        self.open()
        result = self.page.evaluate('regionReadiness([0,1,30,34,0], [0,1,46,69,0], [0,22,174,1,0])')
        self.assertIn('build-94 display-owned mode-5 transaction rejected unchanged A0', result)
        self.assertIn('read-only early-queue timing diagnostic', result)
        self.assertIn('never clears or repeats', result)
        already = self.page.evaluate('regionReadiness([0,1,30,34,0], [0,1,46,69,0], [0,22,174,1,1])')
        self.assertIn('US already reported', already)

    def test_guided_bike_check_never_enters_motor_pc_mode_or_sets_region(self):
        self.open(requireSetup=True,motorModel=34,motorFirmware=69,motorPatch=0,
            nativeReplies={0:[0,1,134,69,0,0],1:[0,1,134,68,8,0]})
        self.page.locator('#passkey').fill('123456')
        self.page.locator('#guidedUS').click()
        self.page.wait_for_function("document.getElementById('log').textContent.includes('guided bike-status check end')",timeout=65000)
        writes=self.writes()
        self.assertFalse(any(p[1]=='2afe' and p[2][1] in (0x16,0x32) and p[2][2] in (0xa0,0xa8,0xe8,0x10,0x30)
            for p in writes))
        self.assertIn('Current destination: EU',self.page.locator('#log').inner_text())
        self.assertIn('No motor unlock or setting write sent',self.page.locator('#log').inner_text())
        self.assertIn('Bike check complete: EU',self.page.locator('#guidedUSStatus').inner_text())
        self.assertFalse(self.errors)

    def test_guided_button_advances_to_only_the_next_safe_action(self):
        self.ready_for_identify(motorModel=34,motorFirmware=69,motorPatch=0,
            maxAssistSpeed=2500,usMaxAssistSpeed=3218,
            nativeReplies={0:[0,1,134,69,0,0],1:[0,1,134,68,8,0]})
        self.wait_batch()
        self.assertEqual(self.page.locator('#guidedUS').inner_text(),'Set US region once')
        self.assertIn('Bike check complete: EU',self.page.locator('#guidedUSStatus').inner_text())
        self.page.evaluate("""() => {
          window.guidedCalls=[];
          authenticateMotor=async()=>{guidedCalls.push('authenticate-motor');session.motorAuthenticated=true;controls();};
          setUS=async()=>{
            guidedCalls.push('set-us');
            probeRecord={kind:'command-us-region',verified:false,phase:'immediate-us',connection:session.probeToken};
            session.currentDestination=1;controls();
          };
        }""")
        self.page.on('dialog',lambda dialog: dialog.accept())
        self.page.locator('#guidedUS').click()
        self.page.wait_for_function('guidedCalls.length === 2')
        self.assertEqual(self.page.evaluate('guidedCalls'),['authenticate-motor','set-us'])
        self.assertEqual(self.page.locator('#guidedUS').inner_text(),'I power-cycled — verify US')
        self.page.evaluate("""() => {
          probeRecord={kind:'command-us-region',verified:true,outcome:'us'};
          session.currentDestination=1;session.currentMaxAssistSpeed=2500;
          session.usProfileMaxAssistSpeed=3218;controls();
        }""")
        self.assertEqual(self.page.locator('#guidedUS').inner_text(),'Set 32 km/h once')
        self.assertFalse(self.errors)

    def test_query_traffic_is_scoped_and_tracks_other_channels(self):
        self.ready_for_identify()
        self.wait_batch()
        log = self.page.locator('#log').inner_text()
        motor = next(line for line in log.splitlines() if 'QUERY TRAFFIC Drive-unit model / 2AFD:' in line)
        self.assertIn('2 notifications', motor)
        self.assertIn('00 16 1E 21', motor)
        self.assertIn('00 01 1E 21', motor)
        self.assertNotIn('00 16 80', motor)  # Startup burst cannot consume this query's samples.
        region = next(line for line in log.splitlines() if 'QUERY TRAFFIC Current destination / 2AFD:' in line)
        self.assertIn('00 16 AE 00', region)  # Wrong-slot reply is still visible diagnostically.
        self.assertIn('00 16 AE 01', region)
        self.assertIn('QUERY TRAFFIC Current destination / 2AF9: 0 notifications', log)
        self.assertFalse(self.errors)

    def test_destination_timeout_reports_alternate_channel_traffic(self):
        self.ready_for_identify(regionTimeout=True)
        self.page.wait_for_function("document.getElementById('log').textContent.includes('TX 2AFE Destination slot 0:')")
        self.page.evaluate("""() => {
          const ch = characteristics['2af9'];
          ch.value = new DataView(Uint8Array.from([127, 22, 172, 0]).buffer);
          ch.dispatchEvent(new Event('characteristicvaluechanged'));
        }""")
        self.wait_batch()
        log = self.page.locator('#log').inner_text()
        self.assertIn('QUERY TRAFFIC Destination slot 0 / 2AF9: 1 notifications; 7F 16 AC 00 / 4B', log)
        self.assertIn('QUERY TRAFFIC Current destination / 2AF9: 0 notifications', log)
        self.assertIn('Current destination: no matching reply', log)
        self.assertFalse(self.errors)

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
