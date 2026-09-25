import httpx
import pytest

from app.services.ai_provider import TextGenerationProvider


def make_provider(*, groq: bool = True) -> TextGenerationProvider:
    provider = object.__new__(TextGenerationProvider)
    provider.groq_api_key = "test-key" if groq else ""
    provider.groq_model = "groq-model"
    provider.gemini_model = "gemini-model"
    provider._timeout = 60.0
    return provider


def test_groq_post_retries_rate_limit_using_retry_after(monkeypatch):
    provider = make_provider()
    request = httpx.Request("POST", provider._groq_url)
    responses = iter(
        [
            httpx.Response(429, headers={"retry-after": "0.25"}, request=request),
            httpx.Response(
                200,
                json={"choices": [{"message": {"content": "ok"}}]},
                request=request,
            ),
        ]
    )
    sleeps: list[float] = []
    monkeypatch.setattr(
        "app.services.ai_provider.httpx.post",
        lambda *a, **k: next(responses),
    )
    monkeypatch.setattr("app.services.ai_provider.time.sleep", sleeps.append)

    response = provider._groq_post({"model": "groq-model"})

    assert response.status_code == 200
    assert sleeps == [0.25]


def test_groq_post_stops_retrying_after_limit(monkeypatch):
    provider = make_provider()
    request = httpx.Request("POST", provider._groq_url)
    monkeypatch.setattr(
        "app.services.ai_provider.httpx.post",
        lambda *a, **k: httpx.Response(
            429,
            headers={"retry-after": "0"},
            request=request,
        ),
    )
    monkeypatch.setattr("app.services.ai_provider.time.sleep", lambda _: None)

    with pytest.raises(httpx.HTTPStatusError):
        provider._groq_post({"model": "groq-model"})


def test_groq_generate_caps_output_and_disables_reasoning(monkeypatch):
    provider = make_provider()
    captured: dict = {}
    request = httpx.Request("POST", provider._groq_url)

    def fake_post(payload):
        captured.update(payload)
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": "ok"}}]},
            request=request,
        )

    monkeypatch.setattr(provider, "_groq_post", fake_post)

    assert provider._groq_generate("prompt") == "ok"
    assert captured["max_completion_tokens"] == 2048
    assert captured["reasoning_effort"] == "none"


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
