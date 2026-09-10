"""Guarded D4.5 command-only destination transaction; no hardware required."""
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
          window.commandDelay=async()=>{};
          window.regionWrites=[];window.regionReads=0;window.secureWords=0;
          if(opts.storageFailure){
            const original=Storage.prototype.setItem;
            Storage.prototype.setItem=function(k,v){
              if(k===PROBE_RECORD_KEY)throw Error('Storage blocked');
              return original.call(this,k,v);
            };
          }
          session.verified=session.motorEligible=session.motorAuthenticated=true;
          session.directWriteEligible=session.commandWriteEligible=true;
          session.currentDestination=0;
          for(const short of ['2afe','2afd','2af9','2afb'])
            session.chars[short]=await session.service.getCharacteristic(UUID(short));
          const rx=session.chars['2afd'];
          const emit=data=>{
            rx.value=new DataView(Uint8Array.from(data).buffer);
            rx.dispatchEvent(new Event('characteristicvaluechanged'));
          };
          session.chars['2afe'].writeValueWithResponse=async packet=>{
            const p=[...packet];regionWrites.push(p);
            if(p[1]===0x32&&p[2]===0x10) {
              if(p[3]===5) {
                if(opts.modeRequestFailure)throw Error('PC mode request ATT failure');
                return;
              }
              if(p[3]===0) {
                if(opts.exitWriteFailure)throw Error('PC mode exit ATT failure');
                if(!opts.exitTimeout)emit([0,0x32,opts.exitReject?0x13:0x12,opts.exitReject?0x3a:0]);
                return;
              }
            }
            if(p[1]===0x32&&p[2]===0x30) {
              secureWords++;
              if(opts.secureWriteFailure===secureWords)throw Error('Secure word ATT failure');
              if(secureWords===5)emit([0,0x32,opts.pcReject?0x13:0x12,opts.pcReject?0x3a:0]);
              return;
            }
            if(p[1]!==0x16)throw Error('Unexpected command category');
            if(p[2]===0xac) {
              regionReads++;
              if(opts.readbackWriteFailure&&regionReads===2)throw Error('Readback ATT failure');
              if(opts.shortBefore&&regionReads===1){emit([0,0x16,0xae,1]);return;}
              emit([0,0x16,0xae,0,1]);
              emit([0,0x16,0xae,1,regionReads===1?(opts.before??0):(opts.after??1)]);
              return;
            }
            if(p[2]===0xa4) {
              if(opts.lightingReadWriteFailure)throw Error('Lighting read ATT failure');
              emit(opts.lightingReadReject?[0,0x16,0xa7,0x3a]:[0,0x16,0xa6,0x34,0x12]);
              return;
            }
            if(p[2]===0xa0) {
              if(opts.stageWriteFailure){emit([0,0x16,0xa2]);throw Error('Staging ATT failure');}
              emit(opts.stageReject?[0,0x16,0xa3,0x3a]:[0,0x16,0xa2]);
              return;
            }
            if(p[2]===0xa8) {
              const record=JSON.parse(sessionStorage.getItem(PROBE_RECORD_KEY));
              if(record?.version!==2||record.kind!=='command-us-region'||
                  record.expected?.destination!==1||record.verified)
                throw Error('Missing pending restart record before setter');
              if(opts.destinationWriteFailure){emit([0,0x16,0xaa]);throw Error('Destination ATT failure');}
              emit([0,0x16,0x20,0x4f,0]);
              emit(opts.destinationReject?[0,0x16,0xab,opts.destinationReject]:[0,0x16,0xaa]);
              return;
            }
            throw Error(`Unexpected opcode ${p[2]}`);
          };
          controls();
        }''', options)

    def run_attempt(self):
        self.page.evaluate('setUS();setUS()')
        self.page.wait_for_function(
            "document.getElementById('log').textContent.includes('--- US-region attempt end;')",
            timeout=12000)
        self.assertFalse(self.errors)
        self.assertTrue(self.page.locator('#setUS').is_disabled())

    def packets(self):
        return self.page.evaluate('regionWrites')

    def test_all_state_gates(self):
        self.prepare()
        for field, value in [('directWriteEligible',False),('verified',False),
                             ('motorEligible',False),('motorAuthenticated',False),
                             ('currentDestination',1),('regionWriteAttempted',True)]:
            self.page.evaluate('''([field,value])=>{
              window.previous=session[field];session[field]=value;controls();setUS();
            }''',[field,value])
            self.assertEqual(self.packets(),[])
            self.page.evaluate('field=>{session[field]=previous;controls();}',field)
        self.page.evaluate("probeRecord={version:1,verified:false};setUS()")
        self.assertEqual(self.packets(),[])

    def test_exact_protected_sequence_preserves_lighting_and_sets_us_once(self):
        self.prepare();self.run_attempt()
        self.assertEqual(self.packets(),[
            [0,0x16,0xac,1],
            [0,0x32,0x10,5,0,0,0],
            [0,0x32,0x30,0x27,0x0f,0,0],
            [0,0x32,0x30,0x11,0x55,0,0],
            [0,0x32,0x30,0x35,0xb0,0,0],
            [0,0x32,0x30,0x03,0xf3,0,0],
            [0,0x32,0x30,0x09,0x03,0,0],
            [0,0x16,0xa4,0],
            [0,0x16,0xa0,0x34,0x12,0,0],
            [0,0x16,0xa8,1,1,0,0],
            [0,0x16,0xac,1],
            [0,0x32,0x10,0,0,0,0],
        ])
        self.assertIn('MILESTONE: US (1) read back',self.page.locator('#log').inner_text())
        self.assertEqual(sum(p[2]==0xa8 for p in self.packets()),1)

    def test_restart_record_is_durable_before_the_only_destination_write(self):
        self.prepare();self.run_attempt()
        record=self.page.evaluate("JSON.parse(sessionStorage.getItem(PROBE_RECORD_KEY))")
        self.assertEqual(record['version'],2)
        self.assertEqual(record['kind'],'command-us-region')
        self.assertEqual(record['expected'],{'family':34,'unit':0,'dVersion':'4.5.0.0',
                                             'mVersion':'4.4.8.0','destination':1})
        self.assertRegex(record['deviceBinding'],r'^[a-f0-9]{64}$')
        self.assertFalse(record['verified'])
        self.page.reload()
        self.assertEqual(self.page.evaluate('probeRecord.kind'),'command-us-region')
        self.assertFalse(self.page.evaluate('probeRecord.verified'))

    def test_changed_or_short_fresh_region_stops_before_pc_mode(self):
        for options in ({'before':1},{'before':2},{'shortBefore':True}):
            with self.subTest(options=options):
                self.prepare(**options);self.run_attempt()
                self.assertEqual(self.packets(),[[0,0x16,0xac,1]])
                self.context.close()

    def test_each_prerequisite_failure_prevents_destination_write_and_exits_mode(self):
        failures=(
            {'modeRequestFailure':True}, {'secureWriteFailure':3}, {'pcReject':True},
            {'lightingReadWriteFailure':True}, {'lightingReadReject':True},
            {'stageWriteFailure':True}, {'stageReject':True}, {'storageFailure':True},
        )
        for options in failures:
            with self.subTest(options=options):
                self.prepare(**options);self.run_attempt()
                packets=self.packets()
                self.assertFalse(any(p[2]==0xa8 for p in packets))
                self.assertEqual(sum(p[:4]==[0,0x32,0x10,0] for p in packets),1)
                self.assertNotIn('MILESTONE: US',self.page.locator('#log').inner_text())
                self.context.close()

    def test_destination_and_readback_failures_never_retry_and_always_exit(self):
        failures=({'destinationReject':0x3a},{'destinationWriteFailure':True},
                  {'readbackWriteFailure':True},{'after':0},{'exitReject':True},
                  {'exitWriteFailure':True})
        for options in failures:
            with self.subTest(options=options):
                self.prepare(**options);self.run_attempt()
                packets=self.packets()
                self.assertEqual(sum(p[2]==0xa8 for p in packets),1)
                self.assertEqual(sum(p[:4]==[0,0x32,0x10,0] for p in packets),1)
                if options.get('after')==0:
                    self.assertNotIn('MILESTONE: US',self.page.locator('#log').inner_text())
                self.context.close()

    def test_persistence_check_is_same_device_same_pair_and_terminal(self):
        self.prepare();self.run_attempt()
        self.page.evaluate("session.probeToken='different-connection'")
        self.page.evaluate('''async () => {
          const results=[
            ['Drive-unit model',[0,1,0x1e,0x22,0]],
            ['Drive-unit firmware',[0,1,0x2e,0x45,0]],
            ['Native D firmware',[0,1,0x86,0x45,0,0]],
            ['Native M firmware',[0,1,0x86,0x44,8,0]],
            ['Current destination',[0,0x16,0xae,1,1]],
          ].map(([name,fields])=>({name,status:'reply received',fields:Uint8Array.from(fields)}));
          await verifyPendingBootloaderProbe(session,results);controls();
        }''')
        record=self.page.evaluate('probeRecord')
        self.assertTrue(record['verified'])
        self.assertEqual(record['outcome'],'us')
        self.assertIn('US destination persisted',self.page.locator('#log').inner_text())
        self.assertTrue(self.page.locator('#guidedUS').is_disabled())

    def test_non_us_persistence_result_is_terminal_and_never_retries(self):
        self.prepare(after=0);self.run_attempt()
        destination_writes=sum(p[2]==0xa8 for p in self.packets())
        self.page.evaluate("session.probeToken='different-connection'")
        self.page.evaluate('''async () => {
          const results=[
            ['Drive-unit model',[0,1,0x1e,0x22,0]],
            ['Drive-unit firmware',[0,1,0x2e,0x45,0]],
            ['Native D firmware',[0,1,0x86,0x45,0,0]],
            ['Native M firmware',[0,1,0x86,0x44,8,0]],
            ['Current destination',[0,0x16,0xae,1,0]],
          ].map(([name,fields])=>({name,status:'reply received',fields:Uint8Array.from(fields)}));
          await verifyPendingBootloaderProbe(session,results);controls();setUS();
        }''')
        record=self.page.evaluate('probeRecord')
        self.assertTrue(record['verified'])
        self.assertEqual(record['outcome'],'not-us')
        self.assertEqual(sum(p[2]==0xa8 for p in self.packets()),destination_writes)
        self.assertIn('US did not persist. No retry sent',self.page.locator('#log').inner_text())
        self.assertTrue(self.page.locator('#guidedUS').is_disabled())


if __name__=='__main__':
    unittest.main()
