const assert=require('assert');
const fs=require('fs');
const vm=require('vm');
const html=fs.readFileSync(__dirname+'/../index.html','utf8');
const code=html.split('// BEGIN MAX ASSIST SPEED READS')[1].split('// END MAX ASSIST SPEED READS')[0];
const ctx={Uint8Array,bytes:value=>value instanceof Uint8Array?value:Uint8Array.from(value)};
vm.createContext(ctx);vm.runInContext(code,ctx);

assert.deepEqual([...ctx.maxAssistSpeedReadPacket()],[0,0x16,0xb4,0]);
assert.deepEqual([...ctx.destinationMaxAssistSpeedReadPacket(1)],[0,0x16,0xbc,1]);
assert.equal(ctx.parseMaxAssistSpeedReply(Uint8Array.of(0,0x16,0xb6,0xc4,0x09)),2500);
assert.equal(ctx.parseMaxAssistSpeedReply(Uint8Array.of(0,0x16,0xbe,1,0x80,0x0c),1),3200);
assert.equal(ctx.formatMaxAssistSpeed(2500),'25 km/h');
assert.equal(ctx.formatMaxAssistSpeed(2450),'24.50 km/h');
for(const bad of [Uint8Array.of(0,0x16,0xb7,0x3a),Uint8Array.of(0,0x16,0xb6,0x80),
  Uint8Array.of(0,0x16,0xbe,0,0x80,0x0c),Uint8Array.of(0,0x16,0xb6,0xff,0xff)])
  assert.throws(()=>ctx.parseMaxAssistSpeedReply(bad,bad[2]===0xbe?1:undefined));
for(const destination of [-1,6,1.5])assert.throws(()=>ctx.destinationMaxAssistSpeedReadPacket(destination));
console.log('Maximum-assist-speed read packets, parsing, bounds, and formatting passed');
