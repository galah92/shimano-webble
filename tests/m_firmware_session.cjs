const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const html=fs.readFileSync(require('node:path').join(__dirname,'../index.html'),'utf8');
const code=html.split('// BEGIN FIRMWARE PACKET ENCODERS')[1].split('// END M FIRMWARE SESSION')[0];
const flush=async()=>{for(let i=0;i<100;i++)await Promise.resolve();};
async function run({selector=1,version=[0x20,2,0],fail=-1}={}){
 let now=0,id=0,seq=0,listener=null,result,error;
 const timers=new Map(),writes=[],data=new Uint8Array(65).fill(5),controller=new AbortController();
 const ctx=vm.createContext({Uint8Array,Error,setTimeout(fn,ms){const key=++id;timers.set(key,{fn,at:now+ms});return key;},clearTimeout(key){timers.delete(key);}});
 vm.runInContext(code,ctx);
 ctx.transferMFirmware({data,targetSelector:selector,nextSequence:()=>seq++&255,signal:controller.signal,
  subscribe(fn){assert.equal(listener,null);listener=fn;return()=>listener=null;},
  async write(characteristic,packet){
   const p=[...packet],index=writes.length;writes.push({characteristic,packet:p,at:now});data.fill(0);
   if(index===fail)throw new Error(`ATT failure ${index}`);
   if(p[1]===240){
    if(p[3]===65)listener(Uint8Array.of(242,0,81,...version));
    else listener(Uint8Array.of(242,0,49));
   }else if(p[2]===4)listener(Uint8Array.of(11,0,132,0));
   else if(p[2]===3){
    listener(Uint8Array.of(11,0,192,p[3]));
    if(p[3]===2)listener(Uint8Array.of(242,0,49));
   }
  }
 }).then(r=>result=r,e=>error=e);
 for(let i=0;i<100&&!result&&!error;i++){
  await flush();if(result||error)break;
  assert(timers.size);now=Math.min(...[...timers.values()].map(t=>t.at));
  for(const [key,t]of[...timers])if(t.at<=now){timers.delete(key);t.fn();}
 }
 await flush();assert(result||error);assert.equal(timers.size,0);assert.equal(listener,null);
 return {ctx,writes,result,error};
}
(async()=>{
 for(const selector of [0,1])for(const [version,mode]of [[[0x20,1,255],2],[[0x20,2,0],2],[[0x20,2,1],1],[[0x21,0,0],1]]){
  const {writes,result,error}=await run({selector,version});assert.equal(error,undefined);
  assert.equal(result.mode,mode);assert.equal(result.finished,true);assert.equal(result.reset,false);assert.equal(result.installable,false);
  assert.equal(writes.length,10);
  const prefix=selector===0?19:0,characteristic=selector===0?'2afa':'2afe';
  assert.deepEqual(writes.slice(0,5).map(w=>[w.characteristic,w.packet]),[
   [characteristic,[prefix,240,0,65,0,0,0]],
   [characteristic,[prefix,240,0,33,0,14,0]],
   ['2afa',[11,0,4,mode]],
   [characteristic,[prefix,240,0,36,0,0,252]],
   [characteristic,[prefix,240,0,38,0,0,0]],
  ]);
  assert.equal(writes[5].at-writes[4].at,150);
  assert(writes[5].packet.slice(4,68).every(b=>b===5));
  assert.deepEqual(writes[7].packet.slice(4,68),[5,...Array(63).fill(0)]);
  assert.deepEqual(writes[9].packet,[prefix,240,0,39,69,0,0]); // 65*5 mod256
  assert(writes.slice(5,9).every(w=>w.characteristic==='2afa'));
 }
 for(let fail=0;fail<10;fail++){
  const {writes,error,result}=await run({fail});assert(error);assert.equal(result,undefined);assert.equal(writes.length,fail+1);
 }
 const {ctx}=await run(),match=ctx.mBootloaderVersionMatch;
 assert.equal(match(Uint8Array.of(242,0,81,32,2)).error,'Truncated M bootloader version');
 assert.match(match(Uint8Array.of(242,0,81,32,2,1,242,7,50,58)).error,/rejected; code 58/);
 assert.equal(match(Uint8Array.of(242,7,81,32,2,1)).mode,1);
 assert.equal(match(Uint8Array.of(242,0,49)),null);
 console.log('M setup/data/finish integration, bootloader mode threshold, routing and fail-stop tests passed');
})().catch(e=>{console.error(e);process.exit(1);});
