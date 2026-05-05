"""
Trend Aggregation Service - Combines data from multiple sources,
provides intelligent analysis and dynamic genre/style extraction.
Extremely smart: proactive search, trend clustering, cross-platform analysis.
"""
import asyncio
import json
import logging
import os
import re
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from app.scrapers.novelquickapp import NovelQuickAppScraper
from app.scrapers.hongguo import HongguoScraper
from app.scrapers.tomato import TomatoScraper
from app.models.schemas import TrendItem, TrendSource

logger = logging.getLogger(__name__)

CACHE_DIR = Path(__file__).parent.parent.parent / "cache"
TRENDS_CACHE_FILE = CACHE_DIR / "trends_cache.json"


class TrendService:
    def __init__(self):
        self.nqa = NovelQuickAppScraper()
        self.hongguo = HongguoScraper()
        self.tomato = TomatoScraper()
        self._cache: dict[str, tuple[list[TrendItem], datetime]] = {}
        self._cache_ttl = timedelta(minutes=15)
        self._trend_clusters: dict[str, list[str]] = {}  # tag -> [related tags]
        self._is_fetching = False
        # Load disk cache on init
        self._load_disk_cache()

    def _load_disk_cache(self):
        """Load trends from disk cache if available and fresh."""
        try:
            if TRENDS_CACHE_FILE.exists():
                data = json.loads(TRENDS_CACHE_FILE.read_text(encoding='utf-8'))
                cached_at = datetime.fromisoformat(data.get("cached_at", "2000-01-01"))
                if datetime.now() - cached_at < timedelta(hours=24):
                    items = [TrendItem(**item) for item in data.get("items", [])]
                    self._cache["all_trends_disk"] = (items, cached_at)
                    logger.info(f"Loaded {len(items)} trends from disk cache")
        except Exception as e:
            logger.warning(f"Failed to load disk cache: {e}")

    def _save_disk_cache(self, items: list[TrendItem]):
        """Save trends to disk cache."""
        try:
            CACHE_DIR.mkdir(parents=True, exist_ok=True)
            data = {
                "cached_at": datetime.now().isoformat(),
                "items": [item.model_dump(mode='json') for item in items],
            }
            TRENDS_CACHE_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
            logger.info(f"Saved {len(items)} trends to disk cache")
        except Exception as e:
            logger.warning(f"Failed to save disk cache: {e}")

    @property
    def is_fetching(self) -> bool:
        return self._is_fetching

    async def get_all_trends(self, force_refresh: bool = False) -> list[TrendItem]:
        """Get trends from all sources, with caching."""
        cache_key = f"all_trends_{datetime.now().strftime('%Y%m%d_%H')}"

        if not force_refresh and cache_key in self._cache:
            items, cached_at = self._cache[cache_key]
            if datetime.now() - cached_at < self._cache_ttl:
                return items

        # Check disk cache (24h validity)
        if not force_refresh and "all_trends_disk" in self._cache:
            items, cached_at = self._cache["all_trends_disk"]
            if datetime.now() - cached_at < timedelta(hours=24):
                return items

        self._is_fetching = True
        try:
            all_trends = []

            # Fetch from all sources concurrently
            tasks = [
                self._safe_fetch(self.nqa.fetch_trending, 50, True),
                self._safe_fetch(self.hongguo.fetch_trending),
                self._safe_fetch(self.tomato.fetch_trending),
            ]

            results = await asyncio.gather(*tasks)
            for items in results:
                all_trends.extend(items)

            # Deduplicate by title similarity
            unique = self._deduplicate(all_trends)

            # Sort by heat
            unique.sort(key=lambda x: x.heat, reverse=True)

            # Build trend clusters from tags
            self._build_clusters(unique)

            self._cache[cache_key] = (unique, datetime.now())
            # Save to disk
            self._save_disk_cache(unique)
            return unique
        finally:
            self._is_fetching = False

    async def _safe_fetch(self, fetch_fn, *args) -> list[TrendItem]:
        """Safely fetch trends, returning empty list on error."""
        try:
            return await fetch_fn(*args)
        except Exception as e:
            logger.error(f"Trend fetch error: {e}")
            return []

    def _deduplicate(self, items: list[TrendItem]) -> list[TrendItem]:
        """Remove duplicate items based on title similarity."""
        seen = set()
        unique = []
        for item in items:
            key = item.title[:15]
            if key not in seen:
                seen.add(key)
                unique.append(item)
        return unique

    def _build_clusters(self, trends: list[TrendItem]):
        """Build tag co-occurrence clusters for smarter related search."""
        co_occur = defaultdict(Counter)
        for t in trends:
            for i, tag1 in enumerate(t.tags):
                for tag2 in t.tags[i+1:]:
                    co_occur[tag1][tag2] += 1
                    co_occur[tag2][tag1] += 1

        # For each tag, keep top 5 co-occurring tags
        self._trend_clusters = {}
        for tag, related in co_occur.items():
            self._trend_clusters[tag] = [t for t, _ in related.most_common(5)]

    def _get_cluster_tags(self, tags: list[str]) -> list[str]:
        """Expand a set of tags with co-occurring cluster tags."""
        expanded = set(tags)
        for tag in tags:
            for related in self._trend_clusters.get(tag, []):
                if related not in expanded:
                    expanded.add(related)
        return list(expanded)

    async def get_trend_analysis(self, trends: list[TrendItem] = None) -> dict:
        """Analyze trends to extract patterns, genres, hot keywords."""
        if trends is None:
            trends = await self.get_all_trends()

        if not trends:
            return {
                "categories": {},
                "sources": {},
                "hot_keywords": [],
                "dynamic_genres": [],
                "dynamic_styles": [],
                "total_count": 0,
                "top_10": [],
            }

        # Category distribution
        categories = {}
        for t in trends:
            cat = t.category or "其他"
            if cat not in categories:
                categories[cat] = {"count": 0, "items": []}
            categories[cat]["count"] += 1
            if len(categories[cat]["items"]) < 5:
                categories[cat]["items"].append(t.title)

        # Source distribution
        sources = {}
        for t in trends:
            src = t.source.value
            sources[src] = sources.get(src, 0) + 1

        # Extract hot keywords from all tags and titles
        tag_counter = Counter()
        for t in trends:
            for tag in t.tags:
                tag_counter[tag] += 1

        hot_keywords = [k for k, v in tag_counter.most_common(30)]

        # Dynamic genres from tags - count both in tags and titles
        genre_keywords = [
            "重生", "复仇", "甜宠", "逆袭", "豪门", "总裁", "战神",
            "玄幻", "修仙", "都市", "古装", "宫斗", "仙侠", "末日",
            "系统", "女强", "男频", "穿越", "穿书", "赘婿", "龙王",
            "医神", "千金", "替身", "闪婚", "隐婚", "悬疑", "探案",
            "年代", "民国", "谍战", "抗战", "校园", "青春", "奇幻",
            "脑洞", "种田", "经营", "兽世", "无限流", "体育", "竞技",
            "动作", "喜剧", "虐恋", "追妻", "暗恋", "先婚后爱",
            "打脸", "虐渣", "马甲", "团宠", "权谋", "商战",
            "日久生情", "双向奔赴", "一见钟情", "追妻火葬场",
            "萌宝", "大女主", "赘婿", "龙王", "无敌",
        ]
        dynamic_genres = []
        for kw in genre_keywords:
            count = tag_counter.get(kw, 0)
            # Also count in titles
            title_count = sum(1 for t in trends if kw in t.title)
            total = count + title_count
            if total > 0:
                dynamic_genres.append({"name": kw, "count": total})

        dynamic_genres.sort(key=lambda x: x["count"], reverse=True)

        # Dynamic styles from tags
        style_keywords = [
            "古风", "现代", "赛博朋克", "日漫", "韩漫", "写实",
            "水彩", "油画", "像素", "国风", "二次元", "欧美",
            "写实主义", "超现实", "复古", "未来", "末日废土",
        ]
        dynamic_styles = []
        for kw in style_keywords:
            count = tag_counter.get(kw, 0)
            if count > 0:
                dynamic_styles.append({"name": kw, "count": count})

        # If not enough styles from tags, add common ones
        if len(dynamic_styles) < 5:
            for s in ["古风", "现代都市", "赛博朋克", "日漫", "韩漫", "写实", "国潮"]:
                if not any(ds["name"] == s for ds in dynamic_styles):
                    dynamic_styles.append({"name": s, "count": 0})

        # Trend clusters (top co-occurring tag groups)
        trend_clusters = []
        if self._trend_clusters:
            for tag, related in list(self._trend_clusters.items())[:10]:
                if tag_counter.get(tag, 0) >= 2:
                    trend_clusters.append({
                        "core": tag,
                        "related": related,
                        "count": tag_counter[tag],
                    })

        return {
            "categories": categories,
            "sources": sources,
            "hot_keywords": hot_keywords,
            "dynamic_genres": dynamic_genres[:30],
            "dynamic_styles": dynamic_styles[:15],
            "total_count": len(trends),
            "trend_clusters": trend_clusters,
            "top_10": [
                {
                    "title": t.title,
                    "source": t.source.value,
                    "heat": t.heat,
                    "tags": t.tags,
                    "description": t.description[:100] if t.description else "",
                    "url": t.url,
                }
                for t in trends[:10]
            ],
        }

    async def search_across_platforms(self, keyword: str) -> list[TrendItem]:
        """Search for a keyword across all platforms."""
        tasks = [
            self.nqa.search(keyword),
            self.hongguo.search_drama(keyword),
            self.tomato.search_novel(keyword),
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        all_results = []
        for result in results:
            if isinstance(result, list):
                all_results.extend(result)
        return self._deduplicate(all_results)

    async def get_related_trends(self, trend: TrendItem) -> list[TrendItem]:
        """Find trends related to a given trend using smart analysis."""
        related = []

        # 1. Active tag-based search on novelquickapp (most reliable)
        if trend.tags:
            tag_results = await self.nqa.search_related_by_tags(trend.tags[:3], limit=10)
            related.extend(tag_results)

        # 2. Search by original tags across platforms
        for tag in trend.tags[:3]:
            results = await self.search_across_platforms(tag)
            related.extend(results)

        # 3. Search by cluster-expanded tags (co-occurring tags)
        cluster_tags = self._get_cluster_tags(trend.tags[:3])
        for tag in cluster_tags[:3]:
            if tag not in trend.tags[:3]:
                results = await self.search_across_platforms(tag)
                related.extend(results)

        # 4. Search by title keywords
        title_words = re.findall(r'[\u4e00-\u9fff]{2,4}', trend.title)
        for word in title_words[:2]:
            results = await self.search_across_platforms(word)
            related.extend(results)

        # Deduplicate and remove the original trend
        related = self._deduplicate(related)
        related = [r for r in related if r.id != trend.id]

        return related[:20]

    async def get_genres_for_topic(self, topic: str) -> dict:
        """Get genres and styles dynamically based on a specific topic/trend."""
        all_trends = await self.get_all_trends()
        if not all_trends:
            return {"genres": [], "styles": []}

        topic_lower = topic.lower()
        # Find trends matching the topic
        matched = []
        for t in all_trends:
            if (topic_lower in t.title.lower() or
                any(topic_lower in tag.lower() for tag in t.tags) or
                (t.description and topic_lower in t.description.lower())):
                matched.append(t)

        # Also find related trends via clusters
        for t in all_trends[:5]:
            for tag in t.tags:
                if topic_lower in tag.lower():
                    matched.append(t)
                    break

        # Extract all tags from matched trends
        tag_counter = Counter()
        for t in matched:
            for tag in t.tags:
                tag_counter[tag] += 1

        # Also include tags from all trends weighted by heat
        for t in all_trends:
            for tag in t.tags:
                if tag not in tag_counter:
                    tag_counter[tag] += 1

        # Build genres from actual tags (no hardcoded list)
        genres = []
        seen = set()
        for tag, count in tag_counter.most_common(30):
            if len(tag) >= 2 and tag not in seen:
                seen.add(tag)
                genres.append({"value": tag, "label": tag, "count": count})

        # Extract styles from tags
        style_tags = []
        for t in matched:
            for tag in t.tags:
                if any(kw in tag for kw in ["风", "都市", "现代", "古", "赛博", "日漫", "韩漫", "写实", "国潮", "国风", "二次元", "欧美", "奇幻", "仙侠"]):
                    if tag not in style_tags:
                        style_tags.append(tag)

        if not style_tags:
            style_tags = ["古风", "现代都市", "赛博朋克", "日漫", "韩漫", "写实", "国潮"]

        # Infer suggested audience from genre tags
        male_genres = {"穿越", "战神", "赘婿", "玄幻", "系统", "商战", "谍战", "逆袭", "仙侠", "末日", "脑洞"}
        female_genres = {"重生", "甜宠", "复仇", "豪门", "总裁", "校园", "民国", "种田", "宫斗"}
        genre_set = {tag for tag, _ in tag_counter.most_common(10)}
        male_count = len(genre_set & male_genres)
        female_count = len(genre_set & female_genres)
        if male_count > female_count:
            suggested_audience = "18-35岁男性"
        elif female_count > male_count:
            suggested_audience = "18-35岁女性"
        else:
            suggested_audience = "全年龄"

        # Infer suggested style
        ancient_genres = {"古装", "穿越", "仙侠", "玄幻", "民国", "古风", "种田", "宫斗"}
        modern_genres = {"都市", "总裁", "豪门", "校园", "商战", "谍战"}
        if len(genre_set & ancient_genres) > len(genre_set & modern_genres):
            suggested_style = "古风"
        elif len(genre_set & modern_genres) > len(genre_set & ancient_genres):
            suggested_style = "现代都市"
        else:
            suggested_style = style_tags[0] if style_tags else "古风"

        return {
            "genres": genres[:20],
            "styles": style_tags[:10],
            "suggested_audience": suggested_audience,
            "suggested_style": suggested_style,
        }

    async def get_smart_suggestions(self, topic: str) -> dict:
        """Get smart suggestions for a user topic, combining trend data."""
        # Search across platforms
        search_results = await self.search_across_platforms(topic)

        # Get all trends
        all_trends = await self.get_all_trends()

        # Find trends that match the topic
        topic_lower = topic.lower()
        matched_trends = [t for t in all_trends if topic_lower in t.title.lower() or
                          any(topic_lower in tag for tag in t.tags)]

        # Extract relevant genres from matched trends
        genre_counter = Counter()
        for t in matched_trends:
            for tag in t.tags:
                genre_counter[tag] += 1

        suggested_genres = [g for g, _ in genre_counter.most_common(10)]

        # Find related tags via clusters
        related_tags = set()
        for tag in suggested_genres[:3]:
            for related in self._trend_clusters.get(tag, []):
                related_tags.add(related)

        return {
            "search_results": search_results[:10],
            "matched_trends": matched_trends[:10],
            "suggested_genres": suggested_genres,
            "related_tags": list(related_tags)[:10],
        }

    async def close(self):
        await self.nqa.close()
        await self.hongguo.close()
        await self.tomato.close()


trend_service = TrendService()
