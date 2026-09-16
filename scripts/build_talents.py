"""Build an offline talent viewer from the preserved Forever DB2 exports."""
from __future__ import annotations
import argparse, ast, base64, collections, csv, hashlib, json, operator, re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EVIDENCE = ROOT / 'evidence' / '2026-09-16'
DB = EVIDENCE / 'db2'
OUT = ROOT / 'dist'

def rows(name):
    with (DB / f'{name}.csv').open(encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(f))

def index(name, key='ID'):
    return {int(r[key]): r for r in rows(name)}

def group(name, key):
    result = collections.defaultdict(list)
    for r in rows(name): result[int(r[key])].append(r)
    return result

SPELLS, NAMES = index('Spell'), index('SpellName')
DEFS, ENTRIES = index('TraitDefinition'), index('TraitNodeEntry')
MISC = {int(r['SpellID']):r for r in rows('SpellMisc') if r['DifficultyID']=='0'}
EFFECTS = {(int(r['SpellID']),int(r['EffectIndex'])):r for r in rows('SpellEffect') if r['DifficultyID']=='0'}
AURAS = {int(r['SpellID']):r for r in rows('SpellAuraOptions') if r['DifficultyID']=='0'}
DURATION, RADIUS, RANGE = index('SpellDuration'), index('SpellRadius'), index('SpellRange')
POINTS, CURVES = group('TraitDefinitionEffectPoints','TraitDefinitionID'), group('CurvePoint','CurveID')
LINKS = group('TraitNodeXTraitNodeEntry','TraitNodeID')
NODES = index('TraitNode')
VARIABLES=index('SpellDescriptionVariables')
SPELL_VARIABLES={int(r['SpellID']):VARIABLES[int(r['SpellDescriptionVariablesID'])]['Variables'] for r in rows('SpellXDescriptionVariables')}
CLASS_CONFIG = {
 1:('warrior','Warrior',1117,['Arms','Fury','Protection']),
 2:('paladin','Paladin',1100,['Holy','Protection','Retribution']),
 3:('hunter','Hunter',1091,['Beast Mastery','Marksmanship','Survival']),
 4:('rogue','Rogue',1111,['Assassination','Combat','Subtlety']),
 5:('priest','Priest',1114,['Discipline','Holy','Shadow']),
 7:('shaman','Shaman',1082,['Elemental','Enhancement','Restoration']),
 8:('mage','Mage',1112,['Arcane','Fire','Frost']),
 9:('warlock','Warlock',1116,['Affliction','Demonology','Destruction']),
 11:('druid','Druid',1089,['Balance','Feral Combat','Restoration']),
}

def fmt(value):
    return f'{value:.3f}'.rstrip('0').rstrip('.') if value else '0'

def arithmetic(expression):
    ops={ast.Add:operator.add,ast.Sub:operator.sub,ast.Mult:operator.mul,ast.Div:operator.truediv,ast.USub:operator.neg,ast.UAdd:operator.pos}
    def walk(n):
        if isinstance(n,ast.Constant) and type(n.value) in (int,float): return n.value
        if isinstance(n,ast.BinOp) and type(n.op) in ops: return ops[type(n.op)](walk(n.left),walk(n.right))
        if isinstance(n,ast.UnaryOp) and type(n.op) in ops:return ops[type(n.op)](walk(n.operand))
        raise ValueError('Dynamic expression')
    return walk(ast.parse(expression,mode='eval').body)

def rank_overrides(definition,rank):
    result={}
    for p in POINTS[definition]:
        if p['OperationType']!='0':continue
        exact=next((c for c in CURVES[int(p['CurveID'])] if float(c['Pos_0'])==rank),None)
        if exact:result[int(p['EffectIndex'])]=float(exact['Pos_1'])
    return result

def effect_value(sid,ix,origin,overrides):
    if sid==origin and ix in overrides:return overrides[ix]
    e=EFFECTS.get((sid,ix))
    if not e:return None
    # This is a character-independent reader: use the explicit base amount. The
    # UI separately labels spells that can scale with level or character stats.
    if float(e['EffectBasePointsF'])==0 and any(float(e.get(k,0)) for k in ('EffectRealPointsPerLevel','Coefficient','BonusCoefficientFromAP','ResourceCoefficient')):return None
    return float(e['EffectBasePointsF'])

