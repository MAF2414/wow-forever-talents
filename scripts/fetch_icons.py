"""Cache mapped public spell icons so the generated HTML works offline."""
import concurrent.futures, json, re, urllib.request
from pathlib import Path

ROOT=Path(__file__).resolve().parent.parent
BASE=ROOT/'evidence'/'2026-09-16'
OUT=BASE/'icons'
OUT.mkdir(exist_ok=True)
mapping=json.loads((BASE/'icon-map.json').read_text(encoding='utf-8'))

def fetch(pair):
    icon_id,path=pair
    out=OUT/(icon_id+'.jpg')
    if out.exists():return (icon_id,'cached')
    name=Path(path).stem.lower()
    if not re.fullmatch(r'[a-z0-9_.-]+',name):return (icon_id,'unsupported name')
    url='https://wow.zamimg.com/images/wow/icons/large/'+name+'.jpg'
    try:
        with urllib.request.urlopen(url,timeout=20) as response:
            content=response.read(500_000)
            if not content.startswith(b'\xff\xd8'):raise ValueError('Not a JPEG')
        out.write_bytes(content)
        return(icon_id,'ok')
    except Exception as e:return(icon_id,str(e))

with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
    results=list(pool.map(fetch,mapping.items()))
(BASE/'icon-downloads.json').write_text(json.dumps(results,indent=2),encoding='utf-8')
print('Icons',len(results),'available',sum(status in ('ok','cached') for _,status in results))
print('Unavailable',[(i,s) for i,s in results if s not in ('ok','cached')])
