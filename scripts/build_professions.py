"""Build the profession archive from audited client tables and Classic exports."""
from __future__ import annotations
import collections, csv, hashlib, json, math, re
from pathlib import Path
from build_comparison import Context, normalize
from build_pvp import flat
import build_talents as talent

ROOT = Path(__file__).resolve().parent.parent
BASE = ROOT / 'evidence/2026-09-16'
AUDIT = BASE / 'audit'
BUILD = '1.60.1.69876'
PROFESSIONS = [171, 164, 333, 202, 182, 165, 186, 393, 197, 185, 129, 356]
SPECIALIZATIONS = {9787,9788,17039,17040,17041,10656,10658,10660,20219,20222}
SLOTS = {1:'Head',2:'Neck',3:'Shoulder',5:'Chest',6:'Waist',7:'Legs',8:'Feet',9:'Wrist',10:'Hands',11:'Finger',12:'Trinket',13:'One-hand',14:'Shield',15:'Ranged',16:'Back',17:'Two-hand',18:'Bag',19:'Tabard',20:'Robe',21:'Main hand',22:'Off hand',23:'Held in off hand',24:'Ammo',25:'Thrown',26:'Ranged',28:'Relic'}

def read(folder, table):
    return json.loads((AUDIT/folder/f'{table}.json').read_text(encoding='utf-8'))

def csv_rows(folder, table):
    p=BASE/folder/f'{table}.csv'
    if not p.exists():return []
    with p.open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))

def index(rows, key='ID'):return {int(r[key]):r for r in rows}

