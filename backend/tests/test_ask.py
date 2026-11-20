"""Tests for the ask endpoint. A fake model replaces Gemini: no network, no key, no cost."""

from uuid import uuid4

import pytest

import config
from deps import get_llm
from main import app
from services.ask import (
    SYSTEM_INSTRUCTION,
    build_prompt,
    cited_numbers,
)
from services.llm import FakeLLM, LLMRateLimited, LLMUnavailable, default_llm


def use_llm(fake):
    app.dependency_overrides[get_llm] = lambda: fake
    return fake


def add_lines(repo, collection_id, texts):
    """Create one document with one page in the collection and link the lines to that page."""
    document_id, page_id = str(uuid4()), str(uuid4())
    repo.create_document({"id": document_id, "collection_id": collection_id})
    repo.create_pages([{"id": page_id, "document_id": document_id, "page_number": 3}])
    repo.upsert_text_lines(
        [
            {"source_line_id": f"{page_id}-{i}", "text": text, "language": "la"}
            for i, text in enumerate(texts)
        ]
    )
    for line in repo.text_lines.values():
        if line["source_line_id"].startswith(page_id):
            line["page_id"] = page_id
    return document_id, page_id


def ask(client, collection_id, question="Who writes about Zurich?"):
    return client.post(f"/api/collections/{collection_id}/ask", json={"question": question})


DOC = "FROM THE DOCUMENTS:"
GEN = "FROM GENERAL KNOWLEDGE:"


def test_answer_is_split_into_documents_and_own_knowledge(client, repo, collection):
    document_id, page_id = add_lines(repo, collection["id"], ["ad Zürich missi", "nothing here"])
    fake = use_llm(
        FakeLLM(reply=f"{DOC}\nZürich is mentioned [1].\n\n{GEN}\nZürich is a city in Switzerland.")
    )

    response = ask(client, collection["id"])

    assert response.status_code == 200
    body = response.json()
    assert body["document_answer"] == "Zürich is mentioned [1]."
    assert body["general_answer"] == "Zürich is a city in Switzerland."
    assert body["grounded"] is True and len(body["sources"]) == 1
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
    fake = use_llm(FakeLLM(reply=f"{DOC}\nok [1]\n{GEN}\nnone"))

    ask(client, collection["id"])

    assert "in ours" in fake.calls[0][1] and "the other" not in fake.calls[0][1]


def test_question_without_matching_words_still_reaches_the_model(client, repo, collection):
    add_lines(repo, collection["id"], ["completely different words"])
    fake = use_llm(FakeLLM(reply=f"{DOC}\nIt is about different words [1].\n{GEN}\nnone"))
    body = ask(client, collection["id"], "Zzzz qqqq?").json()
    assert body["grounded"] is True
    assert "completely different words" in fake.calls[0][1]


def test_recognised_page_lines_are_used_when_no_text_lines_exist(client, repo, collection):
    document_id, page_id = str(uuid4()), str(uuid4())
    repo.create_document({"id": document_id, "collection_id": collection["id"]})
    repo.create_pages([{"id": page_id, "document_id": document_id, "page_number": 1}])
    repo.save_page_lines(page_id, [{"line_index": 0, "text": "Rex quidam exul factus"}], 100, 100)
    fake = use_llm(FakeLLM(reply=f"{DOC}\nA king became an exile [1].\n{GEN}\nnone"))

    body = ask(client, collection["id"], "Who became an exile?").json()

    assert body["grounded"] is True and body["sources"][0]["page_id"] == page_id
    assert "Rex quidam exul factus" in fake.calls[0][1]


def test_any_question_is_answered_even_when_the_collection_is_empty(client, repo, collection):
    fake = use_llm(FakeLLM(reply=f"{DOC}\nnone\n{GEN}\nParis is the capital of France."))
    body = ask(client, collection["id"], "What is the capital of France?").json()
    assert body["general_answer"] == "Paris is the capital of France."
    assert body["document_answer"] is None and body["sources"] == [] and body["grounded"] is False
    assert len(fake.calls) == 1 and "no transcribed lines" in fake.calls[0][1]


def test_a_document_claim_without_a_valid_citation_is_not_shown_as_from_the_documents(
    client, repo, collection
):
    add_lines(repo, collection["id"], ["ad Zürich missi"])
    use_llm(FakeLLM(reply=f"{DOC}\nZürich is in Switzerland [7].\n{GEN}\nnone"))  # no line 7
    body = ask(client, collection["id"]).json()
    assert body["document_answer"] is None and body["sources"] == [] and body["grounded"] is False


def test_a_reply_that_ignores_the_format_counts_as_general_knowledge(client, repo, collection):
    add_lines(repo, collection["id"], ["ad Zürich missi"])
    use_llm(FakeLLM(reply="Just some text [1]."))
    body = ask(client, collection["id"]).json()
    assert body["general_answer"] == "Just some text [1]."
    assert body["sources"] == [] and body["grounded"] is False


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


@pytest.mark.parametrize(
    "answer, expected",
    [
        ("A [1] and B [2][3].", [1, 2, 3]),
        ("A [1, 3] and again [1].", [1, 3]),
        ("Unknown [0] [9] and (1).", []),
        ("No citation at all.", []),
    ],
)
def test_cited_numbers(answer, expected):
    assert cited_numbers(answer, 3) == expected
