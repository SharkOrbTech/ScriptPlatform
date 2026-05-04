"""
红果短剧 scraper - fetches trending/short drama content.
Scrapes novelquickapp.com category pages for specific genres.
"""
import hashlib
import logging
import re
from datetime import datetime

from bs4 import BeautifulSoup

from app.scrapers.base import BaseScraper
from app.models.schemas import TrendItem, TrendSource

logger = logging.getLogger(__name__)


class HongguoScraper(BaseScraper):
    """Scrapes trending short drama content from 红果短剧 via novelquickapp.com categories."""

    CATEGORY_URLS = [
        ("https://novelquickapp.com/category?sort_type=1", "最热短剧"),
        ("https://novelquickapp.com/category?setting=cate_1051", "打脸虐渣"),
        ("https://novelquickapp.com/category?setting=cate_760", "大女主"),
        ("https://novelquickapp.com/category?setting=cate_36", "重生"),
        ("https://novelquickapp.com/category?topic=cate_1048", "女性成长"),
        ("https://novelquickapp.com/category?setting=cate_96", "甜宠"),
        ("https://novelquickapp.com/category?topic=cate_1019", "玄幻"),
        ("https://novelquickapp.com/category?setting=cate_1044", "赘婿逆袭"),
    ]

    async def fetch_trending(self) -> list[TrendItem]:
        """Fetch trending short dramas from multiple category pages."""
        all_items = []

        for url, category_label in self.CATEGORY_URLS:
            items = await self._scrape_category(url, category_label)
            all_items.extend(items)

        # Deduplicate
        seen = set()
        unique = []
        for item in all_items:
            if item.id not in seen:
                seen.add(item.id)
                unique.append(item)

        return unique[:30]

    async def _scrape_category(self, url: str, category_label: str) -> list[TrendItem]:
        """Scrape a category page for drama items."""
        items = []
        try:
            resp = await self.get(url)
            if not resp or resp.status_code != 200:
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

                items.append(TrendItem(
                    id=series_id,
                    title=parsed["title"],
                    source=TrendSource.HONGGUO,
                    category=category_label,
                    heat=len(items) * 50 + 300,
                    description=parsed["description"],
                    url=f"https://novelquickapp.com{href}",
                    tags=parsed["tags"],
                    scraped_at=datetime.now(),
                ))

                if len(items) >= 10:
                    break

        except Exception as e:
            logger.debug(f"Category scrape {url} failed: {e}")

        return items

    def _parse_entry_text(self, text: str) -> dict:
        """Parse entry text to extract tags, title, and description."""
        known_tags = [
            "女性成长", "宫斗", "宅斗", "穿书", "女强", "逆袭", "重生",
            "都市", "爱情", "打脸", "虐渣", "甜宠", "玄幻", "穿越",
            "总裁", "豪门", "马甲", "大女主", "悬疑", "喜剧",
            "日久生情", "先婚后爱", "追妻", "虐恋", "权谋",
        ]

        tags = []
        remaining = text

        for tag in sorted(known_tags, key=len, reverse=True):
            if remaining.startswith(tag):
                tags.append(tag)
                remaining = remaining[len(tag):]
            elif tag in remaining[:40]:
                idx = remaining.find(tag)
                if 0 <= idx < 40:
                    tags.append(tag)
                    remaining = remaining[:idx] + remaining[idx + len(tag):]

        # Extract episode count
        ep_match = re.search(r"全(\d+)集", remaining)
        if ep_match:
            remaining = remaining[ep_match.end():]

        # Title is the remaining text up to first punctuation
        parts = re.split(r"[，。！？]", remaining, maxsplit=1)
        title = parts[0].strip()[:25] if parts else remaining[:25]
        title = re.sub(r"^[，。、\s]+", "", title)

        return {
            "title": title or remaining[:25],
            "description": "",
            "tags": tags,
        }

    async def search_drama(self, keyword: str) -> list[TrendItem]:
        """Search for a specific drama for copyright checking."""
        items = []
        try:
            resp = await self.get("https://novelquickapp.com/category")
            if not resp or resp.status_code != 200:
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

                items.append(TrendItem(
                    id=series_id_match.group(1),
                    title=text[:50],
                    source=TrendSource.HONGGUO,
                    category="搜索结果",
                    url=f"https://novelquickapp.com{href}",
                    scraped_at=datetime.now(),
                ))

                if len(items) >= 10:
                    break

        except Exception:
            pass
        return items
