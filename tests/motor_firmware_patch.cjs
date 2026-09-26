// Deterministic five-byte D-image patch construction; no vendor image is stored.
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const {webcrypto,createHash}=require('node:crypto');
let code=fs.readFileSync(__dirname+'/../index.html','utf8').split('// BEGIN FIRMWARE PACKET ENCODERS')[1].split('// END FIRMWARE FILE CHECKS')[0];
const sha=data=>createHash('sha256').update(data).digest('hex');
const input=new Uint8Array(256);input.fill(0x5a);input.fill(255,0,16);
input.set([0x45,0,0],16);input.set([34,0,4],40);input.set([0x44,8,0],47);
input.set([0x2d,0xd1],100);input.set([0x24,0xd1],120);
const expected=input.slice();expected[0x12]=1;expected.set([0x00,0xbf],100);expected.set([0x00,0xbf],120);
const motorPeer=new Uint8Array(256);motorPeer.fill(0x33);motorPeer.set([0x44,8,0],8);
motorPeer.set([255,255,34,0],12);motorPeer.set([0x44,6,0],16);
code=code
  .replace('const FIRMWARE_IMAGES = Object.freeze({',
    `const FIRMWARE_IMAGES = Object.freeze({'${sha(input)}':'restoration','${sha(motorPeer)}':'restoration',`)
  .replace("name:'D4.5.0 PC-mode gate experiment',size:138072,",
    "name:'D4.5.0 PC-mode gate experiment',size:256,")
  .replace("inputHash:'44806bd54aedff95a88bb73fafe0f0581297f2f67b2ea35545cea012899d90bb'",`inputHash:'${sha(input)}'`)
  .replace("outputHash:'0dbbb3d3b634d831d8450d2758d953502bfdc7f16ac8640a4e3ca46fff3fff18'",`outputHash:'${sha(expected)}'`)
  .replace("peerHash:'9ea350e988345a9d9fb41c1363562ca190f1a8d5e1cc8a38c6373f69b877f033'",`peerHash:'${sha(motorPeer)}'`)
  .replace('offset:0x152c8','offset:100')
  .replace('offset:0x15394','offset:120');
(async()=>{
  const ctx=vm.createContext({Uint8Array,TextEncoder,Error,WeakSet,AbortController,crypto:webcrypto,setTimeout,clearTimeout});
  vm.runInContext(code,ctx);
  const before=input.slice(),result=await ctx.buildPatchedD450Image(input);
  assert.deepEqual([...input],[...before]);assert.deepEqual([...result.data],[...expected]);
  assert.equal(result.source,'pc-mode-patch');assert.equal(result.component,'D');assert.equal(result.version,'4.5.0.1');
  assert.equal(result.changedBytes,5);assert.equal(result.outputHash,sha(expected));
  assert.equal(result.checksum,expected.reduce((sum,value)=>sum+value,0)&255);
  assert.equal(result.geometry.blocks,4);assert.equal(result.geometry.padding,0);assert.equal(result.installable,false);
  const file=bytes=>({size:bytes.length,arrayBuffer:async()=>Uint8Array.from(bytes).buffer});
  const pair=await ctx.loadPatchedD450FirmwarePair([file(input),file(motorPeer)]);
  assert.equal(pair.source,'pc-mode-patch');assert.equal(pair.installable,false);
  assert.deepEqual([...pair.d.version],[4,5,0,1]);assert.deepEqual([...pair.m.version],[4,4,8,0]);
  assert.equal(pair.d.hash,sha(expected));assert.equal(pair.m.hash,sha(motorPeer));
  assert.deepEqual([...pair.d.data],[...expected]);assert.deepEqual([...pair.m.data],[...motorPeer]);
  assert.equal(pair.restoration.dHash,sha(input));assert.equal(pair.restoration.mHash,sha(motorPeer));
  pair.d.data.fill(0);pair.m.data.fill(0);
  const bad=input.slice();bad[100]^=1;
  await assert.rejects(ctx.buildPatchedD450Image(bad),/exact reviewed input image/);
  const alternate=input.slice();alternate[10]^=1;
  await assert.rejects(ctx.applyReviewedFirmwarePatch(alternate,{
    size:alternate.length,inputHash:sha(alternate),outputHash:'0'.repeat(64),
    sites:[{name:'wrong site',offset:100,original:[0x2c,0xd1],replacement:[0,0xbf]}]}),/site mismatch/);
  console.log('Motor firmware patch: exact hashes, five-byte diff, marker header and non-installable stock-peer loader passed');
})().catch(error=>{console.error(error);process.exit(1);});
