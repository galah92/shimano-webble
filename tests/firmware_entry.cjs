const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const html=fs.readFileSync(__dirname+'/../index.html','utf8');
const code=html.split('// BEGIN FIRMWARE PACKET ENCODERS')[1].split('// END FIRMWARE UPDATE ENTRY')[0];
const flush=async()=>{for(let i=0;i<120;i++)await Promise.resolve();};
async function run({selector=13,mode=0,fail=-1,reject=false,wrongMode=false,abort=false,silent=-1,badSlot=false,leadingZero=false,recoveryInstall=false}={}){
 let now=0,id=0,listener=null,result,error;const timers=new Map(),calls=[];
 const controller=new AbortController();
 const ctx=vm.createContext({Uint8Array,Error,AbortController,setTimeout(fn,ms){const key=++id;timers.set(key,{fn,at:now+ms});return key;},clearTimeout(key){timers.delete(key);}});
 vm.runInContext(code,ctx);
 const native=name=>({async writeValueWithResponse(bytes){
  const p=[...bytes],n=calls.length;calls.push({name,p,at:now});
  if(n===fail)throw new Error('native failure');
  if(n===silent)return;
  if(abort&&n===1){controller.abort();return;}
  if(n===0)listener(Uint8Array.of(0x24,128|mode|selector));
  if(n===1)listener(Uint8Array.of(0x23,0));
  if(n===2)listener(Uint8Array.of(0x24,128|mode|selector|(wrongMode?64:0)));
  if(n===3 && !(recoveryInstall===true&&mode===32&&selector===0))listener(Uint8Array.of(...(leadingZero?[0]:[]),0x32,reject?0x23:0x22,1));
  if(n===(recoveryInstall===true&&mode===32&&selector===0?3:4))listener(Uint8Array.of(0x26,badSlot?1:0));
 }});
 const writer=ctx.createFirmwareGattWriter({'2afa':native('2afa'),'2afe':native('2afe')},controller.signal);
 const transport={write:writer.write,recoveryInstall,signal:controller.signal,subscribe(fn){assert(!listener);listener=fn;return()=>listener=null;}};
 const pending=(async()=>{const entry=await ctx.enterFirmwareUpdateSession(transport);await ctx.selectMFirmwareSlot(transport);return entry;})().then(r=>result=r,e=>error=e);
 for(let i=0;i<40&&!result&&!error;i++){
  await flush();if(result||error)break;
  assert(timers.size);now=Math.min(...[...timers.values()].map(t=>t.at));
  for(const [key,t]of[...timers])if(t.at<=now){timers.delete(key);t.fn();}
 }
 await pending;assert.equal(listener,null);assert.equal(timers.size,0);
 return {ctx,result,error,calls,now};
}
(async()=>{
 for(const leadingZero of [false,true])for(const selector of [0,13,31])for(const mode of [0,32]){
  const {result,error,calls}=await run({selector,mode,leadingZero});assert(!error);
  assert.equal(result.targetSelector,selector);assert.equal(result.mode,mode);assert.equal(result.bootloaderVerified,false);
  assert.deepEqual(calls.map(c=>c.p),[[0,4],[0,3,mode],[0,4],selector===0?[0,19,50,32,1]:[0,50,32,1],[0,6,0]]);
  assert.equal(calls[3].name,selector===0?'2afa':'2afe');assert.equal(calls[2].at,1000);assert.equal(calls[4].at,3000);
 }
 for(const selector of [0,13,31])for(const mode of [0,32]){
  const r=await run({selector,mode,recoveryInstall:true});assert(!r.error);
  const skipped=mode===32&&selector===0;
  assert.equal(r.result.pcaSkipped,skipped);assert.equal(r.calls.length,skipped?4:5);
  if(skipped){assert.deepEqual(r.calls.map(c=>c.p),[[0,4],[0,3,32],[0,4],[0,6,0]]);assert.equal(r.calls[3].at,3000);}
 }
 const invalid=await run({recoveryInstall:'true'});assert(invalid.error);assert.equal(invalid.calls.length,0);
 for(let fail=0;fail<5;fail++){const r=await run({fail});assert(r.error);assert.equal(r.calls.length,fail+1);}
 for(let silent=0;silent<5;silent++){const r=await run({silent});assert(r.error);assert.equal(r.calls.length,silent+1);assert.equal(r.now-r.calls[silent].at,silent===3?6000:3000);}
 const bad=await run({badSlot:true});assert(bad.error);assert.equal(bad.now,6000);
 for(const option of [{reject:true},{wrongMode:true},{abort:true}]){const r=await run(option);assert(r.error);assert(r.calls.length<5);}
 const {ctx}=await run();
 for(const prefix of [[50],[0,50],[72,50],[72,7,50],[0,72,7,50]]){
  assert.equal(ctx.firmwareUpdateReply(Uint8Array.from([...prefix,34,1])).accepted,true);
  for(const suffix of [[34],[34,0],[35,1]])assert(ctx.firmwareUpdateReply(Uint8Array.from([...prefix,...suffix])).error);
 }
 for(const p of [[],[1,50,34,1],[50,33,1]])assert.equal(ctx.firmwareUpdateReply(Uint8Array.from(p)),null);
 assert.equal(ctx.firmwareBridgeStatus(Uint8Array.of(0,36,141)),141);
 assert.equal(ctx.firmwareBridgeStatus(Uint8Array.of(141)),141);
 assert.equal(ctx.firmwareBridgeStatus(Uint8Array.of(36)),null);
 console.log('Update entry and M slot selection: physical ATT framing, modes/routes, required success value, deadlines and all-stage failure tests passed');
})().catch(e=>{console.error(e);process.exit(1);});
