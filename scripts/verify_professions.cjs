const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const path=require('node:path');
const root=path.resolve(__dirname,'..');
const data=JSON.parse(fs.readFileSync(path.join(root,'docs/professions-data.json'),'utf8'));
const record=(pid,id)=>data.records.find(r=>r.professionID===pid&&r.id===id);
assert.equal(data.professions.length,12);
assert.equal(new Set(data.records.map(r=>`${r.professionID}:${r.id}`)).size,data.records.length);
assert.equal(data.records.filter(r=>r.professionID===129&&r.category==='Healing Potions'&&r.status==='new').length,6);
assert.equal(record(171,2330).status,'removed');
assert.deepEqual(record(129,1244431).reagents,[{id:3371,count:1},{id:2678,count:1},{id:2447,count:1}]);
assert.equal(record(129,1244431).outputs[0].id,118);
assert.equal(record(164,1252229).books[0],251332);
assert.equal(data.items[251332].requiredSkillRank,35);
assert.equal(record(186,1306126).station,'Molten Foundry');
assert.equal(record(333,7771).description,'Permanently enchant a cloak to increase armor by 10.');
assert.equal(data.records.filter(r=>r.kind==='specialization'&&r.status!=='removed').length,10);
const input={value:'60'};
const scope=vm.createContext({PROFESSIONS:data,document:{getElementById:()=>input}});
const script=fs.readFileSync(path.join(root,'site/professions.js'),'utf8');
vm.runInContext(script.slice(0,script.indexOf('function effectText')),scope);
const render=(text,level)=>{input.value=String(level);scope.sample=text;return vm.runInContext('displayDescription(sample)',scope)};
const mana=data.items[279956].effects[0].description;
assert.match(render(mana,20),/10 Mana every 5 sec/);
assert.match(render(mana,60),/29 Mana every 5 sec/);
const lute=data.items[279976].effects[0].description;
assert.match(render(lute,60),/308\s+increase to Armor, 13 increase to all stats, and 22 increase to all resistances/);
for(const i of Object.values(data.items))for(const e of i.effects)for(const level of [1,9,10,19,20,23,24,39,40,49,50,59,60]){
 const text=render(e.description,level);
 assert(!text.includes('$'),`Unformatted item text ${i.id}: ${text}`);
 if(e.description.includes('$?pc142418'))assert(text.includes('Conditional bonus:'));
}
for(const r of data.records){
 assert.equal(new Set(r.tools).size,r.tools.length);
 assert(!render(r.description,60).includes('$'),`Unformatted recipe ${r.id}`);
 for(const x of [...r.reagents,...r.outputs])assert(data.items[x.id],`Missing item ${x.id}`);
 for(const id of r.books)assert(data.items[id],`Missing recipe book ${id}`);
}
console.log('Profession checks passed: recipe relocation, ingredients, book requirements, stations, enchants, specializations, dynamic buff boundaries and all item links.');