def resolve_description(text,sid,definition,rank,depth=0,origin=None,overrides=None):
    if depth>6:return text
    if origin is None:origin=sid
    if overrides is None:overrides=rank_overrides(definition,rank)
    # Variable definitions and references are data only. No code is executed.
    for name,value in re.findall(r'\$(\w+)=(.*?)(?=\n\$|$)',SPELL_VARIABLES.get(sid,''),re.S):
        text=text.replace('$<'+name+'>',value.strip())
    text=re.sub(r'\$@spellname(\d+)',lambda m:NAMES.get(int(m[1]),{}).get('Name_lang',m[0]),text)
    text=re.sub(r'\$@spelldesc(\d+)',lambda m:resolve_description(SPELLS.get(int(m[1]),{}).get('Description_lang',m[0]),int(m[1]),definition,rank,depth+1,origin,overrides),text)
    token=re.compile(r'\$(?:(\d+))?([sSmMoOaAtTdDhHuUnNrR])(\d*)(?![A-Za-z])')
    def substitute(m,signed=False):
        target=int(m[1]) if m[1] else sid; kind=m[2].lower();ix=int(m[3] or 1)-1
        ef=EFFECTS.get((target,ix),{});misc=MISC.get(target,{})
        value=None
        if kind in ('s','m'):value=effect_value(target,ix,origin,overrides)
        elif kind=='d':
            duration=DURATION.get(int(misc.get('DurationIndex',0)),{}).get('Duration')
            if duration is not None and float(duration)>=0:value=float(duration)/1000
            if value is not None and not signed:return fmt(value)+' sec'
        elif kind=='t':value=float(ef.get('EffectAuraPeriod',0))/1000 or None
        elif kind=='a':
            rad=RADIUS.get(int(ef.get('EffectRadiusIndex_0',0)),{})
            if rad and float(rad.get('RadiusPerLevel',0))==0:value=float(rad['Radius'])
        elif kind=='r':
            r=RANGE.get(int(misc.get('RangeIndex',0)),{})
            if r:value=float(r['RangeMax_0'])
        elif kind in ('h','u','n'):
            a=AURAS.get(target,{})
            k={'h':'ProcChance','u':'CumulativeAura','n':'ProcCharges'}[kind]
            if k in a:value=float(a[k])
        elif kind=='o':
            val=effect_value(target,ix,origin,overrides);dur=DURATION.get(int(misc.get('DurationIndex',0)),{}).get('Duration');period=float(ef.get('EffectAuraPeriod',0))
            if val is not None and dur is not None and period>0 and float(dur)>0:value=val*float(dur)/period
        if value is None:return m[0]
        return fmt(value if signed else abs(value))
    def legacy_math(m):
        value=token.sub(lambda t:substitute(t,True),'$'+m[3])
        try:
            number=arithmetic(value)
            return fmt(abs(number/float(m[2]) if m[1]=='/' else number*float(m[2])))
        except (ValueError,TypeError,SyntaxError,ZeroDivisionError):return m[0]
    text=re.sub(r'\$([/*])([\d.]+);((?:\d+)?[sSmMoO]\d+)',legacy_math,text)
    # Evaluate constant expressions with signed effect values, then format plain tokens.
    for _ in range(5):
        previous=text
        def expr(m):
            value=token.sub(lambda t:substitute(t,True),m[1])
            try:return fmt(arithmetic(value))
            except (ValueError,TypeError,SyntaxError,ZeroDivisionError):return '${'+value+'}'
        text=re.sub(r'\$\{([^{}]*)\}(?:\.\d)?',expr,text)
        if text==previous:break
    text=token.sub(substitute,text)
    if '$proccooldown' in text and sid in AURAS:
        text=text.replace('$proccooldown',fmt(float(AURAS[sid]['ProcCategoryRecovery'])/1000))
    text=re.sub(r'\$[lL]([^:;]*):([^;]*);',lambda m:m[2],text)
    text=re.sub(r'\|[cC][0-9a-fA-F]{8}|\|[rR]','',text).replace('|n','\n')
    text=re.sub(r'\|T[^|]*\|t','',text)
    text=re.sub(r'\r+\n?', '\n',text)
    text=re.sub(r'\n{3,}','\n\n',text)
    return text.strip()

