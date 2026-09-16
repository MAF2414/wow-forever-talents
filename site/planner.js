// Level-60 builds are independent for each class and client version.
const plannerStorageKey = `wow-forever-planner:v1:${DATA.build}:${DATA.classicBuild}`;
let plannerEnabled = false, plannerSaved = {}, plannerMessage = '';
try {
  const stored = JSON.parse(localStorage.getItem(plannerStorageKey) || '{}');
  plannerEnabled = stored.enabled === true;
  if (stored.builds && typeof stored.builds === 'object' && !Array.isArray(stored.builds)) plannerSaved = stored.builds;
} catch (_) { /* The planner also works when browser storage is unavailable. */ }
const plannerContexts = new Map();
function plannerContext() {
  const key = `${treeVersion}:${currentClass.id}`;
  if (!plannerContexts.has(key)) {
    const engine = TalentPlanner.create(versionTrees());
    const saved = plannerSaved[key];
    const ranks = saved && typeof saved === 'object' && !Array.isArray(saved) && !engine.validate(saved) ? {...saved} : {};
    plannerContexts.set(key, {engine, ranks});
  }
  return plannerContexts.get(key);
}
function savePlanner() {
  for (const [key, context] of plannerContexts) plannerSaved[key] = context.ranks;
  try { localStorage.setItem(plannerStorageKey, JSON.stringify({enabled: plannerEnabled, builds: plannerSaved})); }
  catch (_) { plannerMessage = 'Build kept for this session. Browser storage is unavailable.'; }
}
document.querySelector('.view-toolbar').insertAdjacentHTML('beforeend', `<button id="planner-toggle" class="planner-toggle" type="button" role="switch" aria-checked="false"><span class="switch-track" aria-hidden="true"></span>Level 60 planner</button>`);
$('trees').insertAdjacentHTML('beforebegin', `<section id="planner-panel" class="planner-panel" aria-label="Level 60 talent planner" hidden><div class="planner-top"><div><strong id="planner-remaining"></strong><div id="planner-spent" class="sub"></div></div><div class="planner-actions"><button id="planner-inspect" type="button">Talent details</button><button id="planner-reset" type="button">Reset build</button></div></div><meter id="planner-meter" min="0" max="51" value="0" aria-label="Talent points spent"></meter><div id="planner-split" class="planner-split"></div><p class="planner-help">Click: +1 · Right-click or Shift-click: −1 · Use + / − in Talent details on touch screens.</p><p id="planner-scope" class="planner-help"></p><div id="planner-status" class="planner-status" role="status" aria-live="polite"></div></section>`);
function refreshPlanner() {
  const visible = viewMode === 'trees';
  $('planner-toggle').hidden = !visible;
  $('planner-toggle').setAttribute('aria-checked', String(plannerEnabled));
  $('planner-panel').hidden = !visible || !plannerEnabled;
  $('trees').classList.toggle('planning', plannerEnabled);
  const {engine, ranks} = plannerContext();
  const used = engine.spent(ranks);
  $('planner-remaining').textContent = `${engine.budget - used} points left`;
  $('planner-spent').textContent = `${used} / ${engine.budget} spent · Level 60 · ${treeVersion === 'classic' ? 'Classic Era' : 'Forever'}`;
  $('planner-meter').value = used;
  $('planner-reset').disabled = used === 0;
  $('planner-split').innerHTML = versionTrees().map(tree => `<span>${esc(tree.name)} <b>${engine.treeSpent(ranks, tree)}</b></span>`).join('');
  $('planner-scope').textContent = treeVersion === 'forever' ? 'Client-based planner. Flagged beta conditions remain provisional; additional off-grid nodes are view-only.' : 'Each tier needs points in earlier rows of the same tree. Builds are saved separately per class and version.';
  $('planner-status').textContent = plannerMessage;
  document.querySelectorAll('.tree .talent').forEach(button => {
    const id = Number(button.dataset.id), node = engine.nodes.get(id);
    if (!node) return;
    const entry = node.talent.entries[0], value = engine.rank(ranks, id);
    const next = engine.change(ranks, id, 1);
    button.querySelector('.rank-count').textContent = plannerEnabled ? `${value}/${entry.maxRanks}` : entry.maxRanks;
    button.classList.toggle('planner-locked', plannerEnabled && !value && !next.ok);
    button.classList.toggle('planner-invested', plannerEnabled && value > 0);
    button.classList.toggle('planner-maxed', plannerEnabled && value === entry.maxRanks);
    button.setAttribute('aria-label', plannerEnabled ? `${entry.name}, ${value} of ${entry.maxRanks} points` : `${entry.name}, ${entry.maxRanks} ${entry.maxRanks === 1 ? 'rank' : 'ranks'}`);
    if (!button.dataset.readTitle) button.dataset.readTitle = button.title;
    button.title = plannerEnabled ? `${entry.name} · ${value}/${entry.maxRanks}\n${next.ok ? 'Click to add a point.' : next.reason}\nRight-click or Shift-click to remove a point.` : button.dataset.readTitle;
  });
  document.querySelectorAll('.tree').forEach((element, index) => {
    const tree = versionTrees()[index];
    const foot = element.querySelector('.tree-foot');
    foot.innerHTML = plannerEnabled ? `<span>${engine.treeSpent(ranks, tree)} points in ${esc(tree.name)}</span><button type="button" class="planner-tree-reset" ${engine.treeSpent(ranks, tree) ? '' : 'disabled'}>Reset tree</button>` : 'Select a talent to read all ranks.';
    const reset = foot.querySelector('button');
    if (reset) {
      reset.setAttribute('aria-label', `Reset ${tree.name} tree`);
      reset.onclick = () => applyPlannerResult(engine.resetTree(ranks, tree.id), `${tree.name} reset.`);
    }
  });
}
function applyPlannerResult(result, message) {
  if (result.ok) {
    plannerContext().ranks = result.ranks;
    plannerMessage = message;
    savePlanner();
  } else plannerMessage = result.reason;
  const context = plannerContext();
  if (context.engine.nodes.has(selectedTalent?.id)) selectedRank = Math.max(1, context.engine.rank(context.ranks, selectedTalent.id));
  refreshPlanner();
  renderDetail();
}
function spendPlannerPoint(id, delta) {
  const {engine, ranks} = plannerContext();
  applyPlannerResult(engine.change(ranks, id, delta), delta > 0 ? 'Point added.' : 'Point removed.');
}
const plannerRenderTrees = renderTrees;
renderTrees = function() { plannerRenderTrees(); refreshPlanner(); };
const plannerRenderMode = renderMode;
renderMode = function() { plannerRenderMode(); plannerMessage = ''; refreshPlanner(); };
const plannerRenderDetail = renderDetail;
renderDetail = function() {
  plannerRenderDetail();
  if (!plannerEnabled || viewMode !== 'trees') return;
  const {engine, ranks} = plannerContext(), id = selectedTalent.id;
  if (!engine.nodes.has(id)) return;
  const entry = selectedTalent.entries[0], value = engine.rank(ranks, id);
  const add = engine.change(ranks, id, 1), remove = engine.change(ranks, id, -1);
  $('detail-content').querySelector('.detail-heading').insertAdjacentHTML('afterend', `<div class="planner-detail"><div class="planner-detail-controls"><button id="planner-minus" type="button" aria-label="Remove point from ${esc(entry.name)}" ${remove.ok ? '' : 'disabled'}>−</button><strong>${value} / ${entry.maxRanks}<small>points allocated</small></strong><button id="planner-plus" type="button" aria-label="Add point to ${esc(entry.name)}" ${add.ok ? '' : 'disabled'}>+</button></div>${!add.ok && value < entry.maxRanks ? `<p>${esc(add.reason)}</p>` : ''}${value && !remove.ok ? `<p>Cannot remove: ${esc(remove.reason)}</p>` : ''}</div>`);
  for (const [buttonID, delta] of [['planner-plus', 1], ['planner-minus', -1]]) {
    $(buttonID).onclick = () => { spendPlannerPoint(id, delta); const button = $(buttonID); if (!button.disabled) button.focus(); };
  }
};
const plannerSelectTalent = selectTalent;
selectTalent = function(id, open = true) {
  plannerSelectTalent(id, open);
  if (plannerEnabled) {
    const {engine, ranks} = plannerContext();
    if (engine.nodes.has(selectedTalent.id)) {
      selectedRank = Math.max(1, engine.rank(ranks, selectedTalent.id));
      renderDetail();
    }
  }
};
// Capture allocation clicks before the original inspection listener.
$('trees').addEventListener('click', event => {
  const button = event.target.closest('.tree .talent');
  if (!plannerEnabled || !button) return;
  event.preventDefault(); event.stopImmediatePropagation();
  const id = Number(button.dataset.id);
  selectTalent(id, false);
  spendPlannerPoint(id, event.shiftKey ? -1 : 1);
}, true);
$('trees').addEventListener('contextmenu', event => {
  const button = event.target.closest('.tree .talent');
  if (!plannerEnabled || !button) return;
  event.preventDefault();
  const id = Number(button.dataset.id);
  selectTalent(id, false);
  spendPlannerPoint(id, -1);
});
$('trees').addEventListener('keydown', event => {
  const button = event.target.closest('.tree .talent');
  if (!plannerEnabled || !button || !['Backspace', 'Delete'].includes(event.key)) return;
  event.preventDefault();
  const id = Number(button.dataset.id);
  selectTalent(id, false);
  spendPlannerPoint(id, -1);
});
$('planner-toggle').onclick = () => {
  plannerEnabled = !plannerEnabled;
  plannerMessage = '';
  if (plannerEnabled) selectedRank = Math.max(1, plannerContext().engine.rank(plannerContext().ranks, selectedTalent.id));
  savePlanner(); refreshPlanner(); renderDetail();
};
$('planner-reset').onclick = () => applyPlannerResult({ok: true, ranks: {}}, 'Build reset.');
$('planner-inspect').onclick = () => {
  lastFocus = $('planner-inspect');
  $('details').classList.add('open');
  const close = $('details').querySelector('.mobile-close');
  if (close.getClientRects().length) close.focus();
  else $('details').querySelector('#planner-plus:not(:disabled),.rank-btn')?.focus();
};
$('source-copy').insertAdjacentHTML('beforeend', '<p><strong>Level 60 planner:</strong> 51 points across the three regular trees. Tier gates and prerequisite ranks are checked; refunds cannot invalidate invested talents. The planner uses known client rules. Flagged beta conditions remain provisional. Off-grid entries are view-only. Builds are stored in this browser, separately for every class and version.</p>');
if (plannerEnabled) selectedRank = Math.max(1, plannerContext().engine.rank(plannerContext().ranks, selectedTalent.id));
refreshPlanner(); renderDetail();
