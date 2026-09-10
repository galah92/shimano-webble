// Preparation-to-US-to-restoration lineage and final readback gates.
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const {webcrypto,createHash}=require('node:crypto');
const rawCode=fs.readFileSync(__dirname+'/../index.html','utf8').split('// BEGIN FIRMWARE PACKET ENCODERS')[1].split('// END FIRMWARE FILE CHECKS')[0];
const image=(component,version,minimum,marker)=>{const b=new Uint8Array(256);b[200]=marker;
  if(component==='D'){b.fill(255,0,16);b.set(version,16);b.set([34,0,4],40);b.set(minimum,47);}
  else {b.set(version,8);b.set([255,255,34,0],12);b.set(minimum,16);}return b;};
const dp=image('D',[0x43,0,0],[0x42,0,0],1),mp=image('M',[0x42,1,0],[0x42,0,0],2);
const dr=image('D',[0x45,0,0],[0x44,8,0],3),mr=image('M',[0x44,8,0],[0x45,0,0],4);
const hash=b=>createHash('sha256').update(b).digest('hex');
const code=rawCode.replace('const FIRMWARE_IMAGES = Object.freeze({',
  `const FIRMWARE_IMAGES = Object.freeze({'${hash(dp)}':'preparation','${hash(mp)}':'preparation','${hash(dr)}':'restoration','${hash(mr)}':'restoration',`);
const file=b=>({size:b.length,arrayBuffer:async()=>b.slice().buffer});
const storage=()=>{const values=new Map();return {getItem:k=>values.get(k)??null,setItem:(k,v)=>values.set(k,String(v)),removeItem:k=>values.delete(k)};};
const original={identity:'a'.repeat(64),family:34,unit:0,dVersion:'4.5.0.0',mVersion:'4.4.8.0',destination:0};
const prepared={...original,dVersion:'4.3.0.0',mVersion:'4.2.1.0',destination:1};
const reference={version:1,verified:true,expected:{identity:original.identity},salt:'07'.repeat(16),
  bootloaderIdentity:{version:1,family:34,unit:0,identity:'b'.repeat(64)}};
(async()=>{
  const ctx=vm.createContext({Uint8Array,TextEncoder,Error,WeakSet,AbortController,crypto:webcrypto,setTimeout,clearTimeout});vm.runInContext(code,ctx);
  const prep=await ctx.loadFirmwarePair([file(dp),file(mp)]),restore=await ctx.loadFirmwarePair([file(dr),file(mr)]),journalStorage=storage();
  let journal=await ctx.createFirmwareRecoveryJournal({deviceId:'bike-a',pair:prep,baseline:original,identityReference:reference});
  journal={...journal,revision:20,stage:'US-persistence-verified',completed:{m:true,d:true},
    resetConnection:'d'.repeat(64),us:{writeConnection:'c'.repeat(64)}};
  ctx.writeFirmwareRecoveryJournal(journalStorage,journal);

  const restoredReference=await ctx.authorizeFirmwarePairTransfer({pair:restore,baseline:prepared,
    identityReference:null,deviceId:'bike-a',journalStorage});
  assert.equal(restoredReference.salt,reference.salt);assert.equal(restoredReference.expected.identity,original.identity);
  assert.deepEqual({...restoredReference.bootloaderIdentity},reference.bootloaderIdentity);
  let restoration=await ctx.createFirmwareRecoveryJournal({deviceId:'bike-a',pair:restore,baseline:prepared,
    identityReference:restoredReference});
  restoration={...restoration,revision:8,stage:'reset-write-completed',completed:{m:true,d:true},resetConnection:'d'.repeat(64)};
  ctx.writeFirmwareRecoveryJournal(journalStorage,restoration);
  ctx.verifyFirmwareAfterReconnect=async options=>{
    assert.deepEqual({...options.expected},{identity:original.identity,dVersion:'4.5.0.0',mVersion:'4.4.8.0',destination:1});
    return {state:'reconnected-readback-matches',identityMatches:true,firmwareReadbackMatches:true,
      regionReadbackMatches:true,dVersion:'4.5.0.0',mVersion:'4.4.8.0',destination:1};
  };
  let result=await ctx.verifyRestoredFirmwareAfterReconnect({journalStorage,deviceId:'bike-a',connection:'restored-session'});
  assert.equal(result.state,'restoration-readback-verified');assert.equal(result.goalVerified,true);
  assert.equal(ctx.readFirmwareRecoveryJournal(journalStorage).stage,'restoration-readback-verified');

  journal={...journal,revision:21,stage:'US-readback-verified'};ctx.writeFirmwareRecoveryJournal(journalStorage,journal);
  await assert.rejects(ctx.authorizeFirmwarePairTransfer({pair:restore,baseline:prepared,deviceId:'bike-a',journalStorage}),/power-cycle/);
  journal={...journal,revision:22,stage:'US-persistence-verified'};ctx.writeFirmwareRecoveryJournal(journalStorage,journal);
  await assert.rejects(ctx.authorizeFirmwarePairTransfer({pair:restore,baseline:{...prepared,destination:0},deviceId:'bike-a',journalStorage}),/prepared/);
  await assert.rejects(ctx.authorizeFirmwarePairTransfer({pair:restore,baseline:prepared,deviceId:'bike-b',journalStorage}),/different/);
  await assert.rejects(ctx.authorizeFirmwarePairTransfer({pair:prep,baseline:{...original,destination:1},
    identityReference:reference,deviceId:'bike-a',journalStorage}),/original/);

  restoration={...restoration,revision:9,stage:'reset-write-completed'};ctx.writeFirmwareRecoveryJournal(journalStorage,restoration);
  ctx.verifyFirmwareAfterReconnect=async()=>({state:'reconnected-readback-mismatch',identityMatches:true,
    firmwareReadbackMatches:true,regionReadbackMatches:false,dVersion:'4.5.0.0',mVersion:'4.4.8.0',destination:0});
  result=await ctx.verifyRestoredFirmwareAfterReconnect({journalStorage,deviceId:'bike-a',connection:'restored-session'});
  assert.equal(result.goalVerified,false);assert.equal(result.state,'restoration-readback-mismatch');
  const stopped=ctx.readFirmwareRecoveryJournal(journalStorage);assert.equal(stopped.stage,'stopped');
  assert.equal(stopped.lastStage,'restoration-readback-verification');
  await assert.rejects(ctx.recoverFirmwarePair({}),/Incomplete recovery|firmware transfer completion/);
  console.log('Firmware goal transaction: verified US lineage, restoration authorization and final original-pair US readback passed');
})().catch(error=>{console.error(error);process.exit(1);});
