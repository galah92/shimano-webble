// Hidden D4.3.0 wheel-circumference fallback: packet shape, durable one-shot
// journal, uncertainty resolution and power-cycle persistence gates.
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const {webcrypto,createHash}=require('node:crypto');
const rawCode=fs.readFileSync(__dirname+'/../index.html','utf8')
  .split('// BEGIN FIRMWARE PACKET ENCODERS')[1].split('// END FIRMWARE FILE CHECKS')[0];
const image=(component,version,minimum,marker)=>{const b=new Uint8Array(256);b[200]=marker;
  if(component==='D'){b.fill(255,0,16);b.set(version,16);b.set([34,0,4],40);b.set(minimum,47);}
  else {b.set(version,8);b.set([255,255,34,0],12);b.set(minimum,16);}return b;};
const dp=image('D',[0x43,0,0],[0x42,0,0],1),mp=image('M',[0x42,1,0],[0x42,0,0],2);
const hash=b=>createHash('sha256').update(b).digest('hex');
const code=rawCode.replace('const FIRMWARE_IMAGES = Object.freeze({',
  `const FIRMWARE_IMAGES = Object.freeze({'${hash(dp)}':'preparation','${hash(mp)}':'preparation',`);
const file=b=>({size:b.length,arrayBuffer:async()=>b.slice().buffer});
const storage=()=>{const values=new Map();return {values,getItem:k=>values.get(k)??null,
  setItem:(k,v)=>values.set(k,String(v)),removeItem:k=>values.delete(k)};};
const original={identity:'a'.repeat(64),family:34,unit:0,dVersion:'4.5.0.0',mVersion:'4.4.8.0',destination:0};
const prepared={...original,dVersion:'4.3.0.0',mVersion:'4.2.1.0'};
const reference={version:1,verified:true,expected:{identity:original.identity},salt:'07'.repeat(16),
  bootloaderIdentity:{version:1,family:34,unit:0,identity:'b'.repeat(64)}};

async function preparedStorage(ctx) {
  const journalStorage=storage(),pair=await ctx.loadFirmwarePair([file(dp),file(mp)]);
  let journal=await ctx.createFirmwareRecoveryJournal({deviceId:'bike-a',pair,baseline:original,
    identityReference:reference});
  journal={...journal,revision:10,stage:'prepared-readback-verified',completed:{m:true,d:true},
    resetConnection:'d'.repeat(64)};
  ctx.writeFirmwareRecoveryJournal(journalStorage,journal);
  pair.d.data.fill(0);pair.m.data.fill(0);
  return journalStorage;
}

