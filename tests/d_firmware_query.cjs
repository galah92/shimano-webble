const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const html=fs.readFileSync(require('node:path').join(__dirname,'../index.html'),'utf8');
const code=html.split('// BEGIN FIRMWARE PACKET ENCODERS')[1].split('// END D FIRMWARE QUERY')[0];
const flush=async()=>{for(let i=0;i<8;i++)await Promise.resolve();};
function fixture(blockIndex,mode='pending') {
 let now=0,id=0,listener=null,removed=0,result,error,resolveWrite;
 const timers=new Map(),writes=[];
 const ctx=vm.createContext({Uint8Array,Error,setTimeout(fn,ms){const key=++id;timers.set(key,{fn,at:now+ms});return key;},clearTimeout(key){timers.delete(key);}});
 vm.runInContext(code,ctx);
 const controller=new AbortController();
 const pending=new Promise(r=>resolveWrite=r);
 ctx.queryDFirmwareBlock({blockIndex,querySequence:8,dataSequence:7,signal:controller.signal,
 subscribe(fn){listener=fn;return()=>{listener=null;removed++;};},
 write(p){assert(listener);writes.push([...p]);return mode==='pending'?pending:Promise.resolve();}
 }).then(r=>result=r,e=>error=e);
 return {ctx,writes,controller,resolveWrite,
 emit(p){listener?.(Uint8Array.from(p));},
 async advance(ms){now+=ms;for(const [key,t] of [...timers])if(t.at<=now){timers.delete(key);t.fn();}await flush();},
 get result(){return result;},get error(){return error;},get removed(){return removed;},get timers(){return timers.size;}};
}
(async()=>{
 let f=fixture(0);f.emit([11,0,192,7]);f.emit([136,49,1,0]);await flush();assert.equal(f.result,undefined);
 f.resolveWrite();await flush();assert.equal(f.result.state,'evidence-complete');assert.equal(f.removed,1);assert.equal(f.timers,0);assert.deepEqual(f.writes,[[11,8,3,7]]);
 for(const block of [0,2,3]) {
  f=fixture(block);await f.advance(7999);f.resolveWrite();await flush();
  const timeout=block<3?25000:3000;await f.advance(timeout-1);assert.equal(f.error,undefined);
  await f.advance(1);assert.match(f.error.message,/reply timed out/);assert.equal(f.removed,1);
 }
 f=fixture(3,'resolve');await flush();f.emit([136,49,4,0]);await flush();assert.equal(f.result,undefined);
 f.emit([11,0,192,7]);await flush();assert.equal(f.result.state,'evidence-complete');
 f=fixture(3,'resolve');await flush();f.emit([11,0,192,7]);f.emit([136,49,5,0]);assert.equal(f.result,undefined);
 f.emit([136,50,4,0]);await flush();assert.match(f.error.message,/D block result rejected/);
 f=fixture(0);await f.advance(8000);assert.match(f.error.message,/ATT write timed out/);f.resolveWrite();await flush();assert.equal(f.timers,0);
 f=fixture(0);f.controller.abort();await flush();assert.match(f.error.message,/aborted/);assert.equal(f.removed,1);
 const plan=f.ctx.dFirmwareAddressPlan;
 const plain=x=>JSON.parse(JSON.stringify(x));
 const initial=plan(132072,0);assert.deepEqual(plain(initial.initial.map(x=>x.payload)),[[33,0,64,0],[10,0,0,0],[36,0,64,0]]);
 assert.equal(plan(132072,1023).boundary.length,0);
 assert.deepEqual(plain(plan(132072,1024).boundary.map(x=>x.payload)),[[36,0,64,1],[10,1,0,0]]);
 assert.deepEqual(plain(plan(132072,2048).boundary.map(x=>x.payload)),[[36,0,64,2],[10,2,0,0]]);
 assert.equal(plan(196608,3071).address,0x33fc0);assert.equal(initial.installable,false);
 assert.throws(()=>plan(196609,0),/Invalid/);assert.throws(()=>plan(64,1),/Invalid/);
 console.log('D query deadlines, ACK/result correlation, abort, cleanup and bank setup tests passed');
})().catch(e=>{console.error(e);process.exit(1);});
