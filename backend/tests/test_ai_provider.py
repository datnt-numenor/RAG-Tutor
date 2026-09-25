import pytest

from app.services.ai_provider import TextGenerationProvider


def make_provider(*, groq: bool = True) -> TextGenerationProvider:
    provider = object.__new__(TextGenerationProvider)
    provider.groq_api_key = "test-key" if groq else ""
    provider.groq_model = "groq-model"
    provider.gemini_model = "gemini-model"
    return provider


def test_generate_uses_groq_when_configured(monkeypatch):
    provider = make_provider()
    monkeypatch.setattr(provider, "_groq_generate", lambda prompt, json_mode=False: "groq")
    monkeypatch.setattr(provider, "_gemini_generate", lambda prompt: "gemini")

    assert provider.generate("prompt") == "groq"


def test_generate_falls_back_to_gemini_when_groq_fails(monkeypatch):
    provider = make_provider()

    def fail(*args, **kwargs):
        raise RuntimeError("rate limited")

    monkeypatch.setattr(provider, "_groq_generate", fail)
    monkeypatch.setattr(provider, "_gemini_generate", lambda prompt: "gemini")

    assert provider.generate("prompt") == "gemini"


def test_stream_falls_back_before_first_groq_token(monkeypatch):
    provider = make_provider()

    def fail_stream(prompt):
        raise RuntimeError("transport failed")
        yield

    monkeypatch.setattr(provider, "_groq_stream", fail_stream)
    monkeypatch.setattr(provider, "_gemini_stream", lambda prompt: iter(["fallback"]))

    assert list(provider.stream("prompt")) == ["fallback"]


def test_empty_stream_falls_back_to_non_streaming_gemini(monkeypatch):
    provider = make_provider(groq=False)
    monkeypatch.setattr(provider, "_gemini_stream", lambda prompt: iter(()))
    monkeypatch.setattr(provider, "_gemini_generate", lambda prompt: "fallback")

    assert list(provider.stream("prompt")) == ["fallback"]


def test_stream_does_not_retry_after_partial_output(monkeypatch):
    provider = make_provider()

    def partial_stream(prompt):
        yield "partial"
        raise RuntimeError("interrupted")

    monkeypatch.setattr(provider, "_groq_stream", partial_stream)
    monkeypatch.setattr(provider, "_gemini_stream", lambda prompt: iter(["duplicate"]))
    stream = provider.stream("prompt")

    assert next(stream) == "partial"
    with pytest.raises(RuntimeError, match="interrupted"):
        next(stream)
