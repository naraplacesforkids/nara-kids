"""Discovery from public event listing pages.

Listings are *leads*, not confirmation of admission, times, age or availability.
Page layout may change, so always retain source links and log extracted counts.
"""
import hashlib
import re
from datetime import date,timedelta
from urllib.parse import urljoin,urlparse
from bs4 import BeautifulSoup

# Include family outings, rather than just activities with 'child' in the title.
FAMILY=re.compile(r'子ども|こども|子育て|親子|幼児|乳児|赤ちゃん|ベビー|キッズ|児童|おはなし|読み聞かせ|手遊び|工作|体験|科学|昆虫|動物|ファミリー|祭|フェス|マルシェ|ハロウィン|ピニャータ|サーカス|コスモス|遊び|あそび|ショー|ワークショップ|イルミネーション|展示|パレード|family|kids|circus', re.I)
EXCLUDE=re.compile(r'プレゼントキャンペーン|応募|抽選会|求人|就職|セミナー|クレジットカード|住宅ローン|補助金|募集要項|献血|職員|保険相談|説明会|認定講座',re.I)
DATE=re.compile(r'(20\d{2})\s*[年/.-]\s*(\d{1,2})\s*[月/.-]\s*(\d{1,2})\s*日?')

def spans(text):
    dates=[]
    for y,m,d in DATE.findall(text):
        try: dates.append(date(int(y),int(m),int(d)))
        except ValueError: pass
    # Direct listing pages can contain multiple dates. Use first two nearby dates.
    return dates

def extract_listing(html,source,today=None):
    today=today or date.today()
    soup=BeautifulSoup(html,'html.parser')
    results=[];seen=set()
    root=urlparse(source['url'])
    for a in soup.select('a[href]'):
        raw=a.get_text(' ',strip=True)
        if not raw or len(raw)>240: continue
        href=urljoin(source['url'],a.get('href',''))
        dest=urlparse(href)
        if dest.scheme!='https' or dest.hostname!=root.hostname:continue
        # Event links should be direct detail links, not the navigation or search index.
        if dest.path.rstrip('/') == root.path.rstrip('/'):continue
        container=a
        sample=raw
        for _ in range(3):
            if spans(sample):break
            container=container.parent or container
            sample=container.get_text(' ',strip=True)[:700]
        dates=spans(sample)
        if not dates:continue
        # An item's date text may include a calendar/other event, so keep it nearby.
        start=dates[0]
        end=dates[1] if len(dates)>=2 and dates[1]>=start and (dates[1]-start).days<=180 else start
        if end<today or start>today+timedelta(days=75):continue
        title=re.sub(r'^(開催中|本日限定|開催予定|開催終了|New|NEW)\s*','',raw).strip()
        # Avoid date-only anchors, dates in title, or giant generic containers.
        title=DATE.sub('',title)
        title=re.sub(r'\([月火水木金土日]\)', '', title).strip(' -・　')
        if len(title)<4 or len(title)>100 or not FAMILY.search(title) or EXCLUDE.search(title):continue
        key=(href,start,end)
        if key in seen:continue
        seen.add(key)
        uid=hashlib.sha256(f'{source["name"]}|{start}|{href}'.encode()).hexdigest()[:16]
        results.append({'id':uid,'title':title,'start':start.isoformat(),'end':end.isoformat(),
                        'city':source.get('city','Nara'),'location':source.get('location',''),
                        'description':'','url':href,'provider':source['name'],
                        'free':False,'costKnown':False,'reviewStatus':'unverified',
                        'discoveredFrom':'public_event_listing'})
    return results


# Conservative summaries: only text extracted from the organizer's own event page.
# No AI-generated details and no guessed admission, schedule or age eligibility.
def extract_event_summary(html, title):
    soup=BeautifulSoup(html,'html.parser')
    for node in soup(['script','style','nav','footer','header','noscript']): node.decompose()
    candidates=[]
    for attr in ({'property':'og:description'},{'name':'description'},{'name':'twitter:description'}):
        meta=soup.find('meta',attrs=attr)
        if meta and meta.get('content'): candidates.append(meta['content'])
    main=soup.find('main') or soup.find('article') or soup
    for p in main.select('p, .event-description, .event-detail, .description')[:45]:
        candidates.append(p.get_text(' ',strip=True))
    title_compact=re.sub(r'\s+','',title)
    for txt in candidates:
        txt=re.sub(r'\s+',' ',txt).strip()
        if len(txt)<28:continue
        if len(txt)>1400:continue
        if re.search(r'プライバシー|Cookie|ログイン|すべてのイベント|サイトマップ|お問い合わせ|無断転載|Copyright|メルマガ',txt,re.I):continue
        # Avoid generic site-wide metadata that may appear on every page.
        if len(txt)<100 and title_compact and title_compact not in re.sub(r'\s+','',txt):
            # Paragraphs may not repeat the title; keep them but require event-like descriptions.
            if not re.search(r'開催|参加|楽し|体験|登場|作|食|演奏|ショー|展示|ワークショップ|マルシェ|festiv|event|famil',txt,re.I):continue
        if len(txt)>175:txt=txt[:172].rsplit(' ',1)[0].rstrip('、，,。')+'…'
        return txt
    return ''
