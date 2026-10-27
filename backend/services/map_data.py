"""Turns flat 'mention' rows into what the map needs.

One row = one time a place was found on one page. Example row:
  {"mention_id": "...", "place_name": "Geneva", "country_code": "CH",
   "snippet": "...arrived in Geneva on...", "page_id": "...", "page_number": 3,
   "document_id": "...", "document_name": "letter_001.pdf", "collection_id": "..."}
"""

from collections import defaultdict


def normalize_code(code: str | None) -> str | None:
    """'ch ' -> 'CH'. Returns None for empty / non 2-letter values."""
    if not code:
        return None
    code = code.strip().upper()
    return code if len(code) == 2 and code.isalpha() else None


def summarize_countries(rows: list[dict]) -> list[dict]:
    """One entry per country: how many mentions and how many different places.
    Rows without a valid country code are skipped (they cannot be coloured)."""
    mentions: dict[str, int] = defaultdict(int)
    places: dict[str, set] = defaultdict(set)
    for row in rows:
        code = normalize_code(row.get("country_code"))
        if code is None:
            continue
        mentions[code] += 1
        places[code].add(row.get("place_name"))
    result = [
        {"country_code": c, "mention_count": mentions[c], "place_count": len(places[c])}
        for c in mentions
    ]
    # Most mentioned first, then A-Z so the order is stable.
    return sorted(result, key=lambda x: (-x["mention_count"], x["country_code"]))


def mentions_for_country(rows: list[dict], country_code: str) -> list[dict]:
    """All mentions inside one country, in reading order (document, then page)."""
    wanted = normalize_code(country_code)
    out = [
        {
            "mention_id": r["mention_id"],
            "place_name": r["place_name"],
            "snippet": r.get("snippet"),
            "page_id": r["page_id"],
            "page_number": r["page_number"],
            "document_id": r["document_id"],
            "document_name": r["document_name"],
        }
        for r in rows
        if wanted and normalize_code(r.get("country_code")) == wanted
    ]
    return sorted(out, key=lambda m: (m["document_name"], m["page_number"], m["place_name"]))
