const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const {webcrypto,createHash}=require('node:crypto');
const code=fs.readFileSync(__dirname+'/../index.html','utf8').split('// BEGIN FIRMWARE PACKET ENCODERS')[1].split('// END FIRMWARE FILE CHECKS')[0];
const salt=new Uint8Array(16).fill(7),serial=Uint8Array.of(1,2,3,4,5,6);
const identity=createHash('sha256').update(salt).update(serial).digest('hex');
async function run({fail=-1,silent=-1,truncated=-1,family=34,otherSerial=false,dVersion=[0x43,0,0],mVersion=[0x42,1,0],destination=1,sameSession=false,mutate=false}={}){
 let now=0,id=0,listener,result,error;const timers=new Map(),calls=[];
 const ctx=vm.createContext({Uint8Array,Error,AbortController,crypto:webcrypto,setTimeout(fn,ms){const key=++id;timers.set(key,{fn,at:now+ms});return key;},clearTimeout(key){timers.delete(key);}});vm.runInContext(code,ctx);
 const expected={identity,dVersion:'4.3.0.0',mVersion:'4.2.1.0',destination:1};
 const replies=[[0,1,30,family,0],[0,1,62,...(otherSerial?[6,5,4,3,2,1]:serial)],[0,1,134,...dVersion],[0,1,134,...mVersion],[0,22,174,1,destination]];
 const packets=[[0,1,28,0],[0,1,60,0],[0,1,132,0],[0,1,132,1],[0,22,172,1]];
 const writer=ctx.createFirmwareGattWriter({'2afe':{async writeValueWithResponse(bytes){
  const n=calls.length;calls.push([...bytes]);assert.deepEqual([...bytes],packets[n]);
  if(mutate){expected.identity='0'.repeat(64);expected.destination=0;}
  if(n!==silent)listener(Uint8Array.from(n===truncated?replies[n].slice(0,-1):replies[n]));
  if(n===fail)throw new Error('ATT failed after reply');
 }}});
 const connection={},previousConnection=sameSession?connection:{};
 const promise=ctx.verifyFirmwareAfterReconnect({expected,connection,previousConnection,identitySalt:salt,
  write:writer.write,subscribe(fn){assert.equal(listener,undefined);listener=fn;return()=>listener=undefined;}}).then(r=>result=r,e=>error=e);
 // listener starts undefined to make cleanup assertions exact.
 for(let i=0;i<40&&!result&&!error;i++){
  await new Promise(setImmediate);if(result||error)break;
  if(!timers.size)continue;
  now=Math.min(...[...timers.values()].map(t=>t.at));for(const [key,t]of[...timers])if(t.at<=now){timers.delete(key);t.fn();}
 }
 await promise;assert.equal(timers.size,0);assert.equal(listener,undefined);
 return {ctx,result,error,calls};
}
(async()=>{
 for(const mutate of [false,true]){
  const r=await run({mutate});assert(!r.error);assert.equal(r.result.state,'reconnected-readback-matches');assert.equal(r.calls.length,5);
  assert.equal(r.result.persistenceVerified,false);assert.equal(r.result.powerCycleVerified,false);assert(!JSON.stringify(r.result).includes(identity));
 }
 for(const changes of [{destination:0},{dVersion:[0x45,0,0]},{mVersion:[0x44,8,0]},{otherSerial:true}]){
  const r=await run(changes);assert(!r.error);assert.equal(r.result.state,'reconnected-readback-mismatch');
  if(changes.otherSerial){assert.equal(r.result.firmwareReadbackMatches,false);assert.equal(r.result.regionReadbackMatches,false);}
 }
 for(let n=0;n<5;n++)for(const type of ['fail','silent','truncated']){
  const r=await run({[type]:n});assert(r.error);assert.equal(r.calls.length,n+1);
 }
 let r=await run({sameSession:true});assert(r.error);assert.equal(r.calls.length,0);
 r=await run({family:35});assert(r.error);assert.equal(r.calls.length,1);
 console.log('Readback: same-motor identity, native D/M and region matching, immutable expectation, new-session requirement, all read failures/timeouts, no persistence claim passed');
})().catch(e=>{console.error(e);process.exit(1);});
