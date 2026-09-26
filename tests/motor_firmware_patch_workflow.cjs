// Exact patched-pair orchestration and lineage use generated firmware bytes.
// No vendor image, Bluetooth command, or browser UI is involved.
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const {webcrypto,createHash}=require('node:crypto');
let code=fs.readFileSync(__dirname+'/../index.html','utf8')
  .split('// BEGIN FIRMWARE PACKET ENCODERS')[1].split('// END FIRMWARE FILE CHECKS')[0];
const sha=data=>createHash('sha256').update(data).digest('hex');
const stockD=new Uint8Array(256);stockD.fill(0x5a);stockD.fill(255,0,16);
stockD.set([0x45,0,0],16);stockD.set([34,0,4],40);stockD.set([0x44,8,0],47);
stockD.set([0x2d,0xd1],100);stockD.set([0x24,0xd1],120);
const patchedD=stockD.slice();patchedD[0x12]=1;patchedD.set([0,0xbf],100);patchedD.set([0,0xbf],120);
const stockM=new Uint8Array(256);stockM.fill(0x33);stockM.set([0x44,8,0],8);
stockM.set([255,255,34,0],12);stockM.set([0x44,6,0],16);
code=code
  .replace('const FIRMWARE_IMAGES = Object.freeze({',
    `const FIRMWARE_IMAGES = Object.freeze({'${sha(stockD)}':'restoration','${sha(stockM)}':'restoration',`)
  .replace("name:'D4.5.0 PC-mode gate experiment',size:138072,",
    "name:'D4.5.0 PC-mode gate experiment',size:256,")
  .replace("inputHash:'44806bd54aedff95a88bb73fafe0f0581297f2f67b2ea35545cea012899d90bb'",`inputHash:'${sha(stockD)}'`)
  .replace("outputHash:'0dbbb3d3b634d831d8450d2758d953502bfdc7f16ac8640a4e3ca46fff3fff18'",`outputHash:'${sha(patchedD)}'`)
  .replace("peerHash:'9ea350e988345a9d9fb41c1363562ca190f1a8d5e1cc8a38c6373f69b877f033'",`peerHash:'${sha(stockM)}'`)
  .replace('offset:0x152c8','offset:100').replace('offset:0x15394','offset:120');
const ctx=vm.createContext({Uint8Array,TextEncoder,Error,WeakSet,AbortController,
  crypto:webcrypto,setTimeout,clearTimeout});
vm.runInContext(code,ctx);
const file=bytes=>({size:bytes.length,arrayBuffer:async()=>Uint8Array.from(bytes).buffer});
const files=()=>[file(stockD),file(stockM)];
const storage=()=>{const values=new Map();return {values,getItem:key=>values.get(key)??null,
  setItem:(key,value)=>values.set(key,String(value)),removeItem:key=>values.delete(key)};};
const baseline=(destination=0,dVersion='4.5.0.0')=>({identity:'a'.repeat(64),family:34,unit:0,
  dVersion,mVersion:'4.4.8.0',destination});
const bootloaderIdentity={version:1,family:34,unit:0,identity:createHash('sha256')
  .update(Uint8Array.of(68,66,76,49,...new Uint8Array(16).fill(7),34,0,9,8,7,6,5,4)).digest('hex')};
const reference=()=>({version:1,verified:true,expected:{identity:'a'.repeat(64)},
  salt:'07'.repeat(16),bootloaderIdentity:{...bootloaderIdentity}});

