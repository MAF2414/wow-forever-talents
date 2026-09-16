// Pure allocation rules, shared by the browser and the planner regression tests.
const TalentPlanner = {
  create(trees, budget = 51) {
    const nodes = new Map(trees.flatMap(tree => tree.talents.map(talent => [talent.id, {talent, tree}])));
    const rank = (ranks, id) => ranks[id] || 0;
    const spent = ranks => Object.values(ranks).reduce((sum, value) => sum + value, 0);
    const treeSpent = (ranks, tree) => tree.talents.reduce((sum, talent) => sum + rank(ranks, talent.id), 0);
    const maxRank = talent => talent.entries[0].maxRanks;
    function requirement(ranks, talent, tree) {
      const lowerPoints = tree.talents.filter(t => t.row < talent.row).reduce((sum, t) => sum + rank(ranks, t.id), 0);
      if (lowerPoints < talent.requiredPoints) return `${talent.entries[0].name} needs ${talent.requiredPoints} points in earlier rows of ${tree.name} (${lowerPoints} spent).`;
      const incoming = tree.edges.filter(edge => edge.to === talent.id && [2, 3].includes(edge.type));
      const satisfied = edge => rank(ranks, edge.from) >= edge.requiredRanks;
      const label = edge => `${nodes.get(edge.from).talent.entries[0].name} rank ${edge.requiredRanks}`;
      const required = incoming.find(edge => edge.type === 3 && !satisfied(edge));
      if (required) return `${talent.entries[0].name} requires ${label(required)}.`;
      if (incoming.length && !incoming.some(satisfied)) return `${talent.entries[0].name} requires ${incoming.map(label).join(' or ')}.`;
      return '';
    }
    function validate(ranks) {
      for (const [id, value] of Object.entries(ranks)) {
        const node = nodes.get(Number(id));
        if (!node || !Number.isInteger(value) || value < 0 || value > maxRank(node.talent)) return 'Invalid talent rank.';
      }
      if (spent(ranks) > budget) return `All ${budget} level-60 talent points are already spent.`;
      for (const {talent, tree} of nodes.values()) {
        if (rank(ranks, talent.id)) {
          const reason = requirement(ranks, talent, tree);
          if (reason) return reason;
        }
      }
      return '';
    }
    function change(ranks, id, delta) {
      const node = nodes.get(id);
      if (!node || ![1, -1].includes(delta)) return {ok: false, reason: 'This client entry is view-only.'};
      const value = rank(ranks, id) + delta;
      if (value < 0) return {ok: false, reason: 'No points to remove from this talent.'};
      if (value > maxRank(node.talent)) return {ok: false, reason: 'This talent is already at maximum rank.'};
      const next = {...ranks, [id]: value};
      if (!value) delete next[id];
      const reason = validate(next);
      return reason ? {ok: false, reason} : {ok: true, ranks: next};
    }
    function resetTree(ranks, id) {
      const next = {...ranks};
      const tree = trees.find(tree => tree.id === id);
      if (!tree) return {ok: false, reason: 'Unknown talent tree.'};
      tree.talents.forEach(talent => delete next[talent.id]);
      const reason = validate(next);
      return reason ? {ok: false, reason} : {ok: true, ranks: next};
    }
    return {nodes, budget, rank, spent, treeSpent, validate, change, resetTree};
  }
};
if (typeof module !== 'undefined' && module.exports) module.exports = TalentPlanner;
