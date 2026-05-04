"""
番茄小说 scraper - fetches trending novels from Tomato Novel platform.
Uses fanqienovel.com API for category data.
"""
import hashlib
import logging
import re
from datetime import datetime

from bs4 import BeautifulSoup

from app.scrapers.base import BaseScraper
from app.models.schemas import TrendItem, TrendSource

logger = logging.getLogger(__name__)


class TomatoScraper(BaseScraper):
    """Scrapes trending novel content from 番茄小说."""

    CATEGORY_API = "https://fanqienovel.com/api/author/book/category_list/v0/"

    async def fetch_trending(self) -> list[TrendItem]:
        """Fetch trending novels from fanqienovel categories."""
        results = []

        # Fetch category data from API
        items = await self._fetch_categories()
        results.extend(items)

        # Also try Bing search for supplementary data
        items = await self._scrape_bing()
        results.extend(items)

        # Deduplicate
        seen = set()
        unique = []
        for item in results:
            key = item.title[:15]
            if key not in seen:
                seen.add(key)
                unique.append(item)

        return unique[:25]

    async def _fetch_categories(self) -> list[TrendItem]:
        """Fetch novel categories from fanqienovel API."""
        items = []
        try:
            resp = await self.get(self.CATEGORY_API, params={
                "page_count": "20",
                "page_index": "0",
                "gender": "-1",
                "category_id": "-1",
                "creation_status": "-1",
                "word_count": "-1",
            })
            if resp and resp.status_code == 200:
                data = resp.json()
                categories = data.get("data", [])
                for cat in categories:
                    name = cat.get("name", "")
                    desc = cat.get("description", "")
                    cat_id = cat.get("category_id", "")
                    if name:
                        items.append(TrendItem(
                            id=f"fanqie_cat_{cat_id}",
                            title=name,
                            source=TrendSource.TOMATO,
                            category="番茄小说分类",
                            description=desc,
                            heat=500,
                            scraped_at=datetime.now(),
                        ))
        except Exception as e:
            logger.debug(f"Fanqie category fetch failed: {e}")

        return items

    async def _scrape_bing(self) -> list[TrendItem]:
        """Scrape Bing for trending novel content as supplement."""
        items = []
        queries = [
            "番茄小说 热门 排行榜 2025",
            "番茄小说 最火 完结 推荐",
        ]

        for query in queries:
            try:
                resp = await self.get("https://cn.bing.com/search", params={"q": query, "count": "10"})
                if resp and resp.status_code == 200:
                    soup = BeautifulSoup(resp.text, "lxml")
                    for idx, result in enumerate(soup.select("#b_results .b_algo")[:5]):
                        title_el = result.select_one("h2 a")
                        if title_el:
                            title = title_el.get_text(strip=True)
                            title = re.sub(r'\s+', ' ', title).strip()
                            if title and 5 < len(title) < 80:
                                desc = ""
                                desc_el = result.select_one(".b_caption p, .b_lineclamp2")
                                if desc_el:
                                    desc = desc_el.get_text(strip=True)[:200]

                                # Filter out irrelevant results
                                if any(kw in title for kw in ['番茄', '小说', '短剧', '排行', '推荐', '热门']):
                                    items.append(TrendItem(
                                        id=hashlib.md5(f"tomato_bing_{title}".encode()).hexdigest()[:12],
                                        title=title,
                                        source=TrendSource.TOMATO,
                                        category="番茄小说",
                                        heat=(5 - idx) * 50 + 200,
                                        description=desc,
                                        url=title_el.get("href", ""),
                                        scraped_at=datetime.now(),
                                    ))
            except Exception as e:
                logger.debug(f"Bing query '{query}' failed: {e}")

        return items

    async def search_novel(self, keyword: str) -> list[TrendItem]:
        """Search for a specific novel for copyright checking."""
        items = []
        queries = [f"番茄小说 {keyword}", f"小说 {keyword} 热门"]
        for query in queries:
            try:
                resp = await self.get("https://cn.bing.com/search", params={"q": query, "count": "10"})
                if resp and resp.status_code == 200:
                    soup = BeautifulSoup(resp.text, "lxml")
                    for idx, result in enumerate(soup.select("#b_results .b_algo")[:5]):
                        title_el = result.select_one("h2 a")
                        if title_el:
                            title = title_el.get_text(strip=True)
                            if title:
                                desc = ""
                                desc_el = result.select_one(".b_caption p, .b_lineclamp2")
                                if desc_el:
                                    desc = desc_el.get_text(strip=True)[:200]
                                items.append(TrendItem(
                                    id=hashlib.md5(f"tomato_search_{keyword}_{idx}".encode()).hexdigest()[:12],
                                    title=title,
                                    source=TrendSource.TOMATO,
                                    category="搜索结果",
                                    description=desc,
                                    url=title_el.get("href", ""),
                                    scraped_at=datetime.now(),
                                ))
            except Exception:
                pass
        return items
