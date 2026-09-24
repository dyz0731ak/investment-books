#!/usr/bin/env python3
"""Validate built HTML, crawlable links, structured data and sitemap; no network."""
import json
import re
import sys
from pathlib import Path
from collections import Counter
from urllib.parse import urlsplit, unquote
from xml.etree import ElementTree as ET
from html.parser import HTMLParser
ROOT = Path(__file__).resolve().parents[1]
SITE = 'https://stock-overflow24.com'
class Page(HTMLParser):
    def __init__(self, text):
        super().__init__(); self.ids=[]; self.links=[]; self.h1=0; self.canonical=[]; self.descriptions=[]; self.structured=[]; self.title=''; self.in_title=False; self.in_json=False; self.buffer=''; self.robots=''; self.images=[]
        self.feed(text)
    def handle_starttag(self, tag, attrs):
        a=dict(attrs)
        if 'id' in a: self.ids.append(a['id'])
        if tag=='h1': self.h1+=1
        if tag=='a': self.links.append(a.get('href',''))
        if tag=='img': self.images.append(a)
        if tag=='title': self.in_title=True
        if tag=='link' and a.get('rel')=='canonical': self.canonical.append(a.get('href'))
        if tag=='meta' and a.get('name')=='description': self.descriptions.append(a.get('content',''))
        if tag=='meta' and a.get('name')=='robots': self.robots=a.get('content','')
        if tag=='script' and a.get('type')=='application/ld+json': self.in_json=True; self.buffer=''
    def handle_data(self, data):
        if self.in_title: self.title+=data
        if self.in_json: self.buffer+=data
    def handle_endtag(self, tag):
        if tag=='title': self.in_title=False
        if tag=='script' and self.in_json: self.structured.append(json.loads(self.buffer)); self.in_json=False

def main():
    pages={}; errors=[]
    for path in ROOT.rglob('*.html'):
        if any(part.startswith('.') or part in ('node_modules',) for part in path.relative_to(ROOT).parts): continue
        url='/' + str(path.relative_to(ROOT)).replace('index.html','')
        pages[url]=Page(path.read_text())
    titles=[];descriptions=[];link_count=0
    for url,p in pages.items():
        if p.h1!=1: errors.append(f'{url}: {p.h1} h1 headings')
        if len(p.canonical)!=1 or p.canonical[0]!=SITE+url: errors.append(f'{url}: wrong canonical {p.canonical}')
        if len(p.descriptions)!=1 or not p.descriptions[0]: errors.append(f'{url}: missing description')
        if 'main' not in p.ids: errors.append(f'{url}: missing skip-link target')
        if len(p.ids)!=len(set(p.ids)): errors.append(f'{url}: duplicate IDs')
        titles.append(p.title);descriptions+=p.descriptions
        for href in p.links:
            parsed=urlsplit(href)
            if parsed.scheme in ('mailto','tel'): continue
            if parsed.netloc and parsed.netloc != urlsplit(SITE).netloc: continue
            link_count+=1
            target=unquote(parsed.path) or url
            if target.endswith('.pdf'): continue
            if not target.startswith('/'): target=url.rsplit('/',1)[0]+'/'+target
            if target not in pages:
                errors.append(f'{url}: broken internal link {href}'); continue
            if parsed.fragment and unquote(parsed.fragment) not in pages[target].ids:
                errors.append(f'{url}: missing anchor {href}')
        for img in p.images:
            if 'alt' not in img or 'width' not in img or 'height' not in img: errors.append(f'{url}: incomplete image dimensions/alt {img.get("src")}')
        if url.startswith('/books/') and url!='/books/':
            schema=[d for d in p.structured if d.get('@type')=='Book']
            if len(schema)!=1: errors.append(f'{url}: missing Book schema')
        if url not in ('/','/404.html') and not any(d.get('@type')=='BreadcrumbList' for d in p.structured): errors.append(f'{url}: missing breadcrumb schema')
    for name,values in [('titles',titles),('descriptions',descriptions)]:
        duplicates=[v for v,n in Counter(values).items() if n>1]
        if duplicates: errors.append(f'duplicate {name}: {duplicates}')
    ns={'s':'http://www.sitemaps.org/schemas/sitemap/0.9'}
    locations=[node.text.removeprefix(SITE) for node in ET.parse(ROOT/'sitemap.xml').findall('.//s:loc',ns)]
    intended={u for u,p in pages.items() if 'noindex' not in p.robots}
    if set(locations)!=intended: errors.append(f'Sitemap mismatch: {set(locations)^intended}')
    if len(locations)!=len(set(locations)): errors.append('Duplicate sitemap URLs')
    result={'pages':len(pages),'indexable_pages':len(locations),'internal_links_checked':link_count,'errors':errors}
    print(json.dumps(result,ensure_ascii=False,indent=2))
    return bool(errors)
if __name__=='__main__':sys.exit(main())
