"""
Copyright Risk Checker - Automated plagiarism/copyright risk assessment.

Strategy:
1. Extract key elements from the generated script (title, character names, plot points)
2. Search across drama/novel platforms for similar content
3. Calculate similarity scores using multiple methods
4. Generate a risk report with suggestions
"""
import hashlib
import logging
import re
from collections import Counter
from datetime import datetime
from difflib import SequenceMatcher
from typing import Optional

from app.services.trend_service import trend_service
from app.models.schemas import Script, CopyrightResult

logger = logging.getLogger(__name__)


class CopyrightChecker:
    """Checks copyright risk of generated scripts against existing content."""

    async def check_script(self, script: Script) -> CopyrightResult:
        """Full copyright risk assessment of a script."""
        # Extract key elements
        elements = self._extract_elements(script)

        # Search for similar content
        all_results = []
        for keyword in elements["search_keywords"][:10]:  # Limit searches
            results = await trend_service.search_across_platforms(keyword)
            all_results.extend(results)

        # Calculate similarity scores
        similar_titles = self._find_similar(script, all_results)

        # Calculate overall risk
        risk_score = self._calculate_risk_score(script, similar_titles)
        risk_level = self._get_risk_level(risk_score)

        # Generate suggestions
        suggestions = self._generate_suggestions(risk_level, similar_titles, script)

        return CopyrightResult(
            risk_level=risk_level,
            risk_score=risk_score,
            similar_titles=similar_titles,
            suggestions=suggestions,
        )

    def _extract_elements(self, script: Script) -> dict:
        """Extract key searchable elements from a script."""
        # Title keywords
        title_words = re.findall(r'[\u4e00-\u9fff]{2,}', script.title)

        # Character names
        char_names = [c.name for c in script.characters]

        # Plot keywords from synopsis
        plot_words = re.findall(r'[\u4e00-\u9fff]{2,}', script.synopsis)
        plot_keywords = [w for w in plot_words if len(w) >= 2]

        # Genre-specific terms
        genre_terms = []
        genre_map = {
            "重生": ["重生", "回到过去", "记忆"],
            "复仇": ["复仇", "报仇", "反击"],
            "逆袭": ["逆袭", "翻盘", "翻身"],
            "甜宠": ["甜宠", "甜蜜", "恋爱"],
            "豪门": ["豪门", "世家", "有钱"],
            "总裁": ["总裁", "CEO", "霸道"],
            "战神": ["战神", "战王", "无敌"],
        }
        for key, terms in genre_map.items():
            if key in script.title or key in script.synopsis:
                genre_terms.extend(terms)

        # Combine all search keywords
        search_keywords = list(set(
            title_words + char_names[:3] + plot_keywords[:5] + genre_terms
        ))

        return {
            "title_words": title_words,
            "char_names": char_names,
            "plot_keywords": plot_keywords,
            "genre_terms": genre_terms,
            "search_keywords": search_keywords,
        }

    def _find_similar(self, script: Script, search_results: list) -> list[dict]:
        """Find similar content from search results."""
        similar = []

        # Compare title
        for result in search_results:
            title_sim = self._text_similarity(script.title, result.title)

            # Compare synopsis with description
            desc_sim = 0
            if result.description:
                desc_sim = self._text_similarity(script.synopsis[:200], result.description[:200])

            # Compare character names
            char_sim = 0
            for char in script.characters:
                if char.name in result.title:
                    char_sim = 0.8
                    break

            # Overall similarity
            overall_sim = max(title_sim, desc_sim * 0.8, char_sim)

            if overall_sim > 0.3:  # Threshold
                similar.append({
                    "title": result.title,
                    "source": result.source.value,
                    "similarity": round(overall_sim * 100, 1),
                    "match_type": "title" if title_sim == overall_sim else "content",
                    "url": result.url,
                })

        # Sort by similarity
        similar.sort(key=lambda x: x["similarity"], reverse=True)
        return similar[:10]

    def _text_similarity(self, text1: str, text2: str) -> float:
        """Calculate text similarity using multiple methods."""
        if not text1 or not text2:
            return 0.0

        # Method 1: Sequence matching
        seq_sim = SequenceMatcher(None, text1, text2).ratio()

        # Method 2: Jaccard similarity of characters
        set1 = set(text1)
        set2 = set(text2)
        jaccard_sim = len(set1 & set2) / len(set1 | set2) if set1 | set2 else 0

        # Method 3: Common substring ratio
        common_chars = sum(1 for c in text1 if c in text2)
        common_sim = common_chars / max(len(text1), len(text2))

        # Weighted average
        return seq_sim * 0.4 + jaccard_sim * 0.3 + common_sim * 0.3

    def _calculate_risk_score(self, script: Script, similar: list[dict]) -> float:
        """Calculate overall risk score (0-100)."""
        if not similar:
            return 10.0  # Low base risk

        # Highest similarity
        max_sim = max((s["similarity"] for s in similar), default=0)

        # Number of similar items
        count_factor = min(len(similar) / 5, 1.0)

        # Title uniqueness
        title_factor = 1.0 - max(
            self._text_similarity(script.title, s["title"])
            for s in similar
        ) if similar else 1.0

        # Calculate score
        score = max_sim * 0.5 + count_factor * 20 + title_factor * 30

        return min(max(score, 0), 100)

    def _get_risk_level(self, score: float) -> str:
        if score < 30:
            return "low"
        elif score < 60:
            return "medium"
        else:
            return "high"

    def _generate_suggestions(self, risk_level: str, similar: list[dict], script: Script) -> list[str]:
        """Generate actionable suggestions based on risk level."""
        suggestions = []

        if risk_level == "low":
            suggestions.append("版权风险较低，剧本原创性较高")
            suggestions.append("建议保持当前的创意方向")

        elif risk_level == "medium":
            suggestions.append("存在一定相似内容，建议调整以下方面：")
            if similar:
                most_similar = similar[0]
                suggestions.append(f"与「{most_similar['title']}」相似度较高({most_similar['similarity']}%)，建议修改核心设定")
            suggestions.append("建议更换角色名称，使用更有辨识度的名字")
            suggestions.append("建议调整剧情节奏和关键转折点")

        else:  # high
            suggestions.append("⚠️ 版权风险较高，强烈建议修改：")
            suggestions.append("重新设计核心剧情线，避免与已有作品雷同")
            suggestions.append("更换主要角色设定和人物关系")
            suggestions.append("调整故事背景和世界观设定")
            if similar:
                for s in similar[:3]:
                    suggestions.append(f"与「{s['title']}」(相似度{s['similarity']}%)存在雷同，需重点规避")

        # General suggestions
        suggestions.append("建议在正式使用前进行人工审核")
        suggestions.append("可以通过增加原创元素降低风险")

        return suggestions


copyright_checker = CopyrightChecker()
