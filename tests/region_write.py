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
          window.secureWordsByMode={1:0,4:0};window.currentPcMode=0;window.currentPcSlot=0;
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
          if(opts.omitPcApplicationSlot)delete session.pcApplicationSlot;
          else session.pcApplicationSlot=opts.pcApplicationSlot??0x0d;
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
              currentPcSlot=p[4];
              if(p[3]===1) {
                currentPcMode=1;
                if(opts.mode1RequestFailure)throw Error('Normal PC-link request ATT failure');
                if(opts.mode1PreKeyStatus)emit([0,0x32,0x12,1,currentPcSlot]);
                return;
              }
              if(p[3]===4) {
                currentPcMode=4;
                if(opts.modeRequestFailure||opts.mode4RequestFailure)throw Error('Authenticated PC mode request ATT failure');
                return;
              }
              if(p[3]===0) {
                if(opts.exitWriteFailure)throw Error('PC mode exit ATT failure');
                if(!opts.exitTimeout)emit([0,0x32,opts.exitReject?0x13:0x12,opts.exitReject?0x3a:0,currentPcSlot]);
                return;
              }
            }
            if(p[1]===0x32&&p[2]===0x30) {
              secureWords++;
              if(opts.secureWriteFailure===secureWords)throw Error('Secure word ATT failure');
              secureWordsByMode[currentPcMode]++;
              if(currentPcMode===1)emit([0,0x32,0x30,p[3],p[4]]);
              if(secureWordsByMode[currentPcMode]===5) {
                const reject=currentPcMode===1?opts.mode1Reject:opts.pcReject;
                const target=opts.completionRoute||'2afd';
                const targetRx=session.chars[target];
                if(opts.wrongModeFirst&&!reject){
                  targetRx.value=new DataView(Uint8Array.from([0,0x32,0x12,currentPcMode===1?4:1,currentPcSlot]).buffer);
                  targetRx.dispatchEvent(new Event('characteristicvaluechanged'));
                }
                if(opts.wrongSlotFirst&&!reject){
                  targetRx.value=new DataView(Uint8Array.from([0,0x32,0x12,currentPcMode,(currentPcSlot+1)&0x3e]).buffer);
                  targetRx.dispatchEvent(new Event('characteristicvaluechanged'));
                }
                targetRx.value=new DataView(Uint8Array.from([0,0x32,reject?0x13:0x12,reject?0x3a:currentPcMode,currentPcSlot]).buffer);
                targetRx.dispatchEvent(new Event('characteristicvaluechanged'));
              }
              return;
            }
            if(p[1]!==0x16)throw Error('Unexpected command category');
            if(p[2]===0xac) {
              regionReads++;
              if(opts.readbackWriteFailure&&regionReads===2)throw Error('Readback ATT failure');
              if(opts.shortBefore&&regionReads===1){emit([0,0x16,0xae,1]);return;}
              emit([0,0x16,0xae,0,1,0x10,0x20,0x30,0x40,0xff]);
              emit([0,0x16,0xae,1,regionReads===1?(opts.before??0):(opts.after??1),0x21,0x43,0x65,0x87,0xff]);
              return;
            }
            if(p[2]===0xa4) {
              if(opts.lightingReadWriteFailure)throw Error('Lighting read ATT failure');
              emit(opts.lightingReadReject?[0,0x16,0xa7,0x3a]:opts.shortLightingReply?
                [0,0x16,0xa6,0x34]:[0,0x16,0xa6,0x34,0x12,0x56,0x78,0x9a,0xff,0xff]);
              return;
            }
            if(p[2]===0xa0) {
              if(opts.stageWriteFailure&&(opts.stageFailureLength??7)===p.length){emit([0,0x16,0xa2]);throw Error('Staging ATT failure');}
              emit((opts.stageReject&&(opts.stageFailureLength??7)===p.length)?[0,0x16,0xa3,0x3a]:[0,0x16,0xa2]);
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

    def test_exact_mode4_sequence_stages_unchanged_lighting_and_sets_us_once(self):
        self.prepare(omitPcApplicationSlot=True);self.run_attempt()
        self.assertEqual(self.packets(),[
            [0,0x16,0xac,1],
            [0,0x32,0x10,1,0x0d,0,0],
            [0,0x32,0x30,0xa2,0x2b,0,0],
            [0,0x32,0x30,0x30,0x0e,0,0],
            [0,0x32,0x30,0x7a,0x4d,0,0],
            [0,0x32,0x30,0x62,0x2b,0,0],
            [0,0x32,0x30,0x85,0xb4,0,0],
            [0,0x32,0x10,4,0x0d,0,0],
            [0,0x32,0x30,0x19,0xb2,0,0],
            [0,0x32,0x30,0x73,0xd8,0,0],
            [0,0x32,0x30,0xa4,0x73,0,0],
            [0,0x32,0x30,0xb1,0x72,0,0],
            [0,0x32,0x30,0x01,0x10,0,0],
            [0,0x16,0xa4,0],
            [0,0x16,0xa0,0x34,0x12,0xff,0xff],
            [0,0x16,0xa8,1,1],
            [0,0x16,0xac,1],
            [0,0x32,0x10,0,0x0d,0,0],
        ])
        self.assertIn('MILESTONE: US (1) read back',self.page.locator('#log').inner_text())
        self.assertIn('using wireless slot 0D',self.page.locator('#log').inner_text())
        self.assertIn('unchanged lighting time accepted in authenticated mode 4',self.page.locator('#log').inner_text())
        self.assertEqual(sum(p[2]==0xa8 for p in self.packets()),1)

    def test_a0_failure_stops_before_destination_write(self):
        self.prepare(stageReject=True,stageFailureLength=7);self.run_attempt()
        packets=self.packets()
        self.assertFalse(any(p[2]==0xa8 for p in packets))
        self.assertEqual(sum(p[:4]==[0,0x32,0x10,0] for p in packets),1)
        self.assertEqual([len(p) for p in packets if p[2]==0xa0],[7])

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
            {'mode1RequestFailure':True}, {'mode1Reject':True},
            {'mode4RequestFailure':True}, {'secureWriteFailure':3}, {'pcReject':True},
            {'lightingReadWriteFailure':True}, {'lightingReadReject':True}, {'shortLightingReply':True},
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

    def test_mode_completion_can_arrive_on_any_subscribed_reply_route(self):
        for route in ('2af9','2afb','2afd'):
            with self.subTest(route=route):
                self.prepare(completionRoute=route);self.run_attempt()
                self.assertEqual(sum(p[2]==0xa8 for p in self.packets()),1)
                log=self.page.locator('#log').inner_text()
                self.assertIn(f'completion via {route.upper()}',log)
                self.context.close()

    def test_mode1_pre_key_status_does_not_unlock_the_transaction(self):
        self.prepare(mode1PreKeyStatus=True);self.run_attempt()
        packets=self.packets()
        self.assertEqual(sum(p[2]==0xa8 for p in packets),1)
        self.assertEqual(sum(p[:4]==[0,0x32,0x30,0xa2] for p in packets),1)
        self.assertIn('pre-key status',self.page.locator('#log').inner_text())

    def test_wrong_mode_completion_is_ignored_until_exact_mode_arrives(self):
        self.prepare(wrongModeFirst=True);self.run_attempt()
        self.assertEqual(sum(p[2]==0xa8 for p in self.packets()),1)
        self.assertIn('ignored mode',self.page.locator('#log').inner_text())

    def test_wrong_slot_completion_is_ignored_until_exact_slot_arrives(self):
        self.prepare(wrongSlotFirst=True);self.run_attempt()
        self.assertEqual(sum(p[2]==0xa8 for p in self.packets()),1)
        self.assertIn('ignored application slot',self.page.locator('#log').inner_text())

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
        self.assertFalse(self.page.locator('#guidedUS').is_disabled())  # Read-only status check remains available.

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
        self.assertFalse(self.page.locator('#guidedUS').is_disabled())  # No destination retry is reachable from the UI.


if __name__=='__main__':
    unittest.main()
