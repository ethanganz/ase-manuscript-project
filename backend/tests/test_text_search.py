"""Tests for turning a question into search words and finding lines. No database is used."""

from database.repository import InMemoryRepository
from services.text_search import extract_query_words, search_lines


def test_question_words_lose_filler_words_and_duplicates():
    assert extract_query_words("Who writes about Zürich? Tell me about Zürich and Basel!") == [
        "zürich",
        "basel",
    ]


def test_short_words_numbers_and_punctuation_are_ignored():
    assert extract_query_words("is it in 1549, a letter?") == ["letter"]


def test_german_and_latin_words_are_kept_and_filler_removed():
    assert extract_query_words("Wer schreibt über Tigurum?") == ["schreibt", "tigurum"]


def test_empty_or_only_filler_question_gives_no_words():
    assert extract_query_words("") == []
    assert extract_query_words(None) == []
    assert extract_query_words("what is this?") == []


def test_at_most_ten_words_are_used():
    question = "alpha bravo charlie delta echo foxtrot golf hotel india juliett kilo lima"
    assert extract_query_words(question) == question.split()[:10]


def _repo_with_lines():
    repo = InMemoryRepository()
    repo.documents["d1"] = {"id": "d1", "collection_id": "c1"}
    repo.documents["d2"] = {"id": "d2", "collection_id": "c2"}
    repo.pages["p1"] = {"id": "p1", "document_id": "d1", "page_number": 1}
    repo.pages["p2"] = {"id": "p2", "document_id": "d2", "page_number": 1}
    repo.upsert_text_lines(
        [
            {"source_line_id": "a", "text": "ad Zürich missi"},
            {"source_line_id": "b", "text": "Rex quidam Zürich et Basileę"},
            {"source_line_id": "c", "text": "Zürich in the other collection"},
            {"source_line_id": "d", "text": "no place here"},
        ]
    )
    repo.text_lines["a"]["page_id"] = "p1"
    repo.text_lines["b"]["page_id"] = "p1"
    repo.text_lines["c"]["page_id"] = "p2"
    # line "d" is not linked to any page
    return repo


def test_search_returns_only_lines_of_the_collection_best_first():
    repo = _repo_with_lines()
    hits = search_lines(repo, "Who mentions Zurich and a king, rex?", "c1")
    assert [h["source_line_id"] for h in hits] == ["b", "a"]


def test_search_ignores_accents_and_case():
    repo = _repo_with_lines()
    assert [h["source_line_id"] for h in search_lines(repo, "ZURICH", "c1")] == ["a", "b"]


def test_search_with_no_usable_words_does_not_touch_the_database():
    class Boom(InMemoryRepository):
        def search_text_lines(self, *a, **k):
            raise AssertionError("should not be called")

    assert search_lines(Boom(), "what is this?", "c1") == []


def test_unlinked_lines_are_never_returned():
    repo = _repo_with_lines()
    assert search_lines(repo, "place", "c1") == []


def test_limit_is_applied():
    repo = _repo_with_lines()
    assert len(search_lines(repo, "Zurich", "c1", limit=1)) == 1


# cd backend
# pytest tests/test_text_search.py tests/test_transcript_import.py -v


# select score, source_line_id, text from search_text_lines(array['exull']);       -- 878_01_r2l14, about 0.67
# select score, source_line_id, text from search_text_lines(array['basilea']);     -- 611_01_r1l31, about 0.75
# select score, source_line_id, text from search_text_lines(array['wirtemberg']);  -- 402_01_r1l1, about 0.91
