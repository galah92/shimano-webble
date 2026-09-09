// Test the exact single-file app implementation; no vendor binaries checked in.
const fs = require('node:fs');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const {webcrypto} = require('node:crypto');
const html = fs.readFileSync(require('node:path').join(__dirname, '../index.html'), 'utf8');
const code = html.split('// BEGIN FIRMWARE FILE CHECKS')[1].split('// END FIRMWARE FILE CHECKS')[0];
const context = vm.createContext({Uint8Array, crypto: webcrypto});
vm.runInContext(code, context);
const {firmwareHeader: header, firmwarePairRequirements: pair, checkFirmwarePair: check} = context;
function d(v, min) {
  const bytes = new Uint8Array(256); bytes.fill(255, 0, 16);
  bytes.set([34,0,4],40);bytes.set(v,16);bytes.set(min,47);return bytes;
}
function m(v,min) {
  const bytes = new Uint8Array(256);bytes.set([255,255,34,0],12);
  bytes.set(v,8);bytes.set(min,16);return bytes;
}
const oldD=d([0x43,0,0],[0x42,0,0]),oldM=m([0x42,1,0],[0x42,0,0]);
const newD=d([0x45,0,0],[0x44,8,0]),newM=m([0x44,8,0],[0x44,6,0]);
assert(pair(header(oldD),header(oldM)));
assert(pair(header(newD),header(newM)));
assert(!pair(header(oldD),header(newM)));
assert(!pair(header(newD),header(oldM)));
assert.throws(()=>pair(header(oldD),header(oldD)),/one D/);
assert.throws(()=>header(new Uint8Array(255)),/raw DAT/);
assert.throws(()=>header(new Uint8Array(256)),/Unrecognized/);
const file = bytes => ({size:bytes.length,arrayBuffer:async()=>Uint8Array.from(bytes).buffer,name:'misleading.dat'});
(async()=>{
  await assert.rejects(check([]),/exactly two/);
  await assert.rejects(check([file(oldD),file(oldM)]),/reviewed/);
  await assert.rejects(check([{size:33*1024*1024,arrayBuffer:()=>{throw Error('must not read');}},file(oldM)]),/size/);
  // Optional private image integration: D-prep M-prep D-restoration M-restoration.
  if(process.argv.length>2) {
    assert.equal(process.argv.length,6);
    const images=process.argv.slice(2).map(p=>new Uint8Array(fs.readFileSync(p)));
    const prep=await check(images.slice(0,2).reverse().map(file));
    assert.equal(prep.source,'preparation');assert.equal(prep.dVersion,'4.3.0.0');assert.equal(prep.mVersion,'4.2.1.0');assert.equal(prep.installable,false);
    const restore=await check(images.slice(2).map(file));
    assert.equal(restore.source,'restoration');assert.equal(restore.dVersion,'4.5.0.0');assert.equal(restore.mVersion,'4.4.8.0');
    await assert.rejects(check([file(images[0]),file(images[3])]),/Mixed/);
    await assert.rejects(check([file(images[0]),file(images[0])]),/one D/);
    images[0][100]^=1;
    await assert.rejects(check(images.slice(0,2).map(file)),/reviewed/);
  }
  console.log('Firmware file checks passed');
})().catch(e=>{console.error(e);process.exit(1);});
