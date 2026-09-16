const $=id=>document.getElementById(id);
const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const DATA=PROFESSIONS,profs=new Map(DATA.professions.map(p=>[p.id,p]));
const labels={new:'New spell ID',changed:'Changed vs. Classic',unchanged:'Unchanged vs. Classic',inherited:'Inherited ID',removed:'Classic-only record'};
const kinds={recipe:'Recipe',enchant:'Enchantment',training:'Training',specialization:'Specialization',ability:'Ability'};
const slug=p=>p.name.toLowerCase().replaceAll(' ','-');
const item=id=>DATA.items[id]||{id,name:'Item '+id,available:false,effects:[]};
const recordURL=r=>'#recipe-'+r.professionID+'-'+r.id;
const itemText=(id,old=false)=>{const i=item(id);return old?(i.classic?.name||'Item '+id):!i.available&&i.classicName?`${i.name} (Classic name; item ${id})`:i.name};
const duration=n=>n>=3600?`${+(n/3600).toFixed(2)} hr`:n>=60?`${+(n/60).toFixed(2)} min`:`${n} sec`;
let page=0;const PAGE_SIZE=30;

function displayDescription(text){
 const level=Math.min(60,Math.max(1,Number($('buff-level').value)||60));
 text=text.replace(/\$@spellicon\d+\s*/g,'');
 text=text.replace(/\$\?\$PL[<>]=?\d+\[[^\[\]]*\](?:\?\$PL[<>]=?\d+\[[^\[\]]*\])*\[[^\[\]]*\]/g,chain=>{
  const branches=[...chain.matchAll(/\?\$PL([<>]=?)(\d+)\[([^\[\]]*)\]/g)];
  for(const b of branches){const n=Number(b[2]);if(b[1]==='<'?level<n:b[1]==='>'?level>n:b[1]==='<='?level<=n:level>=n)return b[3]}
  return chain.match(/\[([^\[\]]*)\]$/)[1];
 });
 text=text.replace(/\$\?s\d+\[[^\[\]]*\](?:\?s\d+\[[^\[\]]*\])*\[([^\[\]]*)\]/g,'$1');
 text=text.replace(/\$\?pc\d+\[([^\[\]]*)\]\[\]/g,(_,s)=>'Conditional bonus: '+s.replace(/^Additionally, /,''));
 text=text.replace(/Restores \$o\d+ (health|mana)/g,'Restores $1').replace(/Heals \$o\d+ damage/g,'Heals damage');
 text=text.replace('$1249907s2 Herbalism','bonus Herbalism').replace('Ineffective against targets above level $1252546s2.','Has a target-level limit.');
 return text.replace(/\b(\d+) sec\b/g,(m,n)=>Number(n)>=60&&Number(n)%60===0?duration(Number(n)):m);
}
function effectText(e){return `<p class="description">${esc(displayDescription(e.description))}</p>${e.description.includes('$PL')?`<p class="small muted">Buff values at level ${Math.min(60,Math.max(1,Number($('buff-level').value)||60))}</p>`:''}<details><summary>Original item effect · Spell ${e.spellID}</summary><pre class="raw">${esc(e.rawDescription)}</pre></details>`}
function outputHTML(o,old=false){const raw=item(o.id),i=old?(raw.classic||{}):raw;const qty=o.min===null?'':o.min===o.max?`${o.min} × `:`${o.min}–${o.max} × `;return `<div class="output"><div class="output-name quality-${i.quality||0}">${qty}${esc(itemText(o.id,old))}</div><p class="small muted">Item ${o.id}${i.itemLevel?' · ilvl '+i.itemLevel:''}${i.requiredLevel?' · Level '+i.requiredLevel:''}${i.slot?' · '+esc(i.slot):''}${i.containerSlots?' · '+i.containerSlots+' slots':''}${!old&&!i.available?' · Item details not present':''}</p>${i.description?`<p class="description">${esc(i.description)}</p>`:''}${old?'':i.effects.map(effectText).join('')}</div>`}
function ingredientsHTML(rs){return rs.length?`<ul class="materials">${rs.map(m=>`<li><strong>${m.count} ×</strong> ${esc(itemText(m.id))}</li>`).join('')}</ul>`:'<p class="small muted">No ingredients listed.</p>'}
function referenceHTML(r){return `<details><summary>Classic recipe${r.differences.length?' · '+r.differences.map(esc).join(', '):''}</summary><h3>${esc(r.classic.name)}</h3>${r.classic.description?`<p class="description">${esc(displayDescription(r.classic.description))}</p>`:''}<p class="small">${r.classic.outputs.map(o=>`${o.min===null?'':o.min+' × '}${esc(itemText(o.id,true))} · Item ${o.id}`).join('<br>')}</p>${ingredientsHTML(r.classic.reagents)}<p class="small muted">Cast: ${duration(r.classic.castTime)} · Cooldown: ${duration(r.classic.cooldown)} · Skill-up thresholds: ${r.classic.skillupLow} / ${r.classic.skillupHigh}</p>${r.classic.tools.length?`<p class="small">Tools: ${r.classic.tools.map(esc).join(' · ')}</p>`:''}${r.classic.station?`<p class="small">Station: ${esc(r.classic.station)}</p>`:''}</details>`}
function recipeHTML(r){const p=profs.get(r.professionID);return `<article class="card" id="recipe-${r.professionID}-${r.id}"><div class="tags"><span class="tag status-${r.status}">${labels[r.status]}</span><span class="tag">${esc(p.name)}</span><span class="tag">${esc(kinds[r.kind])}</span>${r.seasonal?'<span class="tag">SoD category</span>':''}</div><h3 class="recipe-title">${esc(r.name)}${r.subtext?` <span class="small muted">${esc(r.subtext)}</span>`:''}</h3><p class="small muted">${esc(r.category||kinds[r.kind])} · Spell ${r.id}</p>${r.description?`<p class="description">${esc(displayDescription(r.description))}</p>`:''}${r.outputs.map(o=>outputHTML(o,r.status==='removed')).join('')}${r.enchantments.length?`<p class="role">${r.enchantments.map(e=>esc(e.name)).join(' · ')}</p>`:''}${['recipe','enchant'].includes(r.kind)?`<h4>Ingredients</h4>${ingredientsHTML(r.reagents)}`:''}<div class="recipe-meta">${r.castTime?`<span>Cast: ${duration(r.castTime)}</span>`:''}${r.cooldown?`<span>Cooldown: ${duration(r.cooldown)}</span>`:''}${r.skillupLow||r.skillupHigh?`<span>Skill-up thresholds: ${r.skillupLow} / ${r.skillupHigh}</span>`:''}</div>${r.tools.length?`<p class="small"><strong>Tools:</strong> ${r.tools.map(esc).join(' · ')}</p>`:''}${r.station?`<p class="role"><strong>Requires:</strong> ${esc(r.station)}</p>`:''}${r.books.length?`<details><summary>Recipe items & requirements (${r.books.length})</summary><ul class="book-list">${r.books.map(id=>{const i=item(id);return `<li>${esc(i.name)} · Item ${id}${i.requiredSkillRank?` · ${esc(profs.get(i.requiredSkill)?.name||'Profession')} ${i.requiredSkillRank}`:''}${i.requiredLevel?' · Level '+i.requiredLevel:''}${i.requiredAbilityName?' · '+esc(i.requiredAbilityName):''}${i.requiredFaction?' · '+esc(i.requiredFaction)+' '+esc(i.requiredReputation):''}</li>`}).join('')}</ul></details>`:''}${r.classic?referenceHTML(r):''}<details><summary>Spell ID & original text</summary><p>Spell ${r.id} · SkillLineAbility ${r.abilityRowID}</p><pre class="raw">${esc(r.rawDescription||'No recipe description.')}</pre></details><p class="small"><a href="${recordURL(r)}">Link to this entry →</a></p></article>`}

