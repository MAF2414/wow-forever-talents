const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const planner = require('../site/planner-engine.js');
const data = JSON.parse(fs.readFileSync(path.join(__dirname, '../dist/talents.json'), 'utf8'));

// Small independent examples isolate gates, prerequisite ranks and safe refunds.
const talent = (id, row, maxRanks, requiredPoints) => ({id, row, requiredPoints, entries:[{name:`Talent ${id}`, maxRanks}]});
const fixture = [{id:'a', name:'Tree A', talents:[talent(1,0,5,0),talent(2,0,5,0),talent(3,1,3,5),talent(4,2,1,10)], edges:[{from:3,to:4,type:3,requiredRanks:3}]},
  {id:'b',name:'Tree B',talents:[talent(5,0,5,0)],edges:[]}];
const engine = planner.create(fixture);
assert.equal(engine.change({},3,1).ok, false, 'locked tier');
assert.equal(engine.change({5:5},3,1).ok, false, 'other trees cannot unlock a tier');
assert.equal(engine.change({1:5},3,1).ok, true);
assert.equal(engine.change({1:5,3:1},1,-1).ok, false, 'refund must retain lower-tier investment');
assert.equal(engine.change({1:5,2:5,3:2},4,1).ok, false, 'prerequisite needs its full required rank');
assert.equal(engine.change({1:5,2:5,3:3},4,1).ok, true);
assert.equal(engine.change({1:5,2:5,3:3,4:1},3,-1).ok, false, 'cannot break a prerequisite');
assert.equal(engine.change({1:5},1,1).ok, false, 'max rank');
assert.equal(engine.change({},1,-1).ok, false, 'no negative rank');
assert.equal(engine.change({},999,1).ok, false, 'unknown/off-grid nodes are view-only');
assert.notEqual(engine.validate({1:'5'}), '', 'corrupt stored builds are rejected');
assert.notEqual(engine.validate({1:1.5}), '', 'fractional ranks are rejected');
assert.deepEqual(engine.resetTree({1:5,3:3,5:5},'a').ranks,{5:5});
const alternate = planner.create([{id:'or',name:'Alternatives',talents:[talent(1,0,1,0),talent(2,0,1,0),talent(3,0,1,0)],edges:[{from:1,to:3,type:2,requiredRanks:1},{from:2,to:3,type:2,requiredRanks:1}]}]);
assert.equal(alternate.change({},3,1).ok,false);
assert.equal(alternate.change({1:1},3,1).ok,true);
assert.equal(alternate.change({2:1},3,1).ok,true);
assert.equal(alternate.change({1:1,2:1,3:1},1,-1).ok,true);
assert.equal(alternate.change({2:1,3:1},2,-1).ok,false);

// Exercise all real class/version trees, several distinct allocation orders,
// the 51-point budget, and refundable builds all the way back to zero.
let builds = 0;
for (const cls of data.classes) for (const version of ['trees','classicTrees']) {
  const trees = cls[version], rules = planner.create(trees);
  assert(trees.every(t => t.talents.every(n => n.entries.length === 1)));
  for (let seed = 1; seed <= 3; seed++) {
    let ranks = {}, random = seed * 1000 + cls.id;
    for (let points = 0; points < 51; points++) {
      const options = [...rules.nodes.keys()].map(id => rules.change(ranks,id,1)).filter(r => r.ok);
      assert(options.length, `${cls.name}/${version}: unable to reach 51`);
      random = (random * 1664525 + 1013904223) >>> 0;
      ranks = options[random % options.length].ranks;
      assert.equal(rules.spent(ranks),points+1);
      assert.equal(rules.validate(ranks),'');
    }
    assert([...rules.nodes.keys()].every(id => !rules.change(ranks,id,1).ok), 'budget cannot be exceeded');
    assert.equal(trees.reduce((n,t) => n+rules.treeSpent(ranks,t),0),51);
    for (let points = 51; points; points--) {
      const options = Object.keys(ranks).map(id => rules.change(ranks,Number(id),-1)).filter(r => r.ok);
      assert(options.length, `${cls.name}/${version}: no valid refund`);
      ranks = options[0].ranks;
      assert.equal(rules.spent(ranks),points-1);
    }
    assert.deepEqual(ranks,{});
    builds++;
  }
}
console.log(`Planner checks passed: gates, prerequisite ranks, alternatives, refunds, resets, saved-rank validation; ${builds} complete 51-point builds across all 18 class/version combinations.`);
