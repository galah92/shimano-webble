// Exercise the actual entry/read/reset pipeline through physical GATT writes.
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const {webcrypto}=require('node:crypto');
const code=fs.readFileSync(__dirname+'/../index.html','utf8').split('// BEGIN FIRMWARE PACKET ENCODERS')[1].split('// END FIRMWARE FILE CHECKS')[0];
const credentials=()=>Uint8Array.from({length:15},(_,i)=>i+1);
async function run({fail=-1,late=false,abortAt=-1,drop=null,wrongIdentity=false,wrongBaseline=false,recoveryRejected=false,failIdentityRecord=false}={}) {
 let now=0,id=0,listener=null,result,error,stage='',status=141,selector=13,baseline,bootloaderIdentity;
 const timers=new Map(),calls=[],stages=[],diagnostics=[],controller=new AbortController();
 const ctx=vm.createContext({Uint8Array,Error,AbortController,crypto:webcrypto,setTimeout(fn,ms){const key=++id;timers.set(key,{fn,at:now+ms});return key;},clearTimeout(key){timers.delete(key);}});
 vm.runInContext(code,ctx);
 const rx=p=>{if(stage!==drop&&listener)listener(Uint8Array.from(p));};
 function native(name,bytes) {
  const n=calls.length,p=[...bytes];calls.push({name,p,stage});
  if(n===fail&&!late)throw Error('ATT failure');
  if(n===abortAt){controller.abort();return;}
  if(stage==='baseline') {
   assert.equal(name,'2afe');
   const queries=[[0,1,28,0],[0,1,60,0],[0,1,132,0],[0,1,132,1],[0,22,172,1]];
   const replies=[[0,1,30,34,0],[0,1,62,1,2,3,4,5,6],[0,1,134,69,0,0],[0,1,134,68,8,0],[0,22,174,1,wrongBaseline?1:0]];
   assert.deepEqual(p,queries[n]);rx(replies[n]);
  } else {
   const logical=name==='2afa'?(assert.equal(p[0],0),p.slice(1)):p;
   if(name==='2afa'&&logical[0]===3){status=128|(logical[1]&96)|selector;rx([35,0]);}
   else if(name==='2afa'&&logical[0]===4)rx([36,status]);
   else if(name==='2afa'&&logical[0]===6)rx([38,0]);
   else if(stage==='D-recovery-entry'){
    assert.equal(logical[0],136);const s=logical[1];assert(s>=1&&s<=5);assert.deepEqual(logical.slice(2),[3*s-2,3*s-1,3*s]);rx(recoveryRejected?[0,136,18]:[0,136,17,s]);
   } else if(stage==='D-bootloader-identity'){
    const replies={46:[58],47:[59],48:[60,wrongIdentity?35:34,0],41:[53,9,8,7],42:[54,6,5,4]};
    assert.equal(logical[0],136);assert(replies[logical[1]]);rx([136,...replies[logical[1]]]);
   } else {assert.equal(stage,'reset-request');assert.deepEqual(logical,[136,40,0,0,0]);}
  }
  if(n===fail&&late)throw Error('ATT failed after reply');
 }
 const characteristic=name=>({async writeValueWithResponse(p){native(name,p);},async writeValueWithoutResponse(){throw Error('Probe must never send fragmented firmware data');}});
 const promise=ctx.probeBootloaderRoundTrip({characteristics:{'2afa':characteristic('2afa'),'2afe':characteristic('2afe')},credentials:credentials(),identitySalt:new Uint8Array(16).fill(7),signal:controller.signal,
  subscribe(fn){assert.equal(listener,null);listener=fn;return()=>listener=null;},onDiagnostic(e){diagnostics.push(e);},onBaseline(b){baseline=b;},onBootloaderIdentity(value){assert.equal(stage,'D-bootloader-identity');bootloaderIdentity=value;if(failIdentityRecord)throw Error('Record failed');value.identity='mutated callback copy';},onStage(s){stage=s;stages.push(s);}
 }).then(r=>result=r,e=>error=e);
 for(let i=0;i<1000&&!result&&!error;i++){
  await new Promise(setImmediate);if(result||error)break;
  if(!timers.size)continue;
  now=Math.min(...[...timers.values()].map(t=>t.at));for(const [key,t]of[...timers])if(t.at<=now){timers.delete(key);t.fn();}
 }
 await promise;assert.equal(timers.size,0);assert.equal(listener,null);
 return {result,error,calls,stages,baseline,bootloaderIdentity,ctx,diagnostics};
}
(async()=>{
 const ok=await run();assert(!ok.error,ok.error?.message);assert(ok.result.resetRequested);assert.equal(ok.result.rebootVerified,false);assert.equal(ok.result.firmwareDataSent,false);assert(ok.baseline.identity);
 assert.equal(ok.calls.length,20);assert.equal(ok.result.recoveryEntryAcknowledged,true);
 assert.deepEqual(ok.stages,['baseline','D-recovery-entry','D-bootloader-identity','reset-request']);
 assert(ok.diagnostics.some(e=>e.step==='D-recovery-stage-5-reply'&&e.event==='accepted'));
 assert.match(ok.result.bootloaderIdentity.identity,/^[a-f0-9]{64}$/);
 assert.notEqual(ok.result.bootloaderIdentity.identity,ok.baseline.identity);
 assert.equal(ok.bootloaderIdentity.identity,'mutated callback copy');
 assert(!JSON.stringify(ok.result).includes('serial'));
 const failedRecord=await run({failIdentityRecord:true});assert(failedRecord.error);assert(!failedRecord.error.resetRequested);assert.equal(failedRecord.error.stage,'D-bootloader-identity');
 const salt=new Uint8Array(16).fill(7),identity={family:34,unit:0,serial:Uint8Array.of(9,8,7,6,5,4)};
 const proof=await ok.ctx.fingerprintDBootloaderIdentity(identity,salt);
 assert.equal(proof.identity,ok.result.bootloaderIdentity.identity);
 const pendingProof=ok.ctx.fingerprintDBootloaderIdentity(identity,salt);identity.serial.fill(3);salt.fill(2);
 assert.equal((await pendingProof).identity,proof.identity);
 assert.notEqual((await ok.ctx.fingerprintDBootloaderIdentity(identity,salt)).identity,proof.identity);
 for(const serial of [new Uint8Array(6),new Uint8Array(6).fill(255),new Uint8Array(5)])
  await assert.rejects(ok.ctx.fingerprintDBootloaderIdentity({...identity,serial},salt));
 await assert.rejects(ok.ctx.fingerprintDBootloaderIdentity({...identity,family:35},salt));
 await assert.rejects(ok.ctx.fingerprintDBootloaderIdentity(identity,new Uint8Array(15)));
 for(const late of [false,true])for(let fail=0;fail<ok.calls.length;fail++){
  const r=await run({fail,late});assert(r.error);assert.equal(r.calls.length,fail+1);assert.equal(r.error.resetRequested,fail===ok.calls.length-1);
 }
 for(let abortAt=0;abortAt<ok.calls.length;abortAt++){const r=await run({abortAt});assert(r.error);assert.equal(r.calls.length,abortAt+1);}
 for(const drop of ok.stages.filter(s=>s!=='reset-request')){const r=await run({drop});assert(r.error);assert.equal(r.error.stage,drop);}
 const wrong=await run({wrongIdentity:true});assert(wrong.error);assert(!wrong.error.resetRequested);
 const original=await run({wrongBaseline:true});assert(original.error);assert.equal(original.calls.length,5);assert(!original.baseline);
 const rejected=await run({recoveryRejected:true});assert(rejected.error);
 assert.equal(rejected.calls.length,9);assert.equal(rejected.error.stage,'D-recovery-entry');
 assert.equal(rejected.diagnostics.at(-1).reason,'device-rejected (FIRMUP 12)');
 assert(!rejected.error.resetRequested);
 assert(ok.diagnostics.filter(e=>e.prefix).every(e=>e.prefix.length<=3));
 assert(ok.diagnostics.filter(e=>e.packet).every(e=>e.packet[0]!==136));
 let count=0;const writer=ok.ctx.createBootloaderProbeWriter({'2afa':{async writeValueWithResponse(){count++;}},'2afe':{async writeValueWithResponse(){count++;}}},credentials());
 const forbidden=[['2afa',[6,31]],['2afe',[0,50,32,1]],['2afa',[3,0]],['2afa',[136,40,0,0,0]],['2afa',[11,0,4,1]],['2afa',[11,0,2,...new Array(68).fill(0)]],['2afe',[0,22,168,1,1]],['2afa',[136,1,99,99,99]]];
 for(const command of [6,7,8,9,10,33,36,38,39])forbidden.push(['2afa',[136,command,0,0,0]]);
 for(const [name,p]of forbidden)await assert.rejects(writer.write(name,Uint8Array.from(p)));
 assert.equal(count,0);writer.allowReset();await writer.write('2afa',Uint8Array.of(136,40,0,0,0));assert.equal(count,1);writer.close();await assert.rejects(writer.write('2afa',Uint8Array.of(4)));
 console.log(`Bootloader probe: ${ok.calls.length} physical writes; no data/erase/write-region commands, failure-before/after and abort at every write, phase timeouts, identity/baseline gates, reset gate and cleanup passed`);
})().catch(e=>{console.error(e);process.exit(1);});
