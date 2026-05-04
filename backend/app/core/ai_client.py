import asyncio
import logging

import openai
import anthropic
from app.core.config import get_settings
from typing import AsyncGenerator

logger = logging.getLogger(__name__)
settings = get_settings()

MAX_RETRIES = 3
RETRY_DELAY = 2.0


class AIClient:
    def __init__(self):
        self.provider = settings.AI_PROVIDER
        if self.provider == "openai":
            self.client = openai.AsyncOpenAI(
                api_key=settings.OPENAI_API_KEY,
                base_url=settings.OPENAI_BASE_URL,
            )
            self.model = settings.OPENAI_MODEL
        else:
            self.client = anthropic.AsyncAnthropic(
                api_key=settings.ANTHROPIC_API_KEY,
            )
            self.model = "claude-sonnet-4-20250514"

    async def chat(self, messages: list[dict], temperature: float = 0.8, max_tokens: int = 8192) -> str:
        last_error = None
        for attempt in range(MAX_RETRIES):
            try:
                if self.provider == "openai":
                    resp = await self.client.chat.completions.create(
                        model=self.model,
                        messages=messages,
                        temperature=temperature,
                        max_tokens=max_tokens,
                    )
                    content = resp.choices[0].message.content
                    if not content:
                        raise ValueError("AI returned empty response")
                    return content
                else:
                    system = ""
                    anthropic_messages = []
                    for m in messages:
                        if m["role"] == "system":
                            system = m["content"]
                        else:
                            anthropic_messages.append(m)
                    resp = await self.client.messages.create(
                        model=self.model,
                        max_tokens=max_tokens,
                        system=system,
                        messages=anthropic_messages,
                        temperature=temperature,
                    )
                    content = resp.content[0].text
                    if not content:
                        raise ValueError("AI returned empty response")
                    return content
            except (openai.APIError, openai.APIConnectionError, openai.RateLimitError,
                    anthropic.APIError, anthropic.APIConnectionError, anthropic.RateLimitError,
                    ValueError, TimeoutError) as e:
                last_error = e
                logger.warning(f"AI call attempt {attempt + 1}/{MAX_RETRIES} failed: {e}")
                if attempt < MAX_RETRIES - 1:
                    await asyncio.sleep(RETRY_DELAY * (attempt + 1))
            except Exception as e:
                logger.error(f"Unexpected AI error: {e}", exc_info=True)
                raise

        raise Exception(f"AI调用失败（已重试{MAX_RETRIES}次）: {last_error}")

    async def chat_stream(self, messages: list[dict], temperature: float = 0.8, max_tokens: int = 8192) -> AsyncGenerator[str, None]:
        if self.provider == "openai":
            stream = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=True,
            )
            async for chunk in stream:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
        else:
            system = ""
            anthropic_messages = []
            for m in messages:
                if m["role"] == "system":
                    system = m["content"]
                else:
                    anthropic_messages.append(m)
            async with self.client.messages.stream(
                model=self.model,
                max_tokens=max_tokens,
                system=system,
                messages=anthropic_messages,
                temperature=temperature,
            ) as stream:
                async for text in stream.text_stream:
                    yield text


ai_client = AIClient()
