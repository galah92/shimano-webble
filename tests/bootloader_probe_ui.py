"""Guided UI wiring. Physical packet behavior is tested in bootloader_probe.cjs."""
from pathlib import Path
from playwright.sync_api import sync_playwright, expect
html=(Path(__file__).resolve().parents[1]/'index.html').read_text()
with sync_playwright() as p:
    browser=p.chromium.launch()
    page=browser.new_page()
    errors=[]
    page.on('pageerror',lambda e:errors.append(str(e)))
    page.route('https://shimano.test/',lambda r:r.fulfill(body=html,content_type='text/html'))
    page.goto('https://shimano.test/')
    expect(page.locator('#bootProbe')).to_be_disabled()
    assert page.locator('#bootProfileFile').count()==0
    page.evaluate('''() => {
      window.calls=[];
      window.fakeSession=()=>({device:{gatt:{connected:true,disconnect(){this.connected=false;}}},chars:{},controller:new AbortController(),probeToken:crypto.randomUUID()});
      session=fakeSession();controls();
      authenticate=async()=>{calls.push('session');session.verified=true;};
      identifyDrive=async()=>{calls.push('read');session.batchDone=true;session.motorEligible=true;await verifyPendingBootloaderProbe(session);};
      authenticateMotor=async()=>{calls.push('motor');session.motorAuthenticated=true;};
      probeBootloaderRoundTrip=async opts=>{
        calls.push('probe');
        if(opts.credentials.length!==15)throw Error('Missing embedded profile');
        opts.onBaseline({identity:'a'.repeat(64),family:34,unit:0,dVersion:'4.5.0.0',mVersion:'4.4.8.0',destination:0});
        await opts.onBootloaderIdentity({version:1,family:34,unit:0,identity:'b'.repeat(64)});
        opts.onStage('reset-request');
        return {family:34,unit:0,recoveryEntryAcknowledged:true};
      };
    }''')
    page.locator('#bootProbe').click()
    expect(page.locator('#bootProbeStatus')).to_contain_text('passkey first')
    assert page.evaluate('calls')==[]
    page.locator('#passkey').fill('123456')
    page.locator('#bootProbe').click()
    expect(page.locator('#bootProbeStatus')).to_contain_text('Region check finished')
    expect(page.locator('#bootProbe')).to_have_text('Check region')
    assert page.evaluate('calls')==['session','read']
    assert page.evaluate('session!==null && !busy && !guidedTestRunning')
    assert page.evaluate('probeRecord===null')
    # Repeated checks on this connection must not launch recovery either.
    page.locator('#bootProbe').click()
    assert page.evaluate('calls')==['session','read']
    # Preserve verification for records created by earlier builds.
    page.evaluate("""() => {
      probeRecord={version:1,connection:'previous',salt:'07'.repeat(16),expected:{identity:'a'.repeat(64),family:34,unit:0,dVersion:'4.5.0.0',mVersion:'4.4.8.0',destination:0},verified:false,bootloaderIdentity:{version:1,family:34,unit:0,identity:'b'.repeat(64)}};
      saveProbeRecord();
    }""")
    # Verification must stop after reading, without motor authentication or a second probe.
    page.evaluate('''() => {
      calls=[];session=fakeSession();controls();
      verifyFirmwareAfterReconnect=async()=>({state:'reconnected-readback-matches',identityMatches:true,dVersion:'4.5.0.0',mVersion:'4.4.8.0',destination:0});
    }''')
    page.locator('#passkey').fill('123456')
    expect(page.locator('#bootProbe')).to_have_text('Verify after restart')
    page.locator('#bootProbe').click()
    expect(page.locator('#bootProbeStatus')).to_contain_text('Test finished')
    assert page.evaluate('calls')==['session','read']
    assert page.evaluate('probeRecord.verified')
    assert page.evaluate("probeRecord.bootloaderIdentity.identity==='b'.repeat(64)")
    # US verification uses the same button but must not claim original EU or restart a probe.
    page.evaluate("window.originalProbeRecord=JSON.stringify(probeRecord)")
    for matches in (False, True):
        page.evaluate('''matches=>{
          calls=[];session=fakeSession();
          probeRecord={version:1,kind:'us-region',connection:'previous',salt:'07'.repeat(16),expected:{identity:'a'.repeat(64),family:34,unit:0,dVersion:'4.3.0.0',mVersion:'4.2.1.0',destination:1},verified:false};
          verifyFirmwareAfterReconnect=async opts=>{
            if(opts.expected.destination!==1)throw Error('Wrong US expectation');
            return {state:matches?'reconnected-readback-matches':'reconnected-readback-mismatch',identityMatches:matches,dVersion:'4.3.0.0',mVersion:'4.2.1.0',destination:matches?1:0};
          };controls();
        }''',matches)
        page.locator('#passkey').fill('123456')
        page.locator('#bootProbe').click()
        page.wait_for_function('!guidedTestRunning')
        assert page.evaluate('calls')==['session','read']
        assert page.evaluate('probeRecord.verified')==matches
        expect(page.locator('#log')).to_contain_text('Post-region readback:')
        assert 'Post-region readback:' in page.evaluate('exportLog()')
    page.evaluate("probeRecord=JSON.parse(originalProbeRecord);saveProbeRecord()")
    # A failed prerequisite must never reach the probe.
    for failure,expected in [('session',['session']),('read',['session','read'])]:
        page.evaluate('''failure=>{
          probeRecord=null;calls=[];session=fakeSession();controls();
          authenticate=async()=>{calls.push('session');session.verified=failure!=='session';};
          identifyDrive=async()=>{calls.push('read');session.batchDone=failure!=='read';session.motorEligible=failure!=='read';};
          authenticateMotor=async()=>{calls.push('motor');session.motorAuthenticated=failure!=='motor';};
        }''',failure)
        page.locator('#passkey').fill('123456')
        page.locator('#bootProbe').click()
        page.wait_for_function('!guidedTestRunning')
        assert page.evaluate('calls')==expected
    page.reload()
    assert page.evaluate('probeRecord.verified')
    assert page.evaluate("probeRecord.bootloaderIdentity.identity==='b'.repeat(64)")
    page.evaluate("text => { logEl.textContent=text; }", "[one] Connected; first\n[one] Bootloader entry/exit probe started.\n[one] stopped\n[two] Connected; second\n[two] Post-probe readback: matches\n")
    copied=page.evaluate('exportLog()')
    assert 'stopped' in copied and 'Post-probe readback' in copied
    assert not errors,errors
    browser.close()
print('Region check UI: no motor authentication or recovery, verification-only restart, prerequisite failures and saved record passed')
