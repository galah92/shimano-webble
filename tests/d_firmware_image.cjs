const fs = require('node:fs'), vm = require('node:vm'), assert = require('node:assert/strict');
const html = fs.readFileSync(require('node:path').join(__dirname, '../index.html'), 'utf8');
const code = html.split('// BEGIN FIRMWARE PACKET ENCODERS')[1].split('// END D FIRMWARE IMAGE WORKER')[0];
async function run(length, failure) {
  const ctx = vm.createContext({Uint8Array, Error, setTimeout, clearTimeout});
  vm.runInContext(code, ctx);
  const data = Uint8Array.from({length}, (_, i) => (i * 17 + 3) & 255), original = data.slice();
  const controller = new AbortController();
  let listener, removed = 0, registered = 0, block = 0, lastData, result, error;
  const writes = [];
  try {
    result = await ctx.sendDFirmwareImage({data, signal: controller.signal,
      subscribe(fn) {
        assert.equal(listener, undefined, 'Only one reply window may own the transport');
        listener = fn; registered++;
        return () => { listener = undefined; removed++; };
      },
      async write(packet) {
        const p = [...packet]; writes.push(p);
        if (writes.length === 1) data.fill(0); // Caller mutation cannot change the image.
        if (p[0] === 0x88) {
          assert(listener);
          listener(Uint8Array.of(0x88, failure === 'setup' ? 0x32 : 0x31, 0, 0));
        } else if (p[2] === 2) {
          assert.equal(listener, undefined);
          assert.equal(p.length, 71);
          assert.equal(p[1], (block * 2) & 255);
          assert.equal(p[69] | (p[70] << 8), block);
          const chunk = Array.from({length: 64}, (_, i) => original[block * 64 + i] ?? 255);
          assert.deepEqual(p.slice(4, 68), chunk);
          assert.equal(p[68], chunk.reduce((a, b) => a + b, 0) & 255);
          lastData = p[1];
          if (failure === 'data' && block === 3) throw new Error('uncertain data write');
          if (failure === 'abort' && block === 3) controller.abort();
        } else {
          assert(listener);
          assert.deepEqual(p, [11, (block * 2 + 1) & 255, 3, lastData]);
          listener(Uint8Array.of(11, 0, 192, lastData));
          const index = block + 1;
          listener(Uint8Array.of(136, failure === 'query' && block === 3 ? 50 : 49, index & 255, index >> 8));
          block++;
        }
      },
    });
  } catch (e) { error = e; }
  assert.equal(listener, undefined); assert.equal(removed, registered);
  return {writes, result, error, original};
}
(async () => {
  for (const length of [1, 64, 65, 65536, 65537, 132072, 138072, 196608]) {
    const {writes, result, error, original} = await run(length);
    assert.equal(error, undefined);
    const blocks = Math.ceil(length / 64);
    assert.equal(result.blocks, blocks); assert.equal(result.state, 'data-phase-complete');
    assert.equal(result.checksum, original.reduce((a, b) => a + b, 0) & 255);
    assert.equal(result.installable, false); assert.equal(result.finished, false); assert.equal(result.reset, false);
    const expected = [[136, 33, 0, Math.floor((length - 1) / 2048), 0], [136, 10, 0, 0, 0], [136, 36, 0, 64, 0]];
    for (let bank = 1; bank * 1024 < blocks; bank++) expected.push([136, 36, 0, 64, bank], [136, 10, bank, 0, 0]);
    assert.deepEqual(writes.filter(p => p[0] === 136), expected);
    assert.equal(writes.length, expected.length + blocks * 2);
    for (const bank of [1, 2]) if (bank * 1024 < blocks) {
      const at = writes.findIndex(p => p[0] === 136 && p[1] === 36 && p[4] === bank);
      assert.equal(writes[at - 1][2], 3); assert.equal(writes[at + 2][2], 2);
      assert.equal(writes[at + 2][69] | writes[at + 2][70] << 8, bank * 1024);
    }
  }
  for (const failure of ['setup', 'data', 'query', 'abort']) {
    const {writes, error} = await run(132072, failure);
    assert(error, failure);
    assert.equal(writes.length, {setup: 1, data: 10, query: 11, abort: 10}[failure]);
  }
  for (const length of [0, 196609]) {
    const {writes, error} = await run(length); assert(error); assert.equal(writes.length, 0);
  }
  console.log('D full-image sequencing, bank transitions, padding, checksum, snapshot and fail-stop tests passed');
})().catch(e => { console.error(e); process.exit(1); });
