const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict'),path=require('node:path');
const html=fs.readFileSync(path.join(__dirname,'../index.html'),'utf8');
const ctx=vm.createContext({Uint8Array});
vm.runInContext(html.split('// BEGIN FIRMWARE PACKET ENCODERS')[1].split('// END FIRMWARE PACKET ENCODERS')[0],ctx);
const vectors=JSON.parse(fs.readFileSync(path.join(__dirname,'m_rewrite_vectors.json'),'utf8'));
for(const v of vectors){
 const data=Uint8Array.from({length:v.length},(_,i)=>(i*37+11)&255);
 const failed=v.length===116320?116288:v.length===2048?1920:v.length===65?64:v.offset;
 const packet=ctx.firmwareMRewriteBlock(data,failed,v.offset,v.sequence);
 assert.equal(Buffer.from(packet.slice(1)).toString('hex'),v.payload_hex);
 if(v.length===116320){
  assert.throws(()=>ctx.firmwareBlock(data,'M',v.offset,0),/aligned/);
  assert.equal(packet[68],data.slice(115712).reduce((a,b)=>(a+b)&255,0));
  assert.throws(()=>ctx.firmwareMRewriteBlock(data,failed,116288,0),/rewrite sequence/);
 }
}
const data=new Uint8Array(116320);
assert.equal(ctx.firmwareMRewriteBlock(data,116288,116256,0).length,71,'zero checksum retains checkpoint marker');
for(const [failed,offset,seq] of [[-1,0,0],[data.length,0,0],[1.5,0,0],[116288,115712,0],[116288,116320,0],[116288,116256,256]])
 assert.throws(()=>ctx.firmwareMRewriteBlock(data,failed,offset,seq));
console.log('M partial rewrite: Java payload vectors, final-window checksum, alignment and range checks passed');