def make_entry(link):
    entry=ENTRIES[int(link['TraitNodeEntryID'])];did=int(entry['TraitDefinitionID']);definition=DEFS[did];sid=int(definition['SpellID'])
    visible=int(definition['VisibleSpellID']) or sid
    name=definition['OverrideName_lang'] or NAMES.get(sid,{}).get('Name_lang') or NAMES.get(visible,{}).get('Name_lang')
    assert name, ('Missing spell name',sid,did)
    description=definition['OverrideDescription_lang'] or SPELLS.get(sid,{}).get('Description_lang','')
    if not description and visible!=sid:description=SPELLS.get(visible,{}).get('Description_lang','')
    maxr=int(entry['MaxRanks'])
    ranks=[]
    for rank in range(1,maxr+1):
        resolved=resolve_description(description,sid,did,rank)
        ranks.append({'rank':rank,'description':resolved,'unresolved':'$' in resolved})
    icon=int(definition['OverrideIcon']) or int(MISC.get(visible,{}).get('SpellIconFileDataID',0))
    referenced={sid}|{int(x) for x in re.findall(r'\$(\d+)[a-zA-Z]',description)}
    scaling_types={2,10,17,31,58,121}
    scaling_auras={3,8,69}
    base_notice=any(s in referenced and (int(e['Effect']) in scaling_types or (int(e['Effect'])==6 and int(e['EffectAura']) in scaling_auras)) for (s,_),e in EFFECTS.items())
    return {'id':int(entry['ID']),'definitionID':did,'spellID':sid,'name':name,'description':description,'maxRanks':maxr,'iconID':icon,'ranks':ranks,'baseValueNotice':base_notice,'ranksEstimated':maxr>1 and not POINTS[did] and '$' in description}

