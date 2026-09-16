"""Extend the offline viewer with an audited Era/Forever comparison.

Era spell membership is checked against a pre-SoD client. Extra inherited
seasonal records are retained separately, never presented as confirmed new spells.
"""
from __future__ import annotations
import base64, collections, csv, json, re
from pathlib import Path
import build_talents as b

BASE=b.EVIDENCE
ERA_BUILD='1.14.4.51395'
REFERENCE_BUILD=ERA_BUILD
CLASSIC_FOLDER='era-baseline'
SKILLS={1:[26,256,257],2:[594,267,184],3:[50,163,51,261],4:[253,38,39,40,633],5:[613,56,78],7:[375,373,374],8:[237,8,6],9:[355,354,593],11:[574,134,573]}

def read(folder,name):
    if name=='SpellDescriptionVariables' and not (BASE/folder/(name+'.csv')).exists():return []
    with (BASE/folder/(name+'.csv')).open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))

def normalize(text):return re.sub(r'\s+',' ',str(text)).strip().casefold()
def num(value):
    n=round(float(value),5)
    return int(n) if n==int(n) else n
def icon(id):
    p=BASE/'icons'/f'{id}.jpg'
    return 'data:image/jpeg;base64,'+base64.b64encode(p.read_bytes()).decode() if p.exists() else ''

