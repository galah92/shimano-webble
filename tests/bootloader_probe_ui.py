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
        opts.onStage('reset-request');
        return {mBootloaderVersion:[2,0,3,0],family:34,unit:0};
      };
    }''')
    page.locator('#bootProbe').click()
    expect(page.locator('#bootProbeStatus')).to_contain_text('passkey first')
    assert page.evaluate('calls')==[]
    page.locator('#passkey').fill('123456')
    page.locator('#bootProbe').click()
    expect(page.locator('#bootProbeStatus')).to_contain_text('Turn the bike off and on')
    assert page.evaluate('calls')==['session','read','motor','probe']
    assert page.evaluate('session===null && !busy && !guidedTestRunning')
    assert page.evaluate("JSON.parse(sessionStorage.getItem(PROBE_RECORD_KEY)).verified===false")
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
    # A failed prerequisite must never reach the probe.
    for failure,expected in [('session',['session']),('read',['session','read']),('motor',['session','read','motor'])]:
        page.evaluate('''failure=>{
          probeRecord=null;calls=[];session=fakeSession();controls();
          authenticate=async()=>{calls.push('session');session.verified=failure!=='session';};
          identifyDrive=async()=>{calls.push('read');session.batchDone=true;session.motorEligible=failure!=='read';};
          authenticateMotor=async()=>{calls.push('motor');session.motorAuthenticated=failure!=='motor';};
        }''',failure)
        page.locator('#passkey').fill('123456')
        page.locator('#bootProbe').click()
        page.wait_for_function('!guidedTestRunning')
        assert page.evaluate('calls')==expected
    page.reload()
    assert page.evaluate('probeRecord.verified')
    assert not errors,errors
    browser.close()
print('Guided test UI: embedded profile, passkey gate, ordered automatic setup, verification-only restart, prerequisite failures and saved record passed')
