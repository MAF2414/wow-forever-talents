"""Resolve client appearances and export a bounded selection as static glTF previews.

Inputs are the independently decoded 1.60.1.69876 DB2 tables and CASC assets.
Run inventory, fetch model-asset-ids.json via ClientAudit --assets, dependencies,
fetch again, then build. Raw assets stay in ignored evidence storage.
M2/SKIN layout reference: wow.export (MIT), license in docs/vendor/wow-export-LICENSE.
"""
import collections
import csv
import hashlib
import io
import json
from pathlib import Path
import shutil
import struct
import sys
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / 'evidence/2026-09-16/audit'
RAW = AUDIT / 'model-assets'
OUT = ROOT / 'docs/models'

def read(path):
    return json.loads(path.read_text(encoding='utf-8'))

def write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')

def inventory():
    tables = {p.stem: read(p) for p in (AUDIT/'model-db2').glob('*.json')}
    indexed = {n: {r.get('ID', r.get('FileDataID')): r for r in rows} for n, rows in tables.items()}
    def group(table, key):
        result = collections.defaultdict(list)
        for row in tables[table]: result[row[key]].append(row)
        return result
    mods = group('ItemModifiedAppearance', 'ItemID')
    models = group('ModelFileData', 'ModelResourcesID')
    textures = group('TextureFileData', 'MaterialResourcesID')
    textures = collections.defaultdict(list,{key:[r for r in rows if r['UsageType']==0] for key,rows in textures.items()})
    mats = group('ItemDisplayInfoModelMatRes', 'ItemDisplayInfoID')
    cloth = group('ItemDisplayInfoMaterialRes', 'ItemDisplayInfoID')
    filenames = dict((int(a), b.strip()) for a,b in (line.split(';',1) for line in (ROOT/'evidence/2026-09-16/community-listfile.csv').open()))
    assets, sets = {}, []
    def asset(fid, ext):
        if fid: assets[f'{fid}.{ext}'] = fid
    for s in read(ROOT/'docs/content-data.json')['sets']:
        if s['status'] not in ('new', 'changed-classic'): continue
        pieces = []
        for member in s['items']:
            iid = member['id']
            item = indexed['Item'].get(iid)
            if not item or not mods[iid]: continue
            mod = min(mods[iid],key=lambda r:r['ItemAppearanceModifierID'])
            app = indexed['ItemAppearance'].get(mod['ItemAppearanceID'])
            if not app: continue
            display = indexed['ItemDisplayInfo'].get(app['ItemDisplayInfoID'])
            if not display: continue
            piece = {'itemID':iid,'name':member.get('name'), 'slot':item['InventoryType'], 'appearanceID':app['ID'], 'displayID':display['ID'], 'iconFileDataID':app['DefaultIconFileDataID'], 'parts':[], 'cloth':[]}
            for mi, res in enumerate(display['ModelResourcesID']):
                if not res: continue
                choices = []
                for r in models[res]:
                    fid = r['FileDataID']; c = indexed['ComponentModelFileData'].get(fid,{})
                    if c.get('RaceID') not in (0,1) or c.get('GenderIndex') not in (0,2): continue
                    if item['InventoryType']==3 and c.get('PositionIndex',-1) not in (-1,mi):continue
                    choices.append((0 if c.get('RaceID')==1 and c.get('GenderIndex')==0 else 1, fid))
                if not choices: continue
                fid = min(choices)[1]
                material_map = {}
                for mat in mats[display['ID']]:
                    if mat['ModelIndex']==mi and textures[mat['MaterialResourcesID']]:
                        material_map[str(mat['TextureType'])] = textures[mat['MaterialResourcesID']][0]['FileDataID']
                resmat = display['ModelMaterialResourcesID'][mi]
                if '2' not in material_map and resmat and textures[resmat]:material_map['2'] = textures[resmat][0]['FileDataID']
                piece['parts'].append({'fileDataID':fid,'path':filenames.get(fid,''),'textures':material_map,'side':('Left shoulder' if mi==0 else 'Right shoulder') if item['InventoryType']==3 else 'Head' if item['InventoryType']==1 else 'Model','geosets':display['AttachmentGeosetGroup']})
                asset(fid,'m2')
                for tf in material_map.values():asset(tf,'blp')
            for mat in cloth[display['ID']]:
                candidates = textures[mat['MaterialResourcesID']]
                # UsageType 0 supplies the base color texture; it is not a gender flag.
                for r in candidates:
                    if r['UsageType']==0:
                        piece['cloth'].append({'section':mat['ComponentSection'],'fileDataID':r['FileDataID'],'usageType':r['UsageType']})
                        asset(r['FileDataID'],'blp')
            if piece['parts'] or piece['cloth']:
                pieces.append(piece)
                asset(piece['iconFileDataID'],'blp')
        if pieces:
            sets.append({k:s[k] for k in ('id','name','class','role','category','status')} | {'pieces':pieces})
    old_models = {int(r['ID']) for r in csv.DictReader((ROOT/'evidence/2026-09-16/models-sod/CreatureModelData.csv').open(encoding='utf-8-sig'))}
    old_displays = {int(r['ID']) for r in csv.DictReader((ROOT/'evidence/2026-09-16/models-sod/CreatureDisplayInfo.csv').open(encoding='utf-8-sig'))}
    displays = group('CreatureDisplayInfo','ModelID')
    creatures=[]
    # New geometry with a concrete non-character display and its assigned textures.
    for model in tables['CreatureModelData']:
        fid=model['FileDataID']
        if model['ID'] in old_models or fid < 7000000:continue
        variants=[d for d in displays[model['ID']] if not d['ExtendedDisplayInfoID'] and any(d['TextureVariationFileDataID'])]
        if not variants:continue
        variant=variants[0]
        tex={str(11+i):v for i,v in enumerate(variant['TextureVariationFileDataID'][:3]) if v}
        creatures.append({'id':model['ID'],'displayID':variant['ID'],'fileDataID':fid,'path':filenames.get(fid,''),'textures':tex,'geosets':[], 'variantCount':len(variants),'name':f'Creature model {model["ID"]}'})
        asset(fid,'m2')
        for tf in tex.values():asset(tf,'blp')
    result={'build':'1.60.1.69876','sets':sets,'creatures':creatures,'bossAssignments':0,'tables':read(AUDIT/'model-extraction.json')}
    write(AUDIT/'model-inventory.json',result)
    write(AUDIT/'model-asset-ids.json',assets)
    print(f'{len(sets)} sets, {sum(len(s["pieces"]) for s in sets)} pieces, {len(creatures)} creature models; {len(assets)} assets')

