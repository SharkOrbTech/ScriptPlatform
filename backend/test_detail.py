"""Test detail page scraping from novelquickapp.com."""
import httpx
import re
import json
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15",
    "Accept": "text/html",
    "Accept-Language": "zh-CN,zh;q=0.9",
}


def explore_detail(series_id: str):
    url = f"https://novelquickapp.com/detail?series_id={series_id}"
    print(f"Fetching: {url}")
    resp = httpx.get(url, headers=HEADERS, follow_redirects=True, timeout=15)
    html = resp.text
    soup = BeautifulSoup(html, "lxml")

    print(f"\n=== Page Length: {len(html)} chars ===")

    # Find all text content
    text = soup.get_text(separator="\n", strip=True)

    # Find title
    title_el = soup.find("title")
    if title_el:
        print(f"Title: {title_el.get_text(strip=True)}")

    # Find meta description
    meta_desc = soup.find("meta", attrs={"name": "description"})
    if meta_desc:
        print(f"Meta desc: {meta_desc.get('content', '')[:200]}")

    # Find structured data
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(script.string)
            print(f"\nJSON-LD: {json.dumps(data, ensure_ascii=False, indent=2)[:500]}")
        except:
            pass

    # Find all meaningful text blocks
    print("\n=== Text Blocks ===")
    blocks = re.findall(r"[\u4e00-\u9fff\uff0c\u3002\uff01\uff1f]{20,}", text)
    for i, b in enumerate(blocks[:15]):
        print(f"  Block {i}: {b[:150]}")

    # Find tags/labels
    print("\n=== Tags/Labels ===")
    for el in soup.select('[class*="tag"], [class*="label"], [class*="genre"], [class*="type"]'):
        t = el.get_text(strip=True)
        if t and len(t) < 20:
            print(f"  Tag: {t}")

    # Find images
    print("\n=== Images ===")
    for img in soup.find_all("img"):
        src = img.get("src", "")
        alt = img.get("alt", "")
        if src and ("novel" in src or "book" in src or "cover" in src or "byteimg" in src):
            print(f"  IMG: {src[:100]} alt={alt}")

    # Find links to chapters
    print("\n=== Chapter Links ===")
    for a in soup.find_all("a", href=True):
        href = a["href"]
        text = a.get_text(strip=True)
        if "chapter" in href or "read" in href or "第" in text:
            print(f"  {href} -> {text[:50]}")


if __name__ == "__main__":
    # Test with a known series ID
    explore_detail("7574406343008734232")