class Context:
    def __init__(self,folder,classic=False):
        self.classic=classic;self.folder=folder
        self.tables={n:read(folder,n) for n in ['Spell','SpellName','SpellEffect','SpellMisc','SpellDuration','SpellRange','SpellRadius','SpellAuraOptions','SpellDescriptionVariables','SpellXDescriptionVariables','SpellLevels','SpellCooldowns','SpellPower','SpellCastTimes','SkillLineAbility','SkillLine']}
        self.names={int(r['ID']):r['Name_lang'] for r in self.tables['SpellName']}
        self.spells={int(r['ID']):r for r in self.tables['Spell']}
        self.skills={int(r['ID']):r for r in self.tables['SkillLine']}
        self.effects=collections.defaultdict(list)
        for raw in self.tables['SpellEffect']:
            if raw['DifficultyID']!='0':continue
            r=dict(raw)
            if classic:
                die=float(r.get('EffectDieSides',0));base=float(r.get('EffectBasePoints',0))
                # Normalize integer base + die roll to the modern mean/variance format.
                mean=base+((die+1)/2 if die>0 else die)
                r['EffectBasePointsF']=str(mean)
                r['Variance']=str((die-1)/abs(mean) if die>1 and mean else 0)
            self.effects[int(r['SpellID'])].append(r)
        self.by_spell={}
        for table in ['SpellMisc','SpellAuraOptions','SpellLevels','SpellCooldowns']:
            self.by_spell[table]={int(r['SpellID']):r for r in self.tables[table] if r.get('DifficultyID','0')=='0'}
        self.powers=collections.defaultdict(list)
        for r in self.tables['SpellPower']:self.powers[int(r['SpellID'])].append(r)
        self.power_divisors={int(r['PowerTypeEnum']):float(r['DisplayModifier']) or 1 for r in read(folder,'PowerType')}
        self.indices={n:{int(r['ID']):r for r in self.tables[n]} for n in ['SpellDuration','SpellRange','SpellRadius','SpellCastTimes','SpellDescriptionVariables']}
        if not classic:
            # Names verified against wowdev/WoWDBDefs, layout 224F7EA0.
            m={'002':'ID','003':'SkillLine','004':'Spell','005':'MinSkillLineRank','006':'ClassMask','007':'SupercedesSpell'}
            self.abilities=[{m.get(k.removeprefix('Field_1_60_1_69876_'),k):v for k,v in r.items()} for r in self.tables['SkillLineAbility']]
        else:self.abilities=self.tables['SkillLineAbility']
        self.cache={}

    def activate(self):
        b.SPELLS=self.spells;b.NAMES={int(r['ID']):r for r in self.tables['SpellName']}
        b.EFFECTS={(sid,int(e['EffectIndex'])):e for sid,es in self.effects.items() for e in es}
        b.MISC=self.by_spell['SpellMisc'];b.AURAS=self.by_spell['SpellAuraOptions']
        b.DURATION=self.indices['SpellDuration'];b.RADIUS=self.indices['SpellRadius'];b.RANGE=self.indices['SpellRange']
        variables=self.indices['SpellDescriptionVariables']
        b.SPELL_VARIABLES={int(r['SpellID']):variables.get(int(r['SpellDescriptionVariablesID']),{}).get('Variables','') for r in self.tables['SpellXDescriptionVariables']}

    def record(self,sid):
        if sid in self.cache:return self.cache[sid]
        raw=self.spells.get(sid,{});misc=self.by_spell['SpellMisc'].get(sid,{})
        desc=b.resolve_description(raw.get('Description_lang',''),sid,0,1,overrides={})
        level=self.by_spell['SpellLevels'].get(sid,{})
        cd=self.by_spell['SpellCooldowns'].get(sid,{})
        dur=self.indices['SpellDuration'].get(int(misc.get('DurationIndex',0)),{})
        cast=self.indices['SpellCastTimes'].get(int(misc.get('CastingTimeIndex',0)),{})
        ran=self.indices['SpellRange'].get(int(misc.get('RangeIndex',0)),{})
        power_names={0:'Mana',1:'Rage',2:'Focus',3:'Energy',4:'Combo points',6:'Runic power',-2:'Health'}
        costs=[]
        for p in sorted(self.powers[sid],key=lambda p:int(p.get('OrderIndex',0))):
            parts=[]
            for field,label in [('ManaCost',''),('PowerCostPct','% base'),('ManaCostPerLevel',' per level'),('ManaPerSecond',' / sec'),('PowerPctPerSecond','% / sec')]:
                v=float(p.get(field,0))
                if field in ('ManaCost','ManaCostPerLevel','ManaPerSecond'):v/=self.power_divisors.get(int(p['PowerType']),1)
                if v:parts.append(f'{num(v)}{label}')
            if parts:costs.append(' + '.join(parts)+' '+power_names.get(int(p['PowerType']),f'Resource {p["PowerType"]}'))
        duration=float(dur.get('Duration',0))
        metrics={'Level':int(level.get('SpellLevel',0)),'Cost':'; '.join(costs) or '—','Cast time (sec)':num(float(cast.get('Base',0))/1000),'Cooldown (sec)':num(max(float(cd.get('RecoveryTime',0)),float(cd.get('CategoryRecoveryTime',0)))/1000),'Duration (sec)':'Unlimited' if duration<0 else num(duration/1000),'Range':f'{num(ran.get("RangeMin_0",0))}–{num(ran.get("RangeMax_0",0))} yd'}
        efkeys=['Effect','EffectAura','EffectAuraPeriod','EffectBasePointsF','Variance','EffectBonusCoefficient','EffectRealPointsPerLevel','Coefficient','BonusCoefficientFromAP','ResourceCoefficient','EffectTriggerSpell','EffectChainTargets','EffectMiscValue_0','EffectMiscValue_1']
        effects=[{'index':int(e['EffectIndex']),**{k:num(e.get(k,0)) for k in efkeys}} for e in sorted(self.effects[sid],key=lambda e:int(e['EffectIndex']))]
        iid=int(misc.get('SpellIconFileDataID',0))
        r={'spellID':sid,'name':self.names.get(sid,f'Spell {sid}'),'subtext':raw.get('NameSubtext_lang',''),'description':desc,'rawDescription':raw.get('Description_lang',''),'unresolved':'$' in desc,'iconID':iid,'metrics':metrics,'effects':effects,'passive':bool(int(misc.get('Attributes_0',0))&64)}
        self.cache[sid]=r
        return r

