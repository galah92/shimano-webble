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
          window.regionWrites=[];window.regionReads=0;
          window.currentPcMode=1;window.currentPcSlot=0;
          window.regionChanged=false;window.destinationGate=false;window.mode5Requests=0;
          window.probeJournalWrites=0;
          if(opts.storageFailure||opts.storageFailureAt){
            const original=Storage.prototype.setItem;
            Storage.prototype.setItem=function(k,v){
              if(k===PROBE_RECORD_KEY) {
                probeJournalWrites++;
                if(opts.storageFailure||opts.storageFailureAt===probeJournalWrites)
                  throw Error('Storage blocked');
              }
              return original.call(this,k,v);
            };
          }
          session.verified=session.motorEligible=session.motorAuthenticated=true;
          session.directWriteEligible=session.commandWriteEligible=true;
          session.currentDestination=0;
          if(opts.omitPcApplicationSlot)delete session.pcApplicationSlot;
          else session.pcApplicationSlot=opts.pcApplicationSlot??0x0d;
          for(const short of ['2afa','2afe','2afd','2af9','2afb'])
            session.chars[short]=await session.service.getCharacteristic(UUID(short));
          const emitTo=(short,data)=>{
            const rx=session.chars[short];
            rx.value=new DataView(Uint8Array.from(data).buffer);
            rx.dispatchEvent(new Event('characteristicvaluechanged'));
          };
          const emit=data=>emitTo('2afd',data);
          session.chars['2afa'].writeValueWithResponse=async packet=>{
            const p=[...packet];regionWrites.push(p);
            if(p[1]!==0x0c)throw Error('Unexpected display command');
            const mode=p[2],slot=session.pcApplicationSlot??0x0d;
            if(mode===5)mode5Requests++;
            if(mode===5&&opts.mode5RequestFailure)throw Error('Display mode-5 ATT failure');
            if(mode===5&&mode5Requests===2&&opts.secondMode5RequestFailure)
              throw Error('Refreshed display mode-5 ATT failure');
            if(mode===0&&opts.exitWriteFailure)throw Error('Display mode-exit ATT failure');
            const secondMode5=mode===5&&mode5Requests===2;
            const displayReject=mode===5
              ? (opts.displayModeReject||(secondMode5&&opts.secondDisplayModeReject))
              : opts.exitDisplayReject;
            if(!opts.displayAckTimeout)emitTo('2af9',[0x2c,displayReject?1:0]);
            if(displayReject||opts.displayAckTimeout)return;
            const motorReject=mode===5
              ? (opts.pcReject||(secondMode5&&opts.secondPcReject))
              : opts.exitReject;
            if(opts.modeCompletionTimeout)return;
            const target=opts.completionRoute||'2afd';
            if(opts.wrongModeFirst&&!motorReject)
              emitTo(target,[0,0x32,0x12,mode===5?1:5,slot]);
            if(opts.wrongSlotFirst&&!motorReject)
              emitTo(target,[0,0x32,0x12,mode,(slot+1)&0x3e]);
            if(motorReject)emitTo(target,[0,0x32,0x13,0x3a,slot]);
            else {currentPcMode=mode;currentPcSlot=slot;emitTo(target,[0,0x32,0x12,mode,slot]);}
          };
          session.chars['2afe'].writeValueWithResponse=async packet=>{
            const p=[...packet];regionWrites.push(p);
            if(p[1]!==0x16)throw Error('Unexpected command category');
            if(p[2]===0xa4) {
              emit([0,0x16,0xa6,0x0a,0x00,0xff,0xff,0xa4,1,0xff]);
              return;
            }
            if(p[2]===0xac) {
              regionReads++;
              if(opts.readbackWriteFailure&&regionReads===2)throw Error('Readback ATT failure');
              if(opts.shortBefore&&regionReads===1){emit([0,0x16,0xae,1]);return;}
              const afterValue=opts.after!==undefined?opts.after:(window.regionChanged?1:0);
              emit([0,0x16,0xae,0,1,0x10,0x20,0x30,0x40,0xff]);
              emit([0,0x16,0xae,1,regionReads===1?(opts.before??0):afterValue,0x21,0x43,0x65,0x87,0xff]);
              return;
            }
            if(p[2]===0xa0) {
              const record=JSON.parse(localStorage.getItem(PROBE_RECORD_KEY));
              if(record?.phase!=='a0-started')throw Error('A0 phase was not durably recorded before enqueue');
              if(opts.stageWriteFailure)throw Error('A0 ATT failure');
            if(currentPcMode===5&&!opts.stageReject&&!opts.pcReject){
                window.destinationGate=true;emit([0,0x16,0xa2]);
              } else emit([0,0x16,0xa3,opts.stageReject||0x3a]);
              return;
            }
            if(p[2]===0xa8) {
              const record=JSON.parse(localStorage.getItem(PROBE_RECORD_KEY));
              if(record?.version!==2||record.kind!=='command-us-region'||
                  record.expected?.destination!==1||record.verified||record.phase!=='a8-started')
                throw Error('Missing pending restart record before setter');
              if(opts.destinationWriteFailure){emit([0,0x16,0xaa]);throw Error('Destination ATT failure');}
              if(window.destinationGate&&!opts.destinationReject&&!opts.pcReject){
                window.destinationGate=false;window.regionChanged=true;
                emit([0,0x16,0x20,0x4f,0]);emit([0,0x16,0xaa]);
              }
              else emit([0,0x16,0xab,opts.destinationReject||0x3a]);
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
        self.page.evaluate("probeRecord={version:2,kind:'command-us-region',verified:true,outcome:'not-us'};setUS()")
        self.assertEqual(self.packets(),[])

    def test_display_owned_mode5_sequence_waits_for_completion_then_sets_us_once(self):
        self.prepare(omitPcApplicationSlot=True);self.run_attempt()
        self.assertEqual(self.packets(),[
            [0,0x16,0xac,1],
            [0,0x16,0xa4,0],
            [0,0x0c,5],
            [0,0x16,0xa0,0x0a,0x00,0xff,0xff],
            [0,0x0c,5],
            [0,0x16,0xa8,1,1],
            [0,0x16,0xac,1],
            [0,0x0c,0],
        ])
        self.assertIn('MILESTONE: US (1) read back',self.page.locator('#log').inner_text())
        self.assertIn('using wireless slot 0D',self.page.locator('#log').inner_text())
        log=self.page.locator('#log').inner_text()
        self.assertIn('SC-E7000-owned PC mode 5 before A0 display acknowledgement',log)
        self.assertIn('SC-E7000-owned PC mode 5 before A0 motor completion',log)
        self.assertIn('SC-E7000-owned PC mode 5 refreshed before A8 display acknowledgement',log)
        self.assertIn('SC-E7000-owned PC mode 5 refreshed before A8 motor completion',log)
        self.assertIn('unchanged-lighting A0 in display-owned mode 5',log)
        self.assertIn('A8 US after refreshed display-owned mode 5',log)
        self.assertRegex(log,r'Display-owned mode-5 completion to A0 enqueue: \d+\.\d ms')
        self.assertRegex(log,r'Display-owned mode-5 completion to A0 acceptance: \d+\.\d ms')
        self.assertRegex(log,r'Refreshed display-owned mode-5 completion to A8 enqueue: \d+\.\d ms')
        self.assertLess(log.index('SC-E7000-owned PC mode 5 before A0 motor completion'),log.index('unchanged-lighting A0 in display-owned mode 5'))
        self.assertLess(log.index('unchanged-lighting A0 in display-owned mode 5'),log.index('SC-E7000-owned PC mode 5 refreshed before A8 motor completion'))
        self.assertLess(log.index('SC-E7000-owned PC mode 5 refreshed before A8 motor completion'),log.index('A8 US after refreshed display-owned mode 5'))
        self.assertEqual(sum(p[2]==0xa8 for p in self.packets()),1)
        self.assertEqual(sum(p[2]==0xa0 for p in self.packets()),1)
        self.assertEqual(sum(p==[0,0x0c,5] for p in self.packets()),2)
        self.assertFalse(any(len(p)>2 and p[1]==0x32 for p in self.packets()))

    def test_a8_rejection_changes_nothing_and_never_retries(self):
        self.prepare(destinationReject=0x3a);self.run_attempt()
        packets=self.packets()
        self.assertEqual(sum(p[2]==0xa8 for p in packets),1)
        log=self.page.locator('#log').inner_text()
        self.assertIn('A8 US after refreshed display-owned mode 5 rejected 3A',log)
        self.assertIn('No retry was sent',log)
        self.assertNotIn('MILESTONE: US',log)
        self.assertFalse(self.page.evaluate('window.regionChanged'))
        self.assertEqual(sum(p==[0,0x0c,0] for p in packets),1)

    def test_a0_rejection_still_bounds_a8_and_changes_nothing(self):
        self.prepare(stageReject=0x3a);self.run_attempt()
        packets=self.packets()
        self.assertEqual(sum(p[2]==0xa0 for p in packets),1)
        self.assertEqual(sum(p[2]==0xa8 for p in packets),0)
        log=self.page.locator('#log').inner_text()
        self.assertIn('unchanged-lighting A0 in display-owned mode 5 rejected 3A',log)
        self.assertNotIn('MILESTONE: US',log)
        self.assertFalse(self.page.evaluate('window.regionChanged'))

    def test_mode5_rejection_prevents_a0_a8_and_cannot_trigger_a_retry(self):
        self.prepare(pcReject=True);self.run_attempt()
        packets=self.packets()
        self.assertEqual(sum(p[2]==0xa0 for p in packets),0)
        self.assertEqual(sum(p[2]==0xa8 for p in packets),0)
        self.assertEqual(sum(p==[0,0x0c,5] for p in packets),1)
        self.assertFalse(self.page.evaluate('window.regionChanged'))
        self.assertIn('SC-E7000-owned PC mode 5 before A0 motor handshake rejected 3A',self.page.locator('#log').inner_text())

    def test_refreshed_mode5_is_required_after_a2_and_never_retries_a0_or_a8(self):
        failures=({'secondMode5RequestFailure':True},
                  {'secondDisplayModeReject':True},
                  {'secondPcReject':True})
        for options in failures:
            with self.subTest(options=options):
                self.prepare(**options);self.run_attempt()
                packets=self.packets()
                self.assertEqual(sum(p[2]==0xa0 for p in packets),1)
                self.assertEqual(sum(p[2]==0xa8 for p in packets),0)
                self.assertEqual(sum(p==[0,0x0c,5] for p in packets),2)
                self.assertEqual(sum(p==[0,0x0c,0] for p in packets),1)
                self.assertTrue(self.page.evaluate('window.destinationGate'))
                log=self.page.locator('#log').inner_text()
                self.assertIn('A0 was accepted but A8 was not sent',log)
                self.assertIn('physical bike power cycle',log)
                record=self.page.evaluate("JSON.parse(localStorage.getItem(PROBE_RECORD_KEY))")
                self.assertEqual(record['phase'],'a0-accepted')
                self.page.reload()
                self.assertEqual(self.page.evaluate('probeRecord.phase'),'a0-accepted')
                self.assertFalse(self.page.evaluate('''() => {
                  session={verified:true,directWriteEligible:true,motorEligible:true,
                    motorAuthenticated:true,currentDestination:0,regionWriteAttempted:false};
                  return canSetUS(session);
                }'''))
                self.context.close()

    def test_restart_record_is_durable_before_the_only_destination_write(self):
        self.prepare();self.run_attempt()
        record=self.page.evaluate("JSON.parse(localStorage.getItem(PROBE_RECORD_KEY))")
        self.assertEqual(record['version'],2)
        self.assertEqual(record['kind'],'command-us-region')
        self.assertEqual(record['phase'],'immediate-us')
        self.assertEqual(record['expected'],{'family':34,'unit':0,'dVersion':'4.5.0.0',
                                             'mVersion':'4.4.8.0','destination':1})
        self.assertRegex(record['deviceBinding'],r'^[a-f0-9]{64}$')
        self.assertFalse(record['verified'])
        self.page.reload()
        self.assertEqual(self.page.evaluate('probeRecord.kind'),'command-us-region')
        self.assertFalse(self.page.evaluate('probeRecord.verified'))
        self.assertEqual(self.page.evaluate('probeRecord.phase'),'immediate-us')
        self.assertFalse(self.page.evaluate('''() => {
          session={verified:true,directWriteEligible:true,motorEligible:true,
            motorAuthenticated:true,currentDestination:0,regionWriteAttempted:false};
          return canSetUS(session);
        }'''))

    def test_durable_attempt_loader_fails_closed_and_migrates_session_record(self):
        self.open()
        self.page.evaluate("localStorage.setItem(PROBE_RECORD_KEY,'{')")
        self.page.reload()
        self.assertTrue(self.page.evaluate('probeRecord.invalid'))
        self.assertFalse(self.page.evaluate('''() => canSetUS({verified:true,
          directWriteEligible:true,motorEligible:true,motorAuthenticated:true,
          currentDestination:0,regionWriteAttempted:false})'''))
        self.context.close()

        self.open()
        self.page.evaluate('''() => sessionStorage.setItem(PROBE_RECORD_KEY,JSON.stringify({
          version:2,kind:'command-us-region',connection:'old-session',
          salt:'00000000000000000000000000000000',
          deviceBinding:'1111111111111111111111111111111111111111111111111111111111111111',
          expected:{family:34,unit:0,dVersion:'4.5.0.0',mVersion:'4.4.8.0',destination:1},
          verified:false
        }))''')
        self.page.reload()
        self.assertEqual(self.page.evaluate('probeRecord.phase'),'legacy-attempt')
        self.assertEqual(self.page.evaluate(
          "JSON.parse(localStorage.getItem(PROBE_RECORD_KEY)).phase"),'legacy-attempt')
        self.assertFalse(self.page.evaluate('''() => canSetUS({verified:true,
          directWriteEligible:true,motorEligible:true,motorAuthenticated:true,
          currentDestination:0,regionWriteAttempted:false})'''))

    def test_changed_or_short_fresh_region_stops_before_pc_mode(self):
        for options in ({'before':1},{'before':2},{'shortBefore':True}):
            with self.subTest(options=options):
                self.prepare(**options);self.run_attempt()
                self.assertEqual(self.packets(),[[0,0x16,0xac,1]])
                self.context.close()

    def test_each_prerequisite_failure_prevents_destination_write(self):
        # Durable restart state is saved before PC-mode entry, so a storage
        # failure sends no privileged or destination command.
        pre_mode=({'storageFailure':True},)
        for options in pre_mode:
            with self.subTest(options=options,phase='pre-mode'):
                self.prepare(**options);self.run_attempt()
                packets=self.packets()
                self.assertFalse(any(p[2] in (0xa0,0xa8) for p in packets))
                self.assertFalse(any(p[1]==0x32 for p in packets))
                self.assertNotIn('MILESTONE: US',self.page.locator('#log').inner_text())
                self.context.close()

    def test_required_phase_journal_failure_prevents_corresponding_setting(self):
        for failure_at,expected_a0 in ((2,0),(4,1)):
            with self.subTest(failure_at=failure_at):
                self.prepare(storageFailureAt=failure_at);self.run_attempt()
                packets=self.packets()
                self.assertEqual(sum(p[2]==0xa0 for p in packets),expected_a0)
                self.assertEqual(sum(p[2]==0xa8 for p in packets),0)
                log=self.page.locator('#log').inner_text()
                self.assertIn('Could not durably record the command-only attempt',log)
                if expected_a0:
                    self.assertIn('A0 was accepted but A8 was not sent',log)
                    record=self.page.evaluate("JSON.parse(localStorage.getItem(PROBE_RECORD_KEY))")
                    self.assertEqual(record['phase'],'a0-accepted')
                self.context.close()
        # Display-mode entry failures always request a display-owned exit once
        # and never reach either drive-setting write.
        in_mode=(
            {'mode5RequestFailure':True}, {'displayModeReject':True},
            {'pcReject':True},
        )
        for options in in_mode:
            with self.subTest(options=options,phase='in-mode'):
                self.prepare(**options);self.run_attempt()
                packets=self.packets()
                self.assertFalse(any(p[2] in (0xa0,0xa8) for p in packets))
                self.assertEqual(sum(p==[0,0x0c,0] for p in packets),1)
                self.assertFalse(any(len(p)>2 and p[1]==0x32 for p in packets))
                self.assertNotIn('MILESTONE: US',self.page.locator('#log').inner_text())
                self.context.close()

    def test_mode_completion_can_arrive_on_any_subscribed_reply_route(self):
        for route in ('2af9','2afb','2afd'):
            with self.subTest(route=route):
                self.prepare(completionRoute=route);self.run_attempt()
                self.assertEqual(sum(p[2]==0xa0 for p in self.packets()),1)
                self.assertEqual(sum(p[2]==0xa8 for p in self.packets()),1)
                log=self.page.locator('#log').inner_text()
                self.assertIn(f'completion via {route.upper()}',log)
                self.context.close()

    def test_wrong_mode_completion_is_ignored_until_exact_mode_arrives(self):
        self.prepare(wrongModeFirst=True);self.run_attempt()
        self.assertEqual(sum(p[2]==0xa0 for p in self.packets()),1)
        self.assertEqual(sum(p[2]==0xa8 for p in self.packets()),1)
        self.assertIn('ignored mode',self.page.locator('#log').inner_text())

    def test_wrong_slot_completion_is_ignored_until_exact_slot_arrives(self):
        self.prepare(wrongSlotFirst=True);self.run_attempt()
        self.assertEqual(sum(p[2]==0xa0 for p in self.packets()),1)
        self.assertEqual(sum(p[2]==0xa8 for p in self.packets()),1)
        self.assertIn('ignored application slot',self.page.locator('#log').inner_text())

    def test_destination_and_readback_failures_never_retry_and_always_exit(self):
        failures=({'destinationReject':0x3a},{'destinationWriteFailure':True},
                  {'stageReject':0x3a},{'stageWriteFailure':True},
                  {'readbackWriteFailure':True},{'after':0},{'exitReject':True},
                  {'exitWriteFailure':True})
        for options in failures:
            with self.subTest(options=options):
                self.prepare(**options);self.run_attempt()
                packets=self.packets()
                self.assertEqual(sum(p[2]==0xa0 for p in packets),1)
                self.assertEqual(sum(p[2]==0xa8 for p in packets),0 if options.get('stageWriteFailure') or options.get('stageReject') else 1)
                self.assertEqual(sum(p==[0,0x0c,0] for p in packets),1)
                self.assertFalse(any(len(p)>2 and p[1]==0x32 for p in packets))
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
        self.assertEqual(record['phase'],'verified-not-us')
        self.assertEqual(sum(p[2]==0xa8 for p in self.packets()),destination_writes)
        self.assertIn('US did not persist. No retry sent',self.page.locator('#log').inner_text())
        self.assertFalse(self.page.locator('#guidedUS').is_disabled())  # No destination retry is reachable from the UI.
        self.page.reload()
        self.assertEqual(self.page.evaluate('probeRecord.outcome'),'not-us')
        self.assertFalse(self.page.evaluate('''() => {
          session={verified:true,directWriteEligible:true,motorEligible:true,
            motorAuthenticated:true,currentDestination:0,regionWriteAttempted:false};
          return canSetUS(session);
        }'''))


if __name__=='__main__':
    unittest.main()
