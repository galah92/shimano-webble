const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const html=fs.readFileSync(require('node:path').join(__dirname,'../index.html'),'utf8');
const code=html.split('// BEGIN FIRMWARE PACKET ENCODERS')[1].split('// END M FIRMWARE QUERY')[0];
const flush=async()=>{for(let i=0;i<6;i++)await Promise.resolve();};
function fixture(writeMode='resolve',checkpoint=false) {
 let time=0,id=0,listener=null,removed=0,resolveWrite,rejectWrite;
 const timers=new Map(),writes=[];
 const ctx=vm.createContext({Uint8Array,Error,
  setTimeout(fn,ms){const key=++id;timers.set(key,{fn,at:time+ms});return key;},
  clearTimeout(key){timers.delete(key);}});
 vm.runInContext(code,ctx);
 const controller=new AbortController();
 const writePromise=new Promise((r,j)=>{resolveWrite=r;rejectWrite=j;});
 const options={querySequence:8,dataSequence:7,checkpoint,signal:controller.signal,
  subscribe(fn){listener=fn;return()=>{removed++;listener=null;};},
  write(packet){assert(listener,'subscribe before write');writes.push([...packet]);
   if(writeMode==='immediate-ack')listener(Uint8Array.of(11,0,192,7));
   if(writeMode==='throw')throw Error('ATT failed');
   return writeMode==='pending'?writePromise:Promise.resolve();}};
 let result=null,error=null;
 const promise=ctx.queryMFirmwareBlock(options).then(r=>result=r,e=>error=e);
 return {async advance(ms){time+=ms;for(const [key,t] of [...timers])if(t.at<=time){timers.delete(key);t.fn();}await flush();},
  emit(packet){listener?.(Uint8Array.from(packet));},writes,controller,promise,resolveWrite,rejectWrite,
  get result(){return result;},get error(){return error;},get removed(){return removed;},get timers(){return timers.size;}};
}
(async()=>{
 let f=fixture('immediate-ack');await flush();assert.equal(f.result.state,'evidence-complete');
 assert.deepEqual(f.writes,[[11,8,3,7]]);assert.equal(f.removed,1);assert.equal(f.timers,0);
 f=fixture('pending');f.emit([11,0,192,7]);await flush();assert.equal(f.result,null);
 f.rejectWrite(Error('ATT failure after RX'));await flush();assert.match(f.error.message,/ATT failure/);assert.equal(f.removed,1);
 f=fixture('pending');await f.advance(7999);assert.equal(f.error,null);f.resolveWrite();await flush();
 await f.advance(2999);assert.equal(f.error,null);await f.advance(1);assert.match(f.error.message,/reply timed out/);assert.equal(f.timers,0);
 f=fixture('pending');await f.advance(8000);assert.match(f.error.message,/ATT write timed out/);
 f.resolveWrite();await flush();assert.equal(f.timers,0);assert.equal(f.removed,1);
 f=fixture('resolve',true);await flush();f.emit([11,0,192,7]);await flush();assert.equal(f.result,null);
 f.emit([242,0,49]);await flush();assert.equal(f.result.state,'evidence-complete');assert.equal(f.result.checksumCorrelated,false);
 f=fixture('resolve',true);await flush();f.emit([11,0,192,7,242,0,50]);await flush();assert.match(f.error.message,/checksum-rejected/);
 for(const code of [0,2,5,10,255]) {
  f=fixture('resolve',true);await flush();f.emit([242,0,50,code]);await flush();
  assert.match(f.error.message,/checksum-rejected/);
  assert.deepEqual(Array.from(f.error.checksumErrorCodes),[code]);
  assert.equal(f.writes.length,1,'diagnostic code cannot trigger another query');
 }
 f=fixture('resolve',true);await flush();f.emit([242,0,50]);await flush();
 assert.deepEqual(Array.from(f.error.checksumErrorCodes),[],'missing byte is not code zero');
 f=fixture('pending',true);f.emit([242,0,50,2]);f.emit([242,0,50,5]);f.resolveWrite();await flush();
 assert.deepEqual(Array.from(f.error.checksumErrorCodes),[2,5],'retain conflicting uncorrelated observations');
 f=fixture('pending');f.emit([11,0,192,7]);f.emit([11,0,131,8,1]);f.resolveWrite();await flush();assert.match(f.error.message,/query-status-1/);
 f=fixture();await flush();f.emit([11,0,145,7]);f.emit([11,0,192,8]);await flush();assert.equal(f.result,null);
 f.controller.abort();await flush();assert.match(f.error.message,/aborted/);assert.equal(f.timers,0);assert.equal(f.removed,1);
 f=fixture('throw');await flush();assert.match(f.error.message,/ATT failed/);assert.equal(f.removed,1);assert.equal(f.timers,0);
 console.log('M query timing, immediate RX, failure precedence, abort and cleanup cases passed');
})().catch(e=>{console.error(e);process.exit(1);});
