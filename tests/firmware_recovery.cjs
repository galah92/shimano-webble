// Reconnect recovery is a complete M replay followed by the paired D path.
// This test controls workers; their physical packets have separate suites.
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const {webcrypto,createHash}=require('node:crypto');
const rawCode=fs.readFileSync(__dirname+'/../index.html','utf8').split('// BEGIN FIRMWARE PACKET ENCODERS')[1].split('// END FIRMWARE FILE CHECKS')[0];
const d=new Uint8Array(256),m=new Uint8Array(256);
d.fill(255,0,16);d.set([0x43,0,0],16);d.set([34,0,4],40);d.set([0x42,0,0],47);
m.set([255,255,34,0],12);m.set([0x42,1,0],8);m.set([0x42,0,0],16);
const hash=b=>createHash('sha256').update(b).digest('hex');
const code=rawCode.replace('const FIRMWARE_IMAGES = Object.freeze({',
  `const FIRMWARE_IMAGES = Object.freeze({'${hash(d)}':'preparation','${hash(m)}':'preparation',`);
const identityReference=()=>({version:1,verified:true,expected:{identity:'a'.repeat(64)},salt:'07'.repeat(16),
  bootloaderIdentity:{version:1,family:34,unit:0,identity:createHash('sha256').update(Uint8Array.of(68,66,76,49,...new Uint8Array(16).fill(7),34,0,9,8,7,6,5,4)).digest('hex')}});
const baseline=()=>({identity:'a'.repeat(64),family:34,unit:0,dVersion:'4.5.0.0',mVersion:'4.4.8.0',destination:0});
const file=b=>({size:b.length,arrayBuffer:async()=>b.slice().buffer});
const storage=()=>{const values=new Map();return {values,getItem:k=>values.get(k)??null,
  setItem:(k,v)=>values.set(k,String(v)),removeItem:k=>values.delete(k)};};

async function fixture(fail) {
  const ctx=vm.createContext({Uint8Array,TextEncoder,Error,WeakSet,AbortController,crypto:webcrypto,setTimeout,clearTimeout});
  vm.runInContext(code,ctx);
  const files=[file(m),file(d)],pair=await ctx.loadFirmwarePair(files),journalStorage=storage();
  let journal=await ctx.createFirmwareRecoveryJournal({deviceId:'bike-a',pair,
    baseline:{...baseline(),ignoredPrivateField:'must-not-persist'},identityReference:identityReference()});
  // Model loss after M may already have replied. Recovery must still replay M
  // from byte zero because the vendor worker has no persisted offset input.
  journal={...journal,revision:1,stage:'stopped',lastStage:'D-update-entry',completed:{m:true,d:false}};
  ctx.writeFirmwareRecoveryJournal(journalStorage,journal);
  const calls=[],writes=[],stages=[],keys=new Uint8Array(15).fill(7),controller=new AbortController();
  const native={async writeValueWithResponse(p){writes.push([...p]);},async writeValueWithoutResponse(p){writes.push([...p]);}};
  const record=name=>{calls.push(name);if(name===fail)throw Error('controlled worker failure');};
  let entries=0;
  ctx.enterFirmwareUpdateSession=async o=>{record(`entry${++entries}`);assert.equal(o.recoveryInstall,true);await o.write('2afa',Uint8Array.of(4));return {mode:32,targetSelector:0,pcaSkipped:true};};
  ctx.selectMFirmwareSlot=async()=>record('slot');
  ctx.transferMFirmware=async o=>{record('M');assert.deepEqual([...o.data],[...m]);assert.equal(o.targetSelector,0);assert.equal(o.nextSequence(),0);assert.equal(o.nextSequence(),1);};
  ctx.enterDBootloader=async o=>{record('Dentry');assert.equal(o.recoveryInstall,undefined);assert.equal(o.mode,32);assert.equal(o.targetSelector,0);assert.deepEqual([...o.credentials],new Array(15).fill(7));};
  ctx.transferDComponent=async o=>{record('D');assert.deepEqual([...o.data],[...d]);assert.deepEqual([...o.identitySalt],new Array(16).fill(7));
    assert.equal(o.expectedBootloaderIdentity.identity,identityReference().bootloaderIdentity.identity);await o.write(Uint8Array.of(136,46,0,0,0));};
  const options={files,credentials:keys,deviceId:'bike-a',journalStorage,
    characteristics:{'2afa':native,'2afe':native},subscribe(){throw Error('Controlled workers do not subscribe');},signal:controller.signal,
    onStage:value=>stages.push(value)};
  return {ctx,options,calls,writes,stages,journalStorage};
}

