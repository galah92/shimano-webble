const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const src=fs.readFileSync(__dirname+'/../index.html','utf8');
const ctx=vm.createContext({});vm.runInContext(src.split('// BEGIN REGION COMPATIBILITY')[1].split('// END REGION COMPATIBILITY')[0],ctx);
const prepared=()=>Object.entries({
 'Drive-unit model':[0,1,30,34,0], 'Drive-unit firmware':[0,1,46,67,0],
 'Current destination':[0,22,174,1,0], 'Native D firmware':[0,1,134,67,0,0],
 'Native M firmware':[0,1,134,66,1,0],
}).map(([name,fields])=>({name,fields,status:'reply received'}));
assert(ctx.regionCompatibility(prepared()).directWriteEligible);
const original=prepared();original[1].fields[3]=69;original[3].fields[3]=69;original[4].fields[3]=68;original[4].fields[4]=8;
assert(ctx.regionCompatibility(original).motorEligible);assert(!ctx.regionCompatibility(original).directWriteEligible);
for(let i=0;i<5;i++) {
 const missing=prepared();missing.splice(i,1);assert(!ctx.regionCompatibility(missing).directWriteEligible);
 const error=prepared();error[i].status='device error';assert(!ctx.regionCompatibility(error).directWriteEligible);
 const short=prepared();short[i].fields.pop();assert(!ctx.regionCompatibility(short).directWriteEligible);
 for(let j=0;j<prepared()[i].fields.length;j++) {
  if(i===2&&j===4)continue;
  const changed=prepared();changed[i].fields[j]^=1;assert(!ctx.regionCompatibility(changed).directWriteEligible);
 }
}
const badRegion=prepared();badRegion[2].fields[4]=255;assert(!ctx.regionCompatibility(badRegion).directWriteEligible);
assert(!ctx.regionCompatibility([]).motorEligible);
console.log('Region compatibility: reviewed pair, original firmware, missing/error/truncated/mismatched responses passed');