(async()=>{
  const ctx=vm.createContext({Uint8Array,TextEncoder,Error,WeakSet,AbortController,crypto:webcrypto,
    setTimeout,clearTimeout});vm.runInContext(code,ctx);
  assert.deepEqual([...ctx.wheelReadPacket()],[0,0x35,0x04,0]);
  assert.deepEqual([...ctx.wheelWritePacket(1625)],[0,0x35,0,0x59,0x06]);
  assert.equal(ctx.parseWheelReadReply(Uint8Array.of(0,0x35,0x06,0x20,0x08)),2080);
  assert.throws(()=>ctx.parseWheelReadReply(Uint8Array.of(0,0x35,0x07,0x20,0x08)),/Malformed/);
  const calculation=ctx.wheelFallbackTargetMm(2080);
  assert.equal(calculation.targetMm,1625);assert.equal(calculation.displayRatio,0.78125);
  assert(Math.abs(calculation.estimatedRealCutoffKph-32)<0.01);

  const journalStorage=await preparedStorage(ctx);let wheel=2080,writes=0,reads=0;
  const result=await ctx.runPreparedWheelWriteTransaction({journalStorage,deviceId:'bike-a',
    connection:'write-session',targetMm:1625,readBaseline:async()=>({...prepared}),
    readWheel:async()=>{reads++;return wheel;},writeWheel:async value=>{writes++;wheel=value;return {acknowledged:true};}});
  assert.equal(result.state,'wheel-readback-verified');assert.equal(result.originalMm,2080);
  assert.equal(result.targetMm,1625);assert.equal(writes,1);assert.equal(reads,2);
  let wheelJournal=ctx.readWheelFallbackJournal(journalStorage);
  assert.equal(wheelJournal.stage,'readback-verified');assert.equal(wheelJournal.originalMm,2080);
  await assert.rejects(ctx.runPreparedWheelWriteTransaction({journalStorage,deviceId:'bike-a',
    connection:'duplicate',targetMm:1625,readBaseline:async()=>prepared,readWheel:async()=>wheel,
    writeWheel:async()=>{writes++;return {acknowledged:true};}}),/already journaled/);
  assert.equal(writes,1);
  await assert.rejects(ctx.verifyWheelPersistenceAfterPowerCycle({journalStorage,deviceId:'bike-a',
    connection:'power-session',powerCycleConfirmed:false,readBaseline:async()=>prepared,readWheel:async()=>wheel}),
  /power-cycle/);
  const persistent=await ctx.verifyWheelPersistenceAfterPowerCycle({journalStorage,deviceId:'bike-a',
    connection:'power-session',powerCycleConfirmed:true,readBaseline:async()=>({...prepared}),readWheel:async()=>wheel});
  assert.equal(persistent.state,'wheel-persistence-verified');assert.equal(persistent.persistenceVerified,true);
  assert.equal(ctx.readWheelFallbackJournal(journalStorage).stage,'persistence-verified');

  const uncertainStorage=await preparedStorage(ctx);let uncertainWrites=0;
  await assert.rejects(ctx.runPreparedWheelWriteTransaction({journalStorage:uncertainStorage,deviceId:'bike-a',
    connection:'uncertain-session',targetMm:1625,readBaseline:async()=>({...prepared}),readWheel:async()=>2080,
    writeWheel:async()=>{uncertainWrites++;throw Error('ATT timeout');}}),error=>{
      assert.equal(error.deviceStateUnknown,true);return /outcome is uncertain/.test(error.message);
    });
  assert.equal(uncertainWrites,1);
  wheelJournal=ctx.readWheelFallbackJournal(uncertainStorage);
  assert.equal(wheelJournal.stage,'stopped');assert.equal(wheelJournal.lastStage,'write-attempt');
  const resolved=await ctx.resolveUncertainWheelWriteAfterReconnect({journalStorage:uncertainStorage,
    deviceId:'bike-a',connection:'resolution-session',readBaseline:async()=>({...prepared}),readWheel:async()=>1625});
  assert.equal(resolved.state,'wheel-readback-verified');assert.equal(resolved.mutationRetried,false);
  assert.equal(uncertainWrites,1);

  const unappliedStorage=await preparedStorage(ctx);
  await assert.rejects(ctx.runPreparedWheelWriteTransaction({journalStorage:unappliedStorage,deviceId:'bike-a',
    connection:'failed-session',targetMm:1625,readBaseline:async()=>({...prepared}),readWheel:async()=>2080,
    writeWheel:async()=>{throw Error('disconnect');}}));
  const unapplied=await ctx.resolveUncertainWheelWriteAfterReconnect({journalStorage:unappliedStorage,
    deviceId:'bike-a',connection:'read-session',readBaseline:async()=>({...prepared}),readWheel:async()=>2080});
  assert.equal(unapplied.state,'wheel-write-not-applied');assert.equal(unapplied.mutationRetried,false);
  assert.equal(ctx.readWheelFallbackJournal(unappliedStorage).stage,'stopped');
  console.log('Wheel fallback transaction: exact protocol, calculation, one-shot journal, resolution and persistence gates passed');
})().catch(error=>{console.error(error);process.exit(1);});