(async()=>{
  let f=await fixture(),result=await f.ctx.recoverFirmwarePair(f.options);
  assert.deepEqual(f.calls,['entry1','slot','M','entry2','Dentry','D']);
  assert.deepEqual(f.writes,[[0,4],[0,4],[0,136,46,0,0,0]]);
  assert(result.mFinished&&result.dFinished);assert.equal(result.reset,false);assert.equal(result.firmwareVerified,false);
  let journal=f.ctx.readFirmwareRecoveryJournal(f.journalStorage);
  assert.equal(journal.stage,'paired-transfer-finished');assert.deepEqual({...journal.completed},{m:true,d:true});assert.equal(journal.attempt,1);
  const encoded=f.journalStorage.values.get('shimano-firmware-recovery-v1');
  assert(!encoded.includes('bike-a'));assert(!encoded.includes('[7,7,7,7,7,7,7,7,7,7,7,7,7,7,7]'));
  assert(!encoded.includes('ignoredPrivateField'));

  for(const fail of ['entry1','slot','M','entry2','Dentry','D']) {
    f=await fixture(fail);await assert.rejects(f.ctx.recoverFirmwarePair(f.options),error=>{
      assert.equal(error.mFinished,['entry2','Dentry','D'].includes(fail));assert.equal(error.dFinished,false);
      assert.equal(error.journalPersisted,true);assert.equal(error.reset,false);return true;
    });
    journal=f.ctx.readFirmwareRecoveryJournal(f.journalStorage);
    assert.equal(journal.stage,'stopped');assert.equal(journal.lastStage,f.stages.at(-1));
  }

  f=await fixture();f.options.deviceId='bike-b';
  await assert.rejects(f.ctx.recoverFirmwarePair(f.options),/different Web Bluetooth device/);
  assert.equal(f.calls.length,0);assert.equal(f.writes.length,0);
  f=await fixture();journal=f.ctx.readFirmwareRecoveryJournal(f.journalStorage);
  journal.pair.m.hash='f'.repeat(64);f.ctx.writeFirmwareRecoveryJournal(f.journalStorage,journal);
  await assert.rejects(f.ctx.recoverFirmwarePair(f.options),/files do not match/);
  assert.equal(f.calls.length,0);assert.equal(f.writes.length,0);

  f=await fixture();journal=f.ctx.readFirmwareRecoveryJournal(f.journalStorage);
  journal={...journal,revision:journal.revision+1,stage:'paired-transfer-finished',lastStage:null,completed:{m:true,d:true}};
  f.ctx.writeFirmwareRecoveryJournal(f.journalStorage,journal);
  result=await f.ctx.recoverFirmwarePair(f.options);
  assert.equal(result.state,'paired-transfer-finished');assert.equal(f.calls.length,0);assert.equal(f.writes.length,0);

  f=await fixture();journal=f.ctx.readFirmwareRecoveryJournal(f.journalStorage);
  for(const invalid of [
    {...journal,completed:{m:false,d:true}},
    {...journal,stage:'M-finished',completed:{m:false,d:false}},
    {...journal,stage:'paired-transfer-finished',completed:{m:true,d:false}},
    {...journal,baseline:{...journal.baseline,mVersion:'4.2.1.0'}},
    {...journal,stage:'stopped',lastStage:null},
    {...journal,stage:'M-transfer',lastStage:'M-update-entry'},
    {...journal,stage:'prepared-readback-verified',lastStage:null,completed:{m:true,d:true}},
  ]) assert.throws(()=>f.ctx.validateFirmwareRecoveryJournal(invalid),/Invalid firmware recovery journal/);

  console.log('Firmware recovery journal: exact device/files, full M replay, paired D order, durable stage failures and no-reset completion passed');
})().catch(error=>{console.error(error);process.exit(1);});
