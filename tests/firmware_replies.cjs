const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const root=require('node:path').join(__dirname,'..');
const html=fs.readFileSync(root+'/index.html','utf8');
const ctx=vm.createContext({Uint8Array});
vm.runInContext(html.split('// BEGIN FIRMWARE PACKET ENCODERS')[1].split('// END M FIRMWARE REPLIES')[0],ctx);
const raw=s=>Uint8Array.from(Buffer.from(s,'hex'));
const plain=v=>JSON.parse(JSON.stringify(v));
const vectors=JSON.parse(fs.readFileSync(__dirname+'/m_envelope_vectors.json','utf8'));
for(const v of vectors) {
 const actual=ctx.mFirmwareEnvelopes(raw(v.raw)).map(c=>[c.protocol,Buffer.from(c.payload).toString('hex')]);
 assert.deepEqual(plain(actual),v.envelopes,v.raw);
}
for(const encoded of ['0b00c007','000b00c007','bb0b00c007d3bb']) {
 const w=ctx.mFirmwareReplyWindow(8,7);
 assert.equal(w.receive(raw(encoded)).state,'evidence-complete');
 assert.equal(w.status().installable,false);
}
for(const order of [['0b00c007','f20031'],['f20031','0b00c007']]) {
 const w=ctx.mFirmwareReplyWindow(8,7,true);
 assert.equal(w.receive(raw(order[0])).state,'waiting');
 assert.equal(w.receive(raw(order[1])).state,'evidence-complete');
 assert.equal(w.status().checksumCorrelated,false);
 assert.equal(w.receive(raw('0b00830801')).state,'failed');
 assert.equal(w.receive(raw('f20031')).state,'failed');
}
const w=ctx.mFirmwareReplyWindow(8,7,true);
for(const packet of ['0b009107','0b009207','0b00c008','0b00830701','0b00830800'])
 assert.equal(w.receive(raw(packet)).state,'waiting',packet);
assert.equal(w.receive(raw('0b00c007f20032')).state,'failed');
assert.equal(w.receive(raw('f20031')).state,'failed');
assert.equal(w.close().state,'failed');
const t=ctx.mFirmwareReplyWindow(8,7);
assert.equal(t.close('timeout').error,'timeout');
assert.equal(t.receive(raw('0b00c007')).state,'failed');
const a=ctx.mFirmwareReplyWindow(8,7);a.receive(raw('0b00c007'));a.close();
const b=ctx.mFirmwareReplyWindow(10,9);
assert.equal(b.receive(raw('0b00c007')).state,'waiting');
assert.equal(b.close().error,'incomplete-reply');
assert.throws(()=>ctx.mFirmwareReplyWindow(256,7),/unsigned/);
assert.equal(ctx.mFirmwareEvents(11,raw('f20000f20031'),8,7,true).length,0);
console.log(`${vectors.length} Java envelope vectors and M reply ordering/failure cases passed`);
