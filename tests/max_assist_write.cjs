// Stock D4.5.0/M4.4.8 maximum-assist B0 transaction: exact packet, durable
// at-most-once semantics, fail-closed context gates, and power-cycle proof.
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const {webcrypto}=require('node:crypto');
const code=fs.readFileSync(__dirname+'/../index.html','utf8')
  .split('// BEGIN FIRMWARE PACKET ENCODERS')[1].split('// END FIRMWARE FILE CHECKS')[0];
const storage=()=>{const values=new Map();return {values,getItem:key=>values.get(key)??null,
  setItem:(key,value)=>values.set(key,String(value)),removeItem:key=>values.delete(key)};};
const base={family:34,unit:0,dVersion:'4.5.0.0',mVersion:'4.4.8.0',destination:1,
  currentHundredths:2500,usProfileHundredths:3218};
const clone=value=>({...value});

(async()=>{
  const ctx=vm.createContext({Uint8Array,TextEncoder,Error,WeakSet,AbortController,crypto:webcrypto,
    setTimeout,clearTimeout});
  vm.runInContext(code,ctx);
  const journalKey=vm.runInContext('MAX_ASSIST_US_JOURNAL_KEY',ctx);
  assert.deepEqual([...ctx.maxAssistSpeedWritePacket(3200)],[0,0x16,0xb0,0x80,0x0c,0xff,0xff]);
  assert.equal(ctx.stockMaxAssistUsTarget(3218),3200);
  assert.equal(ctx.stockMaxAssistUsTarget(3190),3190);
  for(const value of [999,5001,2500.5])assert.throws(()=>ctx.maxAssistSpeedWritePacket(value));

  const happyStorage=storage();let speed=2500,writes=0,reads=0,journalSeenBeforeWrite=false;
  const happy=await ctx.runMaxAssistUsWriteTransaction({journalStorage:happyStorage,deviceId:'bike-a',
    connection:'write-session',readSnapshot:async()=>{reads++;return {...base,currentHundredths:speed};},
    writeMaximum:async value=>{writes++;journalSeenBeforeWrite=happyStorage.getItem(journalKey)!==null;
      speed=value;return {acknowledged:true};}});
  assert.equal(happy.state,'max-assist-readback-verified');
  assert.equal(happy.targetHundredths,3200);assert.equal(writes,1);assert.equal(reads,2);
  assert.equal(journalSeenBeforeWrite,true);
  assert.equal(ctx.readMaxAssistUsJournal(happyStorage).stage,'readback-verified');
  assert.equal(ctx.readMaxAssistUsJournal(happyStorage).expected.usProfileHundredths,3218);
  await assert.rejects(ctx.runMaxAssistUsWriteTransaction({journalStorage:happyStorage,deviceId:'bike-a',
    connection:'duplicate',readSnapshot:async()=>base,writeMaximum:async()=>{writes++;return {acknowledged:true};}}),
  /already journaled/);
  assert.equal(writes,1);
  await assert.rejects(ctx.verifyMaxAssistUsPersistenceAfterPowerCycle({journalStorage:happyStorage,
    deviceId:'bike-a',connection:'power-session',powerCycleConfirmed:false,
    readSnapshot:async()=>({...base,currentHundredths:3200})}),/power-cycle/);
  await assert.rejects(ctx.verifyMaxAssistUsPersistenceAfterPowerCycle({journalStorage:happyStorage,
    deviceId:'bike-a',connection:'write-session',powerCycleConfirmed:true,
    readSnapshot:async()=>({...base,currentHundredths:3200})}),/different BLE session/);
  const persistent=await ctx.verifyMaxAssistUsPersistenceAfterPowerCycle({journalStorage:happyStorage,
    deviceId:'bike-a',connection:'power-session',powerCycleConfirmed:true,
    readSnapshot:async()=>({...base,currentHundredths:3200})});
  assert.equal(persistent.state,'max-assist-persistence-verified');
  assert.equal(persistent.persistenceVerified,true);assert.equal(persistent.mutationRetried,false);
  assert.equal(ctx.readMaxAssistUsJournal(happyStorage).stage,'persistence-verified');

  for(const invalid of [
    {...base,destination:0},
    {...base,dVersion:'4.3.0.0'},
    {...base,mVersion:'4.2.1.0'},
    {...base,currentHundredths:3200},
    {...base,usProfileHundredths:999},
  ]) {
    const targetStorage=storage();let invalidWrites=0;
    await assert.rejects(ctx.runMaxAssistUsWriteTransaction({journalStorage:targetStorage,
      deviceId:'bike-a',connection:'invalid-session',readSnapshot:async()=>clone(invalid),
      writeMaximum:async()=>{invalidWrites++;return {acknowledged:true};}}));
    assert.equal(invalidWrites,0);assert.equal(targetStorage.getItem(journalKey),null);
  }

  const rejectedStorage=storage();let rejectedWrites=0;
  const rejected=await ctx.runMaxAssistUsWriteTransaction({journalStorage:rejectedStorage,deviceId:'bike-a',
    connection:'rejected-session',readSnapshot:async()=>clone(base),
    writeMaximum:async()=>{rejectedWrites++;return {acknowledged:false,errorCode:0x3a};}});
  assert.equal(rejected.state,'max-assist-write-rejected');assert.equal(rejected.errorCode,0x3a);
  assert.equal(rejectedWrites,1);assert.equal(ctx.readMaxAssistUsJournal(rejectedStorage).stage,'stopped');
  await assert.rejects(ctx.runMaxAssistUsWriteTransaction({journalStorage:rejectedStorage,deviceId:'bike-a',
    connection:'rejected-repeat',readSnapshot:async()=>base,
    writeMaximum:async()=>{rejectedWrites++;return {acknowledged:true};}}),/already journaled/);
  assert.equal(rejectedWrites,1);

  const uncertainStorage=storage();let uncertainWrites=0;
  await assert.rejects(ctx.runMaxAssistUsWriteTransaction({journalStorage:uncertainStorage,deviceId:'bike-a',
    connection:'uncertain-session',readSnapshot:async()=>clone(base),
    writeMaximum:async()=>{uncertainWrites++;throw Error('ATT timeout');}}),error=>{
      assert.equal(error.deviceStateUnknown,true);assert.equal(error.mutationRetried,false);
      return /outcome is uncertain/.test(error.message);
    });
  assert.equal(uncertainWrites,1);
  let uncertainJournal=ctx.readMaxAssistUsJournal(uncertainStorage);
  assert.equal(uncertainJournal.stage,'stopped');assert.equal(uncertainJournal.lastStage,'write-attempt');
  const resolved=await ctx.verifyMaxAssistUsPersistenceAfterPowerCycle({journalStorage:uncertainStorage,
    deviceId:'bike-a',connection:'resolution-session',powerCycleConfirmed:true,
    readSnapshot:async()=>({...base,currentHundredths:3200})});
  assert.equal(resolved.state,'max-assist-persistence-verified');assert.equal(resolved.mutationRetried,false);
  assert.equal(uncertainWrites,1);

  const mismatchStorage=storage();let mismatchSpeed=2500;
  const mismatch=await ctx.runMaxAssistUsWriteTransaction({journalStorage:mismatchStorage,deviceId:'bike-a',
    connection:'mismatch-write',readSnapshot:async()=>({...base,currentHundredths:mismatchSpeed}),
    writeMaximum:async()=>({acknowledged:true})});
  assert.equal(mismatch.state,'max-assist-readback-mismatch');
  const afterPower=await ctx.verifyMaxAssistUsPersistenceAfterPowerCycle({journalStorage:mismatchStorage,
    deviceId:'bike-a',connection:'mismatch-read',powerCycleConfirmed:true,
    readSnapshot:async()=>({...base,currentHundredths:2500})});
  assert.equal(afterPower.state,'max-assist-persistence-mismatch');
  assert.equal(afterPower.persistenceVerified,false);

  const failingStorage=storage();failingStorage.setItem=()=>{throw Error('durable storage unavailable');};
  let storageFailureWrites=0;
  await assert.rejects(ctx.runMaxAssistUsWriteTransaction({journalStorage:failingStorage,deviceId:'bike-a',
    connection:'storage-failure',readSnapshot:async()=>clone(base),
    writeMaximum:async()=>{storageFailureWrites++;return {acknowledged:true};}}),/storage unavailable/);
  assert.equal(storageFailureWrites,0);

  const wrongDeviceStorage=storage();let wrongSpeed=2500;
  await ctx.runMaxAssistUsWriteTransaction({journalStorage:wrongDeviceStorage,deviceId:'bike-a',
    connection:'wrong-device-write',readSnapshot:async()=>({...base,currentHundredths:wrongSpeed}),
    writeMaximum:async value=>{wrongSpeed=value;return {acknowledged:true};}});
  await assert.rejects(ctx.verifyMaxAssistUsPersistenceAfterPowerCycle({journalStorage:wrongDeviceStorage,
    deviceId:'bike-b',connection:'wrong-device-read',powerCycleConfirmed:true,
    readSnapshot:async()=>({...base,currentHundredths:3200})}),/different Web Bluetooth device/);

  console.log('Maximum-assist B0: exact packet, fail-closed gates, one-shot journal, uncertainty and persistence tests passed');
})().catch(error=>{console.error(error);process.exit(1);});
