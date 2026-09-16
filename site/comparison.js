// Local comparison UI. All records and icons ship in this document.
let viewMode='trees',treeVersion='forever',statusFilter='different',showExtra=false,showPassive=false;
const statusNames={added:'New in Forever',removed:'Removed from tree',changed:'Changed',unchanged:'Unchanged',extra:'Additional client entry'};
const originalSetClass=setClass,originalRenderTrees=renderTrees,originalRenderDetail=renderDetail;
const versionTrees=()=>treeVersion==='classic'?currentClass.classicTrees:currentClass.trees;
const visibleExtras=()=>treeVersion==='classic'?[]:currentClass.extraTalents;
inspectTrees=function(){return [...versionTrees(),...(visibleExtras().length?[{id:'extra',name:'Additional client nodes',talents:visibleExtras(),edges:[]}]:[])]};
$('trees').insertAdjacentHTML('beforebegin',`<div class="view-toolbar"><div class="view-tabs" aria-label="View"><button class="view-tab active" data-view="trees">Talent trees</button><button class="view-tab" data-view="talents">Talent comparison</button><button class="view-tab" data-view="spells">Class spells</button></div><div class="version-switch"><button class="version-btn active" data-version="forever">Forever</button><button class="version-btn" data-version="classic">Classic Era</button></div></div><div class="tree-legend"><span>New</span><span>Changed</span><span>Removed (Classic)</span><span>Unchanged in this comparison</span></div><section id="comparison-view" class="comparison-view" hidden aria-label="Comparison"></section>`);

renderTrees=function(){
 // The original renderer only needs a temporary view of the selected tree set.
 const savedTrees=currentClass.trees,savedExtras=currentClass.extraTalents;
 currentClass.trees=versionTrees();currentClass.extraTalents=visibleExtras();
 originalRenderTrees();currentClass.trees=savedTrees;currentClass.extraTalents=savedExtras;
 document.querySelectorAll('.tree .talent').forEach(btn=>{
  const change=currentClass.talentChanges.find(c=>(treeVersion==='classic'?c.classic:c.forever)?.id===Number(btn.dataset.id));
  if(change){btn.dataset.status=change.status;btn.title+=' · '+statusNames[change.status]}
 });
};
setClass=function(id,updateHash=true){
 // Original selection always starts from the Forever tree; temporarily use the
 // selected version for its automatic first-node selection as well.
 const requested=DATA.classes.find(c=>c.id===Number(id))||DATA.classes[0];
 const was=treeVersion;treeVersion='forever';originalSetClass(id,updateHash);treeVersion=was;
 if(treeVersion==='classic'){renderTrees();selectTalent(versionTrees()[0].talents[0].id,false)}
 $('details').classList.remove('open');renderMode();
};
renderDetail=function(){
 originalRenderDetail();
 if(selectedTalent.classic){
  const link=$('detail-content').querySelector('.source-link');link.href=`https://wago.tools/db2/Talent?build=${DATA.classicBuild}&filter[ID]=${-selectedTalent.id}`;
  $('detail-content').querySelector('.eyebrow').textContent='Classic Era · Talent details';
 }
 const change=currentClass.talentChanges.find(c=>(selectedTalent.classic?c.classic:c.forever)?.id===selectedTalent.id);
 if(change){
  $('detail-content').insertAdjacentHTML('beforeend',`<div class="detail-comparison"><button id="jump-comparison">${esc(statusNames[change.status])} · Classic ↔ Forever</button><p>${esc(change.differences.join(' · ')||'Direct comparison of both snapshots.')}</p></div>`);
  $('jump-comparison').onclick=()=>{viewMode='talents';statusFilter='all';$('search').value=change.name;closeDetail();renderMode();const row=$('comparison-view').querySelector('.comparison-row');if(row){row.open=true;fillRow(row)}};
 }
};

