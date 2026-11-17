"""Turns the places found in a transcribed page into rows the country map can show.

The pipeline gives every place mention a list of possible official places
(`official_place_candidates`). Here each mention goes through the same
resolver the project already has (place_lookup -> candidates -> country_codes):

  resolved       one place, with coordinates and a country  -> shown on the map
  no_country     one place, but no country code             -> kept for review
  ambiguous      several different places fit               -> kept for review
  no_candidates  nothing usable                             -> kept for review

Only "resolved" mentions go to the map. The rest stay in page_lines.places with
all their candidates, so a person can decide later. Nothing is guessed.
"""

import logging
from functools import lru_cache
from pathlib import Path

import config
from database.repository import Repository
from services.place_lookup import PlaceLookup, resolve_mention

logger = logging.getLogger("uvicorn.error")

SNIPPET_CHARS = 200


@lru_cache(maxsize=1)
def get_lookup() -> PlaceLookup:
    """The official place list, loaded once."""
    resources = Path(config.BASE_DIR) / "resources"
    return PlaceLookup.from_files(resources / "place_variants.json", resources / "localities.xml")


def resolve_page(lines: list[dict], lookup: PlaceLookup) -> list[dict]:
    """One dict per resolved mention, ready for repo.replace_page_mentions."""
    found = []
    for line in lines:
        text = (line.get("text") or "").strip()
        for mention in line.get("places") or []:
            choice = resolve_mention(
                {
                    "observed_text": mention["text"],
                    "place_candidates": mention.get("official_place_candidates") or [],
                },
                lookup,
            )
            if choice.status != "resolved" or not choice.official_place_id:
                continue
            found.append(
                {
                    "official_place_id": choice.official_place_id,
                    "name": choice.name,
                    "country_code": choice.country_code,
                    "lat": choice.latitude,
                    "lng": choice.longitude,
                    "snippet": text[:SNIPPET_CHARS],
                }
            )
    return found


def store_page_places(repo: Repository, page_id: str, lines: list[dict]) -> int:
    """Replace the map entries of one page. Returns how many mentions were stored.

    Never raises: the transcription is already saved, and a problem with the map
    must not turn a finished page into a failed one.
    """
    try:
        mentions = resolve_page(lines, get_lookup())
        repo.replace_page_mentions(page_id, mentions)
        return len(mentions)
    except Exception:
        logger.exception("Could not store the places of page %s", page_id)
        return 0