def classic_trees(ctx,cid,names):
    tabs=[r for r in read(CLASSIC_FOLDER,'TalentTab') if int(r['ClassMask'])==(1<<(cid-1))]
    rows=read(CLASSIC_FOLDER,'Talent');trees=[]
    for tab in sorted(tabs,key=lambda r:int(r['OrderIndex'])):
        tid=int(tab['ID']);talents=[];edges=[]
        for r in rows:
            if int(r['TabID'])!=tid:continue
            ids=[int(r[f'SpellRank_{i}']) for i in range(9) if int(r[f'SpellRank_{i}'])]
            if not ids:continue
            first=ctx.record(ids[0]);ranks=[]
            for rank,sid in enumerate(ids,1):
                rr=ctx.record(sid)
                ranks.append({'rank':rank,'spellID':sid,'description':rr['description'],'unresolved':rr['unresolved']})
            base_notice=any(effect['Effect'] in (2,10,17,31,58,121) or (effect['Effect']==6 and effect['EffectAura'] in (3,8,69)) for effect in first['effects'])
            e={'id':int(r['ID']),'spellID':ids[0],'spellIDs':ids,'name':first['name'],'description':first['rawDescription'],'maxRanks':len(ids),'iconID':first['iconID'],'ranks':ranks,'baseValueNotice':base_notice}
            talents.append({'id':-int(r['ID']),'row':int(r['TierID']),'x':12.5+25*int(r['ColumnIndex']),'requiredPoints':5*int(r['TierID']),'entries':[e],'classic':True})
            for i in range(3):
                if int(r[f'PrereqTalent_{i}']):edges.append({'from':-int(r[f'PrereqTalent_{i}']),'to':-int(r['ID']),'type':3,'requiredRanks':int(r[f'PrereqRank_{i}'])+1})
        trees.append({'id':f'classic-{tid}','name':names[int(tab['OrderIndex'])],'talents':sorted(talents,key=lambda t:(t['row'],t['x'])),'edges':edges,'rows':7,'classic':True})
    return trees

def flat(trees):
    result=[]
    for i,tree in enumerate(trees):
        lookup={t['id']:t for t in tree['talents']}
        for t in tree['talents']:
            incoming=[e for e in tree['edges'] if e['to']==t['id'] and e['from'] in lookup]
            prerequisites=sorted(f"{lookup[e['from']]['entries'][0]['name']} (rank {e['requiredRanks']})" for e in incoming)
            mode='any' if len(incoming)>1 and all(e['type']==2 for e in incoming) else 'all'
            result.append({**t,'tree':tree['name'],'treeIndex':i,'prerequisites':prerequisites,'prerequisiteMode':mode})
    return result

def talent_comparison(old,new):
    used=set();out=[]
    for n in new:
        ne=n['entries'][0]
        candidates=[o for o in old if o['id'] not in used and ne['spellID'] in o['entries'][0]['spellIDs']]
        matched='Spell-ID'
        if not candidates:
            candidates=[o for o in old if o['id'] not in used and normalize(ne['name'])==normalize(o['entries'][0]['name'])];matched='Name'
        o=next(iter(candidates),None);diff=[]
        if o:
            used.add(o['id']);oe=o['entries'][0]
            if ne['maxRanks']!=oe['maxRanks']:diff.append(f'Ranks: {oe["maxRanks"]} → {ne["maxRanks"]}')
            if n['treeIndex']!=o['treeIndex']:diff.append(f'Tree: {o["tree"]} → {n["tree"]}')
            if (n['row'],round(n['x']))!=(o['row'],round(o['x'])):diff.append(f'Position: row {o["row"]+1} → {n["row"]+1}, column {round((o["x"]-12.5)/25)+1} → {round((n["x"]-12.5)/25)+1}')
            if n['prerequisites']!=o['prerequisites']:diff.append('Requirements: '+(', '.join(o['prerequisites']) or 'no connection')+' → '+(', '.join(n['prerequisites']) or 'no connection'))
            if n['prerequisiteMode']!=o['prerequisiteMode']:diff.append('Requirement logic: '+o['prerequisiteMode']+' → '+n['prerequisiteMode'])
            if n.get('additionalConditions'):diff.append('Additional client condition (evaluation unverified)')
            if [normalize(r['description']) for r in ne['ranks']] != [normalize(r['description']) for r in oe['ranks']]:diff.append('Description / rank values')
            if normalize(ne['name'])!=normalize(oe['name']):diff.append('Name')
        status='changed' if diff else 'unchanged'
        if not o:status='added'
        out.append({'name':ne['name'],'status':status,'classic':o,'forever':n,'differences':diff,'matchedBy':matched if o else None})
    for o in old:
        if o['id'] not in used:out.append({'name':o['entries'][0]['name'],'status':'removed','classic':o,'forever':None,'differences':[]})
    return out

EFFECT_LABELS={'Effect':'Effect type','EffectAura':'Aura','EffectAuraPeriod':'Tick interval (ms)','EffectBasePointsF':'Base value (mean)','Variance':'Variance','EffectBonusCoefficient':'Spell power coefficient','EffectRealPointsPerLevel':'Value per level','Coefficient':'Scaling coefficient','BonusCoefficientFromAP':'Attack power coefficient','ResourceCoefficient':'Resource coefficient','EffectTriggerSpell':'Triggered spell','EffectChainTargets':'Chain targets','EffectMiscValue_0':'Effect parameter 1','EffectMiscValue_1':'Effect parameter 2'}

