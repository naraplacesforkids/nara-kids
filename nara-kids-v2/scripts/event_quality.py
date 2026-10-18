"""Conservative event normalization, status and deduplication. Never infer free from unknown."""
import re
from datetime import date
from difflib import SequenceMatcher
from unicodedata import normalize

BAD_DESCRIPTION=re.compile(r'当サイトは、県をはじめ|当サイトでは|サイトマップ|プライバシー|Copyright|利用規約')
CITY_NAMES={'平群':'Heguri','へぐり':'Heguri','香芝':'Kashiba','かしば':'Kashiba','奈良市':'Nara','橿原':'Kashihara','藤原宮':'Kashihara','桜井':'Sakurai','天理':'Tenri','明日香':'Asuka','田原本':'Tawaramoto','大和高田':'Yamatotakada','生駒':'Ikoma','宇陀':'Uda'}
FREE_RE=re.compile(r'(?:参加|入場|観覧|入園|体験|参加費|入場料|料金)\s*(?:は|：|:)?\s*(?:無料|0円|０円)|無料\s*(?:で参加|入場|イベント)|free admission|free entry',re.I)
PAID_RE=re.compile(r'(?:参加費|入場料|入館料|観覧料|料金|チケット)\s*(?:は|：|:)?\s*[¥￥]?\s*[0-9０-９,，]+\s*円|有料|チケット制|要入場券',re.I)
AMOUNT_RE=re.compile(r'[¥￥]\s*([0-9,]+)|([0-9,]+)\s*円')

def clean_title(title):
    title=re.sub(r'^\s*\d+\s*閲覧\s*','',str(title or ''))
    title=re.sub(r'\s*\d+\s*閲覧\s*$','',title)
    title=re.split(r'\s+(?:期間|場所|料金|住所)\s',title,1)[0]
    title=re.sub(r'^\s*(?:予告|\d+\s+|【本日終了】)\s*','',title)
    return re.sub(r'\s+',' ',title).strip('・ -　')[:125]

def fix_city(event):
    # The prefecture aggregator's source label is not a verified event city.
    phrase=(event.get('title','')+' '+event.get('location',''))
    for word,city in CITY_NAMES.items():
        if word in phrase:return city
    if 'Event Aggregator' in event.get('provider',''):
        return 'Unconfirmed'
    return event.get('city') or 'Unconfirmed'

def quality(event, today=None):
    event=dict(event)
    event['city']=fix_city(event)
    event['title']=clean_title(event.get('title'))
    if re.search(r'お買物券プレゼント|レシート.*プレゼント|クーポン配布',event.get('title','')):return None
    desc=str(event.get('description') or '')
    if BAD_DESCRIPTION.search(desc):desc=''
    # Only tidy from a natural sentence boundary; avoid trailing broken Japanese fragments.
    desc=re.sub(r'\s+',' ',desc).strip()
    if len(desc)>270:
        shortened=desc[:270]
        candidates=[shortened.rfind(x) for x in ('。','！','!','？','?')]
        cut=max(candidates)
        desc=shortened[:cut+1] if cut>=55 else shortened[:265].rstrip()+'…'
    event['description']=desc
    phrase=desc+' '+str(event.get('priceNote') or '')
    # Never equate no price with paid. Avoid calling free if both paid and free terms occur.
    free=bool(FREE_RE.search(phrase)); paid=bool(PAID_RE.search(phrase))
    if free and paid:
        event.update(priceType='mixed',costKnown=True,free=False,priceNote='Free component and paid component; check organizer')
    elif free:
        event.update(priceType='free',costKnown=True,free=True,priceNote='Free admission/participation stated by organizer')
    elif paid:
        event.update(priceType='paid',costKnown=True,free=False,priceNote='Paid admission/participation indicated; check organizer')
    elif event.get('costKnown') and event.get('free'):
        event.update(priceType='free',costKnown=True,free=True)
    else:
        event.update(priceType='unknown',costKnown=False,free=False,priceNote='')
    day=today or date.today()
    try:
        start=date.fromisoformat(event['start']);end=date.fromisoformat(event.get('end') or event['start'])
    except (KeyError,ValueError,TypeError):return None
    if end<day:return None
    event['end']=end.isoformat()
    return event

def _key(event):
    title=normalize('NFKC',event.get('title','')).lower()
    title=re.sub(r'[^\w\u3040-\u30ff\u4e00-\u9fff]','',title)
    title=re.sub(r'(?:奈良橿原公演|奈良公演|参加者大募集|イオンモール橿原限定)','',title)
    return title

def deduplicate(events):
    out=[]
    for event in events:
        best=None
        for other in out:
            if event['start']!=other['start'] or event['end']!=other['end']:continue
            a,b=_key(event),_key(other)
            if a and b and (a in b or b in a or SequenceMatcher(None,a,b).ratio()>=0.83):
                best=other;break
        if best is None:
            out.append(event);continue
        # Prefer original venue URLs and their descriptions over aggregators.
        def score(x):return (0 if 'Aggregator' in x.get('provider','') else 5)+(2 if x.get('description') else 0)+(2 if x.get('location') else 0)
        keep=event if score(event)>score(best) else best
        lose=best if keep is event else event
        if len(lose.get('description',''))>len(keep.get('description','')) and not BAD_DESCRIPTION.search(lose.get('description','')):
            keep['description']=lose['description']
        keep['additionalSources']=sorted(set(keep.get('additionalSources',[])+lose.get('additionalSources',[])+[lose['url']]))
        if keep is event:out[out.index(best)]=keep
    return out
