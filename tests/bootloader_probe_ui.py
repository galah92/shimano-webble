"""Guided US workflow dispatch. Physical protocol behavior has separate suites."""
from pathlib import Path
from playwright.sync_api import sync_playwright, expect

html=(Path(__file__).resolve().parents[1]/'index.html').read_text()
with sync_playwright() as p:
    browser=p.chromium.launch()
    page=browser.new_page()
    errors=[]
    page.on('pageerror',lambda error:errors.append(str(error)))
    page.route('https://shimano.test/',lambda route:route.fulfill(body=html,content_type='text/html'))
    page.goto('https://shimano.test/')
    expect(page.locator('#bootProbe')).to_be_disabled()
    page.evaluate('''() => {
      window.calls=[];
      session={device:{id:'bike-a',gatt:{connected:true}},chars:{},controller:new AbortController(),
        probeToken:'connection-a',verified:true,batchDone:true,motorEligible:true,motorAuthenticated:true};
      firmwarePairs.preparation=[{}];firmwarePairs.restoration=[{}];
      document.getElementById('firmwareConsent').checked=true;
      window.testJournal={stage:'synthetic'};
      optionalFirmwareJournal=()=>testJournal;
      ensureWorkflowSession=async(_s,opts)=>calls.push(`session:${opts.information}:${opts.motor}`);
      transferAndReset=async(_s,plan)=>calls.push(`transfer:${plan.action}:${plan.pair}`);
      resetCompletedPair=async()=>calls.push('reset');
      createPreparationPreflightJournal=async()=>{calls.push('preflight');return {state:'preflight-reset-requested'};};
      withWorkflowBaselineReader=async(_s,_journal,operation)=>operation({writer:{write(){}},readBaseline:async()=>({})});
      verifyPreparedFirmwareAfterReconnect=async()=>{calls.push('verify-preparation');return {preparationVerified:true};};
      writeAndVerifyUs=async()=>calls.push('write-us');
      resolveUncertainUsWriteAfterReconnect=async()=>{calls.push('resolve-us');return {state:'US-readback-verified'};};
      verifyUsPersistenceAfterPowerCycle=async()=>{calls.push('verify-us');return {persistenceVerified:true};};
      verifyRestoredFirmwareAfterReconnect=async()=>{calls.push('verify-restoration');return {goalVerified:true};};
      readFirmwareRecoveryJournal=()=>testJournal;
      disconnect=()=>calls.push('disconnect');
    }''')

    def run(action,pair='preparation',mutation=False,power=False):
        page.evaluate('''([action,pair,mutation,power])=>{
          calls=[];testPlan={action,label:action,pair,mutation,powerCycle:power};
          document.getElementById('firmwareConsent').checked=true;
          currentFirmwareWorkflowPlan=()=>testPlan;controls();
        }''',[action,pair,mutation,power])
        page.evaluate("document.getElementById('bootProbe').click()")
        page.wait_for_function('!firmwareWorkflowRunning')
        assert not errors,errors
        return page.evaluate('calls')

    assert run('preflight',mutation=True)==['session:true:true','preflight','disconnect']
    assert run('transfer',mutation=True)==['session:true:true','transfer:transfer:preparation']
    assert run('recover',mutation=True)==['session:false:false','transfer:recover:preparation']
    assert run('reset',mutation=True)==['session:false:false','reset']
    value=run('verify-preparation',power=True)
    assert value==['session:true:false','verify-preparation','session:true:true','write-us'],(value,page.locator('#bootProbeStatus').inner_text(),page.locator('#log').inner_text()[-500:])
    assert run('write-us',mutation=True)==['session:true:true','write-us']
    assert run('resolve-us')==['session:true:false','resolve-us','disconnect']
    assert run('verify-us',power=True)==[
        'session:true:false','verify-us','session:true:true','transfer:restore:restoration']
    assert run('restore',pair='restoration',mutation=True)==['session:true:true','transfer:restore:restoration']
    assert run('verify-restoration',pair='restoration',power=True)==['session:true:false','verify-restoration']

    # Firmware acknowledgement remains a required mutation gate.
    page.evaluate("testPlan={action:'restore',label:'restore',pair:'restoration',mutation:true,powerCycle:false};document.getElementById('firmwareConsent').checked=false;calls=[];controls()")
    expect(page.locator('#bootProbe')).to_be_disabled()
    assert page.evaluate('calls')==[]
    # Pressing the explicitly worded action is the physical power-cycle confirmation.
    page.evaluate("testPlan={action:'verify-us',label:'Verify US after power cycle',pair:'preparation',mutation:false,powerCycle:true};document.getElementById('firmwareConsent').checked=true;controls()")
    expect(page.locator('#bootProbe')).to_be_enabled()
    expect(page.locator('#bootProbe')).to_contain_text('I power-cycled')
    assert page.locator('#setUS').is_disabled()

    # The primary action opens Bluetooth and continues in the same tap.
    page.evaluate('''() => {
      Object.defineProperty(navigator,'bluetooth',{value:{},configurable:true});
      calls=[];session=null;workflowPasskey='';
      testPlan={action:'preflight',label:'Start verified preparation',pair:'preparation',mutation:true,powerCycle:false};
      connect=async()=>{calls.push(`connect:${workflowPasskey}:${document.getElementById('passkey').value}`);session={device:{gatt:{connected:true}}};};
      runFirmwareWorkflow=async()=>calls.push('run');controls();
    }''')
    page.locator('#passkey').fill('123456')
    expect(page.locator('#bootProbe')).to_be_enabled()
    expect(page.locator('#bootProbe')).to_contain_text('Connect and start')
    page.evaluate("document.getElementById('bootProbe').click()")
    page.wait_for_function("calls.length === 2")
    assert page.evaluate('calls') == ['connect:123456:', 'run']
    expect(page.locator('#passkeyStatus')).to_contain_text('ready for required reconnects')
    browser.close()
print('Guided US workflow UI dispatch, mutation gates and power-cycle gates passed')
