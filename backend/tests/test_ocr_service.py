from app.services.ocr_service import OCRService


class FakeProvider:
    model_name = "test-vision-model"

    def __init__(self):
        self.calls = 0

    def generate_with_image(self, *args, **kwargs):
        self.calls += 1
        return '{"text":"Groq fallback","uncertain_regions":[]}'


def test_azure_ocr_is_preferred_when_configured(monkeypatch):
    provider = FakeProvider()
    service = OCRService(
        provider,
        azure_endpoint="https://vision.example.test",
        azure_key="secret",
    )
    monkeypatch.setattr(
        service,
        "_extract_with_azure",
        lambda image, mime: {"text": "Azure text", "uncertain_regions": []},
    )

    result = service.extract(b"image", "image/png")

    assert result["text"] == "Azure text"
    assert provider.calls == 0


def test_ocr_falls_back_to_llm_vision_when_azure_fails(monkeypatch):
    provider = FakeProvider()
    service = OCRService(
        provider,
        azure_endpoint="https://vision.example.test",
        azure_key="secret",
    )

    def fail_azure(image, mime):
        raise RuntimeError("azure unavailable")

    monkeypatch.setattr(service, "_extract_with_azure", fail_azure)

    result = service.extract(b"image", "image/png")

    assert result["text"] == "Groq fallback"
    assert provider.calls == 1