function matchesKind(r,k){return k==='all'||k==='camp'&&r.category==='Camping'&&['recipe','enchant'].includes(r.kind)||k==='recipes'&&['recipe','enchant'].includes(r.kind)||r.kind===k}
function matchesStatus(r,s){return s==='all'||s==='current'&&r.status!=='removed'&&!r.seasonal||s==='seasonal'&&r.seasonal||r.status===s&&!r.seasonal}
const searchable=new Map(DATA.records.map(r=>[`${r.professionID}:${r.id}`,[r.id,r.name,r.category,r.description,...r.reagents.map(m=>itemText(m.id)),...r.outputs.map(o=>itemText(o.id)),...r.books.map(id=>itemText(id)),r.station,...r.tools].join(' ').toLowerCase()]));
function render(){const pid=Number($('profession').value),k=$('kind').value,s=$('status').value,q=$('recipe-search').value.trim().toLowerCase(),exact=/^id:\d+$/.test(q)?Number(q.slice(3)):null;
 let rows=DATA.records.filter(r=>(!pid||r.professionID===pid)&&matchesKind(r,k)&&matchesStatus(r,s)&&(exact!==null?r.id===exact:!q||searchable.get(`${r.professionID}:${r.id}`).includes(q)));
 const sort=$('sort').value;rows.sort((a,b)=>sort==='skill'?a.skillupLow-b.skillupLow||a.name.localeCompare(b.name):sort==='level'?Math.max(0,...b.outputs.map(o=>item(o.id).itemLevel||0))-Math.max(0,...a.outputs.map(o=>item(o.id).itemLevel||0))||a.name.localeCompare(b.name):a.name.localeCompare(b.name)||a.id-b.id);
 const pages=Math.max(1,Math.ceil(rows.length/PAGE_SIZE));page=Math.min(page,pages-1);const start=page*PAGE_SIZE;
 $('catalog-title').textContent=(pid?profs.get(pid).name+' · ':'')+(k==='camp'?'Camping':k==='specialization'?'Specializations':'Recipe catalog');
 $('recipe-count').textContent=`${rows.length.toLocaleString('en-US')} matching entries${rows.length?` · Showing ${start+1}–${Math.min(start+PAGE_SIZE,rows.length)}`:''}`;
 $('recipe-results').innerHTML=rows.length?rows.slice(start,start+PAGE_SIZE).map(recipeHTML).join(''):'<p class="empty">No entries match these filters.</p>';
 $('page-count').textContent=`Page ${page+1} of ${pages}`;$('previous').disabled=page===0;$('next').disabled=page===pages-1;
 document.querySelectorAll('[data-profession]').forEach(b=>b.setAttribute('aria-pressed',String(Number(b.dataset.profession)===pid)));
}
function resetPage(){page=0;render()}
function selectProfession(id,update=true){$('profession').value=id;$('recipe-search').value='';page=0;if(update)history.replaceState(null,'',id?'#'+slug(profs.get(Number(id))):location.pathname);render()}
function route(){const h=location.hash.slice(1),p=DATA.professions.find(p=>slug(p)===h),m=h.match(/^recipe-(\d+)-(\d+)$/);if(m&&profs.has(Number(m[1]))){$('profession').value=m[1];$('kind').value='all';$('status').value='all';$('recipe-search').value='id:'+m[2];resetPage()}else if(p)selectProfession(String(p.id),false);else if(h==='camping'){ $('kind').value='camp';$('status').value='current';selectProfession('',false)}}
const summary=DATA.summary;
$('profession-stats').innerHTML=[[summary.professions,'Primary & secondary professions'],[summary.recipes,'Recipes outside SoD categories'],[summary.newRecipeIDs,'New recipe spell IDs'],[summary.campRecipeIDs,'Camping recipe variants']].map(([n,t])=>`<div class="stat"><strong>${n.toLocaleString('en-US')}</strong><span>${t}</span></div>`).join('');
$('profession-list').innerHTML=DATA.professions.map(p=>`<button type="button" class="profession-choice" data-profession="${p.id}" aria-pressed="false"><strong>${esc(p.name)}</strong><small>${p.type} · ${p.recipes} recipes</small><small>${p.new} new IDs · ${p.changed} changed</small></button>`).join('');
$('profession').insertAdjacentHTML('beforeend',DATA.professions.map(p=>`<option value="${p.id}">${esc(p.name)}</option>`).join(''));
$('camp-table').innerHTML=DATA.professions.map(p=>`<tr><td>${esc(p.name)}</td><td>${p.campIDs.map(id=>{const r=DATA.records.find(r=>r.professionID===p.id&&r.id===id);return `<a href="${recordURL(r)}">${esc(r.name)}${r.subtext?' ('+esc(r.subtext)+')':''}</a>`}).join('')}</td></tr>`).join('');
$('prototype-note').textContent='Additional entries: Jewelcrafting categories are explicitly marked PROTOTYPE under a Test Profession. They are excluded from the twelve-profession catalog.';
document.querySelectorAll('[data-profession]').forEach(b=>b.addEventListener('click',()=>selectProfession(b.dataset.profession)));
for(const id of ['kind','status','sort'])$(id).addEventListener('change',resetPage);
$('buff-level').addEventListener('input',render);
$('profession').addEventListener('change',()=>selectProfession($('profession').value));$('recipe-search').addEventListener('input',resetPage);
$('show-all').addEventListener('click',()=>{$('status').value='current';$('kind').value='recipes';selectProfession('')});
$('show-camping').addEventListener('click',()=>{$('status').value='current';$('kind').value='camp';selectProfession('');history.replaceState(null,'','#camping')});
$('show-specializations').addEventListener('click',()=>{$('status').value='current';$('kind').value='specialization';selectProfession('')});
$('show-new').addEventListener('click',()=>{$('status').value='new';$('kind').value='recipes';selectProfession('')});
$('previous').addEventListener('click',()=>{page--;render();$('catalog').scrollIntoView({block:'start'})});$('next').addEventListener('click',()=>{page++;render();$('catalog').scrollIntoView({block:'start'})});
window.addEventListener('hashchange',route);route();render();

$('related-talents').innerHTML=DATA.relatedTalents.map(t=>{const unique=[];for(const v of t.variants){if(!unique.some(u=>JSON.stringify(u.ranks)===JSON.stringify(v.ranks)))unique.push(v)}return `<article class="card"><h3>${esc(t.name)}</h3><p class="small muted">Spell ${t.spellID}${unique.length>1?' · '+unique.length+' rank layouts':''}</p>${unique.map(v=>`<details><summary>${v.maxRanks} ranks · Definition ${v.definitionID}</summary><ol>${v.ranks.map(r=>`<li>${esc(displayDescription(r))}</li>`).join('')}</ol></details>`).join('')}</article>`}).join('');
