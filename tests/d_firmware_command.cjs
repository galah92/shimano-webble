const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const html=fs.readFileSync(require('node:path').join(__dirname,'../index.html'),'utf8');
const code=html.split('// BEGIN FIRMWARE PACKET ENCODERS')[1].split('// END D FIRMWARE COMMANDS')[0];
const flush=async()=>{for(let i=0;i<8;i++)await Promise.resolve();};
function fixture(payload=[10,0,0,0]) {
 let now=0,id=0,listener=null,removed=0,result,error,resolveWrite,rejectWrite;
 const timers=new Map(),writes=[],ctx=vm.createContext({Uint8Array,Error,setTimeout(fn,ms){const key=++id;timers.set(key,{fn,at:now+ms});return key;},clearTimeout(key){timers.delete(key);}});
 vm.runInContext(code,ctx);
 const controller=new AbortController(),pending=new Promise((r,j)=>{resolveWrite=r;rejectWrite=j;});
 ctx.sendDFirmwareCommand({payload,signal:controller.signal,
 subscribe(fn){listener=fn;return()=>{listener=null;removed++;};},
 write(p){assert(listener);writes.push([...p]);return pending;}
 }).then(r=>result=r,e=>error=e);
 return {ctx,payload,writes,controller,resolveWrite,rejectWrite,
 emit(hex){listener?.(Uint8Array.from(Buffer.from(hex,'hex')));},
 async advance(ms){now+=ms;for(const [key,t] of [...timers])if(t.at<=now){timers.delete(key);t.fn();}await flush();},
 get result(){return result;},get error(){return error;},get removed(){return removed;},get timers(){return timers.size;}};
}
(async()=>{
 let f=fixture();
 const vectors=JSON.parse(fs.readFileSync(__dirname+'/d_command_vectors.json','utf8'));
 for(const c of vectors){const m=f.ctx.dFirmwareCommandMatch(Uint8Array.from(Buffer.from(c.raw,'hex')));assert.equal(m?Buffer.from(m.payload).toString('hex'):null,c.match,c.raw);}
 f.emit('88310000');assert.equal(f.result,undefined);f.resolveWrite();await flush();assert.equal(f.result.state,'evidence-complete');assert.equal(f.result.commandCorrelated,false);assert.equal(f.removed,1);assert.equal(f.timers,0);assert.deepEqual(f.writes,[[136,10,0,0,0]]);
 f=fixture();f.emit('88310000');f.rejectWrite(Error('ATT failed after RX'));await flush();assert.match(f.error.message,/ATT failed/);assert.equal(f.removed,1);
 for(const command of [[10,0,0,0],[36,0,64,0],[33,0,64,0],[39,69,0,0]]) {
  f=fixture(command);await f.advance(7999);f.resolveWrite();await flush();
  f.emit('88310100');f.emit('88320100');await flush();assert.equal(f.result,undefined);
  const deadline=command[0]===33?40000:command[0]===39?3000:1200;await f.advance(deadline-1);assert.equal(f.error,undefined);await f.advance(1);assert.match(f.error.message,/reply timed out/);assert.equal(f.writes.length,1);assert.equal(f.timers,0);
 }
 f=fixture();f.emit('88320000');f.resolveWrite();await flush();assert.match(f.error.message,/setup command rejected/);
 f=fixture();await f.advance(8000);assert.match(f.error.message,/ATT write timed out/);f.resolveWrite();await flush();assert.equal(f.timers,0);
 f=fixture();f.controller.abort();await flush();assert.match(f.error.message,/aborted/);assert.equal(f.removed,1);
 for(const payload of [[39,0,1,0],[40,0,0,0],[0,0,0,0],[10,3,0,0],[33,0,96,0],[36,1,64,0],[36,0,0,0],[10,0,0,256]])assert.throws(()=>f.ctx.sendDFirmwareCommand({payload}),/Unsupported|range|unsigned/);
 console.log('108 command fixtures, command bounds, immediate RX, ATT failure, deadlines, abort and no-retry tests passed');
})().catch(e=>{console.error(e);process.exit(1);});
