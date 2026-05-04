"""
novelquickapp.com scraper - Primary data source for trending short dramas.
Scrapes main page and category pages for all dramas, then optionally fetches detail pages for richer data.
504+ dramas available with rich category/tag/setting metadata.
"""
import asyncio
import hashlib
import logging
import re
from datetime import datetime
from typing import Optional

import httpx
from bs4 import BeautifulSoup

from app.models.schemas import TrendItem, TrendSource

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9",
}


class NovelQuickAppScraper:
    """Scrapes trending short dramas from novelquickapp.com (红果短剧官网)."""

    BASE_URL = "https://novelquickapp.com"

    def __init__(self):
        self.client = httpx.AsyncClient(
            headers=HEADERS,
            timeout=20.0,
            follow_redirects=True,
        )

    async def fetch_trending(self, limit: int = 60, fetch_details: bool = True) -> list[TrendItem]:
        """Fetch trending dramas from the main page and category page."""
        items = []
        try:
            # 1. Scrape main page
            main_items = await self._scrape_page(self.BASE_URL)
            items.extend(main_items)

            # 2. Scrape hot/trending category page for more items
            hot_items = await self._scrape_page(f"{self.BASE_URL}/category?sort_type=1")
            items.extend(hot_items)

            # 3. Scrape new items category
            new_items = await self._scrape_page(f"{self.BASE_URL}/category?sort_type=2&time=1")
            items.extend(new_items)

            # Deduplicate by series_id, keeping first occurrence (main page has priority)
            seen = set()
            unique = []
            for item in items:
                if item.id not in seen:
                    seen.add(item.id)
                    unique.append(item)
            items = unique

            # Reassign heat based on final position
            for i, item in enumerate(items):
                item.heat = (len(items) - i) * 50

        except Exception as e:
            logger.error(f"novelquickapp.com scrape failed: {e}")

        # Fetch details for items without descriptions first, then top items
        if fetch_details and items:
            # Prioritize items without descriptions
            no_desc = [i for i in items if not i.description][:15]
            has_desc = [i for i in items if i.description][:5]
            to_enrich = no_desc + has_desc

            detail_tasks = [self._fetch_detail_async(item) for item in to_enrich[:20]]
            await asyncio.gather(*detail_tasks, return_exceptions=True)

        return items[:limit]

    async def _scrape_page(self, url: str) -> list[TrendItem]:
        """Scrape a single page for drama items."""
        items = []
        try:
            resp = await self.client.get(url)
            if resp.status_code != 200:
                logger.warning(f"novelquickapp.com {url} returned {resp.status_code}")
                return items

            soup = BeautifulSoup(resp.text, "lxml")

            for a_tag in soup.find_all("a", href=True):
                href = a_tag["href"]
                if "/detail?series_id=" not in href:
                    continue

                text = a_tag.get_text(strip=True)
                if len(text) < 10:
                    continue

                series_id_match = re.search(r"series_id=(\d+)", href)
                if not series_id_match:
                    continue

                series_id = series_id_match.group(1)
                parsed = self._parse_entry_text(text)

                # Try to extract cover image from parent or sibling img
                cover_url = ""
                parent = a_tag.parent
                if parent:
                    img = parent.find("img")
                    if img:
                        cover_url = img.get("src", "") or img.get("data-src", "")

                items.append(TrendItem(
                    id=series_id,
                    title=parsed["title"],
                    source=TrendSource.HONGGUO,
                    category=parsed["category"],
                    heat=len(items) * 50 + 500,
                    description=parsed["description"],
                    cover_url=cover_url or parsed.get("cover", ""),
                    url=f"{self.BASE_URL}{href}",
                    tags=parsed["tags"],
                    scraped_at=datetime.now(),
                ))

        except Exception as e:
            logger.error(f"Scrape page {url} failed: {e}")

        return items

    async def _fetch_detail_async(self, item: TrendItem):
        """Fetch detail page to enrich a trend item."""
        try:
            detail = await self.fetch_detail(item.id)
            if detail.get("description") and len(detail["description"]) > len(item.description):
                item.description = detail["description"]
            if detail.get("title") and len(detail["title"]) > len(item.title):
                item.title = detail["title"]
            if detail.get("tags"):
                # Merge tags
                existing = set(item.tags)
                for tag in detail["tags"]:
                    if tag not in existing:
                        item.tags.append(tag)
            if detail.get("episode_count") and not item.tags:
                pass  # Already handled in tags
        except Exception as e:
            logger.debug(f"Detail fetch for {item.id} failed: {e}")

    def _parse_entry_text(self, text: str) -> dict:
        """Parse entry text to extract tags, title, and description."""
        known_tags = [
            "女性成长", "宫斗", "宅斗", "穿书", "女强", "逆袭", "重生",
            "抗战", "谍战", "民国", "爱情", "家国情怀", "日久生情",
            "都市", "暗恋", "成真", "打脸", "虐渣", "甜宠",
            "商业联姻", "双向奔赴", "一见钟情", "奇幻", "脑洞",
            "玄幻", "赘婿", "系统", "穿越", "先婚后爱", "读心术",
            "古风", "权谋", "团宠", "青春", "校园", "动作",
            "悬疑", "探案", "追妻", "虐恋", "马甲", "年代",
            "种田", "经营", "豪门", "总裁", "千金", "替身",
            "闪婚", "隐婚", "战神", "医神", "龙王", "无敌",
            "仙侠", "末日", "无限流", "兽世", "体育", "竞技",
            "都市日常", "都市爱情", "都市玄幻", "家庭伦理", "家长里短",
            "真假千金", "大女主", "萌宝", "黄昏恋", "极品亲戚",
            "追妻火葬场", "玄学", "亲情", "婚姻生活", "年代爱情",
            "宫斗宅斗", "奇幻脑洞", "种田经营", "都市总裁",
            "抗战谍战", "剧情", "反转", "直播", "律师", "医生",
            "喜剧", "灵异", "志怪", "武侠", "科幻", "恐怖",
            "商战", "异能", "神豪", "破镜重圆", "青梅竹马",
            "姐弟恋", "病娇", "灵魂互换", "黑道", "丧尸", "特种兵",
        ]

        tags = []
        remaining = text

        # Extract tags from the beginning
        for tag in sorted(known_tags, key=len, reverse=True):
            if remaining.startswith(tag):
                tags.append(tag)
                remaining = remaining[len(tag):]
            elif tag in remaining[:60]:
                idx = remaining.find(tag)
                if 0 <= idx < 60:
                    tags.append(tag)
                    remaining = remaining[:idx] + remaining[idx + len(tag):]

        # Extract episode count
        ep_match = re.search(r"全(\d+)集", remaining)
        episode_count = ""
        if ep_match:
            episode_count = f"全{ep_match.group(1)}集"
            remaining = remaining[ep_match.end():]

        # Split title and description
        parts = re.split(r"[，。！？]", remaining, maxsplit=1)
        if len(parts) > 1 and len(parts[0]) > 2:
            title = parts[0].strip()
            description = remaining[len(title):].strip()
        else:
            title = remaining[:25].strip()
            description = remaining[25:].strip()

        title = re.sub(r"^[，。、\s]+", "", title)
        if not title:
            title = remaining[:25]

        category = " / ".join(tags[:3]) if tags else "短剧"

        return {
            "title": title,
            "description": description[:500],
            "tags": tags,
            "category": category,
            "episode_count": episode_count,
        }

    async def fetch_detail(self, series_id: str) -> dict:
        """Fetch detailed info for a specific drama from its detail page."""
        try:
            resp = await self.client.get(f"{self.BASE_URL}/detail", params={"series_id": series_id})
            if resp.status_code != 200:
                return {}

            soup = BeautifulSoup(resp.text, "lxml")

            # Get title from <title> tag
            title = ""
            title_el = soup.find("title")
            if title_el:
                raw_title = title_el.get_text(strip=True)
                if "|" in raw_title:
                    title = raw_title.split("|")[-1].strip()
                else:
                    title = raw_title

            # Get description from meta tag
            description = ""
            meta_desc = soup.find("meta", attrs={"name": "description"})
            if meta_desc:
                description = meta_desc.get("content", "")

            # Get keywords from meta tag (contains tags)
            tags = []
            meta_kw = soup.find("meta", attrs={"name": "keywords"})
            if meta_kw:
                kw_text = meta_kw.get("content", "")
                kw_parts = [k.strip() for k in kw_text.split(",")]
                for k in kw_parts:
                    if len(k) >= 2 and k not in tags and k != "红果短剧":
                        tags.append(k)

            # Extract more content from page body
            page_text = soup.get_text(separator="\n", strip=True)

            # Try to find synopsis/description in page content
            if not description or len(description) < 30:
                # Look for description patterns in the page
                desc_patterns = [
                    r"简介[：:]\s*(.{20,300})",
                    r"剧情[：:]\s*(.{20,300})",
                    r"内容简介[：:]\s*(.{20,300})",
                ]
                for pattern in desc_patterns:
                    match = re.search(pattern, page_text)
                    if match:
                        description = match.group(1).strip()
                        break

            # Extract episode count from page
            episode_count = ""
            ep_match = re.search(r"全(\d+)集", page_text)
            if ep_match:
                episode_count = ep_match.group(1)

            # Extract more tags from page content
            all_tag_keywords = [
                "女性成长", "宫斗", "宅斗", "穿书", "女强", "逆袭", "重生",
                "都市", "爱情", "打脸", "虐渣", "玄幻", "穿越", "年代",
                "民国", "谍战", "总裁", "豪门", "马甲", "大女主",
                "日久生情", "甜宠", "先婚后爱", "悬疑", "喜剧", "复仇",
                "千金", "替身", "闪婚", "隐婚", "战神", "赘婿", "系统",
                "仙侠", "末日", "校园", "青春", "权谋", "团宠", "萌宝",
            ]
            for k in all_tag_keywords:
                if k in page_text and k not in tags:
                    tags.append(k)

            return {
                "title": title,
                "description": description[:500],
                "tags": tags[:10],
                "episode_count": episode_count,
            }
        except Exception as e:
            logger.error(f"Detail fetch for {series_id} failed: {e}")
            return {}

    async def search_related_by_tags(self, tags: list[str], limit: int = 10) -> list[TrendItem]:
        """Actively search for related trends by tag keywords across the site."""
        items = []
        seen = set()

        # Search across multiple pages with each tag
        pages_to_search = [
            self.BASE_URL,
            f"{self.BASE_URL}/category?sort_type=1",
            f"{self.BASE_URL}/category?sort_type=2&time=1",
        ]

        for tag in tags[:3]:
            for url in pages_to_search:
                try:
                    resp = await self.client.get(url)
                    if resp.status_code != 200:
                        continue
                    soup = BeautifulSoup(resp.text, "lxml")
                    for a_tag in soup.find_all("a", href=True):
                        href = a_tag["href"]
                        if "/detail?series_id=" not in href:
                            continue
                        text = a_tag.get_text(strip=True)
                        if tag not in text:
                            continue
                        series_id_match = re.search(r"series_id=(\d+)", href)
                        if not series_id_match:
                            continue
                        sid = series_id_match.group(1)
                        if sid in seen:
                            continue
                        seen.add(sid)
                        parsed = self._parse_entry_text(text)
                        items.append(TrendItem(
                            id=sid,
                            title=parsed["title"],
                            source=TrendSource.HONGGUO,
                            category=parsed["category"],
                            description=parsed["description"],
                            url=f"{self.BASE_URL}{href}",
                            tags=parsed["tags"],
                            scraped_at=datetime.now(),
                        ))
                        if len(items) >= limit:
                            return items
                except Exception:
                    continue

        return items

    async def search(self, keyword: str) -> list[TrendItem]:
        """Search for dramas matching a keyword."""
        items = []
        try:
            # Search on main page
            resp = await self.client.get(self.BASE_URL)
            if resp.status_code != 200:
                return items

            soup = BeautifulSoup(resp.text, "lxml")
            keyword_lower = keyword.lower()

            for a_tag in soup.find_all("a", href=True):
                href = a_tag["href"]
                if "/detail?series_id=" not in href:
                    continue

                text = a_tag.get_text(strip=True)
                if keyword_lower not in text.lower():
                    continue

                series_id_match = re.search(r"series_id=(\d+)", href)
                if not series_id_match:
                    continue

                parsed = self._parse_entry_text(text)
                items.append(TrendItem(
                    id=series_id_match.group(1),
                    title=parsed["title"],
                    source=TrendSource.HONGGUO,
                    category=parsed["category"],
                    description=parsed["description"],
                    url=f"{self.BASE_URL}{href}",
                    tags=parsed["tags"],
                    scraped_at=datetime.now(),
                ))

                if len(items) >= 10:
                    break

            # Also search category page
            if len(items) < 5:
                resp2 = await self.client.get(f"{self.BASE_URL}/category")
                if resp2.status_code == 200:
                    soup2 = BeautifulSoup(resp2.text, "lxml")
                    for a_tag in soup2.find_all("a", href=True):
                        href = a_tag["href"]
                        if "/detail?series_id=" not in href:
                            continue
                        text = a_tag.get_text(strip=True)
                        if keyword_lower not in text.lower():
                            continue
                        series_id_match = re.search(r"series_id=(\d+)", href)
                        if not series_id_match:
                            continue
                        sid = series_id_match.group(1)
                        if any(i.id == sid for i in items):
                            continue
                        parsed = self._parse_entry_text(text)
                        items.append(TrendItem(
                            id=sid,
                            title=parsed["title"],
                            source=TrendSource.HONGGUO,
                            category=parsed["category"],
                            description=parsed["description"],
                            url=f"{self.BASE_URL}{href}",
                            tags=parsed["tags"],
                            scraped_at=datetime.now(),
                        ))
                        if len(items) >= 15:
                            break

        except Exception as e:
            logger.error(f"Search for '{keyword}' failed: {e}")

        return items

    async def close(self):
        await self.client.aclose()
