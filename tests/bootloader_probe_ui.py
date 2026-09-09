"""UI wiring test; protocol behavior is exercised by bootloader_probe.cjs."""
from pathlib import Path
import hashlib
from playwright.sync_api import sync_playwright, expect
html=(Path(__file__).resolve().parents[1]/'index.html').read_text()
profile=bytes(range(1,16))
# Substitute only the private profile digest in the test page.
import re
html=re.sub(r"const BOOT_PROFILE_HASH = '[a-f0-9]+'",f"const BOOT_PROFILE_HASH = '{hashlib.sha256(profile).hexdigest()}'",html)
with sync_playwright() as p:
    browser=p.chromium.launch()
    page=browser.new_page()
    errors=[]
    page.on('pageerror',lambda e:errors.append(str(e)))
    page.route('https://shimano.test/',lambda r:r.fulfill(body=html,content_type='text/html'))
    page.goto('https://shimano.test/')
    page.locator('summary').filter(has_text='Bootloader entry/exit').click()
    expect(page.locator('#bootProbe')).to_be_disabled()
    def load(data):
        page.locator('#bootProfileFile').set_input_files({'name':'profile.bin','mimeType':'application/octet-stream','buffer':data})
    load(bytes(14))
    expect(page.locator('#bootProbeStatus')).to_contain_text('15-byte')
    load(bytes(15))
    expect(page.locator('#bootProbeStatus')).to_contain_text('does not match')
    load(profile)
    expect(page.locator('#bootProbeStatus')).to_contain_text('Profile loaded locally')
    expect(page.locator('#bootProbe')).to_be_disabled()
    page.evaluate('''() => {
      window.fakeSession=()=>({device:{gatt:{connected:true,disconnect(){this.connected=false;}}},chars:{},controller:new AbortController(),probeToken:crypto.randomUUID(),motorEligible:true,motorAuthenticated:true});
      session=fakeSession();controls();
      probeBootloaderRoundTrip=async opts=>{
        opts.onBaseline({identity:'a'.repeat(64),family:34,unit:0,dVersion:'4.5.0.0',mVersion:'4.4.8.0',destination:0});
        opts.onStage('reset-request');
        return {mBootloaderVersion:[2,0,3,0],family:34,unit:0};
      };
    }''')
    expect(page.locator('#bootProbe')).to_be_enabled()
    page.locator('#bootProbe').click()
    expect(page.locator('#bootProbeStatus')).to_contain_text('Turn the bike off and on')
    assert page.evaluate('session===null && bootProfile===null && !busy')
    assert page.evaluate("JSON.parse(sessionStorage.getItem(PROBE_RECORD_KEY)).verified===false")
    page.reload()
    assert page.evaluate('probeRecord!==null && !probeRecord.verified && bootProfile===null')
    page.evaluate('''async () => {
      session={device:{gatt:{connected:true}},chars:{},controller:new AbortController(),probeToken:probeRecord.connection};
      let calls=0;
      verifyFirmwareAfterReconnect=async opts=>{calls++;return {state:'reconnected-readback-matches',identityMatches:true,dVersion:'4.5.0.0',mVersion:'4.4.8.0',destination:0};};
      await verifyPendingBootloaderProbe(session);
      if(calls!==0)throw Error('Same connection incorrectly verified');
      session.probeToken=crypto.randomUUID();
      await verifyPendingBootloaderProbe(session);
      if(calls!==1 || !probeRecord.verified)throw Error('Reconnect readback not recorded');
    }''')
    expect(page.locator('#log')).to_contain_text('original configuration matches')
    assert not errors,errors
    browser.close()
print('Probe UI: profile validation, authentication gate, consumption/disconnect, pending record reload, distinct connection readback passed')