def audit_tables():
    results=[]
    for source in json.loads((AUDIT/'profession-extraction.json').read_text()):
        assert 'error' not in source,source
        name=source['table'];actual=index([flat(r) for r in read('profession-db2',name)])
        exported=csv_rows('professions-forever',name)
        if not actual:
            assert not exported,name
            results.append({**source,'status':'Empty','comparedFields':0});continue
        assert exported,name
        mapping={}
        first=next(iter(actual.values()))
        if first.keys()!=exported[0].keys():
            assert name=='SkillLineCategory' and len(first)==len(exported[0]),name
            mapping=dict(zip(exported[0],first))
            assert mapping['ID']=='ID'
            exported=[{mapping[k]:v for k,v in r.items()} for r in exported]
        expected=index(exported)
        assert actual.keys()==expected.keys(),name
        count=0
        for rid,row in actual.items():
            assert row.keys()==expected[rid].keys(),(name,rid)
            for k,v in row.items():
                e=expected[rid][k]
                good=math.isclose(v,float(e),rel_tol=1e-6,abs_tol=1e-6) if isinstance(v,(int,float)) else str(v).replace('\r\n','\n')==e.replace('\r\n','\n')
                assert good,(name,rid,k,v,e)
                count+=1
        results.append({**source,'status':'Matched export','comparedFields':count,'columnMapping':mapping})
    return {'build':BUILD,'date':'2026-09-17','matchedTables':sum(r['status']=='Matched export' for r in results),
        'comparedFields':sum(r['comparedFields'] for r in results),'results':results,
        'supportingAudits':['client-audit.json','content-audit.json','pvp-audit.json'],
        'comparison':'Classic Era 1.14.4.51395; SoD 1.15.9.69722',
        'sources':[{'folder':folder,'table':p.stem,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
            for folder in ['professions-forever','professions-classic','professions-sod'] for p in sorted((BASE/folder).glob('*.csv'))]}

def build():
    audit=audit_tables()
    ctx=Context('db2');classic=Context('era-baseline',classic=True)
    skills=index(read('client-db2','SkillLine'))
    categories=index(read('profession-db2','TradeSkillCategory'))
    item_rows=index(read('content-db2','ItemSparse'))
    factions=index(read('pvp-db2','Faction'))
    old_items=index(csv_rows('content-classic','ItemSparse'))
    item_effects=index(read('content-db2','ItemEffect'))
    effect_links=collections.defaultdict(list)
    for x in read('pvp-db2','ItemXItemEffect'):effect_links[x['ItemID']].append(x['ItemEffectID'])
    books=collections.defaultdict(list)
    for iid,links in effect_links.items():
        if iid not in item_rows:continue
        for eid in links:
            e=item_effects.get(eid,{})
            if e.get('TriggerType')==6:books[e['SpellID']].append(iid)
    spell_rows=index(read('client-db2','Spell'))
    direct_effects=collections.defaultdict(list)
    for e in read('client-db2','SpellEffect'):
        if e['DifficultyID']==0:direct_effects[e['SpellID']].append(e)
    reagents=index(read('profession-db2','SpellReagents'),'SpellID')
    old_reagents=index(csv_rows('professions-classic','SpellReagents'),'SpellID')
    totems=index(read('profession-db2','SpellTotems'),'SpellID')
    old_totems=index(csv_rows('professions-classic','SpellTotems'),'SpellID')
    tool_categories=index(read('profession-db2','TotemCategory'))
    focuses=index(read('profession-db2','SpellFocusObject'))
    old_focuses=index(csv_rows('professions-classic','SpellFocusObject'))
    requirements=index(read('client-db2','SpellCastingRequirements'),'SpellID')
    old_requirements=index(csv_rows('era-baseline','SpellCastingRequirements'),'SpellID')
    assert old_requirements,'Missing pre-SoD casting requirements'
    enchantments=index(read('profession-db2','SpellItemEnchantment'))
    old_enchantments=index(csv_rows('professions-classic','SpellItemEnchantment'))
    sod_ids={int(r['ID']) for r in csv_rows('classic-db2','SpellName')}
    current_abilities=read('client-db2','SkillLineAbility')
    unique_abilities={};duplicates=[]
    for a in current_abilities:
        key=(a['SkillLine'],a['Spell'])
        if a['SkillLine'] in PROFESSIONS and key in unique_abilities:
            first=unique_abilities[key]
            assert {k:v for k,v in a.items() if k!='ID'}=={k:v for k,v in first.items() if k!='ID'},key
            duplicates.append({'kept':first['ID'],'duplicate':a['ID'],'spellID':a['Spell']})
        else:unique_abilities[key]=a
    current_abilities=list(unique_abilities.values())
    old_abilities=classic.abilities
    used_items=set();unresolved=[]

    def item_name(iid,old=False):
        row=(old_items if old else item_rows).get(iid,{})
        return row.get('Display_lang',f'Item {iid}')

    def spell_text(context,sid):
        r=context.record(sid)
        return {k:r[k] for k in ['spellID','name','description','rawDescription','unresolved']}

    def record(a,context,old=False):
        sid=int(a['Spell']);pid=int(a['SkillLine']);r=context.record(sid)
        es=context.effects[sid]
        outputs=[]
        for e in es:
            if int(e['Effect'])!=24:continue
            iid=int(e['EffectItemType'])
            if not iid:continue
            base=float(e.get('EffectBasePointsF',0));variance=float(e.get('Variance',0))
            lo=base-abs(base*variance)/2;hi=base+abs(base*variance)/2
            outputs.append({'id':iid,'min':lo if lo>0 else None,'max':hi if hi>0 else None})
            used_items.add(iid)
        reagent_row=(old_reagents if old else reagents).get(sid,{})
        mats=[]
        for n in range(8):
            iid=int(reagent_row.get(f'Reagent_{n}',0)) if old else reagent_row.get('Reagent',[0]*8)[n]
            qty=int(reagent_row.get(f'ReagentCount_{n}',0)) if old else reagent_row.get('ReagentCount',[0]*8)[n]
            if iid>0 and qty>0:mats.append({'id':iid,'count':qty});used_items.add(iid)
        tr=(old_totems if old else totems).get(sid,{})
        tools=[]
        for n in range(2):
            iid=int(tr.get(f'Totem_{n}',0)) if old else tr.get('Totem',[0,0])[n]
            cid=int(tr.get(f'RequiredTotemCategoryID_{n}',0)) if old else tr.get('RequiredTotemCategoryID',[0,0])[n]
            if iid:tools.append(item_name(iid,old));used_items.add(iid)
            if cid:tools.append(tool_categories.get(cid,{}).get('Name_lang',f'Tool category {cid}'))
        req=(old_requirements if old else requirements).get(sid,{})
        fid=int(req.get('RequiresSpellFocus',0))
        station=(old_focuses if old else focuses).get(fid,{}).get('Name_lang','')
        cat=categories.get(int(a.get('TradeSkillCategoryID',0)),{}).get('Name_lang','Uncategorized') if not old else ''
        types={int(e['Effect']) for e in es}
        kind='specialization' if sid in SPECIALIZATIONS else 'enchant' if types & {53,54} else 'recipe' if outputs else 'training' if 118 in types else 'ability'
        recipe_books=sorted(set(books.get(sid,[]))) if not old else []
        used_items.update(recipe_books)
        enchs=[];description=r['description']
        for e in es:
            if int(e['Effect']) in [53,54]:
                eid=int(e['EffectMiscValue_0']);en=(old_enchantments if old else enchantments).get(eid,{})
                ename=en.get('Name_lang',f'Enchantment {eid}')
                for n in range(3):
                    points=int(en.get(f'EffectPointsMin_{n}',0)) if old else en.get('EffectPointsMin',[0]*3)[n]
                    scale=float(en.get(f'EffectScalingPoints_{n}',0)) if old else en.get('EffectScalingPoints',[0]*3)[n]
                    if points and not scale:
                        ename=ename.replace(f'$k{n+1}',str(points))
                        description=description.replace(f'$ec{n+1}',str(points))
                enchs.append({'id':eid,'name':ename,'requiredSkill':int(en.get('RequiredSkillID',0)),'requiredRank':int(en.get('RequiredSkillRank',0))})
        return {'id':sid,'professionID':pid,'name':r['name'],'subtext':r['subtext'],'kind':kind,'category':cat,
            'description':description,'rawDescription':r['rawDescription'],'unresolved':'$' in description,
            'outputs':outputs,'reagents':mats,'tools':sorted(set(tools)),'station':station,'stationID':fid,
            'castTime':r['metrics']['Cast time (sec)'],'cooldown':r['metrics']['Cooldown (sec)'],
            'skillupLow':int(a.get('TrivialSkillLineRankLow',0)),'skillupHigh':int(a.get('TrivialSkillLineRankHigh',0)),
            'minimumSkillField':int(a.get('MinSkillLineRank',0)),
            'books':recipe_books,'enchantments':enchs,'abilityRowID':int(a['ID'])}

    def normalized_pairs(rows,keys):return sorted(tuple(r[k] for k in keys) for r in rows)

    old_records={};classic.activate()
    for a in old_abilities:
        if int(a['SkillLine']) in PROFESSIONS and int(a['Spell']) in classic.names:
            key=(int(a['SkillLine']),int(a['Spell']))
            old_records[key]=record(a,classic,True)
    ctx.activate();records=[];seen=set();stale=[]
    for a in current_abilities:
        if a['SkillLine'] not in PROFESSIONS:continue
        sid=a['Spell'];key=(a['SkillLine'],sid)
        if sid not in ctx.names or sid not in spell_rows:
            stale.append({'abilityRowID':a['ID'],'professionID':a['SkillLine'],'spellID':sid});continue
        assert key not in seen,key
        seen.add(key);r=record(a,ctx);old=old_records.get(key);diff=[]
        if old:
            if old['name']!=r['name']:diff.append('Name')
            if normalize(old['description'])!=normalize(r['description']):diff.append('Description')
            if normalized_pairs(old['reagents'],['id','count'])!=normalized_pairs(r['reagents'],['id','count']):diff.append('Ingredients')
            if normalized_pairs(old['outputs'],['id','min','max'])!=normalized_pairs(r['outputs'],['id','min','max']):diff.append('Crafted result')
            for key2,title in [('castTime','Cast time'),('cooldown','Cooldown'),('station','Crafting station'),('skillupLow','Skill-up thresholds'),('tools','Tools')]:
                if old[key2]!=r[key2]:diff.append(title)
            if old['skillupHigh']!=r['skillupHigh'] and 'Skill-up thresholds' not in diff:diff.append('Skill-up thresholds')
        status=('changed' if diff else 'unchanged') if old else 'inherited' if sid in sod_ids else 'new'
        r.update(status=status,differences=diff,classic=old,seasonal=r['category']=='SEASON OF DISCOVERY')
        records.append(r)
    for key,r in old_records.items():
        if key not in seen:records.append({**r,'status':'removed','differences':[],'classic':None,'seasonal':False})
    output_ids={i['id'] for r in records for i in r['outputs']}
    items={}
    for iid in sorted(used_items):
        i=item_rows.get(iid);old=old_items.get(iid,{})
        classic_item={'name':old['Display_lang'],'itemLevel':int(old['ItemLevel']),'requiredLevel':int(old['RequiredLevel']),'quality':int(old['OverallQualityID'])} if old else None
        if not i:
            items[iid]={'id':iid,'name':old.get('Display_lang',f'Item {iid}'),'available':False,'classicName':old.get('Display_lang'),'classic':classic_item,'effects':[]};continue
        effects=[]
        if iid in output_ids:
            for eid in effect_links[iid]:
                e=item_effects.get(eid)
                if not e or e['TriggerType']==6:continue
                text=spell_text(ctx,e['SpellID'])
                if text['description']:
                    effects.append({**text,'triggerType':e['TriggerType'],'cooldownMS':max(e['CoolDownMSec'],e['CategoryCoolDownMSec'],0)})
                    if text['unresolved']:unresolved.append({'itemID':iid,**text})
        items[iid]={'id':iid,'name':i['Display_lang'],'available':True,'quality':i['OverallQualityID'],
            'itemLevel':i['ItemLevel'],'requiredLevel':i['RequiredLevel'],'requiredSkill':i['RequiredSkill'],'requiredSkillRank':i['RequiredSkillRank'],
            'requiredAbility':i['RequiredAbility'],'slot':SLOTS.get(i['InventoryType'],''),'containerSlots':i['ContainerSlots'],
            'requiredAbilityName':ctx.names.get(i['RequiredAbility'],''),
            'requiredFaction':factions.get(i['MinFactionID'],{}).get('Name_lang',''),
            'requiredReputation':{4:'Friendly',5:'Honored',6:'Revered',7:'Exalted'}.get(i['MinReputation'],''),
            'description':i['Description_lang'],'effects':effects,'classic':classic_item}
    professions=[]
    for pid in PROFESSIONS:
        rs=[r for r in records if r['professionID']==pid]
        current=[r for r in rs if r['status']!='removed' and not r['seasonal']]
        recipes=[r for r in current if r['kind'] in ['recipe','enchant']]
        professions.append({'id':pid,'name':skills[pid]['DisplayName_lang'],
            'type':'Secondary' if pid in [185,129,356] else 'Primary',
            'description':skills[pid]['Description_lang'],
            'recipes':len(recipes),'new':sum(r['status']=='new' for r in recipes),
            'changed':sum(r['status']=='changed' for r in recipes),
            'campIDs':[r['id'] for r in recipes if r['category']=='Camping'],
            'specializationIDs':[r['id'] for r in current if r['kind']=='specialization']})
    prototypes=[{'id':r['ID'],'name':r['Name_lang'],'skillID':r['SkillLineID']} for r in categories.values() if 'PROTOTYPE' in r['Name_lang']]
    related_ids={1225468,1225465,1225460,1225457,1225455,1225435,1225503,1225502,1225499,1225479}
    defs=index(read('client-db2','TraitDefinition'));trait_entries=read('client-db2','TraitNodeEntry')
    node_links=read('client-db2','TraitNodeXTraitNodeEntry');related=[]
    for sid in sorted(related_ids):
        variants=[]
        for entry in trait_entries:
            d=defs.get(entry['TraitDefinitionID'],{})
            if d.get('SpellID')!=sid:continue
            variants.append({'definitionID':d['ID'],'entryID':entry['ID'],'maxRanks':entry['MaxRanks'],
                'nodeIDs':[x['TraitNodeID'] for x in node_links if x['TraitNodeEntryID']==entry['ID']],
                'ranks':[talent.resolve_description(ctx.spells[sid]['Description_lang'],sid,d['ID'],rank) for rank in range(1,entry['MaxRanks']+1)]})
        related.append({'spellID':sid,'name':ctx.names[sid],'variants':variants})
    audit.update(staleAbilityReferences=stale,duplicateAbilityRows=duplicates,unresolvedOutputDescriptions=len(unresolved))
    (BASE/'profession-unresolved.json').write_text(json.dumps(unresolved,ensure_ascii=False,indent=2),encoding='utf-8')
    data={'build':BUILD,'date':'2026-09-17','professions':professions,'records':records,'items':items,'prototypes':prototypes,'relatedTalents':related,
        'summary':{'professions':len(professions),'recipes':sum(p['recipes'] for p in professions),'newRecipeIDs':sum(p['new'] for p in professions),
            'changedRecipes':sum(p['changed'] for p in professions),'campRecipeIDs':sum(len(p['campIDs']) for p in professions),
            'seasonalRecords':sum(r['seasonal'] for r in records),'removedRecords':sum(r['status']=='removed' for r in records)},
        'officialSource':'https://worldofwarcraft.blizzard.com/en-us/news/24303313/world-of-warcraft-forever-deep-dive-panel-recap'}
    assert len(professions)==12 and len({r['id'] for r in professions})==12
    assert all(any(r['category']=='Camping' for r in records if r['professionID']==pid) for pid in PROFESSIONS)
    assert next(r for r in records if r['id']==1244431)['professionID']==129
    assert items[251332]['requiredSkillRank']==35
    assert next(r for r in records if r['id']==1252229)['books']==[251332]
    assert next(r for r in records if r['id']==1306126)['station']=='Molten Foundry'
    for r in records:
        assert all(x['id'] in items for x in r['reagents']+r['outputs'])
        assert all(i in items for i in r['books'])
    report=['# Profession findings — September 17, 2026','',f'Forever {BUILD}. [Open the profession viewer](https://maf2414.github.io/wow-forever-talents/professions.html).','',
        '## Catalog','','Counts below include recipes and enchantments with named spell records. Explicit Season of Discovery categories are excluded from the main counts. New means the spell ID is absent from both the Classic and SoD spell-name tables; new IDs can produce familiar items.','',
        '| Profession | Recipes | New IDs | Changed vs. Classic | Camping IDs |','|---|---:|---:|---:|---:|']
    for p in professions:report.append(f'| {p["name"]} | {p["recipes"]} | {p["new"]} | {p["changed"]} | {len(p["campIDs"])} |')
    report+=['','## Reading the data','','Recipe ingredients come from SpellReagents; results come from create-item effects. Tools and crafting stations use SpellTotems and SpellCastingRequirements. Recipe books are joined through ItemXItemEffect and ItemEffect trigger type 6. Book requirements are displayed separately from skill-up thresholds; the client ability minimum is not used as a trainer learning requirement.','',
        'The comparison covers recipe names, descriptions, ingredients, results, cast times, cooldowns, tools, stations and skill-up thresholds. It does not equate an unchanged recipe with unchanged item stats. Classic-only records can be inspected separately. Missing current item metadata is retained as an ID; a Classic name is explicitly labeled.','',
        '## Notable findings','','First Aid has six healing potion recipes from Minor through Major, plus tourniquets, poultices and anti-venoms. All twelve professions have camping recipes. Blueprint item requirements include skill 140 for Tanning Rack and Repair Bot. Heavy Thorium smelting requires a Molten Foundry.','',
        'Ten familiar specialization spells remain linked to Blacksmithing, Leatherworking and Engineering. Jewelcrafting appears under a Test Profession with categories explicitly named PROTOTYPE; it is not counted among the twelve professions.','',
        '## Sources','','[Profession data](professions-data.json) · [Extraction audit](professions-audit.json). The audit includes the independently decoded additional tables and links to the earlier spell, item and item-effect audits.']
    html=(ROOT/'site/professions.template.html').read_text(encoding='utf-8')
    html=html.replace('/*PROFESSION_DATA*/null',json.dumps(data,ensure_ascii=False,separators=(',',':')).replace('</','<\\/'))
    html=html.replace('/*PROFESSION_SCRIPT*/',(ROOT/'site/professions.js').read_text(encoding='utf-8'))
    for folder in ['docs','dist']:
        (ROOT/folder/'professions-data.json').write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8',newline='\n')
        (ROOT/folder/'professions-audit.json').write_text(json.dumps(audit,ensure_ascii=False,indent=2),encoding='utf-8',newline='\n')
        (ROOT/folder/'professions-findings.md').write_text('\n'.join(report)+'\n',encoding='utf-8',newline='\n')
        (ROOT/folder/'professions.html').write_text(html,encoding='utf-8',newline='\n')
    (BASE/'professions-browser-script.js').write_text(re.search(r'<script>([\s\S]*)</script>',html)[1],encoding='utf-8')
    print(json.dumps(data['summary']))
    print(json.dumps({'matchedTables':audit['matchedTables'],'comparedFields':audit['comparedFields'],'unresolvedOutputDescriptions':len(unresolved)}))
    return data

if __name__=='__main__':build()
