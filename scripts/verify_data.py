"""Integrity checks for the exported client data, joins and comparison scope."""
import collections,csv,json,re
from pathlib import Path

ROOT=Path(__file__).resolve().parent.parent
BASE=ROOT/'evidence'/'2026-09-16'
d=json.loads((ROOT/'dist'/'talents.json').read_text(encoding='utf-8'))
def rows(folder,name):
    with (BASE/folder/(name+'.csv')).open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))

assert len(d['classes'])==9
all_forever=[];all_classic=[];all_entries=[]
seed={int(r['Spell']) for r in rows('era-baseline','SkillLineAbility')}
known_era={int(r['ID']) for r in rows('classic-db2','SpellName')}
for c in d['classes']:
    for version in ('trees','classicTrees'):
        assert len(c[version])==3
        for tree in c[version]:
            seen=set();ids={t['id'] for t in tree['talents']}
            for t in tree['talents']:
                pos=(round(t['x']),t['row'])
                assert pos not in seen,(c['name'],tree['name'],'overlap',pos)
                seen.add(pos)
                assert 0<t['x']<100 and 0<=t['row']<=6
                assert t['requiredPoints']==5*t['row']
                for e in t['entries']:
                    assert e['name'] and len(e['ranks'])==e['maxRanks']
                    assert all(r['description'] for r in e['ranks'])
                    assert str(e['iconID']) in d['icons'],e['name']
                    all_entries.append(e)
            assert all(e['from'] in ids and e['to'] in ids for e in tree['edges'])
    forever=[t for tree in c['trees'] for t in tree['talents']]
    classic=[t for tree in c['classicTrees'] for t in tree['talents']]
    assert collections.Counter(x['forever']['id'] for x in c['talentChanges'] if x['forever'])==collections.Counter(t['id'] for t in forever)
    assert collections.Counter(x['classic']['id'] for x in c['talentChanges'] if x['classic'])==collections.Counter(t['id'] for t in classic)
    all_forever.extend(forever+c['extraTalents']);all_classic.extend(classic)
    for s in c['spells']:
        assert s['pairs']
        for p in s['pairs']:
            if p['classic']:assert p['spellID'] in seed
            if s['extra']:assert p['spellID'] in known_era and p['spellID'] not in seed
            if p['forever'] and p['forever'].get('candidate'):assert p['spellID'] not in known_era

treeids={tree['sourceTreeID'] for c in d['classes'] for tree in c['trees']}
expected={int(r['ID']) for r in rows('db2','TraitNode') if int(r['TraitTreeID']) in treeids}
assert {t['id'] for t in all_forever}==expected
assert len(all_forever)==471 and len(all_classic)==432
assert sum(len(c['extraTalents']) for c in d['classes'])==3
mage=next(c for c in d['classes'] if c['id']==8)
focus=next(t for t in mage['talentChanges'] if t['name']=='Arcane Focus')
assert '10%' in focus['classic']['entries'][0]['ranks'][-1]['description']
assert '5%' in focus['forever']['entries'][0]['ranks'][-1]['description']
fireball=next(s for s in mage['spells'] if s['name']=='Fireball' and not s['extra'])
rank1=next(p for p in fireball['pairs'] if p['spellID']==133)
assert rank1['classic']['effects'][0]['EffectBasePointsF']==rank1['forever']['effects'][0]['EffectBasePointsF']==18
warrior=next(c for c in d['classes'] if c['id']==1)
heroic=next(s for s in warrior['spells'] if s['name']=='Heroic Strike' and not s['extra'])
for side in ('classic','forever'):assert heroic['pairs'][0][side]['metrics']['Cost']=='15 Rage'
warlock=next(c for c in d['classes'] if c['id']==9)
agony=next(s for s in warlock['spells'] if s['name']=='Bane of Agony' and not s['extra'])
assert agony['status']=='changed' and agony['previousNames']==['Curse of Agony']
assert all(p['classic'] and p['forever'] for p in agony['pairs'])
# Regression cases discovered by the direct client-file audit.
stance=next(s for s in warrior['spells'] if s['name']=='Battle Stance' and not s['extra'])
for side in ('classic','forever'):assert stance['pairs'][0][side]['metrics']['Duration (sec)']=='Unlimited'
combustion=next(t for t in mage['talentChanges'] if t['name']=='Combustion')
assert combustion['classic']['prerequisites']==['Critical Mass (rank 3)']
hunter=next(c for c in d['classes'] if c['id']==3)
intimidation=next(t for t in hunter['talentChanges'] if t['name']=='Intimidation')
assert intimidation['forever']['prerequisiteMode']=='any'
assert intimidation['forever']['prerequisites']==['Bestial Swiftness (rank 1)','Bestial Wrath (rank 1)']
rogue=next(c for c in d['classes'] if c['id']==4)
venom=next(t for t in rogue['talentChanges'] if t['name']=='Venom')['forever']
assert venom['requiredPoints']==30 and venom['additionalConditions'][0]['ID']=='50984'
import build_talents as source
assert source.resolve_description('$m2 to $M2',116,0,1,overrides={})=='18 to 20'
curve_gaps=[]
for e in all_entries:
    if e.get('definitionID') and source.POINTS[e['definitionID']]:
        for rank in range(1,e['maxRanks']+1):
            for point in source.POINTS[e['definitionID']]:
                assert point['OperationType']=='0'
                if not any(float(p['Pos_0'])==rank for p in source.CURVES[int(point['CurveID'])]):
                    curve_gaps.append((e['name'],int(point['EffectIndex']),rank))
                    assert e.get('curveNotice')
assert sorted(curve_gaps)==[('Cutthroat',1,4),('Cutthroat',1,5)]
html=(ROOT/'dist'/'index.html').read_text(encoding='utf-8')
assert '/*TALENT_DATA*/null' not in html
assert not re.search(r'<script\b[^>]*\bsrc=',html)
script=re.search(r'<script>(.*)</script>',html,re.S).group(1)
(BASE/'browser-script.js').write_text(script,encoding='utf-8')
report={'foreverNodes':len(all_forever),'classicNodes':len(all_classic),'spellGroups':sum(len(c['spells']) for c in d['classes']),'regularActiveSpellGroups':sum(not s['passive'] and not s['talent'] and not s['extra'] for c in d['classes'] for s in c['spells']),'icons':len(d['icons']),'htmlBytes':len(html.encode('utf-8')),'checks':'passed'}
(BASE/'integrity-checks.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report))
