import httpx
import asyncio
import logging
from typing import Optional
from datetime import datetime

logger = logging.getLogger(__name__)

COMMON_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Connection": "keep-alive",
}


class BaseScraper:
    def __init__(self):
        self.client = httpx.AsyncClient(
            headers=COMMON_HEADERS,
            timeout=30.0,
            follow_redirects=True,
        )

    async def get(self, url: str, params: dict = None, headers: dict = None) -> Optional[httpx.Response]:
        try:
            resp = await self.client.get(url, params=params, headers=headers)
            resp.raise_for_status()
            return resp
        except Exception as e:
            logger.error(f"GET {url} failed: {e}")
            return None

    async def post(self, url: str, json: dict = None, data: dict = None, headers: dict = None) -> Optional[httpx.Response]:
        try:
            resp = await self.client.post(url, json=json, data=data, headers=headers)
            resp.raise_for_status()
            return resp
        except Exception as e:
            logger.error(f"POST {url} failed: {e}")
            return None

    async def close(self):
        await self.client.aclose()
