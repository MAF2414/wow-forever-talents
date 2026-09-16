"""Mine PvP progression, battlegrounds and rewards from the preserved Forever build."""
from __future__ import annotations
import collections, csv, hashlib, json, math
from pathlib import Path
from build_comparison import Context

ROOT=Path(__file__).resolve().parent.parent
BASE=ROOT/'evidence/2026-09-16'
AUDIT=BASE/'audit'
BUILD='1.60.1.69876'
CLASSES={1:'Warrior',2:'Paladin',4:'Hunter',8:'Rogue',16:'Priest',64:'Shaman',128:'Mage',256:'Warlock',1024:'Druid'}
REPUTATION={4:'Friendly',5:'Honored',6:'Revered',7:'Exalted'}
SLOTS={1:'Head',2:'Neck',3:'Shoulder',5:'Chest',6:'Waist',7:'Legs',8:'Feet',9:'Wrist',10:'Hands',11:'Finger',12:'Trinket',19:'Tabard'}

def read(table,folder='pvp-db2'):
    return json.loads((AUDIT/folder/f'{table}.json').read_text(encoding='utf-8'))

def index(rows):return {int(r['ID']):r for r in rows}

def exported(version,table):
    p=BASE/f'pvp-{version}'/f'{table}.csv'
    if not p.exists():return []
    with p.open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))

def flat(row):
    result={}
    for k,v in row.items():
        if k=='Index':k='_Index'
        if isinstance(v,list):result.update({f'{k}_{i}':x for i,x in enumerate(v)})
        else:result[k]=v
    return result

