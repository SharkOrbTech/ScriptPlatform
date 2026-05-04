"""Main FastAPI application."""
import asyncio
import logging
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.core.config import get_settings
from app.core.database import init_db
from app.api import trends, scripts

settings = get_settings()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


_refresh_schedule = {"hour": 0, "minute": 0, "enabled": True}


async def _scheduled_trend_refresh():
    """Background task that refreshes trends at the configured time."""
    from datetime import timedelta
    while True:
        if not _refresh_schedule.get("enabled", True):
            await asyncio.sleep(60)
            continue
        now = datetime.now()
        target_hour = _refresh_schedule.get("hour", 0)
        target_minute = _refresh_schedule.get("minute", 0)
        target = now.replace(hour=target_hour, minute=target_minute, second=0, microsecond=0)
        if now >= target:
            target = target + timedelta(days=1)
        wait_seconds = (target - now).total_seconds()
        logger.info(f"Next trend refresh in {wait_seconds:.0f}s (at {target_hour:02d}:{target_minute:02d})")
        await asyncio.sleep(wait_seconds)

        try:
            from app.services.trend_service import trend_service
            logger.info(f"Running scheduled trend refresh at {target_hour:02d}:{target_minute:02d}...")
            await trend_service.get_all_trends(force_refresh=True)
            logger.info("Scheduled trend refresh completed")
        except Exception as e:
            logger.error(f"Scheduled trend refresh failed: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    await init_db()

    # Start scheduled trend refresh task
    refresh_task = asyncio.create_task(_scheduled_trend_refresh())

    yield

    refresh_task.cancel()
    logger.info("Shutting down...")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API routes
app.include_router(trends.router)
app.include_router(scripts.router)


@app.get("/api/health")
async def health_check():
    return {"status": "ok", "version": settings.APP_VERSION}


@app.get("/api/trends/fetch-status")
async def trends_fetch_status():
    """Check if trends are being fetched in the background."""
    from app.services.trend_service import trend_service
    return {"fetching": trend_service.is_fetching}


@app.get("/api/trends/refresh-schedule")
async def get_refresh_schedule():
    """Get the current refresh schedule."""
    return _refresh_schedule


@app.post("/api/trends/refresh-schedule")
async def set_refresh_schedule(data: dict):
    """Set the refresh schedule."""
    global _refresh_schedule
    if "hour" in data:
        _refresh_schedule["hour"] = max(0, min(23, int(data["hour"])))
    if "minute" in data:
        _refresh_schedule["minute"] = max(0, min(59, int(data["minute"])))
    if "enabled" in data:
        _refresh_schedule["enabled"] = bool(data["enabled"])
    return _refresh_schedule


@app.post("/api/trends/refresh")
async def refresh_trends():
    """Trigger a background trend refresh."""
    from app.services.trend_service import trend_service

    if trend_service.is_fetching:
        return {"status": "already_fetching"}

    async def _bg_refresh():
        try:
            await trend_service.get_all_trends(force_refresh=True)
        except Exception as e:
            logger.error(f"Background refresh failed: {e}")

    asyncio.create_task(_bg_refresh())
    return {"status": "started"}


@app.get("/api/config/topic/{topic}")
async def get_config_for_topic(topic: str):
    """Get genres/styles dynamically based on a specific topic."""
    from app.services.trend_service import trend_service
    try:
        result = await trend_service.get_genres_for_topic(topic)
        return result
    except Exception as e:
        logger.error(f"Topic config error: {e}")
        return {"genres": [], "styles": []}


@app.get("/api/config")
async def get_config():
    """Get public configuration with dynamic genres/styles from trends."""
    from app.services.trend_service import trend_service

    try:
        analysis = await trend_service.get_trend_analysis()
        dynamic_genres = analysis.get("dynamic_genres", [])
        dynamic_styles = analysis.get("dynamic_styles", [])
    except Exception:
        dynamic_genres = []
        dynamic_styles = []

    # Build genres list from dynamic data, with fallback
    genre_icons = {
        "重生": "🔄", "复仇": "⚔️", "甜宠": "💕", "逆袭": "📈",
        "豪门": "👑", "玄幻": "✨", "都市": "🏙️", "古装": "🏯",
        "悬疑": "🔍", "喜剧": "😂", "穿越": "🌀", "战神": "⚡",
        "赘婿": "👔", "系统": "🎮", "仙侠": "⚔️", "末日": "🌑",
        "校园": "🎓", "民国": "🏛️", "谍战": "🕵️", "年代": "📻",
        "奇幻": "🦄", "脑洞": "💡", "种田": "🌾", "商战": "📊",
    }

    genres = []
    seen = set()
    for g in dynamic_genres[:20]:
        name = g["name"]
        if name not in seen:
            seen.add(name)
            genres.append({
                "value": name,
                "label": name,
                "icon": genre_icons.get(name, "📖"),
                "count": g["count"],
            })

    # Ensure minimum genres
    fallback_genres = ["重生", "复仇", "甜宠", "逆袭", "豪门", "玄幻", "都市", "古装", "悬疑", "喜剧"]
    for fg in fallback_genres:
        if fg not in seen:
            seen.add(fg)
            genres.append({
                "value": fg,
                "label": fg,
                "icon": genre_icons.get(fg, "📖"),
                "count": 0,
            })

    # Build styles list
    styles = [s["name"] for s in dynamic_styles if s.get("count", 0) > 0]
    fallback_styles = ["古风", "现代都市", "赛博朋克", "日漫", "韩漫", "写实", "国潮"]
    for fs in fallback_styles:
        if fs not in styles:
            styles.append(fs)

    return {
        "genres": genres,
        "styles": styles[:15],
        "episode_counts": [3, 5, 8, 10, 12, 15, 20, 30],
    }
