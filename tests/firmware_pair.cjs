// Orchestration tests use controlled component workers. Their wire protocols
// are independently exercised by entry, component and GATT suites.
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const {webcrypto,createHash}=require('node:crypto');
const rawCode=fs.readFileSync(__dirname+'/../index.html','utf8').split('// BEGIN FIRMWARE PACKET ENCODERS')[1].split('// END FIRMWARE FILE CHECKS')[0];
const d=new Uint8Array(256),m=new Uint8Array(256);
d.fill(255,0,16);d.set([0x43,0,0],16);d.set([34,0,4],40);d.set([0x42,0,0],47);
m.set([255,255,34,0],12);m.set([0x42,1,0],8);m.set([0x42,0,0],16);
const hash=b=>createHash('sha256').update(b).digest('hex');
// Only the test VM trusts synthetic images; deployed allowlist is unchanged.
const code=rawCode.replace('const FIRMWARE_IMAGES = Object.freeze({',`const FIRMWARE_IMAGES = Object.freeze({'${hash(d)}':'preparation','${hash(m)}':'preparation',`);
const identityReference=()=>({version:1,verified:true,expected:{identity:'a'.repeat(64)},salt:'07'.repeat(16),bootloaderIdentity:{version:1,family:34,unit:0,identity:createHash('sha256').update(Uint8Array.of(68,66,76,49,...new Uint8Array(16).fill(7),34,0,9,8,7,6,5,4)).digest('hex')}});
const file=b=>({size:b.length,arrayBuffer:async()=>b.buffer});
function fixture(fail){
 const ctx=vm.createContext({Uint8Array,Error,WeakSet,AbortController,crypto:webcrypto,setTimeout,clearTimeout});vm.runInContext(code,ctx);
 const calls=[],stages=[],writes=[],di=d.slice(),mi=m.slice(),keys=new Uint8Array(15).fill(7),controller=new AbortController();
 const native={async writeValueWithResponse(p){writes.push([...p]);},async writeValueWithoutResponse(p){writes.push([...p]);}};
 const options={files:[file(mi),file(di)],identityReference:identityReference(),baseline:{identity:'a'.repeat(64),family:34,unit:0,dVersion:'4.5.0.0',mVersion:'4.4.8.0'},credentials:keys,
  characteristics:{'2afa':native,'2afe':native},subscribe(){throw Error('Controlled workers do not subscribe');},signal:controller.signal,
  onStage(stage){stages.push(stage);if(stage==='M-update-entry'){di.fill(0);mi.fill(0);keys.fill(0);options.identityReference.bootloaderIdentity.identity='c'.repeat(64);options.identityReference.salt='09'.repeat(16);}}};
 let entries=0;
 const record=name=>{calls.push(name);if(name===fail)throw new Error('private payload must not appear');};
 ctx.enterFirmwareUpdateSession=async t=>{const n=++entries;record('entry'+n);await t.write('2afa',Uint8Array.of(4));return {mode:0,targetSelector:n===1?13:0};};
 ctx.selectMFirmwareSlot=async()=>record('slot');
 ctx.transferMFirmware=async o=>{record('M');assert.deepEqual([...o.data],[...m]);assert.equal(o.targetSelector,13);assert.equal(o.nextSequence(),0);assert.equal(o.nextSequence(),1);};
 ctx.enterDBootloader=async o=>{record('Dentry');assert.equal(o.targetSelector,0);assert.deepEqual([...o.credentials],new Array(15).fill(7));};
 ctx.transferDComponent=async o=>{record('D');assert.equal(o.expectedBootloaderIdentity.identity,identityReference().bootloaderIdentity.identity);assert.deepEqual([...o.identitySalt],new Array(16).fill(7));assert.deepEqual([...o.data],[...d]);await o.write(Uint8Array.of(136,46,0,0,0));};
 return {ctx,options,calls,stages,writes,controller};
}
(async()=>{
 let f=fixture(),result=await f.ctx.transferFirmwarePair(f.options);
 assert.deepEqual(f.calls,['entry1','slot','M','entry2','Dentry','D']);
 assert.deepEqual(f.writes,[[0,4],[0,4],[0,136,46,0,0,0]]);
 assert.equal(result.mFinished,true);assert.equal(result.dFinished,true);assert.equal(result.firmwareVerified,false);assert.equal(result.reset,false);
 for(const fail of ['entry1','slot','M','entry2','Dentry','D']){
  f=fixture(fail);await assert.rejects(f.ctx.transferFirmwarePair(f.options),e=>{
   assert.equal(e.mFinished,['entry2','Dentry','D'].includes(fail));assert.equal(e.dFinished,false);assert.equal(e.reset,false);
   assert(!e.message.includes('private payload'));return true;
  });assert.equal(f.calls.at(-1),fail);
 }
 for(const change of [o=>o.files=[file(d),file(d)],o=>o.files=[file(d),file(new Uint8Array(256))],o=>o.baseline.family=35,o=>delete o.identityReference,o=>o.identityReference.verified=false,o=>delete o.identityReference.bootloaderIdentity,o=>o.identityReference.expected.identity='c'.repeat(64),o=>o.identityReference.salt='bad',o=>o.credentials=new Uint8Array(14),o=>delete o.characteristics['2afe']]){
  f=fixture();change(f.options);await assert.rejects(f.ctx.transferFirmwarePair(f.options));assert.equal(f.calls.length,0);assert.equal(f.writes.length,0);
 }
 f=fixture();f.controller.abort();await assert.rejects(f.ctx.transferFirmwarePair(f.options));assert.equal(f.calls.length,0);
 f=fixture();let release;const gate=new Promise(r=>release=r);const original=f.options.files[0].arrayBuffer;
 f.options.files[0].arrayBuffer=async()=>{await gate;return original();};
 const pending=f.ctx.transferFirmwarePair(f.options);
 await assert.rejects(f.ctx.transferFirmwarePair(f.options),/already active/);release();await pending;
 // Real allowlist rejects the very same synthetic pair before any worker runs.
 const real=vm.createContext({Uint8Array,crypto:webcrypto});vm.runInContext(rawCode,real);
 await assert.rejects(real.loadFirmwarePair([file(d),file(m)]),/reviewed/);
 console.log('Paired orchestration: file validation, snapshots, M-to-D order, new routing, partial completion, no reset, transport ownership and failures passed');
})().catch(e=>{console.error(e);process.exit(1);});