def build():
    classes=index('ChrClasses');group_nodes=group('TraitNodeGroupXTraitNode','TraitNodeGroupID');conds=index('TraitCond')
    node_conds=collections.defaultdict(list)
    for link in rows('TraitNodeGroupXTraitCond'):
        for n in group_nodes[int(link['TraitNodeGroupID'])]:node_conds[int(n['TraitNodeID'])].append(conds[int(link['TraitCondID'])])
    for link in rows('TraitNodeXTraitCond'):node_conds[int(link['TraitNodeID'])].append(conds[int(link['TraitCondID'])])
    edges=rows('TraitEdge'); result=[];layout_notes=[]
    # Class-to-tree association is corroborated by SkillLineXTraitTree and each class's spell names.
    mapped_trees={int(r['TraitTreeID']) for r in rows('SkillLineXTraitTree')}
    assert mapped_trees=={v[2] for v in CLASS_CONFIG.values()}
    for cid,(key,name,treeid,tree_names) in CLASS_CONFIG.items():
        cr=classes[cid];color='#'+''.join(f'{int(cr[k]):02x}' for k in ['ClassColorR','ClassColorG','ClassColorB'])
        c={'id':cid,'key':key,'name':name,'nameEN':cr['Name_lang'],'color':color,'iconID':int(cr['IconFileDataID']),'trees':[],'extraTalents':[]}
        by_branch=[[],[],[]]
        for n in NODES.values():
            if int(n['TraitTreeID'])!=treeid:continue
            nid=int(n['ID']);x=int(n['PosX']);y=int(n['PosY']);original_x=x
            branch=0 if x<4000 else 1 if x<8000 else 2
            base=[1020,5020,9080][branch];column=(x-base)/600
            position=12.5+column*25
            entries=[make_entry(l) for l in sorted(LINKS[nid],key=lambda a:int(a['_Index']))]
            assert entries,('Missing entry',nid)
            required=[int(co['SpentAmountRequired']) for co in node_conds[nid] if co['CondType']=='0']
            talent={'id':nid,'row':round((y-2130)/600),'x':position,'sourceX':original_x,'sourceY':y,'requiredPoints':max(required) if required else 0,'entries':entries}
            if x>20000 or y>20000:
                talent['outsideGrid']=True
                c['extraTalents'].append(talent)
                layout_notes.append({'node':nid,'name':entries[0]['name'],'sourceX':original_x,'sourceY':y,'note':'Outside the normal tree grid. Preserved and shown separately; availability unclear.'})
            else:by_branch[branch].append(talent)
        for branch,talents in enumerate(by_branch):
            talents.sort(key=lambda t:(t['row'],t['x']));ids={t['id'] for t in talents}
            es=[{'from':int(e['LeftTraitNodeID']),'to':int(e['RightTraitNodeID']),'type':int(e['Type'])} for e in edges if int(e['LeftTraitNodeID']) in ids and int(e['RightTraitNodeID']) in ids and e['Type'] in ('2','3')]
            # Preserve the beta's edge direction, including anomalous backwards links.
            lookup={t['id']:t for t in talents}
            for e in es:
                if lookup[e['from']]['row']>lookup[e['to']]['row']:
                    e['warning']='Backwards connection in the client snapshot.'
                    layout_notes.append({'edge':e,'note':'Direction preserved from TraitEdge.'})
            c['trees'].append({'id':f'{treeid}-{branch}','sourceTreeID':treeid,'name':tree_names[branch],'talents':talents,'edges':es,'rows':max(t['row'] for t in talents)+1})
        result.append(c)
    dataset={'build':'1.60.1.69876','localeLabel':'Talent text: English','classes':result,'layoutNotes':layout_notes,'source':'https://wago.tools/db2/TraitNode?build=1.60.1.69876'}
    all_talents=[t for c in result for tree in c['trees'] for t in tree['talents']]+[t for c in result for t in c['extraTalents']]
    dataset['totalTalents']=len(all_talents)
    dataset['extraTalents']=sum(len(c['extraTalents']) for c in result)
    assert len(result)==9 and sum(len(c['trees']) for c in result)==27
    assert len(all_talents)==len({t['id'] for t in all_talents})
    wanted={c['iconID'] for c in result}|{e['iconID'] for t in all_talents for e in t['entries']}
    listfile=EVIDENCE/'community-listfile.csv'; iconmap={}
    if listfile.exists():
        with listfile.open(encoding='utf-8') as f:
            for line in f:
                raw_id,_,path=line.strip().partition(';')
                if raw_id.isdigit() and int(raw_id) in wanted:
                    iconmap[int(raw_id)]=path
    (EVIDENCE/'icon-map.json').write_text(json.dumps(iconmap,indent=2),encoding='utf-8')
    for item in list(result)+[e for t in all_talents for e in t['entries']]:
        path=EVIDENCE/'icons'/f"{item['iconID']}.jpg"
        if path.exists():item['icon']='data:image/jpeg;base64,'+base64.b64encode(path.read_bytes()).decode()
    OUT.mkdir(exist_ok=True)
    (OUT/'talents.json').write_text(json.dumps(dataset,ensure_ascii=False,indent=2),encoding='utf-8')
    html=(ROOT/'site'/'index.template.html').read_text(encoding='utf-8')
    payload=json.dumps(dataset,ensure_ascii=False,separators=(',',':')).replace('</','<\\/')
    (OUT/'index.html').write_text(html.replace('/*TALENT_DATA*/null',payload),encoding='utf-8')
    all_entries=[e for t in all_talents for e in t['entries']]
    unresolved=[{'name':e['name'],'spellID':e['spellID'],'description':e['ranks'][-1]['description']} for e in all_entries if any(r['unresolved'] for r in e['ranks'])]
    validation={'build':dataset['build'],'totalTalents':len(all_talents),'outsideGrid':dataset['extraTalents'],'totalEntries':len(all_entries),'totalRanks':sum(e['maxRanks'] for e in all_entries),'unresolvedDescriptions':unresolved,'missingDescriptions':[e['name'] for e in all_entries if not e['description']],'missingIcons':[e['iconID'] for e in all_entries if not e.get('icon')],'layoutNotes':layout_notes,'classes':{c['name']:{t['name']:len(t['talents']) for t in c['trees']} for c in result}}
    (EVIDENCE/'validation.json').write_text(json.dumps(validation,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in validation.items() if k not in ['unresolvedDescriptions','missingIcons']},ensure_ascii=False))
    print('Unresolved talents:',len(unresolved),'Missing icons:',len(validation['missingIcons']))
    print('Page:',OUT/'index.html')

if __name__=='__main__':build()
