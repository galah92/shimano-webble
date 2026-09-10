// Prepared-firmware US write and power-cycle persistence gates; no hardware required.
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const {webcrypto,createHash}=require('node:crypto');
const rawCode=fs.readFileSync(__dirname+'/../index.html','utf8').split('// BEGIN FIRMWARE PACKET ENCODERS')[1].split('// END FIRMWARE FILE CHECKS')[0];
const d=new Uint8Array(256),m=new Uint8Array(256);
d.fill(255,0,16);d.set([0x43,0,0],16);d.set([34,0,4],40);d.set([0x42,0,0],47);
m.set([255,255,34,0],12);m.set([0x42,1,0],8);m.set([0x42,0,0],16);
const hash=b=>createHash('sha256').update(b).digest('hex');
const code=rawCode.replace('const FIRMWARE_IMAGES = Object.freeze({',
  `const FIRMWARE_IMAGES = Object.freeze({'${hash(d)}':'preparation','${hash(m)}':'preparation',`);
const file=b=>({size:b.length,arrayBuffer:async()=>b.slice().buffer});
const reference=()=>({version:1,verified:true,expected:{identity:'a'.repeat(64)},salt:'07'.repeat(16),
  bootloaderIdentity:{version:1,family:34,unit:0,identity:'b'.repeat(64)}});
const original=()=>({identity:'a'.repeat(64),family:34,unit:0,dVersion:'4.5.0.0',mVersion:'4.4.8.0',destination:0});
const prepared=destination=>({identity:'a'.repeat(64),family:34,unit:0,dVersion:'4.3.0.0',mVersion:'4.2.1.0',destination});
const makeStorage=()=>{const values=new Map();let fail=false;return {values,set fail(value){fail=value;},
  getItem:k=>values.get(k)??null,setItem(k,v){if(fail)throw Error('storage unavailable');values.set(k,String(v));},
  removeItem:k=>values.delete(k)};};
