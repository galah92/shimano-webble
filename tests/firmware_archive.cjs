// A reviewed ZIP may replace the two preparation DAT selections. This builds a
// tiny synthetic archive so no Shimano firmware is committed to the test tree.
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict'),zlib=require('node:zlib');
const {webcrypto,createHash}=require('node:crypto');
const rawCode=fs.readFileSync(__dirname+'/../index.html','utf8').split('// BEGIN FIRMWARE PACKET ENCODERS')[1].split('// END FIRMWARE FILE CHECKS')[0];
const sha=b=>createHash('sha256').update(b).digest('hex');
const d=new Uint8Array(256),m=new Uint8Array(256);
for(let i=0;i<256;i++){d[i]=(i*73+19)&255;m[i]=(i*101+7)&255;}
d.fill(255,0,16);d.set([0x43,0,0],16);d.set([34,0,4],40);d.set([0x42,1,0],47);
m.set([0x42,1,0],8);m.set([255,255,34,0],12);m.set([0x43,0,0],16);
function entry(name,data,crc) {
  const encoded=Buffer.from(name),compressed=zlib.deflateRawSync(data),header=Buffer.alloc(30);
  header.writeUInt32LE(0x04034b50,0);header.writeUInt16LE(20,4);header.writeUInt16LE(0,6);header.writeUInt16LE(8,8);
  header.writeUInt32LE(crc,14);header.writeUInt32LE(compressed.length,18);header.writeUInt32LE(data.length,22);
  header.writeUInt16LE(encoded.length,26);header.writeUInt16LE(0,28);
  return {bytes:Buffer.concat([header,encoded,compressed]),name,compressedSize:compressed.length,size:data.length,crc};
}
const de=entry('D.test.dat',d,0x12345678),me=entry('M.test.dat',m,0x87654321),mOffset=de.bytes.length;
const archive=Buffer.concat([de.bytes,me.bytes]),archiveReview={source:'preparation',size:archive.length,entries:[
  {name:de.name,offset:0,compressedSize:de.compressedSize,size:de.size,crc:de.crc,hash:sha(d)},
  {name:me.name,offset:mOffset,compressedSize:me.compressedSize,size:me.size,crc:me.crc,hash:sha(m)},
]};
const code=rawCode
  .replace('const FIRMWARE_IMAGES = Object.freeze({',
    `const FIRMWARE_IMAGES = Object.freeze({'${sha(d)}':'preparation','${sha(m)}':'preparation',`)
  .replace('const FIRMWARE_ARCHIVES = Object.freeze({',
    `const FIRMWARE_ARCHIVES = Object.freeze({'${sha(archive)}':${JSON.stringify(archiveReview)},`);
const context={Uint8Array,DataView,TextEncoder,TextDecoder,Error,WeakSet,AbortController,crypto:webcrypto,
  setTimeout,clearTimeout,Blob,Response,DecompressionStream};
const ctx=vm.createContext(context);vm.runInContext(code,ctx);
const file=b=>({size:b.length,arrayBuffer:async()=>Uint8Array.from(b).buffer});
(async()=>{
  const pair=await ctx.loadFirmwarePair([file(archive)]);
  assert.equal(pair.source,'preparation');assert.equal(pair.d.version.join('.'),'4.3.0.0');
  assert.equal(pair.m.version.join('.'),'4.2.1.0');assert.equal(pair.d.archiveHash,sha(archive));
  assert.equal(pair.m.archiveHash,sha(archive));assert.deepEqual([...pair.d.data],[...d]);assert.deepEqual([...pair.m.data],[...m]);
  const tampered=Buffer.from(archive);tampered[tampered.length-1]^=1;
  await assert.rejects(ctx.loadFirmwarePair([file(tampered)]),/does not match the reviewed preparation archive/);
  await assert.rejects(ctx.loadFirmwarePair([]),/one reviewed ZIP or exactly two DAT/);
  console.log('Firmware archive: exact archive allowlist, narrow local-header parsing, deflate extraction and raw hashes passed');
})().catch(error=>{console.error(error);process.exit(1);});
