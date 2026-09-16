"""Compare CDN-extracted, DBCD-decoded client tables with the cached CSV exports."""
import csv
import json
import math
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent / 'evidence' / '2026-09-16'
AUDIT = BASE / 'audit'

def flatten(row):
    result = {}
    for key, value in row.items():
        if key == 'Index':
            key = '_Index'  # Wago's CSV escaping of this column name.
        if isinstance(value, list):
            result.update({f'{key}_{i}': item for i, item in enumerate(value)})
        else:
            result[key] = value
    return result

def equal(actual, expected):
    if isinstance(actual, (int, float)):
        return math.isclose(actual, float(expected), rel_tol=0.000001, abs_tol=0.000001)
    return str(actual).replace('\r\n', '\n') == expected.replace('\r\n', '\n')

results = []
extracted = json.loads((AUDIT / 'client-extraction.json').read_text())
assert len(extracted) >= 42 and all('error' not in r for r in extracted)
for source in extracted:
    name = source['table']
    if not (BASE / 'db2' / f'{name}.csv').exists():
        continue
    client = [flatten(r) for r in json.loads((AUDIT / 'client-db2' / f'{name}.json').read_text())]
    with (BASE / 'db2' / f'{name}.csv').open(encoding='utf-8-sig', newline='') as f:
        exported = list(csv.DictReader(f))
    if name in ('SkillLineAbility', 'TraitCurrency'):
        # The original Wago export used anonymous columns for this new layout.
        # DBCD resolves layout 224F7EA0 using the now-named WoWDBDefs schema.
        old_columns = list(exported[0])
        new_columns = list(client[0])
        assert len(old_columns) == len(new_columns) == (20 if name == 'SkillLineAbility' else 8)
        mapping = dict(zip(old_columns, new_columns))
        if name == 'SkillLineAbility':
            assert mapping['Field_1_60_1_69876_004'] == 'Spell'
            assert mapping['Field_1_60_1_69876_006'] == 'ClassMask'
        else:
            assert mapping['Field_1_60_1_69876_000'] == 'ID'
        exported = [{mapping[k]: v for k, v in row.items()} for row in exported]
    raw = {int(row['ID']): row for row in client}
    cached = {int(row['ID']): row for row in exported}
    missing = sorted(cached.keys() - raw.keys())
    extra = sorted(raw.keys() - cached.keys())
    differences = []
    fields = 0
    for id in raw.keys() & cached.keys():
        assert raw[id].keys() == cached[id].keys(), (name, id, raw[id].keys(), cached[id].keys())
        for key in raw[id]:
            fields += 1
            if not equal(raw[id][key], cached[id][key]):
                differences.append({'id': id, 'field': key, 'client': raw[id][key], 'export': cached[id][key]})
    results.append({**source, 'comparedFields': fields, 'missingIDs': missing, 'extraIDs': extra, 'differences': differences})
report = {'build': '1.60.1.69876', 'tables': len(results), 'rows': sum(r['rows'] for r in results),
          'comparedFields': sum(r['comparedFields'] for r in results),
          'passed': all(not r['missingIDs'] and not r['extraIDs'] and not r['differences'] for r in results),
          'results': results}
(AUDIT / 'client-comparison.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
print(json.dumps({k: v for k, v in report.items() if k != 'results'}))
for r in results:
    if r['missingIDs'] or r['extraIDs'] or r['differences']:
        print(r['table'], 'missing', len(r['missingIDs']), 'extra', len(r['extraIDs']), 'differences', len(r['differences']), r['differences'][:3])
assert report['passed'], 'Client data do not match the cached export; inspect audit/client-comparison.json'
