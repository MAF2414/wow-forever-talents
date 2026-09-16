"""Audit and publish set, map and encounter findings from the preserved client."""
from __future__ import annotations
import collections, csv, hashlib, json, math, re
from pathlib import Path
import build_talents as talent
from build_comparison import Context
import build_pvp

ROOT = Path(__file__).resolve().parent.parent
BASE = ROOT / 'evidence/2026-09-16'
AUDIT = BASE / 'audit'
BUILD = '1.60.1.69876'
DATE = '2026-09-17'
OFFICIAL = 'https://worldofwarcraft.blizzard.com/en-us/news/24303862/world-of-warcraft-forever-whats-next-panel-recap'
TIER_BASE = {'Mage':'Arcanist Regalia','Rogue':'Nightslayer Armor','Warlock':'Felheart Raiment',
             'Hunter':'Giantstalker Armor','Warrior':'Battlegear of Might','Priest':'Vestments of Prophecy',
             'Paladin':'Lawbringer Armor','Shaman':'The Earthfury','Druid':'Cenarion Raiment'}

def csv_rows(version, table):
    with (BASE / f'content-{version}' / f'{table}.csv').open(encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(f))

def client(table):
    return json.loads((AUDIT / 'content-db2' / f'{table}.json').read_text())

def indexed(rows):
    return {int(r['ID']): r for r in rows}

def flat(row):
    out = {}
    for key, value in row.items():
        key = '_Index' if key == 'Index' else key
        if isinstance(value, list):
            out.update({f'{key}_{i}': v for i, v in enumerate(value)})
        else:
            out[key] = value
    return out

def verify():
    results = []
    extracted = json.loads((AUDIT / 'content-extraction.json').read_text())
    assert len(extracted) == 15 and not any('error' in r for r in extracted)
    for source in extracted:
        name = source['table']
        actual = indexed([flat(r) for r in client(name)])
        path = BASE / 'content-forever' / f'{name}.csv'
        if not path.exists():
            assert not actual, f'Nonempty client table has no independent export: {name}'
            results.append({**source, 'comparedFields': 0, 'status':'Empty in independently decoded client'})
            continue
        exported = csv_rows('forever', name)
        mapping = {}
        if any(k.startswith('Field_') for k in exported[0]):
            assert name in ('Map', 'ItemSparse', 'AreaTable')
            assert len(exported[0]) == len(next(iter(actual.values())))
            # The serialized column order is the DB2 layout order, independently named by DBCD.
            mapping = dict(zip(exported[0], next(iter(actual.values()))))
            assert mapping['ID'] == 'ID'
            if name == 'Map':
                assert mapping['Field_1_60_1_69876_001_lang'] == 'MapName_lang'
                assert mapping['Field_1_60_1_69876_008'] == 'InstanceType'
            elif name == 'ItemSparse':
                assert mapping['Field_1_60_1_69876_004_lang'] == 'Display_lang'
            else:
                assert mapping['Field_1_60_1_69876_001_lang'] == 'AreaName_lang'
                assert mapping['Field_1_60_1_69876_002'] == 'ContinentID'
            exported = [{mapping[k]: v for k,v in r.items()} for r in exported]
        expected = indexed(exported)
        assert actual.keys() == expected.keys(), name
        fields = 0
        for rid, r in actual.items():
            assert r.keys() == expected[rid].keys(), (name, rid)
            for k,v in r.items():
                e = expected[rid][k]
                equal = math.isclose(v,float(e),rel_tol=1e-6,abs_tol=1e-6) if isinstance(v,(float,int)) else str(v).replace('\r\n','\n') == e.replace('\r\n','\n')
                assert equal, (name,rid,k,v,e)
                fields += 1
        schema = ROOT / 'sources/ClientAudit/DBDCache' / f'{name}.dbd'
        results.append({**source, 'comparedFields':fields, 'status':'Matched CSV export',
                        'columnMapping':mapping, 'schemaSHA256':hashlib.sha256(schema.read_bytes()).hexdigest()})
    exports=[]
    for version,build in [('forever',BUILD),('classic','1.14.4.51395'),('sod','1.15.9.69722')]:
        for path in sorted((BASE/f'content-{version}').glob('*.csv')):
            exports.append({'version':version,'build':build,'table':path.stem,
                'url':f'https://wago.tools/db2/{path.stem}/csv?build={build}',
                'sha256':hashlib.sha256(path.read_bytes()).hexdigest()})
    return {'build':BUILD, 'date':DATE, 'tables':len(results), 'rows':sum(r['rows'] for r in results),
            'comparedFields':sum(r['comparedFields'] for r in results), 'passed':True, 'results':results,
            'scope':'Independent extraction covers Forever. Classic and SoD comparisons use CSV exports.',
            'buildConfig':'e7fab7248766e9e7daddb3b6083c9c3c',
            'exports':exports}

