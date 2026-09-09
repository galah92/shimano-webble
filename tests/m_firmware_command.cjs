const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const html=fs.readFileSync(require('node:path').join(__dirname,'../index.html'),'utf8');
const code=html.split('// BEGIN FIRMWARE PACKET ENCODERS')[1].split('// END M FIRMWARE COMMANDS')[0];
const flush=async()=>{for(let i=0;i<12;i++)await Promise.resolve();};
function fixture(command=33,args=[0,14,0],targetSelector=1) {
 let now=0,id=0,listener=null,result,error,resolveWrite,rejectWrite,removed=0;
 const timers=new Map(),writes=[],controller=new AbortController();
 const ctx=vm.createContext({Uint8Array,Error,setTimeout(fn,ms){const key=++id;timers.set(key,{fn,at:now+ms});return key;},clearTimeout(key){timers.delete(key);}});
 vm.runInContext(code,ctx);
 ctx.sendMFirmwareCommand({command,args,targetSelector,signal:controller.signal,
  subscribe(fn){listener=fn;return()=>{listener=null;removed++;};},
  write(characteristic,packet){assert(listener);writes.push([characteristic,[...packet]]);return new Promise((r,j)=>{resolveWrite=r;rejectWrite=j;});}
 }).then(r=>result=r,e=>error=e);
 return {ctx,writes,controller,resolveWrite,rejectWrite,emit(p){listener?.(Uint8Array.from(p));},
  async advance(ms){now+=ms;for(const [key,t]of[...timers])if(t.at<=now){timers.delete(key);t.fn();}await flush();},
  get result(){return result;},get error(){return error;},get timers(){return timers.size;},get removed(){return removed;}};
}
(async()=>{
 const commands=[[33,[0,14,0],6000],[36,[0,0,252],10000],[38,[0,0,0],2000],[39,[178,0,0],21000]];
 for(const [command,args,deadline]of commands)for(const selector of [0,1,255]){
  let f=fixture(command,args,selector);
  assert.deepEqual(f.writes,[[selector===0?'2afa':'2afe',[selector===0?19:0,240,0,command,...args]]]);
  f.emit([242,0,49]);await flush();assert.equal(f.result,undefined,'ATT failure must still be able to override early RX');
  f.resolveWrite();await flush();assert.equal(f.result.state,'evidence-complete');assert.equal(f.result.commandCorrelated,false);assert.equal(f.result.installable,false);
  assert.equal(f.removed,1);assert.equal(f.timers,0);
  f=fixture(command,args,selector);await f.advance(7999);f.resolveWrite();await flush();
  await f.advance(deadline-1);assert.equal(f.error,undefined);await f.advance(1);assert.match(f.error.message,/reply timed out/);
  assert.equal(f.writes.length,1);assert.equal(f.removed,1);assert.equal(f.timers,0);
 }
 let f=fixture();f.emit([242,0,49]);f.rejectWrite(new Error('ATT rejected'));await flush();assert.match(f.error.message,/ATT rejected/);assert.equal(f.result,undefined);
 f=fixture();f.resolveWrite();await flush();f.emit([0,242,0,50,58]);await flush();assert.match(f.error.message,/M command rejected; code 58/);assert.equal(f.writes.length,1);
 f=fixture();f.controller.abort();await flush();assert.match(f.error.message,/aborted/);assert.equal(f.timers,0);assert.equal(f.removed,1);
 f=fixture();await f.advance(8000);assert.match(f.error.message,/ATT write timed out/);f.resolveWrite();await flush();assert.equal(f.timers,0);
 const match=f.ctx.mFirmwareCommandMatch,plan=f.ctx.mFirmwareCommandPlan;
 for(const prefix of [[],[0],[19],[0,19]])for(const result of [49,50])assert.equal(match(Uint8Array.from([...prefix,242,0,result,58])).result,result);
 for(const p of [[],[242],[242,0],[242,1,49],[49,0,0],[242,0,7,242,0,49]])assert.equal(match(Uint8Array.from(p)),null);
 for(const [command,args,selector]of [[40,[0,0,0],1],[33,[0,0,0],1],[36,[1,0,252],1],[36,[0,0,251],1],[38,[1,0,0],1],[39,[0,1,0],1],[33,[0,14,0],undefined],[33,[0,14,0],-1],[33,[0,14],1]])assert.throws(()=>plan(command,args,selector));
 console.log('M command routing, arguments, first-marker matching, deadlines, early RX, abort and no-retry tests passed');
})().catch(e=>{console.error(e);process.exit(1);});