def audit_tables():
    results=[]
    for source in json.loads((AUDIT/'pvp-extraction.json').read_text()):
        name=source['table'];csv_data=exported('forever',name)
        if 'error' in source:
            assert not csv_data, f'Exported table was not independently decoded: {name}'
            results.append({'table':name,'status':'Unavailable in this extraction'})
            continue
        actual=index([flat(r) for r in read(name)])
        if not actual:
            assert not csv_data
            results.append({**source,'status':'Empty','comparedFields':0})
            continue
        assert csv_data, name
        mapping={}
        first=next(iter(actual.values()))
        if first.keys()!=csv_data[0].keys():
            assert any(k.startswith('Field_') for k in csv_data[0]) and len(first)==len(csv_data[0]), name
            mapping=dict(zip(csv_data[0],first))
            assert mapping['ID']=='ID'
            csv_data=[{mapping[k]:v for k,v in r.items()} for r in csv_data]
        expected=index(csv_data)
        assert actual.keys()==expected.keys(),name
        count=0
        for rid,row in actual.items():
            assert row.keys()==expected[rid].keys(),(name,rid)
            for key,value in row.items():
                e=expected[rid][key]
                good=math.isclose(value,float(e),rel_tol=1e-6,abs_tol=1e-6) if isinstance(value,(int,float)) else str(value).replace('\r\n','\n')==e.replace('\r\n','\n')
                assert good,(name,rid,key,value,e)
                count+=1
        results.append({**source,'status':'Matched export','comparedFields':count,'columnMapping':mapping})
    return {'build':BUILD,'date':'2026-09-17','results':results,
        'matchedTables':sum(r['status']=='Matched export' for r in results),
        'comparedFields':sum(r.get('comparedFields',0) for r in results),
        'uiFiles':json.loads((AUDIT/'pvp-ui-extraction.json').read_text()),
        'uiSourceRevision':'f0da0a9171aa736c8a64d2b3a8ae70195f5d2afb',
        'sources':[{'version':v,'table':p.stem,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
            for v in ['forever','classic','sod'] for p in sorted((BASE/f'pvp-{v}').glob('*.csv'))]}

def build(sets=None):
    audit=audit_tables()
    if sets is None:sets=json.loads((ROOT/'docs/content-data.json').read_text(encoding='utf-8'))['sets']
    currency=index(read('CurrencyTypes'));factions=index(read('Faction'))
    covenant=index(read('Covenant'));strings={r['BaseTag']:r for r in read('GlobalStrings')}
    assert covenant[46]['FactionID']==2800 and covenant[46]['CurrencyTypesID']==3473
    assert currency[3468]['FactionID']==2800 and currency[3473]['MaxQty']==14
    assert factions[2800]['RenownThresholdCurveID']==103650
    ui=(AUDIT/'pvp-db2/PVPRankFrame.lua').read_text(encoding='utf-8-sig')
    assert 'PVP_RANK_POINTS_FACTION_ID = 2800' in ui
    assert 'currentWeekProgressiveMaxLevel' in ui and 'GetTimeUntilCurrentPVPSeasonEnd' in ui
    rewards=collections.defaultdict(list)
    for r in read('RenownRewards'):
        if r['CovenantID']==46:
            rewards[r['Level']].append({'id':r['ID'],'name':r['Description_lang'],'conditionID':r['PlayerConditionID']})
    ranks=[]
    for n in range(1,15):
        # PvPRanks starts its military titles at enum 5; the client UI maps simple ranks to it.
        h=strings[f'PVP_RANK_{n+4}_0'];a=strings[f'PVP_RANK_{n+4}_1']
        ranks.append({'rank':n,'alliance':a['TagText_lang'],'horde':h['TagText_lang'],
            'rewards':list(dict.fromkeys(r['name'] for r in rewards[n])),
            'rewardRecords':rewards[n],'titleStringIDs':[a['ID'],h['ID']]})
    assert len(rewards)==14 and 'Weapon Arsenal' in ranks[-1]['rewards']
    curves=read('CurvePoint','client-db2')
    cap_curve=[{'input':int(r['Pos'][0]),'maxRank':int(r['Pos'][1]),'pointID':r['ID']} for r in curves if r['CurveID']==currency[3473]['MaxQtyCurveID']]
    cap_curve.sort(key=lambda r:r['input'])
    thresholds=[{'input':int(r['Pos'][0]),'value':int(r['Pos'][1]),'pointID':r['ID']} for r in curves if r['CurveID']==103650]
    thresholds.sort(key=lambda r:r['input'])
    old=index(exported('classic','BattlemasterList'));sod=index(exported('sod','BattlemasterList'))
    maps=index(read('Map','content-db2'));map_links=read('BattlemasterListXMap')
    brackets=read('PVPDifficulty');bg=[]
    for r in read('BattlemasterList'):
        bid=r['ID'];mids=[x['MapID'] for x in map_links if x['BattlemasterListID']==bid]
        old_row=old.get(bid) or sod.get(bid)
        compared=['MinLevel','MaxLevel','MinPlayers','MaxPlayers','GroupsAllowed','MaxGroupSize']
        differences=[{'field':k,'old':int(old_row[k]),'new':r[k]} for k in compared if old_row and int(old_row[k])!=r[k]]
        bg.append({'id':bid,'name':r['Name_lang'],'status':'classic' if bid in old else 'inherited' if bid in sod else 'new',
            **{k:r[k] for k in ['InstanceType','PvpType','MinLevel','MaxLevel','MinPlayers','MaxPlayers','MaxGroupSize','RatedPlayers','Required_Player_Condition_ID']},
            'mapIDs':mids,'maps':[{'id':m,'name':maps.get(m,{}).get('MapName_lang',f'Map {m}'),'inCurrentMapTable':m in maps} for m in mids],
            'brackets':sorted([{'min':b['MinLevel'],'max':b['MaxLevel'],'id':b['ID']} for b in brackets if b['MapID'] in mids],key=lambda b:(b['min'],b['max'])),
            'description':r['LongDescription_lang'],'differences':differences})
    dark=next(r for r in bg if r['id']==1157)
    assert dark['mapIDs']==[2997] and dark['MaxPlayers']==15
    assert [(b['min'],b['max']) for b in dark['brackets']]==[(30,39),(40,49),(50,59),(60,60)]
    assert {m['id'] for b in bg if b['id']==32 for m in b['maps']}=={489,529,2997}
    ctx=Context('db2');ctx.activate()
    def spell(sid):
        r=ctx.record(sid)
        return {k:r[k] for k in ['spellID','name','description','rawDescription','unresolved']}
    spells=[spell(i) for i in [1284560,1290859,1290860,1290861]]
    assert 'any controlled point' in spells[0]['description']
    item_rows=read('ItemSparse','content-db2')
    effects=index(read('ItemEffect','content-db2'));item_effects=collections.defaultdict(list)
    for r in read('ItemXItemEffect'):
        item_effects[r['ItemID']].append(r['ItemEffectID'])
    rep_items=[]
    for r in item_rows:
        if r['MinFactionID'] not in [2798,2799]:continue
        bonuses=[{**spell(e['SpellID']),'triggerType':e['TriggerType'],'cooldownMS':e['CoolDownMSec']} for eid in item_effects[r['ID']] if (e:=effects.get(eid))]
        rep_items.append({'id':r['ID'],'name':r['Display_lang'],'factionID':r['MinFactionID'],
            'faction':factions[r['MinFactionID']]['Name_lang'],'side':'Horde' if r['MinFactionID']==2798 else 'Alliance',
            'reputation':REPUTATION[r['MinReputation']],'reputationRank':r['MinReputation'],
            'itemLevel':r['ItemLevel'],'requiredLevel':r['RequiredLevel'],
            'slot':SLOTS.get(r['InventoryType'],str(r['InventoryType'])),'quality':r['OverallQualityID'],'effects':bonuses,
            'missingEffectIDs':[eid for eid in item_effects[r['ID']] if eid not in effects]})
    assert collections.Counter(r['factionID'] for r in rep_items)=={2798:22,2799:22}
    pvp_sets=[]
    for s in sets:
        if s['category']!='pvp' or s['status'] not in ('new','changed-classic'):continue
        masks={i['AllowableClass'] for i in s['items'] if i['available']}
        assert len(masks)==1 and next(iter(masks)) in CLASSES,s['id']
        pvp_sets.append({'id':s['id'],'name':s['name'],'class':CLASSES[next(iter(masks))],
            'faction':'Alliance' if s['name'].startswith(('Field Marshal', 'Lieutenant Commander')) else 'Horde',
            'status':s['status'],'quality':sorted({i['OverallQualityID'] for i in s['items'] if i['available']}),
            'itemLevels':sorted({i['ItemLevel'] for i in s['items'] if i['available']})})
    assert len(pvp_sets)==60 and len({s['class'] for s in pvp_sets})==9
    assert sum(s['status']=='new' for s in pvp_sets)==26
    headers=index(read('PVPScoreboardColumnHeader'))
    stat=index(read('PVPStat'))
    score=[{'statID':r['PVPStatID'],'headerID':r['PVPScoreboardColumnHeaderID'],'name':headers[r['PVPScoreboardColumnHeaderID']]['Name_lang']}
           for r in read('PVPScoreboardLayout') if stat[r['PVPStatID']]['MapID']==2997]
    item_index=index(item_rows)
    honor_costs=[]
    for r in read('ItemExtendedCost'):
        if 1792 not in r['CurrencyID']:continue
        honor=sum(q for c,q in zip(r['CurrencyID'],r['CurrencyCount']) if c==1792)
        honor_costs.append({'id':r['ID'],'honor':honor,'requiredItems':[{'id':i,'count':n,'name':item_index.get(i,{}).get('Display_lang')}
            for i,n in zip(r['ItemID'],r['ItemCount']) if i]})
    tags=['PVP_RANK_SEASON_RANKUP_DESCRIPTION','PVP_RANK_WEEKLY_CAP_INCREASE','PVP_RANK_REWARDS_VENDOR_ALLIANCE','PVP_RANK_REWARDS_VENDOR_HORDE']
    pvp={'build':BUILD,'date':'2026-09-17','honor':currency[1792],'rankPoints':currency[3468],
        'rankCurrency':currency[3473],'ranks':ranks,'rankCapCurve':cap_curve,'rankThresholdCurve':thresholds,
        'progressionStrings':[strings[t] for t in tags],'seasonRecords':read('PvpSeason'),
        'battlegrounds':bg,'darkspearObjectives':maps[2997]['PvpLongDescription_lang'],
        'darkspearFactions':[{'id':i,'name':factions[i]['Name_lang'],'description':factions[i]['Description_lang']} for i in [2798,2799]],
        'darkspearScoreboard':score,'darkspearSpells':spells,'reputationItems':rep_items,
        'sets':pvp_sets,'honorCostEntries':honor_costs,
        'summary':{'ranks':14,'reputationItems':len(rep_items),'newSets':26,'updatedClassicSets':34,'newBattlemasterRecords':sum(b['status']=='new' for b in bg)},
        'sourceFiles':{'ranks':'https://github.com/Gethe/wow-ui-source/blob/f0da0a9171aa736c8a64d2b3a8ae70195f5d2afb/Interface/AddOns/Blizzard_UIPanels_Game/Camelot/PVPRankFrame.lua',
            'announcement':'https://worldofwarcraft.blizzard.com/en-us/news/24303862/world-of-warcraft-forever-whats-next-panel-recap'}}
    report=['# PvP findings — September 17, 2026','',f'Forever {BUILD}. [Open the PvP viewer](https://maf2414.github.io/wow-forever-talents/content.html#pvp).','',
        '## Honor and ranks','','Honor Points (currency 1792) purchase PvP items and have a stored maximum of 15,000. Rank Points (3468) come from battlegrounds and tasks in Gadgetzan, and raise PvP rank. The two currencies have different purposes.','',
        'The PvP rank interface displays season progress, a weekly increasing cap and upcoming rewards. The cap curve runs through ranks 3, 5, 6, 7, 8, 9, 11, 12, 13 and 14. Its raw input/output pairs are included in the JSON; no calendar dates are assigned to these points.','',
        '| Rank | Alliance | Horde | Unlocks |','|---|---|---|---|']
    for r in ranks:report.append(f'| {r["rank"]} | {r["alliance"]} | {r["horde"]} | {", ".join(r["rewards"])} |')
    report+=['','Rewards are purchased in the Champion’s Hall in Stormwind or the Hall of Legends in Orgrimmar.','',
        '## Darkspear Islands','','15 players per side. Brackets: 30–39, 40–49, 50–59 and 60. Capture and hold bases, then carry the Darkspear Flag to a controlled point for Victory Points. The map objective lists 1,500 resources. Scoreboard columns cover flag captures, bases assaulted and bases defended.','',
        'Horde reputation: Darkspear Raiders (2798). Alliance reputation: Theramore Expeditionary Force (2799). Each has 22 associated item records. Friendly unlocks trinkets; Honored includes rings and neck items; Exalted includes epic gloves, shoulders and a tabard. Level 60 epics in this group have item level 65.','',
        '## Queues and additional entries','','Random Battleground links to Warsong Gulch, Arathi Basin and Darkspear Islands. A separate Random Epic Battleground entry has no linked map rows. Battle for Blackrock is already present in the SoD reference.','',
        'Battle for Gilneas, Hyjal Crater and Mak’gora Arena have additional queue records. Both arena entries link to map 2995. They are shown as additional client entries, not announced modes. No rated-arena feature is inferred from the RatedPlayers field.','',
        '## Armor and purchases','','26 new PvP set IDs plus 34 changed Classic PvP sets cover all nine classes. The viewer provides class/faction filters and every set bonus. '+f'There are also {len(honor_costs)} Honor-based extended-cost rows; the JSON retains these without assigning them to vendor items.','',
        '## Sources','','[PvP table audit](pvp-audit.json) · [All PvP findings](pvp-data.json). Bonus spells and item metadata use the existing client extraction. The new PvP rank Lua/XML and API documentation were also read directly from the client archives.']
    for folder in ['docs','dist']:
        (ROOT/folder/'pvp-data.json').write_text(json.dumps(pvp,ensure_ascii=False,indent=2),encoding='utf-8')
        (ROOT/folder/'pvp-audit.json').write_text(json.dumps(audit,ensure_ascii=False,indent=2),encoding='utf-8')
        (ROOT/folder/'pvp-findings.md').write_text('\n'.join(report)+'\n',encoding='utf-8')
    return pvp

if __name__=='__main__':
    data=build();print(json.dumps(data['summary']))