def item_ids(row):
    return [int(i) for i in row['ItemID'] if i] if isinstance(row.get('ItemID'),list) else [int(row[f'ItemID_{i}']) for i in range(17) if int(row.get(f'ItemID_{i}',0))]

def bonuses(rows, ctx):
    ctx.activate()
    result = collections.defaultdict(list)
    for row in rows:
        sid = int(row['SpellID'])
        rec = ctx.record(sid)
        desc = rec['description']
        # Proc cooldown substitution happens after the shared resolver's math pass.
        def constant(m):
            try: return talent.fmt(talent.arithmetic(m[1]))
            except (ValueError,TypeError,SyntaxError,ZeroDivisionError): return m[0]
        desc = re.sub(r'\$\{([^{}]*)\}', constant, desc)
        result[int(row['ItemSetID'])].append({'threshold':int(row['Threshold']), 'spellID':sid,
            'name':rec['name'], 'description':desc, 'rawDescription':rec['rawDescription'],
            'unresolved':'$' in desc, 'effects':rec['effects'], 'available':sid in ctx.spells})
    for v in result.values():v.sort(key=lambda x:(x['threshold'],x['spellID']))
    return result

def main():
    audit = verify()
    fs,cs,ss = client('ItemSet'),csv_rows('classic','ItemSet'),csv_rows('sod','ItemSet')
    csets,ssets = indexed(cs),indexed(ss)
    fb = bonuses(client('ItemSetSpell'), Context('db2'))
    cb = bonuses(csv_rows('classic','ItemSetSpell'), Context('era-baseline',True))
    fi,ci = indexed(client('ItemSparse')),indexed(csv_rows('classic','ItemSparse'))
    def item(i):
        r = fi.get(i)
        return {'id':i, 'name':r['Display_lang'] if r else None, 'available':bool(r),
                'classicName':ci.get(i,{}).get('Display_lang'),
                **({k:r[k] for k in ['ItemLevel','RequiredLevel','OverallQualityID','AllowableClass','InventoryType']} if r else {})}
    def signature(bs):
        return [(b['threshold'],b['spellID'],re.sub(r'\s+',' ',b['description']).strip()) for b in bs]
    sets=[]
    for r in fs:
        sid=r['ID']; old=csets.get(sid); notes=[]
        changed=bool(old and (r['Name_lang']!=old['Name_lang'] or item_ids(r)!=item_ids(old) or signature(fb[sid])!=signature(cb[sid])))
        status='changed-classic' if changed else 'classic' if old else 'inherited' if sid in ssets else 'new'
        tier_names=[b['name'] for b in fb[sid] if '1.60.0 - Item - Tier 1 - ' in b['name']]
        role=re.search(r'Tier 1 - (.*?) \dP Bonus',tier_names[0])[1] if tier_names else ''
        cls=role.split(' - ')[0] if role else ''
        category='tier1' if tier_names else 'pvp' if re.match(r"(?:Champion|Warlord|Field Marshal|Lieutenant Commander)'s ",r['Name_lang']) else 'other'
        if sid==1969: notes.append('No set-bonus links and no member-item metadata in this client snapshot; incomplete entry.')
        if sid==2106: notes.append('The 4-piece internal spell name says Undead, but its description says Demons. The displayed effect uses the client description; this discrepancy is unresolved.')
        if role.startswith('Druid - Guardian'):notes.append('Guardian is the internal set-bonus label for bear tanking; it does not establish a fourth Druid talent tree.')
        if status=='inherited':notes.append('This set ID already exists in the SoD reference; presence here does not establish a new Forever reward.')
        base=next((x for x in cs if x['Name_lang']==TIER_BASE.get(cls)),None)
        sets.append({'id':sid,'name':r['Name_lang'],'status':status,'category':category,'class':cls,'role':role,
            'items':[item(i) for i in item_ids(r)],'bonuses':fb[sid],'notes':notes,
            'classic':{'id':sid,'name':old['Name_lang'],'itemIDs':item_ids(old),'bonuses':cb[sid]} if old else None,
            'classicTier':{'id':int(base['ID']),'name':base['Name_lang'],'itemIDs':item_ids(base),'bonuses':cb[int(base['ID'])]} if base else None})
    fm,cm,sm=client('Map'),indexed(csv_rows('classic','Map')),indexed(csv_rows('sod','Map'))
    fe,ce,se=client('DungeonEncounter'),indexed(csv_rows('classic','DungeonEncounter')),indexed(csv_rows('sod','DungeonEncounter'))
    names={r['Name_lang'].casefold() for r in ce.values()}|{r['Name_lang'].casefold() for r in se.values()}
    encounters=[]
    for r in fe:
        if r['ID'] not in ce and r['ID'] not in se:
            encounters.append({'id':r['ID'],'name':r['Name_lang'],'mapID':r['MapID'],'order':r['OrderIndex'],
                'status':'existing-name' if r['Name_lang'].casefold() in names else 'new-name'})
    types={0:'World',1:'Dungeon-type map',2:'Raid',3:'Battleground',4:'Arena-type map'}
    maps=[]
    for r in fm:
        if r['ID'] in cm or r['ID'] in sm:continue
        rs=sorted([e for e in encounters if e['mapID']==r['ID']],key=lambda x:(x['order'],x['id']))
        md=[x for x in client('MapDifficulty') if x['MapID']==r['ID']]
        notes=[]
        if r['ID']==2995:notes.append('InstanceType=4 (arena), not a raid map. This record does not verify the announced Hyjal Summit raid.')
        if r['ID'] in (3002,3109):notes.append('Dungeon-type map record; no official dungeon announcement was established for this name. It may be a quest space, prototype or other instance.')
        if r['ID'] in (2996,3005,3104,3021):notes.append('Unannounced or development record; this is not evidence of a scheduled release.')
        maps.append({'id':r['ID'],'name':r['MapName_lang'],'type':types.get(r['InstanceType'],str(r['InstanceType'])),
            'instanceType':r['InstanceType'],'encounters':rs,'notes':notes,
            'maxPlayers':sorted({x['MaxPlayers'] for x in md if x['MaxPlayers']}), 'wdtFileDataID':r['WdtFileDataID']})
    # Preserve official announcements independently of what the inspected client tables expose.
    announcements=[
        ('Hyjal Summit','Raid','20 players',None,'Announced; no matching named raid-map or encounter records found in the inspected tables.'),
        ('Barrow Deeps','Raid','10 players',None,'Announced; no matching named raid-map or encounter records found in the inspected tables.'),
        ('Hall of Thanes','Dungeon','',3065,'Map and four encounter records found.'),
        ('Ruins of Lordaeron','Dungeon','',2999,'Map and seven encounter records found.'),
        ('Excavation site above Whelgar’s Excavation','Dungeon','',2998,'Client map is named Excavation Site: Wetlands; four encounter records found.'),
        ('City of Dalaran','Dungeon','',2959,'Map and nine encounter records found; these are record counts, not a confirmed final boss count.'),
        ('Blackmaw Hold','Dungeon','',None,'Named area exists; no matching new dungeon-map or encounter records found.'),
        ('The Drowned City','Dungeon','',None,'Announced; no exact matching map, area or encounter name found.'),
        ("Krol’dok Stronghold",'Dungeon','',None,'Named area found (17780); no matching dungeon-map or encounter records found.'),
        ('Alcaz Prison','Dungeon','',None,'Alcaz Island areas exist; no matching prison dungeon-map or encounter records found.'),
        ('The Shaper’s Terrace','Dungeon','',None,'Named area found (16985); no matching dungeon-map or encounter records found.')]
    areas=[]
    ca,sa=indexed(csv_rows('classic','AreaTable')),indexed(csv_rows('sod','AreaTable'))
    for r in client('AreaTable'):
        if r['ID'] not in ca and r['ID'] not in sa and (r['ParentAreaID']==616 or re.search(r'shaper.s terrace|krol.?dok',r['AreaName_lang'],re.I)):
            areas.append({k:r[k] for k in ['ID','AreaName_lang','ContinentID','ParentAreaID']})
    data={'build':BUILD,'date':DATE,'classicBuild':'1.14.4.51395','sodBuild':'1.15.9.69722',
        'summary':{'sets':len(sets),'newSets':sum(s['status']=='new' for s in sets),'tierSets':sum(s['category']=='tier1' for s in sets),
            'newPvpSets':sum(s['status']=='new' and s['category']=='pvp' for s in sets),
            'changedClassicSets':sum(s['status']=='changed-classic' for s in sets),'newMaps':len(maps),
            'newEncounterRecords':len(encounters),'newEncounterNames':sum(e['status']=='new-name' for e in encounters)},
        'sets':sets,'maps':maps,'encounters':encounters,'areas':areas,
        'announcements':[dict(zip(['name','type','size','mapID','evidence'],a),source=OFFICIAL) for a in announcements],
        'audit':audit,'pvp':build_pvp.build(sets)}
    assert data['summary']['newSets']==51 and data['summary']['tierSets']==18
    assert data['summary']['newEncounterNames']==26 and len(encounters)==34
    assert not [m for m in maps if m['instanceType']==2]
    for s in sets:
        if s['category']=='tier1':
            assert len(s['items'])==6 and [b['threshold'] for b in s['bonuses']]==[2,3,4,5]
            assert all(not i['available'] for i in s['items'])
            assert s['classicTier'] and all(b['available'] and not b['unresolved'] for b in s['bonuses'])
    hunter=next(s for s in sets if s['id']==2101)
    assert '1 sec' in next(b['description'] for b in hunter['bonuses'] if b['threshold']==5)
    raw=json.dumps(data,ensure_ascii=False,separators=(',',':')).replace('</','<\\/')
    template=(ROOT/'site/content.template.html').read_text(encoding='utf-8')
    html=template.replace('/*CONTENT_DATA*/null',raw).replace('/*PVP_SCRIPT*/',(ROOT/'site/pvp.js').read_text(encoding='utf-8'))
    for folder in ['docs','dist']:
        (ROOT/folder/'content.html').write_text(html,encoding='utf-8')
        (ROOT/folder/'content-data.json').write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
    for folder in ['docs','dist']:
        (ROOT/folder/'content-audit.json').write_text(json.dumps(audit,indent=2),encoding='utf-8')
    (BASE/'content-browser-script.js').write_text(html.split('<script>')[1].split('</script>')[0],encoding='utf-8')
    report=['# Sets, instances and bosses — September 17, 2026','',
        f'Client **{BUILD}**, compared with Classic **1.14.4.51395** and SoD **1.15.9.69722**.', '',
        '[Open the searchable findings](https://maf2414.github.io/wow-forever-talents/content.html).', '',
        f'Independent CDN extraction: **{audit["tables"]} tables, {audit["rows"]:,} rows, {audit["comparedFields"]:,} compared fields**. All ten nonempty tables match the CSV exports. Five journal tables are present but empty.', '',
        '## Findings', '', '51 set IDs are absent from both baselines: 18 Tier 1 class/role sets, 26 PvP-named variants and seven other sets. A new ID is not proof of a new appearance or an obtainable reward.', '',
        f'{data["summary"]["changedClassicSets"]} sets sharing a Classic ID have changed names, item membership, bonus spell links or resolved bonus text. The viewer includes the Classic bonuses. This is not a full comparison of item stats or triggered effects.', '',
        'The 18 Tier 1 sets have six member IDs each and four linked bonuses at 2, 3, 4 and 5 pieces. Their spell names explicitly say Tier 1. All 108 referenced tier-item IDs lack ItemSparse metadata in this snapshot; exact item stats, drop sources and raid assignments remain unverified.', '',
        '## Tier 1 class sets', '', '| Class / role | Set | 5-piece bonus |', '|---|---|---|']
    for s in sets:
        if s['category']=='tier1':report.append(f'| {s["role"]} | {s["name"]} | {next(b["description"] for b in s["bonuses"] if b["threshold"]==5)} |')
    report+=['','## New encounter names','','34 new encounter IDs include 26 names absent from both reference encounter tables and eight familiar Sunken Temple names under new IDs. Counts below are client records, not a confirmed final encounter lineup.','']
    for m in maps:
        if m['encounters']:report += [f'### {m["name"]} (Map {m["id"]})','',', '.join(f'{e["name"]} ({e["id"]})' for e in m['encounters']), '']
    report+=['## Raids and limits','',
        f'[Blizzard announced Hyjal Summit (20 players), Barrow Deeps (10 players) and nine dungeons]({OFFICIAL}). Those announcements are tracked separately from client findings.', '',
        'No newly added map has InstanceType=2 (raid) in this snapshot. Hyjal Crater (2995) has InstanceType=4 (arena); it must not be substituted for Hyjal Summit. No boss roster for Hyjal Summit or Barrow Deeps was established from the inspected tables.', '',
        'Half-Pint Tavern (3002) and Manor Mistmantle (3109) are dungeon-type records, but are not established as announced dungeons. The former has two encounter records; the latter has none. They may represent quest spaces or unfinished content.', '',
        'Creature.db2 is not a complete server NPC database. The inspected tables cannot verify world-boss spawns, drop tables, release readiness or hidden/encrypted/unavailable content. An absent record does not prove cancelled content.', '',
        'The Retribution set’s 4-piece internal spell name says Undead, while the description says Demons. Both are retained in the viewer. Guardian in the Druid set labels means a bear-role label in these records, not evidence of a fourth talent tree.', '',
        '## Reproduction','',
        'Source tables: ItemSet, ItemSetSpell, ItemSparse, ItemEffect, Map, MapDifficulty, DungeonEncounter, AreaTable, LFGDungeons and Creature. JournalInstance, JournalEncounter, JournalEncounterCreature, JournalEncounterItem and JournalEncounterSection were independently decoded and are empty.', '',
        '[Extraction hashes and field comparison](content-audit.json) · [All findings and source IDs](content-data.json).', '',
        'Uses the CASCLib / DBCD extraction method and source revisions documented in [the talent audit](audit.md). Map, AreaTable and ItemSparse anonymous export columns are mapped to the independently named DB2 layout in column order; mappings and schema hashes are recorded in the audit.', '',
        'With the preserved source exports and decoded client files present, run `python scripts/build_content.py`. The builder asserts source equality, baseline classification, all 18 tier-set bonus thresholds, Classic tier references and encounter counts before writing the page.']
    for folder in ['docs','dist']:
        (ROOT/folder/'content-findings.md').write_text('\n'.join(report)+'\n',encoding='utf-8')
    for name in ['audit.md','client-audit.json']:
        (ROOT/'dist'/name).write_bytes((ROOT/'docs'/name).read_bytes())
    print(json.dumps(data['summary']))
    print(json.dumps({k:v for k,v in audit.items() if k not in ('results','exports')}))

if __name__=='__main__':main()
