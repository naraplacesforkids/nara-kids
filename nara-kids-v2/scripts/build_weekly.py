"""Generate a source-linked family weekend guide from imported events, without guessing details."""
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo
ROOT=Path(__file__).resolve().parents[1]
JST=ZoneInfo('Asia/Tokyo')

def build(now=None):
    today=(now or datetime.now(JST)).date()
    saturday=today+timedelta(days=(5-today.weekday())%7)
    sunday=saturday+timedelta(days=1)
    # Include Monday listings as potential long-weekend activities; never label it a public holiday without verification.
    monday=sunday+timedelta(days=1)
    src=json.loads((ROOT/'events.json').read_text(encoding='utf-8'))
    featured=[]
    seen=set()
    for event in src.get('events',[]):
        if not isinstance(event,dict) or not event.get('url','').startswith('https://'):continue
        start=event.get('start','');end=event.get('end') or start
        if end<today.isoformat():continue
        if not (start<=monday.isoformat() and end>=saturday.isoformat()):continue
        key=(event.get('url'),event.get('start'),event.get('title'))
        if key in seen:continue
        seen.add(key)
        featured.append({k:event.get(k) for k in ('id','title','start','end','city','location','description','url','provider','free','costKnown','priceType','priceNote','reviewStatus','translations','time','age','booking') if k in event})
    cities={'Kashihara':0,'Asuka':1,'Sakurai':2,'Tenri':3,'Tawaramoto':4,'Yamatotakada':5,'Nara':6}
    featured.sort(key=lambda e:(cities.get(e.get('city'),30),e.get('start',''),e.get('title','')))
    out={'generatedAt':datetime.now(timezone.utc).isoformat(),'weekendStart':saturday.isoformat(),'weekendEnd':sunday.isoformat(),'mondayAfter':monday.isoformat(),'events':featured,'sourceUpdatedAt':src.get('updatedAt'),'sourceErrors':src.get('errors',[]),'note':'Monday listings are included for convenience; Monday is not necessarily a public holiday. All details require source confirmation.'}
    (ROOT/'weekly.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(f'Weekly guide: {len(featured)} dated events for {saturday} through {monday}.')
if __name__=='__main__':build()
