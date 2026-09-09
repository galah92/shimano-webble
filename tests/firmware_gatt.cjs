const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const html=fs.readFileSync(require('node:path').join(__dirname,'../index.html'),'utf8');
const code=html.split('// BEGIN FIRMWARE PACKET ENCODERS')[1].split('// END M FIRMWARE BLOCK WORKER')[0];
const flush=async()=>{for(let i=0;i<30;i++)await Promise.resolve();};
function fixture(){
 let now=0,id=0;const timers=new Map();
 const ctx=vm.createContext({Uint8Array,Error,AbortController,setTimeout(fn,ms){const key=++id;timers.set(key,{fn,at:now+ms});return key;},clearTimeout(key){timers.delete(key);}});
 vm.runInContext(code,ctx);
 return {ctx,timers,async advance(ms){now+=ms;for(const [key,t]of[...timers])if(t.at<=now){timers.delete(key);t.fn();}await flush();}};
}
(async()=>{
 let f=fixture();const plan=f.ctx.firmwareGattFragments;
 for(const vector of JSON.parse(fs.readFileSync(__dirname+'/gatt_fragment_vectors.json','utf8'))){
  const fragments=plan('2afa',Uint8Array.from(Buffer.from(vector.packet,'hex')));
  assert.deepEqual(Array.from(fragments,x=>({hex:Buffer.from(x.bytes).toString('hex'),withoutResponse:x.withoutResponse})),vector.fragments);
 }
 assert.deepEqual([...plan('2afa',Uint8Array.of(19,1,28,0))[0].bytes],[0,19,1,28,0]); // Known live display query.
 assert.deepEqual([...plan('2afe',Uint8Array.of(0,1,28,0))[0].bytes],[0,1,28,0]);
 const logical=new Uint8Array(71).fill(5);logical[0]=11;
 assert.deepEqual(Array.from(plan('2afa',logical),x=>[x.bytes[0],x.bytes.length]),[[128,20],[160,20],[192,20],[96,18]]);
 for(const [name,p]of [['2afa',new Uint8Array()],['2afa',new Uint8Array(72)],['2afe',new Uint8Array(21)],['2aff',logical]])assert.throws(()=>plan(name,p));
 for(const fail of [-1,0,1,2,3]){
  f=fixture();const calls=[],input=logical.slice();
  const writer=f.ctx.createFirmwareGattWriter({ '2afa': {
   async writeValueWithoutResponse(bytes){const n=calls.length;calls.push([...bytes]);input.fill(0);if(n===fail)throw new Error('native write failed');},
   async writeValueWithResponse(){throw new Error('Wrong write mode');}
  }});
  let error;try{await writer.write('2afa',input);}catch(e){error=e;}
  assert.equal(calls.length,fail<0?4:fail+1);
  assert(calls.every(p=>p.slice(2).every(b=>b===5)),'all fragments use the same snapshot');
  if(fail>=0){assert(error);await assert.rejects(writer.write('2afa',logical),/closed/);}
  else assert.equal(error,undefined);
  assert.equal(f.timers.size,0);
 }
 for(const stop of ['timeout','abort','close']){
  f=fixture();const calls=[],controller=new AbortController();let complete,error;
  const writer=f.ctx.createFirmwareGattWriter({'2afa':{writeValueWithoutResponse(bytes){calls.push([...bytes]);return new Promise(r=>complete=r);}}},controller.signal);
  const pending=writer.write('2afa',logical).catch(e=>error=e);await flush();
  await assert.rejects(writer.write('2afa',logical),/Concurrent/);
  if(stop==='timeout')await f.advance(7000);else if(stop==='abort')controller.abort();else writer.close();
  await pending;assert(error);assert.equal(calls.length,1);assert.equal(f.timers.size,0);
  complete();await flush();assert.equal(calls.length,1,'late native completion must not send remaining fragments');
  await assert.rejects(writer.write('2afa',logical),/closed/);
 }
 f=fixture();const calls=[];const writer=f.ctx.createFirmwareGattWriter({'2afe':{async writeValueWithResponse(p){calls.push([...p]);}}});
 await writer.write('2afe',Uint8Array.of(0,240,0,65,0,0,0));assert.deepEqual(calls,[[0,240,0,65,0,0,0]]);assert.equal(f.timers.size,0);
 console.log('10 original Java t0 vectors, live short framing, write modes, snapshots and partial-write fail-stop tests passed');
})().catch(e=>{console.error(e);process.exit(1);});
