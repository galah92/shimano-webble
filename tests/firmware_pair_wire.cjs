// End-to-end coordinator test: only the BLE device, clock and trusted test
// image list are simulated. All app entry/transfer/framing functions are real.
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const {webcrypto,createHash}=require('node:crypto');
const source=fs.readFileSync(__dirname+'/../index.html','utf8').split('// BEGIN FIRMWARE PACKET ENCODERS')[1].split('// END FIRMWARE FILE CHECKS')[0];
const flush=async()=>{for(let i=0;i<150;i++)await Promise.resolve();};
const sum=a=>a.reduce((x,y)=>(x+y)&255,0);
function images(dLength,mLength){
 const d=Uint8Array.from({length:dLength},(_,i)=>(i*13+7)&255),m=Uint8Array.from({length:mLength},(_,i)=>(i*17+3)&255);
 d.fill(255,0,16);d.set([0x43,0,0],16);d.set([34,0,4],40);d.set([0x42,0,0],47);
 m.set([255,255,34,0],12);m.set([0x42,1,0],8);m.set([0x42,0,0],16);return {d,m};
}
async function run({dLength=256,mLength=256,fail=-1,lateFail=false,abortAt=-1,wrongIdentity=false,dropPhase=null}={}){
 const {d,m}=images(dLength,mLength),hash=b=>createHash('sha256').update(b).digest('hex');
 const code=source.replace('const FIRMWARE_IMAGES = Object.freeze({',`const FIRMWARE_IMAGES = Object.freeze({'${hash(d)}':'preparation','${hash(m)}':'preparation',`);
 let now=0,id=0,listener=null,result,error,stage='',selector=13,status=141,fragments=null,fragmentIndex=0,pending=null;
 let nativeCount=0,mBlocks=0,dBlocks=0,checkpoints=0,deviceError=null,mFinished=false,dFinished=false;
 const timers=new Map(),stages=[],commands=[],controller=new AbortController();
 const ctx=vm.createContext({Uint8Array,Error,AbortController,crypto:webcrypto,setTimeout(fn,ms){const key=++id;timers.set(key,{fn,at:now+ms});return key;},clearTimeout(key){timers.delete(key);}});
 vm.runInContext(code,ctx);
 const rx=(...bytes)=>{if(stage!==dropPhase&&listener)listener(Uint8Array.from(bytes));};
 function logical(name,p){
  commands.push({name,p:[...p],stage});
  if(name==='2afa'&&p[0]===3){status=128|(p[1]&96)|selector;rx(35,0);return;}
  if(name==='2afa'&&p[0]===4){rx(36,status);return;}
  if(name==='2afa'&&p[0]===6){assert([0,31].includes(p[1]));rx(38,0);return;}
  if((p[0]===0||p[0]===19)&&p[1]===50){assert.deepEqual(p.slice(1),[50,32,1]);rx(50,34,1);return;}
  if((p[0]===0||p[0]===19)&&p[1]===240){
   assert.equal(stage,'M-transfer');assert.equal(p[2],0);
   if(p[3]===65)rx(242,0,81,32,3,0);
   else {assert([33,36,38,39].includes(p[3]));if(p[3]===39){assert.equal(mBlocks,Math.ceil(m.length/64));assert.equal(p[4],sum(m));mFinished=true;}rx(242,0,49);}
   return;
  }
  if(p[0]===11){
   if(p[2]===4){assert.deepEqual(p,[11,0,4,1]);rx(11,0,132,0);return;}
   if(p[2]===3){
    assert(pending);assert.equal(p[3],pending.sequence);rx(11,0,192,p[3]);
    if(pending.component==='M'){if(pending.checkpoint)rx(242,0,49);}
    else {const block=pending.index+1;rx(136,49,block&255,block>>8);}
    pending=null;return;
   }
   assert.equal(pending,null,'query must resolve each data block before next');
   const component=p[2]===2?'D':'M',index=component==='D'?dBlocks:mBlocks,data=component==='D'?d:m;
   assert.equal(stage,component==='M'?'M-transfer':'D-identity-and-transfer');
   const offset=index*64,expected=new Array(64).fill(component==='D'?255:0);
   expected.splice(0,Math.min(64,data.length-offset),...data.slice(offset,offset+64));
   assert.deepEqual(p.slice(4,68),expected);assert.equal(p[3],0);
   let checkpoint=false;
   if(component==='D'){
    assert.equal(p.length,71);assert.equal(p[68],sum(expected));assert.equal(p[69]|p[70]<<8,index);dBlocks++;
   }else{
    const end=Math.min(offset+64,data.length);checkpoint=end%1024===0||end===data.length;
    assert.equal(p[2],checkpoint?18:17);assert.equal(p.length,checkpoint?71:68);
    if(checkpoint){assert.equal(p[68],sum(data.slice(Math.floor(offset/1024)*1024,end)));assert.deepEqual(p.slice(69),[0,0]);checkpoints++;}mBlocks++;
   }
   pending={sequence:p[1],component,index,checkpoint};return;
  }
  assert.equal(p[0],136);
  if(stage==='D-bootloader-entry'){
   const n=p[1];assert(n>=1&&n<=5);assert.deepEqual(p.slice(2),[3*n-2,3*n-1,3*n]);rx(0,136,17,n);return;
  }
  assert.equal(stage,'D-identity-and-transfer');
  const replies={46:[58],47:[59],48:[60,wrongIdentity?35:34,0],41:[53,9,8,7],42:[54,6,5,4]};
  if(replies[p[1]]){rx(136,...replies[p[1]]);return;}
  assert([6,7,8,9,33,10,36,39].includes(p[1]),'unexpected D command or reset');
  if(p[1]===39){assert.equal(dBlocks,Math.ceil(d.length/64));assert.equal(p[2],sum(d));dFinished=true;}
  rx(136,49,0,0);
 }
 function native(name,withoutResponse,bytes){
  const call=nativeCount++,p=[...bytes];
  if(call===fail&&!lateFail)throw new Error('simulated native failure');
  if(call===abortAt){controller.abort();return;}
  try{
   assert(p.length<=20);
   if(name==='2afe'){assert(!withoutResponse);logical(name,p);}
   else if(p[0]===0){assert(!withoutResponse);assert.equal(fragments,null);logical(name,p.slice(1));}
   else{
    assert(withoutResponse);const index=(p[0]&127)>>5;
    if(!fragments){assert.equal(index,0);fragments=[p[1]];fragmentIndex=0;}
    assert.equal(index,fragmentIndex++);assert.equal(p[1],fragments[0]);fragments.push(...p.slice(2));
    if(!(p[0]&128)){const packet=fragments;fragments=null;logical(name,packet);}
   }
  }catch(e){deviceError=e;throw e;}
  if(call===fail&&lateFail)throw new Error('simulated ATT failure after reply');
 }
 const characteristic=name=>({async writeValueWithResponse(p){native(name,false,p);},async writeValueWithoutResponse(p){native(name,true,p);}});
 const file=data=>({size:data.length,arrayBuffer:async()=>data.slice().buffer});
 const promise=ctx.transferFirmwarePair({files:[file(m),file(d)],baseline:{family:34,unit:0,dVersion:'4.5.0.0',mVersion:'4.4.8.0'},credentials:Uint8Array.from({length:15},(_,i)=>i+1),
  characteristics:{'2afa':characteristic('2afa'),'2afe':characteristic('2afe')},signal:controller.signal,
  subscribe(fn){assert.equal(listener,null);listener=fn;return()=>listener=null;},
  onStage(value){stage=value;stages.push(value);if(value==='D-update-entry'){assert(mFinished);selector=0;status=128;}}
 }).then(r=>result=r,e=>error=e);
 for(let i=0;i<30000&&!result&&!error;i++){
  await flush();await new Promise(setImmediate);if(result||error)break;
  if(!timers.size){await new Promise(setImmediate);continue;} // Real SHA-256 completion.
  now=Math.min(...[...timers.values()].map(t=>t.at));
  for(const [key,t]of[...timers])if(t.at<=now){timers.delete(key);t.fn();}
 }
 await promise;if(deviceError)throw deviceError;
 assert.equal(listener,null);assert.equal(timers.size,0);
 return {result,error,nativeCount,mBlocks,dBlocks,checkpoints,stages,commands,mFinished,dFinished};
}
(async()=>{
 const first=await run();assert(!first.error);assert(first.result.mFinished&&first.result.dFinished);assert.equal(first.result.reset,false);
 assert.equal(first.result.firmwareVerified,false);assert(first.mFinished&&first.dFinished);
 let uncertainFinishes=0;
 for(const lateFail of [false,true])for(let fail=0;fail<first.nativeCount;fail++){
  const r=await run({fail,lateFail});assert(r.error);assert.equal(r.nativeCount,fail+1);assert.equal(r.result,undefined);assert.equal(r.error.deviceStateUnknown,true);
  if(r.mFinished&&!r.error.mFinished||r.dFinished&&!r.error.dFinished)uncertainFinishes++;
 }
 assert(uncertainFinishes>=2, 'post-reply ATT failures must not claim components unchanged');
 for(let abortAt=0;abortAt<first.nativeCount;abortAt++){const r=await run({abortAt});assert(r.error);assert.equal(r.nativeCount,abortAt+1);}
 for(const dropPhase of first.stages.slice(1)){const r=await run({dropPhase});assert(r.error);assert.equal(r.error.stage,dropPhase);}
 const mismatch=await run({wrongIdentity:true});assert(mismatch.error);assert.equal(mismatch.error.mFinished,true);assert.equal(mismatch.dBlocks,0);
 for(const [dLength,mLength]of [[65537,1025],[132072,116320],[138072,119824]]){
  const r=await run({dLength,mLength});assert(!r.error, r.error?.message);assert.equal(r.dBlocks,Math.ceil(dLength/64));assert.equal(r.mBlocks,Math.ceil(mLength/64));assert.equal(r.checkpoints,Math.ceil(mLength/1024));
 }
 console.log(`Full paired wire simulation passed: ${first.nativeCount}-write small pair, failure-before/after and abort at every write, phase timeouts, wrong identity, bank/checkpoint boundaries and both reviewed pair sizes`);
})().catch(e=>{console.error(e);process.exit(1);});
