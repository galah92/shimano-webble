const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const {webcrypto,createHash}=require('node:crypto');
const html=fs.readFileSync(require('node:path').join(__dirname,'../index.html'),'utf8');
const code=html.split('// BEGIN FIRMWARE PACKET ENCODERS')[1].split('// END FIRMWARE FILE CHECKS')[0];
const flush=async()=>{for(let i=0;i<150;i++)await Promise.resolve();};
async function run({family=34,unit=0,fail=-1,reject=-1,invalid=false,wrongSerial=false,missingReference=false}={}){
 let now=0,id=0,listener=null,result,error,block=0;
 const timers=new Map(),writes=[],data=new Uint8Array(256);
 data.fill(255,0,16);data.set([0x43,0,0],16);data.set([34,0,4,0],40);data.set([0x42,0,0],47);
 if(invalid)data[40]=35;
 const original=data.slice(),ctx=vm.createContext({Uint8Array,Error,crypto:webcrypto,setTimeout(fn,ms){const key=++id;timers.set(key,{fn,at:now+ms});return key;},clearTimeout(key){timers.delete(key);}});
 vm.runInContext(code,ctx);
 const replies={46:[58],47:[59],48:[60,family,unit],41:[53,wrongSerial?8:9,8,7],42:[54,6,5,4]};
 const expectedBootloaderIdentity={version:1,family:34,unit:0,identity:createHash('sha256').update(Uint8Array.of(68,66,76,49,...new Uint8Array(16).fill(7),34,0,9,8,7,6,5,4)).digest('hex')};
 ctx.transferDComponent({data,expectedBootloaderIdentity:missingReference?null:expectedBootloaderIdentity,identitySalt:new Uint8Array(16).fill(7),subscribe(fn){assert.equal(listener,null);listener=fn;return()=>listener=null;},
  async write(packet){
   const p=[...packet],index=writes.length;writes.push(p);data.fill(0);
   if(index===fail)throw new Error('ATT failure');
   if(p[0]===136){
    if(replies[p[1]])listener(Uint8Array.of(136,...replies[p[1]]));
    else listener(Uint8Array.of(136,index===reject?50:49,0,0));
   }else if(p[2]===3){const n=++block;listener(Uint8Array.of(11,0,192,p[3]));listener(Uint8Array.of(136,49,n,0));}
  }
 }).then(r=>result=r,e=>error=e);
 for(let i=0;i<1000&&!result&&!error;i++){
  await flush();await new Promise(setImmediate);if(result||error)break;
  if(!timers.size)continue;now=Math.min(...[...timers.values()].map(t=>t.at));
  for(const [key,t]of[...timers])if(t.at<=now){timers.delete(key);t.fn();}
 }
 await flush();assert(result||error);assert.equal(timers.size,0);assert.equal(listener,null);
 return {writes,result,error,original};
}
(async()=>{
 let s=await run();assert.equal(s.error,undefined);assert.equal(s.result.finished,true);assert.equal(s.result.reset,false);assert.equal(s.result.installable,false);
 assert.equal(s.result.family,34);assert.equal(s.result.unit,0);assert.equal('serial' in s.result,false);
 assert.deepEqual(s.writes.slice(0,9),[
  [136,46,0,0,0],[136,47,0,0,0],[136,48,0,0,0],[136,41,0,0,0],[136,42,0,0,0],
  [136,6,34,0,0],[136,7,9,8,0],[136,8,7,6,0],[136,9,5,4,0]
 ]);
 assert.equal(s.writes.length,21);
 assert.deepEqual(s.writes[20],[136,39,s.original.reduce((a,b)=>a+b,0)&255,0,0]);
 assert.deepEqual(s.writes[12].slice(4,68),[...s.original.slice(0,64)]);
 for(let fail=0;fail<21;fail++){s=await run({fail});assert(s.error);assert.equal(s.result,undefined);assert.equal(s.writes.length,fail+1);}
 for(const reject of [5,6,7,8]){s=await run({reject});assert(s.error);assert.equal(s.writes.length,reject+1);}
 for(const mismatch of [{family:35},{unit:1}]){s=await run(mismatch);assert.match(s.error.message,/identity does not match/);assert.equal(s.writes.length,5);}
 s=await run({wrongSerial:true});assert.match(s.error.message,/recorded motor/);assert.equal(s.writes.length,5);
 s=await run({missingReference:true});assert(s.error);assert.equal(s.writes.length,0);
 s=await run({invalid:true});assert(s.error);assert.equal(s.writes.length,0);
 console.log('D component identity/setup/data/finish ordering, snapshot, mismatch and all-stage failure tests passed');
})().catch(e=>{console.error(e);process.exit(1);});
