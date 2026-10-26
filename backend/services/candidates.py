"""
What it does: for one word, our list can contain several possible places. 
This file picks the right one. If two entries are the same city (like Zürich twice, 1 km apart), 
it merges them and keeps the one that has a country.

Why it exists: we need one clear answer per word.
Special case: if the entries are really different places (two cities called Frankfurt), 
it says “unsure, a person must decide”. It never picks one at random


Our model gives each mention a list called place_candidates. Example for
"Tigurum" (the old name of Zürich): TWO candidates that are really the same city.

  1. "Zürich"  47.3769,  8.5417  from a diary PDF       -> no country
  2. "Zürich"  47.36667, 8.55    from the official list -> country "Schweiz"

  
What we do
----------
1. Throw away candidates without coordinates (we cannot put them on a map).
2. Group candidates that are the SAME place: same name AND close together.
   (Same name alone is not enough: "Frankfurt" exists in two far-away places.)
3. If more than one group is left, the word is ambiguous. We do NOT guess.
4. Inside the one group, prefer the candidate that has an official country.
5. Turn that country word into a code ("Schweiz" -> "CH").

The answer is a Choice with a status:
  resolved       one place, with coordinates and a country code
  no_country     one place found, but we cannot give a country code
  ambiguous      several different places fit; a person must decide
  no_candidates  nothing usable to work with


  Where the country comes from: candidates.py takes the country from the place list (localities.xml).
    It does not work it out by itself. We do the mapping, for example “Schweiz” becomes “CH”,
"""
import math
import unicodedata
from dataclasses import dataclass, field

from services.country_codes import country_code

# Two candidates with the same name closer than this are treated as one place.
# The duplicates in the real data are about 1 km apart.
SAME_PLACE_KM = 10


@dataclass
class Choice:
    status: str                     # resolved | no_country | ambiguous | no_candidates
    reason: str                     # one sentence a human can read
    name: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    country_code: str | None = None
    official_place_id: str | None = None   # e.g. "l587" in the Bullinger list
    alternatives: list[dict] = field(default_factory=list)  # filled when ambiguous


def _plain_name(name: str | None) -> str:
    """"Zürich" and "Zurich" and " zürich " all become "zurich"."""
    text = unicodedata.normalize("NFKD", (name or "").strip().casefold())
    return "".join(ch for ch in text if not unicodedata.combining(ch))


def _distance_km(a: dict, b: dict) -> float:
    """Straight-line distance between two candidates on the globe (haversine)."""
    lat1, lon1, lat2, lon2 = map(
        math.radians, (a["latitude"], a["longitude"], b["latitude"], b["longitude"]))
    h = (math.sin((lat2 - lat1) / 2) ** 2
         + math.cos(lat1) * math.cos(lat2) * math.sin((lon2 - lon1) / 2) ** 2)
    return 2 * 6371 * math.asin(math.sqrt(h))


def _official_country(candidate: dict) -> str:
    return ((candidate.get("official_name_fields") or {}).get("country") or "").strip()


def _same_place(a: dict, b: dict) -> bool:
    return (_plain_name(a.get("canonical_name")) == _plain_name(b.get("canonical_name"))
            and _distance_km(a, b) <= SAME_PLACE_KM)


def group_candidates(candidates: list[dict]) -> list[list[dict]]:
    """Put candidates that mean the same place into the same group."""
    groups: list[list[dict]] = []
    for candidate in candidates:
        for group in groups:
            if _same_place(group[0], candidate):
                group.append(candidate)
                break
        else:
            groups.append([candidate])
    return groups


def _best_of_group(group: list[dict]) -> dict:
    """The candidate with an official country wins; otherwise the first one."""
    with_country = [c for c in group if _official_country(c)]
    return (with_country or group)[0]


def _describe(candidate: dict) -> dict:
    """Small summary of a candidate, used in 'alternatives' for the reviewer."""
    return {
        "name": candidate.get("canonical_name"),
        "latitude": candidate["latitude"],
        "longitude": candidate["longitude"],
        "country": _official_country(candidate) or None,
    }


def choose_candidate(candidates: list[dict] | None) -> Choice:
    # 1. keep only candidates that have coordinates
    usable = [c for c in (candidates or [])
              if c.get("latitude") is not None and c.get("longitude") is not None]
    if not usable:
        return Choice("no_candidates", "No candidate with coordinates")

    # 2 + 3. group duplicates; several groups = several different places
    groups = group_candidates(usable)
    if len(groups) > 1:
        return Choice(
            "ambiguous",
            f"{len(groups)} different places fit; a person must decide",
            alternatives=[_describe(_best_of_group(g)) for g in groups],
        )

    # 4. one place: take its best candidate
    best = _best_of_group(groups[0])
    official_id = best.get("official_place_id")
    common = dict(
        name=best.get("canonical_name"),
        latitude=best["latitude"],
        longitude=best["longitude"],
        official_place_id=official_id,
    )

    # 5. country word -> code
    country_word = _official_country(best)
    if not country_word:
        return Choice("no_country", "Place found, but the source has no country", **common)
    code = country_code(country_word)
    if code is None:
        return Choice(
            "no_country",
            f"Place found, but the country '{country_word}' cannot be turned into a code",
            **common)
    return Choice("resolved", f"Matched to {best.get('canonical_name')} ({code})",
                  country_code=code, **common)