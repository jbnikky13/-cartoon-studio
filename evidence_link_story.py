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
    image_entries=[]
    for prop in ("og:image","twitter:image"):
        value=_meta(soup,prop)
        if value: image_entries.append({"url":urljoin(r.url,value),"alt":"","context":""})
    for img in soup.find_all("img"):
        src=img.get("src") or img.get("data-src") or img.get("data-lazy-src") or img.get("data-original")
        if src:
            absolute=urljoin(r.url,src)
            if not any(e["url"]==absolute for e in image_entries):
                alt=(img.get("alt") or "").strip()
                context=_nearby_text(img)
                image_entries.append({"url":absolute,"alt":alt,"context":context})
        if len(image_entries)>=max_images: break
    main=soup.find("article") or soup.find("main") or soup.body or soup
    paragraphs=[p.get_text(" ",strip=True) for p in main.find_all(["p","h2","h3","li"])]
    text=re.sub(r"\s+"," "," ".join(p for p in paragraphs if len(p)>=35)).strip()
    text=unescape(text or description or soup.get_text(" ",strip=True))[:max_chars]
    return {"url":r.url,"title":title.strip(),"description":description.strip(),"text":text,
            "image_urls":[e["url"] for e in image_entries[:max_images]],
            "image_entries":image_entries[:max_images]}

def _nearby_text(img_tag):
    fig=img_tag.find_parent("figure")
    if fig:
        cap=fig.find("figcaption")
        if cap:
            t=cap.get_text(" ",strip=True)
            if t: return t
    title=(img_tag.get("title") or "").strip()
    if title: return title
    prev=img_tag.find_previous(["p","h2","h3"])
    if prev:
        t=prev.get_text(" ",strip=True)
        if len(t)>=25: return t[:220]
    return ""

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

def narration_for_image(story,image_url,sentences_used,intro=False):
    """Pick narration that matches the selected image when possible."""
    title=story.get("title") or "Untitled discovery"; desc=story.get("description") or ""
    if intro:
        return f"The discovery: {title}." + (f" {desc}" if desc else "")
    entry=next((e for e in story.get("image_entries",[]) if e.get("url")==image_url),None)
    if entry:
        ctx=(entry.get("context") or entry.get("alt") or "").strip()
        if ctx: return ctx
    text=story.get("text") or ""
    sentences=[s.strip() for s in re.split(r"(?<=[.!?])\s+",text) if len(s.strip())>30]
    for s in sentences:
        if s not in sentences_used:
            sentences_used.add(s); return s
    return "⚠️ No matching text found for this image — please write a caption."

def download_images(story,max_downloads=8,timeout=12):
    results=[]
    entries=story.get("image_entries") or [{"url":u,"alt":"","context":""} for u in story.get("image_urls",[])]
    for entry in entries[:max_downloads]:
        url=entry["url"]
        try:
            r=requests.get(url,headers={"User-Agent":"CartoonStudioDiscovery/2.0"},timeout=timeout)
            if r.ok and r.headers.get("content-type","").startswith("image/") and len(r.content)>5000:
                results.append({"url":url,"bytes":r.content,"alt":entry.get("alt",""),"context":entry.get("context","")})
        except requests.RequestException: pass
    return results
