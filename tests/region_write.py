"""US destination write behavior with synthetic BLE replies; no hardware required."""
import unittest
from playwright.sync_api import sync_playwright
import browser

class RegionWriteTests(unittest.TestCase):
    open = browser.BrowserTests.open

    @classmethod
    def setUpClass(cls):
        cls.playwright = sync_playwright().start()
        cls.browser = cls.playwright.chromium.launch()

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.playwright.stop()

    def prepare(self, **options):
        self.open()
        self.assertTrue(self.page.locator('#setUS').is_disabled())
        self.page.evaluate('''async opts => {
          window.regionWrites = []; window.regionReads = 0;
          readFirmwareBaseline=async()=>({family:34,unit:0,identity:'a'.repeat(64),dVersion:opts.wrongBaseline?'4.5.0.0':'4.3.0.0',mVersion:'4.2.1.0',destination:0});
          if(opts.storageFailure){const original=Storage.prototype.setItem;Storage.prototype.setItem=function(k,v){if(k==='shimano-probe-readback-v1')throw Error('Storage blocked');return original.call(this,k,v);};}
          session.verified = session.motorEligible = session.motorAuthenticated = true;
          // Synthetic eligible path for testing the retained setter; the current original firmware remains ineligible.
          session.directWriteEligible = true;
          session.currentDestination = 0;
          for (const short of ['2afe','2afd','2af9','2afb'])
            session.chars[short] = await session.service.getCharacteristic(UUID(short));
          const rx = session.chars['2afd'];
          const emit = data => {
            rx.value = new DataView(Uint8Array.from(data).buffer);
            rx.dispatchEvent(new Event('characteristicvaluechanged'));
          };
          session.chars['2afe'].writeValueWithResponse = async packet => {
            const p = [...packet]; regionWrites.push(p);
            if (p[2] === 172) {
              regionReads++;
              if (opts.readFailure && regionReads === 2) throw Error('Readback ATT failure');
              if (opts.shortBefore && regionReads === 1) { emit([0,22,174,1]);return; }
              emit([0,22,174,0,1]); // Other slot must never satisfy current-value read.
              emit([0,22,174,1,regionReads === 1 ? (opts.before ?? 0) : (opts.after ?? 1)]);
              return;
            }
            if (p[2] !== 168) throw Error('Unexpected write');
            const record=JSON.parse(sessionStorage.getItem(PROBE_RECORD_KEY));
            if(record?.kind!=='us-region'||record.expected.destination!==1||record.verified)throw Error('Missing pending restart record before setter');
            if (opts.disconnect) { bike.gatt.disconnect();return; }
            const reply = () => {
              emit([0,22,32,79,0]); // Background telemetry is not a write result.
              if (opts.noAck || opts.stall) return;
              emit(opts.shortError ? [0,22,171] : opts.rejected ? [0,22,171,opts.rejected] : [0,22,170]);
            };
            if (opts.delayed) setTimeout(reply, 20); else reply();
            if (opts.writeFailure) throw Error('Setter ATT failure');
            if (opts.stall) return new Promise(()=>{});
          };
          controls();
        }''', options)

    def run_attempt(self):
        self.page.locator('#setUS').click()
        # Simulate an additional programmatic tap while busy.
        self.page.evaluate('setUS()')
        self.page.wait_for_function("document.getElementById('log').textContent.includes('--- US-region attempt end;')", timeout=25000)
        self.assertFalse(self.errors)
        self.assertTrue(self.page.locator('#setUS').is_disabled())

    def packets(self):
        return self.page.evaluate('regionWrites')

    def test_authentication_and_destination_gates(self):
        self.prepare()
        for field, value in [('directWriteEligible',False),('verified',False),('motorEligible',False),('motorAuthenticated',False),('currentDestination',1),('regionWriteAttempted',True)]:
            self.page.evaluate('''([field,value]) => { window.previous = session[field];session[field]=value;controls();setUS(); }''',[field,value])
            self.assertTrue(self.page.locator('#setUS').is_disabled())
            self.assertEqual(self.packets(),[])
            self.page.evaluate('field => {session[field]=previous;controls();}',field)

    def test_success_requires_fresh_read_setter_and_us_readback(self):
        for delayed in (False, True):
            self.prepare(delayed=delayed); self.run_attempt()
            self.assertEqual(self.packets(),[[0,22,172,1],[0,22,168,1,1],[0,22,172,1]])
            self.assertIn('MILESTONE: US (1) read back', self.page.locator('#log').inner_text())
            self.assertIn('Persistence and assistance speed remain unverified',self.page.locator('#log').inner_text())
            self.context.close()

    def test_baseline_or_storage_failure_never_writes(self):
        for opts in ({'wrongBaseline':True},{'storageFailure':True}):
            self.prepare(**opts);self.run_attempt()
            self.assertEqual(self.packets(),[[0,22,172,1]])
            self.assertNotIn('MILESTONE: US',self.page.locator('#log').inner_text())
            self.context.close()

    def test_restart_expectation_is_saved_before_write_and_survives_reload(self):
        self.prepare();self.run_attempt()
        record=self.page.evaluate("JSON.parse(sessionStorage.getItem('shimano-probe-readback-v1'))")
        self.assertEqual(record['kind'],'us-region')
        self.assertEqual(record['expected']['destination'],1)
        self.assertEqual(record['expected']['identity'],'a'*64)
        self.assertFalse(record['verified'])
        self.page.reload()
        self.assertEqual(self.page.evaluate('probeRecord.kind'),'us-region')
        self.assertFalse(self.page.evaluate('probeRecord.verified'))

    def test_changed_or_short_preflight_never_writes(self):
        for opts in ({'before':1},{'before':2},{'shortBefore':True}):
            self.prepare(**opts);self.run_attempt()
            self.assertEqual(self.packets(),[[0,22,172,1]])
            self.assertNotIn('MILESTONE: US',self.page.locator('#log').inner_text())
            self.context.close()

    def test_ack_without_changed_value_is_not_success(self):
        self.prepare(after=0);self.run_attempt()
        self.assertNotIn('MILESTONE: US',self.page.locator('#log').inner_text())
        self.assertIn('EU read back',self.page.locator('#regionStatus').inner_text())

    def test_failures_never_claim_success_or_retry(self):
        for opts in ({'rejected':58},{'rejected':59},{'rejected':70},{'shortError':True},{'writeFailure':True},{'readFailure':True},{'disconnect':True},{'stall':True}):
            with self.subTest(opts=opts):
                self.prepare(**opts);self.run_attempt()
                self.assertEqual(sum(p[2]==168 for p in self.packets()),1)
                self.assertNotIn('MILESTONE: US',self.page.locator('#log').inner_text())
                if not opts.get('readFailure'): self.assertEqual(len(self.packets()),2)
                self.context.close()

    def test_missing_ack_still_reads_value_without_retry(self):
        self.prepare(noAck=True);self.run_attempt()
        self.assertEqual(len(self.packets()),3)
        self.assertIn('No destination acknowledgement',self.page.locator('#log').inner_text())
        self.assertIn('MILESTONE: US (1) read back',self.page.locator('#log').inner_text())

if __name__ == '__main__': unittest.main()
