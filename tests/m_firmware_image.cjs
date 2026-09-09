const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const html=fs.readFileSync(require('node:path').join(__dirname,'../index.html'),'utf8');
const code=html.split('// BEGIN FIRMWARE PACKET ENCODERS')[1].split('// END M FIRMWARE IMAGE WORKER')[0];
const flush=async()=>{for(let i=0;i<24;i++)await Promise.resolve();};
async function run(length, failure) {
 let now=0,id=0,seq=254,listener=null,block=0,attempts=0,queries=0,result,error,lastData;
 const timers=new Map(),writes=[],controller=new AbortController();
 const data=Uint8Array.from({length},(_,i)=>(i*7+5)&255),original=data.slice();
 const ctx=vm.createContext({Uint8Array,Error,setTimeout(fn,ms){const key=++id;timers.set(key,{fn,at:now+ms});return key;},clearTimeout(key){timers.delete(key);}});
 vm.runInContext(code,ctx);
 ctx.sendMFirmwareImage({data,signal:controller.signal,nextSequence(){const n=seq;seq=(seq+1)&255;return n;},
  subscribe(fn){assert.equal(listener,null);listener=fn;return()=>listener=null;},
  async write(packet){
   const p=[...packet];writes.push({at:now,bytes:p});
   if(p[2]!==3){
    data.fill(0); // Neither a later block nor a retry may observe caller mutation.
    attempts++;lastData=p[1];
    assert.equal(p[1],(254+(attempts-1)*2)&255);
    const offset=block*64,end=Math.min(length,offset+64),checkpoint=end===length||end%1024===0;
    assert.equal(p[2],checkpoint?18:17);assert.equal(p.length,checkpoint?71:68);
    assert.deepEqual(p.slice(4,68),Array.from({length:64},(_,i)=>original[offset+i]??0));
    if(checkpoint)assert.equal(p[68],original.slice(Math.floor(offset/1024)*1024,end).reduce((a,b)=>a+b,0)&255);
    if(failure==='data'&&block===16)throw new Error('uncertain ATT');
    if(failure==='abort'&&block===16)controller.abort();
   } else {
    queries++;assert.deepEqual(p,[11,(lastData+1)&255,3,lastData]);
    assert.equal(now-writes[writes.length-2].at,15);
    if(failure==='retry'&&block===15&&queries===16){listener(Uint8Array.of(11,0,131,p[1],1));return;}
    listener(Uint8Array.of(11,0,192,lastData));
    const end=Math.min(length,(block+1)*64);
    if(end===length||end%1024===0){
     if(failure==='missing-checksum'&&block===15)return;
     listener(Uint8Array.of(242,0,failure==='checksum'&&block===15?50:49));
    }
    block++;
   }
  }
 }).then(r=>result=r,e=>error=e);
 for(let step=0;step<20000&&!result&&!error;step++){
  await flush();if(result||error)break;
  assert(timers.size,'pending operation must have a timer');
  now=Math.min(...[...timers.values()].map(t=>t.at));
  for(const [key,t]of[...timers])if(t.at<=now){timers.delete(key);t.fn();}
 }
 await flush();assert(result||error);assert.equal(timers.size,0);assert.equal(listener,null);
 return {result,error,writes,original};
}
(async()=>{
 for(const length of [1,64,65,1024,1025,116320,119824,262144]){
  const s=await run(length);assert.equal(s.error,undefined);
  assert.equal(s.result.blocks,Math.ceil(length/64));assert.equal(s.result.checkpoints,Math.ceil(length/1024));
  assert.equal(s.result.checksum,s.original.reduce((a,b)=>a+b,0)&255);
  assert.equal(s.result.attempts,s.result.blocks);assert.equal(s.writes.length,s.result.blocks*2);
  assert.equal(s.result.installable,false);assert.equal(s.result.finished,false);assert.equal(s.result.reset,false);
 }
 let s=await run(2049,'retry');assert.equal(s.result.attempts,34);
 assert.equal(s.writes[32].at-s.writes[31].at,400);
 for(const failure of ['checksum','missing-checksum','data','abort']){
  s=await run(2049,failure);assert(s.error,failure);
  assert.equal(s.writes.length,failure==='data'||failure==='abort'?33:32);
 }
 for(const length of [0,262145]){s=await run(length);assert(s.error);assert.equal(s.writes.length,0);}
 console.log('M full-image checksum windows, sequence wrap, padding, retry and failure-stop tests passed');
})().catch(e=>{console.error(e);process.exit(1);});
