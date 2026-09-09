const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const html=fs.readFileSync(require('node:path').join(__dirname,'../index.html'),'utf8');
const ctx=vm.createContext({Uint8Array});
vm.runInContext(html.split('// BEGIN FIRMWARE PACKET ENCODERS')[1].split('// END D FIRMWARE REPLIES')[0],ctx);
const vectors=JSON.parse(fs.readFileSync(__dirname+'/d_reply_vectors.json','utf8'));
for(const c of vectors) {
 const window=ctx.dFirmwareReplyWindow(7,c.block);
 for(const packet of c.packets)window.receive(Uint8Array.from(Buffer.from(packet,'hex')));
 const s=window.status();
 assert.deepEqual([s.ack,s.result,s.errorCode,s.otherBlockErrors,s.errorsAfterSuccess],c.expected,JSON.stringify(c));
 assert.equal(s.replyTimeoutMs,c.block<3?25000:3000);
 assert.equal(s.installable,false);
 assert.equal(s.state,!s.ack||s.result<0?'waiting':s.result===49?'evidence-complete':'failed');
 window.close();window.receive(Uint8Array.of(11,0,192,7));assert.deepEqual(window.status(),s);
}
assert.throws(()=>ctx.dFirmwareReplyWindow(7,3072),/Invalid/);
assert.throws(()=>ctx.dFirmwareReplyWindow(256,0),/Invalid/);
console.log(`${vectors.length} D reply cases match original Java Y6 listener`);
