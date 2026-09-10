// Durable preflight and guided workflow planning; no hardware required.
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const {webcrypto,createHash}=require('node:crypto');
const rawCode=fs.readFileSync(__dirname+'/../index.html','utf8').split('// BEGIN FIRMWARE PACKET ENCODERS')[1].split('// END FIRMWARE FILE CHECKS')[0];
const d=new Uint8Array(256),m=new Uint8Array(256);
d.fill(255,0,16);d.set([0x43,0,0],16);d.set([34,0,4],40);d.set([0x42,0,0],47);
m.set([0x42,1,0],8);m.set([255,255,34,0],12);m.set([0x42,0,0],16);
const hash=b=>createHash('sha256').update(b).digest('hex');
const code=rawCode.replace('const FIRMWARE_IMAGES = Object.freeze({',
  `const FIRMWARE_IMAGES = Object.freeze({'${hash(d)}':'preparation','${hash(m)}':'preparation',`);
const file=b=>({size:b.length,arrayBuffer:async()=>b.slice().buffer});
const storage=()=>{const values=new Map();return {values,getItem:k=>values.get(k)??null,
  setItem:(k,v)=>values.set(k,String(v)),removeItem:k=>values.delete(k)};};
const baseline={identity:'a'.repeat(64),family:34,unit:0,dVersion:'4.5.0.0',mVersion:'4.4.8.0',destination:0};
const bootloaderIdentity={version:1,family:34,unit:0,identity:'b'.repeat(64)};
(async()=>{
  const ctx=vm.createContext({Uint8Array,TextEncoder,Error,WeakSet,AbortController,crypto:webcrypto,setTimeout,clearTimeout});
  vm.runInContext(code,ctx);
  assert.equal(ctx.firmwareWorkflowPlan(null).action,'preflight');
  let probes=0;
  ctx.probeBootloaderRoundTrip=async options=>{
    probes++;options.onBaseline({...baseline});await options.onBootloaderIdentity({...bootloaderIdentity});
    options.onStage?.('reset-request');return {resetRequested:true,firmwareDataSent:false};
  };
  const journalStorage=storage(),salt=new Uint8Array(16).fill(7),credentials=new Uint8Array(15).fill(9);
  const result=await ctx.createPreparationPreflightJournal({files:[file(m),file(d)],credentials,characteristics:{},
    subscribe(){},signal:new AbortController().signal,deviceId:'bike-a',journalStorage,identitySalt:salt});
  assert.equal(probes,1);assert.equal(result.state,'preflight-reset-requested');assert.equal(result.firmwareDataSent,false);
  let journal=ctx.readFirmwareRecoveryJournal(journalStorage);
  assert.equal(journal.stage,'ready');assert.equal(ctx.firmwareWorkflowPlan(journal).action,'transfer');
  assert.equal(ctx.firmwareWorkflowPlan(journal).powerCycle,true);
  assert(!journalStorage.values.get('shimano-firmware-recovery-v1').includes('bike-a'));

  const plan=(stage,options={})=>ctx.firmwareWorkflowPlan({...journal,revision:journal.revision+1,stage,
    lastStage:options.lastStage??null,completed:options.completed??journal.completed,
    ...(options.resetConnection?{resetConnection:options.resetConnection}:{}),...(options.us?{us:options.us}:{})});
  assert.equal(plan('M-transfer').action,'recover');
  assert.equal(plan('paired-transfer-finished',{completed:{m:true,d:true}}).action,'reset');
  const reset='d'.repeat(64),us={writeConnection:'c'.repeat(64)};
  assert.equal(plan('reset-write-completed',{completed:{m:true,d:true},resetConnection:reset}).action,'verify-preparation');
  assert.equal(plan('prepared-readback-verified',{completed:{m:true,d:true},resetConnection:reset}).action,'write-us');
  assert.equal(plan('US-readback-verified',{completed:{m:true,d:true},resetConnection:reset,us}).action,'verify-us');
  assert.equal(plan('US-persistence-verified',{completed:{m:true,d:true},resetConnection:reset,us}).action,'restore');
  assert.equal(ctx.firmwareWorkflowPlan({...journal,revision:4,stage:'stopped',lastStage:'US-write-attempt',
    completed:{m:true,d:true},resetConnection:reset,us}).action,'resolve-us');
  console.log('Firmware workflow: no-data preflight journal and deterministic resume planning passed');
})().catch(error=>{console.error(error);process.exit(1);});
