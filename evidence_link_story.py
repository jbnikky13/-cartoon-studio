"""Create an evidence-board draft from a public article/webpage URL.

This is deliberately deterministic and lightweight: it extracts the page title,
main readable text, and OpenGraph/article images. It does not bypass paywalls,
logins, robots restrictions, or access controls.
"""
from html import unescape
import re
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup


def fetch_story(url, max_chars=12000, max_images=8, timeout=15):
    url = (url or "").strip()
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        raise ValueError("Please enter a valid public http(s) URL.")

    headers = {"User-Agent": "CartoonStudioEvidenceBoard/1.0 (+public-page-reader)"}
    response = requests.get(url, headers=headers, timeout=timeout)
    response.raise_for_status()
    if "text/html" not in response.headers.get("content-type", "").lower():
        raise ValueError("That link does not appear to be an HTML webpage.")

    soup = BeautifulSoup(response.text, "html.parser")
    for tag in soup(["script", "style", "noscript", "svg", "nav", "footer", "form"]):
        tag.decompose()

    title = _meta(soup, "og:title") or (soup.title.get_text(" ", strip=True) if soup.title else "Untitled story")
    description = _meta(soup, "og:description") or _meta(soup, "description") or ""

    image_urls = []
    for prop in ("og:image", "twitter:image"):
        value = _meta(soup, prop)
        if value:
            image_urls.append(urljoin(response.url, value))

    for img in soup.find_all("img"):
        src = img.get("src") or img.get("data-src") or img.get("data-lazy-src")
        if src:
            absolute = urljoin(response.url, src)
            if absolute not in image_urls:
                image_urls.append(absolute)
        if len(image_urls) >= max_images:
            break

    main = soup.find("article") or soup.find("main") or soup.body or soup
    paragraphs = [p.get_text(" ", strip=True) for p in main.find_all(["p", "h2", "h3"])]
    text = "\n".join(p for p in paragraphs if len(p) >= 35)
    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        text = description or soup.get_text(" ", strip=True)
    text = unescape(text)[:max_chars]

    return {
        "url": response.url,
        "title": title.strip(),
        "description": description.strip(),
        "text": text,
        "image_urls": image_urls[:max_images],
    }


def _meta(soup, name):
    node = soup.find("meta", attrs={"property": name}) or soup.find("meta", attrs={"name": name})
    return (node.get("content") or "").strip() if node else ""


def make_story_beats(story, count=6):
    text = story.get("text", "")
    sentences = re.split(r"(?<=[.!?])\s+", text)
    sentences = [s.strip() for s in sentences if len(s.strip()) > 25]
    if not sentences:
        sentences = [story.get("description") or story.get("title") or "This story was selected for review."]
    selected = sentences[:count]
    return [f"{i+1}. {sentence}" for i, sentence in enumerate(selected)]
