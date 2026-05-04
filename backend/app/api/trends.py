"""API routes for trend fetching and analysis."""
from fastapi import APIRouter, Query
from app.services.trend_service import trend_service

router = APIRouter(prefix="/api/trends", tags=["trends"])


@router.get("")
async def get_trends(
    source: str = Query(default="all", description="数据源: all/hongguo/tomato"),
    force_refresh: bool = Query(default=False),
):
    """获取当前热点趋势"""
    trends = await trend_service.get_all_trends(force_refresh=force_refresh)

    if source != "all":
        trends = [t for t in trends if t.source.value == source]

    return {
        "items": [t.model_dump() for t in trends],
        "total": len(trends),
    }


@router.get("/analysis")
async def get_trend_analysis(force_refresh: bool = Query(default=False)):
    """获取热点趋势分析报告"""
    trends = await trend_service.get_all_trends(force_refresh=force_refresh)
    analysis = await trend_service.get_trend_analysis(trends)
    return analysis


@router.get("/search")
async def search_trends(keyword: str = Query(..., description="搜索关键词")):
    """跨平台搜索"""
    results = await trend_service.search_across_platforms(keyword)
    return {
        "items": [r.model_dump() for r in results],
        "total": len(results),
    }


@router.get("/suggestions")
async def get_smart_suggestions(topic: str = Query(..., description="用户输入的主题")):
    """智能推荐 - 基于用户主题提供热点匹配、题材建议"""
    result = await trend_service.get_smart_suggestions(topic)
    return {
        "search_results": [r.model_dump() for r in result["search_results"]],
        "matched_trends": [t.model_dump() for t in result["matched_trends"]],
        "suggested_genres": result["suggested_genres"],
        "related_tags": result["related_tags"],
    }


@router.get("/related/{trend_id}")
async def get_related_trends(trend_id: str):
    """获取与指定热点相关的热点"""
    trends = await trend_service.get_all_trends()
    target = None
    for t in trends:
        if t.id == trend_id:
            target = t
            break
    if not target:
        return {"items": [], "total": 0}
    related = await trend_service.get_related_trends(target)
    return {
        "items": [r.model_dump() for r in related],
        "total": len(related),
    }