async function fixture(){
  const ctx=vm.createContext({Uint8Array,TextEncoder,Error,WeakSet,AbortController,crypto:webcrypto,setTimeout,clearTimeout});
  vm.runInContext(code,ctx);
  const pair=await ctx.loadFirmwarePair([file(m),file(d)]),storage=makeStorage();
  let journal=await ctx.createFirmwareRecoveryJournal({deviceId:'bike-a',pair,baseline:original(),identityReference:reference()});
  journal={...journal,revision:8,stage:'prepared-readback-verified',completed:{m:true,d:true},resetConnection:'d'.repeat(64)};
  ctx.writeFirmwareRecoveryJournal(storage,journal);
  return {ctx,storage};
}
async function successfulWrite(f,{acknowledged=true}={}){
  let reads=0,writes=0;
  const result=await f.ctx.runPreparedUsWriteTransaction({journalStorage:f.storage,deviceId:'bike-a',connection:'write-session',
    readBaseline:async()=>prepared(reads++),writeDestination:async()=>{
      writes++;assert.equal(f.ctx.readFirmwareRecoveryJournal(f.storage).stage,'US-write-attempt');
      return {acknowledged};
    }});
  return {result,reads,writes};
}
(async()=>{
  let f=await fixture(),run=await successfulWrite(f);
  assert.equal(run.reads,2);assert.equal(run.writes,1);assert.equal(run.result.state,'US-readback-verified');
  let journal=f.ctx.readFirmwareRecoveryJournal(f.storage);
  assert.equal(journal.stage,'US-readback-verified');assert.match(journal.us.writeConnection,/^[a-f0-9]{64}$/);
  const encoded=f.storage.getItem('shimano-firmware-recovery-v1');
  assert(!encoded.includes('bike-a'));assert(!encoded.includes('write-session'));

  f=await fixture();run=await successfulWrite(f,{acknowledged:false});
  assert.equal(run.result.state,'US-readback-verified');assert.equal(run.result.acknowledged,false);

  f=await fixture();let reads=0,writes=0;
  await assert.rejects(f.ctx.runPreparedUsWriteTransaction({journalStorage:f.storage,deviceId:'bike-b',connection:'write-session',
    readBaseline:async()=>{reads++;return prepared(0);},writeDestination:async()=>{writes++;}}),/different Web Bluetooth device/);
  assert.equal(reads,0);assert.equal(writes,0);
  f=await fixture();
  await assert.rejects(f.ctx.runPreparedUsWriteTransaction({journalStorage:f.storage,deviceId:'bike-a',connection:'write-session',
    readBaseline:async()=>prepared(1),writeDestination:async()=>{writes++;}}),/baseline differs/);
  assert.equal(writes,0);assert.equal(f.ctx.readFirmwareRecoveryJournal(f.storage).stage,'prepared-readback-verified');
  f=await fixture();f.storage.fail=true;writes=0;
  await assert.rejects(f.ctx.runPreparedUsWriteTransaction({journalStorage:f.storage,deviceId:'bike-a',connection:'write-session',
    readBaseline:async()=>prepared(0),writeDestination:async()=>{writes++;}}));assert.equal(writes,0);

  for(const reply of [{acknowledged:false,errorCode:0x3a},{acknowledged:true,errorCode:-1},null]){
    f=await fixture();writes=0;
    await assert.rejects(f.ctx.runPreparedUsWriteTransaction({journalStorage:f.storage,deviceId:'bike-a',connection:'write-session',
      readBaseline:async()=>prepared(0),writeDestination:async()=>{writes++;return reply;}}),/US write stopped/);
    assert.equal(writes,1);journal=f.ctx.readFirmwareRecoveryJournal(f.storage);
    assert.equal(journal.stage,'stopped');assert.equal(journal.lastStage,'US-write-attempt');
  }
  f=await fixture();reads=0;
  run=await f.ctx.runPreparedUsWriteTransaction({journalStorage:f.storage,deviceId:'bike-a',connection:'write-session',
    readBaseline:async()=>prepared(0),writeDestination:async()=>({acknowledged:true})});
  assert.equal(run.state,'US-readback-mismatch');assert.equal(run.regionVerified,false);
  await assert.rejects(f.ctx.runPreparedUsWriteTransaction({journalStorage:f.storage,deviceId:'bike-a',connection:'write-session-2',
    readBaseline:async()=>{reads++;return prepared(0);},writeDestination:async()=>({acknowledged:true})}),/verified preparation firmware/);
  assert.equal(reads,0);
  await assert.rejects(f.ctx.resolveUncertainUsWriteAfterReconnect({journalStorage:f.storage,deviceId:'bike-a',
    connection:'write-session',readBaseline:async()=>prepared(1)}),/different BLE session/);
  let resolved=await f.ctx.resolveUncertainUsWriteAfterReconnect({journalStorage:f.storage,deviceId:'bike-a',
    connection:'read-session',readBaseline:async()=>prepared(1)});
  assert.equal(resolved.state,'US-readback-verified');assert.equal(resolved.mutationRetried,false);
  assert.equal(f.ctx.readFirmwareRecoveryJournal(f.storage).stage,'US-readback-verified');

  f=await fixture();await f.ctx.runPreparedUsWriteTransaction({journalStorage:f.storage,deviceId:'bike-a',connection:'write-session',
    readBaseline:async()=>prepared(0),writeDestination:async()=>({acknowledged:true})});
  resolved=await f.ctx.resolveUncertainUsWriteAfterReconnect({journalStorage:f.storage,deviceId:'bike-a',
    connection:'read-session',readBaseline:async()=>prepared(0)});
  assert.equal(resolved.state,'US-write-not-applied');assert.equal(resolved.mutationRetried,false);
  assert.equal(f.ctx.readFirmwareRecoveryJournal(f.storage).stage,'stopped');

  f=await fixture();await successfulWrite(f);
  let verifyCalls=0;
  f.ctx.verifyFirmwareAfterReconnect=async options=>{
    verifyCalls++;assert.deepEqual({...options.expected},{identity:'a'.repeat(64),dVersion:'4.3.0.0',mVersion:'4.2.1.0',destination:1});
    assert.notEqual(options.connection,options.previousConnection);assert.deepEqual([...options.identitySalt],new Array(16).fill(7));
    return {state:'reconnected-readback-matches',identityMatches:true,firmwareReadbackMatches:true,
      regionReadbackMatches:true,dVersion:'4.3.0.0',mVersion:'4.2.1.0',destination:1};
  };
  await assert.rejects(f.ctx.verifyUsPersistenceAfterPowerCycle({journalStorage:f.storage,deviceId:'bike-a',
    connection:'restart-session',powerCycleConfirmed:false}),/power-cycle confirmation/);assert.equal(verifyCalls,0);
  await assert.rejects(f.ctx.verifyUsPersistenceAfterPowerCycle({journalStorage:f.storage,deviceId:'bike-a',
    connection:'write-session',powerCycleConfirmed:true}),/different BLE session/);assert.equal(verifyCalls,0);
  let result=await f.ctx.verifyUsPersistenceAfterPowerCycle({journalStorage:f.storage,deviceId:'bike-a',
    connection:'restart-session',powerCycleConfirmed:true});
  assert.equal(result.state,'US-persistence-verified');assert.equal(result.persistenceVerified,true);
  assert.equal(result.powerCycleConfirmed,true);assert.equal(verifyCalls,1);
  assert.equal(f.ctx.readFirmwareRecoveryJournal(f.storage).stage,'US-persistence-verified');

  f=await fixture();await successfulWrite(f);
  f.ctx.verifyFirmwareAfterReconnect=async()=>({state:'reconnected-readback-mismatch',identityMatches:true,
    firmwareReadbackMatches:true,regionReadbackMatches:false,dVersion:'4.3.0.0',mVersion:'4.2.1.0',destination:0});
  result=await f.ctx.verifyUsPersistenceAfterPowerCycle({journalStorage:f.storage,deviceId:'bike-a',
    connection:'restart-session',powerCycleConfirmed:true});
  assert.equal(result.state,'US-persistence-mismatch');assert.equal(result.persistenceVerified,false);
  journal=f.ctx.readFirmwareRecoveryJournal(f.storage);assert.equal(journal.stage,'stopped');
  assert.equal(journal.lastStage,'US-persistence-verification');
  f.ctx.verifyFirmwareAfterReconnect=async()=>{throw Error('read timeout');};
  await assert.rejects(f.ctx.verifyUsPersistenceAfterPowerCycle({journalStorage:f.storage,deviceId:'bike-a',
    connection:'another-session',powerCycleConfirmed:true}),/journal retained/);

  f=await fixture();journal=f.ctx.readFirmwareRecoveryJournal(f.storage);
  assert.throws(()=>f.ctx.writeFirmwareRecoveryJournal(f.storage,{...journal,stage:'US-write-ready'}),/Invalid firmware recovery journal/);
  console.log('Firmware region transaction: durable one-shot write, decisive readback, same-device gates and explicit power-cycle persistence passed');
})().catch(error=>{console.error(error);process.exit(1);});
