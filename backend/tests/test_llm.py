"""Tests for the Gemini wrapper. A stub replaces the real Gemini client: no network, no key."""

from types import SimpleNamespace

import pytest
from google.genai import errors

import config
from services import llm as llm_module
from services.llm import (
    FakeLLM,
    GeminiLLM,
    LLMRateLimited,
    LLMUnavailable,
    default_llm,
    is_daily_limit,
    parse_retry_after,
)


class StubClient:
    """Plays back one behaviour per call: a string is the answer, an exception is raised."""

    def __init__(self, *behaviours):
        self.models = self
        self._behaviours = list(behaviours)
        self.calls = []

    def generate_content(self, *, model, contents, config=None):
        self.calls.append({"model": model, "contents": contents, "config": config})
        behaviour = self._behaviours.pop(0)
        if isinstance(behaviour, Exception):
            raise behaviour
        return SimpleNamespace(text=behaviour)


class Clock:
    def __init__(self):
        self.now = 1000.0

    def __call__(self):
        return self.now


def quota_error(retry_delay=None, message="You exceeded your current quota.", quota_id=None):
    details = []
    if retry_delay:
        details.append(
            {"@type": "type.googleapis.com/google.rpc.RetryInfo", "retryDelay": retry_delay}
        )
    if quota_id:
        details.append(
            {
                "@type": "type.googleapis.com/google.rpc.QuotaFailure",
                "violations": [{"quotaId": quota_id}],
            }
        )
    return errors.ClientError(
        429,
        {
            "error": {
                "code": 429,
                "message": message,
                "status": "RESOURCE_EXHAUSTED",
                "details": details,
            }
        },
    )


def make(client, clock=None, default_retry=60):
    return GeminiLLM(
        "key",
        "some-model",
        default_retry_seconds=default_retry,
        client=client,
        clock=clock or Clock(),
    )


def test_answer_is_returned_and_sent_with_model_system_text_and_prompt():
    client = StubClient("  Hello  ")
    assert make(client).generate("be brief", "say hi") == "Hello"
    call = client.calls[0]
    assert call["model"] == "some-model" and call["contents"] == "say hi"
    assert call["config"].system_instruction == "be brief"


@pytest.mark.parametrize("delay, expected", [("32s", 32), ("0.4s", 1), ("1.2s", 2)])
def test_wait_time_comes_from_the_retry_info_rounded_up(delay, expected):
    with pytest.raises(LLMRateLimited) as info:
        make(StubClient(quota_error(retry_delay=delay))).generate("s", "p")
    assert info.value.retry_after_seconds == expected


def test_wait_time_is_read_from_the_message_when_there_is_no_retry_info():
    error = quota_error(message="Quota exceeded. Please retry in 12.3s.")
    assert parse_retry_after(error) == 13


def test_default_wait_time_is_used_when_gemini_gives_none():
    with pytest.raises(LLMRateLimited) as info:
        make(StubClient(quota_error()), default_retry=45).generate("s", "p")
    assert info.value.retry_after_seconds == 45


def test_daily_limit_is_recognised_from_the_quota_name():
    assert is_daily_limit(quota_error(quota_id="GenerateRequestsPerDayPerProjectPerModel-FreeTier"))
    assert not is_daily_limit(quota_error(quota_id="GenerateRequestsPerMinutePerProjectPerModel"))
    assert not is_daily_limit(quota_error())


def test_after_a_limit_gemini_is_not_called_again_until_the_wait_is_over():
    clock = Clock()
    client = StubClient(quota_error(retry_delay="30s"), "back again")
    llm = make(client, clock)

    with pytest.raises(LLMRateLimited):
        llm.generate("s", "p")

    clock.now += 10
    with pytest.raises(LLMRateLimited) as info:
        llm.generate("s", "p")
    assert info.value.retry_after_seconds == 20
    assert len(client.calls) == 1  # the second request never reached Gemini

    clock.now += 21
    assert llm.generate("s", "p") == "back again"
    assert len(client.calls) == 2


def test_the_daily_flag_is_kept_while_waiting():
    clock = Clock()
    llm = make(StubClient(quota_error(retry_delay="3600s", quota_id="RequestsPerDay")), clock)
    with pytest.raises(LLMRateLimited):
        llm.generate("s", "p")
    with pytest.raises(LLMRateLimited) as info:
        llm.generate("s", "p")
    assert info.value.daily is True


@pytest.mark.parametrize(
    "failure",
    [
        errors.ServerError(500, {"error": {"message": "boom", "status": "INTERNAL"}}),
        errors.ClientError(
            403, {"error": {"message": "key SECRET-KEY refused", "status": "PERMISSION_DENIED"}}
        ),
        errors.ClientError(404, {"error": {"message": "model not found", "status": "NOT_FOUND"}}),
        TimeoutError("timed out"),
    ],
)
def test_other_failures_become_a_safe_unavailable_error(failure):
    with pytest.raises(LLMUnavailable) as info:
        make(StubClient(failure)).generate("s", "p")
    assert str(info.value) == "The AI service is not available right now."
    assert "SECRET-KEY" not in str(info.value)


def test_an_empty_answer_is_reported_not_returned():
    with pytest.raises(LLMUnavailable):
        make(StubClient("   ")).generate("s", "p")
    with pytest.raises(LLMUnavailable):
        make(StubClient(None)).generate("s", "p")


def test_unavailable_errors_do_not_start_a_wait():
    client = StubClient(errors.ServerError(503, {"error": {"message": "busy"}}), "fine")
    llm = make(client)
    with pytest.raises(LLMUnavailable):
        llm.generate("s", "p")
    assert llm.generate("s", "p") == "fine"


def test_default_llm_needs_a_key_and_a_model(monkeypatch):
    default_llm.cache_clear()
    monkeypatch.setattr(config, "GEMINI_API_KEY", "")
    monkeypatch.setattr(config, "GEMINI_MODEL", "some-model")
    with pytest.raises(LLMUnavailable):
        default_llm()
    default_llm.cache_clear()


def test_default_llm_is_one_shared_object(monkeypatch):
    default_llm.cache_clear()
    monkeypatch.setattr(config, "GEMINI_API_KEY", "key")
    monkeypatch.setattr(config, "GEMINI_MODEL", "some-model")
    assert default_llm() is default_llm()
    default_llm.cache_clear()


def test_fake_llm_records_calls_and_can_fail():
    fake = FakeLLM(reply="ok")
    assert fake.generate("s", "p") == "ok" and fake.calls == [("s", "p")]
    with pytest.raises(LLMRateLimited):
        FakeLLM(error=LLMRateLimited(5)).generate("s", "p")


def test_manual_check_reports_the_wait_time(monkeypatch, capsys):
    monkeypatch.setattr(
        llm_module, "default_llm", lambda: FakeLLM(error=LLMRateLimited(32, daily=True))
    )
    assert llm_module.main(["hi"]) == 3
    assert "Wait 32 seconds" in capsys.readouterr().out


# pytest tests/test_llm.py -v