def record_diffs(old,new):
    changes=[]
    if old['name']!=new['name']:changes.append({'field':'Name','old':old['name'],'new':new['name']})
    for k in old['metrics']:
        if old['metrics'][k]!=new['metrics'][k]:changes.append({'field':k,'old':old['metrics'][k],'new':new['metrics'][k]})
    if normalize(old['description'])!=normalize(new['description']):changes.append({'field':'Description','old':'Classic text','new':'Forever text'})
    a={r['index']:r for r in old['effects']};c={r['index']:r for r in new['effects']}
    for ix in sorted(set(a)|set(c)):
        if ix not in a or ix not in c:
            changes.append({'field':f'Effect {ix+1}','old':'present' if ix in a else '—','new':'present' if ix in c else '—'});continue
        for k in EFFECT_LABELS:
            if a[ix][k]!=c[ix][k]:changes.append({'field':f'Effect {ix+1} · {EFFECT_LABELS[k]}','old':a[ix][k],'new':c[ix][k]})
    return changes

def spell_comparison(cid,classic,forever,seed,all_old_ids,talent_ids):
    old={};new={};extras={}
    for ctx,dest in [(classic,old),(forever,new)]:
        ctx.activate()
        for a in ctx.abilities:
            sid=int(a['Spell']);skill=int(a['SkillLine']);mask=int(a['ClassMask'])
            if skill not in SKILLS[cid] or (mask and not(mask&(1<<(cid-1)))):continue
            if sid not in ctx.names or not ctx.spells.get(sid,{}).get('Description_lang'):continue
            rec={**ctx.record(sid),'skill':ctx.skills.get(skill,{}).get('DisplayName_lang',str(skill)),'talent':sid in talent_ids}
            if sid not in seed:
                if ctx.classic:continue
                if sid in all_old_ids:
                    extras[sid]=rec;continue
                rec['candidate']=True
            dest[sid]=rec
    def families(items):
        d=collections.defaultdict(list)
        for r in items.values():d[normalize(r['name'])].append(r)
        for rs in d.values():rs.sort(key=lambda r:(r['metrics']['Level'],int(next(iter(re.findall(r'\d+',r['subtext'])),0)),r['spellID']))
        return d
    a=families(old);c=families(new);out=[]
    # Connect families by spell ID first, retaining renames and merges. A shared
    # name also groups replacements, but unlike matching IDs cannot compare ranks.
    parent={('old',k):('old',k) for k in a}|{('new',k):('new',k) for k in c}
    def root(key):
        while parent[key]!=key:
            parent[key]=parent[parent[key]];key=parent[key]
        return key
    def union(x,y):parent[root(y)]=root(x)
    old_key={r['spellID']:k for k,rs in a.items() for r in rs}
    for k,rs in c.items():
        if k in a:union(('old',k),('new',k))
        for r in rs:
            if r['spellID'] in old_key:union(('old',old_key[r['spellID']]),('new',k))
    components=collections.defaultdict(lambda:{'old':[],'new':[]})
    for side,k in parent:components[root((side,k))][side].extend((a if side=='old' else c)[k])
    for component in components.values():
        os=component['old'];ns=component['new'];om={r['spellID']:r for r in os};nm={r['spellID']:r for r in ns}
        differences=[];pairs=[]
        for sid in sorted(set(om)|set(nm),key=lambda sid:((nm.get(sid) or om[sid])['metrics']['Level'],sid)):
            o=om.get(sid);n=nm.get(sid);ds=record_diffs(o,n) if o and n else []
            pairs.append({'spellID':sid,'classic':o,'forever':n,'differences':ds})
        if os and ns:
            if set(om)!=set(nm):differences.append('Spell ranks / variants')
            categories={d['field'].split(' · ')[-1] for pair in pairs for d in pair['differences']}
            differences.extend(sorted(categories))
        status='added' if not os else 'removed' if not ns else 'changed' if differences else 'unchanged'
        rec=next(iter(ns or os));names=sorted({r['name'] for r in ns or os});oldnames=sorted({r['name'] for r in os})
        out.append({'name':' / '.join(names),'previousNames':oldnames if oldnames!=names else [],'iconID':rec['iconID'],'status':status,'pairs':pairs,'differences':differences,'passive':all(r['passive'] for r in os+ns),'talent':all(r['talent'] for r in os+ns),'extra':False})
    for key,rs in families(extras).items():
        out.append({'name':rs[0]['name'],'iconID':rs[0]['iconID'],'status':'extra','pairs':[{'spellID':r['spellID'],'classic':None,'forever':r,'differences':[]} for r in rs],'differences':[],'passive':all(r['passive'] for r in rs),'talent':all(r['talent'] for r in rs),'extra':True})
    return sorted(out,key=lambda r:(r['extra'],r['name'].casefold()))

