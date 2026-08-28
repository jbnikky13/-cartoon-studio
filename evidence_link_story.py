"""Discovery Story: turn a public webpage into an editable evidence-board draft."""
from html import unescape
import re
from urllib.parse import urljoin,urlparse
import requests
from bs4 import BeautifulSoup

def fetch_story(url,max_chars=18000,max_images=12,timeout=15):
    url=(url or "").strip(); parsed=urlparse(url)
    if parsed.scheme not in ("http","https") or not parsed.netloc: raise ValueError("Please enter a valid public http(s) URL.")
    r=requests.get(url,headers={"User-Agent":"CartoonStudioDiscovery/2.0"},timeout=timeout); r.raise_for_status()
    if "text/html" not in r.headers.get("content-type","").lower(): raise ValueError("That link does not appear to be an HTML webpage.")
    soup=BeautifulSoup(r.text,"html.parser")
    for tag in soup(["script","style","noscript","svg","nav","footer","form"]): tag.decompose()
    title=_meta(soup,"og:title") or (soup.title.get_text(" ",strip=True) if soup.title else "Untitled story")
    description=_meta(soup,"og:description") or _meta(soup,"description") or ""
    image_urls=[]
    for prop in ("og:image","twitter:image"):
        value=_meta(soup,prop)
        if value: image_urls.append(urljoin(r.url,value))
    for img in soup.find_all("img"):
        src=img.get("src") or img.get("data-src") or img.get("data-lazy-src") or img.get("data-original")
        if src:
            absolute=urljoin(r.url,src)
            if absolute not in image_urls: image_urls.append(absolute)
        if len(image_urls)>=max_images: break
    main=soup.find("article") or soup.find("main") or soup.body or soup
    paragraphs=[p.get_text(" ",strip=True) for p in main.find_all(["p","h2","h3","li"])]
    text=re.sub(r"\s+"," "," ".join(p for p in paragraphs if len(p)>=35)).strip()
    text=unescape(text or description or soup.get_text(" ",strip=True))[:max_chars]
    return {"url":r.url,"title":title.strip(),"description":description.strip(),"text":text,"image_urls":image_urls[:max_images]}

def _meta(soup,name):
    node=soup.find("meta",attrs={"property":name}) or soup.find("meta",attrs={"name":name})
    return (node.get("content") or "").strip() if node else ""

def discovery_beats(story,count=6):
    title=story.get("title") or "Untitled discovery"; desc=story.get("description") or ""; text=story.get("text") or ""
    sentences=[s.strip() for s in re.split(r"(?<=[.!?])\s+",text) if len(s.strip())>30]
    beats=[f"The discovery: {title}."]
    if desc: beats.append(f"Here's the key detail: {desc}")
    for s in sentences:
        if len(beats)>=count: break
        beats.append(s)
    while len(beats)<count: beats.append("Another piece of evidence helps connect the story.")
    return beats[:count]

def make_story_beats(story,count=6):
    """Backward-compatible name used by the Evidence Board UI."""
    return discovery_beats(story,count=count)

def download_images(story,max_downloads=8,timeout=12):
    results=[]
    for url in story.get("image_urls",[])[:max_downloads]:
        try:
            r=requests.get(url,headers={"User-Agent":"CartoonStudioDiscovery/2.0"},timeout=timeout)
            if r.ok and r.headers.get("content-type","").startswith("image/") and len(r.content)>5000:
                results.append({"url":url,"bytes":r.content})
        except requests.RequestException: pass
    return results