function renderMode(){
 document.querySelector('.app').classList.toggle('compare-mode',viewMode!=='trees');
 document.querySelectorAll('[data-view]').forEach(b=>{b.classList.toggle('active',b.dataset.view===viewMode);b.setAttribute('aria-pressed',b.dataset.view===viewMode)});
 document.querySelectorAll('[data-version]').forEach(b=>{b.classList.toggle('active',b.dataset.version===treeVersion);b.setAttribute('aria-pressed',b.dataset.version===treeVersion)});
 $('trees').hidden=viewMode!=='trees';$('comparison-view').hidden=viewMode==='trees';document.querySelector('.version-switch').hidden=viewMode!=='trees';document.querySelector('.tree-legend').hidden=viewMode!=='trees';
 $('search').placeholder=viewMode==='spells'?'Search spells or spell IDs …':'Search talents …';$('search').setAttribute('aria-label',viewMode==='spells'?'Search class spells':'Search talents');
 $('class-sub').textContent=viewMode==='trees'?`${treeVersion==='classic'?'Classic Era':'WoW Forever'} · 3 Talent trees · ${versionTrees().reduce((n,t)=>n+t.talents.length,0)} talents`:`Classic Era ${DATA.classicBuild} ↔ Forever ${DATA.build}`;
 if(viewMode!=='trees')renderComparison();else filterTrees();
}
function filterTrees(){const q=$('search').value.toLocaleLowerCase().trim();let found=0;inspectTrees().forEach(tree=>tree.talents.forEach(t=>{const match=!q||t.entries.some(e=>(e.name+' '+e.description+' '+e.spellID).toLocaleLowerCase().includes(q));document.querySelector(`.talent[data-id="${t.id}"]`)?.classList.toggle('dim',!match);if(match)found++}));$('search-summary').textContent=q?`${found} matches in ${currentClass.name}`:''}
// Replace the original search listener with a mode-aware input, preserving focus.
const oldSearch=$('search'),newSearch=oldSearch.cloneNode(true);oldSearch.replaceWith(newSearch);
newSearch.addEventListener('input',()=>viewMode==='trees'?filterTrees():renderComparison());
document.querySelectorAll('[data-view]').forEach(btn=>btn.onclick=()=>{viewMode=btn.dataset.view;$('search').value='';$('search-summary').textContent='';renderMode()});
document.querySelectorAll('[data-version]').forEach(btn=>btn.onclick=()=>{treeVersion=btn.dataset.version;renderTrees();selectTalent(versionTrees()[0].talents[0].id,false);renderMode()});

