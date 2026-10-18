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
    monday=sunday+timedelta(days=1)
    friday=saturday-timedelta(days=1)
    try:
        import jpholiday
        holiday_days=[d for d in (friday,monday) if jpholiday.is_holiday(d)]
    except ImportError:
        holiday_days=[]
    days=[saturday,sunday,*holiday_days]
    first,last=min(days),max(days)
    src=json.loads((ROOT/'events.json').read_text(encoding='utf-8'))
    featured=[]
    seen=set()
    for event in src.get('events',[]):
        if not isinstance(event,dict) or not event.get('url','').startswith('https://'):continue
        start=event.get('start','');end=event.get('end') or start
        if end<today.isoformat():continue
        if not (start<=last.isoformat() and end>=first.isoformat()):continue
        key=(event.get('url'),event.get('start'),event.get('title'))
        if key in seen:continue
        seen.add(key)
        featured.append({k:event.get(k) for k in ('id','title','start','end','city','location','description','url','provider','free','costKnown','priceType','priceNote','reviewStatus','translations','time','age','booking') if k in event})
    for e in featured:
        try:
            duration=(datetime.fromisoformat(e['end']).date()-datetime.fromisoformat(e['start']).date()).days
        except (ValueError,KeyError,TypeError):duration=0
        e['section']='ongoing' if duration>=7 and e['start']<saturday.isoformat() else 'special'
    cities={'Kashihara':0,'Asuka':1,'Sakurai':2,'Tenri':3,'Tawaramoto':4,'Yamatotakada':5,'Nara':6}
    featured.sort(key=lambda e:(0 if e['section']=='special' else 1,cities.get(e.get('city'),30),e.get('start',''),e.get('title','')))
    out={'generatedAt':datetime.now(timezone.utc).isoformat(),'weekendStart':saturday.isoformat(),'weekendEnd':sunday.isoformat(),'mondayAfter':monday.isoformat(),'holidayDates':[d.isoformat() for d in holiday_days],'events':featured,'sourceUpdatedAt':src.get('updatedAt'),'sourceErrors':src.get('errors',[]),'note':'Friday/Monday included only when recognized as Japanese public holidays; event schedules and special opening days require confirmation.'}
    (ROOT/'weekly.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(f'Weekly guide: {len(featured)} dated events for {saturday} through {last}.')
if __name__=='__main__':build()
