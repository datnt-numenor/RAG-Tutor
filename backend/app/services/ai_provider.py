from __future__ import annotations

import base64
import json
import time
from collections.abc import Iterator
from functools import lru_cache

import httpx
import structlog
from google import genai
from google.genai import types

from app.core.config import get_settings


logger = structlog.get_logger()

_GROQ_MAX_RATE_LIMIT_RETRIES = 2
_GROQ_MAX_RETRY_DELAY_SECONDS = 60.0
_GROQ_MAX_COMPLETION_TOKENS = 2048


class TextGenerationProvider:
    """Use Groq when configured and transparently fall back to Gemini."""

    def __init__(
        self,
        *,
        groq_api_key: str | None,
        groq_model: str,
        groq_vision_model: str,
        gemini_api_key: str,
        gemini_model: str,
        timeout_seconds: float = 60.0,
    ):
        self.groq_api_key = (groq_api_key or "").strip()
        self.groq_model = groq_model
        self.groq_vision_model = groq_vision_model
        self.gemini_model = gemini_model
        self.model_name = groq_model if self.groq_api_key else gemini_model
        self._timeout = timeout_seconds
        self._gemini_client = genai.Client(
            api_key=gemini_api_key,
            http_options=types.HttpOptions(
                timeout=int(timeout_seconds * 1000),
                retry_options=types.HttpRetryOptions(attempts=1),
            ),
        )

    @property
    def _groq_url(self) -> str:
        return "https://api.groq.com/openai/v1/chat/completions"

    def _groq_headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.groq_api_key}",
            "Content-Type": "application/json",
        }

    def _groq_retry_delay(
        self,
        response: httpx.Response,
        *,
        attempt: int,
    ) -> float | None:
        if (
            response.status_code != 429
            or attempt >= _GROQ_MAX_RATE_LIMIT_RETRIES
        ):
            return None

        retry_after = response.headers.get("retry-after")
        try:
            delay = float(retry_after) if retry_after is not None else 2**attempt
        except ValueError:
            delay = 2**attempt
        delay = max(0.0, min(delay, _GROQ_MAX_RETRY_DELAY_SECONDS))
        logger.warning(
            "groq_rate_limited_retrying",
            attempt=attempt + 1,
            retry_after_seconds=delay,
            model=self.groq_model,
        )
        return delay

    def _groq_post(self, payload: dict) -> httpx.Response:
        for attempt in range(_GROQ_MAX_RATE_LIMIT_RETRIES + 1):
            response = httpx.post(
                self._groq_url,
                headers=self._groq_headers(),
                json=payload,
                timeout=self._timeout,
            )
            delay = self._groq_retry_delay(response, attempt=attempt)
            if delay is None:
                response.raise_for_status()
                return response
            response.close()
            time.sleep(delay)
        raise RuntimeError("Groq retry loop exhausted")

    def _groq_generate(self, prompt: str, *, json_mode: bool = False) -> str:
        payload: dict = {
            "model": self.groq_model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.2,
            "max_completion_tokens": _GROQ_MAX_COMPLETION_TOKENS,
            "reasoning_effort": "none",
        }
        if json_mode:
            payload["response_format"] = {"type": "json_object"}

        response = self._groq_post(payload)
        text = response.json()["choices"][0]["message"]["content"]
        if not text or not str(text).strip():
            raise ValueError("Groq returned empty text")
        return str(text)

    def _gemini_generate(self, prompt: str) -> str:
        interaction = self._gemini_client.interactions.create(
            model=self.gemini_model,
            input=prompt,
        )
        text = interaction.output_text
        if not text or not str(text).strip():
            raise ValueError("Gemini returned empty text")
        return str(text)

    def generate(self, prompt: str, *, json_mode: bool = False) -> str:
        if self.groq_api_key:
            try:
                return self._groq_generate(prompt, json_mode=json_mode)
            except Exception as exc:
                logger.warning(
                    "groq_generation_failed_using_gemini",
                    error_type=exc.__class__.__name__,
                    model=self.groq_model,
                )
        return self._gemini_generate(prompt)

    def _groq_stream(self, prompt: str) -> Iterator[str]:
        payload = {
            "model": self.groq_model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.2,
            "stream": True,
            "max_completion_tokens": _GROQ_MAX_COMPLETION_TOKENS,
            "reasoning_effort": "none",
        }
        for attempt in range(_GROQ_MAX_RATE_LIMIT_RETRIES + 1):
            with httpx.stream(
                "POST",
                self._groq_url,
                headers=self._groq_headers(),
                json=payload,
                timeout=self._timeout,
            ) as response:
                delay = self._groq_retry_delay(response, attempt=attempt)
                if delay is None:
                    response.raise_for_status()
                    for line in response.iter_lines():
                        if not line.startswith("data: "):
                            continue
                        data = line[6:]
                        if data == "[DONE]":
                            return
                        event = json.loads(data)
                        text = (
                            event.get("choices", [{}])[0]
                            .get("delta", {})
                            .get("content")
                        )
                        if text:
                            yield str(text)
                    return
            time.sleep(delay)

    def _gemini_stream(self, prompt: str) -> Iterator[str]:
        stream = self._gemini_client.interactions.create(
            model=self.gemini_model,
            input=prompt,
            stream=True,
        )
        for event in stream:
            if getattr(event, "event_type", None) != "step.delta":
                continue
            delta = getattr(event, "delta", None)
            if getattr(delta, "type", None) != "text":
                continue
            text = getattr(delta, "text", None)
            if text:
                yield str(text)

    def stream(self, prompt: str) -> Iterator[str]:
        emitted = False
        if self.groq_api_key:
            try:
                for text in self._groq_stream(prompt):
                    emitted = True
                    yield text
                if emitted:
                    return
            except Exception as exc:
                if emitted:
                    raise
                logger.warning(
                    "groq_stream_failed_using_gemini",
                    error_type=exc.__class__.__name__,
                    model=self.groq_model,
                )

        try:
            for text in self._gemini_stream(prompt):
                emitted = True
                yield text
        except Exception as exc:
            if emitted:
                raise
            logger.warning(
                "gemini_stream_failed_using_non_streaming",
                error_type=exc.__class__.__name__,
                model=self.gemini_model,
            )

        if not emitted:
            yield self._gemini_generate(prompt)

    def generate_with_image(
        self,
        prompt: str,
        image_bytes: bytes,
        mime_type: str,
        *,
        json_mode: bool = False,
    ) -> str:
        if self.groq_api_key:
            encoded = base64.b64encode(image_bytes).decode("ascii")
            payload: dict = {
                "model": self.groq_vision_model,
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:{mime_type};base64,{encoded}"
                                },
                            },
                        ],
                    }
                ],
                "temperature": 0.1,
                "max_completion_tokens": _GROQ_MAX_COMPLETION_TOKENS,
                "reasoning_effort": "none",
            }
            if json_mode:
                payload["response_format"] = {"type": "json_object"}
            try:
                response = self._groq_post(payload)
                text = response.json()["choices"][0]["message"]["content"]
                if text and str(text).strip():
                    return str(text)
                raise ValueError("Groq Vision returned empty text")
            except Exception as exc:
                logger.warning(
                    "groq_vision_failed_using_gemini",
                    error_type=exc.__class__.__name__,
                    model=self.groq_vision_model,
                )

        response = self._gemini_client.models.generate_content(
            model=self.gemini_model,
            contents=[
                types.Part.from_text(text=prompt),
                types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
            ],
        )
        text = response.text
        if not text or not str(text).strip():
            raise ValueError("Gemini Vision returned empty text")
        return str(text)


def _build_provider(gemini_model: str) -> TextGenerationProvider:
    settings = get_settings()
    return TextGenerationProvider(
        groq_api_key=settings.groq_api_key,
        groq_model=settings.groq_model,
        groq_vision_model=settings.groq_vision_model,
        gemini_api_key=settings.gemini_api_key,
        gemini_model=gemini_model,
        timeout_seconds=settings.ai_request_timeout_seconds,
    )


@lru_cache
def get_text_provider() -> TextGenerationProvider:
    return _build_provider(get_settings().gemini_model)


@lru_cache
def get_aux_text_provider() -> TextGenerationProvider:
    return _build_provider(get_settings().gemini_aux_model)