def m2(fid):
    raw=(RAW/f'{fid}.m2').read_bytes();chunks={};o=0
    if raw[:4]==b'MD20':chunks[b'MD21']=raw
    else:
        while o+8<=len(raw):
            tag,n=struct.unpack_from('<4sI',raw,o);o+=8
            assert o+n<=len(raw),f'Invalid chunk {fid}'
            chunks[tag]=raw[o:o+n];o+=n
    d=chunks[b'MD21']; assert d[:4]==b'MD20'
    def arr(offset, fmt, stride=None):
        count,start=struct.unpack_from('<II',d,offset);size=stride or struct.calcsize('<'+fmt)
        return [struct.unpack_from('<'+fmt,d,start+i*size) for i in range(count)]
    n,o=struct.unpack_from('<II',d,8)
    name=d[o:o+n].rstrip(b'\0').decode('utf-8','replace')
    vertices=arr(60,'3f4B4B3f2f2f',48)
    texids=list(struct.unpack('<'+'I'*(len(chunks.get(b'TXID',b''))//4),chunks.get(b'TXID',b'')))
    tex=arr(80,'4I'); textures=[{'type':v[0],'flags':v[1],'id':texids[i] if i<len(texids) else 0} for i,v in enumerate(tex)]
    skins=list(struct.unpack('<'+'I'*(len(chunks[b'SFID'])//4),chunks[b'SFID']))
    return {'name':name,'vertices':vertices,'textures':textures,'skinID':skins[0],'materials':arr(112,'2H'),'combos':[v[0] for v in arr(128,'H')]}

def dependencies():
    inv=read(AUDIT/'model-inventory.json');assets={}
    entries=[part for s in inv['sets'] for p in s['pieces'] for part in p['parts']]+inv['creatures']
    errors=[]
    for entry in entries:
        try:
            model=m2(entry['fileDataID'])
            assets[f'{model["skinID"]}.skin']=model['skinID']
            for tex in model['textures']:
                if tex['type']==0 and tex['id']:assets[f'{tex["id"]}.blp']=tex['id']
            entry['internalName']=model['name']
            if entry in inv['creatures']:entry['name']=model['name'].replace('_',' ') or f'Creature model {entry["id"]}'
        except Exception as exc:errors.append({'fileDataID':entry['fileDataID'],'error':str(exc)})
    write(AUDIT/'model-inventory.json',inv);write(AUDIT/'model-asset-ids.json',assets)
    print('Dependencies',len(assets),'errors',errors)

def image_bytes(fid, maximum=1024):
    im=Image.open(RAW/f'{fid}.blp').convert('RGBA')
    im.thumbnail((maximum,maximum))
    b=io.BytesIO();im.save(b,format='PNG',optimize=True);return b.getvalue()

def export_glb(entry):
    model=m2(entry['fileDataID']);skin=(RAW/f'{model["skinID"]}.skin').read_bytes();assert skin[:4]==b'SKIN'
    def arr(offset,fmt,size=None):
        n,o=struct.unpack_from('<II',skin,offset);step=size or struct.calcsize('<'+fmt)
        return [struct.unpack_from('<'+fmt,skin,o+i*step) for i in range(n)]
    indices=[v[0] for v in arr(4,'H')];triangles=[v[0] for v in arr(12,'H')]
    submeshes=arr(28,'10H7f',48);batches=arr(36,'Bb11H',24)
    g={'asset':{'version':'2.0','generator':'WoW Forever static client preview'},'scene':0,'scenes':[{'nodes':[0]}],'nodes':[{'mesh':0}],'meshes':[{'primitives':[]}],'buffers':[],'bufferViews':[],'accessors':[],'materials':[],'images':[],'textures':[],'samplers':[{'magFilter':9729,'minFilter':9987,'wrapS':10497,'wrapT':10497}],'extensionsUsed':['KHR_materials_unlit']}
    buf=bytearray()
    def view(data):
        while len(buf)%4:buf.append(0)
        i=len(g['bufferViews']);g['bufferViews'].append({'buffer':0,'byteOffset':len(buf),'byteLength':len(data)});buf.extend(data);return i
    def accessor(values,fmt,typ,component):
        flat=[n for row in values for n in row];bv=view(struct.pack('<'+fmt*len(flat),*flat));a={'bufferView':bv,'componentType':component,'count':len(values),'type':typ}
        if typ=='VEC3':a.update(min=[min(r[i] for r in values) for i in range(3)],max=[max(r[i] for r in values) for i in range(3)])
        i=len(g['accessors']);g['accessors'].append(a);return i
    vertices=model['vertices'];pos=accessor([(v[0],v[2],-v[1]) for v in vertices],'f','VEC3',5126)
    normals=accessor([(v[11],v[13],-v[12]) for v in vertices],'f','VEC3',5126)
    uv=accessor([(v[14],v[15]) for v in vertices],'f','VEC2',5126)
    used=[];materials={};skipped=[]
    for si,sm in enumerate(submeshes):
        # Equipment files normally have one mesh. Retain default geosets where alternatives exist.
        geo=sm[0]
        if geo!=0 and geo%100!=1:
            selected={(i+1)*100+x for i,x in enumerate(entry.get('geosets',[])) if x}
            if geo not in selected:continue
        candidates=[b for b in batches if b[3]==si]
        if not candidates:continue
        # Base surface only. Animated particles and additive overlay passes are not baked.
        b=min(candidates,key=lambda x:x[7])
        flags,blend=model['materials'][b[6]]
        ti=model['combos'][b[9]];tex=model['textures'][ti]
        fid=tex['id'] if tex['type']==0 else entry['textures'].get(str(tex['type']),0)
        if not fid or not (RAW/f'{fid}.blp').exists():
            skipped.append({'geoset':geo,'textureType':tex['type'],'textureID':fid});continue
        key=(fid,blend,flags)
        if key not in materials:
            png=image_bytes(fid);im=len(g['images']);g['images'].append({'bufferView':view(png),'mimeType':'image/png'});g['textures'].append({'source':im,'sampler':0})
            material={'name':str(fid),'pbrMetallicRoughness':{'baseColorTexture':{'index':im},'metallicFactor':0,'roughnessFactor':1},'doubleSided':bool(flags&4),'extensions':{'KHR_materials_unlit':{}}}
            if blend==1:material.update(alphaMode='MASK',alphaCutoff=0.5)
            elif blend>1:material.update(alphaMode='BLEND')
            materials[key]=len(g['materials']);g['materials'].append(material);used.append(fid)
        start=sm[4]+(sm[1]<<16);count=sm[5]
        tri=[(indices[x],) for x in triangles[start:start+count]]
        assert count%3==0 and len(tri)==count and all(x[0]<len(vertices) for x in tri)
        ia=accessor(tri,'H','SCALAR',5123)
        g['meshes'][0]['primitives'].append({'attributes':{'POSITION':pos,'NORMAL':normals,'TEXCOORD_0':uv},'indices':ia,'material':materials[key]})
    assert g['meshes'][0]['primitives'],f'No textured geometry: {entry["fileDataID"]} {skipped}'
    g['buffers']=[{'byteLength':len(buf)}]
    while len(buf)%4:buf.append(0)
    js=json.dumps(g,separators=(',',':')).encode();js+=b' '*((-len(js))%4)
    glb=struct.pack('<4sII',b'glTF',2,12+8+len(js)+8+len(buf))+struct.pack('<I4s',len(js),b'JSON')+js+struct.pack('<I4s',len(buf),b'BIN\0')+buf
    key=hashlib.sha256(glb).hexdigest()[:20];filename=f'{key}.glb';(OUT/filename).write_bytes(glb)
    return {'url':f'models/{filename}','bytes':len(glb),'vertices':len(vertices),'triangles':sum(g['accessors'][p['indices']]['count']//3 for p in g['meshes'][0]['primitives']),'skinFileDataID':model['skinID'],'textureFileDataIDs':used,'skippedSurfaces':skipped,'internalName':model['name']}

def build():
    OUT.mkdir(parents=True,exist_ok=True);inv=read(AUDIT/'model-inventory.json');errors=[];cache={}
    for creature in inv['creatures']:
        creature['name']=creature.get('name') or f'Creature model {creature["id"]}'
    entries=[p for s in inv['sets'] for i in s['pieces'] for p in i['parts']]+inv['creatures']
    for entry in entries:
        key=json.dumps({k:entry[k] for k in ('fileDataID','textures','geosets')},sort_keys=True)
        try:
            if key not in cache:cache[key]=export_glb(entry)
            entry.update(cache[key])
        except Exception as exc:
            message='Required client asset unavailable' if isinstance(exc,FileNotFoundError) else str(exc)
            entry['error']=message;errors.append({'fileDataID':entry['fileDataID'],'error':message})
    for s in inv['sets']:
        for p in s['pieces']:
            for fid in set([p['iconFileDataID']]+[c['fileDataID'] for c in p['cloth']]):
                if not fid:continue
                target=OUT/f'{fid}.png'
                try:
                    if not target.exists():target.write_bytes(image_bytes(fid,512))
                except Exception as exc:errors.append({'fileDataID':fid,'error':str(exc)})
            p['icon']=f'models/{p["iconFileDataID"]}.png' if (OUT/f'{p["iconFileDataID"]}.png').exists() else None
            for c in p['cloth']:c['url']=f'models/{c["fileDataID"]}.png' if (OUT/f'{c["fileDataID"]}.png').exists() else None
    inv['summary']={'sets':len(inv['sets']),'setsWith3D':sum(any(p.get('url') for i in s['pieces'] for p in i['parts']) for s in inv['sets']),'tierSets':sum(s['category']=='tier1' for s in inv['sets']),'uniquePreviews':len(cache),'creaturePreviews':sum('url' in c for c in inv['creatures']),'bossAssignments':0}
    inv.pop('tables',None)
    write(ROOT/'docs/models-data.json',inv)
    write(ROOT/'docs/models-audit.json',{'build':inv['build'],'tables':read(AUDIT/'model-extraction.json'),'assets':read(AUDIT/'model-assets-extraction.json'),'errors':errors,'summary':inv['summary']})
    shutil.copytree(OUT,ROOT/'dist/models',dirs_exist_ok=True)
    for name in ['models-data.json','models-audit.json']:shutil.copy2(ROOT/'docs'/name,ROOT/'dist'/name)
    for name in ['models.html','models.css','models.js']:
        for folder in ['docs','dist']:shutil.copy2(ROOT/'site'/name,ROOT/folder/name)
    shutil.copytree(ROOT/'docs/vendor',ROOT/'dist/vendor',dirs_exist_ok=True)
    report=f'''# WoW Forever model gallery

Build **{inv['build']}**, extracted from the public client CDN using the pinned build configuration in the existing audit.

[Open the interactive gallery](https://maf2414.github.io/wow-forever-talents/models.html).

- **{len(inv['sets'])} sets** have appearance data, including all **18 new Tier 1 sets**, **60 PvP sets** and **47 other sets**.
- **{inv['summary']['setsWith3D']} sets** have standalone geometry. The other nine provide body texture sections.
- All **108 Tier 1 member IDs** resolve through ItemModifiedAppearance and ItemAppearance despite their missing ItemSparse metadata. All 18 tier sets provide a Human male helm and both shoulder models.
- **{inv['summary']['uniquePreviews']} distinct textured GLB previews**, including **{inv['summary']['creaturePreviews']} creature appearances**. Shared geometry/textures are deduplicated.
- The armor is shown as individual equipment pieces plus body texture sections. Full dressed characters, animation, particle effects and extra additive shader passes are not assembled.

## Bosses and creatures

DungeonEncounter has no model link in this build. JournalEncounterCreature and the other inspected journal tables are empty, and none of the 26 new encounter names match the small Creature.db2 cache. No boss name has been assigned to an unrelated appearance.

The creature selection contains model IDs absent from the SoD 1.15.9.69722 reference table and geometry FileDataIDs above 7,000,000, with a non-character CreatureDisplayInfo row supplying replacement textures. This is a bounded selection, not a census of every new creature or boss. Each preview uses its displayed DisplayID; other client variants may exist. Internal names are stripped in these files, so entries retain their client model IDs. Eight further selected records require unavailable assets and are omitted from the visible gallery.

## Data and reproduction

Armor: ItemSet → Item → ItemModifiedAppearance (default modifier) → ItemAppearance → ItemDisplayInfo → ModelFileData / ComponentModelFileData. Textures use ItemDisplayInfoModelMatRes, ItemDisplayInfoMaterialRes and TextureFileData. Nonzero replacement texture types come from the selected display; fixed textures come from the M2 TXID chunk. Geometry uses the first SFID skin, its vertex lookup, triangle indices and base material batches.

CreatureModelData + CreatureDisplayInfo supply creature geometry and skins. All 13 appearance tables were independently decoded with DBCD from CASC. [Table and asset hashes](models-audit.json) and [resolved appearance links](models-data.json) are published. The source assets remain outside the repository; browser previews contain converted geometry and textures only.

Run `python scripts/build_models.py inventory`, extract the resulting `model-asset-ids.json` with `ClientAudit --assets`, then run `dependencies`, extract again and run `build`. The inventory consumes the existing content dataset and decoded appearance tables. `node scripts/verify_models.cjs` validates every GLB with Khronos glTF Validator 2.0.0-dev.3.10 and checks tier coverage, texture references and item/display links.

M2/SKIN structure reference: [wow.export](https://github.com/Kruithne/wow.export/tree/c2fd7bde36a712be78a5da896c995b84fbfa2545), MIT license retained in `vendor/wow-export-LICENSE`. Viewer: Three.js 0.180.0, self-hosted with its MIT license. Game models and textures belong to Blizzard Entertainment.
'''
    for folder in ['docs','dist']:(ROOT/folder/'models-findings.md').write_text(report,encoding='utf-8')
    print(inv['summary']);print('Errors:',errors)

if __name__=='__main__':
    {'inventory':inventory,'dependencies':dependencies,'build':build}[sys.argv[1]]()
