const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const src=fs.readFileSync(__dirname+'/../index.html','utf8');
const ctx=vm.createContext({});vm.runInContext(src.split('// BEGIN REGION COMPATIBILITY')[1].split('// END REGION COMPATIBILITY')[0],ctx);
const prepared=()=>Object.entries({
 'Drive-unit model':[0,1,30,34,0], 'Drive-unit firmware':[0,1,46,67,0],
 'Current destination':[0,22,174,1,0,0x21,0x43,0x65,0x87], 'Native D firmware':[0,1,134,67,0,0],
 'Native M firmware':[0,1,134,66,1,0],
}).map(([name,fields])=>({name,fields,status:'reply received'}));
assert(ctx.regionCompatibility(prepared()).motorEligible);
assert(!ctx.regionCompatibility(prepared()).directWriteEligible);
const original=prepared();original[1].fields[3]=69;original[3].fields[3]=69;original[4].fields[3]=68;original[4].fields[4]=8;
assert(ctx.regionCompatibility(original).motorEligible);assert(ctx.regionCompatibility(original).directWriteEligible);
assert(ctx.regionCompatibility(original).commandWriteEligible);
const checkedLengths=[5,5,5,6,6];
for(let i=0;i<5;i++) {
 const missing=original.map(x=>({name:x.name,status:x.status,fields:[...x.fields]}));missing.splice(i,1);assert(!ctx.regionCompatibility(missing).directWriteEligible);
 const error=original.map(x=>({name:x.name,status:x.status,fields:[...x.fields]}));error[i].status='device error';assert(!ctx.regionCompatibility(error).directWriteEligible);
 const short=original.map(x=>({name:x.name,status:x.status,fields:[...x.fields]}));short[i].fields.pop();assert(!ctx.regionCompatibility(short).directWriteEligible);
 for(let j=0;j<checkedLengths[i];j++) {
  if(i===2&&j===4)continue;
  const changed=original.map(x=>({name:x.name,status:x.status,fields:[...x.fields]}));changed[i].fields[j]^=1;assert(!ctx.regionCompatibility(changed).directWriteEligible);
 }
}
const changedOpaqueTail=original.map(x=>({name:x.name,status:x.status,fields:[...x.fields]}));
changedOpaqueTail[2].fields[8]^=1;
assert(ctx.regionCompatibility(changedOpaqueTail).directWriteEligible);
const badRegion=original.map(x=>({name:x.name,status:x.status,fields:[...x.fields]}));badRegion[2].fields[4]=255;assert(!ctx.regionCompatibility(badRegion).directWriteEligible);
assert(!ctx.regionCompatibility([]).motorEligible);
console.log('Region compatibility: exact D4.5/M4.4.8 command path and malformed responses passed');
