/* Validate every published model with the Khronos glTF validator, plus mapping coverage. */
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const root=path.resolve(__dirname,'..'),doc=path.join(root,'docs');
const validator=require(path.join(root,'sources/gltf-validator/package'));
const d=JSON.parse(fs.readFileSync(path.join(doc,'models-data.json')));
const files=new Set(),sets=new Set();
for(const s of d.sets){
  assert(!sets.has(s.id));sets.add(s.id);
  for(const p of s.pieces){
    assert(p.itemID>0&&p.displayID>0&&p.appearanceID>0);
    for(const m of p.parts){assert(m.url,`Missing set model ${m.fileDataID}`);assert.equal(m.skippedSurfaces.length,0);files.add(m.url);}
    if(p.icon)assert(fs.existsSync(path.join(doc,p.icon)));
    for(const t of p.cloth)assert(t.url&&fs.existsSync(path.join(doc,t.url)));
  }
}
const tier=d.sets.filter(s=>s.category==='tier1');assert.equal(tier.length,18);
assert.equal(tier.flatMap(s=>s.pieces).length,108);
for(const s of tier){assert.equal(s.pieces.flatMap(p=>p.parts).filter(p=>p.url).length,3);}
for(const c of d.creatures){if(c.url){assert(c.name);assert.equal(c.skippedSurfaces.length,0);files.add(c.url);}}
assert.equal(d.bossAssignments,0);
(async()=>{
  const reports=[];
  for(const file of files){
    const report=await validator.validateBytes(new Uint8Array(fs.readFileSync(path.join(doc,file))),{uri:file,maxIssues:30});
    reports.push({file,errors:report.issues.numErrors,warnings:report.issues.numWarnings,messages:report.issues.messages});
  }
  const bad=reports.filter(r=>r.errors);const warnings=reports.filter(r=>r.warnings);
  fs.writeFileSync(path.join(root,'evidence/2026-09-16/audit/model-validation.json'),JSON.stringify(reports,null,2));
  console.log(JSON.stringify({sets:sets.size,tierSets:tier.length,uniqueGLB:files.size,errors:bad.length,warnings:warnings.length}));
  if(bad.length){console.log(JSON.stringify(bad.slice(0,3),null,2));process.exitCode=1;}
})().catch(e=>{console.error(e);process.exitCode=1;});
