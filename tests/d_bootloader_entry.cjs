const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const code=fs.readFileSync(__dirname+'/../index.html','utf8').split('// BEGIN FIRMWARE PACKET ENCODERS')[1].split('// END D BOOTLOADER ENTRY')[0];
const flush=async()=>{for(let i=0;i<120;i++)await Promise.resolve();};
async function run({mode=0,selector=13,fail=-1,silent=-1,badStage=false,rejected=false,abortAt=-1,recoveryInstall=false,slotStatus=0}={}){
 let now=0,id=0,listener=null,result,error,selected=31,bridgeMode=mode;
 const diagnostics=[],timers=new Map(),calls=[],credentials=Uint8Array.from({length:15},(_,i)=>i+1),controller=new AbortController();
 const ctx=vm.createContext({Uint8Array,Error,AbortController,setTimeout(fn,ms){const key=++id;timers.set(key,{fn,at:now+ms});return key;},clearTimeout(key){timers.delete(key);}});
 vm.runInContext(code,ctx);
 const writer=ctx.createFirmwareGattWriter({'2afa':{async writeValueWithResponse(bytes){
  const p=[...bytes],n=calls.length;calls.push({p,at:now});credentials.fill(0);
  if(n===fail)throw new Error('native failure');
  if(n===abortAt){controller.abort();return;}
  if(n===silent)return;
  if(p[1]===3){bridgeMode=p[2]&32;listener(Uint8Array.of(35,0));}
  if(p[1]===4)listener(Uint8Array.of(36,192|bridgeMode|selector));
  if(p[1]===6){selected=p[2];listener(Uint8Array.of(38,slotStatus));}
  if(p[1]===136&&listener)listener(rejected?Uint8Array.of(0,136,18):Uint8Array.of(0,136,17,badStage?99:p[2]));
 }}},controller.signal);
 const pending=ctx.enterDBootloader({mode,targetSelector:selector,recoveryInstall,credentials,signal:controller.signal,write:writer.write,
  onDiagnostic(e){diagnostics.push(e);},subscribe(fn){assert(!listener);listener=fn;return()=>listener=null;}}).then(r=>result=r,e=>error=e);
 for(let i=0;i<100&&!result&&!error;i++){
  await flush();if(result||error)break;
  assert(timers.size);now=Math.min(...[...timers.values()].map(t=>t.at));
  for(const [key,t]of[...timers])if(t.at<=now){timers.delete(key);t.fn();}
 }
 await pending;assert.equal(listener,null);assert.equal(timers.size,0);
 return {ctx,calls,result,error,now,diagnostics};
}
(async()=>{
 for(const mode of [0,32])for(const selector of [0,13,31]){
  const r=await run({mode,selector});assert(!r.error);assert.equal(r.result.bootloaderVerified,false);
  const key=n=>[0,136,n,3*n-2,3*n-1,3*n];
  assert.deepEqual(r.calls.map(c=>c.p),[[0,3,64|mode|(mode===0?selector:0)],[0,4],[0,6,31],key(1),key(1),key(1),key(1),[0,6,0],key(1),key(2),key(3),key(4),key(5),[0,3,96],[0,4],[0,6,31],key(5)]);
  assert.equal(r.now,6150);
  assert.deepEqual(r.calls.slice(3,7).map(c=>c.at),[1000,2000,3000,4000]);
 }
 for(const slotStatus of [0,1]) {
  const r=await run({mode:32,selector:0,recoveryInstall:true,slotStatus});assert(!r.error);
  const key=n=>[0,136,n,3*n-2,3*n-1,3*n];
  assert.deepEqual(r.calls.map(c=>c.p),[[0,3,96],[0,4],[0,6,0],key(1),key(2),key(3),key(4),key(5),key(5)]);
  assert.equal(r.now,1250);assert.equal(r.calls[2].at,1100);assert.equal(r.calls[8].at,1250);
  assert.equal(r.result.bootloaderVerified,false);assert.equal(r.result.installable,false);
 }
 for(let n=0;n<9;n++)for(const kind of ['fail','abortAt']) {
  const r=await run({mode:32,selector:0,recoveryInstall:true,[kind]:n});assert(r.error);assert.equal(r.calls.length,n+1);
 }
 for(const n of [0,1,2,3,4,5,6,8]) {
  const r=await run({mode:32,selector:0,recoveryInstall:true,silent:n});assert(r.error);assert.equal(r.calls.length,n+1);
 }
 for(const options of [{mode:0,selector:0},{mode:32,selector:13},{mode:32,selector:0,recoveryInstall:'true'}]){
  const r=await run({recoveryInstall:true,...options});assert(r.error);assert.equal(r.calls.length,0);
 }
 for(const [options,reason] of [
  [{rejected:true},'device-rejected (FIRMUP 12)'],
  [{badStage:true},'FIRMUP stage mismatch: expected 1, received 99'],
  [{silent:3},'reply-timeout'],
  [{fail:3},'transport-or-local-error'],
  [{abortAt:3},'disconnected'],
 ]) {
  const r=await run({mode:32,selector:0,recoveryInstall:true,...options});
  assert(r.error);assert.equal(r.calls.length,4);
  assert.equal(r.diagnostics.at(-1).reason,reason);
  assert(!JSON.stringify(r.diagnostics).includes('native failure'));
 }
 const badRecoverySlot=await run({mode:32,selector:0,recoveryInstall:true,slotStatus:2});assert(badRecoverySlot.error);assert.equal(badRecoverySlot.calls.length,3);
 for(let fail=0;fail<17;fail++){const r=await run({fail});assert(r.error);assert.equal(r.calls.length,fail+1);}
 for(let abortAt=0;abortAt<17;abortAt++){const r=await run({abortAt});assert(r.error);assert.equal(r.calls.length,abortAt+1);}
 for(const silent of [0,1,2,7,8,9,10,11,13,14,15,16]){
  const r=await run({silent});assert(r.error);assert.equal(r.calls.length,silent+1);
  assert.equal(r.now-r.calls[silent].at,[8,9,10,11,16].includes(silent)?2000:3000);
 }
 const bad=await run({badStage:true});assert(bad.error);assert.equal(bad.calls.length,9);
 const {ctx}=await run();
 for(const prefix of [[],[0],[136],[0,136]]){
  assert.equal(ctx.dFirmupReply(Uint8Array.from([...prefix,17,3]),3).accepted,true);
  for(const suffix of [[17],[17,2],[18]])assert(ctx.dFirmupReply(Uint8Array.from([...prefix,...suffix]),3).error);
 }
 assert.equal(ctx.dFirmupReply(Uint8Array.of(3,136,17,3),3),null);
 for(const overrides of [{mode:64},{targetSelector:32},{credentials:new Uint8Array(14)}]){
  await assert.rejects(ctx.enterDBootloader({mode:0,targetSelector:13,credentials:new Uint8Array(15),...overrides}));
 }
 console.log('D entry: complete 17-write physical sequence, mode/selector matrix, timing, credential snapshot, every-stage failure/abort and reply deadlines passed');
})().catch(e=>{console.error(e);process.exit(1);});
