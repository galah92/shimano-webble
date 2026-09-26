"""Hidden stock-pair destination adapter; durable transaction has Node tests."""
from pathlib import Path
from playwright.sync_api import sync_playwright


html = (Path(__file__).resolve().parents[1] / 'index.html').read_text()
with sync_playwright() as playwright:
    browser = playwright.chromium.launch()
    page = browser.new_page()
    errors = []
    page.on('pageerror', lambda error: errors.append(str(error)))
    page.route('https://shimano.test/',
               lambda route: route.fulfill(body=html, content_type='text/html'))
    page.goto('https://shimano.test/')
    page.evaluate('''() => {
      session={device:{id:'bike-a',gatt:{connected:true}},probeToken:'connection-a'};
      window.adapterCalls=[];window.adapterReply=null;window.disconnected=false;
      readFirmwareRecoveryJournal=()=>({stage:'prepared-readback-verified'});
      withWorkflowBaselineReader=async(_s,_journal,operation)=>operation({
        readBaseline:async()=>({identity:'a'.repeat(64),family:34,unit:0,
          dVersion:'4.3.0.0',mVersion:'4.2.1.0',destination:0})});
      runPreparedUsWriteTransaction=async options=>{
        adapterCalls.push([options.deviceId,options.connection]);
        adapterReply=await options.writeDestination();
        return {state:'US-readback-verified',regionVerified:true};
      };
      enterDisplayPcMode5=async(_s,label)=>adapterCalls.push(label);
      exitDisplayPcMode=async()=>adapterCalls.push('exit-mode');
      disconnect=()=>{disconnected=true;};
    }''')

    result = page.evaluate('''async () => {
      driveSettingExchange=async(_s,options)=>{
        adapterCalls.push([...options.packet]);
        adapterCalls.push([options.normalOpcode,options.errorOpcode]);
        if(options.packet[2]===0xa4)return Uint8Array.of(0,0x16,0xa6,0x34,0x12);
        return Uint8Array.of(0,0x16,0xaa);
      };
      const value=await writeAndVerifyUs(session);
      return {value,adapterCalls,adapterReply,disconnected,
        region:document.getElementById('region').textContent};
    }''')
    assert result == {
        'value': {'state': 'US-readback-verified', 'regionVerified': True},
        'adapterCalls': [
            ['bike-a', 'connection-a'],
            [0, 0x16, 0xa4, 0], [0xa6, 0xa7],
            'verified stock D4.3.0/M4.2.1 US write: SC-E7000-owned PC mode 5 before A0',
            [0, 0x16, 0xa0, 0x34, 0x12, 0xff, 0xff], [0xa2, 0xa3],
            'verified stock D4.3.0/M4.2.1 US write: SC-E7000-owned PC mode 5 refreshed before A8',
            [0, 0x16, 0xa8, 1, 1], [0xaa, 0xab], 'exit-mode'],
        'adapterReply': {'acknowledged': True},
        'disconnected': True,
        'region': 'US',
    }, result

    rejected = page.evaluate('''async () => {
      disconnected=false;adapterCalls=[];adapterReply=null;
      session={device:{id:'bike-a',gatt:{connected:true}},probeToken:'connection-b'};
      driveSettingExchange=async(_s,options)=>{
        if(options.packet[2]===0xa4)return Uint8Array.of(0,0x16,0xa6,0x34,0x12);
        if(options.packet[2]===0xa8)throw Error('verified stock D4.3.0/M4.2.1 US write: A8 US rejected 3A');
        return Uint8Array.of(0,0x16,0xa2);
      };
      await writeAndVerifyUs(session);
      return adapterReply;
    }''')
    assert rejected == {'acknowledged': False, 'errorCode': 0x3a}, rejected

    message = page.evaluate('''async () => {
      disconnected=false;adapterCalls=[];adapterReply=null;
      session={device:{id:'bike-a',gatt:{connected:true}},probeToken:'connection-c'};
      driveSettingExchange=async(_s,options)=>{
        if(options.packet[2]===0xa4)return Uint8Array.of(0,0x16,0xa6,0x34,0x12);
        if(options.packet[2]===0xa8)throw Error('A8 reply timed out');
        return Uint8Array.of(0,0x16,0xa2);
      };
      try {await writeAndVerifyUs(session);return null;} catch(error) {return error.message;}
    }''')
    assert message == 'A8 reply timed out', message

    a0_failure = page.evaluate('''async () => {
      disconnected=false;adapterCalls=[];adapterReply=null;
      session={device:{id:'bike-a',gatt:{connected:true}},probeToken:'connection-d'};
      driveSettingExchange=async(_s,options)=>{
        adapterCalls.push([...options.packet]);
        if(options.packet[2]===0xa4)return Uint8Array.of(0,0x16,0xa6,0x34,0x12);
        if(options.packet[2]===0xa0)throw Error('unchanged-lighting A0 rejected 3A');
        throw Error('A8 must not run after A0 rejection');
      };
      let message=null;
      try {await writeAndVerifyUs(session);} catch(error) {message=error.message;}
      return {message,packets:adapterCalls.filter(value=>Array.isArray(value)&&Number.isInteger(value[0])),
        exited:adapterCalls.includes('exit-mode')};
    }''')
    assert a0_failure == {
        'message': 'unchanged-lighting A0 rejected 3A',
        'packets': [[0, 0x16, 0xa4, 0], [0, 0x16, 0xa0, 0x34, 0x12, 0xff, 0xff]],
        'exited': True,
    }, a0_failure
    assert not errors, errors
    browser.close()

print('Prepared stock-pair UI adapter: explicit A0/A8 packets, reply mapping and timeout propagation passed')
