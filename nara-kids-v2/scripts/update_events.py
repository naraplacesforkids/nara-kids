"""Import explicitly configured public iCalendar (.ics) event feeds. No invented events.
Run with: pip install -r requirements.txt && python scripts/update_events.py
"""
import json, re, os, sys, hashlib
from pathlib import Path
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
import requests
from icalendar import Calendar
from municipal_events import extract_calendar
ROOT=Path(__file__).resolve().parents[1]
JST=ZoneInfo('Asia/Tokyo')
TODAY=datetime.now(JST).date()

def as_date(value):
    if hasattr(value,'dt'): value=value.dt
    if isinstance(value,datetime): return value.astimezone(JST).date() if value.tzinfo else value.date()
    return value

def cleaned(x,maxlen=450):
    return re.sub(r'\s+',' ',str(x or '')).strip()[:maxlen]

def main():
    config=json.loads((ROOT/'sources.json').read_text(encoding='utf8'))
    output=[]; successes=[]; failures=[]
    for source in config.get('ical_feeds',[]):
        name=source.get('name','Feed');url=source.get('url','')
        if not url.startswith('https://'):
            failures.append(f'{name}: feed URL must use HTTPS');continue
        try:
            response=requests.get(url,timeout=20,headers={'User-Agent':'NaraKidsEventIndexer/1.0 (+public community directory)'})
            response.raise_for_status()
            if len(response.content)>3_000_000:raise ValueError('feed too large')
            cal=Calendar.from_ical(response.content)
            for item in cal.walk('VEVENT'):
                start=item.get('DTSTART')
                if not start:continue
                day=as_date(start)
                end_item=item.get('DTEND')
                end=as_date(end_item) if end_item else day
                if end_item and not isinstance(end_item.dt,datetime):
                    # In all-day iCalendar items, DTEND is exclusive.
                    end=end-timedelta(days=1)
                if day>TODAY+timedelta(days=120) or end<TODAY:continue
                title=cleaned(item.get('SUMMARY'),160)
                if not title:continue
                page=cleaned(item.get('URL') or source.get('official_url') or url,800)
                if not page.startswith('https://'):continue
                desc=cleaned(item.get('DESCRIPTION'))
                city=cleaned(source.get('city') or '',70)
                location=cleaned(item.get('LOCATION'),140)
                uid=cleaned(item.get('UID') or f'{title}-{day}',300)
                event={'id':hashlib.sha256((name+uid).encode()).hexdigest()[:16],
                       'title':title,'start':day.isoformat(),'end':max(day,end).isoformat(),
                       'city':city,'location':location,'description':desc,'url':page,
                       'provider':name,'free':bool(source.get('all_free',False)), 'costKnown':bool(source.get('all_free',False)), 'reviewStatus':'unverified'}
                output.append(event)
            successes.append(name)
        except Exception as exc:
            failures.append(f'{name}: {type(exc).__name__}: {exc}')
    # Discover family-relevant entries in municipality calendars. Calendar dates are
    # tentative leads, not a confirmation of booking, price, or age suitability.
    for source in config.get('municipal_calendars',[]):
        name=source['name']; url=source['url']
        try:
            response=requests.get(url,timeout=22,headers={'User-Agent':'NaraKids/2.1 (family events directory; respectful daily fetch)'})
            response.raise_for_status()
            if len(response.content)>2_000_000:raise ValueError('calendar page too large')
            found=extract_calendar(response.text, source, TODAY)
            output.extend(found)
            successes.append(name)
            print(f'{name}: {len(found)} possible family events')
        except Exception as exc:
            failures.append(f'{name}: {type(exc).__name__}: {exc}')
    # Fail closed: if configured sources all fail, retain old events instead of silently wiping them.
    prior_path=ROOT/'events.json'
    if (config.get('ical_feeds') or config.get('municipal_calendars')) and not successes:
        print('All sources failed; keeping previous published events.',file=sys.stderr)
        for error in failures:print(error,file=sys.stderr)
        sys.exit(1)
    unique={e['id']:e for e in output}
    data={'updatedAt':datetime.now(timezone.utc).isoformat(), 'sources':successes,
          'errors':failures, 'events':sorted(unique.values(),key=lambda e:e['start'])}
    prior_path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print(f'Updated {len(unique)} dated events; {len(successes)} sources; {len(failures)} errors.')
    for error in failures:print(error,file=sys.stderr)

if __name__=='__main__':main()
