const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const html=fs.readFileSync(require('node:path').join(__dirname,'../index.html'),'utf8');
const code=html.split('// BEGIN FIRMWARE PACKET ENCODERS')[1].split('// END FIRMWARE FILE CHECKS')[0];
const flush=async()=>{for(let i=0;i<50;i++)await Promise.resolve();};
async function run({fail=-1,truncate=-1,prefix=true}={}){
 let now=0,id=0,listener=null,result,error;
 const timers=new Map(),writes=[];
 const ctx=vm.createContext({Uint8Array,Error,setTimeout(fn,ms){const key=++id;timers.set(key,{fn,at:now+ms});return key;},clearTimeout(key){timers.delete(key);}});
 vm.runInContext(code,ctx);
 const replies=[[58,1,2,3],[59,4,5,6],[60,34,0],[53,9,8,7],[54,6,5,4]];
 ctx.queryDBootloaderIdentity({subscribe(fn){assert.equal(listener,null);listener=fn;return()=>listener=null;},
  async write(packet){
   const index=writes.length;writes.push([...packet]);
   if(index===fail)throw new Error('ATT failure');
   // An expected opcode embedded in another command must not count.
   listener(Uint8Array.of(136,0x31,0,replies[index][0],99,99,99));
   const reply=index===truncate?replies[index].slice(0,1):replies[index];
   listener(Uint8Array.from(prefix?[136,...reply]:reply));
  }
 }).then(r=>result=r,e=>error=e);
 for(let i=0;i<20&&!result&&!error;i++){
  await flush();if(result||error)break;
  assert(timers.size);now=Math.min(...[...timers.values()].map(t=>t.at));
  for(const [key,t]of[...timers])if(t.at<=now){timers.delete(key);t.fn();}
 }
 await flush();assert(result||error);assert.equal(timers.size,0);assert.equal(listener,null);
 return {ctx,writes,result,error};
}
(async()=>{
 for(const prefix of [true,false]){
  const {writes,result,error}=await run({prefix});assert.equal(error,undefined);
  assert.deepEqual(writes,[46,47,48,41,42].map(n=>[136,n,0,0,0]));
  assert.equal(result.family,34);assert.equal(result.unit,0);assert.deepEqual([...result.serial],[9,8,7,6,5,4]);assert.equal(result.installable,false);
 }
 for(let fail=0;fail<5;fail++){const s=await run({fail});assert(s.error);assert.equal(s.writes.length,fail+1);}
 for(const truncate of [2,3,4]){const s=await run({truncate});assert.match(s.error.message,/Truncated/);assert.equal(s.writes.length,truncate+1);}
 const {ctx,result}=await run(),match=ctx.dBootloaderReplyMatch;
 assert.equal(match(Uint8Array.of(136,49,60,34,0),60,3),null);
 assert.equal(match(Uint8Array.of(11,0,60,34,0),60,3),null);
 assert.deepEqual([...match(Uint8Array.of(0,136,60,34,0),60,3).data],[60,34,0]);
 const image=new Uint8Array(256);image.fill(255,0,16);image.set([0x43,0,0],16);image.set([34,0,4,0],40);image.set([0x42,0,0],47);
 assert.equal(ctx.checkDBootloaderImage(image,result).state,'D-identity-fields-match');
 for(const identity of [null,{...result,family:35},{...result,unit:1},{...result,serial:new Uint8Array(5)}])assert.throws(()=>ctx.checkDBootloaderImage(image,identity));
 image[40]=35;assert.throws(()=>ctx.checkDBootloaderImage(image,result));
 console.log('D identity query order, response prefixes, serial assembly, truncation and image mismatch tests passed');
})().catch(e=>{console.error(e);process.exit(1);});
