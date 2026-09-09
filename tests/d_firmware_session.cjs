const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const html=fs.readFileSync(require('node:path').join(__dirname,'../index.html'),'utf8');
const code=html.split('// BEGIN FIRMWARE PACKET ENCODERS')[1].split('// END D FIRMWARE SESSION')[0];
const flush=async()=>{for(let i=0;i<100;i++)await Promise.resolve();};
async function run({fail=-1,rejectFinish=false,abortDelay=false,resetOnly=false}={}){
 let now=0,id=0,listener=null,result,error,block=0;
 const timers=new Map(),writes=[],controller=new AbortController(),data=new Uint8Array(65).fill(5);
 const ctx=vm.createContext({Uint8Array,Error,setTimeout(fn,ms){const key=++id;timers.set(key,{fn,at:now+ms});return key;},clearTimeout(key){timers.delete(key);}});
 vm.runInContext(code,ctx);
 const transport={signal:controller.signal,
  subscribe(fn){assert.equal(listener,null);listener=fn;return()=>listener=null;},
  async write(packet){
   const p=[...packet],index=writes.length;writes.push({packet:p,at:now});data.fill(0);
   if(index===fail)throw new Error('uncertain ATT');
   if(resetOnly)return;
   if(p[0]===136)listener(Uint8Array.of(136,p[1]===39&&rejectFinish?50:49,0,0));
   else if(p[2]===3){const n=++block;listener(Uint8Array.of(11,0,192,p[3]));listener(Uint8Array.of(136,49,n,0));}
  }};
 const promise=resetOnly?ctx.requestDFirmwareReset(transport):ctx.transferDFirmware({data,...transport});
 promise.then(r=>result=r,e=>error=e);
 for(let i=0;i<30&&!result&&!error;i++){
  await flush();if(result||error)break;
  if(abortDelay&&writes.length===8){controller.abort();await flush();break;}
  assert(timers.size);now=Math.min(...[...timers.values()].map(t=>t.at));
  for(const [key,t]of[...timers])if(t.at<=now){timers.delete(key);t.fn();}
 }
 await flush();assert(result||error);assert.equal(timers.size,0);assert.equal(listener,null);
 return {writes,result,error,now};
}
(async()=>{
 let s=await run();assert.equal(s.error,undefined);assert.equal(s.result.state,'D-transfer-finished');
 assert.equal(s.result.finished,true);assert.equal(s.result.reset,false);assert.equal(s.result.installable,false);
 assert.equal(s.writes.length,8);assert.deepEqual(s.writes[7].packet,[136,39,69,0,0]);
 assert.equal(s.now-s.writes[7].at,1000);assert(s.writes[3].packet.slice(4,68).every(b=>b===5));
 assert.deepEqual(s.writes[5].packet.slice(4,68),[5,...Array(63).fill(255)]);
 assert(!s.writes.some(w=>w.packet[0]===136&&w.packet[1]===40));
 for(let fail=0;fail<8;fail++){s=await run({fail});assert(s.error);assert.equal(s.result,undefined);assert.equal(s.writes.length,fail+1);}
 s=await run({rejectFinish:true});assert(s.error);assert.equal(s.writes.length,8);assert.equal(s.now,0);
 s=await run({abortDelay:true});assert.match(s.error.message,/aborted/);assert.equal(s.result,undefined);
 s=await run({resetOnly:true});assert.deepEqual(s.writes.map(w=>w.packet),[[136,40,0,0,0]]);
 assert.equal(s.result.state,'reset-write-completed');assert.equal(s.result.rebootVerified,false);assert.equal(s.result.firmwareVerified,false);
 s=await run({resetOnly:true,fail:0});assert(s.error);assert.equal(s.writes.length,1);assert.equal(s.result,undefined);
 console.log('D setup/data/finish ordering, checksum, finish delay, fail-stop and separate reset semantics passed');
})().catch(e=>{console.error(e);process.exit(1);});
