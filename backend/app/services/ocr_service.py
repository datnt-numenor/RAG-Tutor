from __future__ import annotations

import json
import re
from functools import lru_cache

import httpx
import structlog

from app.core.config import get_settings
from app.services.ai_provider import TextGenerationProvider, get_text_provider


logger = structlog.get_logger()


class OCRService:
    def __init__(
        self,
        provider: TextGenerationProvider,
        *,
        azure_endpoint: str | None = None,
        azure_key: str | None = None,
        timeout_seconds: float = 60.0,
    ):
        self.provider = provider
        self.model = provider.model_name
        self.azure_endpoint = (azure_endpoint or "").strip().rstrip("/")
        self.azure_key = (azure_key or "").strip()
        self.timeout_seconds = timeout_seconds

    def _parse_json(self, text: str) -> dict:
        clean = re.sub(r"^\s*\x60\x60\x60(?:json)?\s*", "", text.strip(), flags=re.I)
        clean = re.sub(r"\s*\x60\x60\x60\s*$", "", clean)
        return json.loads(clean)

    def _extract_with_azure(self, image_bytes: bytes, mime_type: str) -> dict:
        response = httpx.post(
            f"{self.azure_endpoint}/computervision/imageanalysis:analyze",
            params={"api-version": "2024-02-01", "features": "read"},
            headers={
                "Ocp-Apim-Subscription-Key": self.azure_key,
                "Content-Type": mime_type,
            },
            content=image_bytes,
            timeout=self.timeout_seconds,
        )
        response.raise_for_status()
        blocks = (response.json().get("readResult") or {}).get("blocks") or []
        lines = [
            line
            for block in blocks
            for line in (block.get("lines") or [])
            if str(line.get("text") or "").strip()
        ]
        text = "\n".join(str(line["text"]).strip() for line in lines)
        if not text:
            raise ValueError("Azure Vision returned empty text")

        uncertain = []
        for line in lines:
            confidences = [
                float(word["confidence"])
                for word in (line.get("words") or [])
                if word.get("confidence") is not None
            ]
            if confidences and min(confidences) < 0.75:
                uncertain.append(
                    {
                        "text": str(line["text"]).strip(),
                        "reason": "Azure OCR confidence below 0.75",
                    }
                )
        return {"text": text, "uncertain_regions": uncertain}

    def extract(self, image_bytes: bytes, mime_type: str) -> dict:
        prompt = """
Bạn là OCR cho bài làm học tập.
Hãy chép lại chính xác nội dung viết tay hoặc in trong ảnh.
Không tự sửa kiến thức, không tự bổ sung câu trả lời.

Return ONLY JSON:
{
  "text": "toàn bộ nội dung nhận dạng",
  "uncertain_regions": [
    {
      "text": "đoạn OCR không chắc chắn",
      "reason": "lý do ngắn"
    }
  ]
}

Nếu không chắc một ký tự/từ, vẫn ghi cách đọc tốt nhất vào text và liệt kê nó trong uncertain_regions.
""".strip()

        if self.azure_endpoint and self.azure_key:
            try:
                return self._extract_with_azure(image_bytes, mime_type)
            except Exception as exc:
                logger.warning(
                    "azure_vision_failed_using_llm_vision",
                    error_type=exc.__class__.__name__,
                )

        result = self._parse_json(
            self.provider.generate_with_image(
                prompt,
                image_bytes,
                mime_type,
                json_mode=True,
            )
        )
        text = str(result.get("text") or "").strip()
        if not text:
            raise ValueError("OCR returned empty text")
        uncertain = result.get("uncertain_regions")
        if not isinstance(uncertain, list):
            uncertain = []
        return {
            "text": text,
            "uncertain_regions": uncertain,
        }


@lru_cache
def get_ocr_service() -> OCRService:
    settings = get_settings()
    return OCRService(
        provider=get_text_provider(),
        azure_endpoint=settings.azure_vision_endpoint,
        azure_key=settings.azure_vision_key,
        timeout_seconds=settings.ai_request_timeout_seconds,
    )
