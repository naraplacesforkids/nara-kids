"""Optional machine translation of event title/description using Google Cloud Translation v2.
Requires GOOGLE_TRANSLATE_API_KEY secret. No key => skip, leaving original Japanese explicit.
Store source text unchanged; translation is unreviewed, never translate official links.
"""
import os,json,time,sys
from pathlib import Path
import requests
ROOT=Path(__file__).resolve().parents[1]
LANGS={'en':'en','ht':'ht','fr':'fr','ne':'ne','hi':'hi'}

def main():
    key=os.getenv('GOOGLE_TRANSLATE_API_KEY','')
    if not key:
        print('No translation API key; original organizer descriptions retained.')
        return
    path=ROOT/'events.json';doc=json.loads(path.read_text(encoding='utf8'))
    count=0
    for ev in doc.get('events',[]):
        source=[ev.get('title',''),ev.get('description','')]
        if not any(source):continue
        ev.setdefault('translations',{})
        for lang,target in LANGS.items():
            if ev['translations'].get(lang,{}).get('description'):continue
            try:
                r=requests.post('https://translation.googleapis.com/language/translate/v2',params={'key':key},json={'q':source,'target':target,'format':'text'},timeout=15)
                r.raise_for_status();rows=r.json()['data']['translations']
                if len(rows)!=2:continue
                import html
                ev['translations'][lang]={'title':html.unescape(rows[0]['translatedText']),'description':html.unescape(rows[1]['translatedText'])}
                count+=1
            except (requests.RequestException,KeyError,ValueError) as ex:
                print(f'Translation failed for {ev.get("id")}, {lang}: {type(ex).__name__}',file=sys.stderr)
            time.sleep(.12)
    path.write_text(json.dumps(doc,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print(f'Translated {count} event-language pairs (machine-generated, unreviewed).')
if __name__=='__main__':main()
