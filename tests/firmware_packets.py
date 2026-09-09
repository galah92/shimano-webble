"""Cross-check deployed JS encoders against Python codecs validated with Java oracles."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from plan_d_transfer import block_payload as d_block
from plan_m_transfer import block_payload as m_block

ROOT = Path(__file__).resolve().parents[1]
NODE = r'''
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict'),crypto=require('node:crypto');
const html=fs.readFileSync('index.html','utf8');
const ctx=vm.createContext({Uint8Array});
vm.runInContext(html.split('// BEGIN FIRMWARE PACKET ENCODERS')[1].split('// END FIRMWARE PACKET ENCODERS')[0],ctx);
const encode=ctx.firmwareBlock;
assert.throws(()=>encode(new Uint8Array(64),'D',1,0),/aligned/);
assert.throws(()=>encode(new Uint8Array(64),'M',0,256),/sequence/);
assert.throws(()=>encode(new Uint8Array(196609),'D',0,0),/range/);
assert.throws(()=>encode(new Uint8Array(262145),'M',0,0),/range/);
assert.throws(()=>encode(new Uint8Array(64),'X',0,0),/range/);
const cases=JSON.parse(fs.readFileSync(0,'utf8'));
const results=cases.map(c=>{
 const data=new Uint8Array(Buffer.from(c.hex,'hex')),hash=crypto.createHash('sha256');
 for(let offset=0;offset<data.length;offset+=64) hash.update(encode(data,c.component,offset,(offset/64*7+251)&255));
 return {hash:hash.digest('hex'),geometry:ctx.firmwareTransferGeometry(data,c.component)};
});
console.log(JSON.stringify(results));
'''
cases=[]
for component, maximum in [('D',196608),('M',262144)]:
    for length in [1,63,64,65,1023,1024,1025,65536,65537,131073,maximum]:
        cases.append((component,bytes((i*17+3)&255 for i in range(length))))
    cases.append((component,bytes(1024))) # zero checksum must still carry checkpoint marker
# Optional pairs of component name and private file path; no binary fixtures committed.
args=sys.argv[1:]
assert len(args)%2==0
for component,path in zip(args[::2],args[1::2]):
    cases.append((component,Path(path).read_bytes()))
result=subprocess.run(['node','-e',NODE],cwd=ROOT,input=json.dumps([
    dict(component=c,hex=data.hex()) for c,data in cases]),text=True,capture_output=True,check=True)
for (component,data),actual in zip(cases,json.loads(result.stdout),strict=True):
    digest=hashlib.sha256()
    for offset in range(0,len(data),64):
        seq=(offset//64*7+251)&255
        payload,_=d_block(data,offset//64,seq) if component=='D' else m_block(data,offset,seq)
        digest.update(bytes([11])+payload)
    assert actual['hash']==digest.hexdigest(),(component,len(data))
    assert actual['geometry']==dict(blocks=(len(data)+63)//64,padding=(-len(data))%64,
        checksum=sum(data)&255,checkpoints=(len(data)+1023)//1024 if component=='M' else 0)
print(f'{len(cases)} complete packet streams match Python codecs, including boundary and sequence-wrap cases')