function eligibleRecords(){return viewMode==='talents'?currentClass.talentChanges:currentClass.spells.filter(r=>(showExtra||!r.extra)&&(showPassive||(!r.passive&&!r.talent)))}
function recordSearch(r){return viewMode==='talents'?[r.name,r.classic?.entries[0].description,r.forever?.entries[0].description,r.classic?.entries[0].spellID,r.forever?.entries[0].spellID].join(' ').toLocaleLowerCase():[r.name,...(r.previousNames||[]),...r.pairs.flatMap(p=>[p.spellID,p.classic?.description,p.forever?.description])].join(' ').toLocaleLowerCase()}
function renderComparison(){
 const all=eligibleRecords(),q=$('search').value.toLocaleLowerCase().trim(),counts={};all.forEach(r=>counts[r.status]=(counts[r.status]||0)+1);
 const records=all.filter(r=>(statusFilter==='all'||statusFilter==='different'&&r.status!=='unchanged'||r.status===statusFilter)&&(!q||recordSearch(r).includes(q)));
 const isSpell=viewMode==='spells';
 $('comparison-view').innerHTML=`<p class="compare-intro">${isSpell?`Spells from class skill lines, grouped by name and spell ID. The Classic spell list is based on the client before Season of Discovery. <strong>New client entries do not confirm in-game availability.</strong> Values are character-independent base values. General damage amounts and effect comparisons use the mean; explicit minimum/maximum expressions retain their bounds.`:`All regular talents from both versions. The comparison covers tree positions, prerequisites, rank counts and resolved descriptions for every rank. <strong>“Removed” means absent from the regular Forever talent tree.</strong> A renamed or substantially replaced ability may appear separately.`}</p><div class="compare-summary">${['added','changed','removed','unchanged'].map(s=>`<span class="summary-chip"><b>${counts[s]||0}</b>${s==='removed'&&isSpell?'Not assigned':statusNames[s]}</span>`).join('')}</div><div class="compare-controls"><select id="status-filter" aria-label="Filter differences">${[['different','Differences only'],['all','All entries'],['added','New in Forever'],['changed','Changed'],['removed',isSpell?'No longer assigned':'Removed from tree'],['unchanged','Unchanged'],...(isSpell&&showExtra?[['extra','Additional client entries']]:[])].map(([v,label])=>`<option value="${v}" ${statusFilter===v?'selected':''}>${label}</option>`).join('')}</select>${isSpell?`<label><input id="show-passive" type="checkbox" ${showPassive?'checked':''}> Passives / talent spells</label><label><input id="show-extra" type="checkbox" ${showExtra?'checked':''}> Seasonal / extra client data</label>`:''}<span class="results-count">${records.length} ${isSpell?'Spell groups':'Talents'} shown</span></div><div class="comparison-list">${records.map((r,i)=>{const e=isSpell?r:(r.forever||r.classic).entries[0];const image=e.icon||DATA.icons?.[e.iconID];return `<details class="comparison-row status-${r.status}" data-record="${i}"><summary>${image?`<img class="compare-icon" src="${image}" alt="" loading="lazy">`:''}<div><div class="compare-name">${esc(r.name)}</div><div class="compare-caption">${esc(isSpell?`${r.pairs.length} Ranks / variants${r.talent?' · Talent spell':r.passive?' · Passive':''}`:[r.classic?.tree,r.forever?.tree].filter((s,i,a)=>s&&a.indexOf(s)===i).join(' → '))}${r.differences.length?' · '+esc(r.differences.slice(0,3).join(' · ')):''}</div></div><span class="compare-label">${esc(r.status==='removed'&&isSpell?'Not assigned':statusNames[r.status])}</span></summary><div class="compare-body"></div></details>`}).join('')||'<div class="compare-empty">No matching entries. Choose “All entries” or change your search.</div>'}</div>`;
 $('comparison-view')._records=records;
 $('status-filter').onchange=e=>{statusFilter=e.target.value;renderComparison()};
 if(isSpell){$('show-passive').onchange=e=>{showPassive=e.target.checked;renderComparison()};$('show-extra').onchange=e=>{showExtra=e.target.checked;if(!showExtra&&statusFilter==='extra')statusFilter='different';renderComparison()}}
 $('comparison-view').querySelectorAll('.comparison-row').forEach(row=>row.addEventListener('toggle',()=>{if(row.open&&!row.dataset.filled)fillRow(row)}));
 $('search-summary').textContent=q?`${records.length} matches in ${currentClass.name}`:'';
}
function rankDescription(rank){return `<p class="description">${esc(rank.description)}</p>${rank.unresolved?'<div class="note">Dynamic client expressions are not fully resolved.</div>':''}`}
function highlightDescriptions(container){
 const a=container.querySelector('.classic-side .description'),b=container.querySelector('.forever-side .description');if(!a||!b)return;
 const x=a.textContent.split(/(\s+)/),y=b.textContent.split(/(\s+)/);if(x.length*y.length>350000)return;
 const dp=Array.from({length:x.length+1},()=>new Uint16Array(y.length+1));
 for(let i=x.length-1;i>=0;i--)for(let j=y.length-1;j>=0;j--)dp[i][j]=x[i]===y[j]?dp[i+1][j+1]+1:Math.max(dp[i+1][j],dp[i][j+1]);
 let i=0,j=0,old=[],fresh=[];
 while(i<x.length||j<y.length){if(i<x.length&&j<y.length&&x[i]===y[j]){old.push(esc(x[i++]));fresh.push(esc(y[j++]))}else if(i<x.length&&(j===y.length||dp[i+1][j]>=dp[i][j+1]))old.push(`<mark class="old">${esc(x[i++])}</mark>`);else fresh.push(`<mark class="new">${esc(y[j++])}</mark>`)}
 a.innerHTML=old.join('');b.innerHTML=fresh.join('');
}
function talentSide(t,side){
 const title=side==='classic'?'Classic Era':'WoW Forever';
 if(!t)return `<div class="pair-side ${side}-side"><h4>${title}</h4><p class="sub">No matching talent in the regular tree.</p></div>`;
 const e=t.entries[0],max=e.maxRanks;
 return `<div class="pair-side ${side}-side"><h4>${title}</h4><h5>${esc(e.name)}</h5><div class="sub">${esc(t.tree)} · Row ${t.row+1} · ${max} ${max===1?'rank':'ranks'} · ${t.requiredPoints} points</div><div class="rank-label"><span>View rank</span><span>Spell ${e.spellID}</span></div><select data-side-rank="${side}" aria-label="${title} Talent rank">${e.ranks.map(r=>`<option value="${r.rank-1}" ${r.rank===max?'selected':''}>Rank ${r.rank} / ${max}</option>`).join('')}</select><div class="rank-text">${rankDescription(e.ranks[max-1])}</div>${e.baseValueNotice?'<div class="note">Damage and healing are client base values; level, gear and talents can modify them.</div>':''}${t.prerequisites?.length?`<p class="sub">${t.prerequisiteMode==='any'?'Requires one of':'Requires'}: ${t.prerequisites.map(esc).join('; ')}</p>`:''}${e.curveNotice?`<div class="note">${esc(e.curveNotice)}</div>`:''}${t.conditionNote?`<div class="note">${esc(t.conditionNote)}</div>`:''}<details class="raw-text"><summary>Original client text</summary><pre>${esc(e.description)}</pre></details></div>`;
}
function spellSide(r,side){
 const title=side==='classic'?'Classic Era':'WoW Forever';
 if(!r)return `<div class="pair-side ${side}-side"><h4>${title}</h4><p class="sub">This spell ID is not assigned to the class spell list in this snapshot.</p></div>`;
 return `<div class="pair-side ${side}-side"><h4>${title}</h4><h5>${esc(r.name)}</h5><div class="sub">${esc(r.subtext||'No rank label')} · Spell ${r.spellID} · ${esc(r.skill)}</div><div class="spell-metrics">${Object.entries(r.metrics).map(([k,v])=>`<div><small>${esc(k)}</small>${esc(v)}</div>`).join('')}</div>${rankDescription(r)}${r.candidate?'<div class="note">New assignment in the Forever client. Availability and learning method are not confirmed by these data alone.</div>':''}<details class="raw-text"><summary>Original client text</summary><pre>${esc(r.rawDescription)}</pre></details></div>`;
}
function fillRow(row){
 const r=$('comparison-view')._records[Number(row.dataset.record)],body=row.querySelector('.compare-body');row.dataset.filled='true';
 if(viewMode==='talents'){
  body.innerHTML=`${r.differences.length?`<div class="diff-notes">${r.differences.map(esc).join('<br>')}</div>`:''}<div class="pair-columns">${talentSide(r.classic,'classic')}${talentSide(r.forever,'forever')}</div>`;
  const updateRanks=()=>{body.querySelectorAll('[data-side-rank]').forEach(sel=>{const e=r[sel.dataset.sideRank].entries[0];sel.parentElement.querySelector('.rank-text').innerHTML=rankDescription(e.ranks[Number(sel.value)])});highlightDescriptions(body)};
  body.querySelectorAll('[data-side-rank]').forEach(sel=>sel.onchange=updateRanks);updateRanks();
 }else{
  body.innerHTML=`${r.extra?'<div class="note">This entry already existed in the Era/SoD client but is outside the Classic baseline. It is not counted as a new Forever ability. Active use is unclear.</div>':''}<div class="compare-row-rank"><span>Rank / variant</span><select class="spell-rank" aria-label="Spell rank comparison">${r.pairs.map((p,i)=>{const x=p.forever||p.classic;return `<option value="${i}" ${i===r.pairs.length-1?'selected':''}>${esc(x.subtext||'Variant')} · Level ${x.metrics.Level} · ID ${p.spellID}</option>`}).join('')}</select></div><div class="spell-pair"></div>`;
  const renderPair=()=>{const p=r.pairs[Number(body.querySelector('.spell-rank').value)];body.querySelector('.spell-pair').innerHTML=`<div class="pair-columns">${spellSide(p.classic,'classic')}${spellSide(p.forever,'forever')}</div>${p.differences.length?`<table class="diff-table"><thead><tr><th>Change</th><th>Classic Era</th><th>Forever</th></tr></thead><tbody>${p.differences.map(d=>`<tr><td>${esc(d.field)}</td><td>${esc(d.old)}</td><td>${esc(d.new)}</td></tr>`).join('')}</tbody></table>`:'<p class="sub" style="margin-top:18px">'+(p.classic&&p.forever?'No differences in the compared text and values for this rank.':'No direct comparison is available for this spell ID.')+'</p>'}`};
  body.querySelector('.spell-rank').onchange=()=>{renderPair();highlightDescriptions(body)};renderPair();highlightDescriptions(body);
 }
}
$('source-copy').insertAdjacentHTML('afterbegin',`<p><strong>Forever client data · September 16, 2026.</strong> <a href="https://github.com/MAF2414/wow-forever-talents/blob/main/docs/audit.md" target="_blank" rel="noopener">Technical audit ↗</a></p><p><strong>Classic comparison:</strong> Talent trees and values from <a href="https://wago.tools/db2/Talent?build=${DATA.classicBuild}" target="_blank" rel="noopener">Classic Era ${DATA.classicBuild}</a>. The class spell baseline is defined using <a href="https://wago.tools/db2/SkillLineAbility?build=${DATA.referenceBuild}" target="_blank" rel="noopener">Classic ${DATA.referenceBuild} before SoD</a>. Seasonal and other extra data already present in the Era client can be displayed separately.</p><p>Talents are matched by spell ID first, otherwise by identical name. Spell ranks are grouped by name and compared using matching spell IDs. “Unchanged” refers to the compared fields, not all possible server-side rules. Different spell IDs appear as separate variants. Effect base values are normalized to a shared mean-value format to avoid treating format changes as gameplay differences. Effects of triggered subspells are not recursively simulated.</p>`);
document.querySelector('.brand span').textContent='TALENTS & SPELLS';
document.title='WoW Forever ↔ Classic · Talents & class spells';
setClass(currentClass.id,false);
