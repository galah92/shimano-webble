"""Motor exchange tests with synthetic serials/challenges; no bike identifiers."""
import json
from pathlib import Path
import unittest
from playwright.sync_api import sync_playwright
import browser

VECTORS=json.loads(Path(__file__).with_name('motor_vectors.json').read_text())
class MotorTests(unittest.TestCase):
    open=browser.BrowserTests.open
    writes=browser.BrowserTests.writes
    auth=browser.BrowserTests.auth
    ready_for_identify=browser.BrowserTests.ready_for_identify
    wait_batch=browser.BrowserTests.wait_batch

    @classmethod
    def setUpClass(cls):
        cls.playwright=sync_playwright().start()
        cls.browser=cls.playwright.chromium.launch()

    @classmethod
    def tearDownClass(cls):
        cls.browser.close();cls.playwright.stop()

    def prepare(self, **opts):
        self.open()
        self.assertTrue(self.page.locator('#motorAuth').is_disabled())
        self.page.evaluate('''async ({serial, opts}) => {
          window.motorOptions=opts; window.testSerial=serial;
          session.verified=true; session.motorEligible=true;
          for (const short of ['2afe','2afd']) session.chars[short]=await session.service.getCharacteristic(UUID(short));
          const tx=session.chars['2afe'], rx=session.chars['2afd'];
          window.motorWrites=[];
          const send=a => {rx.value=new DataView(Uint8Array.from(a).buffer);rx.dispatchEvent(new Event('characteristicvaluechanged'));};
          tx.writeValueWithResponse=async packet => {
            const p=[...packet]; motorWrites.push(p);
            const emit=() => {
              if(p[1]===1) {send(opts.shortSerial ? [0,1,62] : [0,1,62,...serial,255]);return;}
              if(p[2]===216) {
                if(opts.disconnect) {bike.gatt.disconnect();return;}
                if(opts.db) {send([0,22,219,58,0]);return;}
                send([0,22,32,79,0,0,0,0,0,0]); // unrelated telemetry
                send([0,22,218,38,6,7,8,9,10,11]); // deliberately out of order
                send([0,22,218,22,0,1,2,3,4,5]);
                if(opts.conflict) {send([0,22,218,22,1,1,2,3,4,5]);return;}
                if(opts.partial) return;
                send([0,22,218,52,12,13,14,15,opts.badPadding?0:255,255]);return;
              }
              if(p[2]===224 && (p[3]===52 || opts.early)) {
                if(opts.noCompletion)return;
                send([0,22,opts.reject?227:226,255,255,0,0,0,0,0]);
              }
            };
            if(opts.delayed) setTimeout(emit,15); else emit();
            if(opts.writeFailure && p[2]===224 && p[3]===52) throw Error('Synthetic ATT failure');
            if(opts.stall && p[2]===216) return new Promise(()=>{});
          };
          controls();
        }''',dict(serial=VECTORS[0]['serial'],opts=opts))
        # The base mock's BLE challenge also uses 00..0F; isolate the motor log.
        self.page.locator('#clearLog').click()
        self.page.locator('#motorAuth').click()

    def wait_motor(self):
        self.page.wait_for_function("document.getElementById('log').textContent.includes('--- motor authentication end;')",timeout=12000)
        self.assertFalse(self.errors)

    def test_information_batch_controls_eligibility(self):
        for model,firmware,patch,expected in [(34,69,0,True),(33,71,1,False)]:
            self.ready_for_identify(motorModel=model,motorFirmware=firmware,motorPatch=patch)
            self.wait_batch()
            self.assertEqual(self.page.locator('#motorAuth').is_enabled(),expected)
            self.context.close()

    def test_synthetic_reference_vectors(self):
        self.open()
        for v in VECTORS:
            result=self.page.evaluate('''async s => {
              const m=motorMaterial(Uint8Array.from(s));
              return {request:[...m.request],key:[...m.key],ciphertext:[...await encryptBlock(m.key,Uint8Array.from({length:16},(_,i)=>i))]};
            }''',v['serial'])
            self.assertEqual(result,{k:v[k] for k in ('request','key','ciphertext')})

    def test_exchange_both_response_orders_and_private_logging(self):
        for delayed in (False,True):
            self.prepare(delayed=delayed);self.wait_motor()
            packets=self.page.evaluate('motorWrites'); v=VECTORS[0];ct=v['ciphertext']
            self.assertEqual(packets,[[0,1,60,0],[0,22,216]+v['request'],
                [0,22,224,22]+ct[:6],[0,22,224,38]+ct[6:12],[0,22,224,52]+ct[12:]+[255,255]])
            self.assertIn('completion observed',self.page.locator('#motorStatus').inner_text())
            saved=self.page.evaluate('exportLog()+JSON.stringify(sessionStorage)')
            for secret in (v['serial'],v['request'],v['key'],ct,list(range(16))):
                self.assertNotIn(' '.join(f'{b:02X}' for b in secret),saved)
            self.assertTrue(self.page.locator('#motorAuth').is_disabled())
            self.context.close()

    def test_bad_challenge_never_sends_response(self):
        for flag in ('db','shortSerial','conflict','badPadding','disconnect','partial','stall'):
            with self.subTest(flag=flag):
                self.prepare(**{flag:True});self.wait_motor()
                self.assertFalse(any(p[2]==224 for p in self.page.evaluate('motorWrites')))
                self.assertNotIn('MILESTONE: motor authentication',self.page.locator('#log').inner_text())
                self.context.close()

    def test_write_failure_wins_over_early_arriving_ack(self):
        self.prepare(writeFailure=True);self.wait_motor()
        self.assertNotIn('MILESTONE: motor authentication',self.page.locator('#log').inner_text())
        self.assertIn('Synthetic ATT failure',self.page.locator('#log').inner_text())

    def test_completion_rejection_timeout_and_early_marker(self):
        for flag in ('reject','noCompletion','early'):
            with self.subTest(flag=flag):
                self.prepare(**{flag:True});self.wait_motor()
                self.assertNotIn('MILESTONE: motor authentication',self.page.locator('#log').inner_text())
                self.assertIn('not verified',self.page.locator('#motorStatus').inner_text())
                if flag=='early':self.assertEqual(len(self.page.evaluate('motorWrites')),3)
                self.context.close()

if __name__=='__main__':unittest.main()
