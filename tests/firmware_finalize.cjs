// Reset and reconnect readback are separate, journal-gated transactions.
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
const baseline=()=>({identity:'a'.repeat(64),family:34,unit:0,dVersion:'4.5.0.0',mVersion:'4.4.8.0',destination:0});
const makeStorage=()=>{const values=new Map();let fail=false;return {values,set fail(value){fail=value;},
  getItem:k=>values.get(k)??null,setItem(k,v){if(fail)throw Error('storage unavailable');values.set(k,String(v));},
  removeItem:k=>values.delete(k)};};
async function fixture({writeFailure=false}={}) {
  const ctx=vm.createContext({Uint8Array,TextEncoder,Error,WeakSet,AbortController,crypto:webcrypto,setTimeout,clearTimeout});
  vm.runInContext(code,ctx);
  const files=[file(m),file(d)],pair=await ctx.loadFirmwarePair(files),journalStorage=makeStorage();
  let journal=await ctx.createFirmwareRecoveryJournal({deviceId:'bike-a',pair,baseline:baseline(),identityReference:reference()});
  journal={...journal,revision:1,stage:'paired-transfer-finished',completed:{m:true,d:true}};
  ctx.writeFirmwareRecoveryJournal(journalStorage,journal);
  const writes=[];
  const native={async writeValueWithResponse(p){writes.push([...p]);if(writeFailure)throw Error('ATT failed');},
    async writeValueWithoutResponse(p){writes.push([...p]);if(writeFailure)throw Error('ATT failed');}};
  const resetOptions={characteristics:{'2afa':native},signal:new AbortController().signal,deviceId:'bike-a',connection:'reset-session',journalStorage};
  return {ctx,files,pair,journalStorage,writes,resetOptions};
}
(async()=>{
  let f=await fixture(),result=await f.ctx.requestFirmwarePairReset(f.resetOptions);
  assert.deepEqual(f.writes,[[0,136,40,0,0,0]]);assert.equal(result.state,'reset-write-completed');
  let journal=f.ctx.readFirmwareRecoveryJournal(f.journalStorage);
  assert.equal(journal.stage,'reset-write-completed');assert(journal.completed.m&&journal.completed.d);

  const current='readback-session';
  f.ctx.verifyFirmwareAfterReconnect=async options=>{
    assert.notEqual(options.connection,options.previousConnection);
    assert.deepEqual({...options.expected},{identity:'a'.repeat(64),dVersion:'4.3.0.0',mVersion:'4.2.1.0',destination:0});
    assert.deepEqual([...options.identitySalt],new Array(16).fill(7));
    return {state:'reconnected-readback-matches',identityMatches:true,firmwareReadbackMatches:true,
      regionReadbackMatches:true,dVersion:'4.3.0.0',mVersion:'4.2.1.0',destination:0,reconnectObserved:true,
      powerCycleVerified:false,persistenceVerified:false,installable:false};
  };
  result=await f.ctx.verifyPreparedFirmwareAfterReconnect({journalStorage:f.journalStorage,deviceId:'bike-a',connection:current});
  assert.equal(result.state,'prepared-readback-verified');assert.equal(result.preparationVerified,true);
  journal=f.ctx.readFirmwareRecoveryJournal(f.journalStorage);assert.equal(journal.stage,'prepared-readback-verified');

  f=await fixture();f.resetOptions.deviceId='bike-b';
  await assert.rejects(f.ctx.requestFirmwarePairReset(f.resetOptions),/different Web Bluetooth device/);assert.equal(f.writes.length,0);
  f=await fixture();journal=f.ctx.readFirmwareRecoveryJournal(f.journalStorage);
  journal={...journal,stage:'M-finished',completed:{m:true,d:false}};f.ctx.writeFirmwareRecoveryJournal(f.journalStorage,journal);
  await assert.rejects(f.ctx.requestFirmwarePairReset(f.resetOptions),/completed firmware pair/);assert.equal(f.writes.length,0);
  f=await fixture();f.journalStorage.fail=true;
  await assert.rejects(f.ctx.requestFirmwarePairReset(f.resetOptions));assert.equal(f.writes.length,0);

  f=await fixture({writeFailure:true});await assert.rejects(f.ctx.requestFirmwarePairReset(f.resetOptions),error=>{
    assert.equal(error.deviceStateUnknown,true);assert.equal(error.journalPersisted,true);return true;
  });
  journal=f.ctx.readFirmwareRecoveryJournal(f.journalStorage);assert.equal(journal.stage,'stopped');assert.equal(journal.lastStage,'reset-request');

  f=await fixture();await f.ctx.requestFirmwarePairReset(f.resetOptions);
  f.ctx.verifyFirmwareAfterReconnect=async()=>({state:'reconnected-readback-mismatch',identityMatches:true,
    firmwareReadbackMatches:false,regionReadbackMatches:true,dVersion:'4.5.0.0',mVersion:'4.4.8.0',destination:0});
  result=await f.ctx.verifyPreparedFirmwareAfterReconnect({journalStorage:f.journalStorage,deviceId:'bike-a',connection:'readback-session'});
  assert.equal(result.state,'prepared-readback-mismatch');assert.equal(result.preparationVerified,false);
  journal=f.ctx.readFirmwareRecoveryJournal(f.journalStorage);assert.equal(journal.stage,'stopped');assert.equal(journal.lastStage,'prepared-readback-verification');
  f.ctx.verifyFirmwareAfterReconnect=async()=>{throw Error('read timeout');};
  await assert.rejects(f.ctx.verifyPreparedFirmwareAfterReconnect({journalStorage:f.journalStorage,deviceId:'bike-a',connection:'another-readback-session'}),/journal retained/);
  journal=f.ctx.readFirmwareRecoveryJournal(f.journalStorage);assert.equal(journal.stage,'stopped');assert.equal(journal.lastStage,'prepared-readback-verification');

  console.log('Firmware finalize: completed-pair reset gate, exact prepared reconnect readback, device/storage/write failures and retryable journal passed');
})().catch(error=>{console.error(error);process.exit(1);});
