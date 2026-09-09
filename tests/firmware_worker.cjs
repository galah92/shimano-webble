const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const html=fs.readFileSync(require('node:path').join(__dirname,'../index.html'),'utf8');
const code=html.split('// BEGIN FIRMWARE PACKET ENCODERS')[1].split('// END M FIRMWARE BLOCK WORKER')[0];
const flush=async()=>{for(let i=0;i<10;i++)await Promise.resolve();};
async function scenario(replies,{dataFailure=false,hung=false,abortRetry=false,mutate=false}={}) {
 let now=0,id=0,listener=null,seq=254,queries=0,removed=0,result,error;
 const timers=new Map(),writes=[],controller=new AbortController(),data=new Uint8Array(65).fill(5);
 const ctx=vm.createContext({Uint8Array,Error,setTimeout(fn,ms){const key=++id;timers.set(key,{fn,at:now+ms});return key;},clearTimeout(key){timers.delete(key);}});
 vm.runInContext(code,ctx);
 ctx.sendMFirmwareBlock({data,offset:0,nextSequence:()=>{const n=seq;seq=(seq+1)&255;return n;},signal:controller.signal,
  subscribe(fn){listener=fn;return()=>{listener=null;removed++;};},
  write(packet){writes.push({at:now,bytes:[...packet]});
    if(packet[2]!==3){if(mutate)data.fill(9);if(dataFailure)return Promise.reject(undefined);if(hung)return new Promise(()=>{});return Promise.resolve();}
    const reply=replies[queries++];
    if(reply==='ack')listener(Uint8Array.of(11,0,192,packet[3]));
    else if(typeof reply==='number')listener(Uint8Array.of(11,0,131,packet[1],reply));
    return Promise.resolve();}
 }).then(r=>result=r,e=>error=e);
 for(let i=0;i<30&&!result&&!error;i++) {
  await flush();
  if(abortRetry&&queries===1){controller.abort();await flush();break;}
  if(result||error)break;
  assert(timers.size,'pending worker must have a timer');
  now=Math.min(...[...timers.values()].map(t=>t.at));
  for(const [key,t] of [...timers])if(t.at<=now){timers.delete(key);t.fn();}
 }
 await flush();assert(result||error);assert.equal(timers.size,0);assert.equal(listener,null);
 return {result,error,writes,removed};
}
(async()=>{
 let s=await scenario(['ack']);assert.equal(s.result.attempts,1);assert.deepEqual(s.writes.map(w=>[w.at,w.bytes[1],w.bytes[2]]),[[0,254,17],[15,255,3]]);
 s=await scenario([1,1,'ack'],{mutate:true});assert.equal(s.result.attempts,3);assert.equal(s.removed,3);
 assert.deepEqual(s.writes.map(w=>[w.at,w.bytes[1],w.bytes[2]]),[[0,254,17],[15,255,3],[415,0,17],[430,1,3],[830,2,17],[845,3,3]]);
 for(const w of s.writes.filter(w=>w.bytes[2]!==3))assert(w.bytes.slice(4,68).every(b=>b===5),'retry bytes must be snapshotted');
 s=await scenario([1,1,1]);assert.match(s.error.message,/query-status-1/);assert.equal(s.writes.length,6);
 s=await scenario([2]);assert.match(s.error.message,/query-status-2/);assert.equal(s.writes.length,2);
 s=await scenario([]);assert.match(s.error.message,/reply timed out/);assert.equal(s.writes.length,2);
 s=await scenario([],{dataFailure:true});assert(s.error);assert.equal(s.writes.length,1);
 s=await scenario([],{hung:true});assert.match(s.error.message,/ATT write timed out/);assert.equal(s.writes.length,1);
 s=await scenario([1,'ack'],{abortRetry:true});assert.match(s.error.message,/aborted/);assert.equal(s.writes.length,2);
 console.log('M worker attempt limit, sequence wrap, delays, snapshot, abort and no uncertain rewrite tests passed');
})().catch(e=>{console.error(e);process.exit(1);});
