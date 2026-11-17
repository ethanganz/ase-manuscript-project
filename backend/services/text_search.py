"""Find the transcript lines that are relevant to a question.

The question is reduced to its meaningful words, and the database looks for lines
that contain those words (or close spellings of them, see
``database/migrations/search_text_lines.sql``).

Limits, on purpose:
* This matches spellings, not meaning. An English question about "Zurich" will not
  find a Latin line that only says "Tigurum".
* Only the first ``MAX_WORDS`` meaningful words of a question are used.
"""

from __future__ import annotations

import re

from database.repository import Repository

MIN_WORD_LENGTH = 3
MAX_WORDS = 10
DEFAULT_LIMIT = 20

# Question words that say nothing about the content. Short words (under three
# letters) are dropped by the length rule and are not listed.
STOPWORDS = frozenset(
    [
        "the",
        "and",
        "for",
        "with",
        "from",
        "that",
        "this",
        "these",
        "those",
        "who",
        "whom",
        "whose",
        "what",
        "which",
        "when",
        "where",
        "why",
        "how",
        "did",
        "does",
        "was",
        "were",
        "are",
        "been",
        "being",
        "has",
        "have",
        "had",
        "will",
        "would",
        "can",
        "could",
        "should",
        "about",
        "into",
        "onto",
        "over",
        "under",
        "than",
        "then",
        "there",
        "their",
        "they",
        "them",
        "you",
        "your",
        "our",
        "his",
        "her",
        "its",
        "not",
        "any",
        "all",
        "some",
        "tell",
        "show",
        "find",
        "list",
        "give",
        "mention",
        "mentions",
        "mentioned",
        "say",
        "says",
        "said",
        "write",
        "writes",
        "wrote",
        "written",
        "der",
        "die",
        "das",
        "und",
        "ist",
        "wer",
        "was",
        "wo",
        "wie",
        "wann",
        "warum",
        "über",
        "von",
        "mit",
        "für",
        "nicht",
        "eine",
        "einen",
        "einem",
    ]
)

_WORD = re.compile(r"[^\W\d_]+", re.UNICODE)  # runs of letters, in any language


def extract_query_words(question: str, max_words: int = MAX_WORDS) -> list[str]:
    """Return the meaningful words of ``question``: lower case, no duplicates, in order."""
    words: list[str] = []
    for match in _WORD.finditer(question or ""):
        word = match.group().casefold()
        if len(word) < MIN_WORD_LENGTH or word in STOPWORDS or word in words:
            continue
        words.append(word)
        if len(words) == max_words:
            break
    return words


def search_lines(
    repo: Repository, question: str, collection_id: str, limit: int = DEFAULT_LIMIT
) -> list[dict]:
    """Best matching lines of one collection, best first. Empty if nothing matches."""
    words = extract_query_words(question)
    if not words:
        return []
    return repo.search_text_lines(words, collection_id, limit)