(async()=>{
  const journalStorage=storage(),writes=[],calls=[],controller=new AbortController();
  const native={async writeValueWithResponse(packet){writes.push([...packet]);},
    async writeValueWithoutResponse(packet){writes.push([...packet]);}};
  const options={files:files(),baseline:baseline(),credentials:new Uint8Array(15).fill(7),
    identityReference:reference(),deviceId:'bike-a',journalStorage,
    characteristics:{'2afa':native,'2afe':native},subscribe(){throw Error('controlled worker');},
    signal:controller.signal};
  ctx.readFirmwareBaseline=async()=>{calls.push('baseline');return baseline();};
  let entries=0;
  ctx.enterFirmwareUpdateSession=async transport=>{calls.push(`entry${++entries}`);
    await transport.write('2afa',Uint8Array.of(4));return {targetSelector:entries===1?13:0};};
  ctx.selectMFirmwareSlot=async()=>calls.push('slot');
  ctx.transferMFirmware=async value=>{calls.push('M');assert.deepEqual([...value.data],[...stockM]);};
  ctx.enterDBootloader=async value=>{calls.push('Dentry');assert.deepEqual([...value.credentials],new Array(15).fill(7));};
  ctx.transferDComponent=async value=>{calls.push('D');assert.deepEqual([...value.data],[...patchedD]);
    assert.equal(value.expectedBootloaderIdentity.identity,bootloaderIdentity.identity);
    await value.write(Uint8Array.of(136,46,0,0,0));};

  const result=await ctx.transferPatchedD450Pair(options);
  assert.equal(result.source,'pc-mode-patch');assert.equal(result.dVersion,'4.5.0.1');
  assert.equal(result.mVersion,'4.4.8.0');assert(result.mFinished&&result.dFinished);
  assert.deepEqual(calls,['baseline','entry1','slot','M','entry2','Dentry','D']);
  assert.deepEqual(writes,[[0,4],[0,4],[0,136,46,0,0,0]]);
  let journal=ctx.readFirmwareRecoveryJournal(journalStorage);
  assert.equal(journal.pair.source,'pc-mode-patch');assert.equal(journal.pair.d.hash,sha(patchedD));
  assert.equal(ctx.firmwareWorkflowPlan(journal).action,'inspect');
  assert.throws(()=>ctx.validateFirmwareRecoveryJournal({...journal,stage:'stopped',
    lastStage:'patch-readback-verification',resetConnection:'b'.repeat(64),completed:{m:true,d:false}}));

  const recoveryStorage=storage(),recoveryPair=await ctx.loadPatchedD450FirmwarePair(files());
  let recoveryJournal=await ctx.createFirmwareRecoveryJournal({deviceId:'bike-a',pair:recoveryPair,
    baseline:baseline(),identityReference:reference()});
  recoveryJournal={...recoveryJournal,revision:1,stage:'stopped',lastStage:'D-update-entry',
    completed:{m:true,d:false}};
  ctx.writeFirmwareRecoveryJournal(recoveryStorage,recoveryJournal);
  calls.length=0;writes.length=0;entries=0;
  const recovered=await ctx.recoverFirmwarePair({...options,files:files(),journalStorage:recoveryStorage});
  assert.equal(recovered.source,'pc-mode-patch');assert(recovered.mFinished&&recovered.dFinished);
  assert.deepEqual(calls,['entry1','slot','M','entry2','Dentry','D']);
  assert.equal(ctx.readFirmwareRecoveryJournal(recoveryStorage).stage,'paired-transfer-finished');
  recoveryPair.d.data.fill(0);recoveryPair.m.data.fill(0);

  const resetConnection=await ctx.firmwareConnectionBinding('reset-session',journal.identitySalt);
  journal={...journal,revision:journal.revision+1,stage:'reset-write-completed',resetConnection,
    completed:{m:true,d:true}};
  ctx.writeFirmwareRecoveryJournal(journalStorage,journal);
  ctx.verifyFirmwareAfterReconnect=async value=>{assert.equal(value.expected.dVersion,'4.5.0.1');
    assert.equal(value.expected.mVersion,'4.4.8.0');assert.equal(value.expected.destination,0);
    return {state:'reconnected-readback-matches'};};
  let verified=await ctx.verifyPatchedD450FirmwareAfterReconnect({journalStorage,deviceId:'bike-a',
    connection:'patched-session'});
  assert.equal(verified.state,'patch-readback-verified');assert.equal(verified.patchVerified,true);

  let reads=0,writesUS=0;
  const us=await ctx.runPreparedUsWriteTransaction({journalStorage,deviceId:'bike-a',connection:'us-session',
    readBaseline:async()=>baseline(reads++?1:0,'4.5.0.1'),
    writeDestination:async()=>{writesUS++;return {acknowledged:true};}});
  assert.equal(us.state,'US-readback-verified');assert.equal(writesUS,1);assert.equal(reads,2);
  ctx.verifyFirmwareAfterReconnect=async value=>{assert.equal(value.expected.dVersion,'4.5.0.1');
    assert.equal(value.expected.destination,1);return {state:'reconnected-readback-matches'};};
  verified=await ctx.verifyUsPersistenceAfterPowerCycle({journalStorage,deviceId:'bike-a',
    connection:'persistent-session',powerCycleConfirmed:true});
  assert.equal(verified.state,'US-persistence-verified');assert.equal(verified.persistenceVerified,true);

  const restoration=await ctx.loadFirmwarePair(files());
  const authorization=await ctx.authorizeFirmwarePairTransfer({pair:restoration,
    baseline:baseline(1,'4.5.0.1'),deviceId:'bike-a',journalStorage});
  assert.equal(authorization.bootloaderIdentity.identity,bootloaderIdentity.identity);
  const restorationJournal=await ctx.createFirmwareRecoveryJournal({deviceId:'bike-a',pair:restoration,
    baseline:baseline(1,'4.5.0.1'),identityReference:authorization});
  assert.equal(restorationJournal.pair.source,'restoration');
  assert.equal(restorationJournal.baseline.dVersion,'4.5.0.1');

  const genericStorage=storage();
  const writeCount=writes.length;
  await assert.rejects(ctx.transferFirmwarePair({...options,files:files(),journalStorage:genericStorage}),error=>{
    assert.equal(error.stage,'file-validation');return true;
  });
  assert.equal(genericStorage.values.size,0);assert.equal(writes.length,writeCount);
  restoration.d.data.fill(0);restoration.m.data.fill(0);
  console.log('Motor patch workflow: exact derivation, paired transfer, marker readback, one US write, persistence and stock-restoration lineage passed');
})().catch(error=>{console.error(error);process.exit(1);});
