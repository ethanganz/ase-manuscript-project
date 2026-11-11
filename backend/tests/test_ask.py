"""Tests for the ask endpoint. A fake model replaces Gemini: no network, no key, no cost."""
from uuid import uuid4

import pytest

import config
from deps import get_llm
from main import app
from services.ask import (NO_MATCH, NOT_FOUND, SYSTEM_INSTRUCTION, UNSOURCED, build_prompt,
                          cited_numbers)
from services.llm import FakeLLM, LLMRateLimited, LLMUnavailable, default_llm


def use_llm(fake):
    app.dependency_overrides[get_llm] = lambda: fake
    return fake


def add_lines(repo, collection_id, texts):
    """Create one document with one page in the collection and link the lines to that page."""
    document_id, page_id = str(uuid4()), str(uuid4())
    repo.create_document({"id": document_id, "collection_id": collection_id})
    repo.create_pages([{"id": page_id, "document_id": document_id, "page_number": 3}])
    repo.upsert_text_lines([{"source_line_id": f"{page_id}-{i}", "text": text, "language": "la"}
                            for i, text in enumerate(texts)])
    for line in repo.text_lines.values():
        if line["source_line_id"].startswith(page_id):
            line["page_id"] = page_id
    return document_id, page_id


def ask(client, collection_id, question="Who writes about Zurich?"):
    return client.post(f"/api/collections/{collection_id}/ask", json={"question": question})


def test_answer_comes_back_with_the_cited_lines_and_their_page(client, repo, collection):
    document_id, page_id = add_lines(repo, collection["id"], ["ad Zürich missi", "nothing here"])
    fake = use_llm(FakeLLM(reply="Zürich is mentioned [1]."))

    response = ask(client, collection["id"])

    assert response.status_code == 200
    body = response.json()
    assert body["answer"] == "Zürich is mentioned [1]." and body["grounded"] is True
    assert len(body["sources"]) == 1
    source = body["sources"][0]
    assert source["label"] == 1 and source["text"] == "ad Zürich missi"
    assert source["page_id"] == page_id and source["document_id"] == document_id
    assert source["page_number"] == 3
    system, prompt = fake.calls[0]
    assert system == SYSTEM_INSTRUCTION
    assert "[1] ad Zürich missi" in prompt and prompt.endswith("Question: Who writes about Zurich?")


def test_only_lines_of_this_collection_reach_the_model(client, repo, collection):
    other = client.post("/api/collections", json={"name": "Other"}).json()
    add_lines(repo, collection["id"], ["Zürich in ours"])
    add_lines(repo, other["id"], ["Zürich in the other"])
    fake = use_llm(FakeLLM(reply="ok [1]"))

    ask(client, collection["id"])

    assert "in ours" in fake.calls[0][1] and "the other" not in fake.calls[0][1]


def test_no_matching_line_does_not_call_the_model(client, repo, collection):
    add_lines(repo, collection["id"], ["completely different words"])
    fake = use_llm(FakeLLM())
    body = ask(client, collection["id"]).json()
    assert body == {"answer": NO_MATCH, "sources": [], "grounded": False}
    assert fake.calls == []


def test_the_models_not_found_answer_has_no_sources(client, repo, collection):
    add_lines(repo, collection["id"], ["ad Zürich missi"])
    use_llm(FakeLLM(reply=f"{NOT_FOUND} [1]"))
    body = ask(client, collection["id"]).json()
    assert body == {"answer": NOT_FOUND, "sources": [], "grounded": False}


def test_an_answer_without_a_valid_citation_is_withheld(client, repo, collection):
    add_lines(repo, collection["id"], ["ad Zürich missi"])
    use_llm(FakeLLM(reply="Zürich is in Switzerland."))
    assert ask(client, collection["id"]).json() == {
        "answer": UNSOURCED, "sources": [], "grounded": False}
    use_llm(FakeLLM(reply="Zürich is mentioned [7]."))      # line 7 does not exist
    assert ask(client, collection["id"]).json()["answer"] == UNSOURCED


def test_rate_limit_becomes_429_with_wait_time_and_header(client, repo, collection):
    add_lines(repo, collection["id"], ["ad Zürich missi"])
    use_llm(FakeLLM(error=LLMRateLimited(32)))

    response = ask(client, collection["id"])

    assert response.status_code == 429
    assert response.headers["Retry-After"] == "32"
    detail = response.json()["detail"]
    assert detail["code"] == "llm_rate_limited" and detail["retry_after_seconds"] == 32
    assert detail["daily"] is False and "32 seconds" in detail["message"]


def test_daily_limit_message_does_not_promise_a_wait_time(client, repo, collection):
    add_lines(repo, collection["id"], ["ad Zürich missi"])
    use_llm(FakeLLM(error=LLMRateLimited(3600, daily=True)))
    detail = ask(client, collection["id"]).json()["detail"]
    assert detail["daily"] is True and "daily" in detail["message"]
    assert "3600" not in detail["message"]


def test_model_failure_becomes_503_with_a_safe_message(client, repo, collection):
    add_lines(repo, collection["id"], ["ad Zürich missi"])
    use_llm(FakeLLM(error=LLMUnavailable("The AI service is not available right now.")))
    response = ask(client, collection["id"])
    assert response.status_code == 503
    assert response.json()["detail"]["code"] == "llm_unavailable"


def test_missing_configuration_is_a_503_not_a_crash(client, repo, collection, monkeypatch):
    app.dependency_overrides.pop(get_llm, None)
    default_llm.cache_clear()
    monkeypatch.setattr(config, "GEMINI_API_KEY", "")
    response = ask(client, collection["id"])
    assert response.status_code == 503
    default_llm.cache_clear()


def test_unknown_collection_is_404_and_the_model_is_not_called(client):
    fake = use_llm(FakeLLM())
    assert ask(client, str(uuid4())).status_code == 404
    assert fake.calls == []


@pytest.mark.parametrize("question", ["", "   ", "x" * 501])
def test_bad_questions_are_rejected(client, collection, question):
    use_llm(FakeLLM())
    assert ask(client, collection["id"], question).status_code == 422


def test_prompt_has_one_numbered_line_each_and_no_line_breaks_inside_lines():
    prompt = build_prompt("Q?", [{"text": "first\nline  two"}, {"text": "second"}])
    assert prompt.splitlines()[1:3] == ["[1] first line two", "[2] second"]


@pytest.mark.parametrize("answer, expected", [
    ("A [1] and B [2][3].", [1, 2, 3]),
    ("A [1, 3] and again [1].", [1, 3]),
    ("Unknown [0] [9] and (1).", []),
    ("No citation at all.", []),
])
def test_cited_numbers(answer, expected):
    assert cited_numbers(answer, 3) == expected