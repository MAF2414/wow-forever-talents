function renderPvP(){
 const p=CONTENT.pvp;
 $('pvp-honor-cap').textContent=p.honor.MaxQty.toLocaleString('en-US');
 $('pvp-ranks').innerHTML=p.ranks.map(r=>`<tr><td>${r.rank}</td><td>${esc(r.alliance)}</td><td>${esc(r.horde)}</td><td>${r.rewards.map(esc).join(' · ')}</td></tr>`).join('');
 $('pvp-cap-sequence').textContent=p.rankCapCurve.filter((r,i,a)=>r.maxRank>0&&r.maxRank!==a[i-1]?.maxRank).map(r=>'Rank '+r.maxRank).join(' → ');
 const dark=p.battlegrounds.find(b=>b.id===1157);
 const bracketText=dark.brackets.map(b=>b.min===b.max?b.min:`${b.min}–${b.max}`).join(' · ');
 $('pvp-darkspear').innerHTML=`<article class="card"><div class="tags"><span class="tag new">New battleground</span><span class="tag">Map 2997</span></div><h3>15 vs. 15 · Level 30–60</h3><p>Capture and hold bases. Carry the Darkspear Flag to any point your team controls to gain Victory Points.</p><p class="role">Objective: 1,500 resources</p><p class="small muted">Brackets: ${esc(bracketText)}</p><p class="small muted">Scoreboard: ${p.darkspearScoreboard.map(r=>esc(r.name)).join(' · ')}</p></article><article class="card"><h3>Two reputation factions</h3>${p.darkspearFactions.map(f=>`<p><strong>${esc(f.name)}</strong><br><span class="muted">${f.id===2798?'Horde':'Alliance'} · 22 item variants</span></p>`).join('')}<p><a href="${esc(p.sourceFiles.announcement)}" target="_blank" rel="noreferrer">Blizzard’s battleground announcement ↗</a></p></article>`;
 const mainIds=new Set([1,2,3,1157]);
 $('pvp-queues').innerHTML=p.battlegrounds.filter(b=>mainIds.has(b.id)).map(b=>`<tr><td>${esc(b.name)}</td><td>${b.MaxPlayers}</td><td>${b.MinLevel}–${b.MaxLevel}</td><td>${b.MaxGroupSize}</td><td>${b.status==='classic'?(b.differences.length?b.differences.map(d=>`${esc(({MinPlayers:'Minimum players',MaxPlayers:'Maximum players',MinLevel:'Minimum level',MaxLevel:'Maximum level',MaxGroupSize:'Maximum party',GroupsAllowed:'Group flag'})[d.field]||d.field)}: ${d.old} → ${d.new}`).join('<br>'):'Classic queue settings'):'New'}</td></tr>`).join('');
 const random=p.battlegrounds.find(b=>b.id===32);
 $('pvp-random-pool').innerHTML=`<strong>Random Battleground:</strong> ${random.maps.map(m=>esc(m.name)).join(' · ')}.`;
 const notes={
  901:'Separate random epic queue entry; no map links are listed.',
  1122:'Already present in the SoD reference. This is an inherited entry.',
  1159:'10-player team field, maximum party size 5. Level fields are unset; no map link is listed.',
  1168:'Arena entry linked to Hyjal Crater, map 2995. Stored maximum: 5 players per side.',
  1169:'Arena entry linked to the same Hyjal Crater map, 2995. Listed levels: 1–60; stored maximum: 5 players per side.'
 };
 $('pvp-additional').innerHTML=p.battlegrounds.filter(b=>notes[b.id]).map(b=>`<article class="card"><div class="tags"><span class="tag">${b.status==='inherited'?'SoD entry':'Additional client entry'}</span><span class="tag">Queue ${b.id}</span></div><h3>${esc(b.name)}</h3><p class="small">${esc(notes[b.id])}</p></article>`).join('');
 $('pvp-set-class').insertAdjacentHTML('beforeend',[...new Set(p.sets.map(s=>s.class))].sort().map(c=>`<option>${esc(c)}</option>`).join(''));
 for(const id of ['pvp-item-faction','pvp-item-rep'])$(id).addEventListener('change',renderPvpItems);
 $('pvp-item-search').addEventListener('input',renderPvpItems);
 for(const id of ['pvp-set-class','pvp-set-faction','pvp-set-status'])$(id).addEventListener('change',renderPvpSets);
 renderPvpItems();renderPvpSets();
}

function renderPvpItems(){
 const faction=$('pvp-item-faction').value,rep=$('pvp-item-rep').value,q=$('pvp-item-search').value.trim().toLowerCase();
 const items=CONTENT.pvp.reputationItems.filter(i=>(!faction||i.side===faction)&&(!rep||i.reputation===rep)&&(!q||`${i.name} ${i.id}`.toLowerCase().includes(q))).sort((a,b)=>a.side.localeCompare(b.side)||a.reputationRank-b.reputationRank||a.name.localeCompare(b.name)||a.requiredLevel-b.requiredLevel);
 $('pvp-item-count').textContent=`${items.length} item variants`;
 $('pvp-items').innerHTML=items.map(i=>`<article class="card"><div class="tags"><span class="tag">${esc(i.side)} · ${esc(i.reputation)}</span><span class="tag">${i.quality===4?'Epic':i.quality===3?'Rare':'Common'} · ${esc(i.slot)}</span></div><h3>${esc(i.name)}</h3><p class="role">${i.requiredLevel?'Level '+i.requiredLevel:'No level requirement'} · Item level ${i.itemLevel}</p><p class="small muted">${esc(i.faction)} · Item ${i.id}</p>${i.effects.filter(e=>e.description).map(e=>`<p class="small">${esc(e.description)}</p>`).join('')}${i.missingEffectIDs.length?'<p class="small muted">Effect details unavailable.</p>':''}</article>`).join('')||'<p class="empty">No rewards match these filters.</p>';
}

function renderPvpSets(){
 const cls=$('pvp-set-class').value,faction=$('pvp-set-faction').value,status=$('pvp-set-status').value;
 const sets=CONTENT.pvp.sets.filter(s=>(!cls||s.class===cls)&&(!faction||s.faction===faction)&&(!status||s.status===status)).sort((a,b)=>a.class.localeCompare(b.class)||a.faction.localeCompare(b.faction)||a.name.localeCompare(b.name));
 $('pvp-set-count').textContent=`${sets.length} PvP sets`;
 $('pvp-sets').innerHTML=sets.map(m=>{
  const s=CONTENT.sets.find(s=>s.id===m.id);
  return `<article class="card"><div class="tags"><span class="tag ${m.status==='new'?'new':''}">${m.status==='new'?'New set ID':'Updated Classic set'}</span><span class="tag">${esc(m.class)} · ${esc(m.faction)}</span><span class="tag">${m.quality.includes(4)?'Epic':'Rare'}</span></div><h3>${esc(s.name)}</h3><p class="small muted">Set ${s.id} · Item levels ${m.itemLevels.join(', ')}</p><ul class="bonuses">${s.bonuses.map(bonusHTML).join('')}</ul><details><summary>Set pieces</summary><ul>${s.items.map(i=>`<li>${esc(i.name||'Item '+i.id)}${i.available?` · item level ${i.ItemLevel}`:''}</li>`).join('')}</ul></details>${s.classic?referenceHTML(s.classic,'Classic'):''}<p class="small"><a href="#set-${s.id}">Open in set archive →</a></p></article>`;
 }).join('')||'<p class="empty">No sets match these filters.</p>';
}
