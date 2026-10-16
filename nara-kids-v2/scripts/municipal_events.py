"""Conservative extractor for dated municipal calendar tables.

The listing is a lead, NOT confirmation that admission or reservations are available.
Calendar pages often contain unrelated civic meetings; include only family-related titles.
"""
import hashlib
import re
from datetime import date, timedelta
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup

FAMILY = re.compile(r'子ども|こども|子育て|親子|幼児|乳児|赤ちゃん|ベビー|キッズ|児童|おはなし|読み聞かせ|わらべうた|遊ぼう|あそぼう|おもちゃ|工作|体験|科学|昆虫|虫観察|動物|ファミリー|ピクニック|祭り|フェスタ|絵本|手遊び|人形劇|プラネタリウム|kids|family|children',re.I)
EXCLUDE = re.compile(r'募集|説明会|相談|採用|就職|セミナー|講演|研修|資格|会議|委員|ボランティア大募集|おとな|成人|高齢|介護|検診|講習|職員|施設利用|補助金|被災|地域包括|仕事|広報',re.I)
DATE_ROW = re.compile(r'^\s*(\d{1,2})\s*(?:日|[|｜])?\s*(?:月曜|火曜|水曜|木曜|金曜|土曜|日曜|月曜日|火曜日|水曜日|木曜日|金曜日|土曜日|日曜日)?\s*$')
YM = re.compile(r'(20\d{2})年[^\n]{0,25}?(\d{1,2})月')

def extract_calendar(html, source, today=None):
    today = today or date.today()
    soup=BeautifulSoup(html,'html.parser')
    # Require a visible month + year. Never infer an event date from the scrape date.
    heading=' '.join(x.get_text(' ',strip=True) for x in soup.find_all(['h1','h2','h3'])[:30])
    match=YM.search(heading)
    if not match: return []
    year,month=map(int,match.groups())
    events=[]
    for row in soup.select('tr'):
        cells=row.find_all(['td','th'],recursive=False)
        if len(cells)<2:continue
        first=cells[0].get_text(' ',strip=True)
        m=DATE_ROW.match(first)
        if not m:
            # Municipal tables typically use columns "day | weekday | event"
            m=re.match(r'^\s*(\d{1,2})\s*$',first)
        if not m:continue
        day=int(m.group(1))
        try: when=date(year,month,day)
        except ValueError:continue
        if when<today or when>today+timedelta(days=75):continue
        # Do not include links in a weekday / date cell.
        for a in row.select('td a[href], th a[href]'):
            title=a.get_text(' ',strip=True)
            if len(title)<4 or len(title)>180 or not FAMILY.search(title) or EXCLUDE.search(title):continue
            url=urljoin(source['url'],a.get('href',''))
            if urlparse(url).scheme!='https' or urlparse(url).hostname!=urlparse(source['url']).hostname:continue
            uid=hashlib.sha256(f"{source['name']}|{when}|{url}".encode()).hexdigest()[:16]
            events.append({'id':uid,'title':title,'start':when.isoformat(),'end':when.isoformat(),
                'city':source['city'],'location':'','description':'', 'url':url,
                'provider':source['name'],'free':False,'costKnown':False,
                'reviewStatus':'unverified','discoveredFrom':'municipal_calendar'})
    return events
