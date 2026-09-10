// Exact-container normalization tests. No Shimano firmware is stored here.
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const {webcrypto,createHash}=require('node:crypto');
const rawCode=fs.readFileSync(__dirname+'/../index.html','utf8').split('// BEGIN FIRMWARE PACKET ENCODERS')[1].split('// END FIRMWARE FILE CHECKS')[0];
const sha=b=>createHash('sha256').update(b).digest('hex');
const d=new Uint8Array(256),m=new Uint8Array(256);
d.fill(255,0,16);d.set([0x45,0,0],16);d.set([34,0,4],40);d.set([0x44,8,0],47);
m.set([0x44,8,0],8);m.set([255,255,34,0],12);m.set([0x45,0,0],16);
const digest=Uint8Array.from({length:16},(_,i)=>i*7+3),declared=new Uint8Array(4);
new DataView(declared.buffer).setUint32(0,d.length,true);
const file=b=>({size:b.length,arrayBuffer:async()=>b.slice().buffer});
(async()=>{
  let ctx=vm.createContext({Uint8Array,TextEncoder,Error,WeakSet,AbortController,crypto:webcrypto,setTimeout,clearTimeout});
  vm.runInContext(rawCode,ctx);
  const key=ctx.firmwareWrapperKey(digest),iv=Uint8Array.from({length:16},(_,i)=>255-i);
  const cryptoKey=await webcrypto.subtle.importKey('raw',key,{name:'AES-CBC'},false,['encrypt']);
  const ciphertext=new Uint8Array(await webcrypto.subtle.encrypt({name:'AES-CBC',iv},cryptoKey,d));
  const wrapper=Uint8Array.of(...iv,...ciphertext,...digest,...declared,...new Uint8Array(16));
  const code=rawCode
    .replace('const FIRMWARE_IMAGES = Object.freeze({',
      `const FIRMWARE_IMAGES = Object.freeze({'${sha(d)}':'restoration','${sha(m)}':'restoration',`)
    .replace('const FIRMWARE_WRAPPERS = Object.freeze({',
      `const FIRMWARE_WRAPPERS = Object.freeze({'${sha(wrapper)}':{source:'restoration',rawHash:'${sha(d)}',size:${d.length},digest:'${Buffer.from(digest).toString('hex')}'},`);
  ctx=vm.createContext({Uint8Array,TextEncoder,Error,WeakSet,AbortController,crypto:webcrypto,setTimeout,clearTimeout});
  vm.runInContext(code,ctx);
  let pair=await ctx.loadFirmwarePair([file(wrapper),file(m)]);
  assert.equal(pair.source,'restoration');assert.equal(pair.d.hash,sha(d));assert.equal(pair.d.containerHash,sha(wrapper));
  assert.deepEqual([...pair.d.data],[...d]);assert.equal(pair.m.containerHash,null);
  assert.equal(pair.d.version.join('.'),'4.5.0.0');assert.equal(pair.m.version.join('.'),'4.4.8.0');

  const badDigest=digest.slice();badDigest[0]^=1;
  await assert.rejects(ctx.unwrapReviewedFirmwareContainer(wrapper,
    {source:'restoration',rawHash:sha(d),size:d.length,digest:Buffer.from(badDigest).toString('hex')}),/metadata/);
  await assert.rejects(ctx.unwrapReviewedFirmwareContainer(wrapper,
    {source:'restoration',rawHash:'0'.repeat(64),size:d.length,digest:Buffer.from(digest).toString('hex')}),/does not match/);
  const tampered=wrapper.slice();tampered[20]^=1;
  await assert.rejects(ctx.loadFirmwarePair([file(tampered),file(m)]),/Unrecognized raw|reviewed/);
  console.log('Firmware wrapper: exact container allowlist, local AES-CBC normalization, raw hash and metadata gates passed');
})().catch(error=>{console.error(error);process.exit(1);});