def main():
    # Start from the complete original talent export, retaining its exact curves.
    b.build()
    data=json.loads((b.OUT/'talents.json').read_text(encoding='utf-8'))
    classic=Context(CLASSIC_FOLDER,True);forever=Context('db2')
    seed={int(r['Spell']) for r in classic.abilities}
    all_old_ids={int(r['ID']) for r in read('classic-db2','SpellName')}
    talent_ids={int(r[f'SpellRank_{i}']) for r in read(CLASSIC_FOLDER,'Talent') for i in range(9) if int(r[f'SpellRank_{i}'])}
    talent_ids|={e['spellID'] for c in data['classes'] for ts in [c['trees']] for t in flat(ts) for e in t['entries']}
    for c in data['classes']:
        classic.activate();c['classicTrees']=classic_trees(classic,c['id'],[t['name'] for t in c['trees']])
        c['talentChanges']=talent_comparison(flat(c['classicTrees']),flat(c['trees']))
        c['spells']=spell_comparison(c['id'],classic,forever,seed,all_old_ids,talent_ids)
        # Removed from the regular tree is distinct from surviving in an off-grid node.
        for change in c['talentChanges']:
            if change['status']=='removed' and any(normalize(change['name'])==normalize(t['entries'][0]['name']) for t in c['extraTalents']):change['differences'].append('Present in Forever only as a node outside the grid')
    data['classicBuild']=ERA_BUILD;data['referenceBuild']=REFERENCE_BUILD
    wanted=set()
    def collect(obj):
        if isinstance(obj,dict):
            if 'iconID' in obj:wanted.add(obj['iconID'])
            for value in obj.values():collect(value)
        elif isinstance(obj,list):
            for value in obj:collect(value)
    collect(data)
    mapping={}
    with (BASE/'community-listfile.csv').open(encoding='utf-8') as f:
        for line in f:
            key,_,path=line.strip().partition(';')
            if key.isdigit() and int(key) in wanted:mapping[int(key)]=path
    (BASE/'icon-map.json').write_text(json.dumps(mapping,indent=2),encoding='utf-8')
    def add_icons(obj):
        if isinstance(obj,dict):
            obj.pop('icon',None)
            for value in obj.values():add_icons(value)
        elif isinstance(obj,list):
            for value in obj:add_icons(value)
    add_icons(data)
    data['icons']={i:icon(i) for i in sorted(wanted) if icon(i)}
    # Nine rail icons also support the original renderer before comparison init.
    for c in data['classes']:c['icon']=data['icons'].get(c['iconID'],'')
    report={c['name']:{'classicTalents':sum(len(t['talents']) for t in c['classicTrees']),'talents':dict(collections.Counter(d['status'] for d in c['talentChanges'])),'spells':dict(collections.Counter(d['status'] for d in c['spells']))} for c in data['classes']}
    (BASE/'comparison-validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    (b.OUT/'talents.json').write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
    payload=json.dumps(data,ensure_ascii=False,separators=(',',':')).replace('</','<\\/')
    html=(b.ROOT/'site'/'index.template.html').read_text(encoding='utf-8').replace('/*TALENT_DATA*/null',payload)
    css='\n'.join((b.ROOT/'site'/name).read_text(encoding='utf-8') for name in ['comparison.css','planner.css'])
    js='\n'.join((b.ROOT/'site'/name).read_text(encoding='utf-8') for name in ['comparison.js','planner-engine.js','planner.js'])
    html=html.replace('</style>',css+'\n</style>').replace('if(DATA)init();','if(DATA)init();\n'+js)
    (b.OUT/'index.html').write_text(html,encoding='utf-8',newline='\n')
    public=b.ROOT/'docs'
    public.mkdir(exist_ok=True)
    (public/'index.html').write_text(html,encoding='utf-8',newline='\n')
    (public/'.nojekyll').touch()
    print(json.dumps(report,ensure_ascii=False))

if __name__=='__main__':main()
