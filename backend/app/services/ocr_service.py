from __future__ import annotations

import json
import re
from functools import lru_cache

from google import genai
from google.genai import types

from app.core.config import get_settings


class OCRService:
    def __init__(self, api_key: str, model: str):
        self.client = genai.Client(api_key=api_key)
        self.model = model

    def _parse_json(self, text: str) -> dict:
        clean = re.sub(r"^\s*\x60\x60\x60(?:json)?\s*", "", text.strip(), flags=re.I)
        clean = re.sub(r"\s*\x60\x60\x60\s*$", "", clean)
        return json.loads(clean)

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

        response = self.client.models.generate_content(
            model=self.model,
            contents=[
                types.Part.from_text(text=prompt),
                types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
            ],
        )
        result = self._parse_json(response.text or "")
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
        api_key=settings.gemini_api_key,
        model=settings.gemini_model,
    )
